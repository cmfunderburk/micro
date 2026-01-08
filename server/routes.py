"""REST API routes for simulation control."""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.simulation_manager import manager, SimulationConfig

router = APIRouter()

# Default runs directory (can be configured)
RUNS_DIR = Path("./runs")


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


# Replay mode endpoints

class RunInfo(BaseModel):
    """Info about a saved run."""
    name: str
    path: str
    n_ticks: int
    protocol: str
    n_agents: int


class TickDataResponse(BaseModel):
    """Tick data for replay."""
    tick: int
    agents: list[dict[str, Any]]
    trades: list[dict[str, Any]]
    metrics: dict[str, Any]
    beliefs: dict[str, Any]


@router.get("/runs")
async def list_runs() -> list[RunInfo]:
    """List available saved runs."""
    runs = []

    if not RUNS_DIR.exists():
        return runs

    for run_dir in RUNS_DIR.iterdir():
        if not run_dir.is_dir():
            continue

        config_file = run_dir / "config.json"
        ticks_file = run_dir / "ticks.jsonl"

        if not config_file.exists() or not ticks_file.exists():
            continue

        try:
            import json
            with open(config_file) as f:
                config = json.load(f)

            # Count ticks
            n_ticks = sum(1 for _ in open(ticks_file))

            runs.append(RunInfo(
                name=run_dir.name,
                path=str(run_dir),
                n_ticks=n_ticks,
                protocol=config.get("protocol_name", "unknown"),
                n_agents=config.get("n_agents", 0),
            ))
        except Exception:
            continue

    return runs


@router.get("/runs/{run_name}")
async def load_run(run_name: str) -> dict[str, Any]:
    """Load a saved run for replay.

    Returns the full run data including all ticks.
    Client-side seeking per ADR-002.
    """
    run_dir = RUNS_DIR / run_name

    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"Run not found: {run_name}")

    config_file = run_dir / "config.json"
    ticks_file = run_dir / "ticks.jsonl"

    if not config_file.exists() or not ticks_file.exists():
        raise HTTPException(status_code=404, detail=f"Invalid run directory: {run_name}")

    try:
        import json

        with open(config_file) as f:
            config = json.load(f)

        ticks = []
        with open(ticks_file) as f:
            for line in f:
                tick_data = json.loads(line)
                # Transform to frontend format
                ticks.append({
                    "tick": tick_data["tick"],
                    "agents": [
                        {
                            "id": agent["agent_id"],
                            "position": agent["position"],
                            "endowment": [agent["endowment_x"], agent["endowment_y"]],
                            "alpha": agent["alpha"],
                            "utility": agent["utility"],
                            "perception_radius": agent.get("perception_radius", 7.0),
                            "discount_factor": agent.get("discount_factor", 0.95),
                            "has_beliefs": agent.get("has_beliefs", False),
                        }
                        for agent in tick_data.get("agent_snapshots", [])
                    ],
                    "trades": [
                        {
                            "tick": trade["tick"],
                            "agent1_id": trade["agent_1_id"],
                            "agent2_id": trade["agent_2_id"],
                            "alpha1": trade.get("alpha_1", 0.5),
                            "alpha2": trade.get("alpha_2", 0.5),
                            "pre_endowment_1": trade.get("pre_endowment_1", [0, 0]),
                            "pre_endowment_2": trade.get("pre_endowment_2", [0, 0]),
                            "post_allocation_1": [trade["allocation_1_x"], trade["allocation_1_y"]],
                            "post_allocation_2": [trade["allocation_2_x"], trade["allocation_2_y"]],
                            "gains": [trade.get("gain_1", 0), trade.get("gain_2", 0)],
                        }
                        for trade in tick_data.get("trades", [])
                    ],
                    "metrics": {
                        "total_welfare": tick_data.get("total_welfare", 0),
                        "welfare_gains": tick_data.get("total_welfare", 0) - config.get("initial_welfare", 0),
                        "cumulative_trades": tick_data.get("cumulative_trades", 0),
                    },
                    "beliefs": {},  # Beliefs not stored in standard format yet
                })

        return {
            "name": run_name,
            "config": config,
            "ticks": ticks,
            "n_ticks": len(ticks),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load run: {str(e)}")
