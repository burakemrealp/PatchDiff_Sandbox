# PatchDiff Sandbox

[![Live Web App](https://img.shields.io/badge/Live%20Web%20App-patchdiff--sandbox.pages.dev-0ac8b9?logo=cloudflarepages&logoColor=white)](https://patchdiff-sandbox.pages.dev) [![Version: v2.0.1](https://img.shields.io/badge/Version-v2.0.1-10b981)](CHANGELOG.md) [![Language: English](https://img.shields.io/badge/Language-English-0ea5e9)](#) [![Dil: Türkçe](https://img.shields.io/badge/Dil-T%C3%BCrk%C3%A7e-ef4444)](README.tr.md) [![License: MIT](https://img.shields.io/badge/License-MIT-f59e0b)](LICENSE) [![Riot Compliance: Zero-Vanguard](https://img.shields.io/badge/Riot%20Compliance-Zero--Vanguard-6366f1)](SECURITY.md)

**English** | [Türkçe](README.tr.md) | **[Open Live Web App →](https://patchdiff-sandbox.pages.dev)**

A deterministic **League of Legends** patch analysis engine, Level 1–20 combat & Effective Health (EHP) simulator, and AI-assisted build + full 9-slot rune optimizer — engineered to run **100% independent of the game client and Riot Vanguard**.

![PatchDiff Sandbox Showcase](frontend/public/og-banner.png)

---

## Core Capabilities

- **Deterministic Level 1–20 Combat Simulator (`combat_simulator.py`, `damage_calculator.py`, `stat_aggregator.py`):**
  Computes per-level Effective Health (EHP), burst combo damage, sustained DPS using NumPy curves, armor/magic penetration breakdowns, **`13` modeled keystones**, and **`17` item passive effects** across patch versions.
- **Kit-Aware AI Build & Full Rune Page Lab (`build_optimizer.py`, `full_rune_page_engine.py`, `ai_build_advisor.py`):**
  Ranks multi-item core builds and full 9-slot Season 16 rune pages (keystone, 3 primary shards, 2 secondary shards, 3 stat shards) tailored to champion kit archetypes and target enemy resist/threat profiles. Supports OpenAI-compatible LLM explanations (`groq`, `openai`, `deepseek`) with a zero-cost `offline` fallback and user variation feedback tracking.
- **Zero-Day Meta Oracle & Patch Mythbuster (`zero_day_oracle.py`, `socialCardRenderer.ts`):**
  Scans the full champion roster on Day 0 before match statistics exist to detect unlisted indirect item/rune winners and losers, expose deceptive patch myths (`TRAP_BUFF_NET_NERF`, `HIDDEN_NET_BUFF`, `PLACEBO_BUFF`, `PAPER_TIGER_NERF`), and export `1200×630` PNG social summary cards.
- **Official ARAM Modifiers & PvE Waveclear/Objective Lab (`aram_balance_service.py`, `pve_lab_engine.py`):**
  Applies per-champion official ARAM damage/defense/haste/shield multipliers in ARAM mode and evaluates Minute `5 / 9 / 14` caster minion one-shot breakpoints alongside Elemental Dragon, Atakhan, and Baron Nashor solo kill speeds.
- **Win-Rate Trap Detector & 3-Way Game-State Pivots (`game_state_pivot_engine.py`):**
  Flags survivorship-bias trap purchases (such as *Mejai's Soulstealer* or 3500g+ zero-defense luxury walls when behind), recommends cost-effective comeback swaps, and compares dynamic `behind` / `even` / `ahead` build paths.
- **Automatic Riot Patch Sync & Meta Diff Engine (`ddragon_sync.py`, `cdragon_enricher.py`, `patch_diff_engine.py`, `meta_shift_analyzer.py`):**
  Fetches official Riot Data Dragon champion/item/rune snapshots alongside CommunityDragon spell calculations under a thread-safe concurrency lock, builds structured diffs between consecutive patches (for example `16.22.1` vs `16.23.1`), and optionally extracts structured deltas from raw patch notes text (`POST /api/v1/parse-patch`).
- **25 Official LoL UI Locales, Dual Hextech Themes & Mobile-Ready UX (`locale_service.py`, `ThemeProvider.tsx`):**
  Translates UI chrome and backend simulation/build labels across **all `25` official `leagueoflegends.com` locales** (including RTL `ar_AE`), supports auto-detected Dark (*Hextech Twilight*) and Light (*Piltover Daylight*) themes compliant with EU `EN 301 549` / `WCAG 2.1 AA`, and adapts cleanly to mobile screens.
- **Strict Client-Free / Zero-Vanguard Safety:**
  Never hooks into the League client, reads game process memory, injects overlays, or automates inputs. Operates purely on public static patch data and user-selected sandbox scenarios.

---

## Architecture

```mermaid
flowchart TD
    UI["React 19 + TypeScript + Vite Dashboard"] --> API["FastAPI REST API (/api/v1)"]
    API --> ENG["Combat Simulator & Build Optimizer (NumPy)"]
    API --> SYNC["Patch Sync & Diff Pipeline"]
    API --> ADV["AI Build Advisor & Locale Service (25 Locales)"]
    ENG --> PG["PostgreSQL 16 (Snapshots, Runes, Diffs, Logs)"]
    SYNC --> PG
    API --> RED["Redis 7 (Simulation & Recommendation Cache)"]
    SYNC --> DD["Riot Data Dragon CDN"]
    SYNC --> CD["CommunityDragon JSON"]
    ADV --> LLM["OpenAI-Compatible LLM Provider (Optional / Offline Fallback)"]
```

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python `3.12+`, FastAPI `0.115.5`, Uvicorn `0.32.0`, Pydantic `2.9.2`, NumPy `2.1.3`, HTTPX `0.27.2` |
| **Database & Cache** | SQLAlchemy `2.0.36`, PostgreSQL `16` (`psycopg 3.2.3`), Redis `7` (`redis 5.2.0`) |
| **Frontend** | React `19`, TypeScript `6`, Vite `8`, Tailwind CSS `v4`, Recharts `3`, Lucide Icons |
| **Data Sources** | Riot Data Dragon CDN, CommunityDragon static assets, OpenAI-compatible LLM endpoints |
| **Testing & QA** | Pytest `8.3.4`, ESLint + TypeScript type checking (`tsc -b`) |

---

## Quick Start

### Prerequisites

- **Python** `3.12+`
- **Node.js** `20+` and `npm`
- **Docker** & **Docker Compose** (for local PostgreSQL 16 and Redis 7 containers)

### 1. Start PostgreSQL and Redis

From the repository root:

```bash
docker compose up -d
```

This starts `patchdiff_postgres` on port `5432` (`user: patchdiff`, `db: patchdiff_db`) and `patchdiff_redis` on port `6379`.

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and adjust values as needed:

```bash
cp .env.example .env
```

Key environment variables in [`.env.example`](.env.example):

| Variable | Description | Example / Default |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL SQLAlchemy connection URI | `postgresql+psycopg://patchdiff:patchdiff_secret@localhost:5432/patchdiff_db` |
| `REDIS_URL` | Redis cache connection URI | `redis://localhost:6379/0` |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins | `http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000` |
| `LLM_PROVIDER` | AI explanation mode (`groq`, `openai`, `deepseek`, or `offline`) | `offline` (zero-key mode) or `groq` |
| `LLM_BASE_URL` | OpenAI-compatible base URL | `https://api.groq.com/openai/v1` |
| `LLM_API_KEY` | Provider API key (unused when `LLM_PROVIDER=offline`) | `your_llm_api_key_here` |
| `LLM_MODEL` | Target chat completion model | `openai/gpt-oss-20b` |
| `DDRAGON_VERSION` | Initial Riot Data Dragon patch version | `16.23.1` |
| `DDRAGON_LANG` | Default Riot Data Dragon locale | `tr_TR` |
| `AUTO_SYNC_ENABLED` | Enable background patch checks | `true` |
| `AUTO_SYNC_INTERVAL_MINUTES` | Background sync polling interval | `360` |

> [!TIP]
> **100% Free Offline Mode:** Set `LLM_PROVIDER=offline` in `.env` to run the entire deterministic simulator, optimizer, and patch pipeline with **no external LLM API key required**.

### 3. Set Up & Run the Backend

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment:

- **Windows (PowerShell):** `.\.venv\Scripts\Activate.ps1`
- **macOS / Linux:** `source .venv/bin/activate`

Install dependencies, initialize tables, optionally seed baseline entities, and launch FastAPI:

```bash
pip install -r requirements.txt
python -m app.init_db
python -m app.seed_data   # Optional: populates starter champion/item definitions
uvicorn app.main:app --reload
```

Backend API will be served at `http://127.0.0.1:8000` (Swagger UI at `/docs`).

### 4. Set Up & Run the Frontend

In a second terminal from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open the local Vite dev URL (typically `http://localhost:5173`) in your browser.

---

## REST API Overview

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `GET` | `/` | Service metadata & version (`2.0.1`) |
| `GET` | `/api/v1/health` | Health check (database & Redis connectivity) |
| `GET` | `/api/v1/champions` | List synced champions with localized names & base stats |
| `GET` | `/api/v1/items` | List synced Summoner's Rift items & icon metadata |
| `POST` | `/api/v1/parse-patch` | Parse raw patch note text into structured numeric deltas |
| `POST` | `/api/v1/simulate` | Run Level 1–20 patch A/B combat & EHP simulation |
| `GET` | `/api/v1/patches/latest` | Fetch latest synced patches & auto-generated diff feed |
| `POST` | `/api/v1/patches/sync` | Trigger Riot Data Dragon + CommunityDragon synchronization |
| `GET` | `/api/v1/patches/zero-day-radar` | Run full-roster Day-0 indirect impact scan & mythbuster radar |
| `GET` | `/api/v1/patches/{version}/diffs` | Retrieve structured diffs for a specific patch version |
| `POST` | `/api/v1/recommend-builds` | Generate ranked builds, 9-slot runes, trap alerts & 3-state pivots |
| `POST` | `/api/v1/pve-lab` | Compute Minute 5/9/14 waveclear & Dragon/Atakhan/Baron solo DPS |
| `POST` | `/api/v1/feedback` | Record user feedback (`accepted` / `rejected`) on build variations |
| `GET` | `/api/v1/feedback/summary` | Inspect aggregated variation preference metrics |

---

## Verification & Quality Checks

Run the full automated suite before committing or opening a pull request:

```bash
# Backend unit & integration test suite (offline isolated SQLite + mocked Redis)
cd backend
python -m pytest

# Frontend lint & production TypeScript/Vite build
cd ../frontend
npm run lint
npm run build
```

---

## Roadmap (Zero-Vanguard Architecture)

PatchDiff Sandbox follows a phased open-source evolution designed to stay compliant with Riot Games Developer Policies:

- **`v1.0.0` (Completed):** Full-stack patch simulator, Data Dragon + CommunityDragon auto-sync pipeline, AI build & 9-slot rune lab, 25 official LoL locales, and MIT open-source repository foundation.
- **`v2.0.0` (Current Release — Wave 1 Client-Free Meta Intelligence):** Zero-Day Meta Oracle & Patch Mythbuster radar (`1200×630` PNG studio), official per-champion ARAM balance multipliers, Minute 5/9/14 PvE waveclear & epic objective lab, and Win-Rate Trap Detector with 3-way Ahead/Even/Behind dynamic build pivots.
- **`v2.5.0` (Wave 2 — Desktop LCU / Live Client Companion & Practical Tools):** Tauri companion integration, gold breakpoint coach with native LoL Item Set JSON export, and 5v5 survival/CC tenacity matrix.
- **`v3.0.0` (Wave 3 — Official Riot Match-V5 Post-Game Audit):** Server-side post-match timeline comparison ("Shopkeeper Audit") powered exclusively by official Riot Production API keys.

---

## Contributing & Security

- Read [CONTRIBUTING.md](CONTRIBUTING.md) for codebase rules (100% English source/comments, zero champion hardcoding, and test standards).
- Review [SECURITY.md](SECURITY.md) for secret hygiene, Riot Vanguard compliance rules, and responsible vulnerability reporting.
- History of notable changes is tracked in [CHANGELOG.md](CHANGELOG.md).

---

## License

Released under the [MIT License](LICENSE).

---

## Legal Disclaimer

PatchDiff Sandbox isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc.
