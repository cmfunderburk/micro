# Roadmap Discussion: Bilateral Protocols & Sustained Economies

**Date:** 2026-01-08
**Status:** Options document for review
**Purpose:** Capture strategic discussion on next development directions, pending decisions

---

## 1. Context

The current implementation provides a solid foundation:
- Core exchange mechanics (preferences, bundles, bargaining, search, matching)
- Two bargaining protocols (Nash, Rubinstein) with comparison mode
- Information environments (Full, NoisyAlpha)
- Belief system (price beliefs, type beliefs)
- Rich visualization and analysis infrastructure

This document explores two interconnected expansion directions:
1. **Bilateral protocol breadth** - More bargaining mechanisms for institutional comparison
2. **Sustained economies** - Production/gathering to enable ongoing exchange

---

## 2. Bilateral Bargaining Protocol Expansion

### 2.1 Currently Implemented

| Protocol | Type | Key Property | Reference |
|----------|------|--------------|-----------|
| Nash Bargaining | Axiomatic | Symmetric, efficient, IIA | O&R Ch 2 |
| Rubinstein | Strategic (SPE) | Patience = power, first-mover advantage | O&R Ch 4 |

### 2.2 Proposed Additions

#### TIOLI (Take-It-Or-Leave-It)

**Mechanism:**
- Proposer makes single offer
- Responder accepts (trade) or rejects (disagreement point)
- No counter-offers

**Theoretical significance:**
- Extreme commitment power
- Proposer extracts maximal surplus consistent with responder's participation constraint
- Tests what happens when one party has all bargaining power

**Design decision (resolved):**
- Who proposes? **Configurable parameter**
  - Random (coin flip)
  - First-mover (who initiated meeting)
  - By type (e.g., higher α proposes)
  - Fixed role per agent

**Reference:** O&R Bargaining, Ch 3

---

#### Kalai-Smorodinsky Solution

**Mechanism:**
- Axiomatic solution like Nash
- Replace Independence of Irrelevant Alternatives (IIA) with monotonicity
- Outcome: Point on Pareto frontier where ratio of gains equals ratio of maximal possible gains

**Theoretical significance:**
- Alternative fairness concept
- More sensitive to bargaining set shape than Nash
- Same information requirements as Nash (full knowledge of preferences)

**Comparison value:**
- When do Nash and K-S diverge significantly?
- Which better predicts observed behavior?

**Reference:** Kalai & Smorodinsky (1975), O&R Ch 2

---

#### Asymmetric Nash Bargaining

**Mechanism:**
- Generalization of Nash with bargaining power parameter β ∈ (0,1)
- Maximize: (u_A - d_A)^β × (u_B - d_B)^(1-β)
- β = 0.5 recovers symmetric Nash

**Theoretical significance:**
- Bargaining power as explicit parameter
- Can represent institutional advantages, outside options, patience differences
- Connects to Rubinstein (limiting case as discount factors vary)

**Comparison value:**
- Core to institutional visibility: power becomes a parameter
- Can study how power distribution affects welfare, network formation, spatial patterns

**Design question (open):**
- How is β determined?
  - Fixed per agent (intrinsic power)
  - Derived from other parameters (patience, outside options)
  - Situational (who approached whom)
  - Configurable

**Reference:** O&R Ch 2, standard in labor economics

---

#### Nash Demand Game

**Mechanism:**
- Simultaneous move game
- Each agent states a demand (share of surplus)
- If demands compatible (sum ≤ total), trade at stated terms
- If incompatible (sum > total), no trade (disagreement)

**Theoretical significance:**
- Tests coordination without communication
- Multiple equilibria (any split is an equilibrium)
- Focal points matter

**Comparison value:**
- Very different from sequential protocols
- How do agents coordinate?
- Does learning lead to conventions?

**Design questions (open):**
- What's the "demand" exactly?
  - Share of surplus (0 to 1)
  - Specific bundle
  - Exchange rate
