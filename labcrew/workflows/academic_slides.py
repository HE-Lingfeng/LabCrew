from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict
import json
from pathlib import Path
import re
import zipfile
from xml.etree import ElementTree

from labcrew.agents import KnowledgeCardAgent, PaperIngestAgent, PaperReaderAgent, PresentationAgent
from labcrew.config import load_config
from labcrew.schemas import (
    Paper,
    PaperReadingReport,
    SlideMaterial,
    SlideMaterialLibrary,
    SlidePlan,
    Task,
    TaskType,
)
from labcrew.tools.html_slide_adapter import HtmlSlideAdapter


def extract_slide_materials(
    source: str,
    project: str = "general",
    user_materials: Iterable[SlideMaterial | dict[str, object]] | None = None,
    material_paths: Iterable[str | Path] | None = None,
    profile: str = "ai-research",
    output_path: str | Path | None = None,
) -> SlideMaterialLibrary:
    """Extract a reviewable material library before drafting academic slides.

    If *output_path* is provided the library is saved as JSON at that path.
    """
    paper = PaperIngestAgent().run(Task(TaskType.READ_PAPER, {"source": source}, project=project)).data
    if not isinstance(paper, Paper):
        raise ValueError("Paper ingestion did not return a Paper.")

    reading = PaperReaderAgent().run(
        Task(TaskType.READ_PAPER, {"paper": paper, "save_journal": False}, project=project)
    ).data
    report = reading.get("report")
    if not isinstance(report, PaperReadingReport):
        raise ValueError("Paper reading did not return a PaperReadingReport.")

    materials = _materials_from_report(report)
    materials.extend(_materials_from_figures(paper))
    materials.extend(_normalize_user_materials(user_materials or []))
    materials.extend(_materials_from_paths(material_paths or []))

    library = SlideMaterialLibrary(
        title=paper.title or report.title,
        source=source,
        materials=materials,
        open_questions=[
            question
            for chunk in report.chunk_summaries
            for question in chunk.questions
        ],
        notes=[
            "Review this library before rendering slides.",
            "Promote only materials you can explain confidently into the final deck.",
            *_profile_notes(profile),
        ],
    )

    if output_path:
        save_material_library_json(library, Path(output_path))

    return library


def plan_academic_slides(
    source: str,
    project: str = "general",
    user_materials: Iterable[SlideMaterial | dict[str, object]] | None = None,
    material_paths: Iterable[str | Path] | None = None,
    audience: str = "research group",
    duration_minutes: int = 10,
    profile: str = "ai-research",
) -> dict[str, object]:
    """Create the material library and a first slide plan for user review.

    If *material_paths* includes a ``.json`` file created by an earlier
    ``--stage materials`` run, that library is loaded directly and the paper
    extraction step is skipped.
    """
    paths = list(material_paths or [])
    json_path, other_paths = _split_material_paths(paths)

    if json_path is not None:
        library = load_material_library_json(Path(json_path))
        if other_paths:
            extra = _materials_from_paths(other_paths)
            for m in extra:
                m.user_provided = True
            library.materials.extend(extra)
    else:
        paper = PaperIngestAgent().run(Task(TaskType.READ_PAPER, {"source": source}, project=project)).data
        if not isinstance(paper, Paper):
            raise ValueError("Paper ingestion did not return a Paper.")

        reader = PaperReaderAgent()
        reading = reader.run(Task(TaskType.READ_PAPER, {"paper": paper, "save_journal": False}, project=project)).data
        report = reading.get("report")
        if not isinstance(report, PaperReadingReport):
            raise ValueError("Paper reading did not return a PaperReadingReport.")

        library = SlideMaterialLibrary(
            title=paper.title or report.title,
            source=source,
            materials=[
                *_materials_from_report(report),
                *_materials_from_figures(paper),
                *_normalize_user_materials(user_materials or []),
                *_materials_from_paths(other_paths),
            ],
            open_questions=[
                question
                for chunk in report.chunk_summaries
                for question in chunk.questions
            ],
            notes=[
                "Treat this plan as a discussion draft.",
                "Replace weak generated materials with user-reviewed explanation, equations, figures, or examples.",
                *_profile_notes(profile),
            ],
        )

    # Card generation always runs (needs paper metadata).
    paper = PaperIngestAgent().run(Task(TaskType.READ_PAPER, {"source": source}, project=project)).data
    if not isinstance(paper, Paper):
        raise ValueError("Paper ingestion did not return a Paper.")

    reader = PaperReaderAgent()
    reading = reader.run(Task(TaskType.READ_PAPER, {"paper": paper, "save_journal": False}, project=project)).data
    report = reading.get("report")
    if not isinstance(report, PaperReadingReport):
        raise ValueError("Paper reading did not return a PaperReadingReport.")

    card = KnowledgeCardAgent().run(
        Task(TaskType.MAKE_CARD, {"paper": paper, "summary": report}, project=project)
    ).data
    plan = PresentationAgent().run(
        Task(
            TaskType.MAKE_PRESENTATION,
            {
                "card": card,
                "audience": audience,
                "duration_minutes": duration_minutes,
                "material_library": library,
                "profile": profile,
            },
            project=project,
        )
    ).data
    if not isinstance(plan, SlidePlan):
        raise ValueError("Presentation planning did not return a SlidePlan.")

    return {"material_library": library, "slide_plan": plan}


