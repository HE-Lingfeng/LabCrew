# LabCrew

LabCrew is a multi-agent research assistant for graduate research workflows: read papers, create literature cards, manage Zotero items, generate slide decks, and draft research proposals.

## Using LabCrew

Prefer the `labcrew` MCP server tools. When MCP is unavailable, fall back to the CLI:

```bash
python -m labcrew <command> [args]
```

Key commands: `read-paper`, `make-card`, `make-slides`, `propose-research`, `design-experiment`, `zotero {list,read,plan,status}`.

## Safety

- Only sync to Notion / create card files / update Zotero status when the user explicitly asks.
- If a tool returns `ok: false`, report the error clearly and suggest a fix.
