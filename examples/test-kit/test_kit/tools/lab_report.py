from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from kohakuterrarium.modules.tool.base import BaseTool, ExecutionMode, ToolResult


class LabReportTool(BaseTool):
    needs_context = True
    is_concurrency_safe = False

    @property
    def tool_name(self) -> str:
        return "lab_report"

    @property
    def description(self) -> str:
        return "Save a structured lab report to .kohaku/lab-reports/"

    @property
    def execution_mode(self) -> ExecutionMode:
        return ExecutionMode.DIRECT

    def get_parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short test title"},
                "status": {
                    "type": "string",
                    "description": "Result label such as pass, fail, or note",
                },
                "summary": {
                    "type": "string",
                    "description": "One-line result summary",
                },
                "details": {
                    "type": "string",
                    "description": "Longer explanation of what was tested",
                },
                "artifacts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Relevant file paths or artifacts",
                },
            },
            "required": ["title", "status", "summary"],
        }

    async def _execute(self, args: dict[str, Any], **kwargs: Any) -> ToolResult:
        context = kwargs.get("context")
        working_dir = context.working_dir if context else Path.cwd()
        reports_dir = working_dir / ".kohaku" / "lab-reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        title = str(args.get("title", "untitled-test")).strip() or "untitled-test"
        status = str(args.get("status", "note")).strip() or "note"
        summary = str(args.get("summary", "")).strip()
        details = str(args.get("details", "")).strip()
        artifacts = args.get("artifacts") or []
        if not isinstance(artifacts, list):
            artifacts = [str(artifacts)]

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        slug = "-".join(title.lower().split())[:60] or "untitled-test"
        report_path = reports_dir / f"{timestamp}-{slug}.md"

        lines = [
            f"# {title}",
            "",
            f"- status: {status}",
            f"- summary: {summary}",
            f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        ]
        if artifacts:
            lines.append("- artifacts:")
            lines.extend(f"  - {item}" for item in artifacts)
        if details:
            lines.extend(["", "## Details", "", details])
        content = "\n".join(lines) + "\n"
        report_path.write_text(content, encoding="utf-8")

        return ToolResult(
            output=f"Saved lab report to {report_path}",
            exit_code=0,
            metadata={"report_path": str(report_path)},
        )

    def get_full_documentation(self, tool_format: str = "native") -> str:
        return (
            "# lab_report\n\n"
            "Save a structured Markdown report under `.kohaku/lab-reports/`.\n\n"
            "## Required arguments\n"
            "- `title`: short report title\n"
            "- `status`: pass, fail, or note\n"
            "- `summary`: one-line summary\n\n"
            "## Optional arguments\n"
            "- `details`: longer explanation\n"
            "- `artifacts`: list of related file paths\n"
        )
