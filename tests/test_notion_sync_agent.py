from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from labcrew.agents.notion_sync import NotionSyncAgent
from labcrew.schemas import LiteratureCard
from labcrew.tools.notion_adapter import NotionPageRef


class FakeNotionAdapter:
    def __init__(
        self,
        existing_by_key: NotionPageRef | None = None,
        existing_by_title: NotionPageRef | None = None,
    ) -> None:
        self.existing_by_key = existing_by_key
        self.existing_by_title = existing_by_title
        self.created: list[LiteratureCard] = []
        self.queries: list[tuple[str, str]] = []

    def find_by_zotero_key(self, key: str) -> NotionPageRef | None:
        self.queries.append(("zotero", key))
        return self.existing_by_key

    def find_by_title(self, title: str) -> NotionPageRef | None:
        self.queries.append(("title", title))
        return self.existing_by_title

    def create_literature_card(self, card: LiteratureCard) -> NotionPageRef:
        self.created.append(card)
        return NotionPageRef(page_id="new-page", url="https://notion.test/new-page", title=card.title)


class NotionSyncAgentTests(unittest.TestCase):
    def test_publish_card_skips_when_not_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.dict(os.environ, {}, clear=True), patch(
                "pathlib.Path.cwd", return_value=Path(tmp_dir)
            ):
                result = NotionSyncAgent().publish_card(LiteratureCard(title="A Paper"))

        self.assertEqual(result["status"], "skipped")

    def test_publish_card_prefers_zotero_key_for_dedupe(self) -> None:
        existing = NotionPageRef(page_id="existing", url="https://notion.test/existing", title="A Paper")
        fake = FakeNotionAdapter(existing_by_key=existing)

        with tempfile.TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            env_path.write_text("NOTION_API_KEY=test\nNOTION_DATABASE_ID=db\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True), patch(
                "pathlib.Path.cwd", return_value=Path(tmp_dir)
            ):
                result = NotionSyncAgent(adapter_factory=lambda api_key, database_id: fake).publish_card(
                    LiteratureCard(title="A Paper", zotero_item_key="Z123")
                )

        self.assertEqual(result["status"], "already_exists")
        self.assertEqual(fake.queries, [("zotero", "Z123")])
        self.assertEqual(fake.created, [])

    def test_publish_card_creates_when_no_existing_page_matches(self) -> None:
        fake = FakeNotionAdapter()

        with tempfile.TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            env_path.write_text("NOTION_API_KEY=test\nNOTION_DATABASE_ID=db\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True), patch(
                "pathlib.Path.cwd", return_value=Path(tmp_dir)
            ):
                result = NotionSyncAgent(adapter_factory=lambda api_key, database_id: fake).publish_card(
                    LiteratureCard(title="A Paper")
                )

        self.assertEqual(result["status"], "created")
        self.assertEqual(fake.queries, [("title", "A Paper")])
        self.assertEqual(len(fake.created), 1)


if __name__ == "__main__":
    unittest.main()
