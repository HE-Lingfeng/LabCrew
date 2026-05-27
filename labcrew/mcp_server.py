from __future__ import annotations

import json
import sys
from typing import Any

from labcrew.runtime import run_action


PROTOCOL_VERSION = "2024-11-05"


def main() -> None:
    server = LabCrewMCPServer(sys.stdin.buffer, sys.stdout.buffer)
    server.run()


class LabCrewMCPServer:
    def __init__(self, reader: Any, writer: Any) -> None:
        self.reader = reader
        self.writer = writer

    def run(self) -> None:
        while True:
            message = self.read_message()
            if message is None:
                return
            response = self.handle_message(message)
            if response is not None:
                self.write_message(response)

    def handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        if "id" not in message:
            return None
        method = message.get("method")
        try:
            if method == "initialize":
                result = {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "labcrew", "version": "0.1.0"},
                }
            elif method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "tools/call":
                params = message.get("params") or {}
                result = self._call_tool(str(params.get("name", "")), params.get("arguments") or {})
            else:
                return self._error(message["id"], -32601, f"Unknown method: {method}")
            return {"jsonrpc": "2.0", "id": message["id"], "result": result}
        except Exception as exc:
            return self._error(message["id"], -32603, str(exc))

    def _call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name not in TOOL_ACTIONS:
            raise ValueError(f"Unknown LabCrew tool: {name}")
        envelope = run_action(TOOL_ACTIONS[name], **arguments)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(envelope, ensure_ascii=False, indent=2),
                }
            ],
            "isError": not envelope["ok"],
        }

    def _error(self, message_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}

    def read_message(self) -> dict[str, Any] | None:
        headers: dict[str, str] = {}
        while True:
            line = self.reader.readline()
            if line == b"":
                return None
            text = line.decode("ascii").strip()
            if not text:
                break
            key, _, value = text.partition(":")
            headers[key.lower()] = value.strip()
        length = int(headers.get("content-length", "0"))
        if length <= 0:
            return None
        payload = self.reader.read(length)
        return json.loads(payload.decode("utf-8"))

    def write_message(self, message: dict[str, Any]) -> None:
        payload = json.dumps(message, ensure_ascii=False).encode("utf-8")
        header = f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii")
        self.writer.write(header + payload)
        self.writer.flush()


def _tool(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required or [],
        },
    }


COMMON_READ_PROPS = {
    "source": {"type": "string", "description": "Local PDF/text path or supported paper source."},
    "project": {"type": "string", "default": "general"},
    "save_journal": {"type": "boolean", "default": True},
    "journal_period": {"type": "string", "default": "weekly"},
    "save_to_notion": {"type": "boolean", "default": False},
    "save_to_cards": {"type": "boolean", "default": False},
}


TOOLS = [
    _tool(
        "read_paper",
        "Read and summarize a local paper source.",
        {**COMMON_READ_PROPS, "deep_method": {"type": "boolean", "default": False}},
        ["source"],
    ),
    _tool("deep_read_method", "Explain a paper's method section in detail.", COMMON_READ_PROPS, ["source"]),
    _tool("make_card", "Create a literature card from a paper source.", COMMON_READ_PROPS, ["source"]),
    _tool(
        "read_zotero_item",
        "Read and summarize a Zotero item by key.",
        {
            "item_key": {"type": "string"},
            "project": {"type": "string", "default": "general"},
            "deep_method": {"type": "boolean", "default": False},
            "save_journal": {"type": "boolean", "default": True},
            "journal_period": {"type": "string", "default": "weekly"},
            "save_to_notion": {"type": "boolean", "default": False},
            "save_to_cards": {"type": "boolean", "default": False},
        },
        ["item_key"],
    ),
    _tool(
        "plan_zotero_collection",
        "Generate a reading plan from a Zotero collection.",
        {"collection": {"type": "string"}, "batch_size": {"type": "integer", "default": 5}},
        ["collection"],
    ),
    _tool(
        "update_reading_status",
        "Update local reading status for a Zotero item, optionally syncing to Notion.",
        {
            "key": {"type": "string"},
            "status": {"type": "string", "enum": ["unread", "reading", "read", "skipped"]},
            "sync_to_notion": {"type": "boolean", "default": False},
        },
        ["key", "status"],
    ),
    _tool(
        "make_slides",
        "Create a slide plan or self-contained HTML deck from a paper source.",
        {
            "source": {"type": "string"},
            "project": {"type": "string", "default": "general"},
            "format": {"type": "string", "enum": ["plan", "html"], "default": "plan"},
        },
        ["source"],
    ),
    _tool(
        "propose_research",
        "Generate a research proposal scaffold from a source paper or seed question.",
        {
            "source": {"type": "string"},
            "research_question": {"type": "string"},
            "project": {"type": "string", "default": "general"},
        },
    ),
]


TOOL_ACTIONS = {tool["name"]: tool["name"] for tool in TOOLS}
TOOL_ACTIONS["plan_zotero_collection"] = "plan_zotero_collection"


if __name__ == "__main__":
    main()
