from __future__ import annotations

from dataclasses import asdict
from typing import Any

from labcrew.schemas import LiteratureCard


class NotionAdapter:
    def create_literature_card(self, card: LiteratureCard) -> dict[str, Any]:
        return {"provider": "notion", "status": "mock", "payload": asdict(card)}

