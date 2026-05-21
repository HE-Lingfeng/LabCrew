from __future__ import annotations

import tempfile
import unittest
import warnings
from datetime import date
from pathlib import Path

from labcrew.agents import PaperIngestAgent
from labcrew.schemas import ExperimentPlan, LiteratureCard, MethodDeepDive, Paper, PaperCardReport, PaperJournalRecord, PaperReadingReport, ResearchProposal, SlidePlan
from labcrew.schemas import Task, TaskType
from labcrew.tools import JournalStore, PDFParser, TextChunker
from labcrew.workflows import create_literature_card, deep_read_method, design_experiment, make_presentation, propose_research, read_paper


def build_minimal_pdf() -> bytes:
    content = (
        b"BT /F1 24 Tf 72 720 Td (PDF Research Paper Title) Tj "
        b"0 -40 Td (Abstract) Tj 0 -30 Td (This paper studies PDF reading.) Tj "
        b"0 -40 Td (Method Architecture) Tj 0 -30 Td (Figure 1 shows the model framework.) Tj ET"
    )
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream",
    ]
    body = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(body))
        body.extend(f"{index} 0 obj\n".encode("ascii"))
        body.extend(obj)
        body.extend(b"\nendobj\n")
    startxref = len(body)
    body.extend(b"xref\n0 6\n")
    body.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        body.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    body.extend(b"trailer\n<< /Root 1 0 R /Size 6 >>\n")
    body.extend(f"startxref\n{startxref}\n%%EOF\n".encode("ascii"))
    return bytes(body)


def build_pdf_with_architecture_figure(path: Path) -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        import fitz

    document = fitz.open()
    page = document.new_page(width=612, height=792)
    page.insert_text((72, 70), "Architecture Crop Paper", fontsize=20)
    page.insert_text((72, 120), "Method", fontsize=16)
    page.insert_text((72, 150), "We propose a modular neural architecture.", fontsize=11)
    figure_rect = fitz.Rect(95, 230, 500, 430)
    page.draw_rect(figure_rect)
    page.draw_rect(fitz.Rect(125, 275, 235, 335))
    page.draw_rect(fitz.Rect(365, 275, 475, 335))
    page.draw_line((235, 305), (365, 305))
    page.insert_text((145, 310), "Encoder", fontsize=10)
    page.insert_text((385, 310), "Decoder", fontsize=10)
    page.insert_text((95, 455), "Figure 1: Model architecture and pipeline overview.", fontsize=11)
    document.save(path)
    document.close()


