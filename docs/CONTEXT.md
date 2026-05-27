# LabCrew 快速上下文

这份文档给未来的 Codex / Claude / 人类维护者当低 token 入口。处理问题前先读这里，再按需打开具体文件。

## 项目一句话

LabCrew 是一个面向研究生科研工作流的本地优先 multi-agent 助手。当前是 Phase 0/早期可运行骨架：CLI、MCP server、schemas、agents、workflows、adapters 和测试都已有，很多智能行为仍是 mock/local-first 实现。

## 先读顺序

1. `docs/CONTEXT.md`：当前这份快速地图。
2. `CLAUDE.md`：协作和安全约定。
3. `README.md`：用户可见 quick start。
4. `docs/BUILD_PLAN.md`：长期架构和愿景。
5. 具体任务相关模块：优先从 `labcrew/main.py`、`labcrew/runtime.py`、`labcrew/workflows/` 往下追。

## 关键目录

- `labcrew/main.py`：CLI 参数和命令入口；无参数时进入 TUI。
- `labcrew/mcp_server.py`：极简 MCP server，工具名映射到 runtime action。
- `labcrew/runtime.py`：`call_action` / `run_action` 和 action registry；排查行为路由先看这里。
- `labcrew/workflows/`：用户级工作流组合层，比如读论文、做卡片、做 slides、读 Zotero、生成 idea。
- `labcrew/agents/`：具体 agent 实现，尽量通过 schema 传递结构化数据。
- `labcrew/schemas/`：稳定数据契约；改 schema 时要查 workflow、adapter、tests 的使用面。
- `labcrew/tools/`：外部集成和本地工具适配层，包括 PDF、Zotero、Notion、CardStore、JournalStore、slides。
- `data/`：运行产物目录，通常不提交。`.gitignore` 已忽略 `data/papers/*`、`data/artifacts/*`、`data/journals/*`。
- `tests/`：当前主要覆盖 workflow、Notion/Zotero adapter、card store、HTML slides、runtime。

## 常用命令

```bash
python -m labcrew read-paper path/to/paper.txt
python -m labcrew read-paper path/to/paper.pdf --deep-method
python -m labcrew make-card path/to/paper.txt --cards
python -m labcrew make-slides path/to/paper.txt
python -m labcrew make-slides path/to/paper.txt --format html
python -m labcrew academic-slides path/to/paper.pdf --stage materials
python -m labcrew propose-research --source path/to/paper.txt
python -m labcrew propose-research --question "seed research question"
python -m labcrew design-experiment "research question"
python -m labcrew zotero list --limit 20
python -m labcrew zotero read ITEMKEY --deep-method
python -m labcrew zotero plan --collection COLLECTIONKEY
python -m labcrew zotero status --key ITEMKEY --status read
pytest
```
如果 CLI 命令出错，优先检查 `labcrew/main.py` 的参数解析是否传到 `labcrew/runtime.py` 的 action，再检查对应 `labcrew/workflows/*.py`。

## 当前 action / tool 地图

Runtime actions 在 `labcrew/runtime.py` 的 `_ACTIONS` 中注册：

- `read_paper`
- `deep_read_method`
- `make_card`
- `read_zotero_item`
- `plan_zotero_collection`
- `update_reading_status`
- `make_slides`
- `propose_research`
- `research_strategy`
- `generate_idea`
- `design_experiment`
- `zotero_list`

MCP tools 在 `labcrew/mcp_server.py` 的 `TOOLS` 中定义，目前暴露：

- `read_paper`
- `deep_read_method`
- `make_card`
- `read_zotero_item`
- `plan_zotero_collection`
- `update_reading_status`
- `make_slides`
- `propose_research`

注意：CLI 比 MCP 暴露更多 compatibility alias，比如 `research-strategy`、`generate-idea`、`academic-slides`。

## 配置和外部集成

- 环境变量从当前工作目录的 `.env` 和 `.env.local` 读取，不覆盖已有环境变量。实现见 `labcrew/env.py`。
- Notion：需要 `NOTION_API_KEY` 和 `NOTION_DATABASE_ID`。`NotionAdapter` 初始化时会真实访问 Notion API 读取数据库属性。
- Zotero：`ZoteroAdapter` 默认只读 `~/Zotero/zotero.sqlite`，用 SQLite `mode=ro&immutable=1` 打开。
- Local cards：默认输出到 `research/papers`，也可用 `CARDS_OUTPUT_DIR` 覆盖。
- Journal：默认输出到 `data/journals/<project>/paper-journal-<period>.md`。
- Artifacts：默认在 `data/artifacts` 下生成，例如 slides materials、figure snapshots、HTML deck 等。

安全约定：只有用户明确要求时，才同步 Notion、创建本地 card 文件或更新 Zotero 状态。默认读论文会写 journal，除非传 `--no-journal` 或 workflow 参数关闭。

## 常见排查入口

- CLI 参数没有生效：看 `labcrew/main.py` 对应 subparser 和 `call_action(...)` 参数。
- MCP 返回 `ok: false`：看 `labcrew/runtime.py` 的 `run_action` envelope 和 `_friendly_error`。
- 读 PDF/图片抽取异常：看 `labcrew/tools/pdf_parser.py`，相关测试在 `tests/test_workflows.py`。
- 文献卡片字段缺失：看 `labcrew/agents/knowledge_card.py`、`labcrew/schemas/note.py`、`labcrew/tools/card_store.py`、`labcrew/tools/notion_adapter.py`。
- Zotero 找不到条目/PDF：看 `labcrew/tools/zotero_adapter.py` 和 `labcrew/workflows/read_zotero.py`。
- Notion schema 不匹配：看 `NotionAdapter._property_matches`，数据库属性名和类型必须匹配。
- Journal 重复或没有 upsert：看 `labcrew/tools/journal_store.py` 的 HTML comment marker。
- Slides 输出或素材阶段问题：看 `labcrew/workflows/academic_slides.py`、`make_html_slides.py`、`labcrew/tools/html_slide_adapter.py`。

## 改动时的经验规则

- 新 CLI 命令通常要同时改 `labcrew/main.py`、`labcrew/runtime.py`，如果要给 MCP 用，还要改 `labcrew/mcp_server.py`。
- 新结构化字段优先加到 `labcrew/schemas/`，再让 agent/workflow/adapter 消费，避免跨层传裸 dict。
- 外部服务放 adapter 层；workflow 调 adapter，agent 不直接绑定 Notion/Zotero/GitHub。
- 测试尽量围绕 workflow 或 adapter 行为写，避免只测实现细节。
- 不要提交 `.env*`、`data/` 运行产物、`__pycache__`、`.pytest_cache`。

## 验证建议

小改动优先跑相关测试：

```bash
pytest tests/test_runtime.py
pytest tests/test_workflows.py
pytest tests/test_notion_adapter.py
pytest tests/test_zotero_adapter.py
```

广泛改动或准备交付前跑：

```bash
pytest
```
