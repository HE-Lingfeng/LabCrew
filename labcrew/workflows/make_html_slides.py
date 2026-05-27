from __future__ import annotations

from labcrew.agents import LabCrewAgent
from labcrew.config import load_config
from labcrew.schemas import SlidePlan, Task, TaskType
from labcrew.tools.html_slide_adapter import HtmlSlideAdapter


def make_html_slides(source: str, project: str = "general") -> dict:
    """Generate a self-contained HTML slide deck from a paper source.

    Returns html_path, slide_count, and source_title.
    """
    agent = LabCrewAgent()
    result = agent.run(Task(TaskType.MAKE_PRESENTATION, {"source": source}, project=project))
    slide_plan = result.data.get("slide_plan")
    if not isinstance(slide_plan, SlidePlan):
        raise ValueError("MAKE_PRESENTATION did not return a SlidePlan.")

    config = load_config()
    output_dir = config.artifacts_dir / "slides"
    adapter = HtmlSlideAdapter(output_dir=output_dir)
    return adapter.create_deck(slide_plan)
