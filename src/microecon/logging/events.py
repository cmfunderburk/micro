"""Event dataclasses for simulation logging.

These frozen dataclasses capture the complete state of each simulation tick,
including search evaluations, movement decisions, and trade outcomes.
All fields use primitive types (int, float, str, tuple) for JSON serialization.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SimulationConfig:
    """Configuration snapshot for a simulation run.

    Captures all institutional settings needed to reproduce and compare runs:
    - Bargaining protocol (Nash, Rubinstein)
    - Matching protocol (opportunistic, stable_roommates)
    - Information environment (full, noisy)
    """

    n_agents: int
    grid_size: int
    seed: int
    protocol_name: str  # "nash" or "rubinstein"
    protocol_params: dict[str, Any] = field(default_factory=dict)
    perception_radius: float = 3.0
    discount_factor: float = 0.95
    movement_budget: int = 1
    # Institutional metadata (LA-1)
    matching_protocol_name: str = "opportunistic"
    info_env_name: str = "full_information"
    info_env_params: dict[str, Any] = field(default_factory=dict)

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
            "matching_protocol_name": self.matching_protocol_name,
            "info_env_name": self.info_env_name,
            "info_env_params": self.info_env_params,
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
            matching_protocol_name=d.get("matching_protocol_name", "opportunistic"),
            info_env_name=d.get("info_env_name", "full_information"),
            info_env_params=d.get("info_env_params", {}),
        )


@dataclass(frozen=True)
class AgentSnapshot:
    """Complete agent state at a point in time."""

    agent_id: str
    position: tuple[int, int]  # (row, col)
    endowment: tuple[float, float]  # (x, y)
    alpha: float  # preference parameter
    utility: float
    # Belief state (optional for backward compatibility)
    has_beliefs: bool = False
    n_trades_in_memory: int = 0
    n_type_beliefs: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "position": list(self.position),
            "endowment": list(self.endowment),
            "alpha": self.alpha,
            "utility": self.utility,
            "has_beliefs": self.has_beliefs,
            "n_trades_in_memory": self.n_trades_in_memory,
            "n_type_beliefs": self.n_type_beliefs,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "AgentSnapshot":
        return cls(
            agent_id=d["agent_id"],
            position=tuple(d["position"]),
            endowment=tuple(d["endowment"]),
            alpha=d["alpha"],
            utility=d["utility"],
            has_beliefs=d.get("has_beliefs", False),
            n_trades_in_memory=d.get("n_trades_in_memory", 0),
            n_type_beliefs=d.get("n_type_beliefs", 0),
        )


@dataclass(frozen=True)
class TargetEvaluation:
    """Evaluation of a potential trade partner during search."""

    target_id: str
    target_position: tuple[int, int]
    distance: float  # Chebyshev distance (same as ticks_to_reach, perception is square)
    ticks_to_reach: int  # Chebyshev distance (movement ticks required)
    expected_surplus: float  # Nash bargaining surplus
    discounted_value: float  # surplus * (delta ^ ticks_to_reach)
    observed_alpha: float  # Alpha as perceived by observer (enables V-1 visualization)
    # Belief tracking (optional for backward compatibility)
    used_belief: bool = False  # Whether belief was used instead of observation
    believed_alpha: float | None = None  # Alpha from belief (if used)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "target_position": list(self.target_position),
            "distance": self.distance,
            "ticks_to_reach": self.ticks_to_reach,
            "expected_surplus": self.expected_surplus,
            "discounted_value": self.discounted_value,
            "observed_alpha": self.observed_alpha,
            "used_belief": self.used_belief,
            "believed_alpha": self.believed_alpha,
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
            observed_alpha=d.get("observed_alpha", d.get("alpha", 0.5)),  # fallback for old logs
            used_belief=d.get("used_belief", False),
            believed_alpha=d.get("believed_alpha"),
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
class CommitmentFormedEvent:
    """Record of a commitment forming between two agents."""

    agent_a: str
    agent_b: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_a": self.agent_a,
            "agent_b": self.agent_b,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CommitmentFormedEvent":
        return cls(
            agent_a=d["agent_a"],
            agent_b=d["agent_b"],
        )


@dataclass(frozen=True)
class CommitmentBrokenEvent:
    """Record of a commitment breaking."""

    agent_a: str
    agent_b: str
    reason: str  # "trade_completed" or "left_perception"

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_a": self.agent_a,
            "agent_b": self.agent_b,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CommitmentBrokenEvent":
        return cls(
            agent_a=d["agent_a"],
            agent_b=d["agent_b"],
            reason=d["reason"],
        )


@dataclass(frozen=True)
class TypeBeliefSnapshot:
    """Snapshot of an agent's belief about another agent's type."""

    target_agent_id: str
    believed_alpha: float
    confidence: float
    n_interactions: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_agent_id": self.target_agent_id,
            "believed_alpha": self.believed_alpha,
            "confidence": self.confidence,
            "n_interactions": self.n_interactions,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TypeBeliefSnapshot":
        return cls(
            target_agent_id=d["target_agent_id"],
            believed_alpha=d["believed_alpha"],
            confidence=d["confidence"],
            n_interactions=d["n_interactions"],
        )


@dataclass(frozen=True)
class PriceBeliefSnapshot:
    """Snapshot of an agent's price belief."""

    mean: float
    variance: float
    n_observations: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "mean": self.mean,
            "variance": self.variance,
            "n_observations": self.n_observations,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PriceBeliefSnapshot":
        return cls(
            mean=d["mean"],
            variance=d["variance"],
            n_observations=d["n_observations"],
        )


