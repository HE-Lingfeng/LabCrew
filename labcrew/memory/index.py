from __future__ import annotations

from pathlib import Path


class LocalIndex:
    def __init__(self, root: Path = Path("data/cards")) -> None:
        self.root = root

    def list_cards(self) -> list[Path]:
        if not self.root.exists():
            return []
        return sorted(self.root.glob("*.md"))

