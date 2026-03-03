# Vision Workflow Execution Board

**Status:** Draft  
**Version:** 0.1  
**Date:** 2026-02-18  
**Upstream Plan:** `docs/VISION/VISION-WORKFLOW-IMPLEMENTATION-PLAN.md`  
**Target Spec:** `docs/VISION/VISION-WORKFLOW-MASTER-SPEC.md`

---

## 1. How To Use This Board

This file is issue-ready backlog content for direct conversion into tracker tickets.

Recommended issue fields:
- `Title`: use exact issue IDs below (`A-001`, `B-104`, etc.)
- `Milestone`: `Gate A`, `Gate B`, `Gate C`
- `Labels`: use label taxonomy in section 2
- `Description`: copy issue block verbatim
- `Dependencies`: use `Depends On` field

---

## 2. Label Taxonomy

Use these labels consistently:
- `gate:A`
- `gate:B`
- `gate:C`
- `priority:P0`
- `priority:P1`
- `priority:P2`
- `priority:P3`
- `type:epic`
- `type:feature`
- `type:bug`
- `type:infra`
- `type:docs`
- `track:backend`
- `track:frontend`
- `track:simulation`
- `track:contracts`
- `track:analytics`
- `track:workflow`
- `track:artifact`

---

## 3. Milestone Order

1. `M0 Stabilization` (P0 defects and quality baseline)
2. `M1 Contract Foundation` (canonical schema + provenance + compatibility)
3. `M2 Runtime Modularity` (matching/clearing abstraction)
4. `M2.5 Research Workflow Proof` (Gate A.5 scripted end-to-end reproducibility)
5. `M3 Product Services` (manifest + orchestrator + replay hardening)
6. `M4 Workflow Completion` (research + education + narrative linkage)
7. `M5 Publication Readiness` (bundle, audit, rerun, report templates)

---

## 4. Gate A Board (Foundation Coherence)

### EPIC A-E1: Stabilization and Trust Restoration
**Labels:** `gate:A`, `priority:P0`, `type:epic`  
**Depends On:** none  
**Definition of Done:** A-001 through A-007 complete.

### A-001: Replay loader schema mismatch fix
**Type:** `bug`  
**Labels:** `gate:A`, `priority:P0`, `track:backend`  
**Depends On:** none  
**Scope:**
- Fix `server/routes.py` replay transformation to align with `TickRecord` schema.
- Handle agent snapshot `endowment` tuple format.
- Handle current trade event field names.
- Include belief snapshot mapping instead of hardcoded empty beliefs.
**Acceptance Criteria:**
- `/api/runs/{run_name}` loads runs produced by `SimulationLogger` without server errors.
- Replay payloads include beliefs when present in logs.
- Error responses are explicit for invalid/corrupt run directories.
**Validation:**
- Add integration test that creates run via logger, then loads via API path.

### A-002: Batch info environment execution correctness
**Type:** `bug`  
**Labels:** `gate:A`, `priority:P0`, `track:simulation`  
**Depends On:** none  
**Scope:**
- Ensure `BatchRunner` actually passes configured `info_env` into `Simulation`.
- Remove metadata/runtime drift risk in `SimulationConfig` logging.
**Acceptance Criteria:**
- Runs configured with `NoisyAlphaInformation` execute with noisy info.
- `info_env_name` in persisted config matches runtime behavior.
**Validation:**
- Add test asserting simulation info env type when batch config sets noisy environment.

### A-003: Proposer ID provenance fix
**Type:** `bug`  
**Labels:** `gate:A`, `priority:P0`, `track:simulation`, `track:contracts`  
**Depends On:** none  
**Scope:**
- Preserve actual proposer selected by bargaining protocol through runtime trade event.
- Remove hardcoded proposer fallback in logging path.
**Acceptance Criteria:**
- Logged `proposer_id` equals actual proposer used in trade execution.
- Theory/integration tests cover proposer-sensitive protocols.
**Validation:**
- Add deterministic test comparing selected proposer vs logged proposer.

