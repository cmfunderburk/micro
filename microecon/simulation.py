"""
Simulation engine for grid-based search and exchange.

The simulation runs in discrete ticks with three phases:
1. PERCEIVE - All agents observe frozen state (simultaneous snapshot)
2. DECIDE   - All agents select ONE action from available_actions()
3. EXECUTE  - Conflict resolution, execute actions, state transitions

Reference: CLAUDE.md, ADR-001-TICK-MODEL.md, ADR-002-INTERACTION-STATE.md
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Callable, TYPE_CHECKING
from random import Random

from microecon.agent import Agent, AgentInteractionState, InteractionState, create_agent
from microecon.bundle import Bundle
from microecon.grid import Grid, Position
from microecon.information import InformationEnvironment, FullInformation
from microecon.beliefs import record_trade_observation
from microecon.logging.events import TradeEvent
from microecon.bargaining import (
    BargainingOutcome,
    BargainingProtocol,
    NashBargainingProtocol,
)
from microecon.search import (
    evaluate_targets_detailed,
    TargetEvaluationResult,
)
from microecon.actions import (
    Action,
    ActionContext,
    ActionType,
    MoveAction,
    ProposeAction,
    AcceptAction,
    RejectAction,
    WaitAction,
)
from microecon.decisions import (
    DecisionProcedure,
    DecisionContext,
    RationalDecisionProcedure,
)
from microecon.matching import (
    BilateralProposalMatching,
    MatchingProtocol,
    MatchResult,
)

if TYPE_CHECKING:
    from microecon.logging import SimulationLogger


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

    Coordinates agent search, movement, and exchange on the grid using
    the 3-phase tick model (Perceive-Decide-Execute).

    Attributes:
        grid: The spatial grid
        agents: All agents in the simulation
        info_env: Information environment
        bargaining_protocol: Protocol for bilateral bargaining (Nash, Rubinstein, etc.)
        decision_procedure: Procedure for agent action selection
        tick: Current tick number
        trades: History of trades
        logger: Optional SimulationLogger for capturing detailed state
    """
    grid: Grid
    info_env: InformationEnvironment = field(default_factory=FullInformation)
    bargaining_protocol: BargainingProtocol = field(default_factory=NashBargainingProtocol)
    decision_procedure: DecisionProcedure = field(default_factory=RationalDecisionProcedure)
    matching_protocol: MatchingProtocol = field(default_factory=BilateralProposalMatching)
    agents: list[Agent] = field(default_factory=list)
    tick: int = 0
    trades: list[TradeEvent] = field(default_factory=list)
    _agents_by_id: dict[str, Agent] = field(default_factory=dict, repr=False)
    logger: Optional["SimulationLogger"] = field(default=None, repr=False)
    _rng: Random = field(default_factory=Random, repr=False)

    # Track pending proposals: target_id -> proposer_id
    _pending_proposals: dict[str, str] = field(default_factory=dict, repr=False)
    # Track negotiating pairs: (agent_a_id, agent_b_id) -> exchange_id
    _negotiating_pairs: dict[tuple[str, str], str] = field(default_factory=dict, repr=False)

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
        Execute one simulation tick with three phases (ADR-001).

        Phases:
        1. PERCEIVE - All agents observe frozen state (simultaneous snapshot)
        2. DECIDE   - All agents select ONE action from available_actions()
        3. EXECUTE  - Conflict resolution, execute actions, state transitions

        Returns:
            List of trades that occurred this tick
        """
        self.tick += 1
        tick_trades: list[TradeEvent] = []

        # For logging: collect search decisions and movement events
        search_decisions_data: list[tuple[str, Position, int, list[TargetEvaluationResult], Optional[str], float]] = []
        movement_events_data: list[tuple[str, Position, Position, Optional[str], str]] = []

        # Store old positions for movement tracking
        old_positions: dict[str, Position] = {
            agent.id: self.grid.get_position(agent)
            for agent in self.agents
            if self.grid.get_position(agent) is not None
        }

        # =====================================================================
        # PRE-TICK: Tick cooldowns and expire stale proposals
        # =====================================================================
        self._pre_tick_maintenance()

        # =====================================================================
        # PHASE 1: PERCEIVE - Build frozen state snapshot
        # =====================================================================
        # Build visibility map: agent_id -> dict of visible agents
        visible_agents_map: dict[str, dict[str, Agent]] = {}
        # Store evaluation results for logging
        agent_evaluations: dict[str, tuple[Optional[str], Optional[Position], float, int, list[TargetEvaluationResult]]] = {}

        for agent in self.agents:
            agent_pos = self.grid.get_position(agent)
            if agent_pos is None:
                visible_agents_map[agent.id] = {}
                agent_evaluations[agent.id] = (None, None, 0.0, 0, [])
                continue

            # Use detailed evaluation to get visibility info and rankings
            result, evaluations = evaluate_targets_detailed(
                agent, self.grid, self.info_env, self._agents_by_id,
                self.bargaining_protocol
            )

            # Build visible agents dict from evaluations
            visible_agents_map[agent.id] = {
                e.target_id: self._agents_by_id[e.target_id]
                for e in evaluations
                if e.target_id in self._agents_by_id
            }

            # Store for logging
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

        # Build frozen ActionContext for precondition checking
        action_context = self._build_action_context()

        # =====================================================================
        # PHASE 2: DECIDE - Each agent selects one action
        # =====================================================================
        agent_actions: dict[str, Action] = {}

        for agent in self.agents:
            # Build decision context
            decision_context = DecisionContext(
                action_context=action_context,
                visible_agents=visible_agents_map.get(agent.id, {}),
                bargaining_protocol=self.bargaining_protocol,
                agent_positions={
                    aid: pos for aid, pos in
                    ((a.id, self.grid.get_position(a)) for a in self.agents)
                    if pos is not None
                },
            )

            # Let decision procedure choose action
            action = self.decision_procedure.choose(agent, decision_context)
            agent_actions[agent.id] = action

        # =====================================================================
        # PHASE 3: EXECUTE - Conflict resolution and action execution
        # =====================================================================
        tick_trades = self._execute_actions(agent_actions, old_positions, movement_events_data)

        # Record movement events for logging
        if self.logger is not None:
            new_positions = {
                a.id: self.grid.get_position(a) for a in self.agents
            }
            for agent in self.agents:
                old_pos = old_positions.get(agent.id)
                new_pos = new_positions.get(agent.id)
                action = agent_actions.get(agent.id)

                if old_pos is None or new_pos is None:
                    continue

                target_id = None
                if isinstance(action, MoveAction):
                    # Find which agent is at target position
                    for aid, apos in new_positions.items():
                        if apos == action.target_position and aid != agent.id:
                            target_id = aid
                            break

                if old_pos == new_pos:
                    reason = "stayed"
                else:
                    reason = "toward_target" if target_id else "moved"

                movement_events_data.append((
                    agent.id, old_pos, new_pos, target_id, reason
                ))

        # Log the complete tick record
        if self.logger is not None:
            self._log_tick(
                search_decisions_data,
                movement_events_data,
                tick_trades,
                [],  # No commitment events in new model
                [],  # No commitment events in new model
            )

        return tick_trades

    def _pre_tick_maintenance(self) -> None:
        """Pre-tick maintenance: tick cooldowns."""
        for agent in self.agents:
            agent.interaction_state.tick_cooldowns()

    def _build_action_context(self) -> ActionContext:
        """Build frozen ActionContext for precondition checking."""
        # Build agent positions
        agent_positions = {
            agent.id: pos
            for agent in self.agents
            if (pos := self.grid.get_position(agent)) is not None
        }

        # Build co-located agents map
        co_located: dict[str, set[str]] = {agent.id: set() for agent in self.agents}
        for agent in self.agents:
            others = self.grid.agents_at_same_position(agent)
            co_located[agent.id] = others

        # Build adjacent agents map (includes co-located + neighboring positions)
        adjacent: dict[str, set[str]] = {agent.id: set() for agent in self.agents}
        for agent in self.agents:
            others = self.grid.agents_adjacent_to(agent)
            adjacent[agent.id] = others

        # Build interaction state copies
        interaction_states = {
            agent.id: agent.interaction_state.copy()
            for agent in self.agents
        }

        return ActionContext(
            current_tick=self.tick,
            agent_positions=agent_positions,
            agent_interaction_states=interaction_states,
            co_located_agents=co_located,
            adjacent_agents=adjacent,
            pending_proposals=dict(self._pending_proposals),
        )

    def _execute_actions(
        self,
        agent_actions: dict[str, Action],
        old_positions: dict[str, Position],
        movement_events_data: list,
    ) -> list[TradeEvent]:
        """
        Execute all actions with conflict resolution.

        Handles:
        - Multiple proposals to same target
        - Mutual proposals
        - Movement
        - Accept/Reject responses
        - Negotiations completing in trades

        Returns:
            List of trades that occurred this tick
        """
        tick_trades: list[TradeEvent] = []

        # Separate actions by type
        move_actions: dict[str, MoveAction] = {}
        propose_actions: dict[str, ProposeAction] = {}

        for agent_id, action in agent_actions.items():
            if isinstance(action, MoveAction):
                move_actions[agent_id] = action
            elif isinstance(action, ProposeAction):
                propose_actions[agent_id] = action

        # Track agents that traded this tick
        traded_this_tick: set[str] = set()

        # =====================================================================
        # Step 1-2: Matching protocol resolves proposals
        # =====================================================================
        match_result = self.matching_protocol.resolve(
            propose_actions=propose_actions,
            agents=self._agents_by_id,
            positions={a.id: self.grid.get_position(a) for a in self.agents
                       if self.grid.get_position(a) is not None},
            decision_procedure=self.decision_procedure,
            bargaining_protocol=self.bargaining_protocol,
        )

        # Execute matched trades
        for trade_outcome in match_result.trades:
            proposer = self._agents_by_id.get(trade_outcome.proposer_id)
            target = self._agents_by_id.get(trade_outcome.target_id)
            if proposer is None or target is None:
                continue

            exchange_id = propose_actions.get(trade_outcome.proposer_id)
            if exchange_id is not None:
                exchange_id = exchange_id.exchange_id
            else:
                exchange_id = propose_actions.get(trade_outcome.target_id, ProposeAction(target_id="")).exchange_id

            proposer.interaction_state.enter_negotiating(trade_outcome.target_id, self.tick)
            target.interaction_state.enter_negotiating(trade_outcome.proposer_id, self.tick)

            trade_event = self._execute_trade(proposer, target, exchange_id)
            if trade_event:
                tick_trades.append(trade_event)

            proposer.interaction_state.enter_available()
            target.interaction_state.enter_available()

            traded_this_tick.add(trade_outcome.proposer_id)
            traded_this_tick.add(trade_outcome.target_id)

        # Apply cooldowns from rejections
        for rejection in match_result.rejections:
            proposer = self._agents_by_id.get(rejection.proposer_id)
            if proposer is not None:
                proposer.interaction_state.enter_available(
                    add_cooldown_for=rejection.target_id,
                    cooldown_duration=rejection.cooldown_ticks,
                )

        # Build set of all failed proposers for fallback execution
        rejected_proposers = {r.proposer_id for r in match_result.rejections}
        non_selected_proposers = set(match_result.non_selections)
        all_failed_proposers = rejected_proposers | non_selected_proposers

        # =====================================================================
        # Step 3: Execute fallback actions for failed proposals
        # =====================================================================
        for proposer_id in all_failed_proposers:
            proposer = self._agents_by_id.get(proposer_id)
            if proposer is None:
                continue

            action = propose_actions.get(proposer_id)
            if action is None:
                continue

            fallback = action.fallback
            if fallback is None:
                continue

            if isinstance(fallback, MoveAction):
                if proposer.interaction_state.is_available():
                    self.grid.move_toward(
                        proposer,
                        fallback.target_position,
                        steps=proposer.movement_budget
                    )

        # =====================================================================
        # Step 4: Execute movement actions
        # =====================================================================
        for agent_id, action in move_actions.items():
            if agent_id in traded_this_tick:
                continue
            if agent_id in all_failed_proposers:
                continue

            agent = self._agents_by_id.get(agent_id)
            if agent is None:
                continue
            if not agent.interaction_state.is_available():
                continue

            self.grid.move_toward(agent, action.target_position, steps=agent.movement_budget)

        return tick_trades

    def _execute_trade(
        self,
        agent1: Agent,
        agent2: Agent,
        exchange_id: str,
    ) -> Optional[TradeEvent]:
        """
        Execute a trade between two agents.

        Returns TradeEvent if trade occurred, None otherwise.
        """
        # Capture pre-trade holdings for logging
        pre_holdings1 = (agent1.holdings.x, agent1.holdings.y)
        pre_holdings2 = (agent2.holdings.x, agent2.holdings.y)

        # Let protocol select proposer
        proposer = self.bargaining_protocol.select_proposer(agent1, agent2, self._rng)
        outcome = self.bargaining_protocol.execute(agent1, agent2, proposer=proposer)

        if outcome.trade_occurred:
            event = TradeEvent(
                agent1_id=agent1.id,
                agent2_id=agent2.id,
                proposer_id=proposer.id,
                pre_holdings=(pre_holdings1, pre_holdings2),
                post_allocations=(
                    (outcome.allocation_1.x, outcome.allocation_1.y),
                    (outcome.allocation_2.x, outcome.allocation_2.y),
                ),
                utilities=(outcome.utility_1, outcome.utility_2),
                gains=(outcome.gains_1, outcome.gains_2),
                trade_occurred=outcome.trade_occurred,
            )
            self.trades.append(event)

            # Update beliefs for both traders
            observed_type1 = self.info_env.get_observable_type(agent1)
            observed_type2 = self.info_env.get_observable_type(agent2)

            record_trade_observation(
                agent=agent1,
                partner=agent2,
                bundle_before=Bundle(pre_holdings1[0], pre_holdings1[1]),
                bundle_after=outcome.allocation_1,
                observed_partner_alpha=observed_type2.preferences.alpha,
                tick=self.tick,
            )
            record_trade_observation(
                agent=agent2,
                partner=agent1,
                bundle_before=Bundle(pre_holdings2[0], pre_holdings2[1]),
                bundle_after=outcome.allocation_2,
                observed_partner_alpha=observed_type1.preferences.alpha,
                tick=self.tick,
            )

            return event

        return None

    def _log_tick(
        self,
        search_decisions_data: list,
        movement_events_data: list,
        trade_events: list[TradeEvent],
        commitments_formed_data: list[tuple[str, str]],
        commitments_broken_data: list[tuple[str, str, str]],
    ) -> None:
        """Create and log a complete tick record."""
        from microecon.logging import (
            create_agent_snapshot,
            create_belief_snapshot,
            create_commitment_broken_event,
            create_commitment_formed_event,
            create_search_decision,
            create_target_evaluation,
            create_movement_event,
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
                    endowment=(agent.holdings.x, agent.holdings.y),
                    alpha=agent.preferences.alpha,
                    utility=agent.utility(),
                    has_beliefs=agent.has_beliefs,
                    n_trades_in_memory=agent.memory.n_trades() if agent.has_beliefs else 0,
                    n_type_beliefs=len(agent.type_beliefs) if agent.has_beliefs else 0,
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
                    observed_alpha=e.observed_alpha,
                    used_belief=e.used_belief,
                    believed_alpha=e.believed_alpha,
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

        # Trade events are already canonical TradeEvent objects
        trades = trade_events

        # Create commitment events
        commitments_formed = [
            create_commitment_formed_event(agent_a=a, agent_b=b)
            for a, b in commitments_formed_data
        ]
        commitments_broken = [
            create_commitment_broken_event(agent_a=a, agent_b=b, reason=reason)
            for a, b, reason in commitments_broken_data
        ]

        # Create belief snapshots for agents with beliefs
        belief_snapshots = []
        for agent in self.agents:
            if agent.has_beliefs:
                # Collect type beliefs
                type_beliefs_data = [
                    (
                        tb.agent_id,
                        tb.believed_alpha,
                        tb.confidence,
                        tb.n_interactions,
                    )
                    for tb in agent.type_beliefs.values()
                ]
                # Collect price belief
                price_belief_data = (
                    agent.price_belief.mean,
                    agent.price_belief.variance,
                    agent.price_belief.n_observations,
                )
                belief_snapshots.append(create_belief_snapshot(
                    agent_id=agent.id,
                    type_beliefs=type_beliefs_data,
                    price_belief=price_belief_data,
                    n_trades_in_memory=agent.memory.n_trades(),
                ))

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
            belief_snapshots=belief_snapshots,
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
            trade.gains[0] + trade.gains[1]
            for trade in self.trades
        )


def create_simple_economy(
    n_agents: int,
    grid_size: int = 10,
    perception_radius: float = 7.0,
    discount_factor: float = 0.95,
    seed: Optional[int] = None,
    bargaining_protocol: Optional[BargainingProtocol] = None,
    decision_procedure: Optional[DecisionProcedure] = None,
    use_beliefs: bool = False,
    info_env: Optional[InformationEnvironment] = None,
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
        decision_procedure: Procedure for agent action selection (default: Rational)
        use_beliefs: Enable belief system for agents (default: False)
        info_env: Information environment (default: FullInformation)

    Returns:
        Configured Simulation ready to run
    """
    # Create RNG instance - seed if provided, otherwise use system entropy
    rng = Random(seed) if seed is not None else Random()

    sim = Simulation(
        grid=Grid(grid_size),
        info_env=info_env or FullInformation(),
        bargaining_protocol=bargaining_protocol or NashBargainingProtocol(),
        decision_procedure=decision_procedure or RationalDecisionProcedure(),
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

        if use_beliefs:
            agent.enable_beliefs()

    return sim
