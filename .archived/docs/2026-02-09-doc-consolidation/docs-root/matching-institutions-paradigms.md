# Matching Institutions: Paradigms That Fit the Tick Model

This note captures the current “matching gap” discussion and proposes a direction that fits the existing action-budget / 3-phase tick architecture while improving **institutional visibility** for matching.

The core recommendation is a **hybrid** approach:
- Keep agent autonomy in the **Decide** phase (agents submit “intents”).
- Make the **clearing / conflict-resolution rule** explicit and swappable as the matching institution.
- Keep bargaining as a 1-tick “outcome oracle” for now, so matching comparisons stay clean.

---

## 1) Decomposing “matching” into swappable parts

“Matching” is not one mechanism; it is a bundle of choices. Treating these as separate, configurable layers makes matching comparable the same way bargaining protocols are.

1) **Meeting technology** (who can possibly match this tick)
- Examples: co-located only; adjacent (Chebyshev ≤ 1); within radius; random meetings; random within radius; etc.

2) **Submission protocol** (what an agent can do in Decide)
- Examples: one proposal; up to *k* proposals; ranked list; “apply” vs “invite”; mutual-consent handshake; etc.

3) **Clearing / conflict resolution** (how matches are formed from submissions)
- Examples: first-come priority; target chooses best acceptable proposer; maximum-weight matching; deferred acceptance; etc.

This decomposition gives you a clean meaning of “same agents, different matching institution”:
- Hold meeting + submission fixed, vary clearing.
- Or hold clearing fixed, vary meeting technology.

---

## 2) Why a hybrid (decentralized intents + explicit clearing) fits best

The current architecture already *implicitly* implements a matching institution:
- Agents submit intents via `ProposeAction` in `microecon/actions.py`.
- The simulation resolves conflicts in `microecon/simulation.py`:
  - **Mutual proposals** get special handling (immediate trade).
  - Otherwise, the target responds to the first processed proposal; later proposals become “non-selected”.

That last point is important: the effective matching rule is currently **order-sensitive** (an institution in its own right), but it is not expressed as a clean module layer.

Making the clearing rule explicit has three payoffs:
- **Comparability:** same action model, different clearing ⇒ measurable differences in efficiency, networks, welfare.
- **Modularity:** matching becomes swappable like bargaining protocols.
- **Theory grounding:** you can implement a small set of canonical clearing rules without breaking the tick model.

---

## 3) A minimal set of matching institutions that remain 1-tick

These are intentionally “same-tick” rules to stay comparable under the current oracle-bargaining abstraction.

### A. Status quo (baseline institution)
Interpret the current behavior as an institution:
- Directed proposals (adjacent constraint)
- Single proposal per agent per tick
- Conflict resolution with mutual-proposal special case
- Otherwise, effectively “first-processed proposer gets target’s decision”

This is a legitimate baseline, but it bakes in a priority rule that is easy to miss and hard to justify theoretically.

### B. Target-choice clearing (decentralized but less order-dependent)
Keep the same meeting/submission, but change clearing:
- Each target considers *all* incoming proposals in the tick.
- Target chooses the best acceptable proposal (by its decision rule / surplus / opportunity cost).
- Unchosen proposers execute fallback; explicit rejections still trigger cooldown rules as desired.

This preserves autonomy and stays close to “rational target selection,” while removing the “evaluation order” artifact.

### C. Central clearinghouse benchmark (useful even if not the default)
Compute matches centrally as a benchmark, given the same meeting constraints:
- Build a graph of feasible pairs (e.g., adjacency edges).
- Put weights on edges (e.g., predicted surplus, welfare gain, or Nash product improvements).
- Compute a maximum-weight matching and execute those trades.

This breaks pure decentralization, but it provides a powerful reference point:
- “Given the same meeting technology, how much inefficiency comes from decentralized proposal dynamics vs from limited meetings?”

---

## 4) How this interacts with beliefs / information (and why “beliefs in search only” can be coherent)

A consistent interpretation of the current design is:
- **Beliefs matter for approach/search:** who you decide to propose to.
- **Acceptance uses verification:** once adjacent and engaged, the agent can infer enough about the trade to accept/reject based on realized surplus.

If/when you want *incomplete-information bargaining* to be behaviorally real, the pivot question becomes:
- What is revealed at proposal / negotiation time?
- Does bargaining compute outcomes using true types, observed types, or believed types?

Keeping matching modular helps here: you can vary information regimes and matching rules independently, then decide how much “revelation” bargaining provides.

---

## 5) Two questions to resolve now (to pick a path)

1) Should “matching institution” include **meeting technology** as part of the institution, or should meeting be treated as an **environmental constraint** held fixed while varying clearing?

2) Are centralized matching rules acceptable as **benchmarks** (even if not the default), or must all institutions remain agent-autonomous end-to-end?

