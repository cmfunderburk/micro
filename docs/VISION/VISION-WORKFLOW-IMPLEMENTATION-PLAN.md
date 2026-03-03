# Vision Workflow Implementation Plan

**Status:** Draft  
**Version:** 0.1  
**Date:** 2026-02-18  
**Primary Target:** `docs/VISION/VISION-WORKFLOW-MASTER-SPEC.md` (v0.2, 2026-02-13)

---

## 1. Purpose

This document is the execution plan for moving the current Microecon codebase to the master spec target state.

It defines:
- current-state blockers and gaps
- delivery gates and exit criteria
- concrete workstreams and dependencies
- validation and quality controls
- governance needed to keep implementation and documentation aligned

This is an implementation plan, not a product vision replacement.

---

## 2. Planning Scope

### In Scope
- All work required to satisfy master-spec Gates A/B/C
- Runtime architecture, contracts, backend services, frontend workflows, analytics, and publication artifacts
- Determinism, replay fidelity, provenance, and compatibility policy
- Educational and research workflow completion

### Out of Scope (for this plan)
- New economic domains beyond current exchange focus
- Production-grade auth, multi-tenant account systems, and external collaboration SaaS features
- Major macroeconomic expansion work

---

## 3. Evidence Baseline (Current State)

This plan is grounded in direct code and test validation:
- `uv run pytest -q` passed (`716 passed, 15 skipped`)
- `frontend` build passes (`npm run build`)
- `frontend` lint fails (`npm run lint`: 5 errors, 2 warnings)
- Replay endpoint currently breaks on current log schema (`/api/runs/{run}` path mapping mismatch)
- Matching remains embedded (non-swappable)
- No manifest/artifact service stack exists at master-spec level

Key implementation sources:
- `microecon/simulation.py`
- `microecon/logging/events.py`
- `microecon/logging/formats.py`
- `microecon/batch.py`
- `server/routes.py`
- `server/websocket.py`
- `frontend/src/types/simulation.ts`
- `frontend/src/components/Config/ExportMenu.tsx`
- `docs/current/AGENT-ARCHITECTURE.md`

---

## 4. Critical Gap Summary

### P0 Blockers (Must Resolve First)
1. Replay contract breakage
   - `server/routes.py` expects legacy fields that do not match `TickRecord` schema.
   - Impact: replay import path fails against current logs.

2. Provenance accuracy bug in batch infrastructure
   - `BatchRunner` records `info_env` metadata but simulation creation ignores it and uses full info.
   - Impact: run records can claim noisy-info runs that were not actually noisy.

3. Trade proposer provenance corruption
   - Logged `proposer_id` is currently hardcoded to `agent1_id`.
   - Impact: incorrect mechanism-level interpretation for bargaining analysis.

4. Frontend lint baseline not clean
   - Hook immutability/order and state-in-effect violations in core components.
   - Impact: quality gate failure and elevated regression risk.

5. Trade event contract fragmentation in runtime/logging boundary
   - Simulation and logging maintain separate `TradeEvent` shapes with manual tuple transforms.
   - Impact: proposer and trade semantics can silently drift across paths.

### Additional Confirmed Risks (Must Be Planned Before Gate A Freeze)
1. Live payload and persisted tick payload diverge structurally
   - Live websocket payload and persisted `TickRecord` are not shape-compatible.
   - Impact: canonical schema scope is larger than naming alignment.

2. Global RNG contamination in batch path
   - `BatchRunner` calls module-level `random.seed(...)`.
   - Impact: shared RNG state can leak across components and runs.

3. Server has no `NoisyAlphaInformation` configuration pathway
   - Backend config and frontend surface only full-information runtime setup.
   - Impact: information regime is not a true product-level institutional control.

4. Duplicate `SimulationConfig` naming across server/logging domains
   - Same class name with different fields and semantics.
   - Impact: higher schema integration and maintenance risk.

### Structural Gaps (Master-Spec Mismatch)
1. No swappable matching/clearing runtime component
2. No canonical versioned schema across live/replay/analysis/export
3. No experiment manifest service with compatibility checks
4. No execution orchestrator with batch scheduling/cancellation as product service
5. No artifact bundle import/export/integrity workflow
6. Educational and research tracks not complete as end-to-end product workflows

---

## 5. Delivery Strategy

Execution is organized by master-spec gates:
- Gate A: Foundation Coherence
- Gate B: Workflow Completeness
- Gate C: Publication Readiness

Rule: do not start Gate B until Gate A pass criteria are met; do not start Gate C until Gate B pass criteria are met.

