from __future__ import annotations

from labcrew.agents.base import BaseAgent
from labcrew.schemas import Task, TaskResult


class WritingAgent(BaseAgent):
    name = "writing"

    def run(self, task: Task) -> TaskResult:
        topic = str(task.payload.get("topic") or task.payload.get("prompt") or "")
        draft = {
            "topic": topic,
            "draft": "Placeholder academic draft. Connect model-backed writing in a later phase.",
        }
        return TaskResult(task_id=task.task_id, agent_name=self.name, data=draft)

