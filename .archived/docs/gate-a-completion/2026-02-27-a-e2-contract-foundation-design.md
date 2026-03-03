# A-E2: Canonical Contract and Compatibility — Design

**Date:** 2026-02-27
**Status:** Approved
**Scope:** A-102 through A-107 (6 items)
**Depends on:** A-E1 (complete), A-101 (complete)

---

## Context

A-101 established the canonical schema package: frozen dataclasses in `events.py`, schema version 1.0, TS type generation, and the schema contract doc. The remaining A-E2 items build the surrounding infrastructure: run provenance, conformance testing, determinism verification, and documentation governance.

## Sequencing

```
Layer 1 (parallel):  A-104, A-103, A-102, A-106
Layer 2 (after A-103): A-105, A-107
```

Execution order: A-104 → A-103 → A-105 → A-102 → A-106 → A-107

---

## A-104: Run IDs and Manifest IDs

**Goal:** Stable identifiers for every persisted run. Reserved manifest linkage fields for Gate B.

**Design:**
- Add `run_id: str` to logging `SimulationConfig` in `events.py` (UUID4, generated at run start)
- Add `manifest_id: str | None = None` and `treatment_arm: str | None = None` (reserved for Gate B)
- Generate `run_id` in `SimulationLogger.__init__()` before first tick
- Pass through `server/simulation_manager.py` `to_logging_config()`
- Backward-compatible: new fields have defaults, no schema version bump needed

**Files:**
- `microecon/logging/events.py` — add fields to `SimulationConfig`
- `microecon/logging/logger.py` — generate `run_id`
- `server/simulation_manager.py` — pass `run_id` through conversion
- `tests/test_logging.py` — roundtrip tests
- `docs/contracts/schema-v1.md` — document new fields

---

## A-103: Contract Conformance Test Harness

**Goal:** Automated tests proving live/replay/persisted paths all conform to canonical schema.

**Four levels:**

1. **Canonical round-trip**: `to_dict()` → `from_dict()` → assert equality for all dataclasses
2. **Persist → Load**: create simulation, run ticks, persist via logger, load via `formats.load_run()`, assert lossless
3. **Persist → Replay API**: same persisted run loaded via `server/routes.py` `transform_tick_for_replay`, assert adapter contract (renames, derived fields)
4. **Live WebSocket alignment**: capture `SimulationManager` broadcast payload, assert all expected fields present

**Test organization:** `tests/test_contract_conformance.py` with `@pytest.mark.contract` marker.

**Files:**
- `tests/test_contract_conformance.py` — new test suite
- `pyproject.toml` — add `contract` marker
- `tests/conftest.py` — shared fixtures if needed

---

## A-105: Determinism Gate

**Goal:** Prove seeded reruns produce identical outputs. Document tolerance policy.

**Design:**
- Run same config (same seed, same params) twice, compare full tick sequences
- Test all 4 protocols, 3 YAML scenarios, noisy info environment
- **Tolerance policy:**
  - Integer fields: exact match
  - Floating-point values: `abs(a - b) < 1e-10`
  - Sequence ordering: exact (deterministic tie-breaking is contract)

**Files:**
- `tests/test_determinism.py` — determinism gate tests
- `docs/contracts/determinism-policy.md` — tolerance rules
- `pyproject.toml` — add `determinism` marker

---

## A-102: Schema Compatibility Policy

**Goal:** Codify the compatibility rules A-101 implemented.

**Document `docs/contracts/compatibility-policy.md`:**
- N / N-1 read support (readers handle current and one prior version)
- Write policy: always latest
- Migration: `from_dict()` defaults handle old runs (no migration scripts)
- Breaking changes: MAJOR bump, drop N-2, document migration path
- Compatibility horizon: 2 major versions (N and N-1)
- Pre-versioning: runs without `schema_version` = "0.0"

---

## A-106: Documentation Synchronization Gate

**Goal:** Contributor rules ensuring schema changes stay documented.

**Deliverable:** `docs/CONTRIBUTING.md` with schema change checklist:
- Changes to `events.py` fields → update `schema-v1.md` + regenerate `canonical.ts`
- Changes to presentation adapters → update adapter mapping tables
- Changes to protocol semantics → update ADR or create new one

---

## A-107: Proposal-Evaluation Visibility ADR

**Goal:** Investigate, decide, and document whether Execute-phase proposal evaluation uses full or local visibility.

**Approach:**
1. Read `simulation.py` `_execute_actions()` to determine current behavior
2. Determine if proposal evaluation respects `InformationEnvironment` or bypasses it
3. Write ADR: `docs/adr/ADR-005-PROPOSAL-EVALUATION-VISIBILITY.md`
4. Add regression test locking in the documented behavior

**Files:**
- `docs/adr/ADR-005-PROPOSAL-EVALUATION-VISIBILITY.md`
- `tests/test_simulation.py` — regression test for visibility semantics
