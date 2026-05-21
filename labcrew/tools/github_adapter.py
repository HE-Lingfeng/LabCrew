from __future__ import annotations

from dataclasses import asdict
from typing import Any

from labcrew.schemas import LiteratureCard


class GitHubAdapter:
    def create_literature_card(self, card: LiteratureCard, path: str | None = None) -> dict[str, Any]:
        return {"provider": "github", "status": "mock", "path": path, "payload": asdict(card)}

