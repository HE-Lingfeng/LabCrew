from __future__ import annotations

from pathlib import Path

from labcrew.agents.base import BaseAgent
from labcrew.schemas import Paper, PaperIngestionMetadata, Task, TaskResult
from labcrew.tools.pdf_parser import PDFParser


class PaperIngestAgent(BaseAgent):
    name = "paper_ingest"

    def __init__(self, parser: PDFParser | None = None, artifact_dir: Path | None = None) -> None:
        self.parser = parser or PDFParser()
        self.artifact_dir = artifact_dir or Path("data/artifacts/figures")

    def run(self, task: Task) -> TaskResult:
        source = task.payload.get("source") or task.payload.get("path")
        if not source:
            raise ValueError("PaperIngestAgent requires a source or path payload.")

        source_text = str(source)
        path = Path(source_text).expanduser()
        source_url = source_text if self._is_url(source_text) else None
        source_type = self._source_type(source_text, path)
        if source_url:
            raise ValueError("Remote URL ingestion is not implemented yet. Please provide a local PDF or text file.")

        text = self.parser.read_text(path)
        warnings: list[str] = []
        title = self.parser.infer_title(text, fallback=path.stem)
        figures = []
        output_dir = Path(str(task.payload.get("figure_output_dir") or task.payload.get("artifact_dir") or self.artifact_dir))
        should_extract_figures = bool(task.payload.get("extract_figures", True))
        if should_extract_figures and path.exists() and path.suffix.lower() == ".pdf":
            try:
                figures = self.parser.extract_figure_snapshots(
                    path,
                    output_dir=output_dir,
                    max_pages=int(task.payload.get("max_figure_pages", 4)),
                    zoom=float(task.payload.get("figure_zoom", 2.0)),
                )
            except Exception as exc:  # pragma: no cover - PyMuPDF failures are environment-specific.
                warnings.append(f"Figure snapshot extraction failed: {exc}")
        resolved_path = str(path.resolve()) if path.exists() else None
        ingestion = PaperIngestionMetadata(
            source=source_text,
            source_type=source_type,
            text_char_count=len(text),
            figure_snapshot_count=len(figures),
            artifact_dir=str(output_dir) if figures else None,
            warnings=warnings,
        )
        paper = Paper(
            title=title,
            abstract=self.parser.infer_abstract(text),
            sections={"raw_text": text},
            pdf_path=resolved_path if path.exists() and path.suffix.lower() == ".pdf" else None,
            source_url=source_url,
            figures=figures,
            ingestion=ingestion,
        )
        return TaskResult(task_id=task.task_id, agent_name=self.name, data=paper)

    def _is_url(self, source: str) -> bool:
        return source.startswith(("http://", "https://"))

    def _source_type(self, source: str, path: Path) -> str:
        if self._is_url(source):
            return "url"
        if path.exists() and path.suffix.lower() == ".pdf":
            return "pdf"
        if path.exists():
            return "text_file"
        return "inline_text"