- How is disagreement resolved?
  - Walk away (no trade)
  - Fall back to different protocol
  - Retry?

**Reference:** Nash (1953), game theory texts

---

### 2.3 Protocol Comparison Matrix

| Protocol | Power Distribution | Information Required | Strategic Complexity | Efficiency |
|----------|-------------------|---------------------|---------------------|------------|
| Nash | Symmetric | Full (preferences) | None (axiomatic) | Pareto optimal |
| Rubinstein | Patience-weighted | Full + discount factors | High (SPE) | Pareto optimal |
| TIOLI | Proposer takes all | Full | Low | Pareto optimal |
| K-S | Symmetric | Full | None (axiomatic) | Pareto optimal |
| Asymmetric Nash | β-weighted | Full + power parameter | None (axiomatic) | Pareto optimal |
| Nash Demand | Emergent | Partial? | Medium (coordination) | May fail |

### 2.4 Implementation Considerations

**Shared infrastructure:**
- All protocols take: two agents, their preferences, endowments, disagreement point
- All return: trade outcome (bundles exchanged) or no-trade

**Protocol-specific needs:**
- TIOLI: proposer selection rule
- Asymmetric Nash: β determination rule
- Nash Demand: demand representation, compatibility check

**Search integration:**
- Currently search uses Nash surplus for target evaluation
- With multiple protocols: use active protocol's predicted surplus?
- Or: agents have protocol preferences and seek compatible partners?

---

## 3. The Exchange Exhaustion Problem

### 3.1 Current Limitation

The current model is a **finite game**:

```
Initialize(endowments) → Search → Match → Bargain → Trade → ... → Exhaustion → Stasis
```

Without resource regeneration, the simulation converges to a state where:
1. All agents have traded to contract curve (no more mutually beneficial trades), or
2. Agents are spatially separated with no reachable partners

**Consequence:** Cannot study:
- Repeat relationships (nothing to trade after first exchange)
- Network evolution over time
- Sustained "market-like" activity
- Long-run learning effects

### 3.2 What Production/Gathering Enables

With resource acquisition:

```
Initialize → [Produce/Gather] → Search → Match → Bargain → Trade → [Consume?] → Loop
```

This creates a **sustained economy** where:
- Agents regularly acquire heterogeneous goods
- Trade opportunities regenerate
- Networks can evolve over time
- Learning has time to show effects
- Spatial patterns can emerge and persist

---

## 4. Production and Gathering: Theoretical Grounding

### 4.1 Production (Kreps I, Ch 7-9)

**Core concept:** Transformation of inputs to outputs via production function.

**For 2-good economy:**
- Agent can transform good X into good Y (or vice versa)
- Production function: y = f(x) with standard properties
- Heterogeneous production capabilities create comparative advantage

**Gains from specialization:**
- Even with identical preferences, different production functions create trade gains
- Connects to classical trade theory (Ricardo)

**Design questions:**
- Discrete or continuous production?
- Location-specific (production sites) or anywhere?
- Time cost of production?
- Stochastic yields?

### 4.2 Gathering/Harvesting

**Core concept:** Resource extraction from environment.

**Mechanism:**
- Resource nodes exist at grid locations
- Agents at node can extract goods
- Extraction rate may depend on: time spent, agent skill, node richness, crowding

**From VMT reference:**
- "Crude harvesting mechanic" - agents gather resources from locations
- Makes spatial positioning meaningful beyond search

**Design questions:**
- Do resources regenerate? At what rate?
- Common pool (competitive extraction) or private access?
- Does gathering deplete nodes temporarily?
- Heterogeneous node types (X-rich vs Y-rich)?

### 4.3 Consumption

**Current state:** Utility computed but goods not "consumed" - holdings persist.

**Options:**

| Approach | Mechanism | Implication |
|----------|-----------|-------------|
| No consumption | Holdings persist | One-shot economy (current) |
| Passive decay | Holdings deplete over time | Creates ongoing need |
| Active consumption | Agents choose to consume | Intertemporal choice |
| Location-specific | Consume only at home | Spatial anchor |

