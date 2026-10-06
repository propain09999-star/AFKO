# AFKO integration stack

This repository is the orchestration layer for a local-first autonomous engineering environment. The active subsystems are organized into a small, explicit integration graph rather than a pile of unrelated forks.

## Core architecture

AFKO coordinates five layers:

1. Local-first execution and repo processing
   - `core/` and `TPF`
   - `afko_engine.py`
   - `kismet_cloud_ingress.py`

2. Mobile and offline execution
   - `event-horizon-mobile` integration
   - Termux + tmux runtime, SQLite task ledger, local UDS bus

3. Agent communication and memory
   - `buzz` integration
   - signed event relay for agents, humans, workflows, and git events

4. External context and intelligence
   - `worldmonitor` integration
   - geopolitical, financial, and operational awareness

5. Optional decentralized compute/reward layer
   - `bittensor` integration
   - rewards, trust, and network-style coordination where useful

## Priority order

1. `buzz`
2. `event-horizon-mobile`
3. `worldmonitor`
4. `bittensor`
5. optional supporting repos only when they solve a concrete functional gap

## Why these integrations matter

- `buzz` gives AFKO a shared room model for humans and agents, with event signing and auditability.
- `event-horizon-mobile` gives AFKO a zero-budget offline execution plane for phones and low-power devices.
- `worldmonitor` gives AFKO real-world situational awareness without tying decisions to external API credit limits.
- `bittensor` is an optional trust/reward mechanism and can be used as a local compute or incentive layer rather than a hard dependency.

## Rule of thumb

Do not add random forks as first-class components just because they exist. Every integration must answer one of these questions:

- Does it reduce dependence on cloud credits or external API limits?
- Does it improve local autonomous execution?
- Does it give AFKO better agent coordination or auditability?
- Does it provide local intelligence, trust, or runtime safety that the base repo lacks?

If it fails those checks, leave it out of the active stack.
