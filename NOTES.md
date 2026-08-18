# AFKO Local-First Project Notes

## Goal
Build AFKO as a local-first development and repo tooling environment that can:
- work with locally cloned repositories
- use GitHub as host/storage only when needed
- avoid dependence on external service credit limits or token-based APIs where possible
- preserve planning and progress inside the repo history

## Current status
- `github_auth.py` added to centralize GitHub token handling
- Existing scripts now support unauthenticated GitHub access fallback
- `TPF` contains a prototype repository crawler and local AST extraction pipeline
- `kismet_cloud_ingress.py` contains GitHub repo ingestion plus local data caching
- `kismet_boot.sh` currently clones/syncs a GitHub repo and launches a local service

## Local-first strategy
1. Prefer local repository clones and `git` operations over GitHub API calls.
2. Use GitHub only as remote repo hosting or for metadata when necessary.
3. Make GitHub auth optional and fall back to anonymous/public access with reduced rate limits.
4. Keep secrets out of source control; use environment variables and `.env.template` only.
5. Track the plan in source-controlled notes so progress is visible and reproducible.

## Useful patterns
- `git clone` / `git pull` / local checkout parsing
- `os.walk()` for scanning repository files locally
- `sqlite3` or local caches for storing extracted data
- optional `GITHUB_TOKEN` for improved GitHub API rate limits
- anonymous API access only when no token is configured

## Immediate next work
- Refactor `TPF` to support local-only pipeline mode
- Refactor `kismet_cloud_ingress.py` to optionally read from a local repo path instead of always using GitHub contents API
- Update `kismet_boot.sh` to support a local repo directory and a configurable host-only flow
- Add `.gitignore` entries for unrelated downloaded directories or data bundles if desired
- Keep `NOTES.md` and any `Bittensor` research notes under source control

## Bittensor research note
Bittensor is a potential future direction for building decentralized model services and local inference networks. A useful starting point is:
- research how Bittensor interacts with local model nodes and peers
- determine whether Bittensor can be used as a local/self-hosted assistant layer instead of Copilot
- scope it as a separate module or experimental branch

## Action items
- [ ] Keep this file up to date with design decisions
- [ ] Commit local-first refactors separately from unrelated data
- [ ] Avoid pulling large external datasets into the repo unless they are intentionally part of the project
- [ ] Separate notes, downloads, and external repos from core AFKO source code

## Notes
- The Copilot/credits limit is an editor/service issue, not a repo code issue.
- This repo can continue development without external billing if local tooling is the primary workflow.
