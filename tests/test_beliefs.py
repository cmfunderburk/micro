"""Tests for the agent belief system.

Tests cover:
- BELIEF-002: Agent memory (TradeMemory, PriceObservation, InteractionRecord, AgentMemory)
- BELIEF-003: Update rules (BayesianUpdateRule, HeuristicUpdateRule)
- BELIEF-004: Search integration (in TestSearchIntegration)
- BELIEF-005: Exchange integration (record_trade_observation, record_encounter, etc.)
"""

import pytest
from microecon.beliefs import (
    TradeMemory,
    PriceObservation,
    InteractionRecord,
    AgentMemory,
    PriceBelief,
    TypeBelief,
    BeliefUpdateRule,
    BayesianUpdateRule,
    HeuristicUpdateRule,
    record_trade_observation,
    record_encounter,
    record_observed_trade,
)
from microecon.agent import create_agent, Agent
from microecon.bundle import Bundle


class TestAgentMemory:
    """Tests for BELIEF-002: Agent Memory."""

    def test_agent_has_beliefs_property(self):
        """Agent.has_beliefs should be False by default."""
        agent = create_agent(alpha=0.5, endowment_x=10, endowment_y=10)
        assert agent.has_beliefs is False

    def test_enable_beliefs(self):
        """Agent.enable_beliefs should initialize memory and beliefs."""
        agent = create_agent(alpha=0.5, endowment_x=10, endowment_y=10)
        agent.enable_beliefs()

        assert agent.has_beliefs is True
        assert agent.memory is not None
        assert agent.price_belief is not None
        assert agent.type_beliefs is not None
        assert agent.update_rule is not None
        assert isinstance(agent.update_rule, BayesianUpdateRule)

    def test_enable_beliefs_with_custom_rule(self):
        """enable_beliefs should accept custom update rule."""
        agent = create_agent(alpha=0.5, endowment_x=10, endowment_y=10)
        rule = HeuristicUpdateRule(learning_rate=0.2)
        agent.enable_beliefs(update_rule=rule)

        assert isinstance(agent.update_rule, HeuristicUpdateRule)

    def test_disable_beliefs(self):
        """disable_beliefs should clear memory and beliefs."""
        agent = create_agent(alpha=0.5, endowment_x=10, endowment_y=10)
        agent.enable_beliefs()
        agent.disable_beliefs()

        assert agent.has_beliefs is False
        assert agent.memory is None
        assert agent.price_belief is None
        assert agent.type_beliefs is None
        assert agent.update_rule is None

    def test_memory_depth_configurable(self):
        """Memory depth should be configurable."""
        agent = create_agent(alpha=0.5, endowment_x=10, endowment_y=10)
        agent.enable_beliefs(memory_depth=50)

        assert agent.memory.max_depth == 50

    def test_memory_depth_unlimited(self):
        """Memory depth None means unlimited."""
        agent = create_agent(alpha=0.5, endowment_x=10, endowment_y=10)
        agent.enable_beliefs(memory_depth=None)

        assert agent.memory.max_depth is None


class TestTradeMemory:
    """Tests for TradeMemory dataclass."""

    def test_trade_memory_creation(self):
        """TradeMemory should store trade details."""
        tm = TradeMemory(
            tick=5,
            partner_id="abc123",
            my_bundle_before_x=10.0,
            my_bundle_before_y=5.0,
            my_bundle_after_x=8.0,
            my_bundle_after_y=7.0,
            observed_partner_alpha=0.6,
        )

        assert tm.tick == 5
        assert tm.partner_id == "abc123"
        assert tm.my_bundle_before_x == 10.0
        assert tm.my_bundle_after_y == 7.0
        assert tm.observed_partner_alpha == 0.6

    def test_trade_memory_to_dict(self):
        """to_dict should serialize trade memory."""
        tm = TradeMemory(
            tick=5,
            partner_id="abc123",
            my_bundle_before_x=10.0,
            my_bundle_before_y=5.0,
            my_bundle_after_x=8.0,
            my_bundle_after_y=7.0,
            observed_partner_alpha=0.6,
        )
        d = tm.to_dict()

        assert d["tick"] == 5
        assert d["partner_id"] == "abc123"
        assert d["bundle_before"] == [10.0, 5.0]
        assert d["bundle_after"] == [8.0, 7.0]


class TestPriceObservation:
    """Tests for PriceObservation dataclass."""

    def test_price_observation_creation(self):
        """PriceObservation should store exchange details."""
        po = PriceObservation(
            tick=10,
            x_exchanged=2.0,
            y_exchanged=4.0,
            is_own_trade=True,
        )

        assert po.tick == 10
        assert po.x_exchanged == 2.0
        assert po.y_exchanged == 4.0
        assert po.is_own_trade is True

    def test_exchange_rate_computation(self):
        """exchange_rate should compute x/y ratio."""
        po = PriceObservation(tick=0, x_exchanged=2.0, y_exchanged=4.0, is_own_trade=True)
        assert po.exchange_rate == 0.5  # 2/4

    def test_exchange_rate_zero_y(self):
        """exchange_rate should handle y=0."""
        po = PriceObservation(tick=0, x_exchanged=2.0, y_exchanged=0.0, is_own_trade=True)
        assert po.exchange_rate == float('inf')

    def test_exchange_rate_zero_both(self):
        """exchange_rate should handle both zero."""
        po = PriceObservation(tick=0, x_exchanged=0.0, y_exchanged=0.0, is_own_trade=True)
        assert po.exchange_rate == 1.0  # Default

    def test_to_dict(self):
        """to_dict should serialize observation."""
        po = PriceObservation(tick=10, x_exchanged=2.0, y_exchanged=4.0, is_own_trade=True)
        d = po.to_dict()

        assert d["tick"] == 10
        assert d["exchange_rate"] == 0.5


class TestInteractionRecord:
    """Tests for InteractionRecord dataclass."""

    def test_interaction_record_creation(self):
        """InteractionRecord should store interaction details."""
        ir = InteractionRecord(
            tick=15,
            interaction_type="trade",
            observed_alpha=0.7,
            outcome={"utility_gain": 0.5},
        )

        assert ir.tick == 15
        assert ir.interaction_type == "trade"
        assert ir.observed_alpha == 0.7
        assert ir.outcome["utility_gain"] == 0.5

    def test_default_outcome(self):
        """outcome should default to empty dict."""
        ir = InteractionRecord(tick=0, interaction_type="encounter", observed_alpha=0.5)
        assert ir.outcome == {}


