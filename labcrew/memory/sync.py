from __future__ import annotations

from labcrew.schemas import LiteratureCard
from labcrew.tools.github_adapter import GitHubAdapter
from labcrew.tools.notion_adapter import NotionAdapter


class SyncManager:
    def __init__(self, notion: NotionAdapter | None = None, github: GitHubAdapter | None = None) -> None:
        self.notion = notion or NotionAdapter()
        self.github = github or GitHubAdapter()

    def sync_card_mock(self, card: LiteratureCard) -> dict[str, object]:
        return {
            "notion": self.notion.create_literature_card(card),
            "github": self.github.create_literature_card(card),
        }

