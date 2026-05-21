from __future__ import annotations

from labcrew.agents.base import BaseAgent
from labcrew.schemas import LiteratureCard, Paper, PaperReadingReport, Task, TaskResult


class KnowledgeCardAgent(BaseAgent):
    name = "knowledge_card"

    def run(self, task: Task) -> TaskResult:
        paper = task.payload.get("paper")
        summary = task.payload.get("summary")
        if not isinstance(paper, Paper):
            raise ValueError("KnowledgeCardAgent requires a Paper payload.")
        if not isinstance(summary, PaperReadingReport):
            raise ValueError("KnowledgeCardAgent requires a PaperReadingReport summary payload.")

        card = LiteratureCard(
            title=paper.title,
            authors=paper.authors,
            year=paper.year,
            venue=paper.venue,
            one_sentence_summary=summary.key_takeaways[0] if summary.key_takeaways else "",
            problem=summary.research_problem,
            method=summary.method,
            key_results=[summary.experiments],
            strengths=["Pending human or model-backed critique."],
            weaknesses=[summary.limitations],
            useful_for=summary.transferable_ideas,
            open_questions=[
                question
                for chunk_summary in summary.chunk_summaries
                for question in chunk_summary.questions
            ][:5],
            zotero_item_key=paper.zotero_item_key,
            source_pdf_path=paper.pdf_path,
        )
        return TaskResult(task_id=task.task_id, agent_name=self.name, data=card)