---

## 6. Gate A - Foundation Coherence

### A.1 Target Outcomes (from master spec)
- Manifest and schema contracts stabilized
- Live/replay/analytics contract alignment complete
- Matching/clearing abstraction formalized

### A.2 Workstreams

#### WS-A1: Canonical Contract and Versioning
Deliverables:
- Canonical schema package for:
  - live tick payload
  - replay tick payload
  - persisted run record
  - analysis inputs
  - export/import payloads
- Explicit `schema_version` field and compatibility policy doc
- Contract validation tests (server + frontend + loaders)
- Explicit contract for live-vs-persisted relationship:
  - either shared canonical core with adapters
  - or versioned transform layer with losslessness guarantees

Acceptance Criteria:
- One schema maps cleanly to live, replay, analysis, and export paths
- No lossy ad-hoc field transforms
- Schema compatibility tests run in CI
- Canonical mapping between live payload and persisted tick payload is documented and tested

#### WS-A2: Replay Service Stabilization
Deliverables:
- Fix `/api/runs/{run_name}` mapping to current `TickRecord` schema
- Support belief snapshots in replay payloads
- Add replay load integration tests against real logger output
- Add replay failure diagnostics for corrupt/missing artifacts

Acceptance Criteria:
- Replay loads standard logged runs without 500 errors
- Tick-by-tick replay consistency validated against stored data

#### WS-A3: Run Provenance Integrity
Deliverables:
- Fix `BatchRunner` to honor configured `info_env`
- Correct `proposer_id` capture in trade logs
- Remove module-level RNG seeding from batch execution path
- Consolidate trade event runtime->logging boundary (single canonical event model or explicit typed adapter)
- Introduce run IDs and manifest IDs in persisted records
- Provenance completeness checks

Acceptance Criteria:
- Recorded metadata accurately reflects executed runtime configuration
- Deterministic run metadata is complete and queryable
- Proposer, info environment, and RNG behavior are provenance-auditable and regression-tested

#### WS-A4: Matching/Clearing Abstraction
Deliverables:
- Write design/ADR for matching/clearing interface and integration boundaries
- Introduce `MatchingOrClearingProtocol` interface
- Extract state-transition responsibilities (proposal lifecycle, cooldowns, interaction states)
- Lift proposal resolution out of monolithic `_execute_actions` branch
- Keep current bilateral-proposal behavior as default implementation
- Add at least one additional family placeholder implementation path (stub with contract tests)
- Add conformance + performance baseline for modularized matching path

Acceptance Criteria:
- Matching/clearing is swappable without rewriting simulation loop
- Current behavior preserved under default protocol
- Interface and state-transition boundaries are documented before final schema freeze

#### WS-A5: Frontend Quality Baseline
Deliverables:
- Resolve current ESLint errors/warnings
- Add lint and typecheck to CI gates
- Define frontend contract-consumer tests for mode stores (live/compare/replay)
- Require behavior-preserving fixes for hook-order/immutability violations with targeted regression checks

Acceptance Criteria:
- `npm run lint` clean
- no hook-order/immutability violations in core render paths

#### WS-A6: Information Regime Product Surface Parity
Deliverables:
- Add backend config pathway for non-default information environments (`NoisyAlphaInformation` minimum)
- Add server-side validation and parameter handling for info environment options
- Add frontend controls for selecting info environment and parameters (at minimum noise std)
- Add integration tests proving runtime info environment matches persisted provenance and replay metadata

Acceptance Criteria:
- Product users can run both full-information and noisy-information configurations without code edits
- Persisted run metadata matches executed information regime and parameters

### A.3 Gate A Exit Artifacts
- Contract specification doc
- Compatibility policy doc
- Replay conformance test report
- Provenance conformance test report
- Matching abstraction design + implementation note
- Information-regime surface parity report
- CI evidence bundle for determinism and contract checks

---

## 7. Gate B - Workflow Completeness

### B.1 Target Outcomes (from master spec)
- Educational assignment workflow complete
- Research batch workflow complete
- Comparative analytics and narrative-replay linkage complete

### B.2 Workstreams

#### WS-B1: Experiment Manifest Service (MVP)
Deliverables:
- Manifest schema and validator:
  - objective
  - assumptions/locked controls
  - treatment arms
  - sweep definitions
  - seed policy
  - run budget
- Manifest compatibility checker vs current engine contracts
- Manifest persistence and retrieval API

Acceptance Criteria:
- Invalid/incomplete manifests rejected before execution
- Manifest IDs linked to all generated run records

