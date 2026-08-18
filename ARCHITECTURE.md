# AFKO Architecture

## Purpose
AFKO is designed as a local-first development and repo processing system that:
- operates on local repository clones and optional large folders
- uses GitHub only for remote hosting or fallback repository discovery
- avoids dependency on external Copilot credit-based services
- supports unattended execution through a service wrapper

## Layers

### 1. Config / Environment
- `.env.template` provides example environment variables
- `NOTES.md` records strategy and project goals
- `ARCHITECTURE.md` documents the system structure
- environment variables include:
  - `AFKO_BOOT_MODE`
  - `AFKO_LOCAL_REPO_DIR`
  - `AFKO_PIPELINE_MODE`
  - `AFKO_QUERY_LIMIT`
  - `AFKO_START_RUNTIME`
  - `AFKO_SERVICE_LOG`

### 2. Discovery / Source
- Local repositories are discovered under `AFKO_LOCAL_REPO_ROOT`
- Optional large folders are kept out of source control via `.gitignore`
- GitHub repository discovery is optional and used only when necessary

### 3. Ingestion
- `kismet_cloud_ingress.py` ingests local repository files into SQLite
- local ingestion is preferred
- GitHub repository ingestion is a fallback when local copy is missing

### 4. Pipeline
- `TPF` contains the scan and remediation pipeline
- supports `local`, `github`, and `mixed` modes
- can discover local repos, clone remote repos, and scan Python files

### 5. Execution
- `afko_engine.py` orchestrates discovery, ingestion, pipeline execution, and runtime startup
- `run_local_service.sh` launches the engine using local config or `.env`
- `kismet_boot.sh` can start local runtime dependencies like Ollama

### 6. Service / Runtime
- the ideal local service should:
  - run unattended
  - log progress to `afko_service.log`
  - skip missing optional inputs cleanly
  - optionally start local runtime services

## File roles
- `github_auth.py` — GitHub token helper and API client abstraction
- `TPF` — local-first pipeline implementation for repo scanning and patching
- `kismet_cloud_ingress.py` — local/GitHub ingestion module
- `kismet_boot.sh` — bootstraps repo sync and local runtime
- `afko_engine.py` — execution engine and orchestration layer
- `run_local_service.sh` — simple local service wrapper
- `.gitignore` — ignores optional large folders and local artifacts
- `NOTES.md` — project plan and strategy

## Next steps
- add robust logging and error handling
- build a real local agent/runtime integration (e.g. Ollama, Bittensor)
- add a `systemd` unit or cron example for unattended execution
- separate large optional data into a dedicated `optional/` area if needed
