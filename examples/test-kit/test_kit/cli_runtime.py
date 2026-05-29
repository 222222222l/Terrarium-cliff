from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any


def execute_cli_invocation(
    invocation: dict[str, Any],
    working_dir: Path,
) -> dict[str, Any]:
    command = invocation.get("command")
    if not isinstance(command, list) or not command:
        raise ValueError("command must be a non-empty list of strings")
    if not all(isinstance(item, str) and item for item in command):
        raise ValueError("command entries must be non-empty strings")

    provider_name = str(invocation.get("provider_name", "unknown")).strip() or "unknown"
    capability = str(invocation.get("capability", "unknown")).strip() or "unknown"
    task_id = str(invocation.get("task_id", "")).strip() or _default_task_id(provider_name)
    token_budget_mode = str(invocation.get("token_budget_mode", "silent")).strip() or "silent"
    timeout_s = int(invocation.get("timeout_s", 60) or 60)
    expected_artifacts = _normalize_string_list(invocation.get("artifact_expectation"))
    provider_detect_cmd = str(invocation.get("provider_detect_cmd", "")).strip()
    env_overrides = invocation.get("env") or {}
    if env_overrides and not isinstance(env_overrides, dict):
        raise ValueError("env must be a mapping of environment variables")

    run_dir = working_dir / ".kohaku" / "cli-runs" / task_id
    run_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = run_dir / "stdout.log"
    stderr_path = run_dir / "stderr.log"
    raw_log_path = run_dir / "events.jsonl"
    invocation_path = run_dir / "invocation.json"
    result_path = run_dir / "result.json"

    invocation_record = {
        "provider_name": provider_name,
        "capability": capability,
        "task_id": task_id,
        "command": command,
        "token_budget_mode": token_budget_mode,
        "timeout_s": timeout_s,
        "artifact_expectation": expected_artifacts,
        "provider_detect_cmd": provider_detect_cmd or None,
    }
    invocation_path.write_text(
        json.dumps(invocation_record, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    start = time.perf_counter()
    _append_event(raw_log_path, {"event": "start", "command": command, "ts": time.time()})

    if provider_detect_cmd and not _is_command_available(provider_detect_cmd):
        duration_ms = int((time.perf_counter() - start) * 1000)
        record = {
            "provider_name": provider_name,
            "capability": capability,
            "success": False,
            "exit_code": None,
            "stdout_summary": "",
            "stderr_summary": f"required command not found: {provider_detect_cmd}",
            "artifact_paths": [],
            "duration_ms": duration_ms,
            "raw_log_path": str(raw_log_path),
            "retryable": False,
            "error_kind": "provider_unavailable",
            "token_budget_mode": token_budget_mode,
            "diagnostic_excerpt": f"provider command missing: {provider_detect_cmd}",
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "result_path": str(result_path),
        }
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text(record["stderr_summary"] + "\n", encoding="utf-8")
        _append_event(raw_log_path, {"event": "finish", "status": "provider_unavailable", "ts": time.time()})
        _write_record(result_path, record)
        return record

    env = os.environ.copy()
    for key, value in env_overrides.items():
        env[str(key)] = str(value)

    try:
        completed = subprocess.run(
            command,
            cwd=str(working_dir),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
            shell=False,
        )
        stdout_text = completed.stdout or ""
        stderr_text = completed.stderr or ""
        stdout_path.write_text(stdout_text, encoding="utf-8")
        stderr_path.write_text(stderr_text, encoding="utf-8")

        artifact_paths = _resolve_existing_artifacts(working_dir, expected_artifacts)
        missing_artifacts = [
            str((working_dir / path).resolve()) for path in expected_artifacts if not (working_dir / path).exists()
        ]
        success = completed.returncode == 0 and not missing_artifacts
        error_kind = None
        diagnostic_excerpt = ""
        retryable = False

        if completed.returncode != 0:
            error_kind = "process_error"
            diagnostic_excerpt = _diagnostic_excerpt(stderr_text or stdout_text)
            retryable = True
        elif missing_artifacts:
            error_kind = "artifact_missing"
            diagnostic_excerpt = f"missing artifacts: {', '.join(missing_artifacts[:3])}"

        duration_ms = int((time.perf_counter() - start) * 1000)
        record = {
            "provider_name": provider_name,
            "capability": capability,
            "success": success,
            "exit_code": completed.returncode,
            "stdout_summary": _summarize_stream(stdout_text),
            "stderr_summary": _summarize_stream(stderr_text),
            "artifact_paths": artifact_paths,
            "duration_ms": duration_ms,
            "raw_log_path": str(raw_log_path),
            "retryable": retryable,
            "error_kind": error_kind,
            "token_budget_mode": token_budget_mode,
            "diagnostic_excerpt": diagnostic_excerpt,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "result_path": str(result_path),
        }
        _append_event(
            raw_log_path,
            {
                "event": "finish",
                "status": "ok" if success else error_kind,
                "exit_code": completed.returncode,
                "ts": time.time(),
            },
        )
        _write_record(result_path, record)
        return record
    except subprocess.TimeoutExpired as exc:
        stdout_text = exc.stdout or ""
        stderr_text = exc.stderr or ""
        stdout_path.write_text(stdout_text, encoding="utf-8")
        stderr_path.write_text(stderr_text, encoding="utf-8")
        duration_ms = int((time.perf_counter() - start) * 1000)
        record = {
            "provider_name": provider_name,
            "capability": capability,
            "success": False,
            "exit_code": None,
            "stdout_summary": _summarize_stream(stdout_text),
            "stderr_summary": _summarize_stream(stderr_text),
            "artifact_paths": [],
            "duration_ms": duration_ms,
            "raw_log_path": str(raw_log_path),
            "retryable": True,
            "error_kind": "timeout",
            "token_budget_mode": token_budget_mode,
            "diagnostic_excerpt": f"command timed out after {timeout_s}s",
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "result_path": str(result_path),
        }
        _append_event(raw_log_path, {"event": "finish", "status": "timeout", "ts": time.time()})
        _write_record(result_path, record)
        return record


def format_cli_result(record: dict[str, Any]) -> str:
    lines = [
        f"provider={record.get('provider_name')}",
        f"capability={record.get('capability')}",
        f"success={record.get('success')}",
        f"exit_code={record.get('exit_code')}",
        f"stdout_summary={record.get('stdout_summary', '')}",
        f"stderr_summary={record.get('stderr_summary', '')}",
        f"artifacts={len(record.get('artifact_paths') or [])}",
        f"error_kind={record.get('error_kind')}",
        f"raw_log_path={record.get('raw_log_path')}",
        f"result_path={record.get('result_path')}",
    ]
    diagnostic_excerpt = str(record.get("diagnostic_excerpt", "")).strip()
    if diagnostic_excerpt:
        lines.append(f"diagnostic_excerpt={diagnostic_excerpt}")
    return "\n".join(lines)


def _default_task_id(provider_name: str) -> str:
    return f"{provider_name}-{uuid.uuid4().hex[:8]}"


def _normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        result = [str(item).strip() for item in value if str(item).strip()]
        return result
    text = str(value).strip()
    return [text] if text else []


def _resolve_existing_artifacts(working_dir: Path, expected_artifacts: list[str]) -> list[str]:
    results: list[str] = []
    for raw_path in expected_artifacts:
        path = (working_dir / raw_path).resolve()
        if path.exists():
            results.append(str(path))
    return results


def _append_event(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _write_record(path: Path, record: dict[str, Any]) -> None:
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _summarize_stream(text: str, max_chars: int = 180) -> str:
    clean = " ".join(text.strip().split())
    if not clean:
        return ""
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 3] + "..."


def _diagnostic_excerpt(text: str, max_chars: int = 240) -> str:
    clean = text.strip()
    if not clean:
        return ""
    if len(clean) <= max_chars:
        return clean
    return clean[-max_chars:]


def _is_command_available(command_name: str) -> bool:
    if command_name == "python":
        return True
    if command_name == "python3":
        return True
    if command_name == sys.executable:
        return True
    from shutil import which

    return which(command_name) is not None
