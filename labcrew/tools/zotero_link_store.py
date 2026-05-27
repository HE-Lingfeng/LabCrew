from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from labcrew.tools.card_store import CardStore
from labcrew.tools.zotero_adapter import ZoteroItem

SCHEMA = """\
CREATE TABLE IF NOT EXISTS zotero_links (
    zotero_key TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    notion_page_id TEXT,
    notion_url TEXT,
    reading_status TEXT NOT NULL DEFAULT 'unread',
    card_path TEXT,
    last_synced_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

VALID_STATUSES = {"unread", "reading", "read", "skipped"}
UPSERT_FIELDS = {
    "title",
    "notion_page_id",
    "notion_url",
    "reading_status",
    "card_path",
    "last_synced_at",
}


class ZoteroLinkStore:
    """Local SQLite store mapping zotero_key -> Notion page, reading status, and sync info.

    This is the single source of truth for per-paper tracking.
    """

    def __init__(self, db_path: str | Path = "data/zotero_links.db") -> None:
        self.db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(SCHEMA)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> ZoteroLinkStore:
        self.connect()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @property
    def connected(self) -> bool:
        return self._conn is not None

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def get(self, zotero_key: str) -> dict[str, Any] | None:
        row = self._query_one(
            "SELECT * FROM zotero_links WHERE zotero_key = ?",
            (zotero_key,),
        )
        return dict(row) if row else None

    def upsert(self, zotero_key: str, **fields: Any) -> None:
        self._validate_upsert(zotero_key, fields)
        now = _now()
        existing = self.get(zotero_key)
        if existing:
            updates = {k: v for k, v in fields.items() if v is not None}
            if not updates:
                return
            updates["updated_at"] = now
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [zotero_key]
            self._execute(
                f"UPDATE zotero_links SET {set_clause} WHERE zotero_key = ?",
                tuple(values),
            )
        else:
            row = {
                "zotero_key": zotero_key,
                "title": fields.get("title", ""),
                "notion_page_id": fields.get("notion_page_id"),
                "notion_url": fields.get("notion_url"),
                "reading_status": fields.get("reading_status", "unread"),
                "card_path": fields.get("card_path"),
                "last_synced_at": fields.get("last_synced_at"),
                "created_at": now,
                "updated_at": now,
            }
            self._execute(
                """INSERT INTO zotero_links
                   (zotero_key, title, notion_page_id, notion_url, reading_status, card_path, last_synced_at, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    row["zotero_key"], row["title"], row["notion_page_id"], row["notion_url"],
                    row["reading_status"], row["card_path"], row["last_synced_at"],
                    row["created_at"], row["updated_at"],
                ),
            )

    # ------------------------------------------------------------------
    # typed setters
    # ------------------------------------------------------------------

    def set_reading_status(self, zotero_key: str, status: str) -> None:
        self._validate_status(status)
        self.upsert(zotero_key, reading_status=status)

    def set_notion_link(self, zotero_key: str, page_id: str, url: str) -> None:
        self.upsert(
            zotero_key,
            notion_page_id=page_id,
            notion_url=url,
            last_synced_at=_now(),
        )

    def set_card_path(self, zotero_key: str, card_path: str) -> None:
        self.upsert(zotero_key, card_path=card_path)

    # ------------------------------------------------------------------
    # queries
    # ------------------------------------------------------------------

    def list_all(self) -> list[dict[str, Any]]:
        rows = self._query("SELECT * FROM zotero_links ORDER BY updated_at DESC")
        return [dict(r) for r in rows]

    def list_by_status(self, status: str) -> list[dict[str, Any]]:
        self._validate_status(status)
        rows = self._query(
            "SELECT * FROM zotero_links WHERE reading_status = ? ORDER BY updated_at DESC",
            (status,),
        )
        return [dict(r) for r in rows]

    def list_unsynced(self) -> list[dict[str, Any]]:
        rows = self._query(
            "SELECT * FROM zotero_links WHERE reading_status = 'read' AND notion_page_id IS NULL"
        )
        return [dict(r) for r in rows]

    def get_status_summary(self, keys: list[str]) -> dict[str, dict[str, Any]]:
        if not keys:
            return {}
        placeholders = ", ".join("?" for _ in keys)
        rows = self._query(
            f"SELECT * FROM zotero_links WHERE zotero_key IN ({placeholders})",
            tuple(keys),
        )
        return {r["zotero_key"]: dict(r) for r in rows}

    # ------------------------------------------------------------------
    # bulk operations
    # ------------------------------------------------------------------

    def seed_from_zotero_items(self, items: list[ZoteroItem]) -> int:
        """Insert rows for Zotero items not yet tracked. Returns count of newly inserted items."""
        existing = set()
        rows = self._query("SELECT zotero_key FROM zotero_links")
        existing = {r["zotero_key"] for r in rows}

        count = 0
        for item in items:
            if item.key in existing:
                continue
            self.upsert(
                item.key,
                title=item.title,
                reading_status="unread",
            )
            count += 1
        return count

    def rebuild_from_cards(self, card_store: CardStore) -> int:
        """Scan card files and rebuild zotero_key -> card_path / notion_url links.
        Returns count of updated rows.
        """
        count = 0
        for card_path in card_store.root_dir.glob("*.md"):
            fm = card_store._read_frontmatter(card_path)
            zk = fm.get("zotero_key", "").strip()
            if not zk:
                continue
            nu = fm.get("notion_url", "").strip()
            fields: dict[str, Any] = {"card_path": str(card_path)}
            if nu:
                fields["notion_url"] = nu
            self.upsert(zk, **fields)
            count += 1
        return count

    # ------------------------------------------------------------------
    # internal
    # ------------------------------------------------------------------

    def _execute(self, sql: str, params: tuple = ()) -> None:
        if self._conn is None:
            self.connect()
        self._conn.execute(sql, params)
        self._conn.commit()

    def _query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        if self._conn is None:
            self.connect()
        return self._conn.execute(sql, params).fetchall()

    def _query_one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        if self._conn is None:
            self.connect()
        return self._conn.execute(sql, params).fetchone()

    def _validate_upsert(self, zotero_key: str, fields: dict[str, Any]) -> None:
        if not zotero_key:
            raise ValueError("zotero_key is required")
        unknown = set(fields) - UPSERT_FIELDS
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"Unknown ZoteroLinkStore fields: {names}")
        status = fields.get("reading_status")
        if status is not None:
            self._validate_status(str(status))

    @staticmethod
    def _validate_status(status: str) -> None:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid reading_status: {status!r}. Must be one of {sorted(VALID_STATUSES)}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_notion_status(local_status: str) -> str:
    """Map ZoteroLinkStore reading_status values to Notion select values."""
    mapping = {
        "unread": "To Read",
        "reading": "Reading",
        "read": "Read",
        "skipped": "Skipped",
    }
    return mapping.get(local_status, local_status)