def make_academic_html_slides(
    source: str,
    project: str = "general",
    user_materials: Iterable[SlideMaterial | dict[str, object]] | None = None,
    material_paths: Iterable[str | Path] | None = None,
    audience: str = "research group",
    duration_minutes: int = 10,
    profile: str = "ai-research",
) -> dict[str, object]:
    """Render HTML only after producing the reviewable material library and plan."""
    planned = plan_academic_slides(
        source=source,
        project=project,
        user_materials=user_materials,
        material_paths=material_paths,
        audience=audience,
        duration_minutes=duration_minutes,
        profile=profile,
    )
    slide_plan = planned["slide_plan"]
    if not isinstance(slide_plan, SlidePlan):
        raise ValueError("Academic slide planning did not return a SlidePlan.")
    config = load_config()
    deck = HtmlSlideAdapter(output_dir=config.artifacts_dir / "slides").create_deck(slide_plan)
    return {**planned, "deck": deck}


def _materials_from_report(report: PaperReadingReport) -> list[SlideMaterial]:
    entries = [
        ("problem", "Research Problem", report.research_problem, "high", ["motivation"]),
        ("motivation", "Motivation", report.motivation, "high", ["motivation"]),
        ("method", "Core Method", report.method, "high", ["method"]),
        ("experiments", "Experiments", report.experiments, "normal", ["evaluation"]),
        ("limitations", "Limitations", report.limitations, "normal", ["discussion"]),
    ]
    materials = [
        SlideMaterial(
            material_id=f"paper-{kind}",
            kind=kind,
            title=title,
            content=content,
            priority=priority,
            tags=tags,
        )
        for kind, title, content, priority, tags in entries
        if content
    ]
    for index, takeaway in enumerate(report.key_takeaways, start=1):
        materials.append(
            SlideMaterial(
                material_id=f"paper-takeaway-{index}",
                kind="takeaway",
                title=f"Takeaway {index}",
                content=takeaway,
                priority="normal",
                tags=["summary"],
            )
        )
    return materials


def _profile_notes(profile: str) -> list[str]:
    if profile == "ai-research":
        return [
            "AI research deep-dive profile: emphasize motivation and method intuition.",
            "Experiments should stay brief unless there is a special trick, surprising result, or important evaluation caveat.",
            "Limitations are optional; expand them only when user-provided interpretation exists.",
        ]
    if profile == "ai-survey":
        return [
            "AI survey profile: emphasize method landscape, field timeline, and representative papers.",
            "Each paper should receive a compact role in the story instead of a full deep dive.",
            "Experiments are summarized only when they explain field progress or a key evaluation shift.",
        ]
    return []


def _materials_from_figures(paper: Paper) -> list[SlideMaterial]:
    return [
        SlideMaterial(
            material_id=f"figure-{index}",
            kind="figure",
            title=figure.figure_id,
            content=figure.image_path,
            source="paper_figure_snapshot",
            priority="normal",
            tags=figure.keywords,
        )
        for index, figure in enumerate(paper.figures, start=1)
    ]


