from __future__ import annotations

import unittest
from unittest.mock import Mock

from labcrew.schemas import LiteratureCard
from labcrew.tools.notion_adapter import NotionAdapter


class NotionAdapterTests(unittest.TestCase):
    def test_card_to_properties_uses_available_database_columns(self) -> None:
        adapter = NotionAdapter.__new__(NotionAdapter)
        adapter._db_properties = {"Name": "title", "Authors": "rich_text", "Status": "select"}
        card = LiteratureCard(title="A Paper", authors=["Ada", "Mira"], one_sentence_summary="Useful.")

        properties = adapter._card_to_properties(card, "Read")

        self.assertEqual(set(properties), {"Name", "Authors", "Status"})
        self.assertEqual(properties["Name"]["title"][0]["text"]["content"], "A Paper")
        self.assertEqual(properties["Authors"]["rich_text"][0]["text"]["content"], "Ada, Mira")

    def test_card_to_properties_uses_database_title_column_name(self) -> None:
        adapter = NotionAdapter.__new__(NotionAdapter)
        adapter._db_properties = {"Paper": "title", "Name": "rich_text"}
        card = LiteratureCard(title="A Paper")

        properties = adapter._card_to_properties(card, "Read")

        self.assertEqual(set(properties), {"Paper"})
        self.assertEqual(properties["Paper"]["title"][0]["text"]["content"], "A Paper")

    def test_find_by_zotero_key_sends_valid_notion_filter_payload(self) -> None:
        adapter = NotionAdapter.__new__(NotionAdapter)
        adapter._db_properties = {"Name": "title", "Zotero Key": "rich_text"}
        adapter._database_id = "db"
        response = Mock()
        response.json.return_value = {"results": []}
        adapter._post = Mock(return_value=response)

        result = adapter.find_by_zotero_key("Z123")

        self.assertIsNone(result)
        adapter._post.assert_called_once_with(
            "/databases/db/query",
            json={"filter": {"property": "Zotero Key", "rich_text": {"equals": "Z123"}}},
        )

    def test_card_to_children_preserves_card_body_when_database_has_only_title(self) -> None:
        adapter = NotionAdapter.__new__(NotionAdapter)
        card = LiteratureCard(
            title="A Paper",
            authors=["Ada"],
            year=2026,
            one_sentence_summary="A compact summary.",
            problem="The problem.",
            method="The method.",
            key_results=["Result one", "Result two"],
        )

        children = adapter._card_to_children(card)

        block_text = str(children)
        self.assertIn("Authors: Ada", block_text)
        self.assertIn("One Sentence Summary", block_text)
        self.assertIn("A compact summary.", block_text)
        self.assertIn("Result one", block_text)


if __name__ == "__main__":
    unittest.main()
