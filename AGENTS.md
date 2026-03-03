# Repository Guidelines

## Project Structure & Module Organization
- `microecon/`: core simulation library (agents, bargaining, matching, logging, analysis).
- `server/`: FastAPI WebSocket backend used by the web UI.
- `frontend/`: React/Vite UI; main code under `frontend/src/` (components, hooks, store).
- `tests/`: pytest suite; theory tests in `tests/theory/`, scenario tests in `tests/scenarios/`.
- `scenarios/`: YAML scenario definitions; `docs/`: PRDs and design notes; `scripts/`: dev helpers.

## Build, Test, and Development Commands
- `uv sync`: install Python deps (Python 3.12+).
- `uv run pytest`: run all Python tests.
- `uv run pytest --cov=microecon`: run tests with coverage.
- `./scripts/dev.sh`: start backend + frontend together.
- `uv run uvicorn server.app:create_app --factory --port 8000`: start backend only.
- `cd frontend && npm install`: install frontend deps (Node 18+).
- `cd frontend && npm run dev`: start Vite dev server.
- `cd frontend && npm run build`: build frontend bundle.
- `cd frontend && npm run lint`: run ESLint for TS/React.

## Coding Style & Naming Conventions
- Python: 4-space indentation; snake_case for functions/variables; PascalCase for classes.
- Tests: name files `test_*.py`; keep theory tests in `tests/theory/`.
- Frontend: TypeScript/React with semicolons and 2-space indentation; components in PascalCase, hooks as `useX`.
- Linting: ESLint config lives in `frontend/eslint.config.js`.

## Testing Guidelines
- Framework: pytest (configured in `pyproject.toml`).
- Mark slow tests with `@pytest.mark.slow` when appropriate.
- No frontend test runner is configured; rely on `npm run lint` and manual UI checks.

## Commit & Pull Request Guidelines
- Commit history uses patterns like `feat(scope): ...`, `test(scope): ...`, `Fix ...`, `Phase N: ...`, and version tags such as `v0.3.0: ... (#4)`. Follow a similar, imperative summary and include scope when helpful.
- PRs: include a short summary, tests run (or reason not run), link relevant issues/PRDs, and add screenshots or GIFs for UI changes.

## Documentation & Research Grounding
- Align changes with `VISION.md` and current constraints in `STATUS.md`.
- New protocols or behavioral rules should reference theoretical foundations in `theoretical-foundations.md` or related docs.
