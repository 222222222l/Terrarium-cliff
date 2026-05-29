from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def select_provider_for_task(
    task_card: dict[str, Any],
    repo_root: Path,
    registry_path: Path | None = None,
) -> dict[str, Any]:
    registry = _load_registry(
        registry_path or repo_root / "examples" / "test-kit" / "registry" / "registry.yaml"
    )

    preferred_provider = _clean(task_card.get("preferred_provider"))
    task_kind = _clean(task_card.get("task_kind"))
    access_mode = _clean(task_card.get("access_mode"))
    target_hint = _clean(task_card.get("target_hint"))
    needs_browser_session = task_card.get("needs_browser_session")
    artifact_expectation = _normalize_list(task_card.get("artifact_expectation"))

    providers = {item["name"]: item for item in registry.get("providers", []) if isinstance(item, dict)}
    if preferred_provider:
        if preferred_provider not in providers:
            raise ValueError(f"Unknown preferred_provider: {preferred_provider}")
        return _selected_result(
            provider_name=preferred_provider,
            reason="explicit preferred_provider",
            task_kind=task_kind,
            artifact_expectation=artifact_expectation,
            decision_source="preferred_provider",
        )

    if task_kind in {"local_software_task", "service_cli_task"}:
        return _selected_result(
            provider_name="cli-anything",
            reason=f"task_kind:{task_kind}",
            task_kind=task_kind,
            artifact_expectation=artifact_expectation,
            decision_source="task_kind",
        )
    if task_kind in {"browser_authenticated_task", "desktop_app_task", "external_cli_passthrough"}:
        return _selected_result(
            provider_name="opencli",
            reason=f"task_kind:{task_kind}",
            task_kind=task_kind,
            artifact_expectation=artifact_expectation,
            decision_source="task_kind",
        )
    if task_kind == "browser_public_task":
        return _needs_user_choice_result(
            reason="browser_public_task overlaps between CLI-Anything and OpenCLI",
            task_kind=task_kind,
            artifact_expectation=artifact_expectation,
            target_hint=target_hint,
        )

    if access_mode in {"local", "service"}:
        return _selected_result(
            provider_name="cli-anything",
            reason=f"access_mode:{access_mode}",
            task_kind=task_kind or "service_cli_task",
            artifact_expectation=artifact_expectation,
            decision_source="access_mode",
        )
    if access_mode == "desktop":
        return _selected_result(
            provider_name="opencli",
            reason="access_mode:desktop",
            task_kind=task_kind or "desktop_app_task",
            artifact_expectation=artifact_expectation,
            decision_source="access_mode",
        )
    if access_mode == "browser":
        if needs_browser_session is True:
            return _selected_result(
                provider_name="opencli",
                reason="browser task requires live browser session",
                task_kind=task_kind or "browser_authenticated_task",
                artifact_expectation=artifact_expectation,
                decision_source="browser_session_requirement",
            )
        if needs_browser_session is False and target_hint in {"adapter", "site", "website"}:
            return _needs_user_choice_result(
                reason="browser task is public but may fit either reusable CLI or OpenCLI adapter",
                task_kind=task_kind or "browser_public_task",
                artifact_expectation=artifact_expectation,
                target_hint=target_hint,
            )
        return _needs_user_choice_result(
            reason="browser capability overlaps and authentication need is unclear",
            task_kind=task_kind or "browser_public_task",
            artifact_expectation=artifact_expectation,
            target_hint=target_hint,
        )

    return _needs_user_choice_result(
        reason="task card does not provide enough routing information",
        task_kind=task_kind or "unknown",
        artifact_expectation=artifact_expectation,
        target_hint=target_hint,
    )


def _load_registry(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML object in {path}")
    return data


def _selected_result(
    *,
    provider_name: str,
    reason: str,
    task_kind: str,
    artifact_expectation: list[str],
    decision_source: str,
) -> dict[str, Any]:
    return {
        "decision_status": "selected",
        "preferred_provider": provider_name,
        "task_kind": task_kind,
        "artifact_expectation": artifact_expectation,
        "decision_reason": reason,
        "decision_source": decision_source,
        "candidate_providers": [provider_name],
        "user_choice_required": False,
    }


def _needs_user_choice_result(
    *,
    reason: str,
    task_kind: str,
    artifact_expectation: list[str],
    target_hint: str,
) -> dict[str, Any]:
    options = [
        {
            "provider_name": "cli-anything",
            "label": "CLI-Anything",
            "reason": "Prefer when the task should become a reusable or generic CLI workflow.",
        },
        {
            "provider_name": "opencli",
            "label": "OpenCLI",
            "reason": "Prefer when the task depends on browser sessions, adapters, or desktop-app integration.",
        },
    ]
    prompt = "该任务在 CLI-Anything 与 OpenCLI 之间存在重叠，当前信息不足以自动判断更优 provider。"
    if target_hint:
        prompt += f" 当前 target_hint 为 `{target_hint}`。"
    prompt += " 请由用户二选一后继续执行。"
    return {
        "decision_status": "needs_user_choice",
        "preferred_provider": None,
        "task_kind": task_kind,
        "artifact_expectation": artifact_expectation,
        "decision_reason": reason,
        "decision_source": "overlap_guard",
        "candidate_providers": ["cli-anything", "opencli"],
        "user_choice_required": True,
        "user_choice_prompt": prompt,
        "user_choice_options": options,
    }


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _clean(value: Any) -> str:
    return str(value or "").strip().lower()
