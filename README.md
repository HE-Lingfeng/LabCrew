# LabCrew

LabCrew is a multi-agent research assistant for graduate research workflows.

It is designed around a coordinator agent and focused subagents for reading papers, generating literature cards, discovering candidate research gaps, drafting writing, planning experiments, and preparing presentations. Integrations such as Zotero, Notion, GitHub, and presentation tools live behind adapter interfaces so the local workflow remains usable even when external services are disabled.

## Quick Start

```bash
python -m labcrew read-paper path/to/paper.txt
python -m labcrew make-card path/to/paper.txt
python -m labcrew make-slides path/to/card.md
python -m labcrew propose-research --source path/to/paper.txt
python -m labcrew design-experiment "agent planning under limited retrieval evidence"
```

The current implementation is a Phase 0 skeleton: routes, schemas, adapters, and workflows are present with mock or local-first behavior.

## Project Layout

```text
labcrew/
  agents/      Agent implementations and coordinator
  schemas/     Stable data contracts shared across agents
  tools/       External service and utility adapters
  memory/      Local storage and sync primitives
  workflows/   User-facing workflow composition
  evals/       Lightweight evaluation entry points
```