### A-004: Frontend lint baseline cleanup and CI enforcement
**Type:** `infra`  
**Labels:** `gate:A`, `priority:P0`, `track:frontend`  
**Depends On:** none  
**Scope:**
- Resolve current ESLint errors/warnings in hooks and components.
- Add lint and typecheck to CI quality gate.
**Acceptance Criteria:**
- `cd frontend && npm run lint` passes clean.
- `cd frontend && npm run build` still passes.
- CI fails on lint/typecheck regressions.
**Validation:**
- CI evidence from one green run.

### A-005: Batch RNG isolation fix
**Type:** `bug`  
**Labels:** `gate:A`, `priority:P0`, `track:simulation`  
**Depends On:** none  
**Scope:**
- Remove module-level `random.seed(...)` calls from batch execution path.
- Ensure all stochastic behavior is driven by per-run RNG instances and explicit seeds.
**Acceptance Criteria:**
- Batch runs do not mutate global Python RNG state.
- Reproducibility tests remain stable with explicit per-run seed control.
**Validation:**
- Add test proving global RNG state is unchanged after batch execution.

### A-006: Trade-event runtime/logging boundary consolidation
**Type:** `bug`  
**Labels:** `gate:A`, `priority:P0`, `track:simulation`, `track:contracts`  
**Depends On:** A-003  
**Scope:**
- Replace ad-hoc tuple transformation between simulation trade events and logging trade events.
- Use one canonical event model or an explicit typed adapter with full-field mapping tests.
**Acceptance Criteria:**
- Proposer, holdings, allocations, gains, and trade flags survive runtime->log path without drift.
- No hardcoded proposer fallback remains in logging path.
**Validation:**
- Add integration test that catches proposer drift on proposer-sensitive protocol runs.

### A-007: Information-regime product-surface wiring
**Type:** `feature`  
**Labels:** `gate:A`, `priority:P0`, `track:backend`, `track:frontend`, `track:simulation`  
**Depends On:** A-002  
**Scope:**
- Add backend config fields for information environment selection and parameters.
- Wire simulation creation to instantiate configured info environment (minimum: full vs noisy alpha).
- Add frontend controls and contract handling for info environment settings.
**Acceptance Criteria:**
- UI/API users can run both full-information and noisy-information configurations without code edits.
- Persisted run metadata and replay payloads reflect executed info environment settings.
**Validation:**
- API + integration tests asserting runtime info env, persisted metadata, and replay config consistency.

### EPIC A-E2: Canonical Contract and Compatibility
**Labels:** `gate:A`, `priority:P1`, `type:epic`, `track:contracts`  
**Depends On:** A-001, A-002, A-003, A-004, A-005, A-006, A-007  
**Definition of Done:** A-101 through A-107 complete.

### A-101: Canonical schema package definition
**Type:** `feature`  
**Labels:** `gate:A`, `priority:P1`, `track:contracts`  
**Depends On:** A-001, A-006, A-007  
**Scope:**
- Define canonical schema for live ticks, replay ticks, persisted runs, and analysis input.
- Add explicit `schema_version`.
- Define and document live-vs-persisted contract strategy (shared core vs versioned transform layer).
**Acceptance Criteria:**
- Single schema family documented and implemented.
- Existing live/replay/analysis paths conform to schema.
- Live payload and persisted tick payload relationship is explicit, tested, and lossless by policy.

### A-102: Schema compatibility policy and migration rules
**Type:** `docs`  
**Labels:** `gate:A`, `priority:P1`, `track:contracts`, `type:docs`  
**Depends On:** A-101  
**Scope:**
- Define backward/forward compatibility policy.
- Define migration behavior for old run artifacts.
- Define compatibility horizon commitment for schema versions.
**Acceptance Criteria:**
- Compatibility matrix documented.
- Upgrade/downgrade expectations explicit.