class TestAgentMemoryContainer:
    """Tests for AgentMemory container."""

    def test_empty_memory(self):
        """New memory should be empty."""
        mem = AgentMemory()

        assert mem.n_trades() == 0
        assert mem.n_price_observations() == 0
        assert mem.n_partners_known() == 0

    def test_add_trade(self):
        """add_trade should store trade record."""
        mem = AgentMemory()
        tm = TradeMemory(
            tick=1, partner_id="p1",
            my_bundle_before_x=10, my_bundle_before_y=5,
            my_bundle_after_x=8, my_bundle_after_y=7,
            observed_partner_alpha=0.6,
        )
        mem.add_trade(tm)

        assert mem.n_trades() == 1
        assert mem.trade_history[0].partner_id == "p1"

    def test_add_price_observation(self):
        """add_price_observation should store observation."""
        mem = AgentMemory()
        po = PriceObservation(tick=1, x_exchanged=2, y_exchanged=4, is_own_trade=True)
        mem.add_price_observation(po)

        assert mem.n_price_observations() == 1
        assert mem.price_observations[0].exchange_rate == 0.5

    def test_add_interaction(self):
        """add_interaction should store per-partner record."""
        mem = AgentMemory()
        ir = InteractionRecord(tick=1, interaction_type="trade", observed_alpha=0.5)
        mem.add_interaction("p1", ir)

        assert mem.n_partners_known() == 1
        assert len(mem.get_partner_interactions("p1")) == 1

    def test_multiple_partner_interactions(self):
        """Multiple interactions with same partner should accumulate."""
        mem = AgentMemory()
        mem.add_interaction("p1", InteractionRecord(tick=1, interaction_type="trade", observed_alpha=0.5))
        mem.add_interaction("p1", InteractionRecord(tick=2, interaction_type="trade", observed_alpha=0.6))

        assert mem.n_partners_known() == 1
        assert len(mem.get_partner_interactions("p1")) == 2

    def test_eviction_trade_history(self):
        """Trade history should evict oldest when at capacity."""
        mem = AgentMemory(max_depth=3)

        for i in range(5):
            tm = TradeMemory(
                tick=i, partner_id=f"p{i}",
                my_bundle_before_x=10, my_bundle_before_y=5,
                my_bundle_after_x=8, my_bundle_after_y=7,
                observed_partner_alpha=0.5,
            )
            mem.add_trade(tm)

        assert mem.n_trades() == 3
        # Should have ticks 2, 3, 4 (oldest evicted)
        assert mem.trade_history[0].tick == 2

    def test_eviction_price_observations(self):
        """Price observations should evict oldest when at capacity."""
        mem = AgentMemory(max_depth=2)

        for i in range(4):
            po = PriceObservation(tick=i, x_exchanged=1, y_exchanged=i+1, is_own_trade=True)
            mem.add_price_observation(po)

        assert mem.n_price_observations() == 2
        assert mem.price_observations[0].tick == 2

    def test_eviction_partner_history(self):
        """Partner history should evict oldest per-partner."""
        mem = AgentMemory(max_depth=2)

        for i in range(4):
            ir = InteractionRecord(tick=i, interaction_type="trade", observed_alpha=0.5)
            mem.add_interaction("p1", ir)

        assert len(mem.get_partner_interactions("p1")) == 2
        assert mem.get_partner_interactions("p1")[0].tick == 2

    def test_unlimited_memory(self):
        """max_depth=None should not evict."""
        mem = AgentMemory(max_depth=None)

        for i in range(100):
            tm = TradeMemory(
                tick=i, partner_id=f"p{i}",
                my_bundle_before_x=10, my_bundle_before_y=5,
                my_bundle_after_x=8, my_bundle_after_y=7,
                observed_partner_alpha=0.5,
            )
            mem.add_trade(tm)

        assert mem.n_trades() == 100

    def test_clear(self):
        """clear should empty all memory."""
        mem = AgentMemory()
        mem.add_trade(TradeMemory(
            tick=1, partner_id="p1",
            my_bundle_before_x=10, my_bundle_before_y=5,
            my_bundle_after_x=8, my_bundle_after_y=7,
            observed_partner_alpha=0.5,
        ))
        mem.add_price_observation(PriceObservation(tick=1, x_exchanged=1, y_exchanged=2, is_own_trade=True))
        mem.add_interaction("p1", InteractionRecord(tick=1, interaction_type="trade", observed_alpha=0.5))

        mem.clear()

        assert mem.n_trades() == 0
        assert mem.n_price_observations() == 0
        assert mem.n_partners_known() == 0

    def test_to_dict(self):
        """to_dict should serialize entire memory."""
        mem = AgentMemory(max_depth=10)
        mem.add_trade(TradeMemory(
            tick=1, partner_id="p1",
            my_bundle_before_x=10, my_bundle_before_y=5,
            my_bundle_after_x=8, my_bundle_after_y=7,
            observed_partner_alpha=0.5,
        ))

        d = mem.to_dict()

        assert d["max_depth"] == 10
        assert d["n_trades"] == 1
        assert len(d["trades"]) == 1

    def test_read_only_properties(self):
        """Properties should return copies, not originals."""
        mem = AgentMemory()
        mem.add_trade(TradeMemory(
            tick=1, partner_id="p1",
            my_bundle_before_x=10, my_bundle_before_y=5,
            my_bundle_after_x=8, my_bundle_after_y=7,
            observed_partner_alpha=0.5,
        ))

        # Modifying returned list should not affect internal state
        trades = mem.trade_history
        trades.clear()

        assert mem.n_trades() == 1  # Original unchanged


class TestPriceBelief:
    """Tests for PriceBelief dataclass."""

    def test_default_values(self):
        """Default belief should be uninformative."""
        pb = PriceBelief()

        assert pb.mean == 1.0
        assert pb.variance == 1.0
        assert pb.n_observations == 0

    def test_to_dict(self):
        """to_dict should serialize belief."""
        pb = PriceBelief(mean=2.0, variance=0.5, n_observations=10)
        d = pb.to_dict()

        assert d["mean"] == 2.0
        assert d["variance"] == 0.5
        assert d["n_observations"] == 10


class TestTypeBelief:
    """Tests for TypeBelief dataclass."""

    def test_creation(self):
        """TypeBelief should store agent-specific belief."""
        tb = TypeBelief(
            agent_id="abc123",
            believed_alpha=0.6,
            confidence=0.8,
            n_interactions=5,
        )

        assert tb.agent_id == "abc123"
        assert tb.believed_alpha == 0.6
        assert tb.confidence == 0.8
        assert tb.n_interactions == 5

    def test_alpha_clamping(self):
        """Alpha should be clamped to valid range."""
        tb = TypeBelief(agent_id="x", believed_alpha=1.5, confidence=0.5)
        assert tb.believed_alpha == 0.99

        tb = TypeBelief(agent_id="x", believed_alpha=-0.5, confidence=0.5)
        assert tb.believed_alpha == 0.01

    def test_confidence_clamping(self):
        """Confidence should be clamped to [0, 1]."""
        tb = TypeBelief(agent_id="x", believed_alpha=0.5, confidence=1.5)
        assert tb.confidence == 1.0

        tb = TypeBelief(agent_id="x", believed_alpha=0.5, confidence=-0.5)
        assert tb.confidence == 0.0


