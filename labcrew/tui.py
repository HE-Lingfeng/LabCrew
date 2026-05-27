from __future__ import annotations

import json
import os
from typing import Any

import questionary
from rich.console import Console
from rich.text import Text

from labcrew.workflows import (
    create_literature_card,
    deep_read_method,
    design_experiment,
    make_presentation,
    make_html_slides,
    propose_research,
    read_paper,
)
from labcrew.tools import ZoteroAdapter
from labcrew.workflows import read_zotero_item, plan_collection_reading, update_reading_status


MSGS: dict[str, dict[str, str]] = {
    "lang_question": {
        "zh": "选择语言 / Select Language",
        "en": "Select Language / 选择语言",
    },
    "lang_zh": {"zh": "中文", "en": "Chinese"},
    "lang_en": {"zh": "English", "en": "English"},
    "menu_title": {
        "zh": "LabCrew 科研助手",
        "en": "LabCrew Research Assistant",
    },
    "menu_select": {"zh": "请选择操作：", "en": "Select an operation:"},
    "cmd_read_paper": {"zh": "读论文", "en": "Read Paper"},
    "cmd_deep_method": {"zh": "深度读方法", "en": "Deep Read Method"},
    "cmd_make_card": {"zh": "制作文献卡片", "en": "Make Literature Card"},
    "cmd_make_slides": {"zh": "生成 Slides", "en": "Make Slides"},
    "cmd_propose": {"zh": "发现研究 Gap", "en": "Propose Research"},
    "cmd_experiment": {"zh": "设计实验", "en": "Design Experiment"},
    "cmd_zotero": {"zh": "Zotero 管理", "en": "Zotero Management"},
    "cmd_switch_lang": {"zh": "切换语言 / Switch Language", "en": "Switch Language / 切换语言"},
    "cmd_quit": {"zh": "退出", "en": "Quit"},
    "source_label": {
        "zh": "论文路径 / URL / arXiv ID / DOI",
        "en": "Paper path / URL / arXiv ID / DOI",
    },
    "source_help": {
        "zh": "本地 PDF/txt 路径、arXiv ID（如 2401.12345）、DOI、或 URL",
        "en": "Local PDF/txt path, arXiv ID (e.g. 2401.12345), DOI, or URL",
    },
    "deep_method_label": {"zh": "深度解析方法部分?", "en": "Deep method analysis?"},
    "save_journal_label": {"zh": "存入 Journal?", "en": "Save to journal?"},
    "journal_period_label": {"zh": "Journal 周期", "en": "Journal period"},
    "save_notion_label": {"zh": "同步到 Notion?", "en": "Sync to Notion?"},
    "save_cards_label": {"zh": "保存本地文献卡片?", "en": "Save local card file?"},
    "slides_format_label": {"zh": "输出格式", "en": "Output format"},
    "slides_format_plan": {"zh": "Slide 计划 (JSON)", "en": "Slide Plan (JSON)"},
    "slides_format_html": {"zh": "自包含 HTML", "en": "Self-contained HTML"},
    "propose_source_label": {
        "zh": "论文路径（可选，留空则输入研究方向）",
        "en": "Paper path (optional, leave blank to enter research question)",
    },
    "research_question_label": {"zh": "研究方向 / 问题", "en": "Research question / topic"},
    "experiment_question_label": {"zh": "研究方向 / 问题", "en": "Research question / topic"},
    "zotero_sub_menu": {"zh": "选择 Zotero 操作：", "en": "Select Zotero operation:"},
    "zotero_list": {"zh": "列出文献", "en": "List items"},
    "zotero_read": {"zh": "读 Zotero 文献", "en": "Read Zotero item"},
    "zotero_plan": {"zh": "生成阅读计划", "en": "Plan collection reading"},
    "zotero_status": {"zh": "更新阅读状态", "en": "Update reading status"},
    "zotero_item_key": {"zh": "Zotero item key", "en": "Zotero item key"},
    "zotero_collection": {"zh": "Collection key", "en": "Collection key"},
    "zotero_batch_size": {"zh": "每批数量", "en": "Batch size"},
    "zotero_limit": {"zh": "最大数量", "en": "Max results"},
    "zotero_type": {"zh": "文献类型（可选）", "en": "Item type (optional)"},
    "zotero_status_select": {"zh": "新状态", "en": "New status"},
    "status_unread": {"zh": "未读", "en": "Unread"},
    "status_reading": {"zh": "在读", "en": "Reading"},
    "status_read": {"zh": "已读", "en": "Read"},
    "status_skipped": {"zh": "跳过", "en": "Skipped"},
    "zotero_sync_notion": {"zh": "同步到 Notion?", "en": "Sync to Notion?"},
    "executing": {"zh": "正在执行", "en": "Executing"},
    "result_title": {"zh": "执行结果", "en": "Result"},
    "press_enter": {"zh": "按回车继续...", "en": "Press Enter to continue..."},
    "goodbye": {"zh": "再见！", "en": "Goodbye!"},
}

