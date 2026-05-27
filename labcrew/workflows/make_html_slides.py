from __future__ import annotations

from .academic_slides import make_academic_html_slides


def make_html_slides(source: str, project: str = "general") -> dict[str, object]:
    """Generate a self-contained HTML slide deck from a paper source.

    Delegates to the staged academic-slides pipeline (materials → plan → HTML).
    """
    return make_academic_html_slides(source=source, project=project)
