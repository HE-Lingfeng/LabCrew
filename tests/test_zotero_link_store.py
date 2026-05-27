from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from labcrew.tools.zotero_adapter import ZoteroItem
from labcrew.tools.zotero_link_store import ZoteroLinkStore, to_notion_status


class ZoteroLinkStoreTests(unittest.TestCase):
    def test_upsert_rejects_unknown_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with ZoteroLinkStore(Path(tmp_dir) / "links.db") as store:
                with self.assertRaises(ValueError):
                    store.upsert("ABC123", unknown_field="value")

    def test_status_setter_validates_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with ZoteroLinkStore(Path(tmp_dir) / "links.db") as store:
                with self.assertRaises(ValueError):
                    store.set_reading_status("ABC123", "done")

    def test_seed_from_zotero_items_preserves_existing_status(self) -> None:
        items = [
            ZoteroItem(key="ABC123", item_type="journalArticle", title="A Paper"),
            ZoteroItem(key="XYZ789", item_type="conferencePaper", title="Another Paper"),
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            with ZoteroLinkStore(Path(tmp_dir) / "links.db") as store:
                store.set_reading_status("ABC123", "reading")
                inserted = store.seed_from_zotero_items(items)
                existing = store.get("ABC123")
                created = store.get("XYZ789")

        self.assertEqual(inserted, 1)
        self.assertEqual(existing["reading_status"], "reading")
        self.assertEqual(created["title"], "Another Paper")
        self.assertEqual(created["reading_status"], "unread")

    def test_notion_status_mapping(self) -> None:
        self.assertEqual(to_notion_status("unread"), "To Read")
        self.assertEqual(to_notion_status("reading"), "Reading")
        self.assertEqual(to_notion_status("read"), "Read")
        self.assertEqual(to_notion_status("skipped"), "Skipped")


if __name__ == "__main__":
    unittest.main()
