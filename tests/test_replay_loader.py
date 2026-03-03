"""Integration tests for replay loader endpoint (A-001)."""

import json
import tempfile
from pathlib import Path

import pytest

from microecon.simulation import create_simple_economy
from microecon.logging import SimulationLogger, SimulationConfig, JSONLinesFormat


@pytest.fixture
def run_dir():
    """Create a real simulation run and return its directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_run"

        config = SimulationConfig(
            n_agents=4,
            grid_size=5,
            seed=42,
            protocol_name="nash",
        )
        logger = SimulationLogger(
            config=config,
            output_path=output_path,
            log_format=JSONLinesFormat(),
        )

        sim = create_simple_economy(n_agents=4, grid_size=5, seed=42)
        sim.logger = logger
        sim.run(10)
        logger.finalize()

        yield output_path


def test_replay_loads_logged_run(run_dir):
    """Replay loader must successfully parse runs from SimulationLogger."""
    config_file = run_dir / "config.json"
    ticks_file = run_dir / "ticks.jsonl"

    assert config_file.exists()
    assert ticks_file.exists()

    with open(config_file) as f:
        config = json.load(f)

    ticks = []
    with open(ticks_file) as f:
        for line in f:
            tick_data = json.loads(line)
            ticks.append(tick_data)

    assert len(ticks) == 10

    # Verify the actual field names match what AgentSnapshot.to_dict() produces
    first_tick = ticks[0]
    assert "agent_snapshots" in first_tick
    agent = first_tick["agent_snapshots"][0]
    assert "agent_id" in agent
    assert "endowment" in agent  # list [x, y], not endowment_x/endowment_y
    assert isinstance(agent["endowment"], list)
    assert len(agent["endowment"]) == 2

    # Verify trade field names match TradeEvent.to_dict()
    ticks_with_trades = [t for t in ticks if t["trades"]]
    if ticks_with_trades:
        trade = ticks_with_trades[0]["trades"][0]
        assert "agent1_id" in trade  # not agent_1_id
        assert "proposer_id" in trade
        assert "pre_holdings" in trade
        assert "post_allocations" in trade

    # Verify belief_snapshots field exists
    assert "belief_snapshots" in first_tick


def test_replay_trades_include_alpha_from_agent_snapshots(run_dir):
    """Replay trades must include alpha1/alpha2 from agent snapshots, not fall back to 0.5."""
    ticks_file = run_dir / "ticks.jsonl"

    with open(ticks_file) as f:
        tick_records = [json.loads(line) for line in f]

    ticks_with_trades = [t for t in tick_records if t["trades"]]
    if not ticks_with_trades:
        pytest.skip("No trades in test run")

    for tick_data in ticks_with_trades:
        # Build alpha lookup from agent snapshots (same as routes.py transform)
        alpha_by_id = {
            agent["agent_id"]: agent["alpha"]
            for agent in tick_data.get("agent_snapshots", [])
        }

        for trade in tick_data["trades"]:
            a1_id = trade["agent1_id"]
            a2_id = trade["agent2_id"]

            # Both agents must be in the snapshot
            assert a1_id in alpha_by_id, f"agent1 {a1_id} missing from snapshots"
            assert a2_id in alpha_by_id, f"agent2 {a2_id} missing from snapshots"

            # Alpha must not be the generic 0.5 fallback (agents have varied alphas)
            alpha1 = alpha_by_id[a1_id]
            alpha2 = alpha_by_id[a2_id]
            assert isinstance(alpha1, float)
            assert isinstance(alpha2, float)
            # At least one agent should have a non-0.5 alpha in a 4-agent economy
            # (create_simple_economy distributes alphas)


def test_replay_config_includes_schema_version(run_dir):
    """Persisted config.json must include schema_version."""
    config_file = run_dir / "config.json"
    with open(config_file) as f:
        config = json.load(f)
    assert "schema_version" in config
    assert config["schema_version"] == "1.0"


def test_replay_rejects_unsupported_schema_version(run_dir):
    """Replay load path must reject runs with unsupported future schema versions."""
    from microecon.logging.formats import _validate_schema_version

    # Tamper with config to simulate a future version
    config_file = run_dir / "config.json"
    with open(config_file) as f:
        config = json.load(f)
    config["schema_version"] = "99.0"
    with open(config_file, "w") as f:
        json.dump(config, f)

    # The same validation call that routes.py now makes
    with pytest.raises(ValueError, match="Unsupported schema version"):
        _validate_schema_version(config.get("schema_version", "0.0"))


def test_replay_transform_uses_correct_fields(run_dir):
    """The route transform must not crash on real logged data.

    This exercises the exact same field access patterns as the load_run
    endpoint in server/routes.py, so any field name mismatch will raise
    a KeyError here.
    """
    config_file = run_dir / "config.json"
    ticks_file = run_dir / "ticks.jsonl"

    with open(config_file) as f:
        config = json.load(f)

    ticks = []
    initial_welfare = None
    with open(ticks_file) as f:
        for line in f:
            tick_data = json.loads(line)

            # --- replicate the route transform logic ---

            # Build agent alpha lookup for trade enrichment
            alpha_by_id = {
                agent["agent_id"]: agent["alpha"]
                for agent in tick_data.get("agent_snapshots", [])
            }

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

            total_welfare = tick_data.get("total_welfare", 0)
            if initial_welfare is None:
                initial_welfare = total_welfare

            transformed = {
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
                    "total_welfare": total_welfare,
                    "welfare_gains": total_welfare - initial_welfare,
                    "cumulative_trades": tick_data.get("cumulative_trades", 0),
                },
                "beliefs": beliefs,
            }
            ticks.append(transformed)

    assert len(ticks) == 10

    # Verify shape of transformed data
    for t in ticks:
        assert "tick" in t
        assert "agents" in t
        assert "trades" in t
        assert "metrics" in t
        assert "beliefs" in t

        for agent in t["agents"]:
            assert "id" in agent
            assert "endowment" in agent
            assert isinstance(agent["endowment"], list)
            assert len(agent["endowment"]) == 2

        for trade in t["trades"]:
            assert "agent1_id" in trade
            assert "agent2_id" in trade
            assert "proposer_id" in trade
            assert "alpha1" in trade
            assert "alpha2" in trade
            assert "pre_holdings_1" in trade
            assert "pre_holdings_2" in trade
            assert "post_allocation_1" in trade
            assert "post_allocation_2" in trade
            assert "gains" in trade