### A-103: Contract conformance test harness
**Type:** `infra`  
**Labels:** `gate:A`, `priority:P1`, `track:contracts`  
**Depends On:** A-101  
**Scope:**
- Add server and frontend contract conformance tests.
- Validate replay-log-analysis alignment.
**Acceptance Criteria:**
- Contract checks run in CI.
- Breaking schema changes fail tests.

### A-104: Run IDs and manifest IDs in persisted records
**Type:** `feature`  
**Labels:** `gate:A`, `priority:P1`, `track:backend`, `track:contracts`  
**Depends On:** A-101  
**Scope:**
- Introduce stable run identifiers.
- Reserve manifest linkage fields for Gate B integration.
**Acceptance Criteria:**
- Every persisted run has run ID.
- Provenance fields available in replay and analysis loaders.

### A-105: Determinism gate implementation
**Type:** `infra`  
**Labels:** `gate:A`, `priority:P1`, `track:simulation`  
**Depends On:** A-103  
**Scope:**
- Add seeded rerun equivalence checks for key outputs.
- Define tolerance rules for numeric comparisons.
- Publish deterministic equivalence policy (exact fields, tolerance bounds, pass/fail criteria).
**Acceptance Criteria:**
- Determinism checks pass on CI for reference scenarios.
- Determinism policy is documented and referenced by test harness.

### A-106: Documentation synchronization gate
**Type:** `docs`  
**Labels:** `gate:A`, `priority:P1`, `type:docs`  
**Depends On:** A-101  
**Scope:**
- Add contributor rule that semantics/schema changes require doc updates.
- Align status/version references across core docs and server metadata.
**Acceptance Criteria:**
- Doc update checklist enforced in PR template.
- Known version drift items resolved.

### A-107: Proposal-evaluation visibility semantics decision
**Type:** `docs`  
**Labels:** `gate:A`, `priority:P1`, `track:simulation`, `type:docs`  
**Depends On:** A-103  
**Scope:**
- Decide and document whether Execute-phase proposal evaluation uses full visibility or local visibility.
- Align comments, ADR/docs, and tests with chosen semantics.
**Acceptance Criteria:**
- Proposal-evaluation visibility behavior is intentional, documented, and regression-tested.

### EPIC A-E3: Matching/Clearing Runtime Modularity
**Labels:** `gate:A`, `priority:P1`, `type:epic`, `track:simulation`  
**Depends On:** A-101, A-103  
**Definition of Done:** A-200 through A-206 complete.

### A-200: Matching/clearing design ADR
**Type:** `docs`  
**Labels:** `gate:A`, `priority:P1`, `track:simulation`, `type:docs`  
**Depends On:** A-101 (draft schema baseline)  
**Scope:**
- Produce design ADR for matching/clearing interface, edge cases, and action-system coupling.
- Define determinism constraints and migration plan from monolithic execution path.
**Acceptance Criteria:**
- ADR approved with interface contract, ownership boundaries, and test strategy.

### A-201: Matching/clearing interface extraction
**Type:** `feature`  
**Labels:** `gate:A`, `priority:P1`, `track:simulation`  
**Depends On:** A-200  
**Scope:**
- Define swappable matching/clearing protocol interface.
- Separate matching responsibilities from bargaining protocol.
**Acceptance Criteria:**
- Simulation composes matching and bargaining as distinct components.

### A-202: Interaction state-transition extraction
**Type:** `feature`  
**Labels:** `gate:A`, `priority:P1`, `track:simulation`  
**Depends On:** A-201  
**Scope:**
- Extract proposal lifecycle and interaction-state transition logic behind explicit boundaries.
**Acceptance Criteria:**
- State transitions are deterministic and no longer coupled to monolithic action-resolution block.

### A-203: Default bilateral proposal protocol adapter
**Type:** `feature`  
**Labels:** `gate:A`, `priority:P1`, `track:simulation`  
**Depends On:** A-202  
**Scope:**
- Re-implement current behavior as explicit default protocol adapter.
**Acceptance Criteria:**
- No behavioral regression against current baseline tests.