class WorkflowTests(unittest.TestCase):
    def test_read_paper_from_text_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paper_path = Path(tmp_dir) / "paper.txt"
            paper_path.write_text("A Useful Research Paper\nAbstract\nThis paper studies useful systems.", encoding="utf-8")

            result = read_paper(str(paper_path))

        self.assertEqual(result.data["paper"]["title"], "A Useful Research Paper")
        self.assertNotIn("summary", result.data)
        self.assertIn("card_report", result.data)
        self.assertIsInstance(result.data["card_report"], PaperCardReport)
        self.assertNotIn("method_deep_dive", result.data)
        self.assertEqual(result.data["paper"]["ingestion"]["source_type"], "text_file")
        self.assertGreater(result.data["paper"]["ingestion"]["text_char_count"], 0)
        self.assertIsInstance(result.data["journal"], PaperJournalRecord)

    def test_pdf_parser_extracts_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = Path(tmp_dir) / "paper.pdf"
            pdf_path.write_bytes(build_minimal_pdf())

            text = PDFParser().read_text(pdf_path)

        self.assertIn("PDF Research Paper Title", text)
        self.assertIn("This paper studies PDF reading.", text)

    def test_pdf_parser_extracts_candidate_figure_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            pdf_path = tmp_path / "paper.pdf"
            output_dir = tmp_path / "figures"
            pdf_path.write_bytes(build_minimal_pdf())

            figures = PDFParser().extract_figure_snapshots(pdf_path, output_dir=output_dir)
            figure_exists = Path(figures[0].image_path).exists()

        self.assertGreaterEqual(len(figures), 1)
        self.assertIn("architecture", figures[0].keywords)
        self.assertTrue(figure_exists)

    def test_pdf_parser_crops_architecture_figure_when_caption_and_visuals_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            pdf_path = tmp_path / "architecture.pdf"
            output_dir = tmp_path / "figures"
            build_pdf_with_architecture_figure(pdf_path)

            figures = PDFParser().extract_figure_snapshots(pdf_path, output_dir=output_dir)
            figure_exists = Path(figures[0].image_path).exists()

        self.assertGreaterEqual(len(figures), 1)
        self.assertTrue(figures[0].figure_id.startswith("figure-crop"))
        self.assertIn("cropped architecture figure", figures[0].reason)
        self.assertIn("architecture", figures[0].keywords)
        self.assertIsNotNone(figures[0].bbox)
        self.assertLess(figures[0].bbox[2] - figures[0].bbox[0], 612)
        self.assertLess(figures[0].bbox[3] - figures[0].bbox[1], 792)
        self.assertTrue(figure_exists)

    def test_read_paper_from_pdf_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = Path(tmp_dir) / "paper.pdf"
            pdf_path.write_bytes(build_minimal_pdf())

            result = read_paper(str(pdf_path))

        self.assertEqual(result.data["paper"]["title"], "PDF Research Paper Title")
        self.assertIn("This paper studies PDF reading.", result.data["paper"]["abstract"])
        self.assertIsInstance(result.data["card_report"], PaperCardReport)
        self.assertGreaterEqual(len(result.data["paper"]["figures"]), 1)
        self.assertEqual(result.data["paper"]["ingestion"]["source_type"], "pdf")
        self.assertEqual(result.data["paper"]["ingestion"]["figure_snapshot_count"], len(result.data["paper"]["figures"]))
        self.assertIsInstance(result.data["journal"], PaperJournalRecord)

    def test_paper_ingest_can_disable_figure_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = Path(tmp_dir) / "paper.pdf"
            pdf_path.write_bytes(build_minimal_pdf())

            result = PaperIngestAgent().run(
                Task(TaskType.READ_PAPER, {"source": str(pdf_path), "extract_figures": False})
            )

        self.assertEqual(result.data.ingestion.source_type, "pdf")
        self.assertEqual(result.data.ingestion.figure_snapshot_count, 0)
        self.assertEqual(result.data.figures, [])

    def test_text_chunker_splits_by_headings(self) -> None:
        text = "\n".join(
            [
                "Chunking Paper",
                "Abstract",
                "This is the abstract.",
                "Introduction",
                "This is the motivation.",
                "Method",
                "This is the method.",
                "Experiments",
                "This is the evaluation.",
            ]
        )

        chunks = TextChunker(max_chars=120, overlap_chars=20).split(text)

        self.assertGreaterEqual(len(chunks), 4)
        self.assertEqual(chunks[0].heading, "Front matter")
        self.assertIn("Abstract", [chunk.heading for chunk in chunks])
        focus_by_heading = {chunk.heading: (chunk.focus_area, chunk.priority) for chunk in chunks}
        self.assertEqual(focus_by_heading["Method"], ("method", "high"))
        self.assertEqual(focus_by_heading["Experiments"], ("experiment", "high"))

    def test_journal_store_writes_weekly_card_and_upserts_same_paper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = JournalStore(root_dir=Path(tmp_dir), today=date(2026, 5, 20))
            paper = Paper(title="Journal Paper", pdf_path="/tmp/journal-paper.pdf")
            card = PaperCardReport(
                title="Journal Paper",
                one_sentence_summary="A compact summary.",
                problem="The research problem.",
                method_snapshot="The method.",
                experiment_snapshot="The experiments.",
                limitations="The limitations.",
                useful_for=["literature review"],
                follow_up_questions=["What should be tested next?"],
            )

            first = store.save_paper_card(paper, card, project="demo", period="weekly")
            second = store.save_paper_card(paper, card, project="demo", period="weekly")
            content = Path(first.path).read_text(encoding="utf-8")

        self.assertEqual(first.path, second.path)
        self.assertEqual(first.period_start, "2026-05-18")
        self.assertEqual(first.period_end, "2026-05-24")
        self.assertIn("# Paper Journal: demo", content)
        self.assertEqual(content.count("<!-- labcrew-card:"), 1)

    def test_journal_store_accepts_custom_day_period(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = JournalStore(root_dir=Path(tmp_dir), today=date(2026, 5, 20))
            paper = Paper(title="Custom Journal Paper")
            card = PaperCardReport(
                title="Custom Journal Paper",
                one_sentence_summary="A compact summary.",
                problem="The research problem.",
                method_snapshot="The method.",
                experiment_snapshot="The experiments.",
                limitations="The limitations.",
            )

            record = store.save_paper_card(paper, card, project="demo", period="14d")

        self.assertEqual(record.period, "14d")
        self.assertTrue(Path(record.path).name.startswith("paper-journal-14d-"))

    def test_reader_prioritizes_method_and_experiments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paper_path = Path(tmp_dir) / "paper.txt"
            paper_path.write_text(
                "\n".join(
                    [
                        "Priority Paper",
                        "Abstract",
                        "This paper studies prioritization.",
                        "Method",
                        "The method builds a retrieval planner with a verifier.",
                        "Experiments",
                        "Experiments compare against strong baselines on planning tasks.",
                    ]
                ),
                encoding="utf-8",
            )

            result = read_paper(str(paper_path))

        card_report = result.data["card_report"]
        self.assertIn("Method focus", card_report.method_snapshot)
        self.assertIn("retrieval planner", card_report.method_snapshot)
        self.assertIn("Experiment focus", card_report.experiment_snapshot)
        self.assertIn("strong baselines", card_report.experiment_snapshot)

    def test_deep_method_is_only_returned_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paper_path = Path(tmp_dir) / "paper.txt"
            paper_path.write_text(
                "\n".join(
                    [
                        "Deep Method Paper",
                        "Abstract",
                        "This paper studies method reading.",
                        "Method",
                        "The method first retrieves evidence, then plans, then verifies the result.",
                        "Experiments",
                        "Experiments evaluate the planner.",
                    ]
                ),
                encoding="utf-8",
            )

            default_result = read_paper(str(paper_path))
            deep_result = read_paper(str(paper_path), deep_method=True)
            command_result = deep_read_method(str(paper_path))

        self.assertNotIn("method_deep_dive", default_result.data)
        self.assertIsInstance(deep_result.data["method_deep_dive"], MethodDeepDive)
        self.assertIsInstance(command_result.data["method_deep_dive"], MethodDeepDive)
        self.assertIn("retrieves evidence", deep_result.data["method_deep_dive"].method_summary)

    def test_create_literature_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paper_path = Path(tmp_dir) / "paper.txt"
            paper_path.write_text("Card Paper\nThis method improves a research workflow.", encoding="utf-8")

            result = create_literature_card(str(paper_path))

        self.assertIsInstance(result.data["card"], LiteratureCard)
        self.assertEqual(result.data["card"].title, "Card Paper")
        self.assertIsInstance(result.data["card_report"], PaperCardReport)

    def test_make_presentation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paper_path = Path(tmp_dir) / "paper.txt"
            paper_path.write_text("Slides Paper\nThis paper is useful for group meetings.", encoding="utf-8")

            result = make_presentation(str(paper_path))

        self.assertIsInstance(result.data["slide_plan"], SlidePlan)
        self.assertEqual(len(result.data["slide_plan"].slides), 3)

    def test_design_experiment(self) -> None:
        result = design_experiment("Does retrieval improve agent planning?")

        self.assertIsInstance(result.data, ResearchProposal)
        self.assertIsInstance(result.data.experiment_plan, ExperimentPlan)
        self.assertEqual(result.data.validation_status, "seed_direction_needs_literature_check")
        self.assertIn("Does retrieval improve agent planning?", result.data.research_area)
        self.assertEqual(result.data.experiment_plan.implementation_status, "placeholder")

    def test_propose_research_from_paper_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paper_path = Path(tmp_dir) / "paper.txt"
            paper_path.write_text(
                "\n".join(
                    [
                        "Strategy Paper",
                        "Abstract",
                        "This paper studies research ideas.",
                        "Method",
                        "The method uses a planner.",
                        "Experiments",
                        "Experiments evaluate planning quality.",
                    ]
                ),
                encoding="utf-8",
            )

            result = propose_research(source=str(paper_path))

        self.assertIsInstance(result.data["proposal"], ResearchProposal)
        self.assertIsInstance(result.data["proposal"].experiment_plan, ExperimentPlan)
        self.assertEqual(result.data["proposal"].validation_status, "candidate_gap_from_read_paper")
        self.assertTrue(result.data["proposal"].unresolved_problem)
        self.assertTrue(result.data["proposal"].unexplored_direction)
        self.assertGreaterEqual(len(result.data["proposal"].evidence), 2)
        self.assertEqual(result.data["paper"]["title"], "Strategy Paper")


if __name__ == "__main__":
    unittest.main()