def _normalize_user_materials(materials: Iterable[SlideMaterial | dict[str, object]]) -> list[SlideMaterial]:
    normalized: list[SlideMaterial] = []
    for index, material in enumerate(materials, start=1):
        if isinstance(material, SlideMaterial):
            material.user_provided = True
            normalized.append(material)
            continue
        normalized.append(
            SlideMaterial(
                material_id=str(material.get("material_id") or f"user-{index}"),
                kind=str(material.get("kind") or "note"),
                title=str(material.get("title") or f"User Material {index}"),
                content=str(material.get("content") or ""),
                source=str(material.get("source") or "user"),
                priority=str(material.get("priority") or "high"),
                tags=[str(tag) for tag in material.get("tags", [])],
                user_provided=True,
            )
        )
    return normalized


def _materials_from_paths(paths: Iterable[str | Path]) -> list[SlideMaterial]:
    materials: list[SlideMaterial] = []
    for raw_path in paths:
        path = Path(raw_path).expanduser()
        if path.suffix.lower() == ".json":
            continue  # handled at the library level by plan_academic_slides / make_academic_html_slides
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file():
                    materials.extend(_materials_from_file(child))
        elif path.is_file():
            materials.extend(_materials_from_file(path))
    return materials


def _materials_from_file(path: Path) -> list[SlideMaterial]:
    suffix = path.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        return [
            SlideMaterial(
                material_id=f"user-screenshot-{_slug(path.stem)}",
                kind="screenshot",
                title=path.stem,
                content=str(path.resolve()),
                source="user_image",
                priority="high",
                tags=["visual"],
                user_provided=True,
            )
        ]
    if suffix in {".md", ".markdown"}:
        return _materials_from_markdown(path)
    if suffix == ".docx":
        return _materials_from_docx(path)
    return []


def _materials_from_markdown(path: Path) -> list[SlideMaterial]:
    text = path.read_text(encoding="utf-8")
    sections = _split_markdown_sections(text)
    if not sections:
        sections = [(path.stem, text)]
    return [
        SlideMaterial(
            material_id=f"user-md-{_slug(path.stem)}-{index}",
            kind="note",
            title=title,
            content=content.strip(),
            source=str(path.resolve()),
            priority="high",
            tags=["user_note", "markdown"],
            user_provided=True,
        )
        for index, (title, content) in enumerate(sections, start=1)
        if content.strip()
    ]


def _materials_from_docx(path: Path) -> list[SlideMaterial]:
    text = _read_docx_text(path)
    paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
    if not paragraphs:
        return []
    return [
        SlideMaterial(
            material_id=f"user-docx-{_slug(path.stem)}",
            kind="note",
            title=path.stem,
            content="\n".join(paragraphs),
            source=str(path.resolve()),
            priority="high",
            tags=["user_note", "word"],
            user_provided=True,
        )
    ]


def _split_markdown_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = []
    current_title = ""
    current_lines: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^(#{1,3})\s+(.+)$", line)
        if match:
            if current_title or current_lines:
                sections.append((current_title or "Notes", current_lines))
            current_title = match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_title or current_lines:
        sections.append((current_title or "Notes", current_lines))
    return [(title, "\n".join(lines)) for title, lines in sections if "\n".join(lines).strip()]


def _read_docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        texts = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
        line = "".join(texts).strip()
        if line:
            paragraphs.append(line)
    return "\n".join(paragraphs)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "material"


def save_material_library_json(library: SlideMaterialLibrary, path: Path) -> Path:
    """Save *library* as a human-editable JSON file at *path*."""
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(library), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def load_material_library_json(path: Path) -> SlideMaterialLibrary:
    """Load a :class:`SlideMaterialLibrary` from a JSON file created by
    :func:`save_material_library_json`."""
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Materials JSON must be a dict, got {type(data).__name__}")
    return SlideMaterialLibrary.from_dict(data)


def _split_material_paths(
    paths: list[str | Path],
) -> tuple[str | None, list[str | Path]]:
    """Return ``(first_json_path, remaining_paths)`` from a list of paths."""
    json_path: str | None = None
    others: list[str | Path] = []
    for raw in paths:
        p = Path(raw)
        if json_path is None and p.suffix.lower() == ".json":
            json_path = str(raw)
        else:
            others.append(raw)
    return json_path, others
