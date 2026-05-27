from __future__ import annotations

import json
import os
import shlex
from pathlib import Path
from typing import Any

import questionary
from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import ConditionalContainer, HSplit, Layout, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.lexers import SimpleLexer
from prompt_toolkit.styles import Style as PTStyle
from prompt_toolkit.styles import default_ui_style, merge_styles as pt_merge_styles
from questionary.constants import DEFAULT_STYLE as Q_DEFAULT_STYLE
from rich.console import Console
from rich.text import Text

from labcrew.env import load_local_env
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
    "cmd_exit": {"zh": "退出", "en": "Exit"},
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
    "goodbye": {
        "zh": "再见 / Goodbye / さようなら / Au revoir / Adiós / Ciao / 안녕히 가세요 / مع السلامة / Tschüss",
        "en": "再见 / Goodbye / さようなら / Au revoir / Adiós / Ciao / 안녕히 가세요 / مع السلامة / Tschüss",
    },
}

_lang: str = os.environ.get("LABCREW_LANG", "en")
_INTEGRATION_STATUS: str | None = None


def _t(key: str) -> str:
    entry = MSGS.get(key, {})
    return entry.get(_lang, entry.get("en", key))


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


def _print_logo(console: Console, logo: str) -> None:
    lines = logo.splitlines()
    plain_lines = [Text.from_markup(line).plain for line in lines]
    inner_width = max(len(line) for line in plain_lines)
    border = "┄" * (inner_width + 4)

    console.print(f"  [dim sky_blue1]┌{border}┐[/dim sky_blue1]", markup=True)
    console.print(f"  [dim sky_blue1]┊{' ' * (inner_width + 4)}┊[/dim sky_blue1]", markup=True)
    for line, plain in zip(lines, plain_lines):
        right_pad = " " * (inner_width - len(plain))
        console.print(f"  [dim sky_blue1]┊[/dim sky_blue1]  {line}{right_pad}  [dim sky_blue1]┊[/dim sky_blue1]", markup=True)
    console.print(f"  [dim sky_blue1]┊{' ' * (inner_width + 4)}┊[/dim sky_blue1]", markup=True)
    console.print(f"  [dim sky_blue1]└{border}┘[/dim sky_blue1]", markup=True)


def _integration_status() -> str:
    """Return a compact, local-only integration summary for the prompt footer."""
    global _INTEGRATION_STATUS
    if _INTEGRATION_STATUS is not None:
        return _INTEGRATION_STATUS

    load_local_env()
    notion_ready = bool(os.environ.get("NOTION_API_KEY") and os.environ.get("NOTION_DATABASE_ID"))
    zotero_ready = (Path.home() / "Zotero" / "zotero.sqlite").exists()

    notion = "notion:cfg" if notion_ready else "notion:off"
    zotero = "zotero:ok" if zotero_ready else "zotero:off"
    _INTEGRATION_STATUS = f"{zotero} · {notion}"
    return _INTEGRATION_STATUS


# -- command specs for autocomplete ---------------------------------

_CMD_SPECS: list[tuple[str, str, str]] = [
    ("read-paper <source>", "Read and summarize a paper (PDF, URL, arXiv, DOI)", "阅读并总结论文（PDF、URL、arXiv、DOI）"),
    ("deep-read-method <source>", "Deep-read the method section of a paper", "深度解析论文的方法部分"),
    ("make-card <source>", "Create a literature card from a paper", "从论文生成文献卡片"),
    ("make-slides <source>", "Generate slide plan from a paper", "从论文生成 Slides 计划"),
    ("propose-research [question]", "Discover a research gap and propose directions", "发现研究 Gap 并提出方向"),
    ("design-experiment <question>", "Design a first-experiment scaffold", "设计第一版实验方案"),
    ("zotero list [collection]", "List recent Zotero items or a collection", "列出最近的 Zotero 文献或某个 collection"),
    ("zotero read <key>", "Read and summarize a Zotero item by key", "按 key 阅读并总结 Zotero 文献"),
    ("zotero plan <collection>", "Generate a reading plan for a collection", "为 collection 生成阅读计划"),
    ("zotero status <key> <status>", "Update reading status of a Zotero item", "更新 Zotero 文献阅读状态"),
    ("help", "Show available commands", "显示可用命令"),
    ("switch-lang", "Switch language (中文 / English)", "切换语言（中文 / English）"),
    ("exit", "Exit LabCrew", "退出 LabCrew"),
]


