# Critical Consistency Review (Vision/Theory vs Implementation)

Date: 2026-01-02

Scope:
- Vision and theory: `VISION.md`, `theoretical-foundations.md`
- Status and planning: `STATUS.md`, `docs/SESSION_2026-01-02_dashboard_phase1.md`
- Implementation: core engine modules in `src/microecon/`
- Main theory tests: `tests/scenarios/`

The platform already embodies the core idea of institutional visibility in the matching/bargaining split, and the scenario tests are strong for Nash-based bilateral exchange. The main gaps are where the implementation or tests silently depart from the stated theory, or where the docs over-claim coverage relative to code. The findings below focus on those mismatches.

## High-severity consistency issues

1) Rubinstein implementation is not the canonical alternating-offers model for Cobb-Douglas exchange
- Evidence: `src/microecon/bargaining.py` implements Rubinstein by splitting total *utility gains* using the Rubinstein surplus-share formula and then selecting a Pareto-efficient allocation with those shares.
- Theory tension: The Rubinstein share formula is derived for a linear "pie" bargaining game. For general utility functions, the alternating-offers equilibrium converges to a *weighted Nash solution*, not a fixed share of total gains. That means the current method is a surplus-sharing heuristic, not a faithful alternating-offers solution for Cobb-Douglas utility.
- Document mismatch: `STATUS.md` and comments in `src/microecon/bargaining.py` claim "converges to Nash as patience approaches 1". With asymmetric preferences/endowments, the current implementation does not converge to the Nash solution in general.
- Concrete example (run locally):

```python
# in repo root
python - <<'PY'
import sys
sys.path.append('src')
from microecon.preferences import CobbDouglas
from microecon.bundle import Bundle
from microecon.bargaining import nash_bargaining_solution, rubinstein_bargaining_solution

prefs1 = CobbDouglas(0.2)
prefs2 = CobbDouglas(0.7)
endow1 = Bundle(10.0, 2.0)
endow2 = Bundle(3.0, 9.0)

nash = nash_bargaining_solution(prefs1, endow1, prefs2, endow2)
rub = rubinstein_bargaining_solution(prefs1, endow1, prefs2, endow2, 0.999, 0.999, proposer=1)

print('Nash gain share', nash.gains_1/(nash.gains_1+nash.gains_2))
print('Rub gain share', rub.gains_1/(rub.gains_1+rub.gains_2))
PY
```

- Impact: The protocol comparison in `tests/scenarios/test_two_agent.py` is valid only for symmetric cases; for asymmetric cases, the Rubinstein protocol is not theoretically anchored as documented in `theoretical-foundations.md`.
- Guidance:
  - If the goal is theoretical fidelity, implement a true alternating-offers game (or weighted Nash solution derived from delta) for Cobb-Douglas preferences. [**LEAD DEV NOTE**: The goal is theoretical fidelity, so we should think through implementing this.]
  - ~~If the surplus-sharing heuristic is intentional, explicitly document it in `STATUS.md`, `theoretical-foundations.md`, and the Rubinstein tests, and drop the "converges to Nash" claim.~~

2) Protocol visibility breaks in search and matching
- Evidence: Search and matching evaluate targets using Nash surplus regardless of the bargaining protocol: `src/microecon/search.py` and `src/microecon/simulation.py` call `compute_nash_surplus` directly, and `StableRoommatesMatchingProtocol` ignores distance-discounting entirely.
- Document mismatch:
  - `VISION.md` frames bargaining protocol as a primary institutional variable.
  - `STATUS.md` acknowledges the search limitation but does not mention that matching ignores distance discounting and bargaining protocol. [**LEAD DEV NOTE:**: ignoring distance-discounting is unintentional and should be fixed; bargaining protocol is intentionally ignored, pending updates/fixes to the Rubinstein protocol and a more rigorous thinking-through of how the search/match system should work. Specifically, there's an informational question to address: we don't want agents to be able to "bargain-in-advance", so to speak, before they are within trading distance. The movement decision has to be made, in many cases, when agents are distant from each other (though within perception radius), before any bargaining has occurred. So they need theoretically-sound ways to make a choice about who to choose to move to without knowing the bargaining result ahead of time.]
- Impact:
  - In practice, protocol comparison is incomplete: bargaining protocol only affects the *division* of gains at trade time, not partner selection, matching, or path dynamics.
  - This undermines the "institutional visibility" claim for bargaining protocols.
- Guidance:
  - Replace Nash-only surplus calls with `bargaining_protocol.compute_expected_surplus(...)` in both search and matching.
  - Decide whether matching preferences should be distance-discounted (as described in `docs/DESIGN_matching_protocol.md`) and implement accordingly or update the design doc.

3) Rubinstein proposer advantage depends on iteration order, not economic initiation
- Evidence: `src/microecon/simulation.py` sets the proposer as the agent in the outer loop, which is effectively the insertion order of `self.agents` (often lexicographic in tests).
- Theory tension: In Rubinstein, the proposer is a strategic first mover, not an artifact of loop order. The current implementation ties proposer advantage to deterministic iteration rather than to a modeled strategic role or movement decision.
- Impact: In opportunistic trade or crowded co-location, proposer advantage becomes a deterministic but arbitrary bias rather than a modeled institution.
- Guidance:
  - Define proposer based on the movement target (initiator) or randomize proposer to avoid deterministic bias, and document the choice.

