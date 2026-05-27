from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SlideMaterial:
    material_id: str
    kind: str
    title: str
    content: str
    source: str = "paper"
    priority: str = "normal"
    tags: list[str] = field(default_factory=list)
    user_provided: bool = False


@dataclass
class SlideMaterialLibrary:
    title: str
    source: str = ""
    materials: list[SlideMaterial] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class Slide:
    title: str
    purpose: str
    key_message: str
    bullets: list[str] = field(default_factory=list)
    visual_suggestion: str = ""
    speaker_notes: str = ""
    layout: str = "title-and-bullets"
    material_ids: list[str] = field(default_factory=list)
    presenter_checklist: list[str] = field(default_factory=list)


@dataclass
class SlidePlan:
    title: str
    audience: str = "research group"
    duration_minutes: int = 10
    slides: list[Slide] = field(default_factory=list)
    source_papers: list[str] = field(default_factory=list)
