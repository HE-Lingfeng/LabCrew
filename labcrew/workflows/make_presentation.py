from __future__ import annotations

from labcrew.agents import LabCrewAgent
from labcrew.schemas import Task, TaskResult, TaskType


def make_presentation(source: str, project: str = "general") -> TaskResult:
    agent = LabCrewAgent()
    return agent.run(Task(TaskType.MAKE_PRESENTATION, {"source": source}, project=project))

