# Buzz integration

## Role in AFKO

Buzz provides the collaboration and audit substrate for the AFKO agent stack.

It is not just a chat app. It is a room model where humans and agents can coordinate around a shared event log, with project memory and workflow activity tied to the same signed stream.

## Why this matters

AFKO needs an explicit coordination layer so that:

- agents can operate in rooms and channels
- actions are auditable and reviewable
- code changes, approvals, and workflow results are tied to one event stream
- agent output can be validated against historical context rather than pure prompt memory

## Expected use in AFKO

- agent channels for helper, killer, and planner agents
- workflow triggers and approvals
- memory retrieval and local action receipts
- relay-backed coordination for multi-agent collaboration

## Source

- upstream repo: https://github.com/block/buzz (original)
- fork: https://github.com/propain09999-star/buzz

## Notes

Buzz should remain a system boundary, not a monolith dropped into AFKO's runtime. It is the communication layer, not the engine itself.
