from __future__ import annotations

from labcrew.schemas import TaskType


ROUTING_CASES = {
    "summarize this paper": TaskType.READ_PAPER,
    "make a literature card": TaskType.MAKE_CARD,
    "design an experiment": TaskType.DESIGN_EXPERIMENT,
    "make slides": TaskType.MAKE_PRESENTATION,
}

