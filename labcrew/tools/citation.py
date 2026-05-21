from __future__ import annotations

from labcrew.schemas import Paper


class CitationFormatter:
    def format_short(self, paper: Paper) -> str:
        lead_author = paper.authors[0] if paper.authors else "Unknown"
        year = paper.year or "n.d."
        return f"{lead_author} et al., {year}"