def _command_insert_text(fmt: str) -> str:
    command_parts = []
    for part in fmt.split():
        if part.startswith(("<", "[")):
            break
        command_parts.append(part)
    text = "/" + " ".join(command_parts)
    if len(command_parts) < len(fmt.split()):
        text += " "
    return text


def _build_autocomplete() -> list[tuple[str, str, str]]:
    choices: list[tuple[str, str, str]] = []
    for fmt, desc_en, desc_zh in _CMD_SPECS:
        desc = desc_zh if _lang == "zh" else desc_en
        choices.append((_command_insert_text(fmt), f"/{fmt}", desc))
    return choices


class SlashCommandCompleter(Completer):
    def __init__(self, choices: list[tuple[str, str, str]]) -> None:
        self.choices = choices

    def get_completions(self, document: object, complete_event: object) -> object:
        raw = document.text_before_cursor  # type: ignore[attr-defined]
        leading_spaces = len(raw) - len(raw.lstrip())
        prefix = raw[leading_spaces:]
        if not prefix.startswith("/") or " " in prefix:
            return

        query = prefix.lower()
        for insert_text, display, desc in self.choices:
            if prefix == insert_text.rstrip() or prefix.startswith(insert_text):
                continue
            searchable = f"{insert_text} {display}".lower()
            if query in searchable:
                yield Completion(
                    insert_text,
                    start_position=-len(prefix),
                    display=display,
                    display_meta=desc,
                )


def _run_command_prompt(
    width: int, choices: list[tuple[str, str, str]], style: PTStyle, lang: str,
) -> str | None:
    """Run a custom prompt_toolkit Application with completions below the input."""
    completer = SlashCommandCompleter(choices)
    buffer = Buffer(completer=completer, complete_while_typing=True, multiline=False)

    kb = KeyBindings()
    result: list[str] = []

    @kb.add("enter")
    def _submit(event: object) -> None:
        complete_state = buffer.complete_state
        if complete_state is not None and complete_state.current_completion is not None:
            buffer.apply_completion(complete_state.current_completion)
            return
        completions = list(
            completer.get_completions(
                buffer.document,
                CompleteEvent(completion_requested=True),
            )
        )
        if completions:
            buffer.apply_completion(completions[0])
            return
        result.append(buffer.text)
        event.app.exit()  # type: ignore[union-attr]

    @kb.add("c-c")
    def _cancel(event: object) -> None:
        event.app.exit()  # type: ignore[union-attr]

    sep = "─" * width
    lang_label = "中文" if lang == "zh" else "EN"

    cwd_label = os.path.basename(os.getcwd()) or os.getcwd()
    integrations = _integration_status()
    status_line = lambda: HTML(
        f"  <dim>? shortcuts · /help · /exit · lang: {lang_label} · dir: {cwd_label} · {integrations}</dim>"
    )
    sep_line = HTML(f"<dim>{sep}</dim>")

    input_window = Window(
        height=1,
        content=BufferControl(buffer=buffer, lexer=SimpleLexer("class:answer")),
    )

    has_completions = Condition(
        lambda: buffer.text.lstrip().startswith("/") and buffer.complete_state is not None
    )

    body = HSplit([
        Window(height=1, content=FormattedTextControl(sep_line)),       # top separator
        VSplit([                                                         # input line
            Window(width=2, content=FormattedTextControl(HTML("❯ ")), dont_extend_width=True),
            input_window,
        ]),
        ConditionalContainer(
            CompletionsMenu(max_height=12, scroll_offset=1),
            filter=has_completions,
        ),
        Window(height=1, content=FormattedTextControl(sep_line)),       # bottom separator
        Window(height=1, content=FormattedTextControl(status_line)),    # status
    ])

    layout = Layout(body, focused_element=input_window)

    app = Application(
        layout=layout,
        key_bindings=kb,
        style=style,
        include_default_pygments_style=False,
        full_screen=False,
    )
    app.run()
    return result[0] if result else None


# -- command dispatch -------------------------------------------------

