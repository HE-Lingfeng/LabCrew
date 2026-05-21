from __future__ import annotations

from labcrew.agents.base import BaseAgent
from labcrew.schemas import LiteratureCard, Slide, SlidePlan, Task, TaskResult


class PresentationAgent(BaseAgent):
    name = "presentation"

    def run(self, task: Task) -> TaskResult:
        card = task.payload.get("card")
        if not isinstance(card, LiteratureCard):
            raise ValueError("PresentationAgent requires a LiteratureCard payload.")

        plan = SlidePlan(
            title=f"Paper Brief: {card.title}",
            audience=str(task.payload.get("audience", "research group")),
            duration_minutes=int(task.payload.get("duration_minutes", 10)),
            source_papers=[card.title],
            slides=[
                Slide(
                    title="Motivation",
                    purpose="Set up the research problem.",
                    key_message=card.problem or card.one_sentence_summary,
                    bullets=[card.one_sentence_summary],
                ),
                Slide(
                    title="Method",
                    purpose="Explain the central technical idea.",
                    key_message=card.method,
                    bullets=[card.method],
                ),
                Slide(
                    title="Discussion",
                    purpose="Prepare group discussion.",
                    key_message="Connect the paper to future work.",
                    bullets=card.open_questions or ["What should we test next?"],
                ),
            ],
        )
        return TaskResult(task_id=task.task_id, agent_name=self.name, data=plan)

