from __future__ import annotations

import re

from labcrew.schemas import ChunkSummary, MethodDeepDive, PaperCardReport, PaperChunk, PaperReadingReport


class LLMAdapter:
    """Model adapter facade.

    The scaffold uses deterministic local summaries. A real model provider can
    later implement the same methods without changing PaperReaderAgent.
    """

    def summarize_paper_chunk(self, chunk: PaperChunk) -> ChunkSummary:
        compact = self._compact(chunk.text)
        sentences = self._sentences(compact)
        summary = self._summary_for_focus(sentences, compact, chunk.focus_area)
        key_points = self._key_points_for_focus(sentences, compact, chunk.focus_area)
        questions = [self._question_for_focus(chunk.heading, chunk.focus_area)]
        return ChunkSummary(
            chunk_id=chunk.chunk_id,
            heading=chunk.heading,
            summary=summary,
            focus_area=chunk.focus_area,
            priority=chunk.priority,
            key_points=key_points,
            questions=questions,
        )

    def synthesize_paper_report(self, title: str, chunk_summaries: list[ChunkSummary]) -> PaperReadingReport:
        joined = " ".join(summary.summary for summary in chunk_summaries)
        method = self._find_by_focus(chunk_summaries, "method") or self._find_by_heading(chunk_summaries, ["method", "methods", "approach"]) or self._fallback(joined)
        experiments = self._find_by_focus(chunk_summaries, "experiment") or self._find_by_heading(chunk_summaries, ["experiment", "experiments", "evaluation", "results"]) or self._fallback(joined)
        limitations = self._find_by_heading(chunk_summaries, ["limitation", "limitations", "discussion"]) or "Limitations need a model-backed critique pass."
        abstract = self._find_by_heading(chunk_summaries, ["abstract"]) or self._fallback(joined)
        introduction = self._find_by_heading(chunk_summaries, ["introduction", "front matter"]) or abstract
        return PaperReadingReport(
            title=title,
            research_problem=f"Based on the parsed chunks: {introduction}",
            motivation=f"The paper motivation appears to be: {abstract}",
            method=method,
            experiments=experiments,
            limitations=limitations,
            transferable_ideas=["Use the chunk summaries as evidence units for cards, slides, and critique."],
            key_takeaways=[
                "The paper was read through a chunked workflow instead of one full-context prompt.",
                "Method and experiment chunks are marked as high-priority evidence for synthesis.",
            ],
            chunk_summaries=chunk_summaries,
        )

    def create_card_report(self, report: PaperReadingReport) -> PaperCardReport:
        return PaperCardReport(
            title=report.title,
            one_sentence_summary=report.key_takeaways[0] if report.key_takeaways else self._fallback(report.research_problem),
            problem=self._brief(report.research_problem),
            method_snapshot=self._brief(report.method),
            experiment_snapshot=self._brief(report.experiments),
            limitations=self._brief(report.limitations),
            useful_for=report.transferable_ideas[:3],
            follow_up_questions=[
                question
                for summary in report.chunk_summaries
                for question in summary.questions
            ][:3],
        )

    def explain_method_deeply(self, title: str, report: PaperReadingReport) -> MethodDeepDive:
        method_chunks = [summary for summary in report.chunk_summaries if summary.focus_area == "method"]
        evidence = method_chunks or report.chunk_summaries[:2]
        points = [point for summary in evidence for point in summary.key_points]
        return MethodDeepDive(
            title=title,
            method_summary=report.method,
            mechanism=points[:4] or [report.method],
            assumptions=["Identify explicit assumptions from the method section with a model-backed pass."],
            inputs_outputs=["Extract inputs, outputs, and intermediate representations from method chunks."],
            implementation_notes=["Track architecture, training/inference procedure, hyperparameters, and reproducibility details."],
            evidence_chunks=evidence,
        )

    def _compact(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def _sentences(self, text: str) -> list[str]:
        return [item.strip() for item in re.split(r"(?<=[.!?])\s+", text) if item.strip()]

    def _find_by_heading(self, chunk_summaries: list[ChunkSummary], needles: list[str]) -> str | None:
        for summary in chunk_summaries:
            heading = summary.heading.lower()
            if any(needle in heading for needle in needles):
                return summary.summary
        return None

    def _find_by_focus(self, chunk_summaries: list[ChunkSummary], focus_area: str) -> str | None:
        focused = [summary for summary in chunk_summaries if summary.focus_area == focus_area]
        if not focused:
            return None
        high_priority = [summary for summary in focused if summary.priority == "high"]
        candidates = high_priority or focused
        return " ".join(summary.summary for summary in candidates)

    def _summary_for_focus(self, sentences: list[str], compact: str, focus_area: str) -> str:
        if not compact:
            return ""
        if focus_area == "method":
            return "Method focus: " + " ".join(sentences[:3] or [compact[:320]])
        if focus_area == "experiment":
            return "Experiment focus: " + " ".join(sentences[:3] or [compact[:320]])
        return sentences[0] if sentences else compact[:240]

    def _key_points_for_focus(self, sentences: list[str], compact: str, focus_area: str) -> list[str]:
        if not compact:
            return []
        limit = 5 if focus_area in {"method", "experiment"} else 3
        return sentences[:limit] or [compact[:320]]

    def _question_for_focus(self, heading: str, focus_area: str) -> str:
        if focus_area == "method":
            return "What are the core mechanism, assumptions, inputs, outputs, and implementation details of this method?"
        if focus_area == "experiment":
            return "What datasets, baselines, metrics, ablations, and result claims are supported by this experiment section?"
        return f"What role does the {heading} section play in the paper's argument?"

    def _fallback(self, text: str) -> str:
        return text[:280] if text else "No evidence was available in the parsed text."

    def _brief(self, text: str, limit: int = 360) -> str:
        compact = self._compact(text)
        if len(compact) <= limit:
            return compact
        return compact[: limit - 3].rstrip() + "..."
