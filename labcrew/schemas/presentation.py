from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Slide:
    title: str
    purpose: str
    key_message: str
    bullets: list[str] = field(default_factory=list)
    visual_suggestion: str = ""
    speaker_notes: str = ""


@dataclass
class SlidePlan:
    title: str
    audience: str = "research group"
    duration_minutes: int = 10
    slides: list[Slide] = field(default_factory=list)
    source_papers: list[str] = field(default_factory=list)

