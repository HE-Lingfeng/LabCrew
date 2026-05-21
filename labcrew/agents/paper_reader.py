from __future__ import annotations

from labcrew.agents.base import BaseAgent
from labcrew.schemas import Paper, PaperReadingReport, Task, TaskResult, TaskType
from labcrew.tools import JournalStore, LLMAdapter, TextChunker


class PaperReaderAgent(BaseAgent):
    name = "paper_reader"

    def __init__(
        self,
        chunker: TextChunker | None = None,
        llm: LLMAdapter | None = None,
        journal_store: JournalStore | None = None,
    ) -> None:
        self.chunker = chunker or TextChunker()
        self.llm = llm or LLMAdapter()
        self.journal_store = journal_store or JournalStore()

    def run(self, task: Task) -> TaskResult:
        paper = task.payload.get("paper")
        if not isinstance(paper, Paper):
            raise ValueError("PaperReaderAgent requires a Paper payload.")
        if task.type == TaskType.DEEP_READ_METHOD:
            report = task.payload.get("report")
            if not isinstance(report, PaperReadingReport):
                raise ValueError("PaperReaderAgent requires a PaperReadingReport payload for method deep dives.")
            deep_dive = self.llm.explain_method_deeply(paper.title, report)
            return TaskResult(task_id=task.task_id, agent_name=self.name, data=deep_dive)

        raw_text = paper.sections.get("raw_text", "")
        chunks = self.chunker.split(raw_text)
        chunk_summaries = [
            self.llm.summarize_paper_chunk(chunk)
            for chunk in chunks
        ]
        report = self.llm.synthesize_paper_report(paper.title, chunk_summaries)
        card_report = self.llm.create_card_report(report)
        journal_record = None
        if task.payload.get("save_journal", True):
            journal_record = self.journal_store.save_paper_card(
                paper=paper,
                card_report=card_report,
                project=task.project,
                period=str(task.payload.get("journal_period", "weekly")),
            )
        data = {"report": report, "card_report": card_report}
        if journal_record is not None:
            data["journal"] = journal_record
        return TaskResult(
            task_id=task.task_id,
            agent_name=self.name,
            data=data,
            notes=[f"Read paper through {len(chunks)} chunk(s)."],
        )
