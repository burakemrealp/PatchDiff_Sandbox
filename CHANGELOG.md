# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.1] - 2026-11-27

### Added
- **Hextech Dark & Light Dual-Theme System ([ThemeProvider.tsx](frontend/src/theme/ThemeProvider.tsx), [index.css](frontend/src/index.css)):** Added automatic `prefers-color-scheme` detection plus a circular header switcher toggling between **Hextech Twilight** (navy + gold + teal) and **Piltover Daylight** (pearl + sapphire), engineered to meet EU `EN 301 549` / `WCAG 2.1 AA` (`>= 4.5:1`) contrast, keyboard `:focus-visible` rings, and `prefers-reduced-motion` accessibility rules.
- **Unified Hextech Diff-Crystal Brand Identity & SEO ([BrandCrest.tsx](frontend/src/components/BrandCrest.tsx), [index.html](frontend/index.html)):** Replaced starter Vite icons with a unified octagonal Hextech Diff-Crystal emblem (`favicon.svg`, `apple-touch-icon.png`), added a `1200×630` slogan preview banner ([og-banner.png](frontend/public/og-banner.png)), OpenGraph / X `summary_large_image` tags, `JSON-LD` schema, `robots.txt`, `sitemap.xml`, and circular header GitHub link.
- **25-Locale Showcase Navigation & Plain-Language Tooltips ([FeatureShowcaseNav.tsx](frontend/src/components/FeatureShowcaseNav.tsx), [translationsPolish.ts](frontend/src/i18n/translationsPolish.ts)):** Redesigned the 4 top module tabs into concise highlight tiles with click-safe hover/keyboard tooltips explaining each capability clearly for players of all ranks.
- **Footer Version & Open-Source Attribution ([App.tsx](frontend/src/App.tsx)):** Added `PatchDiff Sandbox v2.0.1 · Open Source (MIT)` and repository link above the Riot Legal Jibber Jabber disclaimer.

### Changed
- **Mobile-First Responsive UX Overhaul:** Added a compact 2×2 mobile feature grid, pinned mobile header controls, horizontal swipe strips for changed champions and sub-tabs, 3-state segmented mobile tab switcher inside [PivotAndTrapsPanel.tsx](frontend/src/components/PivotAndTrapsPanel.tsx), full-width mobile search/CTA controls, viewport collision clamping across all 25 locales in [LanguageSelector.tsx](frontend/src/components/LanguageSelector.tsx), and concise `<title>PatchDiff Sandbox</title>`.
- **Social Card Studio Live Attribution ([socialCardRenderer.ts](frontend/src/utils/socialCardRenderer.ts)):** Upgraded the downloadable `1200×630` PNG card to Hextech Twilight styling with the Diff-Crystal crest and added `https://patchdiff-sandbox.pages.dev` to both PNG exports and one-click Reddit/Discord copy summaries.
- **Showcase Documentation & Domain Verification:** Added `riot.txt` domain verification, live `patchdiff-sandbox.pages.dev` badges, preview banner embeds in [README.md](README.md) & [README.tr.md](README.tr.md), and bumped project version parity to `2.0.1`.

## [2.0.0] - 2026-11-26

### Added
- **Zero-Day Meta Oracle & Patch Mythbuster (`zero_day_oracle.py`, `GET /api/v1/patches/zero-day-radar`, `ZeroDayRadarPanel.tsx`):** Scans the full champion roster on Day 0 before post-patch match statistics exist to uncover unlisted indirect winners/losers caused by item and rune ecosystem changes, and exposes deceptive patch myths (`TRAP_BUFF_NET_NERF`, `HIDDEN_NET_BUFF`, `PLACEBO_BUFF`, `PAPER_TIGER_NERF`, `MODE_SPECIFIC_TRAP`).
- **Viral Social Card Studio (`socialCardRenderer.ts`):** Generates client-side `1200×630` HiDPI PNG patch summary cards in the active LoL locale plus one-click formatted Reddit/Discord/X summaries.
- **Official ARAM Champion Balance Modifiers (`aram_balance_service.py`, `aram_overrides.json`, `AramModifiersBar.tsx`):** Parses and caches Riot's official ARAM per-champion multipliers (`dmg_dealt`, `dmg_taken`, `healing`, `shielding`, `ability_haste`, `total_as`, `tenacity`, `energyregen_mod` across `174` champion entries, `134` with active overrides) directly inside combat simulations, AI build scoring, and PvE benchmarks when `game_map="aram"`.
- **PvE Minion Waveclear & Epic Objective Breakpoint Lab (`pve_lab_engine.py`, `POST /api/v1/pve-lab`, `PvELabDrawer.tsx`):** Evaluates Minute `5 / 9 / 14` caster minion one-shot thresholds, missing AP/AD margins, full-wave clear duration, and Elemental Dragon / Atakhan / Baron Nashor solo kill DPS with monster damage caps.
- **Win-Rate Survivorship Trap Detector & 3-Way Game-State Pivot Tree (`game_state_pivot_engine.py`, `PivotAndTrapsPanel.tsx`):** Audits items for survivorship-bias traps (`STACKING_SNOWBALL_TRAP`, `LUXURY_GOLD_WALL_TRAP`, `FLAT_PEN_EXECUTION_TRAP`), suggests cost-effective comeback alternatives, and computes dynamic `behind` / `even` / `ahead` build pivots (`game_state` parameter on `POST /api/v1/recommend-builds`).
- **Full Wave 1 25-Locale Localization (`locale_service.py`, `translationsZeroDay.ts`, `translationsWave1.ts`):** Localized Zero-Day verdicts, PvE monster & scaling stat labels, win-rate trap explanations, and UI controls across all `25` official LoL locales.
- **Zero-Cost Cloud Deployment Support:** Added `normalize_database_url` in `database.py` (supporting Neon/Render `postgres://` and `postgresql://` URIs via `psycopg` v3), configurable `CORS_ORIGINS`, Render free-tier Blueprint ([render.yaml](render.yaml)), and Cloudflare Pages SPA routing ([frontend/public/_redirects](frontend/public/_redirects)).

### Changed
- Upgraded release version parity to `2.0.0` across [backend/app/main.py](backend/app/main.py), [frontend/package.json](frontend/package.json), and [frontend/package-lock.json](frontend/package-lock.json).
- Configured Vite 8 / Rolldown chunk splitting (`react-vendor`, `charts-vendor`, `icons-vendor`, `i18n-bundles`) and `React.lazy` panel loading in [frontend/vite.config.ts](frontend/vite.config.ts) and [frontend/src/App.tsx](frontend/src/App.tsx) to keep every production JS chunk under `500 kB`.

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
