from .artifact import Artifact
from .experiment import ExperimentPlan, ResearchProposal
from .note import LiteratureCard
from .paper import Paper, PaperFigure, PaperIngestionMetadata
from .presentation import Slide, SlidePlan
from .reading import ChunkSummary, MethodDeepDive, PaperCardReport, PaperChunk, PaperJournalRecord, PaperReadingReport
from .task import Task, TaskResult, TaskType

__all__ = [
    "Artifact",
    "ExperimentPlan",
    "ResearchProposal",
    "LiteratureCard",
    "Paper",
    "PaperFigure",
    "PaperIngestionMetadata",
    "PaperChunk",
    "PaperReadingReport",
    "Slide",
    "SlidePlan",
    "Task",
    "TaskResult",
    "TaskType",
    "ChunkSummary",
    "MethodDeepDive",
    "PaperCardReport",
    "PaperJournalRecord",
]
