from __future__ import annotations

import importlib.util
import sys
import json
from pathlib import Path
from typing import Any

from kohakuterrarium.modules.tool.base import BaseTool, ExecutionMode, ToolResult

try:
    from test_kit.provider_selection import select_provider_for_task
except ModuleNotFoundError:
    module_path = Path(__file__).resolve().parents[1] / "provider_selection.py"
    spec = importlib.util.spec_from_file_location("test_kit.provider_selection", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load provider_selection from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["test_kit.provider_selection"] = module
    spec.loader.exec_module(module)
    select_provider_for_task = module.select_provider_for_task


class ProviderSelectTool(BaseTool):
    needs_context = True
    is_concurrency_safe = True

    def __init__(self, **options: Any) -> None:
        super().__init__()
        self._options = dict(options)

    @property
    def tool_name(self) -> str:
        return "provider_select"

    @property
    def description(self) -> str:
        return "Resolve the preferred CLI provider for a task card and require user choice when overlap remains ambiguous."

    @property
    def execution_mode(self) -> ExecutionMode:
        return ExecutionMode.DIRECT

    def get_parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task_kind": {
                    "type": "string",
                    "description": "Normalized task kind such as service_cli_task or browser_public_task.",
                },
                "preferred_provider": {
                    "type": "string",
                    "description": "Optional provider override from the task card.",
                },
                "access_mode": {
                    "type": "string",
                    "enum": ["local", "service", "browser", "desktop"],
                    "description": "High-level execution mode used when task_kind is not enough.",
                },
                "needs_browser_session": {
                    "type": "boolean",
                    "description": "Whether the task requires a live browser session or login state.",
                },
                "artifact_expectation": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Expected artifact paths carried through the task card.",
                },
                "target_hint": {
                    "type": "string",
                    "description": "Optional hint such as adapter, website, cli, or desktop.",
                },
                "registry_path": {
                    "type": "string",
                    "description": "Optional override path for examples/test-kit/registry/registry.yaml.",
                },
            },
        }

    @classmethod
    def option_schema(cls) -> dict[str, dict[str, Any]]:
        return {
            "registry_path": {
                "type": "string",
                "default": "",
                "description": "Optional default registry path override.",
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
        start_dir = Path(context.working_dir) if context else Path.cwd()
        repo_root = self._find_repo_root(start_dir)
        merged_args = self._merge_args(args)
        registry_path = merged_args.get("registry_path")

        result = select_provider_for_task(
            task_card=merged_args,
            repo_root=repo_root,
            registry_path=Path(str(registry_path)).resolve() if registry_path else None,
        )
        exit_code = 0 if result.get("decision_status") == "selected" else 2
        return ToolResult(
            output=json.dumps(result, indent=2, ensure_ascii=False),
            exit_code=exit_code,
            metadata={
                "decision_status": result.get("decision_status"),
                "preferred_provider": result.get("preferred_provider"),
            },
        )

    def _find_repo_root(self, start_dir: Path) -> Path:
        candidates = [start_dir.resolve(), *start_dir.resolve().parents]
        for candidate in candidates:
            if (candidate / "examples" / "test-kit" / "registry" / "registry.yaml").exists():
                return candidate
        return start_dir.resolve()

    def get_full_documentation(self, tool_format: str = "native") -> str:
        return (
            "# provider_select\n\n"
            "Resolve the preferred provider for a task card.\n\n"
            "## Behavior\n"
            "- respects explicit preferred_provider\n"
            "- auto-selects when routing is clear\n"
            "- returns needs_user_choice when CLI-Anything and OpenCLI overlap and the model should not guess\n"
        )