**Theoretical grounding:**
- Consumption is fundamental to utility theory
- Intertemporal consumption: Kreps I, Ch 5-6
- Household production: Becker (1965)

---

## 5. The Locations Concept

### 5.1 Current Grid: Undifferentiated Space

Every cell is identical. Space matters only for:
- Search friction (must be within perception radius)
- Movement cost (takes time to traverse)

### 5.2 Differentiated Space: Location Types

| Location Type | Function | What Happens There | Theoretical Basis |
|---------------|----------|-------------------|-------------------|
| **Resource Node** | Extraction | Agents gather goods | Resource economics |
| **Home** | Anchor | Rest, storage, consumption | Household production |
| **Production Site** | Transformation | Agents produce goods | Theory of the firm |
| **Market** | Exchange facilitation | Reduced search friction, trading advantages | Market microstructure |

### 5.3 Design Questions

#### Are locations fixed or emergent?

| Approach | Description | Implication |
|----------|-------------|-------------|
| Fixed | Placed at initialization | Exogenous geography, study adaptation |
| Emergent | Become locations through use | Endogenous market formation |
| Hybrid | Resources fixed, markets emergent | Mixed dynamics |

#### What makes a "market"?

Options:
- **Definitional:** Where agents congregate to trade (no special mechanics)
- **Mechanical:** Reduced search cost, larger perception radius at location
- **Institutional:** Different matching/bargaining rules at markets (e.g., posted prices)

#### What do "homes" provide?

Options:
- Storage (inventory beyond carried goods)
- Consumption site (utility realized only at home)
- Safety (cannot be approached while at home)
- Production (home production function)
- Respawn point (if agents can "fail")

### 5.4 Spatial Configuration Questions

- How many resource nodes? Distribution?
- Do agents start with homes? Choose homes? Homes assigned?
- Can agents create new locations (build production site)?
- Movement costs between locations vs. open grid?

---

## 6. Tick Model and Action Budget

### 6.1 Current Tick Structure (Problem)

The current implementation has a four-phase tick:
```
EVALUATE → DECIDE → MOVE → EXCHANGE
```

**Issue 1: Move AND Trade in same tick.** Agents move in Phase 3, then trade in Phase 4 if co-located. This means agents don't face a real choice between moving and trading.

**Issue 2: Automatic trade trigger.** Co-location + positive surplus = trade. No consent mechanism; no option to decline a co-located trade to pursue better opportunities.

**Issue 3: No action exclusivity.** With future additions (gathering, production), we need a model where agents choose ONE action per tick.

### 6.2 Revised Tick Model (Decided)

```
PHASE 0: PERCEPTION (free, all agents)
─────────────────────────────────────
For each agent A:
  • Observe all agents within perception_radius
  • Compute expected_surplus(A, B) for each visible B
  • Identify co-located set: {B : distance(A, B) = 0}
  • Identify rejection_cooldown set: {B : A rejected by B within last K ticks}

PHASE 1: CO-LOCATION RESOLUTION (mandatory before other actions)
────────────────────────────────────────────────────────────────
1. Identify all co-located groups

2. For each agent A with co-located partners:
   • Eligible partners = co-located − rejection_cooldown
   • If any eligible partner has expected_surplus > 0:
     → A selects preferred: argmax_{B ∈ eligible} expected_surplus(A, B)
     → A marks intent: ENGAGE
   • Else:
     → A marks intent: DECLINE (proceed to Phase 2)

3. Match selections (simultaneous resolution):
   • MUTUAL MATCH: A selected B AND B selected A
   • NO MATCH: otherwise

4. For each MUTUAL MATCH (A, B):
   • Proposer = agent with higher expected_surplus
   • Proposer makes offer via bargaining protocol
   • Responder decides: ACCEPT or REJECT
     → ACCEPT: Trade executes. Both agents DONE for this tick.
     → REJECT: No trade. Rejection recorded (cooldown starts).
               Both agents proceed to Phase 2.

5. Agents not in mutual match proceed to Phase 2

PHASE 2: ACTION SELECTION (agents not DONE)
───────────────────────────────────────────
Each agent selects ONE action:
  • MOVE(target): Move toward target position
  • WAIT: Do nothing
  • (Future) GATHER: Extract resources at current location
  • (Future) PRODUCE: Transform goods at current location

Note: TRADE is not available here—only in Phase 1

PHASE 3: EXECUTION
──────────────────
• All MOVE actions execute (respecting movement_budget)
• All GATHER/PRODUCE actions execute
• Crossing detection (agents moving toward each other meet)
```

