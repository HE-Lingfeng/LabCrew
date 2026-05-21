from __future__ import annotations

from abc import ABC, abstractmethod

from labcrew.schemas import Task, TaskResult


class BaseAgent(ABC):
    name: str = "base"

    @abstractmethod
    def run(self, task: Task) -> TaskResult:
        """Run an agent task and return a structured result."""

