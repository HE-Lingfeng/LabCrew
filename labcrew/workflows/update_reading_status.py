from __future__ import annotations

from labcrew.agents.notion_sync import NotionSyncAgent
from labcrew.config import load_config
from labcrew.tools.zotero_link_store import ZoteroLinkStore


def update_reading_status(
    zotero_key: str,
    status: str,
    sync_to_notion: bool = False,
) -> dict:
    """Update the reading status of a paper in the local link store, and optionally push to Notion."""
    config = load_config()

    with ZoteroLinkStore(db_path=config.link_store_path) as store:
        row = store.get(zotero_key)
        store.set_reading_status(zotero_key, status)

    result: dict = {
        "zotero_key": zotero_key,
        "reading_status": status,
        "title": row["title"] if row else "",
    }

    if sync_to_notion:
        agent = NotionSyncAgent()
        notion_result = agent.sync_status(zotero_key, status)
        result["notion"] = notion_result
    else:
        result["notion"] = {"status": "skipped", "reason": "--notion flag not set"}

    return result
