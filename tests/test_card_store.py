from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from labcrew.schemas import LiteratureCard
from labcrew.tools.card_store import CardStore


class CardStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.adapter = CardStore(root_dir=self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    # ------------------------------------------------------------------
    # create_literature_card
    # ------------------------------------------------------------------

    def test_creates_markdown_file_with_frontmatter(self) -> None:
        card = LiteratureCard(
            title="Flow-GRPO: Training Flow Matching Models via Online RL",
            authors=["Author One", "Author Two"],
            year=2025,
            venue="NeurIPS",
            one_sentence_summary="A novel online RL approach for flow matching.",
            problem="Training flow matching models is slow.",
            method="They use online RL with GRPO.",
            key_results=["Better sample quality", "Faster convergence"],
            zotero_item_key="ABC123",
            source_pdf_path="/papers/flow.pdf",
            external_links={"notion": "https://notion.so/page"},
        )

        result = self.adapter.create_literature_card(card)

        self.assertEqual(result["status"], "created")
        self.assertIn("flow-grpo-training-flow-matching-models-via-online-rl", result["slug"])
        file_path = Path(result["path"])
        self.assertTrue(file_path.exists())

        content = file_path.read_text("utf-8")
        self.assertIn("---", content)
        self.assertIn("title:", content)
        self.assertIn("Flow-GRPO", content)
        self.assertIn("Author One", content)
        self.assertIn("year: 2025", content)
        self.assertIn("zotero_key:", content)
        self.assertIn("ABC123", content)
        self.assertIn("notion_url: ", content)
        self.assertIn("pdf_path: ", content)
        self.assertIn("# Flow-GRPO", content)
        self.assertIn("## One Sentence Summary", content)
        self.assertIn("online RL", content)
        self.assertIn("## Key Results", content)
        self.assertIn("- Better sample quality", content)
        self.assertIn("## Links", content)
        self.assertIn("[notion]", content)

    def test_minimal_card(self) -> None:
        card = LiteratureCard(title="Minimal Paper")
        result = self.adapter.create_literature_card(card)

        file_path = Path(result["path"])
        content = file_path.read_text("utf-8")
        self.assertIn("title:", content)
        self.assertIn("Minimal Paper", content)
        self.assertIn("notion_url: ", content)

    def test_empty_title_uses_paper_slug(self) -> None:
        card = LiteratureCard(title="")
        result = self.adapter.create_literature_card(card)
        self.assertIn("paper", result["slug"])

    # ------------------------------------------------------------------
    # slug
    # ------------------------------------------------------------------

    def test_slug_lowercases_and_replaces_special_chars(self) -> None:
        result = CardStore._slug("Flow-GRPO: Training!!! Models?")
        self.assertEqual(result, "flow-grpo-training-models")

    def test_slug_strips_leading_trailing_dashes(self) -> None:
        result = CardStore._slug("---Hello World---")
        self.assertEqual(result, "hello-world")

    def test_slug_empty_string(self) -> None:
        result = CardStore._slug("")
        self.assertEqual(result, "paper")

    # ------------------------------------------------------------------
    # dedup
    # ------------------------------------------------------------------

    def test_dedup_returns_slug_when_no_conflict(self) -> None:
        path = CardStore._dedup_path(self.root, "my-paper")
        self.assertEqual(path, self.root / "my-paper.md")

    def test_dedup_adds_suffix_when_file_exists(self) -> None:
        (self.root / "my-paper.md").write_text("existing", encoding="utf-8")
        path = CardStore._dedup_path(self.root, "my-paper")
        self.assertEqual(path, self.root / "my-paper-2.md")

    def test_dedup_increments_suffix(self) -> None:
        (self.root / "my-paper.md").write_text("1", encoding="utf-8")
        (self.root / "my-paper-2.md").write_text("2", encoding="utf-8")
        path = CardStore._dedup_path(self.root, "my-paper")
        self.assertEqual(path, self.root / "my-paper-3.md")

    # ------------------------------------------------------------------
    # yaml_str
    # ------------------------------------------------------------------

    def test_yaml_str_empty(self) -> None:
        self.assertEqual(CardStore._yaml_str(""), '""')

    def test_yaml_str_escapes_quotes(self) -> None:
        result = CardStore._yaml_str('Paper "Title"')
        self.assertEqual(result, '"Paper \\"Title\\""')

    def test_yaml_str_escapes_backslash(self) -> None:
        result = CardStore._yaml_str(r"path\to\file")
        self.assertIn("\\\\", result)

    def test_yaml_str_simple_string(self) -> None:
        result = CardStore._yaml_str("Hello World")
        self.assertEqual(result, '"Hello World"')

    # ------------------------------------------------------------------
    # update_notion_url
    # ------------------------------------------------------------------

    def test_update_notion_url_updates_existing_file(self) -> None:
        file_path = self.root / "test.md"
        file_path.write_text('---\ntitle: "Test"\nnotion_url: ""\n---\n\nBody\n', encoding="utf-8")

        result = self.adapter.update_notion_url(file_path, "https://notion.so/new")
        self.assertTrue(result)

        content = file_path.read_text("utf-8")
        self.assertIn("https://notion.so/new", content)

    def test_update_notion_url_file_not_found(self) -> None:
        result = self.adapter.update_notion_url(self.root / "missing.md", "https://n.so/x")
        self.assertFalse(result)

    # ------------------------------------------------------------------
    # render body
    # ------------------------------------------------------------------

    def test_render_body_lists(self) -> None:
        card = LiteratureCard(
            title="Test",
            key_results=["Result A", "Result B"],
            useful_for=["Use case 1"],
        )
        body = self.adapter._render_body(card)
        self.assertIn("- Result A", body)
        self.assertIn("- Result B", body)
        self.assertIn("- Use case 1", body)

    def test_render_body_no_links_section_when_empty(self) -> None:
        card = LiteratureCard(title="Test")
        body = self.adapter._render_body(card)
        self.assertNotIn("## Links", body)


if __name__ == "__main__":
    unittest.main()
