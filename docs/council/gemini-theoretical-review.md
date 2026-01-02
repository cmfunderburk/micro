# Gemini Theoretical Review

**Date:** 2026-01-02
**Target:** `src/microecon` and `tests/scenarios`
**Scope:** Consistency with `theoretical-foundations.md` and `VISION.md`

## 1. Executive Summary

The codebase demonstrates a high degree of fidelity to the cited theoretical foundations (Kreps, Osborne & Rubinstein). The core economic primitives—preferences, bargaining solutions, and matching algorithms—are implemented as rigorous mathematical translations of the theory, not merely "agent-based heuristics."

However, a significant **consistency gap** exists in the **Search** module. While the system claims "Institutional Visibility" (swappable rules), the search behavior currently hardcodes **Nash Bargaining expectations**. This means agents in a Rubinstein bargaining economy will incorrectly search as if they were in a Nash bargaining economy. This violates the "Rational Expectations" assumption implicit in the `VISION.md` goal of "Institutional Visibility" unless explicitly framed as a bounded rationality constraint.

## 2. Component Analysis

### 2.1. Preferences (`src/microecon/preferences.py`)
*   **Status:** ✅ **Theoretically Consistent**
*   **Reference:** Kreps I, Ch 2 (Utility), Ch 3 (Demand).
*   **Details:**
    *   Correctly implements Cobb-Douglas utility $u(x,y) = x^\alpha y^{1-\alpha}$.
    *   Derives Marshallian demand and MRS analytically.
    *   Properties (monotonicity, convexity, homotheticity) are preserved.

### 2.2. Bargaining (`src/microecon/bargaining.py`)
*   **Status:** ✅ **Theoretically Consistent**
*   **Reference:** O&R-B Ch 2 (Nash), Ch 3 (Rubinstein).
*   **Nash Implementation:**
    *   Correctly solves $\max (u_1 - d_1)(u_2 - d_2)$ on the Pareto frontier.
    *   Uses Golden Section Search for numerical stability on the contract curve.
*   **Rubinstein Implementation:**
    *   Correctly implements the infinite-horizon Subgame Perfect Equilibrium (SPE) payoff shares: $s_1 = \frac{1-\delta_2}{1-\delta_1\delta_2}$.
    *   **Note:** The implementation calculates the *equilibrium outcome* directly rather than simulating the extensive-form game tick-by-tick. This is valid for creating the *economic outcome* of Rubinstein bargaining under full rationality, which is the stated goal.

### 2.3. Matching (`src/microecon/matching.py`)
*   **Status:** ✅ **Theoretically Consistent**
*   **Reference:** Kreps II Ch 25 (Matching), Irving (1985).
*   **Details:**
    *   **Stable Roommates:** Correctly implements Irving's algorithm (Proposal + Rotation Elimination).
    *   **Opportunistic:** Correctly models "search-and-match" friction where any co-located pair trades.
    *   The distinction effectively captures the difference between "Centralized/Structured" vs "Decentralized/Unstructured" markets.

### 2.4. Search (`src/microecon/search.py`)
*   **Status:** ⚠️ **Inconsistent / Leaky Abstraction**
*   **Issue:**
    *   The function `evaluate_targets` explicitly imports and uses `compute_nash_surplus`.
    *   **Violation:** This decouples the *search expectation* from the *bargaining reality*.
    *   **Scenario:** If the simulation uses `RubinsteinBargainingProtocol` (where patience = power), a patient agent *should* expect a higher surplus and potentially target different partners. Currently, they search assuming a symmetric Nash split.
    *   **Impact:** This undermines the "Institutional Visibility" goal because changing the bargaining institution does *not* change search behavior, only the final payoff. This dampens the visible impact of the institution on market dynamics (clustering, network formation).

### 2.5. Simulation Loop (`src/microecon/simulation.py`)
*   **Status:** ⚠️ **Affected by Search Inconsistency**
*   **Details:**
    *   The `DECIDE` phase (matching) also uses `compute_nash_surplus` for the matching preference lists, regardless of the active protocol.
    *   The `EXCHANGE` phase correctly uses `self.bargaining_protocol.execute()`.

## 3. Review of Tests (`tests/scenarios/`)

The scenario tests provide excellent coverage of the *implemented* behavior but reflect the limitations identified above.

*   `test_hub_and_spoke.py` (Nash): rigorously verifies MRS convergence and surplus properties.
*   `test_trading_chain.py` (Matching):
    *   Crucially demonstrates the welfare gap between Committed (Stable) and Opportunistic matching (~2.2% gain).
    *   This successfully validates the "Institutional Visibility" of **Matching Protocols**.
*   `test_two_agent.py` (Rubinstein):
    *   Verifies the internal logic of the Rubinstein protocol (proposer advantage, convergence to Nash).
    *   **Gap:** There is no test verifying that agents *alter their search targets* based on the Rubinstein protocol, because the current implementation precludes this.

## 4. Recommendations

To fully realize the `VISION.md` goal of "making institutions visible," the search and matching logic must be made "institution-aware."

### 4.1. Refactoring Required
1.  **Update `BargainingProtocol` Interface:** Ensure `compute_expected_surplus(agent1, agent2)` is fully supported by all protocols (already exists in abstract base class).
2.  **Dependency Injection in Search:**
    *   Modify `evaluate_targets` to accept a `surplus_estimator` callable.
    *   In `Simulation.step()`, pass `self.bargaining_protocol.compute_expected_surplus` into `evaluate_targets`.
3.  **Update Matching Logic:**
    *   Similarly, `StableRoommatesMatchingProtocol` should use the active protocol's surplus expectation to build preference lists.

### 4.2. New Verification Scenarios
Once refactored, create a `test_institution_aware_search.py`:
*   **Scenario:** Asymmetric patience ($\delta_A = 0.99, \delta_B = 0.5$).
*   **Expectation:** Under Rubinstein, A should be more "choosy" or B should be more desperate compared to Nash.
*   **Check:** Verify that `best_target_id` changes when switching from Nash to Rubinstein protocol for the same agents.

## 5. Conclusion

The platform is a robust implementation of microeconomic theory with one specific architectural leak. The primitives are sound. Fixing the search/bargaining decoupling will significantly enhance the research value of the platform by allowing bargaining institutions to shape *market structure* (who meets whom), not just *market outcomes* (who gets what).
