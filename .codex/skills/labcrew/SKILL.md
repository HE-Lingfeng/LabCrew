---
name: labcrew
description: Use LabCrew for graduate research workflows: read local papers, create literature cards, inspect Zotero items or collections, sync reading status, draft research proposals, and generate slide plans through the LabCrew MCP server or CLI.
---

# LabCrew

Use this skill when the user asks Codex to work with LabCrew research workflows, papers, Zotero items, literature cards, Notion sync, reading status, proposals, or slides.

## Preferred Access

Prefer the LabCrew MCP server when available. Its tools return a stable envelope:

```json
{
  "ok": true,
  "data": {},
  "warnings": [],
  "artifacts": [],
  "error": null
}
```

If MCP tools are not available, use the CLI from the LabCrew workspace:

```bash
python -m labcrew read-paper path/to/paper.pdf
python -m labcrew make-card path/to/paper.pdf --cards
python -m labcrew zotero read ITEMKEY
python -m labcrew zotero plan --collection COLLECTIONKEY
python -m labcrew make-slides path/to/paper.pdf
```

## Tool Selection

- `read_paper`: summarize a local PDF or text paper.
- `deep_read_method`: explain method details.
- `make_card`: create a literature card; pass `save_to_cards=true` only when the user wants a local card.
- `read_zotero_item`: read a Zotero item by key.
- `plan_zotero_collection`: suggest a next reading batch from a Zotero collection.
- `update_reading_status`: update reading status; pass `sync_to_notion=true` only when the user wants Notion updated.
- `make_slides`: create a slide plan or HTML slide deck.
- `propose_research`: generate a proposal scaffold from a paper or seed question.

## Safety Defaults

- Do not sync to Notion unless the user explicitly asks.
- Do not create local card files unless the user explicitly asks.
- Do not update reading status unless the user explicitly asks.
- When reporting results, mention important warnings and artifact paths.
- If a tool returns `ok=false`, summarize `error` and suggest the smallest next check.

## MCP Setup Hint

For local stdio MCP clients, the server entry point is:

```bash
python -m labcrew.mcp_server
```

If the package is installed with scripts, `labcrew-mcp` is also available.
