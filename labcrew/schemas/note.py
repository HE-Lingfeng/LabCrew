from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LiteratureCard:
    title: str
    paper_id: str | None = None
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    tags: list[str] = field(default_factory=list)
    one_sentence_summary: str = ""
    problem: str = ""
    method: str = ""
    key_results: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    useful_for: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    zotero_item_key: str | None = None
    source_pdf_path: str | None = None
    external_links: dict[str, str] = field(default_factory=dict)