### A-204: Proposal resolution refactor in simulation loop
**Type:** `feature`  
**Labels:** `gate:A`, `priority:P1`, `track:simulation`  
**Depends On:** A-203  
**Scope:**
- Remove matching-specific logic from monolithic `_execute_actions`.
- Route through matching protocol contract.
**Acceptance Criteria:**
- Tick loop remains deterministic and test suite stays green.

### A-205: Matching contract tests and benchmark baseline
**Type:** `infra`  
**Labels:** `gate:A`, `priority:P1`, `track:simulation`  
**Depends On:** A-204  
**Scope:**
- Add protocol conformance tests.
- Add baseline performance check to monitor O(n^2) regressions.
**Acceptance Criteria:**
- Matching conformance tests pass.
- Performance baseline recorded for gate promotion.

### A-206: Alternative mechanism stub implementation
**Type:** `feature`  
**Labels:** `gate:A`, `priority:P1`, `track:simulation`  
**Depends On:** A-205  
**Scope:**
- Add at least one non-default matching/clearing mechanism stub that conforms to protocol contract.
**Acceptance Criteria:**
- Secondary mechanism path passes conformance tests and demonstrates swappability.

### EPIC A-E4: Gate A.5 Research Workflow Proof
**Labels:** `gate:A`, `priority:P1`, `type:epic`, `track:workflow`, `track:analytics`  
**Depends On:** A-E1, A-E2  
**Definition of Done:** A-250 complete.

### A-250: Scripted end-to-end research reproducibility flow
**Type:** `feature`  
**Labels:** `gate:A`, `priority:P1`, `track:workflow`, `track:analytics`, `track:backend`  
**Depends On:** A-104, A-105  
**Scope:**
- Deliver one scripted CLI/scripting workflow: configure experiment, run batch, compute comparison outputs, and load replay evidence.
- Produce reference evidence artifact set for Gate B UI targets.
**Acceptance Criteria:**
- Workflow reproduces identical key outputs under declared seed/tolerance policy.
- Steps are documented and runnable without manual code edits.

---

## 5. Gate B Board (Workflow Completeness)

Priority order for Gate B execution:
1. B-E1 and B-E3 (research workflow and traceability path)
2. B-E2 (educational workflow), unless explicitly elevated by scope decision

### EPIC B-E1: Manifest and Orchestrator Services
**Labels:** `gate:B`, `priority:P1`, `type:epic`, `track:backend`, `track:workflow`  
**Depends On:** Gate A complete  
**Definition of Done:** B-101 through B-107 complete.

### B-101: Manifest schema MVP
**Type:** `feature`  
**Labels:** `gate:B`, `priority:P1`, `track:workflow`, `track:contracts`  
**Depends On:** A-101, A-104  
**Scope:**
- Define experiment manifest with objective, assumptions, treatments, sweeps, seed policy, run budget.
**Acceptance Criteria:**
- Manifest can fully describe baseline + treatment experiments.

### B-102: Manifest validator and compatibility checker
**Type:** `feature`  
**Labels:** `gate:B`, `priority:P1`, `track:backend`, `track:contracts`  
**Depends On:** B-101  
**Scope:**
- Validate completeness, bounds, and contract compatibility.
**Acceptance Criteria:**
- Invalid manifests rejected pre-run with actionable errors.

### B-103: Manifest persistence API
**Type:** `feature`  
**Labels:** `gate:B`, `priority:P1`, `track:backend`  
**Depends On:** B-101, B-102  
**Scope:**
- Create/read/list manifest endpoints with version metadata.
**Acceptance Criteria:**
- Manifests are addressable and reusable by ID.

