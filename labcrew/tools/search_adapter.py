from __future__ import annotations


class SearchAdapter:
    def search(self, query: str, limit: int = 5) -> list[dict[str, str]]:
        return [{"title": query, "source": "mock", "summary": "Search integration placeholder."}][:limit]

