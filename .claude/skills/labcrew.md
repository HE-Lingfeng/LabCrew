---
name: labcrew
description: Use LabCrew for graduate research workflows: read papers, create literature cards, Zotero management, research proposals, and slide generation.
---

# LabCrew

Use this skill when the user asks to work with papers, Zotero, literature cards, Notion sync, reading status, proposals, or slides.

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

## Available MCP Tools

- `read_paper` — Read and summarize a local PDF or text paper
- `deep_read_method` — Explain a paper's method section in detail
- `make_card` — Create a literature card from a paper source
- `read_zotero_item` — Read a Zotero item by key
- `plan_zotero_collection` — Suggest a next reading batch from a Zotero collection
- `update_reading_status` — Update reading status for a Zotero item
- `make_slides` — Create a slide plan or HTML deck from a paper source
- `propose_research` — Generate a research proposal scaffold from a source or question

## Safety Defaults

- Do not sync to Notion unless the user explicitly asks.
- Do not create local card files unless the user explicitly asks.
- Do not update reading status unless the user explicitly asks.
- When reporting results, mention important warnings and artifact paths.
- If a tool returns `ok: false`, summarize the error and suggest the smallest next step.

## MCP Setup

For local stdio MCP clients, the server entry point is:

```bash
python -m labcrew.mcp_server
```

If the package is installed with scripts, `labcrew-mcp` is also available.
