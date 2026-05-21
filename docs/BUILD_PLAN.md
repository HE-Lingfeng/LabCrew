# LabCrew 搭建计划

## 1. 项目定位

LabCrew 是一个面向研究生工作流的多 agent 研究助理。它的核心目标不是替代研究者，而是把研究生在日常科研中逐渐形成的技能迁移到一个可维护、可扩展的系统中：

- 读论文、拆论文、总结论文。
- 批判性分析论文贡献、实验设计和局限。
- 辅助设计实验，第一阶段只搭建空壳和标准接口。
- 调用工具生成 PPT、论文草稿、组会材料和文献卡片。
- 和 Zotero、Notion、GitHub 等外部工具协作，形成长期文献管理和知识沉淀。
- 提供轻量彩蛋功能，例如周末放松地点或活动推荐。

长期方向是把 LabCrew 做成一个“研究工作台型 agent”，而不是一个巨大 prompt。主 agent 负责任务理解、路由和结果整合，专业 subagent 负责具体能力，工具适配层负责和外部系统交互。

## 2. 总体架构

```text
User
  |
  v
LabCrewAgent
  |
  +-- PaperIngestAgent
  +-- PaperReaderAgent
  +-- ProposalAgent
  +-- WritingAgent
  +-- PresentationAgent
  +-- KnowledgeCardAgent
  +-- LiteratureManagerAgent
  +-- WeekendEasterEggAgent
  |
  v
Tool Adapters
  |
  +-- ZoteroAdapter
  +-- NotionAdapter
  +-- GitHubAdapter
  +-- PPTAdapter
  +-- DocumentAdapter
  +-- SearchAdapter
  +-- PDFParser
  +-- LocalMemoryStore
```

核心设计原则：

- Agent 之间通过结构化 schema 传递数据，不互相依赖实现细节。
- Zotero、Notion、GitHub、PPT 工具都放在 adapter 层，避免 agent 和具体平台强绑定。
- 本地知识库是第一优先级，外部工具是同步目标。这样即使某个外部工具不可用，LabCrew 仍然能工作。
- 实验设计模块先定义输入输出协议，暂不实现复杂实验自动化。

## 3. 推荐目录结构

```text
LabCrew/
├── README.md
├── pyproject.toml
├── docs/
│   ├── BUILD_PLAN.md
│   ├── ARCHITECTURE.md
│   ├── AGENTS.md
│   ├── INTEGRATIONS.md
│   └── ROADMAP.md
├── labcrew/
│   ├── main.py
│   ├── config.py
│   ├── agents/
│   │   ├── base.py
│   │   ├── coordinator.py
│   │   ├── paper_ingest.py
│   │   ├── paper_reader.py
│   │   ├── proposal.py
│   │   ├── writing.py
│   │   ├── presentation.py
│   │   ├── knowledge_card.py
│   │   ├── literature_manager.py
│   │   └── easter_egg.py
│   ├── schemas/
│   │   ├── task.py
│   │   ├── paper.py
│   │   ├── note.py
│   │   ├── experiment.py
│   │   ├── presentation.py
│   │   └── artifact.py
│   ├── tools/
│   │   ├── pdf_parser.py
│   │   ├── citation.py
│   │   ├── zotero_adapter.py
│   │   ├── notion_adapter.py
│   │   ├── github_adapter.py
│   │   ├── ppt_adapter.py
│   │   ├── document_adapter.py
│   │   └── search_adapter.py
│   ├── memory/
│   │   ├── store.py
│   │   ├── index.py
│   │   └── sync.py
│   ├── workflows/
│   │   ├── read_paper.py
│   │   ├── make_presentation.py
│   │   ├── create_literature_card.py
│   │   └── design_experiment.py
│   └── evals/
│       ├── routing_eval.py
│       ├── paper_summary_eval.py
│       └── card_quality_eval.py
├── data/
│   ├── papers/
│   ├── notes/
│   ├── cards/
│   └── artifacts/
└── tests/
```

## 4. Agent 职责

### 4.1 LabCrewAgent

主协调 agent，负责：

- 判断用户意图。
- 选择需要调用的 subagent。
- 管理多步骤任务。
- 合并结果并给用户最终输出。
- 在需要时调用工具适配层。

典型路由：

