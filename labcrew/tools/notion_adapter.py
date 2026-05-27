from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

from labcrew.env import load_local_env
from labcrew.schemas import LiteratureCard

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


@dataclass
class NotionPageRef:
    page_id: str
    url: str
    title: str


class NotionAdapter:
    """Real Notion integration via the public API."""

    def __init__(self, api_key: str | None = None, database_id: str | None = None) -> None:
        load_local_env()
        self._api_key = api_key or os.environ.get("NOTION_API_KEY", "")
        self._database_id = database_id or os.environ.get("NOTION_DATABASE_ID", "")
        if not self._api_key:
            raise ValueError("NOTION_API_KEY is required. Set via env var or constructor.")
        if not self._database_id:
            raise ValueError("NOTION_DATABASE_ID is required. Set via env var or constructor.")
        self._db_properties: dict[str, str] = self._fetch_db_properties()

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def create_literature_card(self, card: LiteratureCard, status: str = "Read") -> NotionPageRef:
        properties = self._card_to_properties(card, status)
        payload: dict[str, Any] = {"parent": {"database_id": self._database_id}, "properties": properties}
        children = self._card_to_children(card)
        if children:
            payload["children"] = children
        resp = self._post("/pages", json=payload)
        data = resp.json()
        page_id = data["id"]
        return NotionPageRef(page_id=page_id, url=data.get("url", ""), title=card.title)

    def update_card_status(self, page_id: str, status: str) -> None:
        if not self._property_matches("Status", "select"):
            raise ValueError("Notion database has no Status select property.")
        self._patch(f"/pages/{page_id}", json={"properties": {"Status": {"select": {"name": status}}}})

    def find_by_title(self, title: str) -> NotionPageRef | None:
        results = self._query_database(
            {"filter": {"property": self._title_property_name(), "title": {"equals": title}}}
        )
        if results:
            return self._page_ref_from_result(results[0])
        return None

    def find_by_zotero_key(self, key: str) -> NotionPageRef | None:
        if not self._property_matches("Zotero Key", "rich_text"):
            return None
        results = self._query_database({"filter": {"property": "Zotero Key", "rich_text": {"equals": key}}})
        if results:
            return self._page_ref_from_result(results[0])
        return None

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        }

    def _post(self, path: str, json: dict[str, Any]) -> httpx.Response:
        r = httpx.post(f"{NOTION_API_BASE}{path}", headers=self._headers(), json=json, timeout=30)
        r.raise_for_status()
        return r

    def _patch(self, path: str, json: dict[str, Any]) -> httpx.Response:
        r = httpx.patch(f"{NOTION_API_BASE}{path}", headers=self._headers(), json=json, timeout=30)
        r.raise_for_status()
        return r

    def _query_database(self, filter_body: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        body: dict[str, Any] = {}
        if filter_body:
            body["filter"] = filter_body
        resp = self._post(f"/databases/{self._database_id}/query", json=body)
        return resp.json().get("results", [])

    def _page_ref_from_result(self, result: dict[str, Any]) -> NotionPageRef:
        page_id = result["id"]
        title_prop = result.get("properties", {}).get(self._title_property_name(), {})
        title_text = ""
        title_list = title_prop.get("title", [])
        if title_list:
            title_text = title_list[0].get("plain_text", "")
        return NotionPageRef(page_id=page_id, url=result.get("url", ""), title=title_text)

    @staticmethod
    def _ts(value: str) -> list[dict[str, Any]]:
        """Shorthand for a rich_text block."""
        text = value or ""
        if not text:
            return []
        return [
            {"type": "text", "text": {"content": text[index : index + 2000]}}
            for index in range(0, len(text), 2000)
        ]

    def _fetch_db_properties(self) -> dict[str, str]:
        resp = httpx.get(
            f"{NOTION_API_BASE}/databases/{self._database_id}",
            headers=self._headers(),
            timeout=30,
        )
        resp.raise_for_status()
        return {name: prop["type"] for name, prop in resp.json().get("properties", {}).items()}

    def _card_to_properties(self, card: LiteratureCard, status: str) -> dict[str, Any]:
        rich_text_props = {
            "Authors": ", ".join(card.authors),
            "Venue": card.venue or "",
            "One Sentence Summary": card.one_sentence_summary,
            "Problem": card.problem,
            "Method": card.method,
            "Key Results": "\n".join(card.key_results),
            "Strengths": "\n".join(card.strengths),
            "Weaknesses": "\n".join(card.weaknesses),
            "Useful For": "\n".join(card.useful_for),
            "Open Questions": "\n".join(card.open_questions),
            "Zotero Key": card.zotero_item_key or "",
        }
        properties: dict[str, Any] = {self._title_property_name(): {"title": self._ts(card.title)}}
        for name, value in rich_text_props.items():
            if self._property_matches(name, "rich_text"):
                properties[name] = {"rich_text": self._ts(value)}
        if self._property_matches("Year", "number"):
            properties["Year"] = {"number": card.year}
        if self._property_matches("Status", "select"):
            properties["Status"] = {"select": {"name": status}}
        if self._property_matches("PDF Path", "url"):
            properties["PDF Path"] = {"url": card.source_pdf_path or None}
        return properties

    def _property_matches(self, name: str, expected_type: str) -> bool:
        return self._db_properties.get(name) == expected_type

    def _title_property_name(self) -> str:
        for name, property_type in self._db_properties.items():
            if property_type == "title":
                return name
        raise ValueError("Notion database must include a title property.")

    def _card_to_children(self, card: LiteratureCard) -> list[dict[str, Any]]:
        sections: list[tuple[str, str]] = [
            ("One Sentence Summary", card.one_sentence_summary),
            ("Problem", card.problem),
            ("Method", card.method),
            ("Key Results", "\n".join(card.key_results)),
            ("Strengths", "\n".join(card.strengths)),
            ("Weaknesses", "\n".join(card.weaknesses)),
            ("Useful For", "\n".join(card.useful_for)),
            ("Open Questions", "\n".join(card.open_questions)),
        ]
        children: list[dict[str, Any]] = []
        metadata = self._metadata_lines(card)
        if metadata:
            children.append(self._paragraph("\n".join(metadata)))
        for heading, content in sections:
            if not content:
                continue
            children.append(
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": self._ts(heading)},
                }
            )
            for paragraph in self._paragraphs(content):
                children.append(self._paragraph(paragraph))
        return children[:100]

    def _metadata_lines(self, card: LiteratureCard) -> list[str]:
        lines: list[str] = []
        if card.authors:
            lines.append(f"Authors: {', '.join(card.authors)}")
        if card.year:
            lines.append(f"Year: {card.year}")
        if card.venue:
            lines.append(f"Venue: {card.venue}")
        if card.zotero_item_key:
            lines.append(f"Zotero Key: {card.zotero_item_key}")
        if card.source_pdf_path:
            lines.append(f"PDF Path: {card.source_pdf_path}")
        return lines

    def _paragraph(self, content: str) -> dict[str, Any]:
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": self._ts(content)},
        }

    @staticmethod
    def _paragraphs(content: str) -> list[str]:
        paragraphs = [part.strip() for part in content.split("\n") if part.strip()]
        return paragraphs or [content]
