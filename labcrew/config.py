from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class IntegrationConfig:
    enabled: bool = False
    provider: str = "mock"
    settings: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class LabCrewConfig:
    workspace: Path = Path("data")
    default_project: str = "general"
    zotero: IntegrationConfig = field(default_factory=IntegrationConfig)
    notion: IntegrationConfig = field(default_factory=IntegrationConfig)
    github: IntegrationConfig = field(default_factory=IntegrationConfig)
    presentation: IntegrationConfig = field(default_factory=IntegrationConfig)

    @property
    def cards_dir(self) -> Path:
        return self.workspace / "cards"

    @property
    def artifacts_dir(self) -> Path:
        return self.workspace / "artifacts"


def default_config() -> LabCrewConfig:
    return LabCrewConfig()

