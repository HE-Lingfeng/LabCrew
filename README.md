# LabCrew

LabCrew is a multi-agent research assistant for graduate research workflows: read papers, create literature cards, manage Zotero items, generate slide decks, and draft research proposals — all from the command line.

## Features

- **Paper reading** — ingest PDF or text papers, get structured summaries with method deep-dives
- **Literature cards** — generate structured Markdown cards with YAML frontmatter
- **Zotero integration** — read, list, plan, and track reading status of your Zotero library (read-only SQLite access)
- **Notion sync** — optionally sync literature cards and reading status to a Notion database
- **Slide generation** — create slide plans or self-contained HTML decks with multiple themes
- **Research proposals** — discover gaps and draft proposals from a paper or a seed question
- **Experiment design** — scaffold a first experiment with hypothesis, methods, metrics, and ablation plan
- **TUI** — interactive terminal UI with slash-command autocomplete, bilingual (EN/中文)
- **MCP server** — expose all tools as an MCP server for Claude Code, Codex, and other MCP clients

## Installation

```bash
# Clone and install
git clone https://github.com/HE-Lingfeng/LabCrew.git
cd LabCrew
pip install -e .

# Optional PDF backends (at least one required for PDF reading)
pip install pypdf          # first choice
pip install pdfminer.six   # fallback
pip install PyMuPDF        # fallback + figure extraction
```

## Quick Start

```bash
# Read and summarize a paper
python -m labcrew read-paper path/to/paper.pdf

# Deep-read the method section
python -m labcrew deep-read-method path/to/paper.pdf

# Create a literature card
python -m labcrew make-card path/to/paper.pdf

# Generate a slide plan or HTML deck
python -m labcrew make-slides path/to/paper.pdf --format html

# Propose research from a paper or a question
python -m labcrew propose-research --source path/to/paper.pdf
python -m labcrew propose-research --question "agent planning under limited retrieval evidence"

# Design an experiment scaffold
python -m labcrew design-experiment "how does retrieval corpus size affect agent planning quality?"

# Launch the interactive TUI
python -m labcrew
```

## CLI Reference

All commands output JSON. Run `python -m labcrew <command> --help` for details.

### Paper Reading

```bash
python -m labcrew read-paper <source> [options]
```

| Option | Description |
|---|---|
| `--deep-method` | Include method deep-dive |
| `--journal-period` | Journal period: daily, weekly (default), monthly, quarterly, yearly, or N-days |
| `--no-journal` | Skip journal entry |
| `--notion` | Sync literature card to Notion |
| `--cards` | Save literature card as local Markdown file |

```bash
python -m labcrew deep-read-method <source> [options]
```
Same options as `read-paper` (without `--deep-method`, which is always on).

### Literature Cards

```bash
python -m labcrew make-card <source> [options]
```
Same options as `read-paper`. Creates a structured Markdown card with YAML frontmatter in `data/cards/`.

### Slides

```bash
python -m labcrew make-slides <source> [--format {plan,html}]
```

| Format | Output |
|---|---|
| `plan` (default) | JSON slide plan with titles, bullet points, speaker notes |
| `html` | Self-contained HTML deck (themes: light, dark, blue) |

```bash
# Staged academic slide workflow
python -m labcrew academic-slides <source> [options]
```

| Option | Description |
|---|---|
| `--stage {materials,plan,html}` | Pipeline stage (default: html) |
| `--audience` | Target audience description |
| `--duration-minutes` | Presentation duration |
| `--profile {ai-research,ai-survey,standard}` | Slide profile |
| `--materials [paths...]` | Additional material files (.md, .docx, screenshots) |
| `--out` | Output file path |
| `--theme {light,dark,blue}` | HTML theme (default: dark) |

### Research & Experiment

```bash
python -m labcrew propose-research (--source <path> | --question <text>)
python -m labcrew research-strategy (--source <path> | --question <text>)   # alias
python -m labcrew generate-idea (--source <path> | --question <text>)       # alias

python -m labcrew design-experiment <research_question>
```

### Zotero

Reads from `~/Zotero/zotero.sqlite` (read-only, no write back). A local SQLite link store at `data/zotero_links.db` tracks reading status and Notion links.

```bash
# List items (optionally filtered by collection)
python -m labcrew zotero list [--collection KEY] [--type article] [--limit 20]

# Read and summarize a Zotero item by key
python -m labcrew zotero read <item_key> [options]   # same options as read-paper

# Generate a reading plan for a collection
python -m labcrew zotero plan --collection <KEY> [--batch-size 5]

# Update reading status
python -m labcrew zotero status --key <KEY> --status {unread,reading,read,skipped} [--notion]
```

## TUI

Run `python -m labcrew` with no arguments to launch the interactive TUI.

- Type `/` to see all available commands with autocomplete
- `/read-paper`, `/deep-read-method`, `/make-card`, `/make-slides` — workflows with interactive prompts
- `/propose-research`, `/design-experiment` — research ideation
- `/zotero list|read|plan|status` — Zotero management
- `/help` — show command reference
- `/switch-lang` — toggle between English and 中文
- `/exit`, `/quit`, `/q` — exit (Ctrl-C also works)

