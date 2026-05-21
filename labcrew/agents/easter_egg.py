from __future__ import annotations

from labcrew.agents.base import BaseAgent
from labcrew.schemas import Task, TaskResult


class WeekendEasterEggAgent(BaseAgent):
    name = "weekend_easter_egg"

    def run(self, task: Task) -> TaskResult:
        city = str(task.payload.get("city", "your city"))
        recommendation = {
            "city": city,
            "ideas": [
                "Take a low-effort walk somewhere green.",
                "Visit a quiet cafe with no paper-reading agenda.",
                "Pick one small exhibition, bookstore, or live event and call it enough.",
            ],
        }
        return TaskResult(task_id=task.task_id, agent_name=self.name, data=recommendation)

