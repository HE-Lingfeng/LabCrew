from __future__ import annotations

from labcrew.agents.base import BaseAgent
from labcrew.agents.easter_egg import WeekendEasterEggAgent
from labcrew.agents.knowledge_card import KnowledgeCardAgent
from labcrew.agents.literature_manager import LiteratureManagerAgent
from labcrew.agents.paper_ingest import PaperIngestAgent
from labcrew.agents.paper_reader import PaperReaderAgent
from labcrew.agents.presentation import PresentationAgent
from labcrew.agents.proposal import ProposalAgent
from labcrew.agents.writing import WritingAgent
from labcrew.schemas import Task, TaskResult, TaskType


class LabCrewAgent(BaseAgent):
    name = "labcrew"

    def __init__(self) -> None:
        self.paper_ingest = PaperIngestAgent()
        self.paper_reader = PaperReaderAgent()
        self.proposal = ProposalAgent()
        self.knowledge_card = KnowledgeCardAgent()
        self.presentation = PresentationAgent()
        self.literature_manager = LiteratureManagerAgent()
        self.writing = WritingAgent()
        self.easter_egg = WeekendEasterEggAgent()

    def run(self, task: Task) -> TaskResult:
        if task.type == TaskType.READ_PAPER:
            paper, reading = self._read_paper(task)
            data = {"paper": self._paper_brief(paper), "card_report": reading["card_report"]}
            if "journal" in reading:
                data["journal"] = reading["journal"]
            if task.payload.get("deep_method"):
                data["method_deep_dive"] = self.paper_reader.run(
                    Task(TaskType.DEEP_READ_METHOD, {"paper": paper, "report": reading["report"]}, project=task.project)
                ).data
            return TaskResult(task.task_id, self.name, data)

        if task.type == TaskType.MAKE_CARD:
            paper, reading = self._read_paper(task)
            card = self.knowledge_card.run(
                Task(TaskType.MAKE_CARD, {"paper": paper, "summary": reading["report"]}, project=task.project)
            ).data
            data = {"paper": self._paper_brief(paper), "card_report": reading["card_report"], "card": card}
            if "journal" in reading:
                data["journal"] = reading["journal"]
            return TaskResult(task.task_id, self.name, data)

        if task.type == TaskType.MAKE_PRESENTATION:
            card = task.payload.get("card")
            if card is None:
                card = self.run(Task(TaskType.MAKE_CARD, task.payload, project=task.project)).data["card"]
            plan = self.presentation.run(Task(TaskType.MAKE_PRESENTATION, {"card": card}, project=task.project)).data
            return TaskResult(task.task_id, self.name, {"card": card, "slide_plan": plan})

        if task.type == TaskType.CRITIQUE_PAPER:
            paper, reading = self._read_paper(task) if "paper" not in task.payload else (task.payload["paper"], {})
            strategy_payload = {"paper": paper}
            if reading:
                strategy_payload["report"] = reading.get("report")
                strategy_payload["card_report"] = reading.get("card_report")
            proposal = self.proposal.run(Task(TaskType.CRITIQUE_PAPER, strategy_payload, project=task.project)).data
            return TaskResult(task.task_id, self.name, {"paper": self._paper_brief(paper), "proposal": proposal})

        if task.type == TaskType.DEEP_READ_METHOD:
            paper, reading = self._read_paper(task)
            deep_dive = self.paper_reader.run(
                Task(TaskType.DEEP_READ_METHOD, {"paper": paper, "report": reading["report"]}, project=task.project)
            ).data
            data = {"paper": self._paper_brief(paper), "card_report": reading["card_report"], "method_deep_dive": deep_dive}
            if "journal" in reading:
                data["journal"] = reading["journal"]
            return TaskResult(task.task_id, self.name, data)

        if task.type == TaskType.DESIGN_EXPERIMENT:
            proposal = self.proposal.run(task).data
            return TaskResult(task.task_id, self.name, proposal)

        if task.type == TaskType.WRITE:
            return self.writing.run(task)

        if task.type == TaskType.SYNC_LITERATURE:
            return self.literature_manager.run(task)

        if task.type == TaskType.WEEKEND_RECOMMENDATION:
            return self.easter_egg.run(task)

        raise ValueError(f"Unsupported task type: {task.type}")

    def _read_paper(self, task: Task) -> tuple[object, dict[str, object]]:
        paper = self.paper_ingest.run(task).data
        reader_payload = {
            "paper": paper,
            "save_journal": task.payload.get("save_journal", True),
            "journal_period": task.payload.get("journal_period", "weekly"),
        }
        reading = self.paper_reader.run(Task(TaskType.READ_PAPER, reader_payload, project=task.project)).data
        return paper, reading

    def _paper_brief(self, paper: object) -> dict[str, object]:
        return {
            "title": getattr(paper, "title", ""),
            "authors": getattr(paper, "authors", []),
            "year": getattr(paper, "year", None),
            "venue": getattr(paper, "venue", None),
            "abstract": self._brief_text(getattr(paper, "abstract", None)),
            "pdf_path": getattr(paper, "pdf_path", None),
            "source_url": getattr(paper, "source_url", None),
            "zotero_item_key": getattr(paper, "zotero_item_key", None),
            "ingestion": self._ingestion_brief(getattr(paper, "ingestion", None)),
            "figures": [
                {
                    "figure_id": figure.figure_id,
                    "page_number": figure.page_number,
                    "image_path": figure.image_path,
                    "reason": figure.reason,
                    "keywords": figure.keywords,
                    "bbox": figure.bbox,
                }
                for figure in getattr(paper, "figures", [])
            ],
        }

    def _brief_text(self, text: object, limit: int = 500) -> str | None:
        if text is None:
            return None
        compact = " ".join(str(text).split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 3].rstrip() + "..."

    def _ingestion_brief(self, ingestion: object) -> dict[str, object] | None:
        if ingestion is None:
            return None
        return {
            "source": getattr(ingestion, "source", ""),
            "source_type": getattr(ingestion, "source_type", ""),
            "text_char_count": getattr(ingestion, "text_char_count", 0),
            "figure_snapshot_count": getattr(ingestion, "figure_snapshot_count", 0),
            "artifact_dir": getattr(ingestion, "artifact_dir", None),
            "warnings": getattr(ingestion, "warnings", []),
        }
