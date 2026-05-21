from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PaperFigure:
    figure_id: str
    page_number: int
    image_path: str
    reason: str
    keywords: list[str] = field(default_factory=list)
    bbox: tuple[float, float, float, float] | None = None


@dataclass
class PaperIngestionMetadata:
    source: str
    source_type: str
    text_char_count: int
    figure_snapshot_count: int = 0
    artifact_dir: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class Paper:
    title: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    abstract: str | None = None
    sections: dict[str, str] = field(default_factory=dict)
    references: list[str] = field(default_factory=list)
    doi: str | None = None
    arxiv_id: str | None = None
    pdf_path: str | None = None
    source_url: str | None = None
    zotero_item_key: str | None = None
    figures: list[PaperFigure] = field(default_factory=list)
    ingestion: PaperIngestionMetadata | None = None
