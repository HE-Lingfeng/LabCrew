from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from labcrew.schemas import LiteratureCard


class CardStore:
    """Write LiteratureCards as local Markdown files with YAML frontmatter."""

    def __init__(self, root_dir: str | Path = "research/papers") -> None:
        self.root_dir = Path(root_dir)

    def create_literature_card(self, card: LiteratureCard, path: str | None = None) -> dict[str, Any]:
        output_dir = Path(path) if path else self.root_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        slug = self._slug(card.title)
        file_path = self._dedup_path(output_dir, slug)
        file_path.write_text(self._render(card), encoding="utf-8")
        return {
            "provider": "card_store",
            "status": "created",
            "path": str(file_path),
            "slug": slug,
            "title": card.title,
        }

    def update_notion_url(self, file_path: str | Path, notion_url: str) -> bool:
        fp = Path(file_path)
        if not fp.exists():
            return False
        content = fp.read_text(encoding="utf-8")
        updated = re.sub(
            r"^notion_url:.*$",
            f"notion_url: {self._yaml_str(notion_url)}",
            content,
            count=1,
            flags=re.MULTILINE,
        )
        if updated != content:
            fp.write_text(updated, encoding="utf-8")
            return True
        return False

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _render(self, card: LiteratureCard) -> str:
        return f"---\n{self._render_frontmatter(card)}---\n\n{self._render_body(card)}"

    def _render_frontmatter(self, card: LiteratureCard) -> str:
        lines = [f"title: {self._yaml_str(card.title)}"]
        if card.authors:
            author_items = "\n".join(f"  - {self._yaml_str(a)}" for a in card.authors)
            lines.append(f"authors:\n{author_items}")
        if card.year:
            lines.append(f"year: {card.year}")
        if card.venue:
            lines.append(f"venue: {self._yaml_str(card.venue)}")
        if card.tags:
            tag_items = "\n".join(f"  - {self._yaml_str(t)}" for t in card.tags)
            lines.append(f"tags:\n{tag_items}")
        if card.zotero_item_key:
            lines.append(f"zotero_key: {self._yaml_str(card.zotero_item_key)}")
        if card.source_pdf_path:
            lines.append(f"pdf_path: {self._yaml_str(card.source_pdf_path)}")
        notion_url = card.external_links.get("notion", "")
        lines.append(f"notion_url: {self._yaml_str(notion_url)}")
        return "\n".join(lines)

    def _render_body(self, card: LiteratureCard) -> str:
        parts: list[str] = [f"# {card.title}\n"]
        sections: list[tuple[str, str | list[str]]] = [
            ("One Sentence Summary", card.one_sentence_summary),
            ("Problem", card.problem),
            ("Method", card.method),
            ("Key Results", card.key_results),
            ("Strengths", card.strengths),
            ("Weaknesses", card.weaknesses),
            ("Useful For", card.useful_for),
            ("Open Questions", card.open_questions),
        ]
        for heading, content in sections:
            if not content:
                continue
            parts.append(f"## {heading}")
            if isinstance(content, list):
                parts.extend(f"- {item}" for item in content)
            else:
                parts.append(content)
            parts.append("")

        if card.external_links:
            parts.append("## Links")
            parts.extend(f"- [{label}]({url})" for label, url in card.external_links.items())
            parts.append("")

        return "\n".join(parts)

    @staticmethod
    def _slug(value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
        return slug or "paper"

    @staticmethod
    def _dedup_path(directory: Path, slug: str) -> Path:
        candidate = directory / f"{slug}.md"
        if not candidate.exists():
            return candidate
        i = 2
        while True:
            candidate = directory / f"{slug}-{i}.md"
            if not candidate.exists():
                return candidate
            i += 1

    @staticmethod
    def _yaml_str(value: str) -> str:
        if not value:
            return '""'
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
