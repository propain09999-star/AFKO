# AFKO Integrations

This directory keeps the active cross-project integrations in a structured and deliberate format.

## Active stack

- **buzz** — human + agent collaboration relay and event-backed workspace memory
- **event-horizon-mobile** — offline mobile runtime and local control plane
- **worldmonitor** — global situational awareness and intelligence feeds
- **bittensor** — optional decentralized compute / scoring / reward substrate

## Why they are in the stack

### buzz
Purpose: shared event log and agent coordination layer.
Benefits:
- signed audit trail
- community memory and shared workspaces
- agent identities separate from user identities
- workflow and git activity visible in one log

### event-horizon-mobile
Purpose: mobile-first local execution environment.
Benefits:
- Termux-native runtime
- tmux session partitioning
- local UDS messaging
- AST safety validation before execution
- budgeted local task execution

### worldmonitor
Purpose: context layer for geopolitics, finance, conflict, cyber, and operational awareness.
Benefits:
- local and remote intelligence without ad-hoc API glue
- agent-readable structured signals
- real-world situational awareness for reasoning loops

### bittensor
Purpose: optional trust and reward infrastructure.
Benefits:
- incentive layer for local compute and model contribution
- subnet-style coordination patterns
- decentralized model or reward experiments

## Integration policy

The project only keeps integrations that satisfy these heuristics:

- local-first
- low external dependency cost
- security- and audit-friendly
- directly support AFKO's autonomous workflow or runtime goals

If a repo does not clearly map to one of those properties, it stays out of the active integration set.
