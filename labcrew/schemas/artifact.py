from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Artifact:
    artifact_id: str
    type: str
    local_path: str | None = None
    external_target: str | None = None
    external_id: str | None = None
    source_task_id: str | None = None

