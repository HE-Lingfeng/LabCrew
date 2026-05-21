from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PaperChunk:
    chunk_id: str
    heading: str
    text: str
    start_char: int
    end_char: int
    focus_area: str = "general"
    priority: str = "normal"


@dataclass
class ChunkSummary:
    chunk_id: str
    heading: str
    summary: str
    focus_area: str = "general"
    priority: str = "normal"
    key_points: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)


@dataclass
class PaperReadingReport:
    title: str
    research_problem: str
    motivation: str
    method: str
    experiments: str
    limitations: str
    transferable_ideas: list[str] = field(default_factory=list)
    key_takeaways: list[str] = field(default_factory=list)
    chunk_summaries: list[ChunkSummary] = field(default_factory=list)


@dataclass
class PaperCardReport:
    title: str
    one_sentence_summary: str
    problem: str
    method_snapshot: str
    experiment_snapshot: str
    limitations: str
    useful_for: list[str] = field(default_factory=list)
    follow_up_questions: list[str] = field(default_factory=list)


@dataclass
class PaperJournalRecord:
    entry_id: str
    path: str
    period: str
    period_start: str
    period_end: str


@dataclass
class MethodDeepDive:
    title: str
    method_summary: str
    mechanism: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    inputs_outputs: list[str] = field(default_factory=list)
    implementation_notes: list[str] = field(default_factory=list)
    evidence_chunks: list[ChunkSummary] = field(default_factory=list)
