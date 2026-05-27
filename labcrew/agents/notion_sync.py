from __future__ import annotations

import logging
from collections.abc import Callable

from labcrew.agents.base import BaseAgent
from labcrew.config import load_config
from labcrew.schemas import LiteratureCard, Task, TaskResult
from labcrew.tools.notion_adapter import NotionAdapter

logger = logging.getLogger(__name__)


class NotionSyncAgent(BaseAgent):
    name = "notion_sync"

    def __init__(self, adapter_factory: Callable[[str, str], NotionAdapter] | None = None) -> None:
        self.adapter_factory = adapter_factory or (
            lambda api_key, database_id: NotionAdapter(api_key=api_key, database_id=database_id)
        )

    def run(self, task: Task) -> TaskResult:
        card = task.payload.get("card")
        if not isinstance(card, LiteratureCard):
            raise ValueError("NotionSyncAgent requires a LiteratureCard payload.")
        return TaskResult(task_id=task.task_id, agent_name=self.name, data=self.publish_card(card))

    def publish_card(self, card: LiteratureCard) -> dict[str, object]:
        config = load_config().notion
        api_key = config.settings.get("api_key", "")
        database_id = config.settings.get("database_id", "")
        if not api_key or not database_id:
            return {"status": "skipped", "reason": "NOTION_API_KEY or NOTION_DATABASE_ID not set"}

        try:
            adapter = self.adapter_factory(api_key, database_id)
            existing = None
            if card.zotero_item_key:
                existing = adapter.find_by_zotero_key(card.zotero_item_key)
            if existing is None:
                existing = adapter.find_by_title(card.title)
            if existing:
                return {"status": "already_exists", "page_id": existing.page_id, "url": existing.url}

            ref = adapter.create_literature_card(card)
            return {"status": "created", "page_id": ref.page_id, "url": ref.url}
        except Exception as exc:
            logger.warning("Failed to save card to Notion: %s", exc)
            return {"status": "error", "reason": str(exc)}
