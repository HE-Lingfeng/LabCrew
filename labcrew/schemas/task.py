from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class TaskType(str, Enum):
    READ_PAPER = "read_paper"
    CRITIQUE_PAPER = "critique_paper"
    MAKE_CARD = "make_card"
    MAKE_PRESENTATION = "make_presentation"
    DEEP_READ_METHOD = "deep_read_method"
    DESIGN_EXPERIMENT = "design_experiment"
    WRITE = "write"
    SYNC_LITERATURE = "sync_literature"
    WEEKEND_RECOMMENDATION = "weekend_recommendation"
    UNKNOWN = "unknown"


@dataclass
class Task:
    type: TaskType
    payload: dict[str, Any]
    task_id: str = field(default_factory=lambda: str(uuid4()))
    project: str = "general"


@dataclass
class TaskResult:
    task_id: str
    agent_name: str
    data: Any
    notes: list[str] = field(default_factory=list)