### 6.3 Key Design Decisions

| Decision | Resolution | Rationale |
|----------|------------|-----------|
| **Proposer determination** | Higher expected_surplus agent | Reveals preference intensity; configurable later |
| **Multi-agent co-location** | Simultaneous partner selection | Cleaner than sequential; configurable later |
| **Rejection cooldown** | 3 ticks | Prevents degenerate loops; institutional variable |
| **Declining cost** | Free | Agent can decline co-located trade to pursue distant partner; explore later |

### 6.4 Properties of This Model

**Action exclusivity:** Agent does exactly ONE of {Trade, Move, Gather, Produce, Wait} per tick.

**Co-location priority:** Must resolve co-located opportunities before other actions. But can decline if no positive surplus or prefer distant option.

**Consent required:** Trade requires MUTUAL MATCH + ACCEPT. Three opt-out points: DECLINE (don't engage), no mutual selection, REJECT proposal.

**No infinite loops:** Rejection cooldown prevents repeated unwanted engagement.

**Clean extension:** Gather/Produce slot into Phase 2 as alternatives to Move.

### 6.5 Institutional Variables (Flagged for Future Configuration)

These parameters are currently fixed but represent potential research variables:

| Parameter | Current | Alternatives to Explore |
|-----------|---------|------------------------|
| Proposer rule | Higher surplus | Random, initiator advantage, by type |
| Cooldown duration | 3 ticks | 1-5 ticks, or adaptive |
| Declining cost | Free | Partial action cost |
| Multi-agent resolution | Simultaneous | Sequential, priority-based |

---

## 7. Agent Decision Architecture

### 7.1 Current Decision Structure

Agents currently decide:
1. **Target selection:** Who to approach (discounted surplus)
2. **Match acceptance:** Whether to trade (implicit: yes if surplus > 0)
3. **Bargaining:** Determined by protocol

### 7.2 Expanded Decision Structure

With production/gathering, agents must also decide:
4. **Activity choice:** Produce? Gather? Search for trade? Go home? Consume?
5. **Location choice:** Which resource node? Which market? Specific partner?

### 7.3 Theoretical Approaches to Activity Choice

#### Option A: Full Optimization

- Compute expected utility of each activity
- Choose highest expected value
- **Requirements:** Beliefs about production yields, trade opportunities, travel costs
- **Theoretical grounding:** Standard decision theory, Kreps I Ch 2-4
- **Complexity:** High - requires sophisticated belief formation

#### Option B: Hierarchical Needs

- If low on essential good, prioritize acquiring it
- If holdings sufficient, optimize for utility gains
- **Example hierarchy:** Survival → Accumulation → Optimization
- **Theoretical grounding:** Less standard, but connects to subsistence constraints
- **Complexity:** Medium - requires defining thresholds

#### Option C: Rule-Based with Learning

- Start with simple heuristics ("if hungry, gather")
- Learn which activities pay off
- Adapt rules over time
- **Theoretical grounding:** Behavioral economics, bounded rationality
- **Complexity:** Variable - depends on learning rule sophistication

#### Option D: Configurable (Recommended?)

- Activity choice architecture as swappable module (like bargaining protocol)
- Can compare: optimizing agents vs. heuristic agents vs. learning agents
- **Aligns with:** VISION.md emphasis on institutional/behavioral comparison
- **Complexity:** Higher implementation, but enables research flexibility

### 7.4 Decision Questions (Open)

**Q7: Activity choice architecture**
- (a) Full optimization
- (b) Hierarchical needs
- (c) Learning/heuristic
- (d) Configurable (multiple options)

**Q8: Consumption modeling**
- (a) Passive (utility computed, holdings persist)
- (b) Active (holdings deplete, ongoing need)
- (c) Location-specific (consume at home)

**Q9: Location implementation priority**
- (a) Just resource nodes (minimal sustained economy)
- (b) Resource nodes + homes (spatial anchors)
- (c) Full system (resources, homes, markets, production)

---

## 8. Proposed Development Phases

### Phase A: Bilateral Protocol Expansion

**Scope:** TIOLI, Kalai-Smorodinsky, Asymmetric Nash, Nash Demand Game

**Why first:**
- Relatively contained
- Extends existing infrastructure
- Enables immediate comparison research
- Doesn't require sustained economy

**Deliverables:**
- Four new protocol implementations
- Protocol comparison scenarios
- Updated analysis tools

---

### Phase B: Production/Gathering Foundation

**Scope:** Resource nodes, gathering mechanic, minimal activity choice

**Purpose:** Enable sustained economies

**Minimal implementation:**
- Resource nodes placed on grid (fixed locations)
- Gathering: agent at node can extract goods (time-based or action-based)
- Activity choice: simple heuristic (gather if low, trade if opportunity)
- Resource regeneration (configurable rate)

**Deliverables:**
- Resource node infrastructure
- Gathering mechanic
- Basic activity choice
- Scenarios demonstrating sustained exchange

---

### Phase C: Richer Spatial Structure

**Scope:** Homes, production sites, market locations

**Purpose:** Full spatial economy

**Implementation:**
- Home locations (agent anchors)
- Production sites (transformation)
- Market locations (exchange facilitation)
- Fuller activity choice architecture

**Deliverables:**
- Location type system
- Production mechanics
- Market location effects
- Complex spatial scenarios

---

### Phase D: Emergence Analysis

**Scope:** Tools and scenarios for studying emergence

**Focus areas:**
- Network metrics (clustering, degree distribution, path length)
- Spatial clustering (autocorrelation, hotspot detection)
- Learning dynamics (belief convergence, partner preferences)
- Cross-protocol comparison with sustained economy

**Deliverables:**
- Analysis module extensions
- Emergence visualization overlays
- Benchmark scenarios for each phenomenon
- Documentation of emergence patterns

---

## 9. Open Questions Summary

### Protocol Design

| ID | Question | Options | Status |
|----|----------|---------|--------|
| Q1 | TIOLI proposer selection | Random / First-mover / By type / Configurable | **Decided: Configurable** |
| Q2 | Asymmetric Nash β determination | Fixed per agent / Derived / Situational / Configurable | **Decided: Per-agent w_i, β = w_i/(w_i+w_j)** — configurable per scenario; can derive from δ or make situational later |
| Q3 | Nash Demand Game demand representation | Surplus share / Bundle / Exchange rate | **Decided: Surplus share** — scalar s_i ∈ [0,1], compatible if s_A + s_B ≤ 1 |
| Q4 | Nash Demand disagreement handling | Walk away / Fallback / Retry | **Decided: Walk away** — preserves coordination failure content |

### Economy Design

| ID | Question | Options | Status |
|----|----------|---------|--------|
| Q5 | Resource node placement | Fixed / Random / Clustered / Configurable | **Decided: Fixed** — scenario-specified; random as optional mode for robustness |
| Q6 | Resource regeneration | None / Fixed rate / Stochastic / Depletion-recovery | **Decided: Fixed rate with cap** — standard renewable resource; depletion-recovery later |
| Q7 | Activity choice architecture | Full optimization / Hierarchical / Learning / Configurable | **Decided: Heuristic first** — "gather if low, trade if opportunity" behind swappable interface |
| Q8 | Consumption modeling | Passive / Active depletion / Location-specific | **Decided: Active depletion** — either fixed consumption or % decay; breaks one-shot dynamics |
| Q9 | Location priority | Nodes only / + Homes / Full system | **Decided: Nodes only** — minimal sustained economy first; homes/markets later |

### Architecture

| ID | Question | Options | Status |
|----|----------|---------|--------|
| Q10 | Search with multiple protocols | Use active protocol / Agent protocol preferences | **Decided: Use active protocol** — search evaluates using protocol's surplus; preferences later |
| Q11 | Locations: fixed vs emergent | Fixed / Emergent / Hybrid | **Decided: Fixed** — for resources; markets may emerge definitionally |
| Q12 | Market location mechanics | Definitional / Mechanical / Institutional | **Decided: Definitional first** — markets are where agents congregate; mechanical effects later |

### Tick Model (New)

| ID | Question | Options | Status |
|----|----------|---------|--------|
| Q13 | Action exclusivity | Move+Trade same tick / Mutually exclusive | **Decided: Mutually exclusive** — one action per tick |
| Q14 | Trade trigger | Auto (co-location + surplus) / Consent required | **Decided: Consent required** — mutual selection + proposal + acceptance |
| Q15 | Proposer determination (co-location) | Random / Higher surplus / Initiator / Configurable | **Decided: Higher surplus** — configurable later |
| Q16 | Multi-agent co-location | Sequential pairwise / Simultaneous selection | **Decided: Simultaneous selection** — configurable later |
| Q17 | Rejection cooldown | None / Fixed ticks / Adaptive | **Decided: 3 ticks** — institutional variable |
| Q18 | Declining cost | Free / Partial action cost | **Decided: Free** — explore later |

---

## 10. References

### Canonical Sources

- **Kreps I (Microeconomic Foundations I: Choice and Competitive Markets)**
  - Ch 2-4: Consumer choice
  - Ch 5-6: Intertemporal choice
  - Ch 7-9: Production

- **Osborne & Rubinstein (Bargaining and Markets)**
  - Ch 2: Axiomatic bargaining (Nash, K-S, Asymmetric)
  - Ch 3: Strategic bargaining introduction
  - Ch 4: Rubinstein alternating offers

- **Nash (1950, 1953)**
  - "The Bargaining Problem" - axiomatic solution
  - "Two-Person Cooperative Games" - demand game

- **Kalai & Smorodinsky (1975)**
  - "Other Solutions to Nash's Bargaining Problem"

### Additional Sources (To Consult)

- Becker (1965) - Household production theory
- Resource economics texts - Common pool extraction
- Network economics - Trade network formation
- Market microstructure - Location and market formation

---

## 11. Next Steps

1. ~~**Review this document** - Consider open questions, note preferences~~ ✓
2. ~~**Session 2** - Resolve key decisions~~ ✓ (18 questions resolved)
3. **Remaining discussions:**
   - Finalize consumption model specifics (fixed rate vs % decay)
   - Crowding externalities at resource nodes (GPT-5.2/Gemini both flagged)
   - Nash Demand Game: how agents form demands (beliefs? focal points? learning?)
4. **Draft PRD** - Using Ralph Interview protocol once remaining items resolved
5. **Implementation** - Phased execution per roadmap

---

**Document Version:** 2.0
**Created:** 2026-01-08
**Updated:** 2026-01-08 (Session 2)
**Status:** Most design questions resolved; ready for PRD drafting after final items

### Change Log

**v2.0 (Session 2):**
- Added Section 6: Tick Model and Action Budget (new architecture)
- Resolved Q2-Q18 based on discussion and external review
- Added tick model institutional variables table
- Renumbered sections 7-11