### B-104: Execution orchestrator API (single and batch)
**Type:** `feature`  
**Labels:** `gate:B`, `priority:P1`, `track:backend`, `track:workflow`  
**Depends On:** B-102, B-103  
**Scope:**
- Add orchestrator job model for single/batch run execution.
- Include status transitions and cancellation.
**Acceptance Criteria:**
- Jobs can be launched, inspected, and cancelled via API.

### B-105: Run catalog and replay integration
**Type:** `feature`  
**Labels:** `gate:B`, `priority:P1`, `track:backend`, `track:frontend`  
**Depends On:** B-104  
**Scope:**
- Connect orchestrator outputs to replay run catalog.
- Remove dependence on manual filesystem conventions.
**Acceptance Criteria:**
- Replay loader lists orchestrated runs with provenance metadata.

### B-106: Comparative batch reporting MVP
**Type:** `feature`  
**Labels:** `gate:B`, `priority:P1`, `track:analytics`, `track:workflow`  
**Depends On:** B-104  
**Scope:**
- Produce effect outputs with dispersion and uncertainty context.
**Acceptance Criteria:**
- Treatment deltas map cleanly to manifest treatment arms.

### B-107: Orchestrator and manifest integration tests
**Type:** `infra`  
**Labels:** `gate:B`, `priority:P1`, `track:backend`  
**Depends On:** B-104, B-105, B-106  
**Scope:**
- End-to-end tests: manifest -> run job -> replay/analysis availability.
**Acceptance Criteria:**
- CI passes complete workflow tests.

### EPIC B-E2: Educational Workflow Completion
**Labels:** `gate:B`, `priority:P3`, `type:epic`, `track:frontend`, `track:workflow`  
**Depends On:** B-E1  
**Definition of Done:** B-201 through B-206 complete.

### B-201: Instructor objective-first assignment builder
**Type:** `feature`  
**Labels:** `gate:B`, `priority:P3`, `track:frontend`, `track:workflow`  
**Depends On:** B-103  
**Scope:**
- UI flow to choose objective and scenario template.
**Acceptance Criteria:**
- Instructor can define assignment intent before low-level parameters.

### B-202: Assignment control locking
**Type:** `feature`  
**Labels:** `gate:B`, `priority:P3`, `track:frontend`, `track:workflow`  
**Depends On:** B-201  
**Scope:**
- Allow lock/unlock of modifiable controls for student runs.
**Acceptance Criteria:**
- Locked assumptions are enforced at execution time.

### B-203: Student run and submission shell
**Type:** `feature`  
**Labels:** `gate:B`, `priority:P3`, `track:frontend`, `track:workflow`  
**Depends On:** B-202, B-104  
**Scope:**
- Student UI for required runs and structured interpretation submission.
**Acceptance Criteria:**
- Submission links to run IDs and metrics automatically.

### B-204: Cohort outcome comparison view
**Type:** `feature`  
**Labels:** `gate:B`, `priority:P3`, `track:frontend`, `track:analytics`  
**Depends On:** B-203  
**Scope:**
- Instructor dashboard for class-level distributions and misconception indicators.
**Acceptance Criteria:**
- Instructor can compare multiple student outcomes without manual wrangling.

### B-205: Educational workflow evidence export
**Type:** `feature`  
**Labels:** `gate:B`, `priority:P3`, `track:artifact`, `track:workflow`  
**Depends On:** B-203  
**Scope:**
- Export assignment run evidence with traceable references.
**Acceptance Criteria:**
- Evidence package contains assignment context + run linkage.

### B-206: Educational track acceptance test scenarios
**Type:** `infra`  
**Labels:** `gate:B`, `priority:P3`, `track:workflow`  
**Depends On:** B-204, B-205  
**Scope:**
- Add scripted end-to-end acceptance tests for instructor/student workflows.
**Acceptance Criteria:**
- Education demo case passes without code edits.

### EPIC B-E3: Research Workflow and Narrative Linkage
**Labels:** `gate:B`, `priority:P1`, `type:epic`, `track:frontend`, `track:analytics`  
**Depends On:** B-E1  
**Definition of Done:** B-301 through B-306 complete.

