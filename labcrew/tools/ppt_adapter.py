from __future__ import annotations

from dataclasses import asdict
from typing import Any

from labcrew.schemas import SlidePlan


class PPTAdapter:
    def create_deck(self, slide_plan: SlidePlan, style_profile: str = "research", output_target: str = "local") -> dict[str, Any]:
        return {
            "provider": "mock",
            "status": "planned",
            "style_profile": style_profile,
            "output_target": output_target,
            "slide_plan": asdict(slide_plan),
        }

    def update_deck(self, deck_id: str, change_request: str) -> dict[str, str]:
        return {"deck_id": deck_id, "status": "mock", "change_request": change_request}

    def export_deck(self, deck_id: str, file_format: str = "pptx") -> dict[str, str]:
        return {"deck_id": deck_id, "format": file_format, "status": "mock"}

