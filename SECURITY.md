# Security Policy

## Supported Versions

| Version | Supported |
| :--- | :--- |
| `1.0.x` | Yes |
| `< 1.0.0` | No (pre-release / legacy drafts) |

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities, exposed credentials, or exploit paths.

Instead:
1. Use GitHub **Private Vulnerability Reporting** under the repository's **Security -> Advisories** tab to submit details privately.
2. Include steps to reproduce, affected files/endpoints, and potential impact.
3. Expect an initial acknowledgment within 72 hours while the issue is investigated and patched before coordinated disclosure.

## Riot Games & Vanguard Compliance Rules

PatchDiff Sandbox is strictly **client-independent** by design:
- **Zero Game Client Hooks:** Pull requests or forks must never attach to League of Legends processes, read game memory, inject overlays, automate inputs, or bypass Riot Vanguard.
- **Public Static & Approved Data Only:** Simulation and optimization rely exclusively on public Riot Data Dragon / CommunityDragon static datasets and user-provided sandbox inputs.

## Secret & Environment Hygiene

- **Never commit `.env` files** or real API keys (`LLM_API_KEY`, database passwords, Riot API keys) to Git history. Only commit sanitized templates via [`.env.example`](.env.example).
- Keep `DEBUG=false` in production deployments and use restricted credentials for PostgreSQL and Redis.
- Use `LLM_PROVIDER=offline` when running without external API credentials or in untrusted/CI environments.
