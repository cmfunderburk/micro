"""REST API routes for simulation control."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.simulation_manager import manager, SimulationConfig

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str


class ConfigRequest(BaseModel):
    n_agents: int = 10
    grid_size: int = 15
    perception_radius: float = 7.0
    discount_factor: float = 0.95
    seed: int | None = None
    bargaining_protocol: str = "nash"
    matching_protocol: str = "opportunistic"
    use_beliefs: bool = False


class SpeedRequest(BaseModel):
    speed: float


class StateResponse(BaseModel):
    running: bool
    speed: float
    config: dict[str, Any]
    tick_data: dict[str, Any]


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok", version="0.1.0")


@router.get("/state", response_model=StateResponse)
async def get_state() -> StateResponse:
    """Get current simulation state."""
    state = manager.get_state()
    return StateResponse(**state)


@router.post("/simulation/start")
async def start_simulation() -> dict[str, str]:
    """Start continuous simulation."""
    manager.start()
    return {"status": "started"}


@router.post("/simulation/stop")
async def stop_simulation() -> dict[str, str]:
    """Stop continuous simulation."""
    manager.stop()
    return {"status": "stopped"}


@router.post("/simulation/step")
async def step_simulation() -> dict[str, Any]:
    """Execute a single simulation tick."""
    manager.step()
    return manager.get_tick_data()


@router.post("/simulation/reset")
async def reset_simulation() -> dict[str, Any]:
    """Reset simulation to initial state."""
    manager.reset()
    return manager.get_tick_data()


@router.get("/config")
async def get_config() -> dict[str, Any]:
    """Get current simulation configuration."""
    return manager.config.to_dict()


@router.post("/config")
async def set_config(config: ConfigRequest) -> dict[str, Any]:
    """Update simulation configuration and reset."""
    new_config = SimulationConfig(
        n_agents=config.n_agents,
        grid_size=config.grid_size,
        perception_radius=config.perception_radius,
        discount_factor=config.discount_factor,
        seed=config.seed,
        bargaining_protocol=config.bargaining_protocol,
        matching_protocol=config.matching_protocol,
        use_beliefs=config.use_beliefs,
    )
    manager.create_simulation(new_config)
    return manager.config.to_dict()


@router.post("/simulation/speed")
async def set_speed(request: SpeedRequest) -> dict[str, float]:
    """Set simulation speed (ticks per second)."""
    manager.set_speed(request.speed)
    return {"speed": manager.speed}