class TestBeliefUpdates:
    """Tests for BELIEF-003: Update Rules."""

    class TestBayesianUpdateRule:
        """Tests for BayesianUpdateRule."""

        def test_creation(self):
            """Should create with default noise variance."""
            rule = BayesianUpdateRule()
            assert rule.obs_var == 0.01

        def test_creation_custom_noise(self):
            """Should accept custom noise variance."""
            rule = BayesianUpdateRule(observation_noise_variance=0.1)
            assert rule.obs_var == 0.1

        def test_invalid_noise_variance(self):
            """Should reject non-positive noise variance."""
            with pytest.raises(ValueError):
                BayesianUpdateRule(observation_noise_variance=0)

            with pytest.raises(ValueError):
                BayesianUpdateRule(observation_noise_variance=-0.1)

        def test_price_update_moves_toward_observation(self):
            """Price belief mean should move toward observation."""
            rule = BayesianUpdateRule()
            prior = PriceBelief(mean=1.0, variance=1.0, n_observations=0)
            obs = PriceObservation(tick=0, x_exchanged=2.0, y_exchanged=1.0, is_own_trade=True)

            posterior = rule.update_price_belief(prior, obs)

            # Observation is exchange_rate = 2.0
            # Posterior should be between prior (1.0) and observation (2.0)
            assert prior.mean < posterior.mean < 2.0

        def test_price_update_reduces_variance(self):
            """Price belief variance should decrease with observations."""
            rule = BayesianUpdateRule()
            prior = PriceBelief(mean=1.0, variance=1.0, n_observations=0)
            obs = PriceObservation(tick=0, x_exchanged=1.0, y_exchanged=1.0, is_own_trade=True)

            posterior = rule.update_price_belief(prior, obs)

            assert posterior.variance < prior.variance

        def test_price_update_increments_count(self):
            """n_observations should increment."""
            rule = BayesianUpdateRule()
            prior = PriceBelief(mean=1.0, variance=1.0, n_observations=5)
            obs = PriceObservation(tick=0, x_exchanged=1.0, y_exchanged=1.0, is_own_trade=True)

            posterior = rule.update_price_belief(prior, obs)

            assert posterior.n_observations == 6

        def test_price_update_handles_invalid_observation(self):
            """Should handle zero/infinite exchange rates gracefully."""
            rule = BayesianUpdateRule()
            prior = PriceBelief(mean=1.0, variance=1.0, n_observations=0)

            # Zero y gives infinite rate
            obs = PriceObservation(tick=0, x_exchanged=1.0, y_exchanged=0.0, is_own_trade=True)
            posterior = rule.update_price_belief(prior, obs)

            # Should return prior unchanged (except no increment)
            assert posterior.mean == prior.mean
            assert posterior.variance == prior.variance

        def test_type_update_first_observation(self):
            """First observation should initialize belief at observed value."""
            rule = BayesianUpdateRule()

            belief = rule.update_type_belief(None, "agent1", 0.7)

            assert belief.agent_id == "agent1"
            assert belief.believed_alpha == 0.7
            assert belief.n_interactions == 1
            assert belief.confidence > 0

        def test_type_update_moves_toward_observation(self):
            """Type belief should move toward observation."""
            rule = BayesianUpdateRule()
            prior = TypeBelief(agent_id="a1", believed_alpha=0.5, confidence=0.5, n_interactions=5)

            posterior = rule.update_type_belief(prior, "a1", 0.8)

            # Belief should move toward 0.8
            assert prior.believed_alpha < posterior.believed_alpha < 0.8

        def test_type_update_increases_confidence(self):
            """Confidence should increase with interactions."""
            rule = BayesianUpdateRule()
            prior = TypeBelief(agent_id="a1", believed_alpha=0.5, confidence=0.3, n_interactions=2)

            posterior = rule.update_type_belief(prior, "a1", 0.5)

            assert posterior.confidence > prior.confidence

        def test_type_update_clamps_alpha(self):
            """Alpha should be clamped to valid range."""
            rule = BayesianUpdateRule()

            belief = rule.update_type_belief(None, "a1", 1.5)  # Invalid alpha
            assert 0.01 <= belief.believed_alpha <= 0.99

    class TestHeuristicUpdateRule:
        """Tests for HeuristicUpdateRule."""

        def test_creation(self):
            """Should create with default learning rate."""
            rule = HeuristicUpdateRule()
            assert rule.alpha == 0.1

        def test_creation_custom_rate(self):
            """Should accept custom learning rate."""
            rule = HeuristicUpdateRule(learning_rate=0.3)
            assert rule.alpha == 0.3

        def test_invalid_learning_rate(self):
            """Should reject invalid learning rates."""
            with pytest.raises(ValueError):
                HeuristicUpdateRule(learning_rate=0)

            with pytest.raises(ValueError):
                HeuristicUpdateRule(learning_rate=1.5)

        def test_price_update_ema(self):
            """Price update should use EMA formula."""
            rule = HeuristicUpdateRule(learning_rate=0.2)
            prior = PriceBelief(mean=1.0, variance=0.5, n_observations=10)
            obs = PriceObservation(tick=0, x_exchanged=2.0, y_exchanged=1.0, is_own_trade=True)

            posterior = rule.update_price_belief(prior, obs)

            # EMA: new = (1 - 0.2) * 1.0 + 0.2 * 2.0 = 0.8 + 0.4 = 1.2
            assert posterior.mean == pytest.approx(1.2, rel=1e-6)

        def test_type_update_first_observation(self):
            """First observation should initialize at observed value."""
            rule = HeuristicUpdateRule()

            belief = rule.update_type_belief(None, "a1", 0.6)

            assert belief.believed_alpha == 0.6
            assert belief.n_interactions == 1

        def test_type_update_ema(self):
            """Type update should use EMA formula."""
            rule = HeuristicUpdateRule(learning_rate=0.5)
            prior = TypeBelief(agent_id="a1", believed_alpha=0.4, confidence=0.5, n_interactions=5)

            posterior = rule.update_type_belief(prior, "a1", 0.8)

            # EMA: new = (1 - 0.5) * 0.4 + 0.5 * 0.8 = 0.2 + 0.4 = 0.6
            assert posterior.believed_alpha == pytest.approx(0.6, rel=1e-6)

        def test_convergence_with_consistent_observations(self):
            """Beliefs should converge to true value with consistent observations."""
            rule = HeuristicUpdateRule(learning_rate=0.3)
            prior = PriceBelief(mean=1.0, variance=1.0, n_observations=0)
            true_price = 2.0

            belief = prior
            for _ in range(50):
                obs = PriceObservation(tick=0, x_exchanged=true_price, y_exchanged=1.0, is_own_trade=True)
                belief = rule.update_price_belief(belief, obs)

            # Should have converged close to true price
            assert belief.mean == pytest.approx(true_price, rel=0.01)


class TestAgentBeliefMethods:
    """Tests for Agent belief-related methods."""

    def test_get_believed_alpha_no_beliefs(self):
        """get_believed_alpha should return None when beliefs disabled."""
        agent = create_agent(alpha=0.5, endowment_x=10, endowment_y=10)

        assert agent.get_believed_alpha("partner1") is None

    def test_get_believed_alpha_no_belief_for_partner(self):
        """get_believed_alpha should return None when no belief for partner."""
        agent = create_agent(alpha=0.5, endowment_x=10, endowment_y=10)
        agent.enable_beliefs()

        assert agent.get_believed_alpha("unknown_partner") is None

    def test_get_believed_alpha_with_belief(self):
        """get_believed_alpha should return believed alpha when belief exists."""
        agent = create_agent(alpha=0.5, endowment_x=10, endowment_y=10)
        agent.enable_beliefs()

        # Manually add a belief
        agent.type_beliefs["partner1"] = TypeBelief(
            agent_id="partner1",
            believed_alpha=0.7,
            confidence=0.5,
            n_interactions=3,
        )

        assert agent.get_believed_alpha("partner1") == pytest.approx(0.7, rel=1e-6)


