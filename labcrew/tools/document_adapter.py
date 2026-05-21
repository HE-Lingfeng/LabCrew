from __future__ import annotations


class DocumentAdapter:
    def create_document(self, title: str, body: str) -> dict[str, str]:
        return {"provider": "mock", "title": title, "body": body, "status": "created"}

