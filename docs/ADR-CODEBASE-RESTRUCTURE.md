# ADR: Codebase Restructure - Flatten to Project Root

**Status:** Accepted
**Date:** 2026-01-08

## Context

The codebase had Python code in two separate locations:
- `src/microecon/` - Core simulation library (pip-installable)
- `backend/` - FastAPI WebSocket server (imports microecon, not packaged)

This created confusion about where Python code lives and made the project structure harder to navigate.

## Decision

Flatten the structure to project root:

**Before:**
```
microecon/
├── src/microecon/       # Core library
├── backend/             # WebSocket server
├── frontend/            # React UI
└── tests/
```

**After:**
```
microecon/
├── microecon/           # Core library (was src/microecon/)
├── server/              # WebSocket server (was backend/)
├── frontend/            # React UI (unchanged)
└── tests/               # Tests (unchanged)
```

## Rationale

1. **Simpler mental model** - All Python code at same level, no `src/` wrapper
2. **Common pattern** - Most Python projects use `package_name/` at root
3. **Clearer naming** - `server/` better describes the WebSocket server than `backend/`
4. **No import changes** - Package is still `microecon`, imports unchanged

## Consequences

### Positive
- Easier navigation
- Standard project layout
- Clear separation: `microecon/` (library), `server/` (app), `frontend/` (UI)

### Negative
- One-time migration effort
- Need to update `pyproject.toml` package discovery

### Neutral
- `frontend/` stays as-is (npm project, not affected)
- Test imports unchanged (`from microecon import ...`)

## Implementation

1. `git mv src/microecon microecon`
2. `git mv backend server`
3. Update `pyproject.toml` packages path
4. Update `server/` internal imports (`from backend.X` → `from server.X`)
5. Update documentation references
6. Verify tests pass
