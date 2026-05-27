from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
import traceback
from typing import Any, Callable

from labcrew.tools import ZoteroAdapter
from labcrew import workflows


ActionHandler = Callable[[dict[str, Any]], Any]


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return value


def call_action(action: str, **params: Any) -> Any:
    try:
        handler = _ACTIONS[action]
    except KeyError as exc:
        known = ", ".join(sorted(_ACTIONS))
        raise ValueError(f"Unknown LabCrew action '{action}'. Available actions: {known}") from exc
    return handler(params)


def run_action(action: str, **params: Any) -> dict[str, Any]:
    try:
        raw = call_action(action, **params)
        data = to_jsonable(raw)
        return {
            "ok": True,
            "data": data,
            "warnings": _collect_warnings(data),
            "artifacts": _collect_artifacts(data),
            "error": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "data": None,
            "warnings": [],
            "artifacts": [],
            "error": _friendly_error(exc),
        }


def _read_paper(params: dict[str, Any]) -> Any:
    return workflows.read_paper(
        _required(params, "source"),
        project=str(params.get("project", "general")),
        deep_method=bool(params.get("deep_method", False)),
        save_journal=bool(params.get("save_journal", True)),
        journal_period=str(params.get("journal_period", "weekly")),
        save_to_notion=bool(params.get("save_to_notion", False)),
        save_to_cards=bool(params.get("save_to_cards", False)),
    )


def _deep_read_method(params: dict[str, Any]) -> Any:
    return workflows.deep_read_method(
        _required(params, "source"),
        project=str(params.get("project", "general")),
        save_journal=bool(params.get("save_journal", True)),
        journal_period=str(params.get("journal_period", "weekly")),
        save_to_notion=bool(params.get("save_to_notion", False)),
        save_to_cards=bool(params.get("save_to_cards", False)),
    )


def _make_card(params: dict[str, Any]) -> Any:
    return workflows.create_literature_card(
        _required(params, "source"),
        project=str(params.get("project", "general")),
        save_journal=bool(params.get("save_journal", True)),
        journal_period=str(params.get("journal_period", "weekly")),
        save_to_notion=bool(params.get("save_to_notion", False)),
        save_to_cards=bool(params.get("save_to_cards", False)),
    )


def _read_zotero_item(params: dict[str, Any]) -> Any:
    return workflows.read_zotero_item(
        _required(params, "item_key"),
        project=str(params.get("project", "general")),
        deep_method=bool(params.get("deep_method", False)),
        save_journal=bool(params.get("save_journal", True)),
        journal_period=str(params.get("journal_period", "weekly")),
        save_to_notion=bool(params.get("save_to_notion", False)),
        save_to_cards=bool(params.get("save_to_cards", False)),
    )


def _plan_zotero_collection(params: dict[str, Any]) -> Any:
    return workflows.plan_collection_reading(
        collection_key=_required(params, "collection"),
        batch_size=int(params.get("batch_size", 5)),
    )


def _update_reading_status(params: dict[str, Any]) -> Any:
    return workflows.update_reading_status(
        zotero_key=_required(params, "key"),
        status=_required(params, "status"),
        sync_to_notion=bool(params.get("sync_to_notion", False)),
    )


def _make_slides(params: dict[str, Any]) -> Any:
    source = _required(params, "source")
    if str(params.get("format", "plan")) == "html":
        return workflows.make_html_slides(source, project=str(params.get("project", "general")))
    return workflows.make_presentation(source, project=str(params.get("project", "general")))


def _propose_research(params: dict[str, Any]) -> Any:
    source = params.get("source")
    question = params.get("research_question") or params.get("question")
    if not source and not question:
        raise ValueError("Either source or research_question is required.")
    return workflows.propose_research(
        source=source,
        research_question=question,
        project=str(params.get("project", "general")),
    )


def _research_strategy(params: dict[str, Any]) -> Any:
    source = params.get("source")
    question = params.get("research_question") or params.get("question")
    if not source and not question:
        raise ValueError("Either source or research_question is required.")
    return workflows.research_strategy(
        source=source,
        research_question=question,
        project=str(params.get("project", "general")),
    )


def _generate_idea(params: dict[str, Any]) -> Any:
    source = params.get("source")
    question = params.get("research_question") or params.get("question")
    if not source and not question:
        raise ValueError("Either source or research_question is required.")
    return workflows.generate_idea(
        source=source,
        research_question=question,
        project=str(params.get("project", "general")),
    )


def _design_experiment(params: dict[str, Any]) -> Any:
    return workflows.design_experiment(
        _required(params, "research_question"),
        project=str(params.get("project", "general")),
    )


def _zotero_list(params: dict[str, Any]) -> list[dict[str, Any]]:
    with ZoteroAdapter() as adapter:
        if params.get("collection"):
            items = adapter.get_collection_items(str(params["collection"]), limit=int(params.get("limit", 20)))
        else:
            item_type = params.get("type")
            items = adapter.list_items(item_type=str(item_type) if item_type else None, limit=int(params.get("limit", 20)))
    return [
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


def _required(params: dict[str, Any], name: str) -> str:
    value = params.get(name)
    if value is None or value == "":
        raise ValueError(f"Missing required parameter: {name}")
    return str(value)


def _collect_warnings(data: Any) -> list[str]:
    warnings: list[str] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            nested = value.get("warnings")
            if isinstance(nested, list):
                warnings.extend(str(item) for item in nested if item)
            notes = value.get("notes")
            if isinstance(notes, list):
                warnings.extend(str(item) for item in notes if item)
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(data)
    return list(dict.fromkeys(warnings))


def _collect_artifacts(data: Any) -> list[str]:
    artifacts: list[str] = []
    path_keys = {"path", "pdf_path", "image_path", "artifact_dir", "card_path", "output_path"}

    def visit(value: Any, key: str | None = None) -> None:
        if isinstance(value, dict):
            for child_key, child in value.items():
                visit(child, child_key)
        elif isinstance(value, list):
            for item in value:
                visit(item, key)
        elif key in path_keys and isinstance(value, str) and value:
            artifacts.append(value)

    visit(data)
    return list(dict.fromkeys(artifacts))


def _friendly_error(exc: Exception) -> str:
    if isinstance(exc, FileNotFoundError):
        return f"File not found: {exc.filename or exc}"
    if isinstance(exc, PermissionError):
        return f"Permission denied: {exc.filename or exc}"
    if isinstance(exc, ValueError):
        return str(exc)
    if "NOTION" in str(exc).upper() or "notion" in exc.__class__.__name__.lower():
        return f"Notion operation failed: {exc}"
    if "zotero" in str(exc).lower() or "Zotero" in exc.__class__.__name__:
        return f"Zotero operation failed: {exc}"
    return f"{exc.__class__.__name__}: {exc}\n{traceback.format_exc(limit=2).strip()}"


_ACTIONS: dict[str, ActionHandler] = {
    "read_paper": _read_paper,
    "deep_read_method": _deep_read_method,
    "make_card": _make_card,
    "read_zotero_item": _read_zotero_item,
    "plan_zotero_collection": _plan_zotero_collection,
    "update_reading_status": _update_reading_status,
    "make_slides": _make_slides,
    "propose_research": _propose_research,
    "research_strategy": _research_strategy,
    "generate_idea": _generate_idea,
    "design_experiment": _design_experiment,
    "zotero_list": _zotero_list,
}
