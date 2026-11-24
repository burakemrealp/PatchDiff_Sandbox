## Summary

<!-- Briefly describe what this pull request changes and why. -->

## Related Issue

<!-- Link related issue(s), e.g., Fixes #123 -->

## Type of Change

- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Simulation / optimizer math update
- [ ] Documentation or localization update
- [ ] CI / build / repository maintenance

## Verification Results

Run locally before requesting review and summarize the observed results:

- [ ] `cd backend && python -m pytest` (all tests pass)
- [ ] `cd frontend && npm run lint` (`0` errors, `0` warnings)
- [ ] `cd frontend && npm run build` (`tsc -b && vite build` succeeds)

## Engineering & Security Checklist

- [ ] Code, identifiers, comments, docstrings, and logs are **100% English**.
- [ ] Zero per-champion hardcoded branches inside core combat/optimizer/diff engines.
- [ ] User-facing changes remain compatible across all `25` official LoL UI locales (including `ar_AE` RTL).
- [ ] Strictly **client-free / Zero-Vanguard** (no client process hooks, memory access, overlays, or automation).
- [ ] No `.env`, API keys, credentials, or personal files included.