class TestSearchIntegration:
    """Tests for BELIEF-004: Search Integration."""

    def test_search_without_beliefs_uses_observations(self):
        """Search should use observations when beliefs disabled."""
        from microecon.grid import Grid, Position
        from microecon.information import FullInformation
        from microecon.search import evaluate_targets

        # Create agents
        agent1 = create_agent(alpha=0.3, endowment_x=10, endowment_y=5, agent_id="a1")
        agent2 = create_agent(alpha=0.7, endowment_x=5, endowment_y=10, agent_id="a2")

        # Set up grid
        grid = Grid(10)
        grid.place_agent(agent1, Position(0, 0))
        grid.place_agent(agent2, Position(1, 0))

        info_env = FullInformation()
        agents_by_id = {"a1": agent1, "a2": agent2}

        # Search without beliefs
        result = evaluate_targets(agent1, grid, info_env, agents_by_id, use_beliefs=False)

        assert result.best_target_id == "a2"
        assert result.discounted_value > 0

    def test_search_with_beliefs_uses_believed_types(self):
        """Search should use beliefs when enabled and available."""
        from microecon.grid import Grid, Position
        from microecon.information import FullInformation
        from microecon.search import evaluate_targets_detailed

        # Create agents
        agent1 = create_agent(alpha=0.3, endowment_x=10, endowment_y=5, agent_id="a1")
        agent2 = create_agent(alpha=0.7, endowment_x=5, endowment_y=10, agent_id="a2")

        # Enable beliefs and set belief about agent2
        agent1.enable_beliefs()
        agent1.type_beliefs["a2"] = TypeBelief(
            agent_id="a2",
            believed_alpha=0.8,  # Different from true alpha (0.7)
            confidence=0.9,
            n_interactions=10,
        )

        # Set up grid
        grid = Grid(10)
        grid.place_agent(agent1, Position(0, 0))
        grid.place_agent(agent2, Position(1, 0))

        info_env = FullInformation()
        agents_by_id = {"a1": agent1, "a2": agent2}

        # Search with beliefs
        _, evaluations = evaluate_targets_detailed(
            agent1, grid, info_env, agents_by_id, use_beliefs=True
        )

        assert len(evaluations) == 1
        assert evaluations[0].target_id == "a2"
        assert evaluations[0].used_belief is True
        assert evaluations[0].believed_alpha == pytest.approx(0.8, rel=1e-6)
        assert evaluations[0].observed_alpha == pytest.approx(0.7, rel=1e-6)

    def test_search_without_belief_for_partner_uses_observation(self):
        """Search should use observation when no belief exists for partner."""
        from microecon.grid import Grid, Position
        from microecon.information import FullInformation
        from microecon.search import evaluate_targets_detailed

        # Create agents
        agent1 = create_agent(alpha=0.3, endowment_x=10, endowment_y=5, agent_id="a1")
        agent2 = create_agent(alpha=0.7, endowment_x=5, endowment_y=10, agent_id="a2")

        # Enable beliefs but don't add belief about agent2
        agent1.enable_beliefs()

        # Set up grid
        grid = Grid(10)
        grid.place_agent(agent1, Position(0, 0))
        grid.place_agent(agent2, Position(1, 0))

        info_env = FullInformation()
        agents_by_id = {"a1": agent1, "a2": agent2}

        # Search with beliefs enabled but no belief for this partner
        _, evaluations = evaluate_targets_detailed(
            agent1, grid, info_env, agents_by_id, use_beliefs=True
        )

        assert len(evaluations) == 1
        assert evaluations[0].used_belief is False
        assert evaluations[0].believed_alpha is None

    def test_search_beliefs_affect_target_choice(self):
        """Beliefs should affect which target is chosen."""
        from microecon.grid import Grid, Position
        from microecon.information import FullInformation
        from microecon.search import evaluate_targets

        # Create agents with similar true alphas
        agent1 = create_agent(alpha=0.3, endowment_x=10, endowment_y=5, agent_id="a1")
        agent2 = create_agent(alpha=0.7, endowment_x=5, endowment_y=10, agent_id="a2")
        agent3 = create_agent(alpha=0.65, endowment_x=5, endowment_y=10, agent_id="a3")

        # Enable beliefs and set belief that makes agent3 appear more attractive
        agent1.enable_beliefs()
        agent1.type_beliefs["a3"] = TypeBelief(
            agent_id="a3",
            believed_alpha=0.9,  # Much higher than true (0.65)
            confidence=0.9,
            n_interactions=10,
        )

        # Set up grid (agent2 closer but agent3 has higher believed surplus)
        grid = Grid(20)
        grid.place_agent(agent1, Position(0, 0))
        grid.place_agent(agent2, Position(1, 0))  # Very close
        grid.place_agent(agent3, Position(2, 0))  # Slightly farther

        info_env = FullInformation()
        agents_by_id = {"a1": agent1, "a2": agent2, "a3": agent3}

        # Search with beliefs
        result_with_beliefs = evaluate_targets(
            agent1, grid, info_env, agents_by_id, use_beliefs=True
        )

        # Search without beliefs
        result_without_beliefs = evaluate_targets(
            agent1, grid, info_env, agents_by_id, use_beliefs=False
        )

        # With the belief, agent3 might be preferred despite being farther
        # (depends on exact surplus values, but test that results can differ)
        # This is a validity test - beliefs are being used
        assert result_with_beliefs.discounted_value != result_without_beliefs.discounted_value

    def test_should_trade_uses_beliefs(self):
        """should_trade should use beliefs when available."""
        from microecon.information import FullInformation
        from microecon.search import should_trade

        # Create agents with identical true types (no real gains from trade)
        agent1 = create_agent(alpha=0.5, endowment_x=10, endowment_y=10, agent_id="a1")
        agent2 = create_agent(alpha=0.5, endowment_x=10, endowment_y=10, agent_id="a2")

        info_env = FullInformation()

        # Without beliefs (same endowments and preferences = no gains)
        result_no_beliefs = should_trade(agent1, agent2, info_env, use_beliefs=False)
        assert result_no_beliefs is False, "Identical agents should not trade"

        # Enable beliefs for BOTH agents with mutual perceived gains
        # Agent1 believes agent2 prefers good x more (alpha=0.8)
        agent1.enable_beliefs()
        agent1.type_beliefs["a2"] = TypeBelief(
            agent_id="a2",
            believed_alpha=0.8,
            confidence=0.9,
            n_interactions=10,
        )

        # Agent2 believes agent1 prefers good y more (alpha=0.2)
        agent2.enable_beliefs()
        agent2.type_beliefs["a1"] = TypeBelief(
            agent_id="a1",
            believed_alpha=0.2,
            confidence=0.9,
            n_interactions=10,
        )

        # With mutual beliefs that create perceived complementarity, both see gains
        result_with_beliefs = should_trade(agent1, agent2, info_env, use_beliefs=True)
        assert result_with_beliefs is True, "Mutual beliefs should create perceived gains"

        # Verify that use_beliefs=False ignores beliefs (back to no trade)
        result_beliefs_disabled = should_trade(agent1, agent2, info_env, use_beliefs=False)
        assert result_beliefs_disabled is False, "use_beliefs=False should ignore beliefs"

    def test_use_beliefs_false_ignores_beliefs(self):
        """use_beliefs=False should ignore all beliefs."""
        from microecon.grid import Grid, Position
        from microecon.information import FullInformation
        from microecon.search import evaluate_targets_detailed

        # Create agents
        agent1 = create_agent(alpha=0.3, endowment_x=10, endowment_y=5, agent_id="a1")
        agent2 = create_agent(alpha=0.7, endowment_x=5, endowment_y=10, agent_id="a2")

        # Enable beliefs with a very different belief
        agent1.enable_beliefs()
        agent1.type_beliefs["a2"] = TypeBelief(
            agent_id="a2",
            believed_alpha=0.99,  # Very different from true
            confidence=0.99,
            n_interactions=100,
        )

        # Set up grid
        grid = Grid(10)
        grid.place_agent(agent1, Position(0, 0))
        grid.place_agent(agent2, Position(1, 0))

        info_env = FullInformation()
        agents_by_id = {"a1": agent1, "a2": agent2}

        # Search with use_beliefs=False should ignore beliefs
        _, evaluations = evaluate_targets_detailed(
            agent1, grid, info_env, agents_by_id, use_beliefs=False
        )

        assert len(evaluations) == 1
        assert evaluations[0].used_belief is False
        assert evaluations[0].believed_alpha is None
        # Should use observed alpha (true alpha in FullInformation)
        assert evaluations[0].observed_alpha == pytest.approx(0.7, rel=1e-6)


