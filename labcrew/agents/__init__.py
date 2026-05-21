from .base import BaseAgent
from .coordinator import LabCrewAgent
from .easter_egg import WeekendEasterEggAgent
from .knowledge_card import KnowledgeCardAgent
from .literature_manager import LiteratureManagerAgent
from .paper_ingest import PaperIngestAgent
from .paper_reader import PaperReaderAgent
from .presentation import PresentationAgent
from .proposal import ProposalAgent
from .writing import WritingAgent

__all__ = [
    "BaseAgent",
    "KnowledgeCardAgent",
    "LabCrewAgent",
    "LiteratureManagerAgent",
    "PaperIngestAgent",
    "PaperReaderAgent",
    "PresentationAgent",
    "ProposalAgent",
    "WeekendEasterEggAgent",
    "WritingAgent",
]
