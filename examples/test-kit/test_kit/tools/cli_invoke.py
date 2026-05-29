from __future__ import annotations

from pathlib import Path
from typing import Any

from kohakuterrarium.modules.tool.base import BaseTool, ExecutionMode, ToolResult

from test_kit.cli_runtime import execute_cli_invocation, format_cli_result


class CliInvokeTool(BaseTool):
    needs_context = True
    is_concurrency_safe = True

    @property
    def tool_name(self) -> str:
        return "cli_invoke"

    @property
    def description(self) -> str:
        return "Run a CLI command with silent execution defaults and return only a structured execution record."

    @property
    def execution_mode(self) -> ExecutionMode:
        return ExecutionMode.DIRECT

    def get_parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "provider_name": {
                    "type": "string",
                    "description": "Provider label used for metadata and result records.",
                },
                "capability": {
                    "type": "string",
                    "description": "Capability label used for metadata and result records.",
                },
                "command": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Command tokens to execute. Use a tokenized list, not a shell string.",
                },
                "artifact_expectation": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Relative artifact paths expected after command success.",
                },
                "timeout_s": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 3600,
                    "description": "Execution timeout in seconds.",
                },
                "token_budget_mode": {
                    "type": "string",
                    "enum": ["silent", "minimal_diagnostic"],
                    "description": "Silent is default. Minimal diagnostic still returns only summaries unless failure occurs.",
                },
                "provider_detect_cmd": {
                    "type": "string",
                    "description": "Optional command name used to fail fast when a provider binary is missing.",
                },
                "task_id": {
                    "type": "string",
                    "description": "Optional run identifier. Defaults to a provider-prefixed UUID.",
                },
                "env": {
                    "type": "object",
                    "description": "Optional environment variable overrides.",
                },
            },
            "required": ["provider_name", "capability", "command"],
        }

    async def _execute(self, args: dict[str, Any], **kwargs: Any) -> ToolResult:
        context = kwargs.get("context")
        working_dir = Path(context.working_dir) if context else Path.cwd()
        record = execute_cli_invocation(args, working_dir)
        return ToolResult(
            output=format_cli_result(record),
            exit_code=0 if record.get("success") else 1,
            metadata={
                "provider": record.get("provider_name"),
                "capability": record.get("capability"),
                "result_path": record.get("result_path"),
            },
        )

    def get_full_documentation(self, tool_format: str = "native") -> str:
        return (
            "# cli_invoke\n\n"
            "Execute a tokenized CLI command with silent execution defaults.\n\n"
            "## Behavior\n"
            "- writes stdout/stderr to files\n"
            "- returns only summaries and artifact/log paths\n"
            "- upgrades to minimal diagnostic output only on failure\n"
        )