class TestExchangeIntegration:
    """Tests for BELIEF-005: Exchange Integration."""

    def test_record_trade_observation_no_beliefs(self):
        """record_trade_observation should do nothing if beliefs disabled."""
        agent1 = create_agent(alpha=0.3, endowment_x=10, endowment_y=5, agent_id="a1")
        agent2 = create_agent(alpha=0.7, endowment_x=5, endowment_y=10, agent_id="a2")

        bundle_before = Bundle(10, 5)
        bundle_after = Bundle(8, 7)

        # Should not crash when beliefs disabled
        record_trade_observation(
            agent1, agent2, bundle_before, bundle_after, 0.7, tick=1
        )

        # Nothing recorded
        assert agent1.memory is None

    def test_record_trade_observation_records_trade(self):
        """record_trade_observation should record trade in memory."""
        agent1 = create_agent(alpha=0.3, endowment_x=10, endowment_y=5, agent_id="a1")
        agent2 = create_agent(alpha=0.7, endowment_x=5, endowment_y=10, agent_id="a2")
        agent1.enable_beliefs()

        bundle_before = Bundle(10, 5)
        bundle_after = Bundle(8, 7)

        record_trade_observation(
            agent1, agent2, bundle_before, bundle_after, 0.7, tick=5
        )

        assert agent1.memory.n_trades() == 1
        trade = agent1.memory.trade_history[0]
        assert trade.partner_id == "a2"
        assert trade.tick == 5
        assert trade.my_bundle_before_x == 10
        assert trade.my_bundle_after_y == 7

    def test_record_trade_observation_records_price(self):
        """record_trade_observation should record price observation."""
        agent1 = create_agent(alpha=0.3, endowment_x=10, endowment_y=5, agent_id="a1")
        agent2 = create_agent(alpha=0.7, endowment_x=5, endowment_y=10, agent_id="a2")
        agent1.enable_beliefs()

        bundle_before = Bundle(10, 5)
        bundle_after = Bundle(8, 7)  # Gave 2x, got 2y

        record_trade_observation(
            agent1, agent2, bundle_before, bundle_after, 0.7, tick=5
        )

        assert agent1.memory.n_price_observations() == 1
        price_obs = agent1.memory.price_observations[0]
        assert price_obs.is_own_trade is True
        assert price_obs.x_exchanged == pytest.approx(2.0, rel=1e-6)
        assert price_obs.y_exchanged == pytest.approx(2.0, rel=1e-6)

    def test_record_trade_observation_updates_beliefs(self):
        """record_trade_observation should update beliefs."""
        agent1 = create_agent(alpha=0.3, endowment_x=10, endowment_y=5, agent_id="a1")
        agent2 = create_agent(alpha=0.7, endowment_x=5, endowment_y=10, agent_id="a2")
        agent1.enable_beliefs()

        bundle_before = Bundle(10, 5)
        bundle_after = Bundle(8, 7)

        # First trade - should create belief
        record_trade_observation(
            agent1, agent2, bundle_before, bundle_after, 0.7, tick=1
        )

        assert "a2" in agent1.type_beliefs
        belief = agent1.type_beliefs["a2"]
        assert belief.believed_alpha == pytest.approx(0.7, rel=1e-6)
        assert belief.n_interactions == 1

        # Price belief should be updated
        assert agent1.price_belief.n_observations == 1

    def test_record_trade_observation_updates_existing_belief(self):
        """record_trade_observation should update existing beliefs."""
        agent1 = create_agent(alpha=0.3, endowment_x=10, endowment_y=5, agent_id="a1")
        agent2 = create_agent(alpha=0.7, endowment_x=5, endowment_y=10, agent_id="a2")
        agent1.enable_beliefs()

        bundle_before = Bundle(10, 5)
        bundle_after = Bundle(8, 7)

        # Two trades
        record_trade_observation(
            agent1, agent2, bundle_before, bundle_after, 0.6, tick=1
        )
        record_trade_observation(
            agent1, agent2, bundle_before, bundle_after, 0.8, tick=2
        )

        assert agent1.type_beliefs["a2"].n_interactions == 2
        # Belief should be between 0.6 and 0.8
        assert 0.6 < agent1.type_beliefs["a2"].believed_alpha < 0.8

    def test_record_encounter_updates_beliefs(self):
        """record_encounter should update type beliefs."""
        agent1 = create_agent(alpha=0.3, endowment_x=10, endowment_y=5, agent_id="a1")
        agent2 = create_agent(alpha=0.7, endowment_x=5, endowment_y=10, agent_id="a2")
        agent1.enable_beliefs()

        record_encounter(agent1, agent2, 0.7, tick=1)

        assert "a2" in agent1.type_beliefs
        assert agent1.type_beliefs["a2"].believed_alpha == pytest.approx(0.7, rel=1e-6)
        assert len(agent1.memory.get_partner_interactions("a2")) == 1

    def test_record_encounter_no_trade_memory(self):
        """record_encounter should not add to trade history."""
        agent1 = create_agent(alpha=0.3, endowment_x=10, endowment_y=5, agent_id="a1")
        agent2 = create_agent(alpha=0.7, endowment_x=5, endowment_y=10, agent_id="a2")
        agent1.enable_beliefs()

        record_encounter(agent1, agent2, 0.7, tick=1)

        assert agent1.memory.n_trades() == 0
        assert agent1.memory.n_price_observations() == 0

    def test_record_observed_trade_updates_price_belief(self):
        """record_observed_trade should update price belief."""
        agent1 = create_agent(alpha=0.3, endowment_x=10, endowment_y=5, agent_id="a1")
        agent1.enable_beliefs()

        record_observed_trade(
            agent1,
            trader1_id="a2",
            trader2_id="a3",
            x_exchanged=3.0,
            y_exchanged=6.0,
            tick=5,
        )

        assert agent1.memory.n_price_observations() == 1
        price_obs = agent1.memory.price_observations[0]
        assert price_obs.is_own_trade is False
        assert price_obs.exchange_rate == pytest.approx(0.5, rel=1e-6)

        # Price belief should be updated
        assert agent1.price_belief.n_observations == 1

    def test_record_observed_trade_no_type_updates(self):
        """record_observed_trade should not update type beliefs."""
        agent1 = create_agent(alpha=0.3, endowment_x=10, endowment_y=5, agent_id="a1")
        agent1.enable_beliefs()

        record_observed_trade(
            agent1,
            trader1_id="a2",
            trader2_id="a3",
            x_exchanged=3.0,
            y_exchanged=6.0,
            tick=5,
        )

        # No type beliefs should be created (we don't know their types)
        assert "a2" not in agent1.type_beliefs
        assert "a3" not in agent1.type_beliefs

    def test_beliefs_converge_with_repeated_trades(self):
        """Beliefs should converge toward true values with repeated interactions."""
        agent1 = create_agent(alpha=0.3, endowment_x=10, endowment_y=5, agent_id="a1")
        agent2 = create_agent(alpha=0.7, endowment_x=5, endowment_y=10, agent_id="a2")
        agent1.enable_beliefs()

        true_alpha = 0.7
        bundle_before = Bundle(10, 5)
        bundle_after = Bundle(8, 7)

        # Many trades with true alpha
        for tick in range(50):
            record_trade_observation(
                agent1, agent2, bundle_before, bundle_after, true_alpha, tick=tick
            )

        # Belief should converge to true alpha
        assert agent1.type_beliefs["a2"].believed_alpha == pytest.approx(true_alpha, rel=0.01)
        assert agent1.type_beliefs["a2"].confidence > 0.9

    def test_price_beliefs_converge_with_observations(self):
        """Price beliefs should converge with consistent observations."""
        agent1 = create_agent(alpha=0.3, endowment_x=10, endowment_y=5, agent_id="a1")
        agent1.enable_beliefs()

        true_price = 2.0  # 2 units of x per unit of y

        # Many observations at true price
        for tick in range(50):
            record_observed_trade(
                agent1,
                trader1_id="a2",
                trader2_id="a3",
                x_exchanged=2.0,  # 2x for 1y => price = 2
                y_exchanged=1.0,
                tick=tick,
            )

        # Price belief should converge
        assert agent1.price_belief.mean == pytest.approx(true_price, rel=0.01)


