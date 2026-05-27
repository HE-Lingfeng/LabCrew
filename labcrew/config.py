from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from labcrew.env import load_local_env


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
    cards: IntegrationConfig = field(default_factory=IntegrationConfig)
    presentation: IntegrationConfig = field(default_factory=IntegrationConfig)

    @property
    def cards_dir(self) -> Path:
        return self.workspace / "cards"

    @property
    def artifacts_dir(self) -> Path:
        return self.workspace / "artifacts"


def default_config() -> LabCrewConfig:
    return LabCrewConfig()


def load_config() -> LabCrewConfig:
    load_local_env()
    notion_enabled = bool(os.environ.get("NOTION_API_KEY"))
    notion_config = IntegrationConfig(
        enabled=notion_enabled,
        provider="notion" if notion_enabled else "mock",
        settings={
            "api_key": os.environ.get("NOTION_API_KEY", ""),
            "database_id": os.environ.get("NOTION_DATABASE_ID", ""),
        },
    )

    cards_config = IntegrationConfig(
        enabled=True,
        provider="local",
        settings={
            "output_dir": os.environ.get("CARDS_OUTPUT_DIR", "research/papers"),
        },
    )

    return LabCrewConfig(notion=notion_config, cards=cards_config)
