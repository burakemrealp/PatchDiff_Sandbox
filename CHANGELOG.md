# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-11-24

### Added
- Deterministic Level 1–20 combat and Effective Health (EHP) simulator (`combat_simulator.py`, `damage_calculator.py`, `stat_aggregator.py`) with armor/magic penetration curves, NumPy DPS modeling, `13` keystones, and `17` modeled item passives.
- Kit-aware and playstyle-aware AI Build & Full 9-Slot Rune Optimizer (`build_optimizer.py`, `full_rune_page_engine.py`, `ai_build_advisor.py`) supporting OpenAI-compatible LLM providers (`groq`, `openai`, `deepseek`) and a zero-key `offline` fallback mode.
- Thread-safe Riot Data Dragon + CommunityDragon synchronization pipeline (`ddragon_sync.py`, `cdragon_enricher.py`, `patch_sync_orchestrator.py`, `patch_diff_engine.py`, `meta_shift_analyzer.py`) with automated consecutive patch diffs and LLM patch-note extraction (`POST /api/v1/parse-patch`).
- Full frontend & backend localization across all `25` official `leagueoflegends.com` locales (`locale_service.py` and `frontend/src/i18n/*`), including right-to-left (`ar_AE`) layout support.
- User variation feedback persistence and analytics endpoints (`POST /api/v1/feedback`, `GET /api/v1/feedback/summary`).
- Client-free, zero-Vanguard React 19 + TypeScript 6 + Vite 8 + Tailwind CSS v4 + Recharts 3 web dashboard (`frontend/src/*`).
- Bilingual showcase documentation ([README.md](README.md), [README.tr.md](README.tr.md)), MIT [LICENSE](LICENSE), [SECURITY.md](SECURITY.md), and [CONTRIBUTING.md](CONTRIBUTING.md).

### Changed
- Standardized all backend and frontend codebase identifiers, comments, docstrings, CLI logs, OpenAPI metadata, and prompts in English while keeping all `25` UI localization bundles intact.
- Unified backend (`app/main.py`) and frontend (`frontend/package.json`) metadata to release version `1.0.0`.
- Resolved all React 19 ESLint and Fast Refresh findings (`0` lint errors, `0` warnings) and removed legacy temporary test/starter files.

### Security
- Sanitized `.env.example` to strip secret placeholders cleanly, strengthened root and frontend `.gitignore` rules, and normalized cross-platform line endings via `.gitattributes`.
- Embedded official Riot Games Legal Jibber Jabber disclaimer into documentation and the web footer.
