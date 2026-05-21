from __future__ import annotations

import re

from labcrew.schemas import PaperChunk


class TextChunker:
    def __init__(self, max_chars: int = 6000, overlap_chars: int = 400) -> None:
        if max_chars <= overlap_chars:
            raise ValueError("max_chars must be greater than overlap_chars.")
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    def split(self, text: str) -> list[PaperChunk]:
        normalized = self._normalize(text)
        if not normalized:
            return []

        sections = self._split_by_headings(normalized)
        chunks: list[PaperChunk] = []
        cursor = 0
        for heading, section_text in sections:
            section_start = normalized.find(section_text, cursor)
            if section_start == -1:
                section_start = cursor
            for part_index, part in enumerate(self._split_long_text(section_text)):
                start = normalized.find(part, section_start)
                if start == -1:
                    start = section_start
                end = start + len(part)
                chunk_id = f"chunk-{len(chunks) + 1:03d}"
                chunk_heading = heading if part_index == 0 else f"{heading} part {part_index + 1}"
                focus_area = self._focus_area(chunk_heading)
                priority = "high" if focus_area in {"method", "experiment"} else "normal"
                chunks.append(PaperChunk(chunk_id, chunk_heading, part, start, end, focus_area, priority))
                section_start = max(start, end - self.overlap_chars)
            cursor = section_start
        return chunks

    def _normalize(self, text: str) -> str:
        lines = [line.strip() for line in text.replace("\x00", "").splitlines()]
        return "\n".join(line for line in lines if line)

    def _split_by_headings(self, text: str) -> list[tuple[str, str]]:
        heading_pattern = re.compile(
            r"^(abstract|introduction|related work|background|method|methods|approach|experiments?|evaluation|results?|discussion|limitations?|conclusion|references)$",
            re.IGNORECASE | re.MULTILINE,
        )
        matches = list(heading_pattern.finditer(text))
        if not matches:
            return [("Full paper", text)]

        sections: list[tuple[str, str]] = []
        if matches[0].start() > 0:
            sections.append(("Front matter", text[: matches[0].start()].strip()))
        for index, match in enumerate(matches):
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            heading = match.group(0).strip()
            section_text = text[start:end].strip()
            if section_text:
                sections.append((heading, section_text))
        return [(heading, body) for heading, body in sections if body]

    def _split_long_text(self, text: str) -> list[str]:
        if len(text) <= self.max_chars:
            return [text]

        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + self.max_chars, len(text))
            if end < len(text):
                boundary = max(text.rfind("\n", start, end), text.rfind(". ", start, end))
                if boundary > start + self.max_chars // 2:
                    end = boundary + 1
            chunks.append(text[start:end].strip())
            if end >= len(text):
                break
            start = max(0, end - self.overlap_chars)
        return [chunk for chunk in chunks if chunk]

    def _focus_area(self, heading: str) -> str:
        normalized = heading.lower()
        if any(term in normalized for term in ["method", "approach"]):
            return "method"
        if any(term in normalized for term in ["experiment", "evaluation", "result"]):
            return "experiment"
        return "general"