### B-301: Hypothesis and treatment design UI
**Type:** `feature`  
**Labels:** `gate:B`, `priority:P1`, `track:frontend`, `track:workflow`  
**Depends On:** B-101, B-103  
**Scope:**
- Research UI for hypothesis declaration and treatment arm setup.
**Acceptance Criteria:**
- Treatment definitions persist and map to manifests.

### B-302: Sweep and seed policy UI
**Type:** `feature`  
**Labels:** `gate:B`, `priority:P1`, `track:frontend`, `track:workflow`  
**Depends On:** B-301  
**Scope:**
- UI for sweep parameterization and seed policy definition.
**Acceptance Criteria:**
- Batch configuration can be created without code.

### B-303: Research effect/uncertainty reporting panel
**Type:** `feature`  
**Labels:** `gate:B`, `priority:P1`, `track:analytics`, `track:frontend`  
**Depends On:** B-106  
**Scope:**
- Report treatment effects with uncertainty and sensitivity metadata.
**Acceptance Criteria:**
- Comparative outputs include effect magnitude plus uncertainty context.

### B-304: Outlier investigation via synchronized replay
**Type:** `feature`  
**Labels:** `gate:B`, `priority:P1`, `track:frontend`, `track:analytics`  
**Depends On:** B-303, A-001  
**Scope:**
- Connect anomalous results to replay views and event trails.
**Acceptance Criteria:**
- Researcher can jump from outlier metric to replay evidence.

### B-305: Narrative record model and storage
**Type:** `feature`  
**Labels:** `gate:B`, `priority:P1`, `track:backend`, `track:workflow`  
**Depends On:** B-103, B-106  
**Scope:**
- Add narrative records with claims, linked evidence, and replay bookmarks.
**Acceptance Criteria:**
- Narrative claims persist with explicit evidence references.

### B-306: UI traceability path ("show source")
**Type:** `feature`  
**Labels:** `gate:B`, `priority:P1`, `track:frontend`, `track:workflow`  
**Depends On:** B-305  
**Scope:**
- Add consistent source-link UX from charts/claims to data origin.
**Acceptance Criteria:**
- Any displayed result has a direct trace path to source run/metric/bookmark.

---

## 6. Gate C Board (Publication Readiness)

### EPIC C-E1: Artifact Service and Integrity
**Labels:** `gate:C`, `priority:P1`, `type:epic`, `track:artifact`  
**Depends On:** Gate B complete  
**Definition of Done:** C-101 through C-107 complete.

### C-101: Publication bundle schema v1
**Type:** `feature`  
**Labels:** `gate:C`, `priority:P1`, `track:artifact`, `track:contracts`  
**Depends On:** B-101, B-305  
**Scope:**
- Define bundle containing manifests, runs, analyses, narrative records, and assets.
**Acceptance Criteria:**
- Bundle schema has explicit version and compatibility metadata.

### C-102: Bundle exporter service
**Type:** `feature`  
**Labels:** `gate:C`, `priority:P1`, `track:artifact`, `track:backend`  
**Depends On:** C-101  
**Scope:**
- Export complete publication bundle from selected experiment set.
**Acceptance Criteria:**
- Exported bundle includes all referenced artifacts and metadata.

### C-103: Bundle importer service
**Type:** `feature`  
**Labels:** `gate:C`, `priority:P1`, `track:artifact`, `track:backend`  
**Depends On:** C-101  
**Scope:**
- Import bundle and register its contents in local catalog.
**Acceptance Criteria:**
- Imported bundles are replayable and analyzable without manual patching.

### C-104: Integrity manifest and hash verification
**Type:** `feature`  
**Labels:** `gate:C`, `priority:P1`, `track:artifact`  
**Depends On:** C-102, C-103  
**Scope:**
- Add integrity file with hashes and completeness checks.
**Acceptance Criteria:**
- Corrupt/incomplete bundles are detected and rejected.

