"""WebSocket endpoint for real-time simulation streaming."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.simulation_manager import manager

ws_router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

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


connection_manager = ConnectionManager()


async def simulation_loop() -> None:
    """Main simulation loop that runs when simulation is started."""
    while manager.running:
        # Execute a tick
        manager.step()

        # Broadcast tick data to all connected clients
        tick_data = manager.get_tick_data()
        tick_data["type"] = "tick"
        await connection_manager.broadcast(tick_data)

        # Wait based on speed setting
        delay = 1.0 / manager.speed
        await asyncio.sleep(delay)


@ws_router.websocket("/ws/simulation")
async def simulation_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for simulation streaming.

    Protocol:
    - Client connects
    - Server sends initial state
    - Client can send commands: {"command": "start"|"stop"|"step"|"reset"|"speed", ...}
    - Server streams tick data when running
    """
    await connection_manager.connect(websocket)

    # Send initial state
    if manager.simulation is None:
        manager.create_simulation()

    initial_state = manager.get_tick_data()
    initial_state["type"] = "init"
    initial_state["config"] = manager.config.to_dict()
    await websocket.send_json(initial_state)

    # Background task for simulation loop
    simulation_task: asyncio.Task | None = None

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
                manager.start()
                if simulation_task is None or simulation_task.done():
                    simulation_task = asyncio.create_task(simulation_loop())
                await websocket.send_json({"type": "status", "running": True})

            elif command == "stop":
                manager.stop()
                if simulation_task is not None:
                    simulation_task.cancel()
                    try:
                        await simulation_task
                    except asyncio.CancelledError:
                        pass
                    simulation_task = None
                await websocket.send_json({"type": "status", "running": False})

            elif command == "step":
                if not manager.running:
                    manager.step()
                    tick_data = manager.get_tick_data()
                    tick_data["type"] = "tick"
                    await websocket.send_json(tick_data)

            elif command == "reset":
                was_running = manager.running
                if simulation_task is not None:
                    simulation_task.cancel()
                    try:
                        await simulation_task
                    except asyncio.CancelledError:
                        pass
                    simulation_task = None
                manager.reset()
                tick_data = manager.get_tick_data()
                tick_data["type"] = "reset"
                tick_data["config"] = manager.config.to_dict()
                await websocket.send_json(tick_data)
                # Restart if was running
                if was_running:
                    manager.start()
                    simulation_task = asyncio.create_task(simulation_loop())

            elif command == "speed":
                speed = data.get("speed", 1.0)
                manager.set_speed(speed)
                await websocket.send_json({"type": "speed", "speed": manager.speed})

            elif command == "config":
                from backend.simulation_manager import SimulationConfig
                config_data = data.get("config", {})
                new_config = SimulationConfig.from_dict(config_data)
                was_running = manager.running
                if simulation_task is not None:
                    simulation_task.cancel()
                    try:
                        await simulation_task
                    except asyncio.CancelledError:
                        pass
                    simulation_task = None
                manager.create_simulation(new_config)
                tick_data = manager.get_tick_data()
                tick_data["type"] = "config"
                tick_data["config"] = manager.config.to_dict()
                await websocket.send_json(tick_data)
                if was_running:
                    manager.start()
                    simulation_task = asyncio.create_task(simulation_loop())

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown command: {command}"
                })

    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
        # Don't stop simulation on disconnect - other clients may be connected
    except Exception as e:
        connection_manager.disconnect(websocket)
        # Log error but don't crash
        print(f"WebSocket error: {e}")
    finally:
        # Clean up simulation task if this was the last client
        if simulation_task is not None and len(connection_manager.active_connections) == 0:
            manager.stop()
            simulation_task.cancel()
            try:
                await simulation_task
            except asyncio.CancelledError:
                pass
