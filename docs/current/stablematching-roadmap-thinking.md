• Here’s how StableRoommatesMatchingProtocol actually forms the initial
  stable match today, and where it collides with the action‑budget shift in
  the roadmap.

  How the initial stable match is formed (current code path)

  - Each tick, Phase 1 builds a visibility map (who can see whom) and
    computes surplus via the active bargaining protocol; this happens
    before matching. microecon/simulation.py:167
  - If StableRoommatesMatchingProtocol is active, Phase 2 gathers
    uncommitted agents only and runs matching. microecon/simulation.py:213
  - Preference lists are built from visible candidates with positive
    surplus, sorted by (surplus desc, id). Surplus is distance‑discounted
    via surplus_fn. microecon/matching.py:214
  - Irving’s algorithm (proposal phase + rotation elimination) runs on
    those lists to produce a stable matching, if it exists; otherwise
    partial matches may result. microecon/matching.py:264
  - Commitments are formed for matched pairs; committed agents move toward
    partners, and only committed + co‑located pairs can trade in Phase 4.
    microecon/simulation.py:241 microecon/simulation.py:357

  So the “initial stable match” isn’t a one‑time global pre‑processing step
  —it’s computed on tick 1 from current visibility and repeated each tick
  for uncommitted agents.

  Where this overlaps with the action‑budget shift

  - The roadmap introduces explicit action exclusivity and consent (trade
    vs move), but stable matching already decides partners centrally and
    then auto‑routes agents toward them, with trade happening automatically
    once co‑located. That’s conceptually similar to “action selection,”
    just institutionalized at a protocol level.
  - The roadmap’s “co‑location resolution” is an explicit, mutual trade
    decision. Stable matching bypasses this by pre‑committing and
    auto‑trading, which makes consent and action exclusivity moot once a
    commitment exists.
  - Stable matching’s preferences already account for distance via
    discounted surplus; the action‑budget model adds a different constraint
    (one action per tick), which isn’t represented in the matching
    preferences.

  Ways to reconcile the two models (options)

  1. Keep stable matching as a commitment protocol; integrate action
     budgets around it.
      - Run stable matching after perception (Phase 0/1), form commitments.
      - Committed agents spend their action moving toward partners.
      - When co‑located, resolve trade via the roadmap’s mutual selection/
        accept rules.
      - Net effect: stable matching still sets intended partners, but trade
        consumes the action slot and is no longer automatic.
  2. Make “commitment” itself an action.
      - Agents choose either to propose/commit or to move in a tick.
      - Stable matching becomes an emergent outcome of repeated proposal
        actions, rather than a centralized Irving step.
      - This is more consistent with action budgets but deviates from
        “stable roommates” as a protocol.
  3. Localize stable matching to co‑located groups only.
      - Use stable matching only to resolve multi‑agent co‑location (who
        trades with whom), and leave long‑range partner selection to
        movement/search.
      - Reduces overlap but changes the meaning of “stable matching” in the
        model.

  If you want, I can sketch a concrete tick‑sequence that preserves stable
  matching while adding action exclusivity (Option 1) and call out the
  exact code touch points.
