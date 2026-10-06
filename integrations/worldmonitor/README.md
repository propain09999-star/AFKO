# World Monitor integration

## Role in AFKO

World Monitor supplies external situational awareness to the AFKO stack.

It gives the system a structured way to ingest geopolitical, cyber, market, and disaster signals so agents can reason about what is happening in the world, not just inside the repo.

## Why this matters

AFKO is not only a code-processing engine. It must also support:

- emergent issues and operational risk awareness
- structured feed aggregation
- world-state correlation against repo changes and local tasks
- agent-friendly intelligence retrieval without building ad-hoc scraping pipelines

## Expected use in AFKO

- intelligence feeds for decision-support agents
- risk and scenario monitoring
- context source for planner and escalation agents
- model-to-world grounding for local reasoning loops

## Source

- upstream repo: https://github.com/koala73/worldmonitor (original)
- fork: https://github.com/propain09999-star/worldmonitor

## Notes

Use this as a supporting intelligence layer. It should not replace local repo analysis, but it strengthens the decision context around operational and strategic events.