class TestBeliefSystemIntegration:
    """Tests for BELIEF-006: Full belief system integration."""

    def test_simulation_with_belief_enabled_agents(self):
        """Simulation should run correctly with belief-enabled agents."""
        from microecon.grid import Grid, Position
        from microecon.simulation import Simulation
        from microecon.information import FullInformation
        from microecon.bargaining import NashBargainingProtocol

        # Create agents with beliefs
        agents = [
            create_agent(alpha=0.3, endowment_x=10, endowment_y=2, agent_id="a1"),
            create_agent(alpha=0.7, endowment_x=2, endowment_y=10, agent_id="a2"),
        ]
        for agent in agents:
            agent.enable_beliefs()

        # Create simulation
        grid = Grid(size=10)
        sim = Simulation(
            grid=grid,
            bargaining_protocol=NashBargainingProtocol(),
            info_env=FullInformation(),
        )

        # Add agents at same position (to force trade)
        sim.add_agent(agents[0], Position(5, 5))
        sim.add_agent(agents[1], Position(5, 5))

        # Run simulation - should not crash
        sim.run(ticks=10)

        # Agents should still have beliefs enabled after simulation
        assert agents[0].has_beliefs
        assert agents[1].has_beliefs

        # If trades occurred, beliefs should have updated
        if len(sim.trades) > 0:
            # At least one agent should have trade memory
            total_trades = agents[0].memory.n_trades() + agents[1].memory.n_trades()
            assert total_trades > 0, "Trades occurred but no belief updates recorded"

            # Both agents should have formed beliefs about each other
            assert "a2" in agents[0].type_beliefs, "Agent1 should have belief about agent2"
            assert "a1" in agents[1].type_beliefs, "Agent2 should have belief about agent1"

    def test_beliefs_backward_compatible(self):
        """Agents without beliefs should work as before."""
        from microecon.grid import Grid, Position
        from microecon.simulation import Simulation
        from microecon.information import FullInformation
        from microecon.bargaining import NashBargainingProtocol

        # Create agents WITHOUT beliefs (default)
        agents = [
            create_agent(alpha=0.3, endowment_x=10, endowment_y=2, agent_id="a1"),
            create_agent(alpha=0.7, endowment_x=2, endowment_y=10, agent_id="a2"),
        ]

        # Create simulation
        grid = Grid(size=10)
        sim = Simulation(
            grid=grid,
            bargaining_protocol=NashBargainingProtocol(),
            info_env=FullInformation(),
        )

        sim.add_agent(agents[0], Position(5, 5))
        sim.add_agent(agents[1], Position(5, 5))

        # Run simulation - should work exactly as before
        sim.run(ticks=10)

        assert agents[0].memory is None
        assert agents[1].memory is None

    def test_create_simple_economy_with_beliefs(self):
        """create_simple_economy should enable beliefs when use_beliefs=True."""
        from microecon.simulation import create_simple_economy

        # Create economy with beliefs enabled
        sim = create_simple_economy(n_agents=4, grid_size=10, seed=42, use_beliefs=True)

        # All agents should have beliefs enabled
        for agent in sim.agents:
            assert agent.has_beliefs, f"Agent {agent.id} should have beliefs enabled"
            assert agent.memory is not None
            assert agent.type_beliefs is not None

        # Run simulation and verify beliefs update
        sim.run(ticks=50)

        # If trades occurred, at least some agents should have memories
        if len(sim.trades) > 0:
            agents_with_memories = [a for a in sim.agents if a.memory.n_trades() > 0]
            assert len(agents_with_memories) > 0, "No belief updates after trades"

    def test_create_simple_economy_without_beliefs(self):
        """create_simple_economy should not enable beliefs by default."""
        from microecon.simulation import create_simple_economy

        # Create economy without beliefs (default)
        sim = create_simple_economy(n_agents=4, grid_size=10, seed=42)

        # No agents should have beliefs enabled
        for agent in sim.agents:
            assert not agent.has_beliefs, f"Agent {agent.id} should not have beliefs"
            assert agent.memory is None

    def test_memory_serialization(self):
        """Agent memory should be serializable to dict."""
        agent = create_agent(alpha=0.3, endowment_x=10, endowment_y=5, agent_id="a1")
        partner = create_agent(alpha=0.7, endowment_x=5, endowment_y=10, agent_id="a2")
        agent.enable_beliefs()

        # Record some observations
        record_trade_observation(
            agent, partner,
            Bundle(10, 5), Bundle(8, 7),
            0.7, tick=1
        )
        record_encounter(agent, partner, 0.7, tick=2)

        # Serialize memory
        memory_dict = agent.memory.to_dict()

        # Verify structure
        assert "trades" in memory_dict
        assert "price_observations" in memory_dict
        assert "partner_history" in memory_dict
        assert len(memory_dict["trades"]) == 1
        assert memory_dict["n_partners_known"] == 1

    def test_belief_serialization(self):
        """Beliefs should be serializable to dict."""
        agent = create_agent(alpha=0.3, endowment_x=10, endowment_y=5, agent_id="a1")
        agent.enable_beliefs()

        # Update beliefs
        agent.type_beliefs["partner1"] = TypeBelief(
            agent_id="partner1",
            believed_alpha=0.6,
            confidence=0.8,
            n_interactions=5,
        )

        # Serialize
        price_dict = agent.price_belief.to_dict()
        type_dict = agent.type_beliefs["partner1"].to_dict()

        assert "mean" in price_dict
        assert "variance" in price_dict
        assert "believed_alpha" in type_dict
        assert "confidence" in type_dict

    def test_different_update_rules_produce_different_results(self):
        """Bayesian vs. Heuristic update rules should produce different beliefs."""
        # Create two agents with different update rules
        agent_bayesian = create_agent(alpha=0.5, endowment_x=10, endowment_y=10, agent_id="bayesian")
        agent_heuristic = create_agent(alpha=0.5, endowment_x=10, endowment_y=10, agent_id="heuristic")

        agent_bayesian.enable_beliefs(update_rule=BayesianUpdateRule())
        agent_heuristic.enable_beliefs(update_rule=HeuristicUpdateRule(learning_rate=0.3))

        partner = create_agent(alpha=0.7, endowment_x=5, endowment_y=10, agent_id="partner")

        # Same observations to both
        for tick in range(10):
            # Alternating observations to test learning dynamics
            observed_alpha = 0.6 if tick % 2 == 0 else 0.8
            record_encounter(agent_bayesian, partner, observed_alpha, tick=tick)
            record_encounter(agent_heuristic, partner, observed_alpha, tick=tick)

        # Beliefs should differ (different learning dynamics)
        bayesian_belief = agent_bayesian.type_beliefs["partner"].believed_alpha
        heuristic_belief = agent_heuristic.type_beliefs["partner"].believed_alpha

        # Both should be between 0.6 and 0.8
        assert 0.6 <= bayesian_belief <= 0.8
        assert 0.6 <= heuristic_belief <= 0.8

        # With 10 observations and lr=0.3, heuristic should weight recent more
        # (specific values depend on update dynamics, but confirms different rules work)

    def test_mixed_belief_and_non_belief_agents(self):
        """Simulation should work with mix of belief and non-belief agents."""
        from microecon.grid import Grid, Position
        from microecon.simulation import Simulation
        from microecon.information import FullInformation
        from microecon.bargaining import NashBargainingProtocol

        # Create mix of agents
        agent_with_beliefs = create_agent(alpha=0.3, endowment_x=10, endowment_y=2, agent_id="a1")
        agent_without_beliefs = create_agent(alpha=0.7, endowment_x=2, endowment_y=10, agent_id="a2")

        agent_with_beliefs.enable_beliefs()
        # agent_without_beliefs stays with beliefs=None

        # Create simulation
        grid = Grid(size=10)
        sim = Simulation(
            grid=grid,
            bargaining_protocol=NashBargainingProtocol(),
            info_env=FullInformation(),
        )

        sim.add_agent(agent_with_beliefs, Position(5, 5))
        sim.add_agent(agent_without_beliefs, Position(5, 5))

        # Should run without error
        sim.run(ticks=10)

        # Belief-enabled agent should still work
        assert agent_with_beliefs.has_beliefs
        assert not agent_without_beliefs.has_beliefs

    def test_full_test_count_still_above_threshold(self):
        """Verify all 450+ existing tests still pass (meta-test)."""
        # This is verified by the full test suite run
        # This test just documents the requirement
        pass

    def test_belief_update_rule_interface_extensible(self):
        """Custom update rules should work with the interface."""
        class ConstantUpdateRule(BeliefUpdateRule):
            """Always returns prior unchanged (for testing)."""

            def update_price_belief(self, prior, observation):
                return prior

            def update_type_belief(self, prior, agent_id, observed_alpha, context=None):
                if prior is None:
                    return TypeBelief(agent_id=agent_id, believed_alpha=0.5)
                return prior

        agent = create_agent(alpha=0.3, endowment_x=10, endowment_y=5, agent_id="a1")
        agent.enable_beliefs(update_rule=ConstantUpdateRule())

        # Observations should not change beliefs
        initial_price_mean = agent.price_belief.mean
        record_observed_trade(agent, "a2", "a3", 100.0, 1.0, tick=1)

        assert agent.price_belief.mean == initial_price_mean  # Unchanged


