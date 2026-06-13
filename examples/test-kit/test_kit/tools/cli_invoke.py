from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from kohakuterrarium.modules.tool.base import BaseTool, ExecutionMode, ToolResult

try:
    from test_kit.cli_runtime import execute_cli_invocation, format_cli_result
except ModuleNotFoundError:
    module_path = Path(__file__).resolve().parents[1] / "cli_runtime.py"
    spec = importlib.util.spec_from_file_location("test_kit.cli_runtime", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load cli_runtime from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["test_kit.cli_runtime"] = module
    spec.loader.exec_module(module)
    execute_cli_invocation = module.execute_cli_invocation
    format_cli_result = module.format_cli_result


class CliInvokeTool(BaseTool):
    needs_context = True
    is_concurrency_safe = True

    def __init__(self, **options: Any) -> None:
        super().__init__()
        self._options = dict(options)

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
                    "description": "Optional provider label. Default is cli-anything.",
                },
                "capability": {
                    "type": "string",
                    "description": "Optional capability label. Prefer http_fetch for public HTTP GET and shell_exec otherwise.",
                },
                "url": {
                    "type": "string",
                    "description": "Preferred form for public HTTP GET. Example: https://qt.gtimg.cn/q=sh600519",
                },
                "command": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Command to execute. Prefer a tokenized list, but a single command string is also accepted.",
                },
                "command_text": {
                    "type": "string",
                    "description": "Preferred fallback for general shell commands when you do not want to emit a JSON array. Example: curl https://qt.gtimg.cn/q=sh600519",
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
            "required": [],
        }

    @classmethod
    def option_schema(cls) -> dict[str, dict[str, Any]]:
        return {
            "provider_name": {
                "type": "string",
                "default": "cli-anything",
                "description": "Default provider label injected when the call omits it.",
            },
            "timeout_s": {
                "type": "int",
                "default": 90,
                "min": 1,
                "max": 3600,
                "description": "Default execution timeout for CLI calls.",
            },
            "token_budget_mode": {
                "type": "enum",
                "default": "silent",
                "values": ["silent", "minimal_diagnostic"],
                "description": "Default reporting mode when the call omits it.",
            },
            "provider_detect_cmd": {
                "type": "string",
                "default": "",
                "description": "Optional default binary probe command.",
            },
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
        record = execute_cli_invocation(self._merge_args(args), working_dir)
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
            "Execute a CLI action with silent execution defaults.\n\n"
            "## Behavior\n"
            "- prefer `url` for public HTTP GET\n"
            "- otherwise prefer `command_text`\n"
            "- keep `command` array as the legacy precise form\n"
            "- writes stdout/stderr to files\n"
            "- returns only summaries and artifact/log paths\n"
            "- upgrades to minimal diagnostic output only on failure\n"
        )
