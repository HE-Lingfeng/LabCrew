from __future__ import annotations

from pathlib import Path

from labcrew.agents import LabCrewAgent
from labcrew.schemas import Paper, Task, TaskResult, TaskType
from labcrew.tools import PDFParser, ZoteroAdapter


def read_zotero_item(
    item_key: str,
    project: str = "general",
    deep_method: bool = False,
    save_journal: bool = True,
    journal_period: str = "weekly",
    save_to_notion: bool = False,
) -> TaskResult:
    with ZoteroAdapter() as adapter:
        zotero_item = adapter.get_item(item_key)
        if zotero_item is None:
            raise ValueError(f"No Zotero item found with key: {item_key}")
        paper = adapter.to_paper(zotero_item)

    pdf_path = paper.pdf_path
    if pdf_path and Path(pdf_path).exists():
        text = PDFParser().read_text(Path(pdf_path))
        paper.sections["raw_text"] = text
        if not paper.abstract:
            paper.abstract = PDFParser().infer_abstract(text)

    agent = LabCrewAgent()
    return agent.run(
        Task(
            TaskType.READ_PAPER,
            {
                "paper": paper,
                "deep_method": deep_method,
                "save_journal": save_journal,
                "journal_period": journal_period,
                "save_to_notion": save_to_notion,
            },
            project=project,
        )
    )
