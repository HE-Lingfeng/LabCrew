from __future__ import annotations

from labcrew.agents import LabCrewAgent
from labcrew.schemas import Task, TaskResult, TaskType


def deep_read_method(
    source: str,
    project: str = "general",
    save_journal: bool = True,
    journal_period: str = "weekly",
) -> TaskResult:
    agent = LabCrewAgent()
    return agent.run(
        Task(
            TaskType.DEEP_READ_METHOD,
            {"source": source, "save_journal": save_journal, "journal_period": journal_period},
            project=project,
        )
    )
