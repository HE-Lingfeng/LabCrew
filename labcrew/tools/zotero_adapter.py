from __future__ import annotations

from typing import Any


class ZoteroAdapter:
    """Read-only Zotero facade. Replace mock methods with API calls later."""

    def list_items(self, collection: str | None = None) -> list[dict[str, Any]]:
        return [
            {
                "title": "Mock Zotero Item",
                "collection": collection,
                "item_key": "MOCK0001",
                "status": "mock",
            }
        ]

    def find_by_title(self, title: str) -> dict[str, Any] | None:
        return None

