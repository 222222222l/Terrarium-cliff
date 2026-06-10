from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RECIPE = PROJECT_ROOT / "examples" / "test-kit" / "terrariums" / "task-team-minimal"
KT_HOME = PROJECT_ROOT / ".tmp-kt-home"
CLI_RUNS_DIR = PROJECT_ROOT / ".kohaku" / "cli-runs"
COORDINATOR_SYSTEM = (
    (PROJECT_ROOT / "examples" / "test-kit" / "creatures" / "coordinator" / "prompts" / "system.md")
    .read_text(encoding="utf-8")
    + "\n\n"
    + (PROJECT_ROOT / "examples" / "test-kit" / "terrariums" / "task-team-minimal" / "prompts" / "coordinator.md")
    .read_text(encoding="utf-8")
)
CRITIC_SYSTEM = (
    (PROJECT_ROOT / "examples" / "test-kit" / "creatures" / "critic" / "prompts" / "system.md")
    .read_text(encoding="utf-8")
    + "\n\n"
    + (PROJECT_ROOT / "examples" / "test-kit" / "terrariums" / "task-team-minimal" / "prompts" / "critic.md")
    .read_text(encoding="utf-8")
)
ROOT_SYSTEM = (
    (PROJECT_ROOT / "examples" / "test-kit" / "creatures" / "root-privileged" / "prompts" / "system.md")
    .read_text(encoding="utf-8")
    + "\n\n"
    + (PROJECT_ROOT / "examples" / "test-kit" / "terrariums" / "task-team-minimal" / "prompts" / "root.md")
    .read_text(encoding="utf-8")
    + "\n\n"
    + "Direct harness override:\n"
    + "- Do not call, simulate, or mention group_status, group_send, or any tool traces.\n"
    + "- Do not output tool logs.\n"
    + "- Only produce a concise user-facing final answer."
)

os.environ.setdefault("KT_CONFIG_DIR", str(KT_HOME))
(KT_HOME / "logs").mkdir(parents=True, exist_ok=True)

from kohakuterrarium.terrarium import LocalTerrariumService, Terrarium