#### WS-B2: Execution Orchestrator
Deliverables:
- Product service for:
  - single-run execute
  - batch execute
  - job status
  - cancellation
- Run catalog for replay and analysis selection
- Failure recovery and partial-run handling

Acceptance Criteria:
- Users can launch/review/cancel runs without code edits
- Batch runs carry explicit provenance and seed policy

Delivery priority inside Gate B:
- Research track and narrative linkage are prioritized first.
- Educational track is phased; multi-user/LMS-like features require explicit scope decision before full implementation.

#### WS-B3: Research Track Completion
Deliverables:
- Hypothesis/treatment setup UI
- Sweep config UI
- Effect reporting with dispersion and uncertainty context
- Outlier investigation flow with replay linkage

Acceptance Criteria:
- Reported deltas map to treatment definitions
- Batch comparisons are native UI workflows

#### WS-B4: Educational Track Completion (Phased)
Deliverables:
- Instructor flow:
  - choose objective
  - pick scenario template
  - lock assumptions/controls
  - generate assignment shell
- Student flow:
  - execute required comparisons
  - submit structured interpretation linked to evidence
- Instructor cohort review:
  - result distribution
  - misconception pattern surfacing

Acceptance Criteria:
- Assignment constraints enforce locked assumptions
- Submissions include traceable run/metric references

#### WS-B5: Narrative and Replay Linkage
Deliverables:
- Narrative record model:
  - claim text
  - linked metrics
  - linked run IDs
  - replay bookmarks
- UI "show source" path from claims/charts to evidence

Acceptance Criteria:
- Any claim in workflow resolves to supporting run + metric + replay position

### B.3 Gate B Exit Artifacts
- Demo education case (end-to-end)
- Demo research case (end-to-end)
- Narrative evidence trace report
- Usability walkthrough evidence (new user completion path)

---

## 8. Gate C - Publication Readiness

### C.1 Target Outcomes (from master spec)
- Artifact packaging and integrity validation complete
- Import/audit/rerun flow complete for external collaborators
- Report templates available for education and research outputs

### C.2 Workstreams

#### WS-C1: Artifact Service and Bundle Format
Deliverables:
- Publication bundle schema containing:
  - manifest(s)
  - run records
  - analysis records
  - narrative records
  - rendering assets
- Explicit bundle and schema version fields
- Hash/integrity manifest

Acceptance Criteria:
- Export + import round-trip without data loss
- Incomplete/corrupt bundles detected and rejected

#### WS-C2: Audit and Reproduction Workflow
Deliverables:
- Collaborator import flow
- Bundle verifier (schema, hash, provenance completeness)
- One-click rerun from manifest/seed policy
- Output equivalence checks under tolerance policy

Acceptance Criteria:
- Independent reviewer can reproduce key claim from bundle

#### WS-C3: Report Templates
Deliverables:
- Education report template
- Research report template
- Automatic inclusion of assumptions/caveats/uncertainty fields

Acceptance Criteria:
- Published outputs include caveats and uncertainty by default

### C.3 Gate C Exit Artifacts
- External-audit rehearsal package and transcript
- Bundle integrity test suite report
- Reproduction conformance report

---

## 9. Cross-Cutting Quality Plan

### Determinism Gate
- Seeded rerun equivalence tests for key outputs
- Tolerance policy defined for floating-point differences

### Contract Gate
- Schema validation at API boundaries
- Replay/log/analysis schema compatibility tests

### Interpretation Gate
- Reports require explicit assumptions, uncertainty, and confidence qualifiers

### Documentation Gate
- Any behavior/contract change requires updates to:
  - `docs/VISION/VISION-WORKFLOW-MASTER-SPEC.md` (if scope/intent changed)
  - `docs/current/AGENT-ARCHITECTURE.md` (if runtime semantics changed)
  - `STATUS.md` (current-state delta)

---

## 10. Proposed Sequencing (No Calendar Commitments)

### Phase 0: Stabilization Sprint
- Fix replay route schema mapping
- Fix batch `info_env` execution mismatch
- Fix proposer ID logging
- Consolidate trade-event runtime/logging boundary
- Remove global `random.seed(...)` from batch runner path
- Add server/frontend path for selecting information regime (minimum: full vs noisy alpha)
- Clear frontend lint baseline

### Phase 1: Contract Foundation
- Publish canonical schemas + versioning
- Resolve live-vs-persisted schema relationship (shared core vs transform policy) and lock via ADR
- Add compatibility and conformance tests
- Add run/provenance IDs

