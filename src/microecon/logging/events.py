"""Event dataclasses for simulation logging.

These frozen dataclasses capture the complete state of each simulation tick,
including search evaluations, movement decisions, and trade outcomes.
All fields use primitive types (int, float, str, tuple) for JSON serialization.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SimulationConfig:
    """Configuration snapshot for a simulation run."""

    n_agents: int
    grid_size: int
    seed: int
    protocol_name: str  # "nash" or "rubinstein"
    protocol_params: dict[str, Any] = field(default_factory=dict)
    perception_radius: float = 3.0
    discount_factor: float = 0.95
    movement_budget: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_agents": self.n_agents,
            "grid_size": self.grid_size,
            "seed": self.seed,
            "protocol_name": self.protocol_name,
            "protocol_params": self.protocol_params,
            "perception_radius": self.perception_radius,
            "discount_factor": self.discount_factor,
            "movement_budget": self.movement_budget,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SimulationConfig":
        return cls(
            n_agents=d["n_agents"],
            grid_size=d["grid_size"],
            seed=d["seed"],
            protocol_name=d["protocol_name"],
            protocol_params=d.get("protocol_params", {}),
            perception_radius=d.get("perception_radius", 3.0),
            discount_factor=d.get("discount_factor", 0.95),
            movement_budget=d.get("movement_budget", 1),
        )


@dataclass(frozen=True)
class AgentSnapshot:
    """Complete agent state at a point in time."""

    agent_id: str
    position: tuple[int, int]  # (row, col)
    endowment: tuple[float, float]  # (x, y)
    alpha: float  # preference parameter
    utility: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "position": list(self.position),
            "endowment": list(self.endowment),
            "alpha": self.alpha,
            "utility": self.utility,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "AgentSnapshot":
        return cls(
            agent_id=d["agent_id"],
            position=tuple(d["position"]),
            endowment=tuple(d["endowment"]),
            alpha=d["alpha"],
            utility=d["utility"],
        )


@dataclass(frozen=True)
class TargetEvaluation:
    """Evaluation of a potential trade partner during search."""

    target_id: str
    target_position: tuple[int, int]
    distance: float  # Euclidean distance
    ticks_to_reach: int  # Chebyshev distance (movement ticks required)
    expected_surplus: float  # Nash bargaining surplus
    discounted_value: float  # surplus * (delta ^ ticks_to_reach)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "target_position": list(self.target_position),
            "distance": self.distance,
            "ticks_to_reach": self.ticks_to_reach,
            "expected_surplus": self.expected_surplus,
            "discounted_value": self.discounted_value,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TargetEvaluation":
        return cls(
            target_id=d["target_id"],
            target_position=tuple(d["target_position"]),
            distance=d["distance"],
            ticks_to_reach=d["ticks_to_reach"],
            expected_surplus=d["expected_surplus"],
            discounted_value=d["discounted_value"],
        )


@dataclass(frozen=True)
class SearchDecision:
    """Complete record of an agent's search decision for a tick."""

    agent_id: str
    position: tuple[int, int]
    visible_agents: int
    evaluations: tuple[TargetEvaluation, ...]  # All evaluated targets
    chosen_target_id: str | None
    chosen_value: float  # Discounted value of chosen target (0 if none)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "position": list(self.position),
            "visible_agents": self.visible_agents,
            "evaluations": [e.to_dict() for e in self.evaluations],
            "chosen_target_id": self.chosen_target_id,
            "chosen_value": self.chosen_value,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SearchDecision":
        return cls(
            agent_id=d["agent_id"],
            position=tuple(d["position"]),
            visible_agents=d["visible_agents"],
            evaluations=tuple(
                TargetEvaluation.from_dict(e) for e in d["evaluations"]
            ),
            chosen_target_id=d["chosen_target_id"],
            chosen_value=d["chosen_value"],
        )