def _load_call_role_llm():
    try:
        from test_kit.role_llm import call_role_llm  # type: ignore

        return call_role_llm
    except Exception:
        module_path = PROJECT_ROOT / "examples" / "test-kit" / "test_kit" / "role_llm.py"
        module_name = "test_kit.role_llm"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load role_llm helper from {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module.call_role_llm


CALL_ROLE_LLM = _load_call_role_llm()


def _load_resolve_role_llm_settings():
    try:
        from test_kit.role_llm import resolve_role_llm_settings  # type: ignore

        return resolve_role_llm_settings
    except Exception:
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


def _split_codes(raw: str) -> list[str]:
    return [code.strip() for code in raw.split(",") if code.strip()]


def _market_code(code: str) -> str:
    return ("sh" if code.startswith("6") else "sz") + code


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


def _build_history_from_turn_output(turn_result: dict[str, Any]) -> dict[str, Any]:
    text = str(turn_result.get("output_text", "") or "")
    if not text:
        return {"messages": []}
    return {"messages": [{"role": "assistant", "content": text}]}


def _strip_output_wrappers(text: str) -> str:
    cleaned = re.sub(r"\[/?output_[^\]]+\]", "", text)
    cleaned = re.sub(r"</?output_[^>]+>", "", cleaned)
    return cleaned.strip()


def _extract_first_fenced_block(text: str) -> str:
    cleaned = _strip_output_wrappers(text)
    match = re.search(r"```(?:yaml|yml|md|markdown)?\s*\n([\s\S]*?)\n```", cleaned, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return cleaned.strip()


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


def _write_json(path_text: str, payload: dict[str, Any]) -> None:
    if not path_text:
        return
    Path(path_text).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


async def _chat_turn(
    service: LocalTerrariumService,
    creature_id: str,
    message: str,
) -> dict[str, Any]:
    timeout_s = int(os.environ.get("T8_TURN_TIMEOUT", "120") or "120")
    turn_result = await service.run_input_turn(
        creature_id,
        message,
        source="stable-full-demo",
        timeout_s=timeout_s,
        completion_scope="graph",
    )
    history = _build_history_from_turn_output(turn_result)
    if _assistant_count(history) > 0:
        return {"history": history, "turn_result": turn_result}
    raise TimeoutError(f"{creature_id} did not produce assistant text within {timeout_s}s")


async def _run_worker_turn(
    service: LocalTerrariumService,
    task_card: str,
    *,
    require_new_cli_result: bool = True,
) -> dict[str, Any]:
    result_paths_before = _existing_result_paths()
    turn_output = await _chat_turn(service, "worker", task_card)
    worker_history = turn_output["history"]
    turn_result = turn_output["turn_result"]
    execution_packet = _extract_first_fenced_block(_last_message_text(worker_history))
    result_path = _result_path_from_turn_result(turn_result)
    if result_path is None:
        if require_new_cli_result:
            raise AssertionError("worker turn did not surface a cli_invoke result_path in turn output")
        fresh_cli_result_produced = False
        invocation_path = None
    else:
        invocation_path = result_path.with_name("invocation.json")
        fresh_cli_result_produced = str(result_path.resolve()) not in result_paths_before

    result: dict[str, Any] | None = None
    invocation: dict[str, Any] | None = None
    stdout_text = ""
    if result_path and result_path.exists():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        stdout_path = Path(str(result.get("stdout_path", "") or ""))
        if stdout_path.exists():
            stdout_text = stdout_path.read_text(encoding="utf-8")
    if invocation_path and invocation_path.exists():
        invocation = json.loads(invocation_path.read_text(encoding="utf-8"))

    return {
        "history": worker_history,
        "execution_packet": execution_packet,
        "invocation_path": str(invocation_path) if invocation_path else "",
        "result_path": str(result_path) if result_path else "",
        "invocation": invocation,
        "result": result,
        "stdout_text": stdout_text,
        "fresh_cli_result_produced": fresh_cli_result_produced,
        "reused_cli_result": (not fresh_cli_result_produced) and bool(result_path),
    }


async def _run_single_cycle(
    service: LocalTerrariumService,
    *,
    code: str,
    user_goal: str,
    prior_context: str = "",
    include_root: bool = True,
    require_new_cli_result: bool = True,
) -> dict[str, Any]:
    coordinator_request = (
        f"用户目标：{user_goal}\n"
        f"股票代码：{code}\n"
        f"公开行情 URL：https://qt.gtimg.cn/q={_market_code(code)}\n"
        "请输出一个最小可执行的 task_card。\n"
        "只输出一个 fenced YAML block named `task_card`，不要使用 output_task_card 或其他包装标签。"
    )
    if prior_context:
        coordinator_request += f"\n\n补充上下文：\n{prior_context}"

    coordinator_text = CALL_ROLE_LLM(COORDINATOR_SYSTEM, coordinator_request, max_tokens=700)
    task_card = _extract_first_fenced_block(coordinator_text)

    worker_run = await _run_worker_turn(
        service,
        (
            f"{task_card}\n\n"
            "执行要求：\n"
            "- 优先使用最小 schema：url -> command_text -> command。\n"
            "- 不要使用 output_execution_packet 或任何包装标签。\n"
            "- 最终只输出一个 fenced YAML block named `execution_packet`。\n"
        ),
        require_new_cli_result=require_new_cli_result,
    )

    critic_request = (
        f"原始用户目标：{user_goal}\n"
        f"股票代码：{code}\n\n"
        "下面是 worker 的 execution_packet：\n"
        f"```yaml\n{worker_run['execution_packet']}\n```\n\n"
        "请按约定输出一个 fenced YAML block named `review_result`，不要使用 output_review_result 包装标签。"
    )
    critic_text = CALL_ROLE_LLM(CRITIC_SYSTEM, critic_request, max_tokens=900)
    review_result = _extract_first_fenced_block(critic_text)

    root_answer = ""
    if include_root:
        root_request = (
            f"用户原始目标：{user_goal}\n"
            f"股票代码：{code}\n\n"
            "下面是 critic 的 review_result：\n"
            f"```yaml\n{review_result}\n```\n\n"
            "请直接给出面向用户的最终回答。"
            "不要继续 group_send，不要重新派发，只做简要总结、风险提示和下一步建议。"
        )
        root_answer = CALL_ROLE_LLM(ROOT_SYSTEM, root_request, max_tokens=500)

    return {
        "code": code,
        "user_goal": user_goal,
        "task_card": task_card,
        "execution_packet": worker_run["execution_packet"],
        "review_result": review_result,
        "root_answer": root_answer,
        "cli_invocation_path": worker_run["invocation_path"],
        "cli_result_path": worker_run["result_path"],
        "cli_command": (worker_run["invocation"] or {}).get("command"),
        "cli_success": (worker_run["result"] or {}).get("success"),
        "cli_exit_code": (worker_run["result"] or {}).get("exit_code"),
        "stdout_contains_code": code in worker_run["stdout_text"] if worker_run["stdout_text"] else None,
        "fresh_cli_result_produced": worker_run["fresh_cli_result_produced"],
        "reused_cli_result": worker_run["reused_cli_result"],
    }


async def main() -> None:
    RESOLVE_ROLE_LLM_SETTINGS(os.environ)
    codes = _split_codes(os.environ.get("T8_MULTI_CODES", "600519,000001"))
    mode = os.environ.get("T8_MODE", "all").strip().lower() or "all"
    include_root = os.environ.get("T8_INCLUDE_ROOT", "1").strip() not in {"0", "false", "False"}
    interrupt_append = (
        os.environ.get(
            "T8_INTERRUPT_APPEND",
            "在原分析基础上，追加分析成交量、成交额，以及是否存在明显放量或缩量信号。",
        ).strip()
        or "在原分析基础上，追加分析成交量、成交额，以及是否存在明显放量或缩量信号。"
    )
    output_path = os.environ.get("T8_OUTPUT_PATH", "").strip()
    state: dict[str, Any] = {
        "phase": "init",
        "mode": mode,
        "include_root": include_root,
        "multi_stock_codes": codes,
        "interrupt_append": interrupt_append,
    }
    _write_json(output_path, state)

    engine = await Terrarium.from_recipe(str(RECIPE))
    service = LocalTerrariumService(engine)
    try:
        multi_stock_results: list[dict[str, Any]] = []
        interrupt_summary: dict[str, Any] | None = None

        if mode in {"all", "multi"}:
            print("[full-demo] phase=multi_stock_start", flush=True)
            for code in codes:
                goal = f"请对 A 股股票 {code} 做一次当前行情快照、简要分析和轻量投资建议。"
                multi_stock_results.append(
                    await _run_single_cycle(service, code=code, user_goal=goal, include_root=include_root)
                )
                state["phase"] = f"multi_stock_done_{code}"
                state["multi_stock_results"] = multi_stock_results
                _write_json(output_path, state)
                print(f"[full-demo] code={code} done", flush=True)

        if mode in {"all", "interrupt"}:
            interrupt_code = codes[0]
            initial_goal = f"请先对 A 股股票 {interrupt_code} 做一次当前行情快照、简要分析和轻量投资建议。"
            initial_cycle = await _run_single_cycle(
                service,
                code=interrupt_code,
                user_goal=initial_goal,
                include_root=include_root,
            )
            state["phase"] = "interrupt_initial_done"
            state["interrupt_test"] = {"code": interrupt_code, "initial_cycle": initial_cycle}
            _write_json(output_path, state)
            print(f"[interrupt-demo] initial code={interrupt_code} done", flush=True)

            interrupt_context = (
                "这是用户中途追加的目标，请在保留原任务的基础上修正执行重点。\n"
                f"上一次 task_card：\n```yaml\n{initial_cycle['task_card']}\n```\n\n"
                f"上一次 execution_packet：\n```yaml\n{initial_cycle['execution_packet']}\n```"
            )
            interrupted_goal = f"{initial_goal} 另外，{interrupt_append}"
            interrupted_cycle = await _run_single_cycle(
                service,
                code=interrupt_code,
                user_goal=interrupted_goal,
                prior_context=interrupt_context,
                include_root=include_root,
                require_new_cli_result=False,
            )
            interrupt_summary = {
                "code": interrupt_code,
                "append_goal": interrupt_append,
                "initial_cycle": initial_cycle,
                "interrupted_cycle": interrupted_cycle,
            }
            state["phase"] = "interrupt_followup_done"
            state["interrupt_test"] = interrupt_summary
            _write_json(output_path, state)
            print(f"[interrupt-demo] followup code={interrupt_code} done", flush=True)

        summary = {"mode": mode}
        if multi_stock_results:
            summary["multi_stock_codes"] = codes
            summary["multi_stock_results"] = multi_stock_results
        if interrupt_summary:
            summary["interrupt_test"] = interrupt_summary

        if output_path:
            _write_json(output_path, summary)

        for result in multi_stock_results:
            print(
                f"[full-demo] code={result['code']} success={result['cli_success']} "
                f"exit={result['cli_exit_code']} command={result['cli_command']}"
            )
        if interrupt_summary:
            print(
                f"[interrupt-demo] code={interrupt_summary['code']} "
                f"initial_success={interrupt_summary['initial_cycle']['cli_success']} "
                f"interrupted_success={interrupt_summary['interrupted_cycle']['cli_success']}"
            )

        if multi_stock_results:
            assert all(result["fresh_cli_result_produced"] for result in multi_stock_results), "multi-stock run skipped fresh worker cli execution"
            assert all(result["cli_success"] for result in multi_stock_results), "multi-stock run had a failed worker cli step"
            assert all(result["stdout_contains_code"] for result in multi_stock_results), "multi-stock run missing stock code in stdout"
        if interrupt_summary:
            initial_cycle = interrupt_summary["initial_cycle"]
            interrupted_cycle = interrupt_summary["interrupted_cycle"]
            interrupt_focus = "\n".join(
                [
                    interrupted_cycle["task_card"],
                    interrupted_cycle["execution_packet"],
                    interrupted_cycle["review_result"],
                    interrupted_cycle["root_answer"],
                ]
            ).lower()
            assert initial_cycle["fresh_cli_result_produced"] is True, "interrupt initial cycle skipped fresh worker cli execution"
            assert initial_cycle["cli_success"] is True, "interrupt initial cycle failed"
            assert (
                interrupted_cycle["fresh_cli_result_produced"] is True
                or interrupted_cycle["reused_cli_result"] is True
            ), "interrupt follow-up produced no usable cli evidence"
            assert interrupted_cycle["cli_success"] is True, "interrupt follow-up did not preserve successful cli evidence"
            assert any(keyword in interrupt_focus for keyword in ["成交量", "成交额", "volume", "turnover"]), (
                "interrupt goal was not reflected in the revised follow-up output"
            )
    except Exception as exc:
        state["phase"] = "error"
        state["error"] = repr(exc)
        _write_json(output_path, state)
        raise
    finally:
        await service.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