## Medium-severity consistency issues

4) Stable roommates stability claims overstate algorithm guarantees
- Evidence: `StableRoommatesMatchingProtocol` uses preference lists truncated by visibility and positive-surplus filters (`src/microecon/matching.py`). This is a *stable roommates with incomplete lists* variant.
- Document mismatch: `STATUS.md` states "Produces stable matching (no blocking pairs)." With incomplete lists and perception constraints, classical stability guarantees do not directly apply.
- Guidance: Update `STATUS.md` to note stability is conditional (when a stable matching exists under truncated preferences) and that outcomes may be partial.

5) Status says "toroidal grid" but the default is bounded
- Evidence: `Grid` defaults to `wrap=False` in `src/microecon/grid.py`, and tests assume non-wrapping behavior (`tests/test_grid.py`).
- Document mismatch: `STATUS.md` describes `grid.py` as "NxN toroidal grid".
- Guidance: Clarify the default in `STATUS.md` and optionally call out that wrap is configurable.

6) Session doc contradicts current logging implementation
- Evidence: `docs/SESSION_2026_01_02_matching_implementation.md` claims commitment events are defined but not wired. The code now logs commitment events in `src/microecon/simulation.py` and `src/microecon/logging/events.py`.
- Impact: The session document is stale relative to the codebase; it will mislead anyone planning next steps.
- Guidance: Update the session doc or add a short correction note.

7) Duplicate commitment event types in two modules
- Evidence: `src/microecon/matching.py` defines commitment event dataclasses (with tick), while `src/microecon/logging/events.py` defines separate commitment event dataclasses (without tick). Tests reference both (`tests/test_matching.py` uses the matching module versions).
- Impact: Confusion over which event type is authoritative; logging and matching code may drift.
- Guidance: Consolidate to a single set of commitment event types (preferably in logging/events) or explicitly separate responsibilities in docs.

## Scenario test coverage gaps vs theory

8) Scenario tests do not validate non-symmetric Rubinstein outcomes
- Evidence: `tests/scenarios/test_two_agent.py` checks Rubinstein shares for symmetric alphas only.
- Impact: The tests do not catch the lack of Nash convergence for asymmetric preferences, so the theoretical claim is unverified.
- Guidance: Add a Rubinstein test with asymmetric preferences/endowments and verify expected behavior (either weighted Nash or documented heuristic).

9) Theoretical tests index is out of sync with actual test layout
- Evidence: `THEORETICAL_TESTS.md` references `tests/test_theoretical_scenarios.py`, but the scenarios live under `tests/scenarios/`.
- Impact: Readers will look in the wrong place; counts and class names in the doc are likely outdated.
- Guidance: Update `THEORETICAL_TESTS.md` to reflect the current files and scope.

10) Matching preferences ignore spatial costs in committed mode
- Evidence: `StableRoommatesMatchingProtocol` ignores travel time (distance) despite the design doc's stated goal of distance-discounted preferences (`docs/DESIGN_matching_protocol.md`).
- Impact: Committed matching may form pairs that are theoretically optimal in surplus but infeasible or costly in spatial terms, muting the intended institutional visibility of search frictions.
- Guidance: Either incorporate distance discounting in `surplus_fn` for matching or revise the design docs to indicate matching is distance-blind.

## Recommendations for 0.0.1 alpha guidance

1) Clarify the Rubinstein protocol in docs
- Either (a) implement alternating-offers with weighted Nash foundations, or (b) explicitly present the current implementation as a surplus-sharing heuristic with transferable-utility assumptions.
- Update claims in `STATUS.md` and `src/microecon/bargaining.py` accordingly.

2) Make search/matching protocol-aware
- Use `BargainingProtocol.compute_expected_surplus` in `src/microecon/search.py` and `src/microecon/simulation.py`.
- Consider whether `MatchingProtocol.compute_matches` should accept a surplus function that already reflects distance discounting and protocol-specific gains.

3) Fix documentation drift
- Update `STATUS.md` (grid wrap, stability conditions, search/matching limitations).
- Update `THEORETICAL_TESTS.md` to match the actual test layout and counts.
- Note in `docs/SESSION_2026_01_02_matching_implementation.md` that commitment events are now wired.

4) Strengthen scenario tests for theory alignment
- Add asymmetric Rubinstein cases.
- Add a test that explicitly checks matching behavior with distance-discounted surplus (if intended).
- Add tests verifying that bargaining protocol choice changes target selection once search is protocol-aware.

## Positive alignment notes

- The Nash bargaining solution and Cobb-Douglas utility tests are strong and match the theoretical foundations for two-good exchange (`tests/scenarios/test_two_agent.py`, `tests/scenarios/test_trading_chain.py`).
- The matching protocol abstraction directly supports the core "institutional visibility" goal in `VISION.md`.
- The scenario tests explicitly distinguish competitive equilibrium vs bilateral exchange equilibrium in the hub-and-spoke scenarios, which aligns well with micro theory.

---

If you want, I can convert the guidance into concrete issue tickets (or patch the docs and tests) in a follow-up.