_lang: str = os.environ.get("LABCREW_LANG", "zh")


def _t(key: str) -> str:
    entry = MSGS.get(key, {})
    return entry.get(_lang, entry.get("en", key))


def _switch_lang() -> None:
    global _lang
    _lang = "en" if _lang == "zh" else "zh"


def _jsonable(obj: Any) -> Any:
    from dataclasses import asdict, is_dataclass
    from enum import Enum

    if is_dataclass(obj):
        return {k: _jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return obj


def _print_result(data: Any) -> None:
    print(json.dumps(_jsonable(data), ensure_ascii=False, indent=2))


def _ask_source() -> str:
    return questionary.text(_t("source_label"), validate=lambda v: len(v.strip()) > 0).unsafe_ask()


def _ask_read_opts(include_deep: bool = True) -> dict[str, Any]:
    opts: dict[str, Any] = {}
    if include_deep:
        opts["deep_method"] = questionary.confirm(_t("deep_method_label"), default=False).unsafe_ask()
    opts["save_journal"] = questionary.confirm(_t("save_journal_label"), default=True).unsafe_ask()
    if opts["save_journal"]:
        opts["journal_period"] = questionary.select(
            _t("journal_period_label"),
            choices=["daily", "weekly", "monthly", "quarterly", "yearly"],
            default="weekly",
        ).unsafe_ask()
    opts["save_to_notion"] = questionary.confirm(_t("save_notion_label"), default=False).unsafe_ask()
    opts["save_to_cards"] = questionary.confirm(_t("save_cards_label"), default=False).unsafe_ask()
    return opts


def _run_read_paper() -> None:
    source = _ask_source()
    opts = _ask_read_opts(include_deep=True)
    _print_result(read_paper(source, **opts))


def _run_deep_method() -> None:
    source = _ask_source()
    opts = _ask_read_opts(include_deep=False)
    _print_result(deep_read_method(source, **opts))


def _run_make_card() -> None:
    source = _ask_source()
    opts = _ask_read_opts(include_deep=False)
    _print_result(create_literature_card(source, **opts))


def _run_make_slides() -> None:
    source = _ask_source()
    fmt = questionary.select(
        _t("slides_format_label"),
        choices=[
            questionary.Choice(_t("slides_format_plan"), "plan"),
            questionary.Choice(_t("slides_format_html"), "html"),
        ],
        default="plan",
    ).unsafe_ask()
    if fmt == "html":
        _print_result(make_html_slides(source))
    else:
        _print_result(make_presentation(source))


def _run_propose() -> None:
    source = questionary.text(
        _t("propose_source_label"),
        validate=lambda v: True,
    ).unsafe_ask()
    question = None
    if not source.strip():
        question = questionary.text(
            _t("research_question_label"),
            validate=lambda v: len(v.strip()) > 0,
        ).unsafe_ask()
    _print_result(propose_research(source=source.strip() or None, research_question=question))


def _run_experiment() -> None:
    question = questionary.text(
        _t("experiment_question_label"),
        validate=lambda v: len(v.strip()) > 0,
    ).unsafe_ask()
    _print_result(design_experiment(research_question=question))


def _run_zotero() -> None:
    zotero_cmd = questionary.select(
        _t("zotero_sub_menu"),
        choices=[
            questionary.Choice(_t("zotero_list"), "list"),
            questionary.Choice(_t("zotero_read"), "read"),
            questionary.Choice(_t("zotero_plan"), "plan"),
            questionary.Choice(_t("zotero_status"), "status"),
        ],
    ).unsafe_ask()

    if zotero_cmd == "list":
        collection = questionary.text(_t("zotero_collection")).unsafe_ask()
        item_type = questionary.text(_t("zotero_type")).unsafe_ask()
        limit = questionary.text(_t("zotero_limit"), default="20").unsafe_ask()
        with ZoteroAdapter() as adapter:
            if collection.strip():
                items = adapter.get_collection_items(collection.strip(), limit=int(limit))
            else:
                type_filter = item_type.strip() or None
                items = adapter.list_items(item_type=type_filter, limit=int(limit))
        result = [
            {
                "key": item.key,
                "title": item.title,
                "year": item.year,
                "doi": item.doi,
                "venue": item.venue,
                "pdf": bool(item.attachments),
            }
            for item in items
        ]
        _print_result(result)

    elif zotero_cmd == "read":
        item_key = questionary.text(
            _t("zotero_item_key"),
            validate=lambda v: len(v.strip()) > 0,
        ).unsafe_ask()
        opts = _ask_read_opts(include_deep=True)
        _print_result(read_zotero_item(item_key.strip(), **opts))

    elif zotero_cmd == "plan":
        collection = questionary.text(
            _t("zotero_collection"),
            validate=lambda v: len(v.strip()) > 0,
        ).unsafe_ask()
        batch_size = int(questionary.text(_t("zotero_batch_size"), default="5").unsafe_ask())
        _print_result(plan_collection_reading(collection_key=collection.strip(), batch_size=batch_size))

    elif zotero_cmd == "status":
        key = questionary.text(
            _t("zotero_item_key"),
            validate=lambda v: len(v.strip()) > 0,
        ).unsafe_ask()
        status = questionary.select(
            _t("zotero_status_select"),
            choices=[
                questionary.Choice(_t("status_unread"), "unread"),
                questionary.Choice(_t("status_reading"), "reading"),
                questionary.Choice(_t("status_read"), "read"),
                questionary.Choice(_t("status_skipped"), "skipped"),
            ],
        ).unsafe_ask()
        sync_notion = questionary.confirm(_t("zotero_sync_notion"), default=False).unsafe_ask()
        _print_result(update_reading_status(zotero_key=key.strip(), status=status, sync_to_notion=sync_notion))


_COMMANDS: dict[str, tuple[str, callable]] = {}


def _ensure_commands() -> dict[str, tuple[str, callable]]:
    global _COMMANDS
    _COMMANDS = {
        "read_paper": (_t("cmd_read_paper"), _run_read_paper),
        "deep_method": (_t("cmd_deep_method"), _run_deep_method),
        "make_card": (_t("cmd_make_card"), _run_make_card),
        "make_slides": (_t("cmd_make_slides"), _run_make_slides),
        "propose": (_t("cmd_propose"), _run_propose),
        "experiment": (_t("cmd_experiment"), _run_experiment),
        "zotero": (_t("cmd_zotero"), _run_zotero),
    }
    return _COMMANDS


def start_tui() -> None:
    global _lang

    logo = r"""
        ▗▄▖     ▗▄▖
       ▐  ▜▄▄▄▄▄▛  ▌
       ▐  ●     ●  ▌
       ▝▙    ▾    ▟▘
         ▜▙  ▿  ▟▛
           ▀▀▀▀▀
          ▟▌   ▐▙
    ┌────────────────┐
    │    LabCrew     │
    │    woof > _    │
    └────────────────┘
"""
    text = Text(logo)
    text.stylize("bold yellow", 0, 166)
    text.stylize("bold cyan", 167, len(logo))
    text.stylize("bold white", logo.find("LabCrew"), logo.find("LabCrew") + len("LabCrew"))
    text.stylize("bold green", logo.find("read > _"), logo.find("read > _") + len("read > _"))
    Console().print(text)

    # Language selection on first start
    lang_options = [
        questionary.Choice(_t("lang_zh"), "zh"),
        questionary.Choice(_t("lang_en"), "en"),
    ]
    default_lang = next((c for c in lang_options if c.value == _lang), lang_options[0])
    lang_choice = questionary.select(
        _t("lang_question"),
        choices=lang_options,
        default=default_lang,
    ).unsafe_ask()
    _lang = lang_choice

    while True:
        _ensure_commands()
        choices: list = [questionary.Choice(label, key) for key, (label, _fn) in _COMMANDS.items()]
        choices.append(questionary.Separator())
        choices.append(questionary.Choice(_t("cmd_switch_lang"), "_lang"))
        choices.append(questionary.Choice(_t("cmd_quit"), "_quit"))

        cmd = questionary.select(
            _t("menu_select"),
            choices=choices,
        ).unsafe_ask()

        if cmd == "_quit":
            print(_t("goodbye"))
            break
        if cmd == "_lang":
            _switch_lang()
            continue

        try:
            print()  # blank line before executing
            _COMMANDS[cmd][1]()
        except Exception as exc:
            print(f"Error: {exc}")
        print()  # blank line after result
        questionary.press_any_key_to_continue(_t("press_enter")).unsafe_ask()
