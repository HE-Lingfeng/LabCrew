from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from labcrew.schemas import Paper


@dataclass
class ZoteroAttachment:
    key: str
    content_type: str
    path: str
    filename: str


@dataclass
class ZoteroItem:
    key: str
    item_type: str
    title: str
    authors: list[dict[str, str]] = field(default_factory=list)
    date: str | None = None
    year: int | None = None
    doi: str | None = None
    abstract: str | None = None
    url: str | None = None
    venue: str | None = None
    extra: str | None = None
    tags: list[str] = field(default_factory=list)
    collection_keys: list[str] = field(default_factory=list)
    attachments: list[ZoteroAttachment] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    date_added: str | None = None
    date_modified: str | None = None


_FIELD = {
    "title": 1,
    "abstract": 2,
    "date": 6,
    "doi": 8,
    "url": 10,
    "extra": 19,
    "volume": 22,
    "pages": 35,
    "publication": 41,
    "series": 45,
    "issue": 67,
    "journal_abbrev": 85,
}

_CREATOR_AUTHOR = 10


class ZoteroAdapter:
    """Read-only Zotero integration via direct SQLite access."""

    def __init__(self, data_dir: str | Path | None = None, library_id: int = 1) -> None:
        self._data_dir = Path(data_dir) if data_dir else Path.home() / "Zotero"
        self._library_id = library_id
        self._conn: sqlite3.Connection | None = None

    @property
    def db_path(self) -> Path:
        return self._data_dir / "zotero.sqlite"

    @property
    def storage_dir(self) -> Path:
        return self._data_dir / "storage"

    @property
    def connected(self) -> bool:
        return self._conn is not None

    def __enter__(self) -> ZoteroAdapter:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        if not self.db_path.exists():
            raise FileNotFoundError(f"Zotero database not found: {self.db_path}")
        self._conn = sqlite3.connect(f"{self.db_path.resolve().as_uri()}?mode=ro", uri=True)
        self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # collections
    # ------------------------------------------------------------------

    def list_collections(self) -> list[dict]:
        rows = self._query(
            "SELECT c.collectionID, c.collectionName, c.key, c.parentCollectionID "
            "FROM collections c WHERE c.libraryID = ? ORDER BY c.collectionName",
            (self._library_id,),
        )
        return [
            {
                "collection_id": r["collectionID"],
                "name": r["collectionName"],
                "key": r["key"],
                "parent_collection_id": r["parentCollectionID"],
            }
            for r in rows
        ]

    def get_collection_items(self, collection_key: str, limit: int = 100) -> list[ZoteroItem]:
        rows = self._query(
            "SELECT i.itemID FROM items i "
            "JOIN collectionItems ci ON i.itemID = ci.itemID "
            "JOIN collections c ON ci.collectionID = c.collectionID "
            "WHERE c.key = ? AND i.libraryID = ? "
            "ORDER BY ci.orderIndex LIMIT ?",
            (collection_key, self._library_id, limit),
        )
        return [self._build_item(r["itemID"]) for r in rows]

    # ------------------------------------------------------------------
    # items
    # ------------------------------------------------------------------

    def list_items(self, item_type: str | None = None, limit: int = 50) -> list[ZoteroItem]:
        if item_type:
            rows = self._query(
                "SELECT i.itemID FROM items i "
                "JOIN itemTypes t ON i.itemTypeID = t.itemTypeID "
                "WHERE i.libraryID = ? AND t.typeName = ? "
                "ORDER BY i.dateAdded DESC LIMIT ?",
                (self._library_id, item_type, limit),
            )
        else:
            rows = self._query(
                "SELECT i.itemID FROM items i WHERE i.libraryID = ? "
                "ORDER BY i.dateAdded DESC LIMIT ?",
                (self._library_id, limit),
            )
        return [self._build_item(r["itemID"]) for r in rows]

    def get_item(self, key: str) -> ZoteroItem | None:
        row = self._query_one(
            "SELECT itemID FROM items WHERE key = ? AND libraryID = ?",
            (key, self._library_id),
        )
        if row is None:
            return None
        return self._build_item(row["itemID"])

    def find_by_title(self, title: str) -> ZoteroItem | None:
        row = self._query_one(
            "SELECT id.itemID FROM itemData id "
            "JOIN itemDataValues idv ON id.valueID = idv.valueID "
            "JOIN items i ON id.itemID = i.itemID "
            "WHERE id.fieldID = ? AND idv.value = ? AND i.libraryID = ?",
            (_FIELD["title"], title, self._library_id),
        )
        if row is None:
            return None
        return self._build_item(row["itemID"])

    def find_by_doi(self, doi: str) -> ZoteroItem | None:
        row = self._query_one(
            "SELECT id.itemID FROM itemData id "
            "JOIN itemDataValues idv ON id.valueID = idv.valueID "
            "JOIN items i ON id.itemID = i.itemID "
            "WHERE id.fieldID = ? AND idv.value = ? AND i.libraryID = ?",
            (_FIELD["doi"], doi, self._library_id),
        )
        if row is None:
            return None
        return self._build_item(row["itemID"])

    def search_items(self, query: str, limit: int = 50) -> list[ZoteroItem]:
        pattern = f"%{query}%"
        rows = self._query(
            "SELECT DISTINCT id.itemID FROM itemData id "
            "JOIN itemDataValues idv ON id.valueID = idv.valueID "
            "JOIN items i ON id.itemID = i.itemID "
            "WHERE idv.value LIKE ? AND i.libraryID = ? "
            "LIMIT ?",
            (pattern, self._library_id, limit),
        )
        return [self._build_item(r["itemID"]) for r in rows]

    # ------------------------------------------------------------------
    # single-field helpers
    # ------------------------------------------------------------------

    def _field_value(self, item_id: int, name: str) -> str | None:
        row = self._query_one(
            "SELECT idv.value FROM itemData id "
            "JOIN itemDataValues idv ON id.valueID = idv.valueID "
            "WHERE id.itemID = ? AND id.fieldID = ?",
            (item_id, _FIELD[name]),
        )
        return row["value"] if row else None

    def _item_type(self, item_id: int) -> str:
        row = self._query_one(
            "SELECT t.typeName FROM items i "
            "JOIN itemTypes t ON i.itemTypeID = t.itemTypeID "
            "WHERE i.itemID = ?",
            (item_id,),
        )
        return row["typeName"] if row else ""

    def _item_creators(self, item_id: int) -> list[dict[str, str]]:
        rows = self._query(
            "SELECT cr.firstName, cr.lastName FROM itemCreators ic "
            "JOIN creators cr ON ic.creatorID = cr.creatorID "
            "WHERE ic.itemID = ? AND ic.creatorTypeID = ? "
            "ORDER BY ic.orderIndex",
            (item_id, _CREATOR_AUTHOR),
        )
        return [{"first": r["firstName"] or "", "last": r["lastName"] or ""} for r in rows]

    def _item_tags(self, item_id: int) -> list[str]:
        rows = self._query(
            "SELECT t.name FROM itemTags it "
            "JOIN tags t ON it.tagID = t.tagID "
            "WHERE it.itemID = ? ORDER BY t.name",
            (item_id,),
        )
        return [r["name"] for r in rows]

    def _item_collections(self, item_id: int) -> list[str]:
        rows = self._query(
            "SELECT c.key FROM collectionItems ci "
            "JOIN collections c ON ci.collectionID = c.collectionID "
            "WHERE ci.itemID = ?",
            (item_id,),
        )
        return [r["key"] for r in rows]

    def _item_attachments(self, item_id: int) -> list[ZoteroAttachment]:
        rows = self._query(
            "SELECT ia.itemID, ia.contentType, ia.path, i.key "
            "FROM itemAttachments ia "
            "JOIN items i ON ia.itemID = i.itemID "
            "WHERE ia.parentItemID = ?",
            (item_id,),
        )
        results = []
        for r in rows:
            filename = r["path"] or ""
            if filename.startswith("storage:"):
                filename = filename[len("storage:"):]
            results.append(ZoteroAttachment(
                key=r["key"],
                content_type=r["contentType"] or "",
                path=str(self.storage_dir / r["key"] / filename) if filename else "",
                filename=filename,
            ))
        return results

    def _item_notes(self, item_id: int) -> list[str]:
        rows = self._query(
            "SELECT idv.value FROM itemNotes inote "
            "JOIN itemData id ON inote.itemID = id.itemID "
            "JOIN itemDataValues idv ON id.valueID = idv.valueID "
            "JOIN items i ON inote.itemID = i.itemID "
            "WHERE inote.parentItemID = ? AND i.libraryID = ?",
            (item_id, self._library_id),
        )
        return [r["value"] for r in rows if r["value"]]

    def _item_meta(self, item_id: int) -> dict[str, str | None]:
        row = self._query_one(
            "SELECT key, dateAdded, dateModified FROM items WHERE itemID = ?",
            (item_id,),
        )
        if row is None:
            return {}
        return {
            "key": row["key"],
            "date_added": row["dateAdded"],
            "date_modified": row["dateModified"],
        }

    # ------------------------------------------------------------------
    # build
    # ------------------------------------------------------------------

    def _build_item(self, item_id: int) -> ZoteroItem:
        date_val = self._field_value(item_id, "date")
        year = None
        if date_val:
            try:
                year = int(date_val[:4])
            except ValueError:
                pass

        meta = self._item_meta(item_id)
        return ZoteroItem(
            key=meta.get("key", ""),
            item_type=self._item_type(item_id),
            title=self._field_value(item_id, "title") or "",
            authors=self._item_creators(item_id),
            date=date_val,
            year=year,
            doi=self._field_value(item_id, "doi"),
            abstract=self._field_value(item_id, "abstract"),
            url=self._field_value(item_id, "url"),
            venue=self._field_value(item_id, "publication"),
            extra=self._field_value(item_id, "extra"),
            tags=self._item_tags(item_id),
            collection_keys=self._item_collections(item_id),
            attachments=self._item_attachments(item_id),
            notes=self._item_notes(item_id),
            date_added=meta.get("date_added"),
            date_modified=meta.get("date_modified"),
        )

    # ------------------------------------------------------------------
    # conversion
    # ------------------------------------------------------------------

    def to_paper(self, item: ZoteroItem) -> Paper:
        pdf_path = None
        for a in item.attachments:
            if a.content_type == "application/pdf" and a.path:
                pdf_path = a.path
                break

        return Paper(
            title=item.title,
            authors=[f"{a['first']} {a['last']}".strip() for a in item.authors],
            year=item.year,
            venue=item.venue or self._field_value(self._item_id_by_key(item.key), "journal_abbrev"),
            abstract=item.abstract,
            doi=item.doi,
            pdf_path=pdf_path,
            source_url=item.url,
            zotero_item_key=item.key,
        )

    # ------------------------------------------------------------------
    # internal
    # ------------------------------------------------------------------

    def _item_id_by_key(self, key: str) -> int:
        row = self._query_one("SELECT itemID FROM items WHERE key = ?", (key,))
        if row is None:
            raise KeyError(f"No Zotero item with key: {key}")
        return row["itemID"]

    def _query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        if self._conn is None:
            self.connect()
        return self._conn.execute(sql, params).fetchall()

    def _query_one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        if self._conn is None:
            self.connect()
        return self._conn.execute(sql, params).fetchone()
