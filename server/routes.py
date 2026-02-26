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
    # matching_protocol removed - agents now use DecisionProcedure
    use_beliefs: bool = False
    info_env_name: str = "full"
    info_env_params: dict[str, Any] = {}


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


@router.get("/state")
async def get_state() -> dict[str, Any]:
    """Get current simulation state.

    Note: Returns raw dict to support both normal and comparison mode shapes.
    """
    return manager.get_state()


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
        use_beliefs=config.use_beliefs,
        info_env_name=config.info_env_name,
        info_env_params=config.info_env_params,
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
    # Validate run_name to prevent path traversal attacks
    if "/" in run_name or "\\" in run_name or run_name == ".." or run_name.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid run name")

    run_dir = RUNS_DIR / run_name

    # Additional safety: ensure resolved path stays under RUNS_DIR
    try:
        if not run_dir.resolve().is_relative_to(RUNS_DIR.resolve()):
            raise HTTPException(status_code=400, detail="Invalid run path")
    except ValueError:
        # is_relative_to can raise ValueError in some edge cases
        raise HTTPException(status_code=400, detail="Invalid run path")

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
                # Build belief map from belief_snapshots
                beliefs = {}
                for bs in tick_data.get("belief_snapshots", []):
                    beliefs[bs["agent_id"]] = {
                        "type_beliefs": [
                            {
                                "target_id": tb["target_agent_id"],
                                "believed_alpha": tb["believed_alpha"],
                                "confidence": tb["confidence"],
                                "n_interactions": tb["n_interactions"],
                            }
                            for tb in bs.get("type_beliefs", [])
                        ],
                        "price_belief": {
                            "mean": bs["price_belief"]["mean"],
                            "variance": bs["price_belief"]["variance"],
                            "n_observations": bs["price_belief"]["n_observations"],
                        } if bs.get("price_belief") else None,
                        "n_trades_in_memory": bs.get("n_trades_in_memory", 0),
                    }

                # Build agent alpha lookup for trade enrichment
                alpha_by_id = {
                    agent["agent_id"]: agent["alpha"]
                    for agent in tick_data.get("agent_snapshots", [])
                }

                # Transform to frontend format
                ticks.append({
                    "tick": tick_data["tick"],
                    "agents": [
                        {
                            "id": agent["agent_id"],
                            "position": agent["position"],
                            "endowment": agent["endowment"],
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
                            "tick": tick_data["tick"],
                            "agent1_id": trade["agent1_id"],
                            "agent2_id": trade["agent2_id"],
                            "proposer_id": trade.get("proposer_id"),
                            "alpha1": alpha_by_id.get(trade["agent1_id"], 0.5),
                            "alpha2": alpha_by_id.get(trade["agent2_id"], 0.5),
                            "pre_holdings_1": trade["pre_holdings"][0],
                            "pre_holdings_2": trade["pre_holdings"][1],
                            "post_allocation_1": trade["post_allocations"][0],
                            "post_allocation_2": trade["post_allocations"][1],
                            "gains": trade["gains"],
                        }
                        for trade in tick_data.get("trades", [])
                    ],
                    "metrics": {
                        "total_welfare": tick_data.get("total_welfare", 0),
                        "welfare_gains": tick_data.get("total_welfare", 0) - config.get("initial_welfare", 0),
                        "cumulative_trades": tick_data.get("cumulative_trades", 0),
                    },
                    "beliefs": beliefs,
                })

        return {
            "name": run_name,
            "config": config,
            "ticks": ticks,
            "n_ticks": len(ticks),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load run: {str(e)}")


# Scenario endpoints

class ScenarioInfo(BaseModel):
    """Info about a scenario."""
    name: str
    title: str
    complexity: int
    description: str
    n_agents: int
    grid_size: int


@router.get("/scenarios")
async def list_scenarios() -> list[ScenarioInfo]:
    """List available scenarios grouped by complexity."""
    try:
        from microecon.scenarios import load_all_scenarios

        scenarios = load_all_scenarios()
        return [
            ScenarioInfo(
                name=Path(s.path).stem,
                title=s.title,
                complexity=s.complexity,
                description=s.description or "",
                n_agents=len(s.config.agents),
                grid_size=s.config.grid_size,
            )
            for s in scenarios
        ]
    except Exception:
        return []


@router.get("/scenarios/{scenario_name}")
async def load_scenario(scenario_name: str) -> dict[str, Any]:
    """Load a specific scenario and return its config."""
    try:
        from microecon.scenarios import load_all_scenarios

        scenarios = load_all_scenarios()
        for s in scenarios:
            if Path(s.path).stem == scenario_name:
                return {
                    "name": scenario_name,
                    "title": s.title,
                    "complexity": s.complexity,
                    "description": s.description or "",
                    "config": {
                        "n_agents": len(s.config.agents),
                        "grid_size": s.config.grid_size,
                        "perception_radius": s.config.perception_radius,
                        "discount_factor": s.config.discount_factor,
                        "seed": None,  # Scenarios use fixed agent positions
                        "bargaining_protocol": "nash",
                        "use_beliefs": False,
                    },
                    "agents": [
                        {
                            "id": agent.id,
                            "position": agent.position,
                            "alpha": agent.alpha,
                            "endowment": agent.endowment,
                        }
                        for agent in s.config.agents
                    ],
                }

        raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_name}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load scenario: {str(e)}")