### C-105: Reproduction runner from imported manifests
**Type:** `feature`  
**Labels:** `gate:C`, `priority:P1`, `track:workflow`, `track:backend`  
**Depends On:** C-103, B-104  
**Scope:**
- Rerun imported manifests under declared seed policy.
**Acceptance Criteria:**
- Reproduction output can be compared to packaged claims under tolerance policy.

### C-106: External audit workflow UI
**Type:** `feature`  
**Labels:** `gate:C`, `priority:P1`, `track:frontend`, `track:workflow`  
**Depends On:** C-103, C-105  
**Scope:**
- UI flow for collaborator to import bundle, verify integrity, replay claims, rerun.
**Acceptance Criteria:**
- Reviewer can complete audit workflow without code edits.

### C-107: Bundle round-trip and audit test suite
**Type:** `infra`  
**Labels:** `gate:C`, `priority:P1`, `track:artifact`, `track:workflow`  
**Depends On:** C-104, C-105, C-106  
**Scope:**
- Add automated tests for export/import/audit/rerun workflow.
**Acceptance Criteria:**
- Round-trip tests pass and produce gate evidence artifacts.

### EPIC C-E2: Report Templates and Interpretation Standards
**Labels:** `gate:C`, `priority:P2`, `type:epic`, `track:workflow`, `track:analytics`  
**Depends On:** C-E1  
**Definition of Done:** C-201 through C-204 complete.

### C-201: Education report template
**Type:** `feature`  
**Labels:** `gate:C`, `priority:P2`, `track:workflow`  
**Depends On:** B-206, C-102  
**Scope:**
- Template for classroom-ready output including assumptions and evidence references.
**Acceptance Criteria:**
- Generated reports include linked run/metric evidence.

### C-202: Research report template
**Type:** `feature`  
**Labels:** `gate:C`, `priority:P2`, `track:workflow`, `track:analytics`  
**Depends On:** B-303, C-102  
**Scope:**
- Template for hypothesis, treatment effects, uncertainty, caveats, and replay references.
**Acceptance Criteria:**
- Research reports satisfy interpretation gate requirements.

### C-203: Assumption and caveat auto-inclusion
**Type:** `feature`  
**Labels:** `gate:C`, `priority:P2`, `track:workflow`, `track:docs`  
**Depends On:** C-201, C-202  
**Scope:**
- Auto-populate assumptions, non-goals, caveats in generated outputs.
**Acceptance Criteria:**
- Published artifacts include assumptions and caveats by default.

### C-204: Final external reviewer dry run
**Type:** `infra`  
**Labels:** `gate:C`, `priority:P2`, `track:workflow`  
**Depends On:** C-107, C-203  
**Scope:**
- Execute full dry-run with an external reviewer persona against packaged claim.
**Acceptance Criteria:**
- End-to-end verification succeeds from import through replay and rerun.

---

## 7. Immediate Sprint Candidate (Next 2 Weeks)

Create first sprint from these issues:
1. A-001
2. A-002
3. A-003
4. A-005
5. A-006
6. A-004
7. A-101 (draft-only scope: schema proposal doc + review)
8. A-007 (backend contract + config-path slice)

Sprint exit criteria:
- Core P0 correctness issues closed (A-001 through A-006)
- A-007 backend contract slice merged and test-covered
- Gate A contract work kicked off with approved schema design draft

---

## 8. Gate Promotion Checklist

### Promote Gate A
- A-E1 complete
- A-E2 complete
- A-E3 complete
- A-E4 complete
- Determinism and contract CI evidence attached

### Promote Gate B
- B-E1 complete
- B-E3 complete
- B-E2 complete OR explicitly deferred with approved rationale
- Research demo artifact attached
- Education demo artifact attached if B-E2 is in scope for release

### Promote Gate C
- C-E1 complete
- C-E2 complete
- External audit dry-run evidence attached
