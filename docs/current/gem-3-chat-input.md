This is a robust roadmap. The shift from "Exchange Exhaustion" to a "Sustained Economy" is the critical pivot that moves `VMT` from a study of **convergence** (how quickly do we hit the contract curve?) to a study of **dynamics** (stationarity, cycles, and flow).

Based on your *Vision* of "Institutional Visibility" and the open questions in the *Roadmap*, here is a structured breakdown to help us resolve the open design decisions.

### 1. Protocol Design: Defining "Power" and "Coordination"

The expansion of bilateral protocols is excellent for comparative statics.

**Q2: Asymmetric Nash () Determination**

* **Analysis:** If  is purely random, it adds noise. If it is fixed per agent, it models "inherent bargaining skill." However, to serve *Institutional Visibility*,  should arguably be structural or derived.
* **Recommendation:** **Derived from Attributes (with override).**
* In the *Rubinstein* limit, bargaining power is a function of patience ().
* For *Asymmetric Nash* to be a useful benchmark against Rubinstein,  should default to being derived from the ratio of discount factors:  (or similar approximation).
* *Alternatively:* Make it **Situational**. The "initiator" (who paid the search cost) gets . This creates a fascinating incentive to *move* versus *wait*.



**Q3 & Q4: Nash Demand Game Mechanics**

* **Analysis:** In a continuous goods space, demanding a specific bundle is computationally heavy (infinite strategy space).
* **Recommendation:** **Demand a Share of Surplus ().**
* Agents observe the Edgeworth box (via the protocol). They simultaneously submit a demand .
* If , trade executes at those shares.
* **Disagreement (Q4):** **Walk Away (No Trade).** This is essential. If they can just "retry," it becomes a negotiation. The theoretical power of the Demand Game is the risk of total coordination failure (gains = 0).



---

### 2. The Sustained Economy: Closing the Loop

This is the most complex transition. We need to avoid building a "Sims" survival game and ensure we are building an economic model.

**Q8: Consumption Modeling**

* **Analysis:**
* *Active Consumption* requires an arbitrary "hunger" logic.
* *Location-Specific* adds spatial constraints too early.


* **Recommendation:** **Passive Decay (Depletion).**
* At the end of every tick (or  ticks), holdings decay by a small percentage ().
* *Why:* This creates a constant "negative pressure" or explicit cost of time. It forces trade not just to maximize utility, but to maintain stationarity. It naturally aligns with the Cobb-Douglas preference for balance—if Good X decays faster, the MRS shifts dynamically.



**Q7: Activity Choice Architecture**

* **Analysis:** Full optimization (Bellman equations) is too computationally expensive for Phase B.
* **Recommendation:** **Hierarchical Heuristic (Needs-Based).**
* **Priority 1 (Survival):** If , enter **Gather** mode.
* **Priority 2 (Improvement):** If , enter **Search/Trade** mode.
* This provides a baseline "rationality" without complex look-ahead. It allows you to test if market structures can support a population above the survival threshold.



---

### 3. Spatial Structure: The Minimum Viable Economy

**Q5 & Q6: Resource Nodes**

* **Recommendation:** **Fixed Locations, Finite Capacity, Regenerating.**
* Place fixed "Groves" (Good X) and "Mines" (Good Y).
* Nodes have a stock level. Agents extract. Stock regenerates linearly or logistically.
* *Why:* This introduces **crowding externalities**. If too many agents gather at the same node, the yield per agent drops (or the node depletes). This creates an economic incentive to *trade* rather than *gather*—trade becomes the technology for avoiding congestion costs.



**Q9: Location Priority**

* **Recommendation:** **Option A (Nodes Only).**
* Skip "Homes" for now. Homes introduce "storage" vs "inventory" problems.
* Keep it simple: You carry what you own. You gather at nodes. You trade anywhere. This is sufficient to generate the "Trading Chain" or "Market Hub" emergence patterns you are looking for.



---

### Summary of Proposed Decisions for Implementation

| Decision | Proposed Resolution | Rationale |
| --- | --- | --- |
| **Protocol: ** | **Situational** (Initiator gets advantage) | Incentivizes search; distinct from Rubinstein patience. |
| **Protocol: Demand Game** | **Surplus Share** + **Walk Away** | Tests coordination failure risk cleanly. |
| **Consumption** | **Passive Decay** | Creates constant demand without complex "eating" AI. |
| **Activity Choice** | **Heuristic (Threshold)** | "Gather if poor, Trade if rich." Simple baseline. |
| **Space** | **Fixed Nodes, No Homes** | Focuses dynamics on the *trade-off* between gathering and trading. |

**Does this set of resolutions align with your intuition?** If so, we can move to outlining the specific `AgentPrivateState` changes needed for Phase B.
