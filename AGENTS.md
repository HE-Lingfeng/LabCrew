# Codex Agent Notes

This file is the first stop for Codex-style agents working in this repository.

## Start Here

Read `docs/CONTEXT.md` before opening broad project files. It is the compact map for LabCrew's architecture, common commands, runtime action registry, integrations, and debugging entry points.

Then open only the task-relevant files. The usual path is:

1. `labcrew/main.py` for CLI behavior.
2. `labcrew/runtime.py` for action dispatch.
3. `labcrew/mcp_server.py` for MCP tool exposure.
4. `labcrew/workflows/` for user-facing behavior.
5. `labcrew/agents/`, `labcrew/schemas/`, and `labcrew/tools/` for implementation details.

## Working Rules

- Keep changes local to the requested behavior.
- Prefer existing schemas, workflows, and adapter boundaries over new ad hoc dicts.
- External services belong behind adapters in `labcrew/tools/`.
- Do not sync Notion, create local card files, or update Zotero status unless the user explicitly asks.
- Do not touch `.env*`, ignored `data/` runtime outputs, caches, or unrelated untracked files.
- Use `pytest` or targeted tests when code behavior changes.

## Useful Commands

```bash
python -m labcrew read-paper path/to/paper.txt
python -m labcrew make-card path/to/paper.txt --cards
python -m labcrew make-slides path/to/paper.txt --format html
python -m labcrew zotero list --limit 20
pytest
```
