from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from labcrew.schemas import Slide, SlidePlan
from labcrew.tools.html_slide_adapter import HtmlSlideAdapter


class HtmlSlideAdapterTests(unittest.TestCase):
    def test_create_deck_writes_self_contained_html(self) -> None:
        plan = SlidePlan(
            title="A <Paper>",
            slides=[
                Slide(
                    title="Method",
                    purpose="Explain",
                    key_message="Use <strong> evidence",
                    bullets=["A & B"],
                    layout="figure-focus",
                    presenter_checklist=["Can explain the diagram"],
                    speaker_notes="Say less, show more.",
                )
            ],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = HtmlSlideAdapter(Path(tmp_dir)).create_deck(plan)
            html_path = Path(result["html_path"])
            content = html_path.read_text(encoding="utf-8")

        self.assertEqual(result["status"], "created")
        self.assertEqual(result["slide_count"], 1)
        self.assertTrue(str(result["file_url"]).startswith("file://"))
        self.assertIn("&lt;Paper&gt;", content)
        self.assertIn("layout-figure-focus", content)
        self.assertIn("Presenter check", content)
        self.assertIn("Use &lt;strong&gt; evidence", content)
        self.assertIn("A &amp; B", content)

    def test_empty_slide_plan_does_not_generate_crashing_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = HtmlSlideAdapter(Path(tmp_dir)).create_deck(SlidePlan(title="Empty"))
            content = Path(result["html_path"]).read_text(encoding="utf-8")

        self.assertIn("0 / 0", content)
        self.assertEqual(result["slide_count"], 0)


if __name__ == "__main__":
    unittest.main()
