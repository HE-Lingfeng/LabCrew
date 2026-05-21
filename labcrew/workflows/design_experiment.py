from __future__ import annotations

from labcrew.agents import LabCrewAgent
from labcrew.schemas import Task, TaskResult, TaskType


def design_experiment(research_question: str, project: str = "general") -> TaskResult:
    agent = LabCrewAgent()
    return agent.run(Task(TaskType.DESIGN_EXPERIMENT, {"research_question": research_question}, project=project))
