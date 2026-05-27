from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from typing import Any

from labcrew.tools import ZoteroAdapter
from labcrew.workflows import (
    create_literature_card,
    deep_read_method,
    design_experiment,
    generate_idea,
    make_presentation,
    propose_research,
    read_paper,
    read_zotero_item,
    research_strategy,
)


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    return value


def _print_result(result: Any) -> None:
    print(json.dumps(_to_jsonable(result), ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="labcrew", description="Multi-agent research assistant scaffold.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    read_parser = subparsers.add_parser("read-paper", help="Read and summarize a paper source.")
    read_parser.add_argument("source")
    read_parser.add_argument("--deep-method", action="store_true", help="Also include a detailed method explanation.")
    read_parser.add_argument(
        "--journal-period",
        default="weekly",
        help="Journal period: daily, weekly, monthly, quarterly, yearly, or a value like 14d.",
    )
    read_parser.add_argument("--no-journal", action="store_true", help="Do not save the card report into a journal file.")
    read_parser.add_argument("--notion", action="store_true", help="Save the literature card to Notion.")
    read_parser.add_argument("--cards", action="store_true", help="Save the literature card as a local Markdown file (CardStore).")

    deep_method_parser = subparsers.add_parser(
        "deep-read-method",
        help="Read a paper and explain the method section in detail.",
    )
    deep_method_parser.add_argument("source")
    deep_method_parser.add_argument(
        "--journal-period",
        default="weekly",
        help="Journal period: daily, weekly, monthly, quarterly, yearly, or a value like 14d.",
    )
    deep_method_parser.add_argument(
        "--no-journal",
        action="store_true",
        help="Do not save the card report into a journal file.",
    )
    deep_method_parser.add_argument("--notion", action="store_true", help="Save the literature card to Notion.")
    deep_method_parser.add_argument("--cards", action="store_true", help="Save the literature card as a local Markdown file (CardStore).")

    card_parser = subparsers.add_parser("make-card", help="Create a local literature card payload.")
    card_parser.add_argument("source")
    card_parser.add_argument(
        "--journal-period",
        default="weekly",
        help="Journal period: daily, weekly, monthly, quarterly, yearly, or a value like 14d.",
    )
    card_parser.add_argument("--no-journal", action="store_true", help="Do not save the card report into a journal file.")
    card_parser.add_argument("--notion", action="store_true", help="Save the literature card to Notion.")
    card_parser.add_argument("--cards", action="store_true", help="Save the literature card as a local Markdown file (CardStore).")

    slides_parser = subparsers.add_parser("make-slides", help="Create a slide plan from a paper source.")
    slides_parser.add_argument("source")

    experiment_parser = subparsers.add_parser(
        "design-experiment",
        help="Create a first experiment scaffold for a candidate research gap.",
    )
    experiment_parser.add_argument("research_question", help="Seed research area or unresolved problem.")

    proposal_parser = subparsers.add_parser(
        "propose-research",
        help="Discover a candidate research gap and generate a proposal scaffold.",
    )
    proposal_source = proposal_parser.add_mutually_exclusive_group(required=True)
    proposal_source.add_argument("--source", help="Paper source to use as evidence for gap discovery.")
    proposal_source.add_argument("--question", help="Seed research area or unresolved problem to validate.")

    strategy_parser = subparsers.add_parser("research-strategy", help="Compatibility alias for propose-research.")
    strategy_source = strategy_parser.add_mutually_exclusive_group(required=True)
    strategy_source.add_argument("--source", help="Paper source to use as evidence for gap discovery.")
    strategy_source.add_argument("--question", help="Seed research area or unresolved problem to validate.")

    idea_parser = subparsers.add_parser("generate-idea", help="Compatibility alias for propose-research.")
    idea_source = idea_parser.add_mutually_exclusive_group(required=True)
    idea_source.add_argument("--source", help="Paper source to use as evidence for gap discovery.")
    idea_source.add_argument("--question", help="Seed research area or unresolved problem to validate.")

    zotero_parser = subparsers.add_parser("zotero", help="Interact with your local Zotero library.")
    zotero_sub = zotero_parser.add_subparsers(dest="zotero_command", required=True)

    zotero_list = zotero_sub.add_parser("list", help="List recent Zotero items or collections.")
    zotero_list.add_argument("--collection", help="Collection key to list items from.")
    zotero_list.add_argument("--type", help="Item type filter, e.g. journalArticle, conferencePaper.")
    zotero_list.add_argument("--limit", type=int, default=20, help="Max items to show.")

    zotero_read = zotero_sub.add_parser("read", help="Read and summarize a Zotero item by key.")
    zotero_read.add_argument("item_key", help="Zotero item key (e.g. ABC12345).")
    zotero_read.add_argument("--deep-method", action="store_true", help="Also include a detailed method explanation.")
    zotero_read.add_argument("--journal-period", default="weekly", help="Journal period.")
    zotero_read.add_argument("--no-journal", action="store_true", help="Do not save journal entry.")
    zotero_read.add_argument("--notion", action="store_true", help="Save the literature card to Notion.")
    zotero_read.add_argument("--cards", action="store_true", help="Save the literature card as a local Markdown file (CardStore).")

    return parser


def _handle_zotero(args: argparse.Namespace) -> Any:
    if args.zotero_command == "list":
        with ZoteroAdapter() as adapter:
            if args.collection:
                items = adapter.get_collection_items(args.collection, limit=args.limit)
            else:
                items = adapter.list_items(item_type=args.type, limit=args.limit)
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
    if args.zotero_command == "read":
        return read_zotero_item(
            args.item_key,
            deep_method=args.deep_method,
            save_journal=not args.no_journal,
            journal_period=args.journal_period,
            save_to_notion=args.notion,
            save_to_cards=args.cards,
        )
    raise ValueError(f"Unknown zotero command: {args.zotero_command}")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "read-paper":
        _print_result(
            read_paper(
                args.source,
                deep_method=args.deep_method,
                save_journal=not args.no_journal,
                journal_period=args.journal_period,
                save_to_notion=args.notion,
                save_to_cards=args.cards,
            )
        )
    elif args.command == "deep-read-method":
        _print_result(
            deep_read_method(
                args.source,
                save_journal=not args.no_journal,
                journal_period=args.journal_period,
                save_to_notion=args.notion,
                save_to_cards=args.cards,
            )
        )
    elif args.command == "make-card":
        _print_result(
            create_literature_card(
                args.source,
                save_journal=not args.no_journal,
                journal_period=args.journal_period,
                save_to_notion=args.notion,
                save_to_cards=args.cards,
            )
        )
    elif args.command == "make-slides":
        _print_result(make_presentation(args.source))
    elif args.command == "design-experiment":
        _print_result(design_experiment(args.research_question))
    elif args.command == "propose-research":
        _print_result(propose_research(source=args.source, research_question=args.question))
    elif args.command == "research-strategy":
        _print_result(research_strategy(source=args.source, research_question=args.question))
    elif args.command == "generate-idea":
        _print_result(generate_idea(source=args.source, research_question=args.question))
    elif args.command == "zotero":
        _print_result(_handle_zotero(args))
    else:
        parser.error(f"Unknown command: {args.command}")
