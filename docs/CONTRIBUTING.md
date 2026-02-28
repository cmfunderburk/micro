# Contributing to Microecon

## Schema Change Checklist

When modifying canonical schema dataclasses in `microecon/logging/events.py`:

- [ ] Update `docs/contracts/schema-v1.md` with new/changed fields
- [ ] Regenerate TS types: `uv run python scripts/generate_ts_types.py --write`
- [ ] Commit regenerated `frontend/src/types/canonical.ts`
- [ ] If field is removed or renamed: bump `SCHEMA_VERSION` and update `_SUPPORTED_VERSIONS` in `formats.py`
- [ ] Run contract conformance tests: `uv run pytest -m contract`
- [ ] Run determinism tests: `uv run pytest -m determinism`

## Presentation Adapter Changes

When modifying the live WebSocket adapter (`server/simulation_manager.py:get_tick_data`) or replay adapter (`server/routes.py:load_run`):

- [ ] Update the adapter mapping tables in `docs/contracts/schema-v1.md`
- [ ] Update `frontend/src/types/simulation.ts` doc comment if field names change
- [ ] Run contract conformance tests: `uv run pytest -m contract`

## Protocol Semantics Changes

When modifying bargaining, matching, or decision procedures:

- [ ] Update or create an ADR in `docs/adr/`
- [ ] Run theory tests: `uv run pytest -m theory`
- [ ] Run determinism tests: `uv run pytest -m determinism`

## Running Tests

```bash
uv run pytest                      # Full suite
uv run pytest -m contract          # Contract conformance only
uv run pytest -m determinism       # Determinism gate only
uv run pytest -m theory            # Theory verification only
uv run pytest -m "not slow"        # Skip slow tests
```
