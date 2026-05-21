from __future__ import annotations

from labcrew.agents.base import BaseAgent
from labcrew.schemas import Task, TaskResult
from labcrew.tools.zotero_adapter import ZoteroAdapter


class LiteratureManagerAgent(BaseAgent):
    name = "literature_manager"

    def __init__(self, zotero: ZoteroAdapter | None = None) -> None:
        self.zotero = zotero or ZoteroAdapter()

    def run(self, task: Task) -> TaskResult:
        collection = task.payload.get("collection")
        items = self.zotero.list_items(collection=collection)
        return TaskResult(
            task_id=task.task_id,
            agent_name=self.name,
            data=items,
            notes=["ZoteroAdapter is mock/read-only in the scaffold."],
        )

