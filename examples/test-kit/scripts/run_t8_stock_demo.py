from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "terrariums" / "task-team-minimal"
PROJECT_ROOT = ROOT.parents[1]
KT_HOME = PROJECT_ROOT / ".tmp-kt-home"
os.environ.setdefault("KT_CONFIG_DIR", str(KT_HOME))
(KT_HOME / "logs").mkdir(parents=True, exist_ok=True)

from kohakuterrarium.terrarium import LocalTerrariumService, Terrarium


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


def _build_summary(histories: dict[str, dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for cid, history in histories.items():
        messages = history.get("messages") or []
        summary[cid] = {
            "message_count": len(messages),
            "last_message": _last_message_text(history),
        }
    return summary


def _build_stock_task_card(code: str) -> str:
    market = "sh" + code if code.startswith("6") else "sz" + code
    return (
        f"task_id: stock_query_{code}\n"
        f"goal: 查询 A 股股票 {code} 的当前行情并提供简要分析与建议。\n"
        "constraints:\n"
        "  - 必须包含实时或最近收盘价格、涨跌幅、成交量等核心行情数据。\n"
        "  - 优先使用最小可行的公开 HTTP GET 获取路径。\n"
        "inputs:\n"
        f"  stock_code: \"{code}\"\n"
        f"  quote_url: \"https://qt.gtimg.cn/q={market}\"\n"
        "deliverable: 包含行情数据、简要分析及投资建议的文本报告。\n"
        "evidence_needed: 调用的 API 原始数据摘要或查询日志。\n"
        "done_definition: 报告中包含明确的行情数据，且分析逻辑与数据一致。\n"
        "task_kind: service_cli_task\n"
        "preferred_provider: cli-anything\n"
        "artifact_expectation: \"\"\n"
        "token_budget_mode: silent\n"
        "open_questions: []"
    )


def _history_contains(history: dict[str, Any], needle: str) -> bool:
    for message in history.get("messages") or []:
        content = message.get("content", "") if isinstance(message, dict) else message
        if isinstance(content, list):
            content = json.dumps(content, ensure_ascii=False)
        if needle in str(content):
            return True
    return False


def _pipeline_complete(histories: dict[str, dict[str, Any]]) -> bool:
    coordinator_messages = histories["coordinator"].get("messages") or []
    worker_messages = histories["worker"].get("messages") or []
    critic_messages = histories["critic"].get("messages") or []
    return (
        len(coordinator_messages) >= 3
        and len(worker_messages) >= 3
        and len(critic_messages) >= 2
        and _history_contains(histories["coordinator"], "task_id:")
    )


async def _wait_for_activity(engine: Terrarium, timeout_s: int) -> dict[str, dict[str, Any]]:
    service = LocalTerrariumService(engine)
    start = asyncio.get_running_loop().time()
    creature_ids = ["root", "coordinator", "worker", "critic"]
    while True:
        histories = {cid: await service.chat_history(cid) for cid in creature_ids}
        if _pipeline_complete(histories):
            return histories
        if asyncio.get_running_loop().time() - start >= timeout_s:
            return histories
        await asyncio.sleep(2.0)


async def _run_direct_turn(
    service: LocalTerrariumService,
    creature_id: str,
    message: str,
) -> dict[str, Any]:
    async for _ in service.chat(creature_id, message):
        pass
    return await service.chat_history(creature_id)


async def _run_sequential_fallback(
    service: LocalTerrariumService,
    code: str,
) -> dict[str, dict[str, Any]]:
    coordinator_history = await service.chat_history("coordinator")
    task_card = _build_stock_task_card(code)
    worker_message = (
        f"{task_card}\n\n"
        "Execution hint for this fallback run:\n"
        "- Use `cli_invoke` first.\n"
        "- Prefer the smallest schema: `url` first, then `command_text`.\n"
        "- Return one fenced YAML block named `execution_packet`.\n"
        "- Summarize the fetched quote fields before giving lightweight advice.\n"
    )
    worker_history = await _run_direct_turn(service, "worker", worker_message)
    execution_packet = _last_message_text(worker_history)

    critic_history = await _run_direct_turn(service, "critic", execution_packet)
    review_result = _last_message_text(critic_history)

    root_history = await _run_direct_turn(
        service,
        "root",
        f"[direct from critic] {review_result}",
    )
    return {
        "root": root_history,
        "coordinator": coordinator_history,
        "worker": worker_history,
        "critic": critic_history,
    }


async def main() -> None:
    code = os.environ.get("T8_STOCK_CODE", "600519").strip() or "600519"
    timeout_s = int(os.environ.get("T8_WAIT_SECONDS", "90") or "90")
    message = (
        f"用户上传的A股股票代码是 {code}。请使用当前 minimal team 跑通一次完整闭环："
        "先查询这家上市公司的当前股票现状，再给出简要分析和投资建议。"
        "本次目标是先跑通，不追求高质量投研。"
        "如需公开数据源，优先使用可直接通过命令获取的 HTTPS JSON 行情接口。"
    )

    engine = await Terrarium.from_recipe(str(RECIPE))
    service = LocalTerrariumService(engine)
    try:
        print(f"[demo] recipe={RECIPE}")
        print(f"[demo] stock_code={code}")
        print("[demo] injecting task to root")
        await service.inject_input("root", message, source="demo")
        print("\n[demo] waiting for downstream turns...")
        histories = await _wait_for_activity(engine, timeout_s)
        if not _pipeline_complete(histories):
            print("[demo] runtime wiring did not finish the full loop, falling back to sequential handoff")
            histories = await _run_sequential_fallback(service, code)
        summary = _build_summary(histories)

        for cid, history in histories.items():
            messages = history.get("messages") or []
            print(f"\n--- {cid} messages={len(messages)} ---")
            print(_last_message_text(history))

        output_path = os.environ.get("T8_OUTPUT_PATH", "").strip()
        if output_path:
            Path(output_path).write_text(
                json.dumps(summary, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        assert histories["coordinator"].get("messages"), "coordinator produced no conversation"
        assert histories["worker"].get("messages"), "worker produced no conversation"
        assert histories["critic"].get("messages"), "critic produced no conversation"
        assert histories["root"].get("messages"), "root produced no conversation"
    finally:
        await service.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
