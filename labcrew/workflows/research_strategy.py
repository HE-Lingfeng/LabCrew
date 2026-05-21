from __future__ import annotations

from labcrew.schemas import TaskResult
from labcrew.workflows.propose_research import propose_research


def research_strategy(
    source: str | None = None,
    research_question: str | None = None,
    project: str = "general",
) -> TaskResult:
    return propose_research(source=source, research_question=research_question, project=project)
