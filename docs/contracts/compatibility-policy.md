# Schema Compatibility Policy

**Version:** 1.0
**Canonical source:** `microecon/logging/events.py`
**Enforcement:** `microecon/logging/formats.py` (`_validate_schema_version`)

---

## Version Format

Schema versions use `MAJOR.MINOR` semantic versioning (e.g. `1.0`).

## Read Compatibility

Readers (loaders, replay API, analysis tools) support:
- **Version N** (current): full support
- **Version N-1** (one prior): full support via `from_dict()` defaults

Pre-versioning runs (no `schema_version` field) are treated as version `"0.0"`.

## Write Policy

Writers always produce the current schema version. There is no option to write older formats.

## Migration Strategy

Migration from N-1 to N is handled by `from_dict()` default values on new fields:
- New fields get sensible defaults (e.g. `run_id=""`, `manifest_id=None`)
- No separate migration scripts are needed
- Old persisted files are read as-is; they are NOT rewritten on load

## Breaking Changes

A **MAJOR** version bump (e.g. 1.0 → 2.0):
- Removes support for version N-2
- Requires documentation of what changed and how to migrate
- Must update `_SUPPORTED_VERSIONS` in `formats.py`

A **MINOR** version bump (e.g. 1.0 → 1.1):
- Adds new optional fields with defaults
- Does NOT break readers on the same MAJOR version

## Compatibility Horizon

Two major versions: readers support N and N-1. Version N-2 and older are unsupported and raise `ValueError` on load.

## Current State

| Version | Status | Notes |
|---|---|---|
| 0.0 | N-1 (supported) | Pre-versioning runs, no `schema_version` field |
| 1.0 | N (current) | First versioned schema |