The status bar shows current language, working directory, and integration status (Zotero/Notion connectivity).

Set the default language via `LABCREW_LANG=zh` or `LABCREW_LANG=en`.

## MCP Server

LabCrew can run as an MCP server for use with Claude Code, Codex, or any MCP-compatible client.

```bash
python -m labcrew.mcp_server
# or via the entry point:
labcrew-mcp
```

### Available MCP Tools

| Tool | Description |
|---|---|
| `read_paper` | Read and summarize a local paper |
| `deep_read_method` | Deep-read the method section |
| `make_card` | Create a literature card |
| `read_zotero_item` | Read a Zotero item by key |
| `plan_zotero_collection` | Generate a reading plan for a collection |
| `update_reading_status` | Update reading status, optionally sync to Notion |
| `make_slides` | Create slide plan or HTML deck |
| `propose_research` | Generate a research proposal |

All tools return a stable envelope: `{"ok": bool, "data": {}, "warnings": [], "artifacts": [], "error": null}`.

### MCP Client Configuration

For stdio-based MCP clients, add to your client config:

```json
{
  "mcpServers": {
    "labcrew": {
      "command": "python",
      "args": ["-m", "labcrew.mcp_server"],
      "cwd": "/path/to/LabCrew"
    }
  }
}
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `NOTION_API_KEY` | For Notion sync | Notion integration token |
| `NOTION_DATABASE_ID` | For Notion sync | Target Notion database ID |
| `CARDS_OUTPUT_DIR` | No | Override card output directory (default: `data/cards/`) |
| `LABCREW_LANG` | No | TUI language: `zh` or `en` (default: `en`) |

Place these in `.env` or `.env.local` in your working directory. `.env.local` is loaded after `.env` and does not override already-set variables.

### Zotero

No configuration needed. LabCrew reads `~/Zotero/zotero.sqlite` directly in read-only mode. Make sure your Zotero database exists at that path.

### Notion

1. Create a Notion integration at https://www.notion.so/my-integrations
2. Copy the integration token as `NOTION_API_KEY`
3. Share your target database with the integration
4. Copy the database ID from the URL as `NOTION_DATABASE_ID`

## Project Layout

```text
labcrew/
  agents/          Agent implementations and coordinator
    coordinator.py   Main orchestrator (LabCrewAgent)
    paper_ingest.py  PDF/text ingestion → Paper
    paper_reader.py  Chunking + summarization → Report
    knowledge_card.py  Literature card generation
    proposal.py      Research gap discovery + proposal drafting
    presentation.py  Slide plan generation (3 profiles)
    writing.py       Academic writing (placeholder)
    literature_manager.py  Zotero sync
    notion_sync.py   Notion page create/update
    easter_egg.py    Weekend recommendations
  schemas/         Dataclass data contracts (Task, Paper, Card, Slide, Proposal, etc.)
  tools/           External adapters
    pdf_parser.py         PDF text + figure extraction (pypdf/pdfminer/PyMuPDF)
    zotero_adapter.py     Zotero SQLite read-only access
    zotero_link_store.py  Local reading-status + Notion-link store
    notion_adapter.py     Notion API (httpx)
    card_store.py         Markdown + YAML frontmatter card writer
    journal_store.py      Period-based journal files
    llm_adapter.py        LLM facade (currently deterministic mocks)
    text_chunker.py       Heading-based paper chunking
    html_slide_adapter.py Self-contained HTML slide deck generator
    citation.py           Author-year citation formatting
    ppt_adapter.py        PowerPoint export (placeholder)
    search_adapter.py     Academic search (placeholder)
    document_adapter.py   Document creation (placeholder)
  memory/          Local storage primitives (index, store)
  workflows/       User-facing workflow composition
  evals/           Lightweight evaluation entry points
  prompts/         Reference prompt templates
data/
  cards/           Generated literature card Markdown files
  artifacts/
    figures/       Extracted PDF figure snapshots
    slides/        Generated HTML slide decks
    materials/     User-provided slide materials
  journals/        Period-based reading journal entries
tests/             Test suite (workflows, adapters, agents)
```

## Architecture

```
User input (CLI / TUI / MCP)
  → main.py / mcp_server.py
    → runtime.py (call_action / run_action)
      → workflows/ (Task composition)
        → LabCrewAgent (coordinator, dispatches by TaskType)
          → Sub-agents (ingest → read → card → propose → present)
            → Tools/Adapters (PDF, Zotero, Notion, CardStore, HtmlSlide, etc.)
```

The coordinator agent (`LabCrewAgent`) orchestrates sub-agents by task type. Each sub-agent handles a focused responsibility. Adapters keep external integrations (Zotero, Notion) behind stable interfaces so the local workflow remains usable even when external services are unavailable.

> **Phase 0 status**: The current implementation is a skeleton with real adapters (Zotero, Notion, PDF, HTML slides) and deterministic mock LLM behavior. Real model integration replaces `LLMAdapter` methods.

## Development

```bash
# Run tests
python -m pytest tests/ -v

# Type check (if mypy installed)
python -m mypy labcrew/
```