```text
上传论文 PDF -> PaperIngestAgent -> PaperReaderAgent -> KnowledgeCardAgent
总结论文 -> PaperReaderAgent
发现研究方向 -> PaperReaderAgent -> ProposalAgent
设计实验 -> ProposalAgent
做组会 PPT -> PaperReaderAgent -> PresentationAgent
保存文献卡片 -> KnowledgeCardAgent -> NotionAdapter/GitHubAdapter
同步 Zotero 文献 -> LiteratureManagerAgent -> ZoteroAdapter
周末放松推荐 -> WeekendEasterEggAgent
```

### 4.2 PaperIngestAgent

负责论文导入和解析：

- 支持 PDF、本地路径、论文链接、DOI、arXiv ID。
- 提取标题、作者、年份、摘要、章节、参考文献。
- 和 Zotero 数据进行匹配，避免重复导入。
- 输出标准 `Paper` schema。

### 4.3 PaperReaderAgent

负责研究生式精读：

- 论文研究问题。
- 背景和动机。
- 核心方法。
- 关键公式或模型结构。
- 实验设置。
- 主要结果。
- 可迁移的技术点。

### 4.4 ProposalAgent

负责根据已读论文、文献卡片或用户给出的研究领域，先发现候选 research gap / 未充分探索的任务方向，再给出可执行研究方案和第一版实验设计：

- 分析研究现状、论文假设、baseline、实验覆盖、消融支撑和局限性。
- 提出待解决问题、可能没人系统做过的任务方向，且标记 novelty claim 是否仍需文献验证。
- 生成 `ResearchProposal`，包括 current state、unresolved problem、unexplored direction、evidence、proposal、next steps。
- 内嵌生成 `ExperimentPlan`，第一阶段实验自动化仍只做空壳。

输入：

```text
paper / paper_card_report / paper_reading_report
research_area / seed_question
literature_context
evidence
hypothesis
target_dataset
candidate_methods
baseline_methods
metrics
constraints
```

输出：

```text
experiment_goal
experimental_setup
baseline_plan
ablation_plan
metric_plan
risk_notes
implementation_status: placeholder
```

后续可扩展为：

- 自动生成实验脚本。
- 管理实验配置。
- 分析实验结果表格。
- 生成论文中的实验分析段落。

### 4.5 WritingAgent

负责科研写作：

- 摘要。
- introduction。
- related work。
- method。
- experiment analysis。
- conclusion。
- rebuttal。
- 中文到英文学术润色。

WritingAgent 不直接管理引用，只消费 `Paper` 和 `LiteratureCard` schema，由 citation 工具或 ZoteroAdapter 提供引用信息。

### 4.7 PresentationAgent

负责 PPT 工作流：

- 把论文总结转成组会汇报大纲。
- 根据时间长度生成 slide plan。
- 调用 PPTAdapter 生成 slide artifact。
- 支持不同用途：组会、课程展示、proposal、论文分享。

第一阶段可先生成 Markdown slide outline 或 JSON slide plan，后续再接入 PowerPoint、Google Slides 或本地 presentation 工具。

### 4.8 KnowledgeCardAgent

负责生成文献卡片：

```text
title
authors
year
venue
tags
one_sentence_summary
problem
method
key_results
strengths
weaknesses
useful_for
open_questions
related_papers
zotero_item_key
source_pdf_path
```

输出目标：

- 本地 Markdown/JSON。
- Notion database page。
- GitHub issue/discussion/Markdown file。

### 4.9 LiteratureManagerAgent

负责 Zotero 和文献库同步：

- 从 Zotero collection 拉取条目。
- 根据 DOI/title/item key 去重。
- 补全本地 paper metadata。
- 把 LabCrew 生成的阅读状态、标签、卡片链接回写到同步记录中。
- 暂不直接修改 Zotero 原始数据，第一阶段只读或生成建议变更。

### 4.10 WeekendEasterEggAgent

轻量彩蛋功能：

- 周末活动推荐。
- 放松地点推荐。
- 按城市、预算、天气、体力状态给建议。
- 不主动干扰主研究流程，只在用户明确表达放松需求时触发。

## 5. 外部集成设计

### 5.1 Zotero 集成

定位：文献源和引用源。

第一阶段能力：

- 读取 Zotero collection。
- 读取条目 metadata。
- 关联本地 PDF 路径。
- 保存 `zotero_item_key` 到本地文献卡片。

第二阶段能力：

- 自动识别用户给出的 PDF 是否已存在于 Zotero。
- 根据 Zotero tag 或 collection 批量生成阅读计划。
- 生成待读列表、已读列表、组会候选列表。

第三阶段能力：

- 把 Notion/GitHub 卡片链接同步回本地映射表。
- 生成 BibTeX 或引用片段。
- 支持按项目维护不同 collection。

