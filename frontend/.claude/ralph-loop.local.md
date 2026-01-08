---
active: true
iteration: 1
max_iterations: 55
completion_promise: "BILATERAL-PROTOCOLS-EXPANSION-COMPLETE"
started_at: "2026-01-08T22:05:27Z"
---

Execute docs/prd/PRD-BILATERAL-PROTOCOLS-EXPANSION.json systematically.

PHASE ORDER:
1. Core Protocol Implementation (bargaining_power attr, TIOLI, Asymmetric Nash)
2. Theory Tests (O&R Ch 2-3 properties)
3. Server & UI Integration (routing, selector, tooltips, power distribution)
4. Documentation (CLAUDE.md, STATUS.md, docstrings)

Phases 2 and 3 can run in parallel after Phase 1.

CRITICAL REQUIREMENTS:
- TIOLI must use closed-form solution (responder exactly at disagreement utility)
- Asymmetric Nash uses agent.bargaining_power, NOT discount_factor
- Theory tests are PRIMARY verification (research software)
- UI must have tooltips explaining each protocol's power source

NAMING CONVENTION (per ADR-BP-001):
- 'Nash (Symmetric)' - NashBargainingProtocol
- 'Nash (Patience)' - RubinsteinBargainingProtocol
- 'Nash (Power)' - AsymmetricNashBargainingProtocol
- 'Take-It-Or-Leave-It' - TIOLIBargainingProtocol

ESCALATION: Stop if theory tests show divergence > 1e-3 or if TIOLI responder not at indifference.

Track progress via git commits and progress.txt. Update PRD feature passes as completed.
