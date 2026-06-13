from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kohakuterrarium.modules.plugin.base import BasePlugin, PluginContext


class AuditGuardPlugin(BasePlugin):
    name = "audit_guard"
    priority = 140

    def __init__(
        self,
        audit_path: str = ".kohaku/audit/audit-guard.jsonl",
        tracked_tools: list[str] | None = None,
        include_args: bool = True,
        include_result_preview: bool = True,
        **_extra: Any,
    ) -> None:
        super().__init__()
        self.options = {
            "audit_path": audit_path,
            "tracked_tools": list(tracked_tools or ["write", "edit", "cli_invoke"]),
            "include_args": bool(include_args),
            "include_result_preview": bool(include_result_preview),
        }
        self._context: PluginContext | None = None
        self.refresh_options()

    @classmethod
    def option_schema(cls) -> dict[str, dict[str, Any]]:
        return {
            "audit_path": {
                "type": "string",
                "default": ".kohaku/audit/audit-guard.jsonl",
                "doc": "Workspace-relative JSONL audit file path.",
            },
            "tracked_tools": {
                "type": "list",
                "item_type": "string",
                "default": ["write", "edit", "cli_invoke"],
                "doc": "Tool names to audit after execution.",
            },
            "include_args": {
                "type": "bool",
                "default": True,
                "doc": "Whether to include a bounded argument summary.",
            },
            "include_result_preview": {
                "type": "bool",
                "default": True,
                "doc": "Whether to include a bounded result preview.",
            },
        }

    def refresh_options(self) -> None:
        self._audit_path = str(self.options.get("audit_path") or "").strip()
        self._tracked_tools = set(self.options.get("tracked_tools") or [])
        self._include_args = bool(self.options.get("include_args", True))
        self._include_result_preview = bool(
            self.options.get("include_result_preview", True)
        )

    async def on_load(self, context: PluginContext) -> None:
        self._context = context

    async def post_tool_execute(self, result: Any, **kwargs: Any) -> Any | None:
        tool_name = str(kwargs.get("tool_name") or "")
        if tool_name not in self._tracked_tools:
            return None
        context = self._context
        if context is None:
            return None

        record = {
            "schema_version": "audit-guard.v1",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_name": context.agent_name,
            "session_id": context.session_id,
            "tool_name": tool_name,
            "job_id": str(kwargs.get("job_id") or ""),
            "source": "post_tool_execute",
        }
        if self._include_args:
            record["args_summary"] = _summarize_value(kwargs.get("args") or {})
        if self._include_result_preview:
            record["result_preview"] = _summarize_value(result)

        self._write_record(context.working_dir, record)
        return None

    def _write_record(self, working_dir: Path, record: dict[str, Any]) -> None:
        audit_path = Path(self._audit_path)
        if not audit_path.is_absolute():
            audit_path = working_dir / audit_path
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        with audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _summarize_value(value: Any, limit: int = 500) -> str:
    text = value if isinstance(value, str) else repr(value)
    text = " ".join(text.split())
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text