建议不要在早期直接写回 Zotero。先采用只读同步，加一个本地 `zotero_links.json` 或 sqlite 表维护映射，风险更低。

### 5.2 Notion 集成

定位：人类友好的知识库和项目看板。

适合保存：

- 文献卡片。
- 阅读状态。
- 项目相关论文列表。
- 研究问题池。
- 组会记录。

建议 Notion database 字段：

```text
Title
Authors
Year
Venue
Status: To Read / Reading / Read / Skipped
Tags
Project
One Sentence
Key Contribution
Limitations
Useful For
Zotero Key
PDF Path
GitHub Link
Created At
Updated At
```

同步策略：

- 本地是 canonical 数据源。
- Notion 是展示和协作层。
- 每次同步记录 external page id，避免重复创建。

### 5.3 GitHub 集成

定位：版本化知识库和项目协作。

适合保存：

- Markdown 文献卡片。
- 项目研究日志。
- issue 形式的论文阅读任务。
- milestone 形式的 reading list。
- PR 形式的论文笔记修改和 review。

推荐路径：

```text
research/
├── papers/
│   ├── 2026-paper-title.md
│   └── ...
├── reading-lists/
│   ├── llm-agents.md
│   └── ...
└── project-notes/
    └── experiment-ideas.md
```

GitHub 和 Notion 的关系：

- 如果重视版本历史，用 GitHub 作为主知识库，Notion 作为索引视图。
- 如果重视日常管理体验，用 Notion 作为主协作界面，GitHub 作为导出备份。
- LabCrew 内部仍保留本地结构化数据，避免被单个平台锁定。

### 5.4 PPT 工具集成

定位：从研究内容生成演示材料。

PPTAdapter 需要定义统一接口：

```text
create_deck(slide_plan, style_profile, output_target)
update_deck(deck_id, change_request)
export_deck(deck_id, format)
```

SlidePlan schema：

```text
title
audience
duration_minutes
slides:
  - title
    purpose
    key_message
    bullets
    visual_suggestion
    speaker_notes
source_papers
```

第一阶段：

- 生成 slide outline。
- 输出 Markdown 或 JSON。
- 预留 PPTAdapter，不强依赖具体工具。

第二阶段：

- 接入 PowerPoint/Google Slides/本地 presentation 工具。
- 生成可编辑 deck。
- 支持一键从论文卡片生成组会汇报。

第三阶段：

- 根据用户反馈修改 PPT。
- 自动加入图表、方法框图、论文对比表。
- 维护不同 presentation style profile。

## 6. 核心数据模型

### 6.1 Paper

```text
paper_id
title
authors
year
venue
doi
arxiv_id
abstract
sections
references
pdf_path
source_url
zotero_item_key
created_at
updated_at
```

### 6.2 LiteratureCard

```text
card_id
paper_id
summary
problem
method
key_results
strengths
weaknesses
tags
project
useful_for
open_questions
external_links
created_at
updated_at
```

### 6.3 ExperimentPlan

```text
plan_id
research_question
hypothesis
datasets
methods
baselines
metrics
ablations
risks
status
created_at
updated_at
```

### 6.4 Artifact

```text
artifact_id
type: note / card / deck / draft / experiment_plan
source_task_id
local_path
external_target
external_id
created_at
updated_at
```

## 7. MVP 搭建阶段

### Phase 0: 项目骨架

目标：

- 建立 Python 项目结构。
- 定义基础 agent、schema、adapter 接口。
- 增加 README 和最小 CLI。

交付：

- `BaseAgent`
- `LabCrewAgent`
- `Task` schema
- `Paper` schema
- adapter 抽象类
- 一个可运行的 `labcrew` CLI 入口

### Phase 1: 论文阅读主链路

目标：

- 支持输入论文文本或 PDF 路径。
- 输出结构化论文总结。
- 生成本地 Markdown 文献卡片。

交付：

- `PaperIngestAgent`
- `PaperReaderAgent`
- `KnowledgeCardAgent`
- `PDFParser`
- 本地 `data/cards/` 输出

### Phase 2: 外部工具接口空壳

目标：

- 把 Zotero、Notion、GitHub、PPT 的接口先设计出来。
- 暂时允许 mock 实现。

交付：

- `ZoteroAdapter`
- `NotionAdapter`
- `GitHubAdapter`
- `PPTAdapter`
- mock sync workflow

### Phase 3: 实验设计和 PPT 工作流

目标：