def _parse_cmd(user_input: str) -> tuple[str, str]:
    """Return (command, args_string) from user input."""
    raw = user_input.strip()
    if not raw.startswith("/"):
        return ("", raw)
    try:
        parts = shlex.split(raw)
    except ValueError:
        parts = raw.split()
    if not parts:
        return ("", "")
    cmd = parts[0][1:]  # strip leading /
    rest = " ".join(parts[1:])
    return cmd, rest


def _dispatch(cmd: str, args: str) -> bool:
    """Run the command.  Return True to continue, False to quit."""
    handlers: dict[str, callable] = {
        "read-paper": _handle_read_paper,
        "deep-read-method": _handle_deep_method,
        "make-card": _handle_make_card,
        "make-slides": _handle_make_slides,
        "propose-research": _handle_propose,
        "design-experiment": _handle_experiment,
        "zotero": _handle_zotero_cmd,
        "help": _handle_help,
        "switch-lang": _handle_switch_lang,
        "exit": _handle_quit,
        "quit": _handle_quit,
        "q": _handle_quit,
    }

    handler = handlers.get(cmd)
    if handler is None:
        Console().print(f"  [red]Unknown command: /{cmd}[/red]  Type [bold]/help[/bold] to see available commands.", markup=True)
        return True
    return handler(args)


# -- individual command handlers -------------------------------------

def _handle_read_paper(args: str) -> bool:
    source = args.strip() if args.strip() else _ask_source()
    opts = _ask_read_opts(include_deep=True)
    _print_result(read_paper(source, **opts))
    return True


def _handle_deep_method(args: str) -> bool:
    source = args.strip() if args.strip() else _ask_source()
    opts = _ask_read_opts(include_deep=False)
    _print_result(deep_read_method(source, **opts))
    return True


def _handle_make_card(args: str) -> bool:
    source = args.strip() if args.strip() else _ask_source()
    opts = _ask_read_opts(include_deep=False)
    _print_result(create_literature_card(source, **opts))
    return True


def _handle_make_slides(args: str) -> bool:
    source = args.strip() if args.strip() else _ask_source()
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
    return True


def _handle_propose(args: str) -> bool:
    source = args.strip() if args.strip() else questionary.text(
        _t("propose_source_label"), validate=lambda v: True,
    ).unsafe_ask()
    question = None
    if not source.strip():
        question = questionary.text(
            _t("research_question_label"), validate=lambda v: len(v.strip()) > 0,
        ).unsafe_ask()
    _print_result(propose_research(source=source.strip() or None, research_question=question))
    return True


def _handle_experiment(args: str) -> bool:
    question = args.strip() if args.strip() else questionary.text(
        _t("experiment_question_label"), validate=lambda v: len(v.strip()) > 0,
    ).unsafe_ask()
    _print_result(design_experiment(research_question=question))
    return True


def _handle_zotero_cmd(args: str) -> bool:
    parts = args.strip().split()
    sub = parts[0] if parts else ""
    rest = " ".join(parts[1:]) if len(parts) > 1 else ""

    if not sub:
        # fall back to interactive zotero menu
        _run_zotero()
        return True

    if sub == "list":
        collection = rest.strip()
        item_type = questionary.text(_t("zotero_type")).unsafe_ask()
        limit = questionary.text(_t("zotero_limit"), default="20").unsafe_ask()
        with ZoteroAdapter() as adapter:
            if collection:
                items = adapter.get_collection_items(collection, limit=int(limit))
            else:
                type_filter = item_type.strip() or None
                items = adapter.list_items(item_type=type_filter, limit=int(limit))
        result = [
            {"key": i.key, "title": i.title, "year": i.year, "doi": i.doi, "venue": i.venue, "pdf": bool(i.attachments)}
            for i in items
        ]
        _print_result(result)
        return True

    if sub == "read":
        item_key = rest.strip() if rest.strip() else questionary.text(
            _t("zotero_item_key"), validate=lambda v: len(v.strip()) > 0,
        ).unsafe_ask()
        opts = _ask_read_opts(include_deep=True)
        _print_result(read_zotero_item(item_key.strip(), **opts))
        return True

    if sub == "plan":
        collection = rest.strip() if rest.strip() else questionary.text(
            _t("zotero_collection"), validate=lambda v: len(v.strip()) > 0,
        ).unsafe_ask()
        batch_size = int(questionary.text(_t("zotero_batch_size"), default="5").unsafe_ask())
        _print_result(plan_collection_reading(collection_key=collection.strip(), batch_size=batch_size))
        return True

    if sub == "status":
        key = rest.strip().split()[0] if rest.strip() else ""
        if not key:
            key = questionary.text(_t("zotero_item_key"), validate=lambda v: len(v.strip()) > 0).unsafe_ask()
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
        return True

    Console().print(f"  [red]Unknown zotero sub-command: {sub}[/red]", markup=True)
    return True