@dataclass(frozen=True)
class MovementEvent:
    """Record of agent movement during a tick."""

    agent_id: str
    from_pos: tuple[int, int]
    to_pos: tuple[int, int]
    target_id: str | None  # Target agent being pursued (if any)
    reason: str  # "toward_target", "no_target", "at_target", "stayed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "from_pos": list(self.from_pos),
            "to_pos": list(self.to_pos),
            "target_id": self.target_id,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "MovementEvent":
        return cls(
            agent_id=d["agent_id"],
            from_pos=tuple(d["from_pos"]),
            to_pos=tuple(d["to_pos"]),
            target_id=d["target_id"],
            reason=d["reason"],
        )


@dataclass(frozen=True)
class TradeEvent:
    """Complete record of a trade between two agents."""

    agent1_id: str
    agent2_id: str
    proposer_id: str  # Critical for Rubinstein comparison
    pre_endowments: tuple[
        tuple[float, float], tuple[float, float]
    ]  # (agent1, agent2)
    post_allocations: tuple[
        tuple[float, float], tuple[float, float]
    ]  # (agent1, agent2)
    utilities: tuple[float, float]  # Post-trade utilities
    gains: tuple[float, float]  # Surplus for each agent
    trade_occurred: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent1_id": self.agent1_id,
            "agent2_id": self.agent2_id,
            "proposer_id": self.proposer_id,
            "pre_endowments": [list(e) for e in self.pre_endowments],
            "post_allocations": [list(a) for a in self.post_allocations],
            "utilities": list(self.utilities),
            "gains": list(self.gains),
            "trade_occurred": self.trade_occurred,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TradeEvent":
        return cls(
            agent1_id=d["agent1_id"],
            agent2_id=d["agent2_id"],
            proposer_id=d["proposer_id"],
            pre_endowments=tuple(tuple(e) for e in d["pre_endowments"]),
            post_allocations=tuple(tuple(a) for a in d["post_allocations"]),
            utilities=tuple(d["utilities"]),
            gains=tuple(d["gains"]),
            trade_occurred=d["trade_occurred"],
        )


@dataclass(frozen=True)
class TickRecord:
    """Complete record of a single simulation tick."""

    tick: int
    agent_snapshots: tuple[AgentSnapshot, ...]
    search_decisions: tuple[SearchDecision, ...]
    movements: tuple[MovementEvent, ...]
    trades: tuple[TradeEvent, ...]
    total_welfare: float
    cumulative_trades: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "agent_snapshots": [s.to_dict() for s in self.agent_snapshots],
            "search_decisions": [d.to_dict() for d in self.search_decisions],
            "movements": [m.to_dict() for m in self.movements],
            "trades": [t.to_dict() for t in self.trades],
            "total_welfare": self.total_welfare,
            "cumulative_trades": self.cumulative_trades,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TickRecord":
        return cls(
            tick=d["tick"],
            agent_snapshots=tuple(
                AgentSnapshot.from_dict(s) for s in d["agent_snapshots"]
            ),
            search_decisions=tuple(
                SearchDecision.from_dict(sd) for sd in d["search_decisions"]
            ),
            movements=tuple(MovementEvent.from_dict(m) for m in d["movements"]),
            trades=tuple(TradeEvent.from_dict(t) for t in d["trades"]),
            total_welfare=d["total_welfare"],
            cumulative_trades=d["cumulative_trades"],
        )


@dataclass(frozen=True)
class RunSummary:
    """Summary statistics for a completed simulation run."""

    total_ticks: int
    final_welfare: float
    total_trades: int
    welfare_gain: float  # Final welfare - initial welfare

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_ticks": self.total_ticks,
            "final_welfare": self.final_welfare,
            "total_trades": self.total_trades,
            "welfare_gain": self.welfare_gain,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RunSummary":
        return cls(
            total_ticks=d["total_ticks"],
            final_welfare=d["final_welfare"],
            total_trades=d["total_trades"],
            welfare_gain=d["welfare_gain"],
        )
