from __future__ import annotations

from labcrew.agents import LabCrewAgent
from labcrew.schemas import Task, TaskResult, TaskType


def propose_research(
    source: str | None = None,
    research_question: str | None = None,
    project: str = "general",
) -> TaskResult:
    agent = LabCrewAgent()
    payload: dict[str, object] = {}
    if source:
        payload["source"] = source
    if research_question:
        payload["research_question"] = research_question
    task_type = TaskType.CRITIQUE_PAPER if source else TaskType.DESIGN_EXPERIMENT
    return agent.run(Task(task_type, payload, project=project))