### Phase 2: Runtime Modularity
- Introduce matching/clearing abstraction from approved interface design
- Preserve bilateral default implementation
- Develop against draft schema; finalize after matching contract settles

### Phase 2.5: Gate A.5 Research Workflow Proof
- Deliver one end-to-end reproducible research workflow using CLI/scripting path
- Produce provenance and replay evidence package without UI dependencies

### Phase 3: Product Services
- Manifest service
- Execution orchestrator
- Replay service hardening

### Phase 4: Workflow Completion
- Research track implementation
- Narrative-evidence linkage
- Educational track implementation (phased after explicit scope decision)

### Phase 5: Publication Readiness
- Artifact service
- Import/audit/rerun path
- Report templates

Gate promotion is allowed only when gate evidence artifacts are complete.

---

## 11. Dependency Map

Hard dependencies:
1. Replay stabilization can begin immediately; final contract alignment depends on A-101 outputs.
2. Matching abstraction interface work starts after schema draft approval; final schema freeze requires matching contract sign-off.
3. Workflow completion depends on manifest and orchestrator services.
4. Publication readiness depends on stable run/analysis/narrative contracts.
5. Full educational-track implementation depends on explicit decision about single-user vs multi-user/LMS scope.

Soft dependencies:
1. Uncertainty/sensitivity analytics can start before full narrative layer, but final interpretation gate requires both.

---

## 12. Risk Register

1. Architecture churn risk
   - Mitigation: schema-first design docs and compatibility harness before broad refactors.

2. Silent provenance drift
   - Mitigation: provenance conformance tests and run metadata assertions in CI.

3. Performance regression with modular matching
   - Mitigation: benchmark suite and explicit performance budgets before promotion.

4. Documentation drift recurrence
   - Mitigation: release-blocking doc gate and required update checklist in PR template.

5. UX scope creep
   - Mitigation: gate-scoped acceptance criteria and strict non-goal enforcement.

6. Hidden RNG coupling
   - Mitigation: remove module-level RNG mutation and assert RNG isolation in tests.

7. Schema convergence underestimation
   - Mitigation: explicit live-vs-persisted mapping strategy with round-trip conformance tests.

8. Educational scope collapse into LMS requirements
   - Mitigation: phase educational track and gate multi-user features behind explicit scoping decision.

---

## 13. Open Design Decisions (Must Be Assigned)

1. Initial matching/clearing family set for v1 institutional library
2. Backward-compatibility horizon for schema and bundles
3. Determinism tolerance policy definition (metrics, numeric tolerances, and equivalence criteria)
4. Degree of UI-driven scenario authoring vs file-based authoring
5. Minimum uncertainty standard for research reporting
6. Minimal collaboration features for reviewer workflows
7. Educational-track scope boundary: single-user workflow vs multi-user assignment platform

Each decision requires:
- owner
- deadline
- decision record (ADR or equivalent)
- contract and UI language updates

---

## 14. Immediate Action Backlog (Execution-Ready)

### P0 (Start Immediately)
1. Fix replay field mapping in `server/routes.py` and add integration tests.
2. Honor `info_env` in `BatchRunner` simulation creation path.
3. Correct proposer ID propagation from runtime trade execution to logs.
4. Consolidate runtime/logging trade-event boundary to prevent schema drift.
5. Remove module-level `random.seed(...)` from batch run path.
6. Add backend/frontend info-env controls for at least full vs noisy alpha setup.
7. Resolve frontend lint errors/warnings and enforce lint in CI.

### P1 (After P0)
1. Define and implement canonical schema package with versioning and explicit live-vs-persisted mapping strategy.
2. Add compatibility tests across live/replay/analysis/export.
3. Introduce run IDs and manifest IDs in persisted records.
4. Draft and approve matching abstraction interface ADR and default bilateral adapter plan.
5. Capture proposal-evaluation visibility semantics in ADR/tests (lock intentional behavior or change explicitly).
6. Resolve Gate A blocking design decisions with owners and deadlines.

### P2 (After P1)
1. Implement manifest service MVP.
2. Implement execution orchestrator MVP.
3. Build research workflow shell in frontend.
4. Implement narrative record linking and evidence trace UX.

### P3 (After P2)
1. Build educational workflow shell after scope decision on multi-user requirements.

---

## 15. Definition of Plan Completion

This plan is complete when:
1. Gates A/B/C are each promoted with evidence artifacts.
2. Master-spec definition of done statements are demonstrably satisfied.
3. External reviewer can import a publication bundle, replay evidence, and reproduce key claims.