def _handle_help(_args: str) -> bool:
    lines = ["", "  [bold]Available commands:[/bold]", ""]
    for fmt, desc_en, desc_zh in _CMD_SPECS:
        desc = desc_zh if _lang == "zh" else desc_en
        lines.append(f"  [bold]/{fmt}[/bold]")
        lines.append(f"    {desc}")
    lines.append("")
    lines.append("  Tip: type [bold]/[/bold] to see command suggestions while typing.")
    lines.append("  Use [bold]/exit[/bold] to leave LabCrew.")
    Console().print(Panel("\n".join(lines), title="LabCrew Help", border_style="dim"), markup=True)
    return True


def _handle_switch_lang(_args: str) -> bool:
    global _lang
    _lang = "en" if _lang == "zh" else "zh"
    Console().print(f"  Language: [bold]{'中文' if _lang == 'zh' else 'English'}[/bold]", markup=True)
    return True


def _handle_quit(_args: str) -> bool:
    print(_t("goodbye"))
    return False


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



def start_tui() -> None:
    logo = (
        "[bold white]██       █████  ██████  [/bold white][bold sky_blue1] ██████ ██████  ███████ ██     ██ [/bold sky_blue1]\n"
        "[bold white]██      ██   ██ ██   ██ [/bold white][bold sky_blue1]██      ██   ██ ██      ██     ██ [/bold sky_blue1]\n"
        "[bold white]██      ███████ ██████  [/bold white][bold sky_blue1]██      ██████  █████   ██  █  ██ [/bold sky_blue1]\n"
        "[bold white]██      ██   ██ ██   ██ [/bold white][bold sky_blue1]██      ██   ██ ██      ██ ███ ██ [/bold sky_blue1]\n"
        "[bold white]███████ ██   ██ ██████  [/bold white][bold sky_blue1] ██████ ██   ██ ███████  ███ ███[/bold sky_blue1]"
    )
    console = Console()
    _print_logo(console, logo)
    console.print()
    console.print()
    console.print("  [bold white]@HLF Lab[/bold white] [dim]Research workflow assistant[/dim]", markup=True)
    console.print("  [dim]Designed and built by[/dim] [bold white]@HLF Lab[/bold white]", markup=True)
    console.print("  [dim]Tips:[/dim] [bold white]he-lingfeng.github.io[/bold white]", markup=True)

    width = min(console.width or 80, 100)

    pt_style = pt_merge_styles([
        default_ui_style(),
        Q_DEFAULT_STYLE,
        PTStyle.from_dict({
            # completion dropdown — blue text on dark navy background
            "completion-menu": "bg:#0d1b2a #6cb4ee",
            "completion-menu.completion": "bg:#0d1b2a #6cb4ee",
            "completion-menu.completion.current": "bg:#1b3a5c #ffffff bold",
            "completion-menu.meta": "bg:#0d1b2a #4a8ab5",
            "completion-menu.meta.current": "bg:#1b3a5c #6cb4ee",
            "completion-menu.multi-column-meta": "bg:#0d1b2a #4a8ab5",
            # input text color — blue instead of orange
            "answer": "fg:#6cb4ee bold",
        }),
    ])

    while True:
        try:
            choices = _build_autocomplete()
            user_input = _run_command_prompt(width, choices, pt_style, _lang)
        except KeyboardInterrupt:
            print()
            break

        if user_input is None:
            break

        cmd, args = _parse_cmd(user_input)

        if cmd == "" and args == "":
            continue

        if cmd == "":
            if args.lower() in ("quit", "exit", "q"):
                _handle_quit("")
                break
            continue

        try:
            print()
            should_continue = _dispatch(cmd, args)
            if not should_continue:
                break
        except Exception as exc:
            print(f"  [red]Error:[/red] {exc}", markup=True)
        print()