@dataclass(frozen=True)
class BeliefSnapshot:
    """Complete snapshot of an agent's belief state at a point in time.

    Enables belief trajectory analysis: tracking how beliefs evolve
    across ticks as agents interact and learn.
    """

    agent_id: str
    type_beliefs: tuple[TypeBeliefSnapshot, ...]  # Beliefs about other agents
    price_belief: PriceBeliefSnapshot
    n_trades_in_memory: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "type_beliefs": [tb.to_dict() for tb in self.type_beliefs],
            "price_belief": self.price_belief.to_dict(),
            "n_trades_in_memory": self.n_trades_in_memory,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "BeliefSnapshot":
        return cls(
            agent_id=d["agent_id"],
            type_beliefs=tuple(
                TypeBeliefSnapshot.from_dict(tb) for tb in d["type_beliefs"]
            ),
            price_belief=PriceBeliefSnapshot.from_dict(d["price_belief"]),
            n_trades_in_memory=d["n_trades_in_memory"],
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
    # Commitment events (for committed matching protocols)
    commitments_formed: tuple[CommitmentFormedEvent, ...] = ()
    commitments_broken: tuple[CommitmentBrokenEvent, ...] = ()
    # Belief snapshots (for belief-enabled agents)
    belief_snapshots: tuple[BeliefSnapshot, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "agent_snapshots": [s.to_dict() for s in self.agent_snapshots],
            "search_decisions": [d.to_dict() for d in self.search_decisions],
            "movements": [m.to_dict() for m in self.movements],
            "trades": [t.to_dict() for t in self.trades],
            "total_welfare": self.total_welfare,
            "cumulative_trades": self.cumulative_trades,
            "commitments_formed": [c.to_dict() for c in self.commitments_formed],
            "commitments_broken": [c.to_dict() for c in self.commitments_broken],
            "belief_snapshots": [b.to_dict() for b in self.belief_snapshots],
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
            commitments_formed=tuple(
                CommitmentFormedEvent.from_dict(c) for c in d.get("commitments_formed", [])
            ),
            commitments_broken=tuple(
                CommitmentBrokenEvent.from_dict(c) for c in d.get("commitments_broken", [])
            ),
            belief_snapshots=tuple(
                BeliefSnapshot.from_dict(b) for b in d.get("belief_snapshots", [])
            ),
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
