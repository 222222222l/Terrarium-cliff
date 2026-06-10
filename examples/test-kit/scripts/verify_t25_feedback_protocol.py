from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import sys
import tempfile
import types
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class ExecutionMode(Enum):
    DIRECT = "direct"


@dataclass
class ToolContext:
    agent_name: str
    session: object | None
    working_dir: Path


@dataclass
class ToolResult:
    output: str = ""
    exit_code: int | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.error is None and (self.exit_code is None or self.exit_code == 0)

    def get_text_output(self) -> str:
        return self.output


class BaseTool:
    async def execute(
        self, args: dict[str, Any], context: ToolContext | None = None
    ) -> ToolResult:
        return await self._execute(args, context=context)


def load_module(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module {module_name} from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def install_tool_base_stub() -> None:
    sys.modules.setdefault("kohakuterrarium", types.ModuleType("kohakuterrarium"))
    sys.modules.setdefault(
        "kohakuterrarium.modules", types.ModuleType("kohakuterrarium.modules")
    )
    sys.modules.setdefault(
        "kohakuterrarium.modules.tool", types.ModuleType("kohakuterrarium.modules.tool")
    )
    base_module = types.ModuleType("kohakuterrarium.modules.tool.base")
    base_module.BaseTool = BaseTool
    base_module.ExecutionMode = ExecutionMode
    base_module.ToolContext = ToolContext
    base_module.ToolResult = ToolResult
    sys.modules["kohakuterrarium.modules.tool.base"] = base_module


def load_t25_modules(repo_root: Path) -> tuple[object, object]:
    install_tool_base_stub()
    package_root = repo_root / "examples" / "test-kit" / "test_kit"
    load_module("test_kit", package_root / "__init__.py")
    load_module("test_kit.tools", package_root / "tools" / "__init__.py")
    feedback_protocol = load_module(
        "test_kit.feedback_protocol",
        package_root / "feedback_protocol.py",
    )
    result_feedback = load_module(
        "test_kit.tools.result_feedback",
        package_root / "tools" / "result_feedback.py",
    )
    return feedback_protocol, result_feedback


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def verify_json_payload(build_feedback_payload, working_dir: Path) -> dict:
    payload = build_feedback_payload(
        {
            "tool_name": "provider_select",
            "call_status": "success",
            "current_action": "整理 provider 选择结果",
            "next_action": "将 provider 选择写回 task card",
            "achievements": ["完成重叠能力判定", "生成用户可读摘要"],
            "key_findings": ["browser_public_task 仍需用户决定"],
            "artifacts": ["examples/test-kit/registry/registry.yaml"],
            "evidence_paths": ["logs/provider-select.log"],
            "raw_result": {
                "decision_status": "needs_user_choice",
                "candidate_providers": ["cli-anything", "opencli"],
                "verbose_trace": "x" * 400,
            },
        },
        working_dir,
    )
    check(
        payload["schema_version"] == "t25.v1",
        "json payload should expose schema version",
    )
    check(
        "正在做什么：" in payload["user_feedback"],
        "user summary should include current action",
    )
    check(
        "将要做什么：" in payload["user_feedback"],
        "user summary should include next action",
    )
    check(
        "已经达成：" in payload["user_feedback"],
        "user summary should include achievements",
    )

    agent_path = Path(payload["agent_feedback_path"])
    user_path = Path(payload["user_feedback_path"])
    check(agent_path.exists(), "json agent feedback file should exist")
    check(user_path.exists(), "json user feedback file should exist")

    agent_data = json.loads(agent_path.read_text(encoding="utf-8"))
    check(
        agent_data["feedback_target"] == "agent",
        "json agent payload should mark target",
    )
    check(
        agent_data["retention_hint"] == "transient",
        "json agent payload should be transient",
    )
    check(
        agent_data["tool_name"] == "provider_select",
        "json agent payload should keep tool name",
    )
    check(
        agent_data["raw_result_excerpt"]["decision_status"] == "needs_user_choice",
        "json agent payload should keep compact raw result",
    )
    check(
        "verbose_trace" in agent_data["raw_result_excerpt"],
        "json agent payload should keep only compact raw result fields",
    )
    check(
        len(str(agent_data["raw_result_excerpt"]["verbose_trace"])) <= 160,
        "json raw result should be trimmed",
    )
    check(
        user_path.read_text(encoding="utf-8").strip() == payload["user_feedback"],
        "user feedback file should match returned summary",
    )
    return {
        "tool_name": agent_data["tool_name"],
        "call_status": agent_data["call_status"],
        "user_feedback": payload["user_feedback"],
    }


def verify_xml_payload(build_feedback_payload, working_dir: Path) -> dict:
    payload = build_feedback_payload(
        {
            "tool_name": "cli_invoke",
            "call_status": "failed",
            "current_action": "归档失败摘要",
            "next_action": "准备最小化诊断信息",
            "achievements": ["保存 stdout/stderr 摘要"],
            "key_findings": ["stderr 暗示 provider 不可用"],
            "error_kind": "provider_unavailable",
            "raw_result": {"stderr_summary": "command not found"},
            "agent_format": "xml",
        },
        working_dir,
    )
    agent_path = Path(payload["agent_feedback_path"])
    agent_text = agent_path.read_text(encoding="utf-8")
    check(agent_path.suffix == ".xml", "xml payload should write xml file")
    check(
        "<tool_feedback>" in agent_text, "xml payload should use tool_feedback root tag"
    )
    check(
        "<feedback_target>agent</feedback_target>" in agent_text,
        "xml payload should mark target",
    )
    check(
        "<error_kind>provider_unavailable</error_kind>" in agent_text,
        "xml payload should preserve normalized error kind",
    )
    return {
        "tool_name": payload["tool_name"],
        "call_status": payload["call_status"],
        "agent_feedback_format": payload["agent_feedback_format"],
    }


async def verify_tool_execution(ResultFeedbackTool, working_dir: Path) -> dict:
    tool = ResultFeedbackTool()
    context = ToolContext(
        agent_name="lab-runner",
        session=None,
        working_dir=working_dir,
    )
    result = await tool.execute(
        {
            "tool_name": "result_feedback",
            "call_status": "running",
            "current_action": "生成双通道反馈",
            "next_action": "把结构化结果交给后续 agent",
            "achievements": ["用户摘要已生成"],
            "key_findings": ["agent 输出将落盘为结构化文件"],
        },
        context=context,
    )
    check(result.success, "tool execution should succeed")
    check(
        result.get_text_output().startswith(
            "工具 `result_feedback` 当前状态：执行中。"
        ),
        "tool output should stay user-facing",
    )
    check(
        "agent_feedback_path=" not in result.get_text_output(),
        "tool output should not mix path details",
    )
    check(
        result.metadata["schema_version"] == "t25.v1",
        "tool metadata should expose schema version",
    )
    check(
        Path(result.metadata["agent_feedback_path"]).exists(),
        "tool metadata should point to agent feedback",
    )
    check(
        Path(result.metadata["user_feedback_path"]).exists(),
        "tool metadata should point to user feedback",
    )
    return {
        "output_preview": result.get_text_output(),
        "agent_feedback_format": result.metadata["agent_feedback_format"],
    }


def verify_registration(repo_root: Path) -> dict:
    package_manifest = yaml.safe_load(
        (repo_root / "examples" / "test-kit" / "kohaku.yaml").read_text(
            encoding="utf-8"
        )
    )
    creature_config = yaml.safe_load(
        (
            repo_root
            / "examples"
            / "test-kit"
            / "creatures"
            / "lab-runner"
            / "config.yaml"
        ).read_text(encoding="utf-8")
    )
    package_tool_names = [tool["name"] for tool in package_manifest["tools"]]
    creature_tool_names = [tool["name"] for tool in creature_config["tools"]]
    check(
        "result_feedback" in package_tool_names,
        "package manifest should register result_feedback",
    )
    check(
        "result_feedback" in creature_tool_names,
        "lab-runner should expose result_feedback",
    )
    return {
        "package_registered": "result_feedback" in package_tool_names,
        "creature_registered": "result_feedback" in creature_tool_names,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify T25 feedback protocol.")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[3]),
        help="Repository root containing examples/test-kit/.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve()
    feedback_protocol, result_feedback = load_t25_modules(repo_root)

    tmp_root = repo_root / "tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="t25-feedback-", dir=tmp_root) as temp_dir:
        working_dir = Path(temp_dir).resolve()
        json_case = verify_json_payload(
            feedback_protocol.build_feedback_payload, working_dir
        )
        xml_case = verify_xml_payload(
            feedback_protocol.build_feedback_payload, working_dir
        )
        tool_case = asyncio.run(
            verify_tool_execution(result_feedback.ResultFeedbackTool, working_dir)
        )

    registration_case = verify_registration(repo_root)
    report = {
        "status": "PASS",
        "json_case": json_case,
        "xml_case": xml_case,
        "tool_case": tool_case,
        "registration_case": registration_case,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
