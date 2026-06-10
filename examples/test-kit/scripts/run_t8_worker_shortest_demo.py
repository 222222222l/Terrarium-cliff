from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RECIPE = PROJECT_ROOT / "examples" / "test-kit" / "terrariums" / "task-team-minimal"
KT_HOME = PROJECT_ROOT / ".tmp-kt-home"
CLI_RUNS_DIR = PROJECT_ROOT / ".kohaku" / "cli-runs"

os.environ.setdefault("KT_CONFIG_DIR", str(KT_HOME))
(KT_HOME / "logs").mkdir(parents=True, exist_ok=True)

from kohakuterrarium.terrarium import LocalTerrariumService, Terrarium


def _load_resolve_role_llm_settings():
    try:
        from test_kit.role_llm import resolve_role_llm_settings  # type: ignore

        return resolve_role_llm_settings
    except Exception:
        import importlib.util
        import sys

        module_path = PROJECT_ROOT / "examples" / "test-kit" / "test_kit" / "role_llm.py"
        module_name = "test_kit.role_llm"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load role_llm helper from {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module.resolve_role_llm_settings


RESOLVE_ROLE_LLM_SETTINGS = _load_resolve_role_llm_settings()


def _build_task_card(code: str) -> str:
    market = "sh" + code if code.startswith("6") else "sz" + code
    return (
        f"task_id: stock_query_{code}\n"
        f"goal: 查询 A 股股票 {code} 的当前行情并提供简要分析与建议。\n"
        "constraints:\n"
        "  - 必须包含实时或最近收盘价格、涨跌幅、成交量等核心行情数据。\n"
        "  - 优先使用最小可行的公开 HTTP GET 获取路径。\n"
        "inputs:\n"
        f"  stock_code: \"{code}\"\n"
        f"  quote_url: \"https://qt.gtimg.cn/q={'sh' + code if code.startswith('6') else 'sz' + code}\"\n"
        "deliverable: 包含行情数据、简要分析及投资建议的文本报告。\n"
        "evidence_needed: 调用的 API 原始数据摘要或查询日志。\n"
        "done_definition: 报告中包含明确的行情数据，且分析逻辑与数据一致。\n"
        "task_kind: service_cli_task\n"
        "preferred_provider: cli-anything\n"
        "artifact_expectation: \"\"\n"
        "token_budget_mode: silent\n"
        "open_questions: []\n"
        "\n"
        "Execution hint:\n"
        "- Prefer `cli_invoke`.\n"
        "- Prefer the smallest schema: `url` first, then `command_text`, then `command`.\n"
        f"- For this task, the public quote URL is https://qt.gtimg.cn/q={market}\n"
        "- Return exactly one fenced YAML block named `execution_packet`.\n"
    )


def _last_message_text(history: dict[str, Any]) -> str:
    messages = history.get("messages") or []
    if not messages:
        return ""
    last = messages[-1]
    if isinstance(last, dict):
        content = last.get("content", "")
        if isinstance(content, list):
            return json.dumps(content, ensure_ascii=False)
        return str(content)
    return str(last)


def _assistant_count(history: dict[str, Any]) -> int:
    count = 0
    for message in history.get("messages") or []:
        if isinstance(message, dict) and str(message.get("role", "")).lower() == "assistant":
            count += 1
    return count


def _extract_first_fenced_block(text: str) -> str:
    match = re.search(r"```(?:yaml|yml|md|markdown)?\s*\n([\s\S]*?)\n```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()


def _result_path_from_text(text: str) -> Path | None:
    for raw_path in re.findall(r"[A-Za-z]:\\[^\r\n\"']+?result\.json", text):
        result_path = Path(raw_path)
        if result_path.exists():
            return result_path
    return None


def _result_path_from_turn_result(turn_result: dict[str, Any]) -> Path | None:
    result_path = _result_path_from_text(str(turn_result.get("output_text", "") or ""))
    if result_path is not None:
        return result_path
    for activity in turn_result.get("activities") or []:
        if not isinstance(activity, dict):
            continue
        metadata = activity.get("metadata") or {}
        if isinstance(metadata, dict):
            for key in ("output", "result", "error"):
                result_path = _result_path_from_text(str(metadata.get(key, "") or ""))
                if result_path is not None:
                    return result_path
        result_path = _result_path_from_text(str(activity.get("detail", "") or ""))
        if result_path is not None:
            return result_path
    return None


def _existing_result_paths() -> set[str]:
    return {str(path.resolve()) for path in CLI_RUNS_DIR.glob("*/result.json") if path.exists()}


async def main() -> None:
    RESOLVE_ROLE_LLM_SETTINGS(os.environ)
    code = os.environ.get("T8_STOCK_CODE", "600519").strip() or "600519"
    output_path = os.environ.get("T8_OUTPUT_PATH", "").strip()
    timeout_s = int(os.environ.get("T8_WAIT_SECONDS", "90") or "90")
    task_card_path = os.environ.get("T8_TASK_CARD_PATH", "").strip()
    task_card = (
        Path(task_card_path).read_text(encoding="utf-8")
        if task_card_path
        else _build_task_card(code)
    )

    engine = await Terrarium.from_recipe(str(RECIPE))
    service = LocalTerrariumService(engine)
    try:
        result_paths_before = _existing_result_paths()
        turn_result = await service.run_input_turn(
            "worker",
            task_card,
            source="shortest-demo",
            timeout_s=timeout_s,
            completion_scope="graph",
        )

        output_text = str(turn_result.get("output_text", "") or "")
        execution_packet = _extract_first_fenced_block(output_text)
        result_path = _result_path_from_turn_result(turn_result)
        if result_path is None:
            raise AssertionError("worker shortest-chain run did not surface a cli_invoke result_path in turn output")
        invocation_path = result_path.with_name("invocation.json")
        if not invocation_path.exists():
            raise AssertionError(f"worker shortest-chain run surfaced result_path without invocation.json: {result_path}")

        invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
        result = json.loads(result_path.read_text(encoding="utf-8"))
        stdout_text = Path(result["stdout_path"]).read_text(encoding="utf-8")
        fresh_cli_result_produced = str(result_path.resolve()) not in result_paths_before
        worker_history = (
            {"messages": [{"role": "assistant", "content": output_text}]}
            if output_text
            else {"messages": []}
        )

        summary = {
            "code": code,
            "task_card_path": task_card_path or None,
            "worker_message_count": len(worker_history.get("messages") or []),
            "worker_last_message": _last_message_text(worker_history),
            "invocation_path": str(invocation_path),
            "result_path": str(result_path),
            "command": invocation.get("command"),
            "success": result.get("success"),
            "exit_code": result.get("exit_code"),
            "stdout_summary": result.get("stdout_summary"),
            "assistant_turn_observed": bool(output_text),
            "fresh_cli_result_produced": fresh_cli_result_produced,
        }

        if output_path:
            Path(output_path).write_text(
                json.dumps(summary, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        print(f"[shortest] code={code}")
        print(f"[shortest] result_path={result_path}")
        print(f"[shortest] success={result.get('success')} exit_code={result.get('exit_code')}")
        print(f"[shortest] command={invocation.get('command')}")
        print(f"[shortest] stdout_summary={result.get('stdout_summary')}")

        assert fresh_cli_result_produced is True, "shortest-chain run reused an old cli result instead of producing a fresh one"
        assert result.get("success") is True, f"cli_invoke did not succeed: {result_path}"
        assert result.get("exit_code") == 0, f"cli_invoke exit code was not 0: {result_path}"
        assert f"~{code}~" in stdout_text, "quote payload does not contain the requested stock code"
        assert invocation.get("command") == ["curl.exe", f"https://qt.gtimg.cn/q=sh{code}"] or invocation.get(
            "command"
        ) == ["curl.exe", f"https://qt.gtimg.cn/q=sz{code}"], "unexpected cli_invoke command"
    finally:
        await service.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
