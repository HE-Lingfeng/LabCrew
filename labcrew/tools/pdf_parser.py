from __future__ import annotations

from pathlib import Path
from typing import Callable
import warnings

from labcrew.schemas import PaperFigure

ARCHITECTURE_FIGURE_KEYWORDS = {
    "architecture": 6,
    "framework": 5,
    "model": 4,
    "pipeline": 4,
    "overview": 3,
    "method": 3,
    "methods": 3,
    "approach": 3,
    "network": 3,
    "module": 2,
    "encoder": 2,
    "decoder": 2,
}


class PDFParser:
    """Extract text from paper files.

    The parser keeps a small dependency surface for the rest of LabCrew: agents
    ask for text, while this facade decides which PDF backend is available.
    """

    def read_text(self, path: Path) -> str:
        if not path.exists():
            return str(path)
        if path.suffix.lower() == ".pdf":
            return self._read_pdf(path)
        return path.read_text(encoding="utf-8")

    def infer_title(self, text: str, fallback: str) -> str:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped and stripped.lower() not in {"abstract", "introduction"}:
                return stripped[:160]
        return fallback

    def infer_abstract(self, text: str) -> str | None:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        lowered_lines = [line.lower() for line in lines]
        try:
            index = lowered_lines.index("abstract")
        except ValueError:
            return None

        abstract_lines: list[str] = []
        stop_headings = {
            "1 introduction",
            "1. introduction",
            "introduction",
            "keywords",
            "background",
            "related work",
        }
        for line in lines[index + 1 :]:
            normalized = line.lower().rstrip(":")
            if normalized in stop_headings:
                break
            abstract_lines.append(line)

        abstract = " ".join(abstract_lines).strip()
        return abstract or None

    def extract_figure_snapshots(
        self,
        path: Path,
        output_dir: Path,
        max_pages: int = 4,
        zoom: float = 2.0,
    ) -> list[PaperFigure]:
        if not path.exists() or path.suffix.lower() != ".pdf":
            return []

        fitz = self._import_fitz()

        output_dir.mkdir(parents=True, exist_ok=True)
        document = fitz.open(path)
        try:
            candidates = self._rank_visual_candidate_pages(document)
            figures: list[PaperFigure] = []
            crop_candidates: list[dict[str, object]] = []
            for candidate in candidates[: max(max_pages * 2, max_pages)]:
                page = document[candidate["page_index"]]
                crop_candidates.extend(self._find_architecture_figure_crops(page, candidate))

            for rank, crop in enumerate(crop_candidates[:max_pages], start=1):
                page = document[crop["page_index"]]
                rect = crop["bbox"]
                matrix = fitz.Matrix(zoom, zoom)
                pixmap = page.get_pixmap(matrix=matrix, clip=rect, alpha=False)
                image_path = output_dir / f"{path.stem}-figure-crop-p{crop['page_number']}-{rank:02d}.png"
                pixmap.save(image_path)
                figures.append(
                    PaperFigure(
                        figure_id=f"figure-crop-{rank:02d}",
                        page_number=crop["page_number"],
                        image_path=str(image_path),
                        reason=str(crop["reason"]),
                        keywords=list(crop["keywords"]),
                        bbox=self._rect_tuple(rect),
                    )
                )

            if figures:
                return figures

            for rank, candidate in enumerate(candidates[:max_pages], start=1):
                page = document[candidate["page_index"]]
                matrix = fitz.Matrix(zoom, zoom)
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                image_path = output_dir / f"{path.stem}-figure-candidate-p{candidate['page_number']}.png"
                pixmap.save(image_path)
                figures.append(
                    PaperFigure(
                        figure_id=f"figure-candidate-{rank:02d}",
                        page_number=candidate["page_number"],
                        image_path=str(image_path),
                        reason=str(candidate["reason"]),
                        keywords=list(candidate["keywords"]),
                        bbox=self._rect_tuple(page.rect),
                    )
                )
            return figures
        finally:
            document.close()

    def _read_pdf(self, path: Path) -> str:
        errors: list[str] = []
        extractors: list[tuple[str, Callable[[Path], str]]] = [
            ("pypdf", self._read_pdf_with_pypdf),
            ("pdfminer", self._read_pdf_with_pdfminer),
            ("pymupdf", self._read_pdf_with_pymupdf),
        ]

        for name, extractor in extractors:
            try:
                text = self._normalize_text(extractor(path))
            except Exception as exc:  # pragma: no cover - backend-specific failures vary.
                errors.append(f"{name}: {exc}")
                continue
            if text:
                return text
            errors.append(f"{name}: extracted no text")

        message = f"Unable to extract text from PDF: {path}"
        if errors:
            message = f"{message}. Tried backends: {'; '.join(errors)}"
        raise ValueError(message)

    def _read_pdf_with_pypdf(self, path: Path) -> str:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)

    def _read_pdf_with_pdfminer(self, path: Path) -> str:
        from pdfminer.high_level import extract_text

        return extract_text(str(path))

    def _read_pdf_with_pymupdf(self, path: Path) -> str:
        fitz = self._import_fitz()

        document = fitz.open(path)
        try:
            return "\n\n".join(page.get_text("text") for page in document)
        finally:
            document.close()

    def _normalize_text(self, text: str) -> str:
        lines = [line.rstrip() for line in text.replace("\x00", "").splitlines()]
        normalized = "\n".join(line for line in lines if line.strip())
        return normalized.strip()

    def _import_fitz(self) -> object:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            import fitz

        return fitz

    def _rank_visual_candidate_pages(self, document: object) -> list[dict[str, object]]:
        focus_keywords = {
            "method": 5,
            "methods": 5,
            "approach": 5,
            "architecture": 6,
            "framework": 5,
            "model": 4,
            "pipeline": 4,
            "overview": 3,
            "figure": 2,
            "fig.": 2,
            "experiment": 3,
            "experiments": 3,
            "evaluation": 3,
        }
        candidates: list[dict[str, object]] = []
        for page_index in range(len(document)):  # type: ignore[arg-type]
            page = document[page_index]  # type: ignore[index]
            text = page.get_text("text").lower()
            image_count = len(page.get_images(full=True))
            drawing_count = len(page.get_drawings())
            matched = [keyword for keyword in focus_keywords if keyword in text]
            score = sum(focus_keywords[keyword] for keyword in matched)
            score += min(image_count, 4) * 3
            score += min(drawing_count, 8)
            if score <= 0:
                continue
            reason = "candidate architecture/method/experiment page"
            if image_count or drawing_count:
                reason = f"{reason}; visual elements detected"
            candidates.append(
                {
                    "page_index": page_index,
                    "page_number": page_index + 1,
                    "score": score,
                    "reason": reason,
                    "keywords": matched,
                }
            )
        return sorted(candidates, key=lambda item: (-int(item["score"]), int(item["page_number"])))

    def _find_architecture_figure_crops(self, page: object, page_candidate: dict[str, object]) -> list[dict[str, object]]:
        fitz = self._import_fitz()

        page_rect = page.rect
        visual_rects = self._visual_rects(page)
        if not visual_rects:
            return []

        caption_blocks = self._caption_blocks(page)
        crops: list[dict[str, object]] = []
        for caption in caption_blocks:
            caption_rect = caption["rect"]
            nearby_visuals = self._nearby_visual_rects(visual_rects, caption_rect, page_rect)
            if not nearby_visuals:
                continue
            crop_rect = self._union_rects(fitz, nearby_visuals + [caption_rect])
            crop_rect = self._expand_rect(fitz, crop_rect, page_rect, margin=18)
            if not self._is_useful_crop(crop_rect, page_rect):
                continue
            crops.append(
                {
                    "page_index": page_candidate["page_index"],
                    "page_number": page_candidate["page_number"],
                    "bbox": crop_rect,
                    "score": int(page_candidate["score"]) + 20 + len(nearby_visuals),
                    "reason": "cropped architecture figure from caption and nearby visual elements",
                    "keywords": sorted(set(page_candidate["keywords"]) | set(caption["keywords"])),
                }
            )

        if crops:
            return sorted(crops, key=lambda item: (-int(item["score"]), self._rect_area(item["bbox"])))

        page_text = page.get_text("text").lower()
        matched = self._matched_architecture_keywords(page_text)
        if not matched:
            return []
        largest = max(visual_rects, key=self._rect_area)
        crop_rect = self._expand_rect(fitz, largest, page_rect, margin=24)
        if not self._is_useful_crop(crop_rect, page_rect):
            return []
        return [
            {
                "page_index": page_candidate["page_index"],
                "page_number": page_candidate["page_number"],
                "bbox": crop_rect,
                "score": int(page_candidate["score"]) + 8,
                "reason": "cropped likely architecture figure from largest visual element on a method page",
                "keywords": sorted(set(page_candidate["keywords"]) | set(matched)),
            }
        ]

    def _visual_rects(self, page: object) -> list[object]:
        fitz = self._import_fitz()

        rects: list[object] = []
        seen: set[tuple[int, int, int, int]] = set()
        for image in page.get_images(full=True):
            for rect in page.get_image_rects(image[0]):
                if self._rect_area(rect) >= 900:
                    key = self._rect_key(rect)
                    if key not in seen:
                        seen.add(key)
                        rects.append(rect)
        for drawing in page.get_drawings():
            rect = drawing.get("rect")
            if rect is not None and self._rect_area(rect) >= 900:
                key = self._rect_key(rect)
                if key not in seen:
                    seen.add(key)
                    rects.append(fitz.Rect(rect))
        return rects

    def _caption_blocks(self, page: object) -> list[dict[str, object]]:
        fitz = self._import_fitz()

        captions: list[dict[str, object]] = []
        for block in page.get_text("blocks"):
            if len(block) < 5:
                continue
            text = str(block[4]).strip()
            lowered = text.lower()
            if "fig." not in lowered and "figure" not in lowered:
                continue
            matched = self._matched_architecture_keywords(lowered)
            if not matched:
                continue
            captions.append(
                {
                    "rect": fitz.Rect(block[:4]),
                    "text": text,
                    "keywords": matched,
                }
            )
        return captions

    def _nearby_visual_rects(self, visual_rects: list[object], caption_rect: object, page_rect: object) -> list[object]:
        candidates: list[tuple[float, object]] = []
        page_height = float(page_rect.height)
        for rect in visual_rects:
            vertical_gap = min(abs(float(caption_rect.y0) - float(rect.y1)), abs(float(rect.y0) - float(caption_rect.y1)))
            horizontal_overlap = max(0.0, min(float(rect.x1), float(caption_rect.x1)) - max(float(rect.x0), float(caption_rect.x0)))
            min_width = max(1.0, min(float(rect.width), float(caption_rect.width)))
            overlap_ratio = horizontal_overlap / min_width
            if vertical_gap <= page_height * 0.35 and overlap_ratio >= 0.15:
                candidates.append((vertical_gap, rect))
        if candidates:
            return [rect for _, rect in sorted(candidates, key=lambda item: item[0])[:3]]

        caption_center_y = (float(caption_rect.y0) + float(caption_rect.y1)) / 2
        nearest = sorted(
            visual_rects,
            key=lambda rect: abs(((float(rect.y0) + float(rect.y1)) / 2) - caption_center_y),
        )
        return nearest[:1]

    def _matched_architecture_keywords(self, text: str) -> list[str]:
        return [keyword for keyword in ARCHITECTURE_FIGURE_KEYWORDS if keyword in text]

    def _union_rects(self, fitz: object, rects: list[object]) -> object:
        union = fitz.Rect(rects[0])
        for rect in rects[1:]:
            union |= rect
        return union

    def _expand_rect(self, fitz: object, rect: object, page_rect: object, margin: float) -> object:
        expanded = fitz.Rect(rect)
        expanded.x0 = max(float(page_rect.x0), float(expanded.x0) - margin)
        expanded.y0 = max(float(page_rect.y0), float(expanded.y0) - margin)
        expanded.x1 = min(float(page_rect.x1), float(expanded.x1) + margin)
        expanded.y1 = min(float(page_rect.y1), float(expanded.y1) + margin)
        return expanded

    def _is_useful_crop(self, rect: object, page_rect: object) -> bool:
        page_area = self._rect_area(page_rect)
        rect_area = self._rect_area(rect)
        if rect_area < 2500:
            return False
        return rect_area <= page_area * 0.9

    def _rect_area(self, rect: object) -> float:
        return max(0.0, float(rect.width)) * max(0.0, float(rect.height))

    def _rect_key(self, rect: object) -> tuple[int, int, int, int]:
        return (round(float(rect.x0)), round(float(rect.y0)), round(float(rect.x1)), round(float(rect.y1)))

    def _rect_tuple(self, rect: object) -> tuple[float, float, float, float]:
        return (round(float(rect.x0), 2), round(float(rect.y0), 2), round(float(rect.x1), 2), round(float(rect.y1), 2))
