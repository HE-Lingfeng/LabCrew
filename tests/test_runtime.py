from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from labcrew.mcp_server import LabCrewMCPServer
from labcrew.runtime import run_action
from labcrew.schemas import TaskResult


class RuntimeTests(unittest.TestCase):
    def test_run_action_returns_envelope_and_artifacts(self) -> None:
        result = TaskResult(
            task_id="task-1",
            agent_name="labcrew",
            data={
                "paper": {
                    "title": "Paper",
                    "pdf_path": "/tmp/paper.pdf",
                    "ingestion": {"warnings": ["figure extraction skipped"]},
                },
                "cards": {"path": "research/papers/paper.md"},
            },
            notes=["mock note"],
        )
        with patch("labcrew.runtime.workflows.read_paper", return_value=result) as read_paper:
            envelope = run_action("read_paper", source="/tmp/paper.pdf", deep_method=True, save_to_cards=True)

        read_paper.assert_called_once_with(
            "/tmp/paper.pdf",
            project="general",
            deep_method=True,
            save_journal=True,
            journal_period="weekly",
            save_to_notion=False,
            save_to_cards=True,
        )
        self.assertTrue(envelope["ok"])
        self.assertEqual(envelope["data"]["task_id"], "task-1")
        self.assertIn("/tmp/paper.pdf", envelope["artifacts"])
        self.assertIn("research/papers/paper.md", envelope["artifacts"])
        self.assertIn("figure extraction skipped", envelope["warnings"])
        self.assertIn("mock note", envelope["warnings"])

    def test_run_action_returns_friendly_error(self) -> None:
        envelope = run_action("read_zotero_item")

        self.assertFalse(envelope["ok"])
        self.assertEqual(envelope["data"], None)
        self.assertIn("Missing required parameter: item_key", envelope["error"])


class MCPServerTests(unittest.TestCase):
    def test_tools_list_exposes_labcrew_tools(self) -> None:
        server = LabCrewMCPServer(reader=None, writer=None)

        response = server.handle_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertIn("read_paper", names)
        self.assertIn("read_zotero_item", names)
        self.assertIn("propose_research", names)

    def test_tools_call_wraps_runtime_envelope_as_text_content(self) -> None:
        server = LabCrewMCPServer(reader=None, writer=None)
        envelope = {"ok": True, "data": {"title": "Paper"}, "warnings": [], "artifacts": [], "error": None}

        with patch("labcrew.mcp_server.run_action", return_value=envelope) as run:
            response = server.handle_message(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "read_paper", "arguments": {"source": "/tmp/paper.pdf"}},
                }
            )

        run.assert_called_once_with("read_paper", source="/tmp/paper.pdf")
        assert response is not None
        content = response["result"]["content"][0]
        self.assertEqual(content["type"], "text")
        self.assertEqual(json.loads(content["text"]), envelope)
        self.assertFalse(response["result"]["isError"])


if __name__ == "__main__":
    unittest.main()
