from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Mapping

DEFAULT_ROLE_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_ROLE_MODEL = "gemini-3-flash-preview"
DEFAULT_ROLE_MAX_ATTEMPTS = 3
DEFAULT_ROLE_RETRY_DELAY_S = 1.0


@dataclass(frozen=True)
class RoleLlmSettings:
    base_url: str
    api_key: str
    model: str


def _decode_bytes(data: bytes | None) -> str:
    if not data:
        return ""
    for encoding in ("utf-8", "gb18030", "cp936", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _shorten(text: str, limit: int = 1200) -> str:
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[:limit] + "...(truncated)"


def _is_retryable_http_error(status_code: int, response_body: str) -> bool:
    lowered = response_body.lower()
    return status_code >= 500 or "empty_response" in lowered or "temporar" in lowered


def _is_retryable_transport_error(exc: Exception) -> bool:
    if isinstance(exc, urllib.error.URLError):
        return True
    lowered = str(exc).lower()
    return (
        "timed out" in lowered or "connection reset" in lowered or "temporar" in lowered
    )


def _build_curl_command(url: str, api_key: str, payload_path: str) -> list[str]:
    command = [
        _curl_binary(),
        "-sS",
        "-X",
        "POST",
        url,
        "-H",
        "Content-Type: application/json",
        "-H",
        f"Authorization: Bearer {api_key}",
    ]
    if os.name == "nt":
        command.append("--ssl-no-revoke")
    command.extend(
        [
            "--data-binary",
            "@" + payload_path,
        ]
    )
    return command


def _curl_binary() -> str:
    return "curl.exe" if os.name == "nt" else "curl"


def resolve_role_llm_settings(env: Mapping[str, str] | None = None) -> RoleLlmSettings:
    source = env or os.environ
    base_url = (
        str(source.get("TASK_TEAM_BASE_URL", "") or "").strip()
        or str(source.get("OPENROUTER_BASE_URL", "") or "").strip()
        or DEFAULT_ROLE_BASE_URL
    )
    model = (
        str(source.get("TASK_TEAM_MODEL", "") or "").strip()
        or str(source.get("OPENROUTER_MODEL", "") or "").strip()
        or DEFAULT_ROLE_MODEL
    )
    api_key = (
        str(source.get("TASK_TEAM_API_KEY", "") or "").strip()
        or str(source.get("OPENROUTER_API_KEY", "") or "").strip()
    )
    if not api_key:
        raise RuntimeError(
            "Missing role LLM API key. Set TASK_TEAM_API_KEY or OPENROUTER_API_KEY "
            f"(base_url defaults to {DEFAULT_ROLE_BASE_URL}, model defaults to {DEFAULT_ROLE_MODEL})."
        )
    return RoleLlmSettings(
        base_url=base_url.rstrip("/"),
        api_key=api_key,
        model=model,
    )


def call_role_llm(
    system_prompt: str,
    user_message: str,
    *,
    max_tokens: int = 800,
    env: Mapping[str, str] | None = None,
) -> str:
    settings = resolve_role_llm_settings(env)
    payload = json.dumps(
        {
            "model": settings.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": max_tokens,
        }
    ).encode("utf-8")
    url = f"{settings.base_url}/chat/completions"
    primary_error_detail = ""
    body = None
    for attempt in range(1, DEFAULT_ROLE_MAX_ATTEMPTS + 1):
        retryable = False
        try:
            request = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.api_key}",
                },
            )
            with urllib.request.urlopen(request, timeout=120) as response:
                body = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            response_body = _decode_bytes(exc.read())
            primary_error_detail = (
                f"HTTP {exc.code} {exc.reason} from {url}. "
                f"Response body: {_shorten(response_body) or '<empty>'}"
            )
            retryable = _is_retryable_http_error(exc.code, response_body)
        except Exception as exc:
            primary_error_detail = f"{type(exc).__name__}: {exc}"
            retryable = _is_retryable_transport_error(exc)

        if retryable and attempt < DEFAULT_ROLE_MAX_ATTEMPTS:
            time.sleep(DEFAULT_ROLE_RETRY_DELAY_S * attempt)
            continue
        body = None
        break

    if body is None:
        with tempfile.NamedTemporaryFile("wb", suffix=".json", delete=False) as handle:
            handle.write(payload)
            payload_path = handle.name
        try:
            command = _build_curl_command(url, settings.api_key, payload_path)
            try:
                result = subprocess.run(
                    command,
                    check=True,
                    capture_output=True,
                    text=False,
                )
            except FileNotFoundError as exc:
                raise RuntimeError(
                    "role call failed after urllib fallback to curl. "
                    f"Primary error: {primary_error_detail or '<none>'}. "
                    f"curl executable not found: {command[0]}."
                ) from exc
            except subprocess.CalledProcessError as exc:
                stdout_text = _shorten(_decode_bytes(exc.stdout))
                stderr_text = _shorten(_decode_bytes(exc.stderr))
                raise RuntimeError(
                    "role call failed after urllib fallback to curl. "
                    f"Primary error: {primary_error_detail or '<none>'}. "
                    f"curl exit code: {exc.returncode}. "
                    f"curl stdout: {stdout_text or '<empty>'}. "
                    f"curl stderr: {stderr_text or '<empty>'}."
                ) from exc
            stdout_text = _decode_bytes(result.stdout)
            try:
                body = json.loads(stdout_text)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    "role call curl fallback returned non-JSON output. "
                    f"Primary error: {primary_error_detail or '<none>'}. "
                    f"curl stdout: {_shorten(stdout_text) or '<empty>'}."
                ) from exc
        finally:
            try:
                os.unlink(payload_path)
            except FileNotFoundError:
                pass
    if "choices" not in body:
        raise RuntimeError(
            f"role call did not return choices: {json.dumps(body, ensure_ascii=False)}"
        )
    return str(body["choices"][0]["message"]["content"])