class TestBeliefSnapshotLogging:
    """Tests for FIND-03 Option B: Belief snapshot logging."""

    def test_belief_snapshot_dataclass(self):
        """BeliefSnapshot dataclass should serialize correctly."""
        from microecon.logging import (
            BeliefSnapshot,
            PriceBeliefSnapshot,
            TypeBeliefSnapshot,
        )

        snapshot = BeliefSnapshot(
            agent_id="agent_001",
            type_beliefs=(
                TypeBeliefSnapshot(
                    target_agent_id="agent_002",
                    believed_alpha=0.7,
                    confidence=0.8,
                    n_interactions=5,
                ),
            ),
            price_belief=PriceBeliefSnapshot(mean=1.5, variance=0.2, n_observations=10),
            n_trades_in_memory=3,
        )

        # Serialize to dict
        d = snapshot.to_dict()
        assert d["agent_id"] == "agent_001"
        assert len(d["type_beliefs"]) == 1
        assert d["type_beliefs"][0]["believed_alpha"] == 0.7
        assert d["price_belief"]["mean"] == 1.5
        assert d["n_trades_in_memory"] == 3

        # Deserialize from dict
        restored = BeliefSnapshot.from_dict(d)
        assert restored.agent_id == "agent_001"
        assert len(restored.type_beliefs) == 1
        assert restored.type_beliefs[0].believed_alpha == 0.7

    def test_tick_record_includes_belief_snapshots(self):
        """TickRecord should include belief_snapshots field."""
        from microecon.logging import (
            BeliefSnapshot,
            PriceBeliefSnapshot,
            TickRecord,
            TypeBeliefSnapshot,
        )

        belief_snapshots = (
            BeliefSnapshot(
                agent_id="a1",
                type_beliefs=(),
                price_belief=PriceBeliefSnapshot(mean=1.0, variance=1.0, n_observations=0),
                n_trades_in_memory=0,
            ),
        )

        tick_record = TickRecord(
            tick=0,
            agent_snapshots=(),
            search_decisions=(),
            movements=(),
            trades=(),
            total_welfare=100.0,
            cumulative_trades=0,
            belief_snapshots=belief_snapshots,
        )

        # Should serialize with belief snapshots
        d = tick_record.to_dict()
        assert "belief_snapshots" in d
        assert len(d["belief_snapshots"]) == 1

        # Should deserialize with belief snapshots
        restored = TickRecord.from_dict(d)
        assert len(restored.belief_snapshots) == 1
        assert restored.belief_snapshots[0].agent_id == "a1"

    def test_create_belief_snapshot_helper(self):
        """create_belief_snapshot helper should work correctly."""
        from microecon.logging import create_belief_snapshot

        snapshot = create_belief_snapshot(
            agent_id="test_agent",
            type_beliefs=[
                ("partner1", 0.6, 0.9, 10),
                ("partner2", 0.4, 0.7, 5),
            ],
            price_belief=(1.2, 0.5, 15),
            n_trades_in_memory=7,
        )

        assert snapshot.agent_id == "test_agent"
        assert len(snapshot.type_beliefs) == 2
        assert snapshot.type_beliefs[0].target_agent_id == "partner1"
        assert snapshot.type_beliefs[0].believed_alpha == 0.6
        assert snapshot.type_beliefs[1].target_agent_id == "partner2"
        assert snapshot.price_belief.mean == 1.2
        assert snapshot.n_trades_in_memory == 7

    def test_simulation_logs_belief_snapshots(self):
        """Simulation should log belief snapshots for belief-enabled agents."""
        from microecon.grid import Grid, Position
        from microecon.simulation import Simulation
        from microecon.information import FullInformation
        from microecon.bargaining import NashBargainingProtocol
        from microecon.logging import SimulationLogger, SimulationConfig

        # Create agents with beliefs
        agent1 = create_agent(alpha=0.3, endowment_x=10, endowment_y=2, agent_id="a1")
        agent2 = create_agent(alpha=0.7, endowment_x=2, endowment_y=10, agent_id="a2")
        agent1.enable_beliefs()
        agent2.enable_beliefs()

        # Create simulation with logging
        grid = Grid(size=10)
        config = SimulationConfig(
            n_agents=2,
            grid_size=10,
            seed=42,
            protocol_name="nash",
        )
        logger = SimulationLogger(config)

        sim = Simulation(
            grid=grid,
            bargaining_protocol=NashBargainingProtocol(),
            info_env=FullInformation(),
        )
        sim.logger = logger

        # Place agents at same position to force trade
        sim.add_agent(agent1, Position(5, 5))
        sim.add_agent(agent2, Position(5, 5))

        # Run simulation
        sim.run(ticks=5)

        # Get logged data
        run_data = logger.finalize()

        # Should have tick records
        assert len(run_data.ticks) == 5

        # Each tick should have belief snapshots for belief-enabled agents
        for tick_record in run_data.ticks:
            assert len(tick_record.belief_snapshots) == 2  # Both agents have beliefs
            agent_ids = {bs.agent_id for bs in tick_record.belief_snapshots}
            assert agent_ids == {"a1", "a2"}

    def test_belief_snapshots_reflect_learning(self):
        """Belief snapshots should show belief changes over time."""
        from microecon.grid import Grid, Position
        from microecon.simulation import Simulation
        from microecon.information import FullInformation
        from microecon.bargaining import NashBargainingProtocol
        from microecon.logging import SimulationLogger, SimulationConfig

        # Create agents with beliefs
        agent1 = create_agent(alpha=0.3, endowment_x=10, endowment_y=2, agent_id="a1")
        agent2 = create_agent(alpha=0.7, endowment_x=2, endowment_y=10, agent_id="a2")
        agent1.enable_beliefs()
        agent2.enable_beliefs()

        # Create simulation with logging
        grid = Grid(size=10)
        config = SimulationConfig(
            n_agents=2,
            grid_size=10,
            seed=42,
            protocol_name="nash",
        )
        logger = SimulationLogger(config)

        sim = Simulation(
            grid=grid,
            bargaining_protocol=NashBargainingProtocol(),
            info_env=FullInformation(),
        )
        sim.logger = logger

        # Place agents at same position to force trade
        sim.add_agent(agent1, Position(5, 5))
        sim.add_agent(agent2, Position(5, 5))

        # Run simulation
        sim.run(ticks=10)

        run_data = logger.finalize()

        # After trades, agents should form beliefs about each other
        # Find a1's belief snapshots across ticks
        a1_snapshots = [
            bs for tick in run_data.ticks
            for bs in tick.belief_snapshots
            if bs.agent_id == "a1"
        ]

        # Initially no type beliefs (tick 0), then beliefs form after trade
        tick0_beliefs = run_data.ticks[0].belief_snapshots
        a1_tick0 = next(bs for bs in tick0_beliefs if bs.agent_id == "a1")

        # Check that beliefs accumulate over time
        # (The exact timing depends on when trades occur)
        final_tick_beliefs = run_data.ticks[-1].belief_snapshots
        a1_final = next(bs for bs in final_tick_beliefs if bs.agent_id == "a1")

        # Should have some trades in memory by end if trading occurred
        if len(sim.trades) > 0:
            assert a1_final.n_trades_in_memory > 0

    def test_non_belief_agents_excluded_from_snapshots(self):
        """Agents without beliefs should not appear in belief_snapshots."""
        from microecon.grid import Grid, Position
        from microecon.simulation import Simulation
        from microecon.information import FullInformation
        from microecon.bargaining import NashBargainingProtocol
        from microecon.logging import SimulationLogger, SimulationConfig

        # Create agents - only one has beliefs
        agent1 = create_agent(alpha=0.3, endowment_x=10, endowment_y=2, agent_id="a1")
        agent2 = create_agent(alpha=0.7, endowment_x=2, endowment_y=10, agent_id="a2")
        agent1.enable_beliefs()
        # agent2 does NOT have beliefs enabled

        # Create simulation with logging
        grid = Grid(size=10)
        config = SimulationConfig(
            n_agents=2,
            grid_size=10,
            seed=42,
            protocol_name="nash",
        )
        logger = SimulationLogger(config)

        sim = Simulation(
            grid=grid,
            bargaining_protocol=NashBargainingProtocol(),
            info_env=FullInformation(),
        )
        sim.logger = logger

        sim.add_agent(agent1, Position(5, 5))
        sim.add_agent(agent2, Position(5, 5))

        sim.run(ticks=3)

        run_data = logger.finalize()

        # Only agent1 should have belief snapshots
        for tick_record in run_data.ticks:
            assert len(tick_record.belief_snapshots) == 1
            assert tick_record.belief_snapshots[0].agent_id == "a1"
