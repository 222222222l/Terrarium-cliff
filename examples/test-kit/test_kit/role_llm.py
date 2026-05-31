from __future__ import annotations

import json
import os
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass
from typing import Mapping

DEFAULT_ROLE_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_ROLE_MODEL = "gemini-3-flash-preview"


@dataclass(frozen=True)
class RoleLlmSettings:
    base_url: str
    api_key: str
    model: str


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
    except Exception:
        with tempfile.NamedTemporaryFile("wb", suffix=".json", delete=False) as handle:
            handle.write(payload)
            payload_path = handle.name
        try:
            result = subprocess.run(
                [
                    "curl.exe",
                    "-sS",
                    "-X",
                    "POST",
                    url,
                    "-H",
                    "Content-Type: application/json",
                    "-H",
                    f"Authorization: Bearer {settings.api_key}",
                    "--data-binary",
                    "@" + payload_path,
                ],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            body = json.loads(result.stdout)
        finally:
            try:
                os.unlink(payload_path)
            except FileNotFoundError:
                pass
    if "choices" not in body:
        raise RuntimeError(f"role call did not return choices: {json.dumps(body, ensure_ascii=False)}")
    return str(body["choices"][0]["message"]["content"])
