"""
Simulation engine for grid-based search and exchange.

The simulation runs in discrete ticks with four phases:
1. EVALUATE - Observe visible agents, compute surplus rankings
2. DECIDE   - Form commitments (committed mode) or select targets (opportunistic)
3. MOVE     - Move toward committed partner or selected target
4. EXCHANGE - Execute bargaining (commitment-gated or any co-located)

Reference: CLAUDE.md, DESIGN_matching_protocol.md
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Callable, TYPE_CHECKING
import random as random_module
from random import Random

from microecon.agent import Agent, create_agent
from microecon.grid import Grid, Position
from microecon.information import InformationEnvironment, FullInformation
from microecon.bargaining import (
    BargainingOutcome,
    BargainingProtocol,
    NashBargainingProtocol,
)
from microecon.search import (
    compute_move_target,
    should_trade,
    evaluate_targets,
    evaluate_targets_detailed,
    TargetEvaluationResult,
)
from microecon.matching import (
    MatchingProtocol,
    OpportunisticMatchingProtocol,
    CommitmentState,
)

if TYPE_CHECKING:
    from microecon.logging import SimulationLogger


@dataclass
class TradeEvent:
    """Record of a trade that occurred."""
    tick: int
    agent1_id: str
    agent2_id: str
    outcome: BargainingOutcome


@dataclass
class SimulationState:
    """
    Snapshot of simulation state at a point in time.

    Attributes:
        tick: Current tick number
        agents: List of agents
        positions: Map of agent ID to position
        trades: Trades that have occurred
    """
    tick: int
    agent_utilities: dict[str, float]
    agent_positions: dict[str, Position]
    total_trades: int


@dataclass
class Simulation:
    """
    Main simulation engine.

    Coordinates agent search, movement, and exchange on the grid.

    Attributes:
        grid: The spatial grid
        agents: All agents in the simulation
        info_env: Information environment
        bargaining_protocol: Protocol for bilateral bargaining (Nash, Rubinstein, etc.)
        matching_protocol: Protocol for forming trading pairs (Opportunistic, StableRoommates)
        tick: Current tick number
        trades: History of trades
        commitments: Tracks committed pairs (for committed matching protocols)
        logger: Optional SimulationLogger for capturing detailed state
    """
    grid: Grid
    info_env: InformationEnvironment = field(default_factory=FullInformation)
    bargaining_protocol: BargainingProtocol = field(default_factory=NashBargainingProtocol)
    matching_protocol: MatchingProtocol = field(default_factory=OpportunisticMatchingProtocol)
    agents: list[Agent] = field(default_factory=list)
    tick: int = 0
    trades: list[TradeEvent] = field(default_factory=list)
    commitments: CommitmentState = field(default_factory=CommitmentState)
    _agents_by_id: dict[str, Agent] = field(default_factory=dict, repr=False)
    logger: Optional["SimulationLogger"] = field(default=None, repr=False)
    _rng: Random = field(default_factory=Random, repr=False)

    def add_agent(self, agent: Agent, position: Position) -> None:
        """Add an agent to the simulation at the given position."""
        self.agents.append(agent)
        self._agents_by_id[agent.id] = agent
        self.grid.place_agent(agent, position)

    def add_agent_random(self, agent: Agent) -> Position:
        """Add an agent at a random position on the grid."""
        pos = Position(
            self._rng.randint(0, self.grid.size - 1),
            self._rng.randint(0, self.grid.size - 1),
        )
        self.add_agent(agent, pos)
        return pos

    def remove_agent(self, agent: Agent) -> None:
        """Remove an agent from the simulation."""
        self.agents.remove(agent)
        del self._agents_by_id[agent.id]
        self.grid.remove_agent(agent)

    def step(self) -> list[TradeEvent]:
        """
        Execute one simulation tick with four phases.

        Phases:
        1. EVALUATE - Observe visible agents, compute surplus rankings
        2. DECIDE   - Form commitments (committed mode) or select targets (opportunistic)
        3. MOVE     - Move toward committed partner or selected target
        4. EXCHANGE - Execute bargaining (commitment-gated or any co-located)

        Returns:
            List of trades that occurred this tick
        """
        self.tick += 1
        tick_trades: list[TradeEvent] = []

        # For logging: collect search decisions and movement events
        search_decisions_data: list[tuple[str, Position, int, list[TargetEvaluationResult], Optional[str], float]] = []
        movement_events_data: list[tuple[str, Position, Position, Optional[str], str]] = []
        # Track commitment events for logging
        commitments_formed_data: list[tuple[str, str]] = []
        commitments_broken_data: list[tuple[str, str, str]] = []  # (agent_a, agent_b, reason)

        # Store old positions for crossing detection
        old_positions: dict[str, Position] = {
            agent.id: self.grid.get_position(agent)
            for agent in self.agents
            if self.grid.get_position(agent) is not None
        }

        # =====================================================================
        # PRE-TICK: Commitment maintenance (break stale commitments)
        # =====================================================================
        if self.matching_protocol.requires_commitment:
            broken_pairs = self._maintain_commitments()
            for agent_a_id, agent_b_id in broken_pairs:
                commitments_broken_data.append((agent_a_id, agent_b_id, "left_perception"))

        # =====================================================================
        # PHASE 1: EVALUATE - Observe visible agents, compute surplus rankings
        # =====================================================================
        # Build visibility map: agent_id -> set of visible agent_ids
        visibility: dict[str, set[str]] = {}
        # Store evaluation results for Decide phase and logging
        agent_evaluations: dict[str, tuple[Optional[str], Optional[Position], float, int, list[TargetEvaluationResult]]] = {}

        for agent in self.agents:
            agent_pos = self.grid.get_position(agent)
            if agent_pos is None:
                visibility[agent.id] = set()
                agent_evaluations[agent.id] = (None, None, 0.0, 0, [])
                continue

            # Use detailed evaluation to get visibility info and rankings
            result, evaluations = evaluate_targets_detailed(
                agent, self.grid, self.info_env, self._agents_by_id,
                self.bargaining_protocol
            )

            # Build visibility set from evaluations
            visibility[agent.id] = {e.target_id for e in evaluations}

            # Store for Decide phase
            agent_evaluations[agent.id] = (
                result.best_target_id,
                result.best_target_position,
                result.discounted_value,
                result.visible_agents,
                evaluations,
            )

            # Record for logging
            if self.logger is not None:
                search_decisions_data.append((
                    agent.id,
                    agent_pos,
                    result.visible_agents,
                    evaluations,
                    result.best_target_id,
                    result.discounted_value,
                ))

        # =====================================================================
        # PHASE 2: DECIDE - Form commitments or select targets
        # =====================================================================
        move_targets: dict[str, Optional[Position]] = {}
        move_target_ids: dict[str, Optional[str]] = {}

        if self.matching_protocol.requires_commitment:
            # Committed mode: run matching for uncommitted agents
            uncommitted_ids = self.commitments.get_uncommitted_agents(
                {a.id for a in self.agents}
            )
            uncommitted_agents = [
                self._agents_by_id[aid] for aid in uncommitted_ids
                if aid in self._agents_by_id
            ]

            # Define surplus function for matching with protocol and distance discounting
            def surplus_fn(a: Agent, b: Agent) -> float:
                # Get expected surplus using the bargaining protocol
                base_surplus = self.bargaining_protocol.compute_expected_surplus(a, b)
                if base_surplus <= 0:
                    return 0.0

                # Apply distance discounting
                pos_a = self.grid.get_position(a)
                pos_b = self.grid.get_position(b)
                if pos_a is None or pos_b is None:
                    return 0.0

                ticks_to_reach = pos_a.chebyshev_distance_to(pos_b)
                return base_surplus * (a.discount_factor ** ticks_to_reach)

            # Compute new matches
            new_pairs = self.matching_protocol.compute_matches(
                uncommitted_agents, visibility, surplus_fn
            )

            # Form new commitments
            for agent_a_id, agent_b_id in new_pairs:
                self.commitments.form_commitment(agent_a_id, agent_b_id)
                commitments_formed_data.append((agent_a_id, agent_b_id))

            # Set movement targets based on commitment status
            for agent in self.agents:
                partner_id = self.commitments.get_partner(agent.id)
                if partner_id is not None:
                    # Committed: move toward partner
                    partner = self._agents_by_id.get(partner_id)
                    if partner is not None:
                        partner_pos = self.grid.get_position(partner)
                        move_targets[agent.id] = partner_pos
                        move_target_ids[agent.id] = partner_id
                    else:
                        # Partner not found, use fallback
                        best_id, best_pos, _, _, _ = agent_evaluations.get(agent.id, (None, None, 0, 0, []))
                        move_targets[agent.id] = best_pos
                        move_target_ids[agent.id] = best_id
                else:
                    # Uncommitted/unmatched: use fallback (best surplus target)
                    best_id, best_pos, _, _, _ = agent_evaluations.get(agent.id, (None, None, 0, 0, []))
                    move_targets[agent.id] = best_pos
                    move_target_ids[agent.id] = best_id
        else:
            # Opportunistic mode: select best surplus target
            for agent in self.agents:
                best_id, best_pos, _, _, _ = agent_evaluations.get(agent.id, (None, None, 0, 0, []))
                move_targets[agent.id] = best_pos
                move_target_ids[agent.id] = best_id

        # =====================================================================
        # PHASE 3: MOVE - Move toward partner or target
        # =====================================================================
        for agent in self.agents:
            target = move_targets.get(agent.id)
            if target is not None:
                self.grid.move_toward(agent, target, steps=agent.movement_budget)

        # Detect crossing paths - if two agents swapped positions or
        # crossed through each other, place them at the same position (meeting)
        new_positions: dict[str, Position] = {
            a.id: self.grid.get_position(a) for a in self.agents
        }
        for i, agent1 in enumerate(self.agents):
            for agent2 in self.agents[i+1:]:
                old1, old2 = old_positions.get(agent1.id), old_positions.get(agent2.id)
                new1, new2 = new_positions.get(agent1.id), new_positions.get(agent2.id)

                if old1 is None or old2 is None or new1 is None or new2 is None:
                    continue

                # Check if they crossed paths (swapped positions or crossed through)
                crossed = (old1 == new2 and old2 == new1)
                # Also check if they're now adjacent but were moving toward each other
                adjacent = new1.chebyshev_distance_to(new2) == 1
                moving_toward = (
                    move_targets.get(agent1.id) == old2 and
                    move_targets.get(agent2.id) == old1
                )

                if crossed or (adjacent and moving_toward):
                    # Place both at the midpoint (agent1's new position)
                    self.grid.move_agent(agent2, new1)
                    new_positions[agent2.id] = new1

        # Record movement events for logging
        if self.logger is not None:
            for agent in self.agents:
                old_pos = old_positions.get(agent.id)
                new_pos = new_positions.get(agent.id)
                target_id = move_target_ids.get(agent.id)

                if old_pos is None or new_pos is None:
                    continue

                if old_pos == new_pos:
                    reason = "at_target" if target_id is not None else "no_target"
                elif target_id is not None:
                    reason = "toward_target"
                else:
                    reason = "stayed"

                movement_events_data.append((
                    agent.id, old_pos, new_pos, target_id, reason
                ))

        # =====================================================================
        # PHASE 4: EXCHANGE - Execute bargaining
        # =====================================================================
        traded_this_tick: set[str] = set()
        trade_events_data: list[tuple] = []

        for agent in self.agents:
            if agent.id in traded_this_tick:
                continue

            # Find other agents at same position
            others = self.grid.agents_at_same_position(agent)
            others = {oid for oid in others if oid not in traded_this_tick}

            if not others:
                continue

            # Trade with first available partner (sorted by ID for determinism)
            for other_id in sorted(others):
                other = self._agents_by_id.get(other_id)
                if other is None:
                    continue

                # Check if trade is allowed under current matching protocol
                if self.matching_protocol.requires_commitment:
                    # Committed mode: only committed pairs can trade
                    if self.commitments.get_partner(agent.id) != other_id:
                        continue  # Not committed to this agent

                if should_trade(agent, other, self.info_env, self.bargaining_protocol):
                    # Capture pre-trade endowments for logging
                    pre_endowment1 = (agent.endowment.x, agent.endowment.y)
                    pre_endowment2 = (other.endowment.x, other.endowment.y)

                    # Random proposer assignment eliminates arbitrary bias
                    # (With BRW Rubinstein, proposer identity doesn't affect outcomes anyway)
                    proposer = self._rng.choice([agent, other])
                    outcome = self.bargaining_protocol.execute(agent, other, proposer=proposer)
                    if outcome.trade_occurred:
                        event = TradeEvent(
                            tick=self.tick,
                            agent1_id=agent.id,
                            agent2_id=other.id,
                            outcome=outcome,
                        )
                        tick_trades.append(event)
                        self.trades.append(event)
                        traded_this_tick.add(agent.id)
                        traded_this_tick.add(other.id)

                        # Break commitment after successful trade (committed mode)
                        if self.matching_protocol.requires_commitment:
                            self.commitments.break_commitment(agent.id, other.id)
                            commitments_broken_data.append((agent.id, other.id, "trade_completed"))

                        # Record for logging
                        if self.logger is not None:
                            trade_events_data.append((
                                agent.id,
                                other.id,
                                proposer.id,  # proposer_id (randomly assigned)
                                (pre_endowment1, pre_endowment2),
                                ((outcome.allocation_1.x, outcome.allocation_1.y),
                                 (outcome.allocation_2.x, outcome.allocation_2.y)),
                                (outcome.utility_1, outcome.utility_2),
                                (outcome.gains_1, outcome.gains_2),
                                outcome.trade_occurred,
                            ))

                        break  # Agent can only trade once per tick

        # Log the complete tick record
        if self.logger is not None:
            self._log_tick(
                search_decisions_data,
                movement_events_data,
                trade_events_data,
                commitments_formed_data,
                commitments_broken_data,
            )

        return tick_trades

    def _maintain_commitments(self) -> list[tuple[str, str]]:
        """
        Check and break stale commitments.

        A commitment is broken if the partner is no longer within perception radius.
        Called at the start of each tick (before Evaluate phase).

        Returns:
            List of (agent_a, agent_b) pairs that were broken due to leaving perception.
        """
        to_break: list[tuple[str, str]] = []

        for agent_a_id, agent_b_id in self.commitments.get_all_committed_pairs():
            agent_a = self._agents_by_id.get(agent_a_id)
            agent_b = self._agents_by_id.get(agent_b_id)

            if agent_a is None or agent_b is None:
                to_break.append((agent_a_id, agent_b_id))
                continue

            pos_a = self.grid.get_position(agent_a)
            pos_b = self.grid.get_position(agent_b)

            if pos_a is None or pos_b is None:
                to_break.append((agent_a_id, agent_b_id))
                continue

            # Check if partner is still within perception radius (using Chebyshev)
            distance = self.grid.chebyshev_distance(pos_a, pos_b)
            if distance > agent_a.perception_radius or distance > agent_b.perception_radius:
                to_break.append((agent_a_id, agent_b_id))

        for agent_a_id, agent_b_id in to_break:
            self.commitments.break_commitment(agent_a_id, agent_b_id)

        return to_break

    def _log_tick(
        self,
        search_decisions_data: list,
        movement_events_data: list,
        trade_events_data: list,
        commitments_formed_data: list[tuple[str, str]],
        commitments_broken_data: list[tuple[str, str, str]],
    ) -> None:
        """Create and log a complete tick record."""
        from microecon.logging import (
            create_agent_snapshot,
            create_commitment_broken_event,
            create_commitment_formed_event,
            create_search_decision,
            create_target_evaluation,
            create_movement_event,
            create_trade_event,
            create_tick_record,
            TargetEvaluation,
        )

        # Create agent snapshots
        agent_snapshots = []
        for agent in self.agents:
            pos = self.grid.get_position(agent)
            if pos is not None:
                agent_snapshots.append(create_agent_snapshot(
                    agent_id=agent.id,
                    position=(pos.row, pos.col),
                    endowment=(agent.endowment.x, agent.endowment.y),
                    alpha=agent.preferences.alpha,
                    utility=agent.utility(),
                ))

        # Create search decisions
        search_decisions = []
        for agent_id, pos, visible, evals, chosen_id, chosen_val in search_decisions_data:
            evaluations = [
                create_target_evaluation(
                    target_id=e.target_id,
                    target_position=(e.target_position.row, e.target_position.col),
                    distance=e.distance,
                    ticks_to_reach=e.ticks_to_reach,
                    expected_surplus=e.expected_surplus,
                    discounted_value=e.discounted_value,
                )
                for e in evals
            ]
            search_decisions.append(create_search_decision(
                agent_id=agent_id,
                position=(pos.row, pos.col),
                visible_agents=visible,
                evaluations=evaluations,
                chosen_target_id=chosen_id,
                chosen_value=chosen_val,
            ))

        # Create movement events
        movements = [
            create_movement_event(
                agent_id=agent_id,
                from_pos=(from_pos.row, from_pos.col),
                to_pos=(to_pos.row, to_pos.col),
                target_id=target_id,
                reason=reason,
            )
            for agent_id, from_pos, to_pos, target_id, reason in movement_events_data
        ]

        # Create trade events
        trades = [
            create_trade_event(
                agent1_id=a1,
                agent2_id=a2,
                proposer_id=proposer,
                pre_endowments=pre,
                post_allocations=post,
                utilities=utils,
                gains=gains,
                trade_occurred=occurred,
            )
            for a1, a2, proposer, pre, post, utils, gains, occurred in trade_events_data
        ]

        # Create commitment events
        commitments_formed = [
            create_commitment_formed_event(agent_a=a, agent_b=b)
            for a, b in commitments_formed_data
        ]
        commitments_broken = [
            create_commitment_broken_event(agent_a=a, agent_b=b, reason=reason)
            for a, b, reason in commitments_broken_data
        ]

        # Create and log the tick record
        tick_record = create_tick_record(
            tick=self.tick,
            agent_snapshots=agent_snapshots,
            search_decisions=search_decisions,
            movements=movements,
            trades=trades,
            total_welfare=self.total_welfare(),
            cumulative_trades=len(self.trades),
            commitments_formed=commitments_formed,
            commitments_broken=commitments_broken,
        )

        self.logger.log_tick(tick_record)

    def run(self, ticks: int, callback: Optional[Callable[[int, list[TradeEvent]], None]] = None) -> None:
        """
        Run the simulation for a number of ticks.

        Args:
            ticks: Number of ticks to run
            callback: Optional function called after each tick with (tick_number, trades)
        """
        for _ in range(ticks):
            tick_trades = self.step()
            if callback:
                callback(self.tick, tick_trades)

    def get_state(self) -> SimulationState:
        """Get a snapshot of current simulation state."""
        return SimulationState(
            tick=self.tick,
            agent_utilities={a.id: a.utility() for a in self.agents},
            agent_positions={
                a.id: pos
                for a in self.agents
                if (pos := self.grid.get_position(a)) is not None
            },
            total_trades=len(self.trades),
        )

    def total_welfare(self) -> float:
        """Compute sum of all agent utilities."""
        return sum(agent.utility() for agent in self.agents)

    def welfare_gains(self) -> float:
        """Compute total gains from trade (sum of all trade surpluses)."""
        return sum(
            trade.outcome.gains_1 + trade.outcome.gains_2
            for trade in self.trades
        )


def create_simple_economy(
    n_agents: int,
    grid_size: int = 10,
    perception_radius: float = 7.0,
    discount_factor: float = 0.95,
    seed: Optional[int] = None,
    bargaining_protocol: Optional[BargainingProtocol] = None,
    matching_protocol: Optional[MatchingProtocol] = None,
) -> Simulation:
    """
    Create a simple economy with heterogeneous agents.

    Creates agents with:
    - Varied preference parameters (alpha uniformly distributed)
    - Complementary endowments (half have more x, half have more y)

    This setup guarantees gains from trade between agents with
    different preferences.

    Args:
        n_agents: Number of agents
        grid_size: Size of the grid
        perception_radius: How far agents can see
        discount_factor: Time preference
        seed: Random seed for reproducibility
        bargaining_protocol: Protocol for bilateral bargaining (default: Nash)
        matching_protocol: Protocol for forming trading pairs (default: Opportunistic)

    Returns:
        Configured Simulation ready to run
    """
    # Create RNG instance - seed if provided, otherwise use system entropy
    rng = Random(seed) if seed is not None else Random()

    sim = Simulation(
        grid=Grid(grid_size),
        info_env=FullInformation(),
        bargaining_protocol=bargaining_protocol or NashBargainingProtocol(),
        matching_protocol=matching_protocol or OpportunisticMatchingProtocol(),
        _rng=rng,
    )

    for i in range(n_agents):
        # Vary preference parameter
        alpha = 0.2 + 0.6 * (i / max(1, n_agents - 1))

        # Complementary endowments: some have more x, some have more y
        if i % 2 == 0:
            endowment_x, endowment_y = 10.0, 2.0
        else:
            endowment_x, endowment_y = 2.0, 10.0

        # Use deterministic agent IDs for reproducibility
        agent_id = f"agent_{i:03d}"

        agent = create_agent(
            alpha=alpha,
            endowment_x=endowment_x,
            endowment_y=endowment_y,
            perception_radius=perception_radius,
            discount_factor=discount_factor,
            agent_id=agent_id,
        )

        sim.add_agent_random(agent)

    return sim
