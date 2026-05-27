from __future__ import annotations

from labcrew.agents.base import BaseAgent
from labcrew.schemas import Task, TaskResult
from labcrew.tools.zotero_adapter import ZoteroAdapter


class LiteratureManagerAgent(BaseAgent):
    name = "literature_manager"

    def __init__(self, zotero: ZoteroAdapter | None = None) -> None:
        self.zotero = zotero or ZoteroAdapter()

    def run(self, task: Task) -> TaskResult:
        collection_key = task.payload.get("collection")
        if collection_key:
            items = self.zotero.get_collection_items(collection_key)
        else:
            items = self.zotero.list_items()
        data = [{"key": i.key, "title": i.title, "year": i.year, "doi": i.doi} for i in items]
        return TaskResult(
            task_id=task.task_id,
            agent_name=self.name,
            data=data,
            notes=[f"Synced {len(data)} items from Zotero."],
        )

