# Contributing to PatchDiff Sandbox

Thank you for contributing to **PatchDiff Sandbox**! This project aims to stay clean, deterministic, Riot-compliant, and easy for global contributors to read and extend.

## Core Engineering Rules

1. **100% English Codebase:**
   All source files, identifiers, comments, docstrings, CLI logs, OpenAPI strings, and commit messages must be written in clear English. Localized display text belongs exclusively inside [`locale_service.py`](backend/app/services/locale_service.py) and `frontend/src/i18n/*`.
2. **Zero Champion Hardcoding:**
   Do not hardcode single-champion special cases (`if champion == "..."`) inside core engines (`combat_simulator.py`, `build_optimizer.py`, `damage_calculator.py`, `cdragon_enricher.py`). All mechanics must resolve dynamically from Riot Data Dragon / CommunityDragon attributes and kit profiles.
3. **25-Locale Integrity:**
   Ensure new user-facing UI keys or backend rationale labels gracefully support all `25` official Riot locales without breaking right-to-left (`ar_AE`) rendering or falling back to untranslated debug tokens.
4. **Client-Free / Zero-Vanguard Boundary:**
   Contributions must never touch League of Legends client files, process memory, overlays, or input automation. Only static patch data and user-driven sandbox simulations belong in this repository.

## Development Workflow

### Prerequisites

- Python `3.12+`
- Node.js `20+` and `npm`
- Docker (optional for local PostgreSQL 16 + Redis 7 via [`docker-compose.yml`](docker-compose.yml))

### Local Verification Checklist

Run every verification command locally and verify `0` failures before submitting a Pull Request:

```bash
# 1. Backend tests (isolated in-memory SQLite + mocked Redis)
cd backend
python -m pytest

# 2. Frontend ESLint & TypeScript/Vite build
cd ../frontend
npm run lint
npm run build
```

## Commit & Pull Request Guidelines

- Follow **Conventional Commits** where practical (e.g., `feat(engine): ...`, `fix(i18n): ...`, `docs: ...`, `ci: ...`).
- Keep PRs focused on a single concern and avoid mixing formatting churn with behavioral changes.
- Never include `.env`, API tokens, database dumps, or local personal documents in commits.
- Summarize what changed and include observed test/lint outputs in your PR description.
