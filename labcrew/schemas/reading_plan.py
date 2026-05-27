from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PaperReadingStatus:
    zotero_key: str
    title: str
    year: int | None
    doi: str | None
    has_pdf: bool
    has_card: bool
    has_notion_sync: bool
    has_journal_entry: bool
    status: str


@dataclass
class CollectionReadingPlan:
    collection_key: str
    collection_name: str
    total_items: int
    read_count: int
    unread_count: int
    synced_to_notion_count: int
    reading_count: int = 0
    skipped_count: int = 0
    items: list[PaperReadingStatus] = field(default_factory=list)
    next_batch: list[PaperReadingStatus] = field(default_factory=list)
