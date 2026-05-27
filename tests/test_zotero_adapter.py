from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from labcrew.tools import ZoteroAdapter, ZoteroAttachment, ZoteroItem


def _build_test_db(db_path: Path, storage_dir: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE items (itemID INTEGER PRIMARY KEY, itemTypeID INT, dateAdded TIMESTAMP,
            dateModified TIMESTAMP, clientDateModified TIMESTAMP, libraryID INT, key TEXT,
            version INT, synced INT);
        CREATE TABLE itemTypes (itemTypeID INTEGER PRIMARY KEY, typeName TEXT,
            templateItemTypeID INT, display INT);
        CREATE TABLE itemData (itemID INT, fieldID INT, valueID INT);
        CREATE TABLE itemDataValues (valueID INTEGER PRIMARY KEY, value TEXT);
        CREATE TABLE fields (fieldID INTEGER PRIMARY KEY, fieldName TEXT, fieldFormatID INT);
        CREATE TABLE creators (creatorID INTEGER PRIMARY KEY, firstName TEXT,
            lastName TEXT, fieldMode INT);
        CREATE TABLE itemCreators (itemID INT, creatorID INT, creatorTypeID INT, orderIndex INT);
        CREATE TABLE collections (collectionID INTEGER PRIMARY KEY, collectionName TEXT,
            parentCollectionID INT, clientDateModified TIMESTAMP, libraryID INT, key TEXT,
            version INT, synced INT);
        CREATE TABLE collectionItems (collectionID INT, itemID INT, orderIndex INT);
        CREATE TABLE itemAttachments (itemID INTEGER PRIMARY KEY, parentItemID INT,
            linkMode INT, contentType TEXT, charsetID INT, path TEXT, syncState INT,
            storageModTime INT, storageHash TEXT, lastProcessedModificationTime INT,
            lastRead INT);
        CREATE TABLE itemNotes (itemID INTEGER PRIMARY KEY, parentItemID INT);
        CREATE TABLE itemTags (itemID INT, tagID INT, type INT);
        CREATE TABLE tags (tagID INTEGER PRIMARY KEY, name TEXT);

        INSERT INTO itemTypes VALUES (22, 'journalArticle', 0, 1);
        INSERT INTO itemTypes VALUES (11, 'conferencePaper', 0, 1);
        INSERT INTO itemTypes VALUES (31, 'preprint', 0, 1);

        INSERT INTO fields VALUES (1, 'title', 0);
        INSERT INTO fields VALUES (2, 'abstractNote', 0);
        INSERT INTO fields VALUES (6, 'date', 0);
        INSERT INTO fields VALUES (8, 'DOI', 0);
        INSERT INTO fields VALUES (10, 'url', 0);
        INSERT INTO fields VALUES (41, 'publicationTitle', 0);
        INSERT INTO fields VALUES (19, 'extra', 0);
        INSERT INTO fields VALUES (22, 'volume', 0);

        INSERT INTO creators VALUES (1, 'Jane', 'Smith', 0);
        INSERT INTO creators VALUES (2, 'Bob', 'Chen', 0);

        INSERT INTO items VALUES (1, 22, '2025-01-01', '2025-06-01', '2025-06-01', 1,
            'ABC123', 1, 1);
        INSERT INTO items VALUES (2, 31, '2025-03-01', '2025-06-02', '2025-06-02', 1,
            'DEF456', 1, 1);
        INSERT INTO items VALUES (3, 11, '2025-04-01', '2025-06-03', '2025-06-03', 1,
            'GHI789', 1, 1);

        INSERT INTO itemData VALUES (1, 1, 1);
        INSERT INTO itemData VALUES (1, 2, 2);
        INSERT INTO itemData VALUES (1, 6, 3);
        INSERT INTO itemData VALUES (1, 8, 4);
        INSERT INTO itemData VALUES (1, 41, 5);
        INSERT INTO itemData VALUES (2, 1, 6);
        INSERT INTO itemData VALUES (2, 8, 7);
        INSERT INTO itemData VALUES (3, 1, 8);
        INSERT INTO itemData VALUES (3, 6, 9);
        INSERT INTO itemData VALUES (3, 10, 10);

        INSERT INTO itemDataValues VALUES (1, 'Test Paper One');
        INSERT INTO itemDataValues VALUES (2, 'An abstract about testing.');
        INSERT INTO itemDataValues VALUES (3, '2025');
        INSERT INTO itemDataValues VALUES (4, '10.1234/test.1');
        INSERT INTO itemDataValues VALUES (5, 'Journal of Testing');
        INSERT INTO itemDataValues VALUES (6, 'Preprint Paper Two');
        INSERT INTO itemDataValues VALUES (7, '10.5678/arxiv.2');
        INSERT INTO itemDataValues VALUES (8, 'Conference Paper Three');
        INSERT INTO itemDataValues VALUES (9, '2024-06');
        INSERT INTO itemDataValues VALUES (10, 'https://example.org/paper3');

        INSERT INTO itemCreators VALUES (1, 1, 10, 0);
        INSERT INTO itemCreators VALUES (1, 2, 10, 1);
        INSERT INTO itemCreators VALUES (2, 1, 10, 0);

        INSERT INTO collections VALUES (1, 'AI', NULL, '2025-01-01', 1, 'COL_AI', 1, 1);
        INSERT INTO collections VALUES (2, 'NLP', 1, '2025-02-01', 1, 'COL_NLP', 1, 1);

        INSERT INTO collectionItems VALUES (1, 1, 0);
        INSERT INTO collectionItems VALUES (1, 2, 1);
        INSERT INTO collectionItems VALUES (2, 1, 0);

        -- attachment child items (type 3 = attachment)
        INSERT INTO items VALUES (10, 3, '2025-01-01', '2025-01-01', '2025-01-01', 1,
            'ATT_1', 1, 1);
        INSERT INTO items VALUES (11, 3, '2025-01-01', '2025-01-01', '2025-01-01', 1,
            'ATT_2', 1, 1);
        INSERT INTO itemAttachments VALUES (10, 1, 0, 'application/pdf', 0,
            'storage:test_one.pdf', 0, 0, '', 0, 0);
        INSERT INTO itemAttachments VALUES (11, 2, 0, 'application/pdf', 0,
            'storage:preprint_two.pdf', 0, 0, '', 0, 0);

        INSERT INTO tags VALUES (1, 'machine learning');
        INSERT INTO tags VALUES (2, 'testing');
        INSERT INTO itemTags VALUES (1, 1, 0);
        INSERT INTO itemTags VALUES (1, 2, 0);

        INSERT INTO itemNotes VALUES (20, 1);
        -- note child item (type 28 = note)
        INSERT INTO items VALUES (20, 28, '2025-01-01', '2025-01-01', '2025-01-01', 1,
            'NOTE_1', 1, 1);
        INSERT INTO itemData VALUES (20, 1, 20);
        INSERT INTO itemDataValues VALUES (20, 'This is a useful paper.');
    """)
    conn.commit()
    conn.close()

    # Create mock PDF files in attachment key directories
    (storage_dir / "ATT_1").mkdir(parents=True, exist_ok=True)
    (storage_dir / "ATT_1" / "test_one.pdf").touch()
    (storage_dir / "ATT_2").mkdir(parents=True, exist_ok=True)
    (storage_dir / "ATT_2" / "preprint_two.pdf").touch()


class ZoteroAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._root = Path(self._tmp.name)
        self._storage = self._root / "storage"
        _build_test_db(self._root / "zotero.sqlite", self._storage)
        self.adapter = ZoteroAdapter(data_dir=self._root)

    def tearDown(self) -> None:
        self.adapter.close()
        self._tmp.cleanup()

    def test_connect_and_close(self) -> None:
        self.assertFalse(self.adapter.connected)
        self.adapter.connect()
        self.assertTrue(self.adapter.connected)
        self.adapter.close()
        self.assertFalse(self.adapter.connected)

    def test_connection_is_read_only(self) -> None:
        self.adapter.connect()
        assert self.adapter._conn is not None
        with self.assertRaises(sqlite3.OperationalError):
            self.adapter._conn.execute("CREATE TABLE should_not_write (id INT)")

    def test_context_manager_closes_connection(self) -> None:
        with ZoteroAdapter(data_dir=self._root) as adapter:
            self.assertFalse(adapter.connected)
            self.assertIsNotNone(adapter.get_item("ABC123"))
            self.assertTrue(adapter.connected)
        self.assertFalse(adapter.connected)

    def test_missing_db_raises(self) -> None:
        bad = ZoteroAdapter(data_dir=Path("/no/such/path"))
        with self.assertRaises(FileNotFoundError):
            bad.connect()

    def test_list_collections(self) -> None:
        cols = self.adapter.list_collections()
        names = {c["name"] for c in cols}
        self.assertIn("AI", names)
        self.assertIn("NLP", names)

    def test_get_collection_items(self) -> None:
        items = self.adapter.get_collection_items("COL_AI")
        keys = {i.key for i in items}
        self.assertIn("ABC123", keys)
        self.assertIn("DEF456", keys)

    def test_get_item_returns_full_metadata(self) -> None:
        item = self.adapter.get_item("ABC123")
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.key, "ABC123")
        self.assertEqual(item.title, "Test Paper One")
        self.assertEqual(item.abstract, "An abstract about testing.")
        self.assertEqual(item.doi, "10.1234/test.1")
        self.assertEqual(item.venue, "Journal of Testing")
        self.assertEqual(item.year, 2025)
        self.assertEqual(item.item_type, "journalArticle")
        self.assertEqual(len(item.authors), 2)
        self.assertEqual(item.authors[0], {"first": "Jane", "last": "Smith"})
        self.assertEqual(item.authors[1], {"first": "Bob", "last": "Chen"})

    def test_get_item_returns_none_for_unknown_key(self) -> None:
        item = self.adapter.get_item("NONEXIST")
        self.assertIsNone(item)

    def test_find_by_title(self) -> None:
        item = self.adapter.find_by_title("Test Paper One")
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.key, "ABC123")

        item = self.adapter.find_by_title("No Such Title")
        self.assertIsNone(item)

    def test_find_by_doi(self) -> None:
        item = self.adapter.find_by_doi("10.1234/test.1")
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.key, "ABC123")

        item = self.adapter.find_by_doi("10.9999/nope")
        self.assertIsNone(item)

    def test_search_items(self) -> None:
        results = self.adapter.search_items("Paper")
        keys = {r.key for r in results}
        self.assertIn("ABC123", keys)
        self.assertIn("DEF456", keys)
        self.assertIn("GHI789", keys)

        results = self.adapter.search_items("Preprint")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].key, "DEF456")

    def test_list_items_filter_by_type(self) -> None:
        items = self.adapter.list_items(item_type="journalArticle")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].key, "ABC123")

        items = self.adapter.list_items(item_type="preprint")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].key, "DEF456")

    def test_attachments(self) -> None:
        item = self.adapter.get_item("ABC123")
        assert item is not None
        self.assertEqual(len(item.attachments), 1)
        att = item.attachments[0]
        self.assertEqual(att.content_type, "application/pdf")
        self.assertEqual(att.filename, "test_one.pdf")
        self.assertTrue(Path(att.path).exists())

    def test_tags(self) -> None:
        item = self.adapter.get_item("ABC123")
        assert item is not None
        self.assertIn("machine learning", item.tags)
        self.assertIn("testing", item.tags)

    def test_notes(self) -> None:
        item = self.adapter.get_item("ABC123")
        assert item is not None
        self.assertIn("This is a useful paper.", item.notes)

    def test_item_without_optional_fields(self) -> None:
        item = self.adapter.get_item("DEF456")
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.abstract, None)
        self.assertEqual(item.year, None)
        self.assertEqual(item.date, None)
        self.assertEqual(item.url, None)
        self.assertEqual(item.venue, None)

    def test_to_paper(self) -> None:
        item = self.adapter.get_item("ABC123")
        assert item is not None
        paper = self.adapter.to_paper(item)
        self.assertEqual(paper.title, "Test Paper One")
        self.assertEqual(paper.authors, ["Jane Smith", "Bob Chen"])
        self.assertEqual(paper.year, 2025)
        self.assertEqual(paper.doi, "10.1234/test.1")
        self.assertEqual(paper.venue, "Journal of Testing")
        self.assertEqual(paper.zotero_item_key, "ABC123")
        self.assertIn("test_one.pdf", paper.pdf_path or "")

    def test_conference_paper(self) -> None:
        item = self.adapter.get_item("GHI789")
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.title, "Conference Paper Three")
        self.assertEqual(item.year, 2024)
        self.assertEqual(item.url, "https://example.org/paper3")


if __name__ == "__main__":
    unittest.main()
