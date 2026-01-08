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

## 6. Agent Decision Architecture

### 6.1 Current Decision Structure

Agents currently decide:
1. **Target selection:** Who to approach (discounted surplus)
2. **Match acceptance:** Whether to trade (implicit: yes if surplus > 0)
3. **Bargaining:** Determined by protocol

### 6.2 Expanded Decision Structure

With production/gathering, agents must also decide:
4. **Activity choice:** Produce? Gather? Search for trade? Go home? Consume?
5. **Location choice:** Which resource node? Which market? Specific partner?

### 6.3 Theoretical Approaches to Activity Choice

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

### 6.4 Decision Questions (Open)

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

## 7. Proposed Development Phases

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

## 8. Open Questions Summary

### Protocol Design

| ID | Question | Options | Status |
|----|----------|---------|--------|
| Q1 | TIOLI proposer selection | Random / First-mover / By type / Configurable | **Decided: Configurable** |
| Q2 | Asymmetric Nash β determination | Fixed per agent / Derived / Situational / Configurable | Open |
| Q3 | Nash Demand Game demand representation | Surplus share / Bundle / Exchange rate | Open |
| Q4 | Nash Demand disagreement handling | Walk away / Fallback / Retry | Open |

### Economy Design

| ID | Question | Options | Status |
|----|----------|---------|--------|
| Q5 | Resource node placement | Fixed / Random / Clustered / Configurable | Open |
| Q6 | Resource regeneration | None / Fixed rate / Stochastic / Depletion-recovery | Open |
| Q7 | Activity choice architecture | Full optimization / Hierarchical / Learning / Configurable | Open |
| Q8 | Consumption modeling | Passive / Active depletion / Location-specific | Open |
| Q9 | Location priority | Nodes only / + Homes / Full system | Open |

### Architecture

| ID | Question | Options | Status |
|----|----------|---------|--------|
| Q10 | Search with multiple protocols | Use active protocol / Agent protocol preferences | Open |
| Q11 | Locations: fixed vs emergent | Fixed / Emergent / Hybrid | Open |
| Q12 | Market location mechanics | Definitional / Mechanical / Institutional | Open |

---

## 9. References

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

## 10. Next Steps

1. **Review this document** - Consider open questions, note preferences
2. **Session 2** - Resolve key decisions, prioritize phases
3. **Draft PRD** - Using Ralph Interview protocol once decisions firm
4. **Implementation** - Phased execution per roadmap

---

**Document Version:** 1.0
**Created:** 2026-01-08
**For Review By:** [User]
**Next Session:** TBD
