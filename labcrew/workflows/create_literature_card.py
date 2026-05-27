from __future__ import annotations

from labcrew.agents import LabCrewAgent
from labcrew.schemas import Task, TaskResult, TaskType


def create_literature_card(
    source: str,
    project: str = "general",
    save_journal: bool = True,
    journal_period: str = "weekly",
    save_to_notion: bool = False,
    save_to_cards: bool = False,
) -> TaskResult:
    agent = LabCrewAgent()
    return agent.run(
        Task(
            TaskType.MAKE_CARD,
            {"source": source, "save_journal": save_journal, "journal_period": journal_period, "save_to_notion": save_to_notion, "save_to_cards": save_to_cards},
            project=project,
        )
    )
