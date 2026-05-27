from __future__ import annotations

from labcrew.config import load_config
from labcrew.schemas.reading_plan import CollectionReadingPlan, PaperReadingStatus
from labcrew.tools import ZoteroAdapter
from labcrew.tools.zotero_link_store import VALID_STATUSES, ZoteroLinkStore


def plan_collection_reading(
    collection_key: str,
    batch_size: int = 5,
) -> CollectionReadingPlan:
    """Generate a reading plan for a Zotero collection.

    Uses ZoteroLinkStore as the single source of truth for per-paper status.
    Seeds new items from Zotero that aren't yet tracked.
    """
    config = load_config()
    with ZoteroAdapter() as zotero:
        items = zotero.get_collection_items(collection_key)
        collections = {c["key"]: c["name"] for c in zotero.list_collections()}

    collection_name = collections.get(collection_key, collection_key)

    with ZoteroLinkStore(db_path=config.link_store_path) as store:
        store.seed_from_zotero_items(items)
        summary = store.get_status_summary([item.key for item in items])

    statuses: list[PaperReadingStatus] = []
    for item in items:
        row = summary.get(item.key, {})
        status = row.get("reading_status", "unread")
        if status not in VALID_STATUSES:
            status = "unread"
        has_notion = bool(row.get("notion_url"))

        statuses.append(PaperReadingStatus(
            zotero_key=item.key,
            title=item.title,
            year=item.year,
            doi=item.doi,
            has_pdf=bool(item.attachments),
            has_card=bool(row.get("card_path")),
            has_notion_sync=has_notion,
            has_journal_entry=False,  # no longer scanned separately
            status=status,
        ))

    read_items = [s for s in statuses if s.status == "read"]
    unread_items = [s for s in statuses if s.status == "unread"]
    reading_items = [s for s in statuses if s.status == "reading"]
    skipped_items = [s for s in statuses if s.status == "skipped"]
    synced_items = [s for s in statuses if s.has_notion_sync]

    next_batch = (reading_items + unread_items)[:batch_size]

    return CollectionReadingPlan(
        collection_key=collection_key,
        collection_name=collection_name,
        total_items=len(statuses),
        read_count=len(read_items),
        unread_count=len(unread_items),
        reading_count=len(reading_items),
        skipped_count=len(skipped_items),
        synced_to_notion_count=len(synced_items),
        items=statuses,
        next_batch=next_batch,
    )
