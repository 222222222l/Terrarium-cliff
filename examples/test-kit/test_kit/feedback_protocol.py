from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape


def build_feedback_payload(
    payload: dict[str, Any],
    working_dir: Path,
) -> dict[str, Any]:
    working_dir = working_dir.resolve()
    tool_name = _clean(payload.get("tool_name")) or "unknown_tool"
    call_status = _clean(payload.get("call_status")) or "unknown"
    current_action = _clean_text(payload.get("current_action"))
    next_action = _clean_text(payload.get("next_action"))
    achievements = _normalize_list(payload.get("achievements"))
    key_findings = _normalize_list(payload.get("key_findings"))
    artifacts = _normalize_list(payload.get("artifacts"))
    evidence_paths = _normalize_list(payload.get("evidence_paths"))
    error_kind = _clean(payload.get("error_kind"))
    raw_result = payload.get("raw_result")
    agent_format = _clean(payload.get("agent_format")) or "json"

    if agent_format not in {"json", "xml"}:
        raise ValueError("agent_format must be json or xml")

    user_summary = build_user_summary(
        current_action=current_action,
        next_action=next_action,
        achievements=achievements,
        call_status=call_status,
        tool_name=tool_name,
        error_kind=error_kind,
    )
    agent_feedback = build_agent_feedback(
        tool_name=tool_name,
        call_status=call_status,
        current_action=current_action,
        next_action=next_action,
        achievements=achievements,
        key_findings=key_findings,
        artifacts=artifacts,
        evidence_paths=evidence_paths,
        error_kind=error_kind,
        raw_result=raw_result,
        agent_format=agent_format,
    )

    feedback_dir = working_dir / ".kohaku" / "feedback"
    feedback_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = "-".join(tool_name.lower().split())[:60] or "tool"
    extension = "json" if agent_format == "json" else "xml"
    agent_feedback_path = feedback_dir / f"{timestamp}-{slug}-agent.{extension}"
    user_feedback_path = feedback_dir / f"{timestamp}-{slug}-user.txt"

    agent_feedback_path.write_text(agent_feedback["serialized"], encoding="utf-8")
    user_feedback_path.write_text(user_summary + "\n", encoding="utf-8")

    return {
        "schema_version": "t25.v1",
        "tool_name": tool_name,
        "call_status": call_status,
        "user_feedback": user_summary,
        "agent_feedback_format": agent_format,
        "agent_feedback_path": str(agent_feedback_path),
        "user_feedback_path": str(user_feedback_path),
        "agent_feedback_preview": agent_feedback["preview"],
        "compression_notes": [
            "agent_feedback keeps only short structured fields",
            "user_feedback keeps only milestone-level natural language",
            "raw_result is trimmed before serialization",
        ],
    }


def build_user_summary(
    *,
    current_action: str,
    next_action: str,
    achievements: list[str],
    call_status: str,
    tool_name: str,
    error_kind: str,
) -> str:
    lines = [f"工具 `{tool_name}` 当前状态：{_label_status(call_status, error_kind)}。"]
    if current_action:
        lines.append(f"正在做什么：{current_action}")
    if next_action:
        lines.append(f"将要做什么：{next_action}")
    if achievements:
        lines.append(f"已经达成：{'; '.join(achievements[:3])}")
    return "\n".join(lines)


def build_agent_feedback(
    *,
    tool_name: str,
    call_status: str,
    current_action: str,
    next_action: str,
    achievements: list[str],
    key_findings: list[str],
    artifacts: list[str],
    evidence_paths: list[str],
    error_kind: str,
    raw_result: Any,
    agent_format: str,
) -> dict[str, str]:
    compact_payload = {
        "schema_version": "t25.v1",
        "feedback_target": "agent",
        "retention_hint": "transient",
        "tool_name": tool_name,
        "call_status": call_status,
        "current_action": current_action,
        "next_action": next_action,
        "achievements": achievements[:5],
        "key_findings": key_findings[:5],
        "artifacts": artifacts[:5],
        "evidence_paths": evidence_paths[:5],
        "error_kind": error_kind or None,
        "raw_result_excerpt": _compact_raw_result(raw_result),
    }
    compact_payload = {
        key: value
        for key, value in compact_payload.items()
        if value not in ("", None, [], {})
    }

    if agent_format == "json":
        serialized = json.dumps(compact_payload, indent=2, ensure_ascii=False) + "\n"
    else:
        serialized = _to_xml(compact_payload)
    preview = serialized[:240].strip()
    return {"serialized": serialized, "preview": preview}


def _to_xml(payload: dict[str, Any]) -> str:
    lines = ["<tool_feedback>"]
    for key, value in payload.items():
        lines.extend(_xml_lines(key, value, 1))
    lines.append("</tool_feedback>")
    return "\n".join(lines) + "\n"


def _xml_lines(key: str, value: Any, level: int) -> list[str]:
    indent = "  " * level
    tag = escape(str(key))
    if isinstance(value, list):
        lines = [f"{indent}<{tag}>"]
        for item in value:
            lines.append(f"{indent}  <item>{escape(str(item))}</item>")
        lines.append(f"{indent}</{tag}>")
        return lines
    return [f"{indent}<{tag}>{escape(str(value))}</{tag}>"]


def _compact_raw_result(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key in sorted(value.keys())[:8]:
            item = value[key]
            if isinstance(item, (str, int, float, bool)) or item is None:
                result[str(key)] = str(item)[:160] if isinstance(item, str) else item
            elif isinstance(item, list):
                result[str(key)] = [str(v) for v in item[:5]]
            else:
                result[str(key)] = str(item)[:160]
        return result
    if isinstance(value, list):
        return [str(item)[:120] for item in value[:8]]
    return str(value)[:240]


def _label_status(call_status: str, error_kind: str) -> str:
    if call_status == "success":
        return "已完成"
    if call_status == "running":
        return "执行中"
    if call_status == "failed":
        if error_kind:
            return f"执行失败（{error_kind}）"
        return "执行失败"
    return call_status or "未知"


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _clean(value: Any) -> str:
    return str(value or "").strip().lower()


def _clean_text(value: Any) -> str:
    return str(value or "").strip()
