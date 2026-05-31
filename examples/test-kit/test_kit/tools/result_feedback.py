from __future__ import annotations
import importlib.util
import sys
from pathlib import Path
from typing import Any

from kohakuterrarium.modules.tool.base import BaseTool, ExecutionMode, ToolResult

try:
    from test_kit.feedback_protocol import build_feedback_payload
except ModuleNotFoundError:
    module_path = Path(__file__).resolve().parents[1] / "feedback_protocol.py"
    spec = importlib.util.spec_from_file_location("test_kit.feedback_protocol", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load feedback_protocol from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["test_kit.feedback_protocol"] = module
    spec.loader.exec_module(module)
    build_feedback_payload = module.build_feedback_payload


class ResultFeedbackTool(BaseTool):
    needs_context = True
    is_concurrency_safe = True

    def __init__(self, **options: Any) -> None:
        super().__init__()
        self._options = dict(options)

    @property
    def tool_name(self) -> str:
        return "result_feedback"

    @property
    def description(self) -> str:
        return "Create dual-channel feedback for any tool result: structured agent output plus concise user-facing progress text."

    @property
    def execution_mode(self) -> ExecutionMode:
        return ExecutionMode.DIRECT

    def get_parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tool_name": {"type": "string", "description": "Tool name being summarized."},
                "call_status": {
                    "type": "string",
                    "enum": ["running", "success", "failed"],
                    "description": "Current call status.",
                },
                "current_action": {
                    "type": "string",
                    "description": "What is happening now.",
                },
                "next_action": {
                    "type": "string",
                    "description": "What will happen next.",
                },
                "achievements": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Completed milestones to surface to the user.",
                },
                "key_findings": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Short structured findings for downstream agent use.",
                },
                "artifacts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Primary artifacts produced by the tool call.",
                },
                "evidence_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Logs or evidence paths related to the call.",
                },
                "error_kind": {
                    "type": "string",
                    "description": "Optional normalized error kind when the call failed.",
                },
                "raw_result": {
                    "description": "Optional raw result object or summary to be compressed for downstream agents.",
                },
                "agent_format": {
                    "type": "string",
                    "enum": ["json", "xml"],
                    "description": "Serialization format for the agent-facing output.",
                },
            },
            "required": ["tool_name", "call_status", "current_action"],
        }

    @classmethod
    def option_schema(cls) -> dict[str, dict[str, Any]]:
        return {
            "agent_format": {
                "type": "enum",
                "default": "json",
                "values": ["json", "xml"],
                "description": "Default agent-facing feedback format.",
            }
        }

    @classmethod
    def default_options(cls) -> dict[str, Any]:
        return {
            key: value.get("default")
            for key, value in cls.option_schema().items()
            if "default" in value
        }

    def _merge_args(self, args: dict[str, Any]) -> dict[str, Any]:
        merged = self.default_options()
        merged.update(self._options)
        merged.update({key: value for key, value in args.items() if value is not None})
        return merged

    async def _execute(self, args: dict[str, Any], **kwargs: Any) -> ToolResult:
        context = kwargs.get("context")
        working_dir = Path(context.working_dir) if context else Path.cwd()
        payload = build_feedback_payload(self._merge_args(args), working_dir)
        return ToolResult(
            output=payload["user_feedback"],
            exit_code=0,
            metadata={
                "schema_version": payload["schema_version"],
                "agent_feedback_path": payload["agent_feedback_path"],
                "user_feedback_path": payload["user_feedback_path"],
                "agent_feedback_format": payload["agent_feedback_format"],
                "agent_feedback_preview": payload["agent_feedback_preview"],
            },
        )

    def get_full_documentation(self, tool_format: str = "native") -> str:
        return (
            "# result_feedback\n\n"
            "Create dual-channel feedback for any tool result.\n\n"
            "## Channels\n"
            "- user-facing: concise progress text\n"
            "- agent-facing: compact structured feedback in JSON or XML\n"
        )
