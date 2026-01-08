"""WebSocket endpoint for real-time simulation streaming."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server.simulation_manager import manager

ws_router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections and shared simulation loop.

    All connected clients share a single simulation instance.
    The simulation loop is started once when any client requests start,
    and stopped when all clients disconnect or any client requests stop.
    """

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self._simulation_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, data: dict[str, Any]) -> None:
        """Broadcast data to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    async def start_simulation(self) -> None:
        """Start the shared simulation loop if not already running."""
        async with self._lock:
            if self._simulation_task is None or self._simulation_task.done():
                manager.start()
                self._simulation_task = asyncio.create_task(self._simulation_loop())
            # Broadcast status to all clients
            await self.broadcast({"type": "status", "running": True})

    async def stop_simulation(self) -> None:
        """Stop the shared simulation loop."""
        async with self._lock:
            manager.stop()
            if self._simulation_task is not None:
                self._simulation_task.cancel()
                try:
                    await self._simulation_task
                except asyncio.CancelledError:
                    pass
                self._simulation_task = None
            # Broadcast status to all clients
            await self.broadcast({"type": "status", "running": False})

    async def reset_simulation(self) -> None:
        """Reset simulation and broadcast to all clients."""
        async with self._lock:
            was_running = manager.running
            # Stop loop if running
            if self._simulation_task is not None:
                manager.stop()
                self._simulation_task.cancel()
                try:
                    await self._simulation_task
                except asyncio.CancelledError:
                    pass
                self._simulation_task = None

            # Reset simulation
            manager.reset()

            # Broadcast reset state to all clients
            tick_data = manager.get_tick_data()
            tick_data["type"] = "reset"
            tick_data["config"] = manager.config.to_dict()
            await self.broadcast(tick_data)

            # Restart if was running
            if was_running:
                manager.start()
                self._simulation_task = asyncio.create_task(self._simulation_loop())
                await self.broadcast({"type": "status", "running": True})

    async def update_config(self, config: Any) -> None:
        """Update config and broadcast to all clients."""
        async with self._lock:
            was_running = manager.running
            # Stop loop if running
            if self._simulation_task is not None:
                manager.stop()
                self._simulation_task.cancel()
                try:
                    await self._simulation_task
                except asyncio.CancelledError:
                    pass
                self._simulation_task = None

            # Create new simulation with config
            manager.create_simulation(config)

            # Broadcast config state to all clients
            tick_data = manager.get_tick_data()
            tick_data["type"] = "config"
            tick_data["config"] = manager.config.to_dict()
            await self.broadcast(tick_data)

            # Restart if was running
            if was_running:
                manager.start()
                self._simulation_task = asyncio.create_task(self._simulation_loop())
                await self.broadcast({"type": "status", "running": True})

    async def cleanup_on_last_disconnect(self) -> None:
        """Clean up when the last client disconnects."""
        async with self._lock:
            if len(self.active_connections) == 0 and self._simulation_task is not None:
                manager.stop()
                self._simulation_task.cancel()
                try:
                    await self._simulation_task
                except asyncio.CancelledError:
                    pass
                self._simulation_task = None

    async def enter_comparison_mode(
        self,
        config1: Any,
        config2: Any,
        label1: str = "A",
        label2: str = "B",
    ) -> None:
        """Enter comparison mode with two simulations."""
        async with self._lock:
            # Stop any running simulation
            if self._simulation_task is not None:
                manager.stop()
                self._simulation_task.cancel()
                try:
                    await self._simulation_task
                except asyncio.CancelledError:
                    pass
                self._simulation_task = None

            # Create comparison simulations
            sim_id1, sim_id2 = manager.create_comparison(config1, config2, label1, label2)

            # Broadcast comparison state to all clients
            state = manager.get_state()
            state["type"] = "comparison_init"
            await self.broadcast(state)

    async def exit_comparison_mode(self) -> None:
        """Exit comparison mode and return to single simulation."""
        async with self._lock:
            # Stop any running simulation
            if self._simulation_task is not None:
                manager.stop()
                self._simulation_task.cancel()
                try:
                    await self._simulation_task
                except asyncio.CancelledError:
                    pass
                self._simulation_task = None

            manager.exit_comparison()
            manager.create_simulation()

            # Broadcast exit state
            tick_data = manager.get_tick_data()
            tick_data["type"] = "comparison_exit"
            tick_data["config"] = manager.config.to_dict()
            await self.broadcast(tick_data)

    async def _simulation_loop(self) -> None:
        """Main simulation loop that broadcasts to all clients."""
        while manager.running:
            # Execute a tick
            manager.step()

            # Broadcast tick data to all connected clients
            if manager.comparison_mode:
                tick_data = manager.get_comparison_tick_data()
                tick_data["type"] = "comparison_tick"
            else:
                tick_data = manager.get_tick_data()
                tick_data["type"] = "tick"
            await self.broadcast(tick_data)

            # Wait based on speed setting
            delay = 1.0 / manager.speed
            await asyncio.sleep(delay)


connection_manager = ConnectionManager()


@ws_router.websocket("/ws/simulation")
async def simulation_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for simulation streaming.

    Protocol:
    - Client connects
    - Server sends initial state
    - Client can send commands: {"command": "start"|"stop"|"step"|"reset"|"speed", ...}
    - Server streams tick data when running
    - Comparison mode: {"command": "comparison", "config1": {...}, "config2": {...}}

    All clients share a single simulation. Commands from any client affect all clients.
    """
    await connection_manager.connect(websocket)

    # Send initial state
    if manager.comparison_mode:
        initial_state = manager.get_state()
        initial_state["type"] = "init"
    else:
        if manager.simulation is None:
            manager.create_simulation()
        initial_state = manager.get_tick_data()
        initial_state["type"] = "init"
        initial_state["config"] = manager.config.to_dict()
        initial_state["comparison_mode"] = False
    initial_state["running"] = manager.running
    await websocket.send_json(initial_state)

    try:
        while True:
            # Receive commands from client
            try:
                data = await websocket.receive_json()
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            command = data.get("command")

            if command == "start":
                await connection_manager.start_simulation()

            elif command == "stop":
                await connection_manager.stop_simulation()

            elif command == "step":
                if not manager.running:
                    manager.step()
                    if manager.comparison_mode:
                        tick_data = manager.get_comparison_tick_data()
                        tick_data["type"] = "comparison_tick"
                    else:
                        tick_data = manager.get_tick_data()
                        tick_data["type"] = "tick"
                    # Broadcast step to all clients
                    await connection_manager.broadcast(tick_data)

            elif command == "reset":
                await connection_manager.reset_simulation()

            elif command == "speed":
                speed = data.get("speed", 1.0)
                manager.set_speed(speed)
                # Broadcast speed to all clients
                await connection_manager.broadcast({"type": "speed", "speed": manager.speed})

            elif command == "config":
                from server.simulation_manager import SimulationConfig
                config_data = data.get("config", {})
                new_config = SimulationConfig.from_dict(config_data)
                await connection_manager.update_config(new_config)

            elif command == "comparison":
                # Enter comparison mode with two configs
                from server.simulation_manager import SimulationConfig
                config1_data = data.get("config1", {})
                config2_data = data.get("config2", {})
                label1 = data.get("label1", "A")
                label2 = data.get("label2", "B")
                config1 = SimulationConfig.from_dict(config1_data)
                config2 = SimulationConfig.from_dict(config2_data)
                await connection_manager.enter_comparison_mode(config1, config2, label1, label2)

            elif command == "exit_comparison":
                # Exit comparison mode
                await connection_manager.exit_comparison_mode()

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown command: {command}"
                })

    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
        await connection_manager.cleanup_on_last_disconnect()
    except Exception as e:
        connection_manager.disconnect(websocket)
        await connection_manager.cleanup_on_last_disconnect()
        print(f"WebSocket error: {e}")