- Proposal 模块返回研究方案和标准实验计划模板。
- PPT 模块从论文卡片生成 slide outline。

交付：

- `ProposalAgent`
- `PresentationAgent`
- `ResearchProposal` schema
- `SlidePlan` schema
- `ExperimentPlan` schema

### Phase 4: 真实集成

目标：

- 接入 Zotero metadata 读取。
- 接入 Notion/GitHub 卡片保存。
- 接入至少一个 PPT 生成或导出工具。

交付：

- Zotero collection sync。
- Notion database page 创建。
- GitHub Markdown 卡片写入。
- PPT artifact 生成。

### Phase 5: 长期维护能力

目标：

- 增加测试、eval、路由质量检查。
- 支持项目级配置。
- 支持记忆索引和检索。

交付：

- routing eval。
- paper summary eval。
- card quality eval。
- project config。
- local search/index。

## 8. 测试策略

必须优先测试：

- 用户请求是否路由到正确 agent。
- schema 是否稳定。
- 文献卡片是否能重复生成且格式一致。
- 外部同步是否去重。
- adapter 失败时主流程是否仍能返回本地结果。

建议测试类型：

```text
unit tests:
  schema validation
  adapter mock behavior
  markdown card generation

workflow tests:
  read paper -> card
  card -> notion mock
  card -> github mock
  card -> slide outline

evals:
  routing accuracy
  summary completeness
  critique usefulness
```

## 9. 配置设计

建议使用项目级配置：

```toml
[labcrew]
workspace = "data"
default_project = "general"

[models]
coordinator = "default"
reader = "default"
writer = "default"

[integrations.zotero]
enabled = false
library_type = "user"
library_id = ""

[integrations.notion]
enabled = false
database_id = ""

[integrations.github]
enabled = false
repo = ""
cards_path = "research/papers"

[integrations.presentation]
enabled = false
provider = "mock"
```

配置原则：

- 默认所有外部集成都关闭。
- 本地功能不依赖外部 API。
- 外部集成通过环境变量或本地私有配置提供 credentials。
- 不把 token 写入仓库。

## 10. 风险和取舍

### 平台锁定

风险：过早绑定 Notion 或 GitHub 会让数据迁移困难。

策略：本地 schema 和本地存储作为主数据源，外部平台作为同步目标。

### Agent 过多导致复杂度上升

风险：subagent 太细会让调度复杂。

策略：先实现少数核心 agent，其他 agent 只保留接口或 mock。

### PPT 自动生成质量不稳定

风险：直接生成完整 PPT 容易风格和内容都不可控。

策略：先生成 slide plan，再生成 deck。slide plan 是中间产物，便于修改。

### Zotero 写入风险

风险：自动修改 Zotero 条目可能破坏用户文献库。

策略：早期只读 Zotero，写操作必须显式确认。

## 11. 建议优先级

第一优先级：

1. 项目骨架。
2. 论文总结。
3. 本地文献卡片。
4. PPT outline。
5. Research strategy 生成和实验设计空壳。

第二优先级：

1. Zotero 只读同步。
2. Notion/GitHub 卡片保存。
3. ProposalAgent 质量评估。
4. WritingAgent。

第三优先级：

1. 真实 PPT 工具集成。
2. 本地知识库检索。
3. 多项目 workspace。
4. 周末彩蛋。

## 12. 第一轮开发任务清单

- 创建 Python 包结构。
- 定义 `BaseAgent` 和 `LabCrewAgent`。
- 定义 `Task`、`Paper`、`LiteratureCard`、`SlidePlan`、`ExperimentPlan` schema。
- 实现 mock agent 路由。
- 实现本地 Markdown 文献卡片生成。
- 实现 mock Zotero/Notion/GitHub/PPT adapter。
- 加入最小 CLI：

```text
labcrew read-paper path/to/paper.pdf
labcrew make-card path/to/paper.pdf
labcrew make-slides path/to/card.md
labcrew design-experiment "research question"
```

- 写 3 个 workflow test：

```text
read paper -> summary
summary -> card
card -> slide outline
```

## 13. 长期演进图

```text
MVP local assistant
  |
  v
Local literature card system
  |
  v
Zotero + Notion/GitHub sync
  |
  v
Research presentation and writing assistant
  |
  v
Experiment planning and result analysis assistant
  |
  v
Project-level research operating system
```

最终目标是让 LabCrew 成为一个持续积累的研究伙伴：它知道你读过什么、正在做什么、哪些论文值得回看、哪些想法可以实验、哪些内容可以直接变成组会 PPT 或论文草稿。
