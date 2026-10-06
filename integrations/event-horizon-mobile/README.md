# Event Horizon Mobile integration

## Role in AFKO

Event Horizon Mobile is the local runtime layer for zero-budget, offline-first mobile execution.

It matches the architecture described for AFKO: a device-local control plane with separate execution roles, local messaging, budget tracking, and code validation before execution.

## Why this matters

AFKO needs a constrained execution environment that can:

- run safely on low-resource devices
- avoid unrestricted shell execution
- keep messages local via Unix domain sockets
- record budgets and audit actions in SQLite
- progressively expand into multi-agent orchestration without turning into an unmanaged sandbox

## Expected use in AFKO

- mobile runtime bootstrap and orchestration shell
- task ledger and scheduler integration
- local UDS bus for agent communication
- AST-based safety scanner and execution guardrails

## Source

- upstream repo: https://github.com/propain09999-star/event-horizon-mobile

## Notes

This is a foundational component of the offline-first path and should be treated as a core integration, not an optional addon.
