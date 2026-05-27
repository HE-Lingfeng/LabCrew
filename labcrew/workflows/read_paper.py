from __future__ import annotations

from labcrew.agents import LabCrewAgent
from labcrew.schemas import Task, TaskResult, TaskType


def read_paper(
    source: str,
    project: str = "general",
    deep_method: bool = False,
    save_journal: bool = True,
    journal_period: str = "weekly",
    save_to_notion: bool = False,
) -> TaskResult:
    agent = LabCrewAgent()
    return agent.run(
        Task(
            TaskType.READ_PAPER,
            {
                "source": source,
                "deep_method": deep_method,
                "save_journal": save_journal,
                "journal_period": journal_period,
                "save_to_notion": save_to_notion,
            },
            project=project,
        )
    )
