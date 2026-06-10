from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import urllib.error
from pathlib import Path

import pytest
import yaml


MODULE_PATH = (
    Path(__file__).resolve().parents[3]
    / "examples"
    / "test-kit"
    / "test_kit"
    / "role_llm.py"
)
TEST_KIT_DIR = MODULE_PATH.parent
CLI_RUNTIME_PATH = TEST_KIT_DIR / "cli_runtime.py"
SYNC_SCRIPT_PATH = TEST_KIT_DIR.parent / "scripts" / "sync_test_kit_module_configs.py"


def _load_role_llm_module():
    module_name = "test_kit.role_llm_test"
    spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_resolve_role_llm_settings_prefers_task_team_env():
    role_llm = _load_role_llm_module()

    settings = role_llm.resolve_role_llm_settings(
        {
            "TASK_TEAM_BASE_URL": "https://example.test/v1",
            "TASK_TEAM_API_KEY": "task-key",
            "TASK_TEAM_MODEL": "task-model",
            "OPENROUTER_API_KEY": "fallback-key",
            "OPENROUTER_MODEL": "fallback-model",
        }
    )

    assert settings.base_url == "https://example.test/v1"
    assert settings.api_key == "task-key"
    assert settings.model == "task-model"


def test_resolve_role_llm_settings_falls_back_to_openrouter_env():
    role_llm = _load_role_llm_module()

    settings = role_llm.resolve_role_llm_settings(
        {
            "OPENROUTER_API_KEY": "or-key",
            "OPENROUTER_MODEL": "or-model",
        }
    )

    assert settings.base_url == role_llm.DEFAULT_ROLE_BASE_URL
    assert settings.api_key == "or-key"
    assert settings.model == "or-model"


def test_resolve_role_llm_settings_requires_api_key():
    role_llm = _load_role_llm_module()

    with pytest.raises(RuntimeError, match="TASK_TEAM_API_KEY or OPENROUTER_API_KEY"):
        role_llm.resolve_role_llm_settings({})


def test_call_role_llm_preserves_http_500_body_and_curl_failure_details(monkeypatch):
    role_llm = _load_role_llm_module()

    def _boom_urlopen(_request, timeout):
        raise urllib.error.HTTPError(
            url="https://example.test/v1/chat/completions",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=io.BytesIO(b'{"error":"upstream overloaded"}'),
        )

    def _boom_run(*args, **kwargs):
        raise subprocess.CalledProcessError(
            35,
            args[0],
            stdout=b"",
            stderr="SSL connect error".encode("gb18030"),
        )

    monkeypatch.setattr(role_llm.urllib.request, "urlopen", _boom_urlopen)
    monkeypatch.setattr(role_llm.subprocess, "run", _boom_run)

    with pytest.raises(RuntimeError, match="HTTP 500") as excinfo:
        role_llm.call_role_llm(
            "system",
            "user",
            env={
                "TASK_TEAM_BASE_URL": "https://example.test/v1",
                "TASK_TEAM_API_KEY": "task-key",
                "TASK_TEAM_MODEL": "task-model",
            },
        )

    message = str(excinfo.value)
    assert "upstream overloaded" in message
    assert "curl exit code: 35" in message
    assert "SSL connect error" in message


def test_call_role_llm_decodes_non_utf8_curl_stdout(monkeypatch):
    role_llm = _load_role_llm_module()

    def _boom_urlopen(_request, timeout):
        raise urllib.error.HTTPError(
            url="https://example.test/v1/chat/completions",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=io.BytesIO(b'{"error":"retry via curl"}'),
        )

    payload = {"choices": [{"message": {"content": "probe-ok"}}]}
    stdout_bytes = json.dumps(payload, ensure_ascii=False).encode("gb18030")

    def _ok_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout=stdout_bytes, stderr=b"")

    monkeypatch.setattr(role_llm.urllib.request, "urlopen", _boom_urlopen)
    monkeypatch.setattr(role_llm.subprocess, "run", _ok_run)

    output = role_llm.call_role_llm(
        "system",
        "user",
        env={
            "TASK_TEAM_BASE_URL": "https://example.test/v1",
            "TASK_TEAM_API_KEY": "task-key",
            "TASK_TEAM_MODEL": "task-model",
        },
    )

    assert output == "probe-ok"


def test_call_role_llm_retries_empty_response_before_falling_back(monkeypatch):
    role_llm = _load_role_llm_module()
    attempts = {"count": 0}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def read(self):
            return b'{"choices":[{"message":{"content":"retry-ok"}}]}'

    def _flaky_urlopen(_request, timeout):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise urllib.error.HTTPError(
                url="https://example.test/v1/chat/completions",
                code=500,
                msg="Internal Server Error",
                hdrs={},
                fp=io.BytesIO(
                    b'{"error":{"code":"empty_response","message":"empty response from Gemini API"}}'
                ),
            )
        return _Response()

    sleep_calls: list[float] = []
    curl_called: list[bool] = []

    def _sleep(delay: float):
        sleep_calls.append(delay)

    def _unexpected_curl(*args, **kwargs):
        curl_called.append(True)
        raise AssertionError("curl fallback should not be used when retry succeeds")

    monkeypatch.setattr(role_llm.urllib.request, "urlopen", _flaky_urlopen)
    monkeypatch.setattr(role_llm.time, "sleep", _sleep)
    monkeypatch.setattr(role_llm.subprocess, "run", _unexpected_curl)

    output = role_llm.call_role_llm(
        "system",
        "user",
        env={
            "TASK_TEAM_BASE_URL": "https://example.test/v1",
            "TASK_TEAM_API_KEY": "task-key",
            "TASK_TEAM_MODEL": "task-model",
        },
    )

    assert output == "retry-ok"
    assert attempts["count"] == 3
    assert sleep_calls == [1.0, 2.0]
    assert not curl_called


def test_build_curl_command_adds_ssl_no_revoke_on_windows(monkeypatch):
    role_llm = _load_role_llm_module()

    monkeypatch.setattr(role_llm.os, "name", "nt", raising=False)

    command = role_llm._build_curl_command(
        "https://example.test/v1/chat/completions",
        "task-key",
        "C:\\temp\\payload.json",
    )

    assert "--ssl-no-revoke" in command


@pytest.mark.parametrize(
    ("relative_path", "class_name", "module_name"),
    [
        ("tools/cli_invoke.py", "CliInvokeTool", "test_kit.tools.cli_invoke_test"),
        ("tools/provider_select.py", "ProviderSelectTool", "test_kit.tools.provider_select_test"),
        ("tools/result_feedback.py", "ResultFeedbackTool", "test_kit.tools.result_feedback_test"),
        ("tools/lab_report.py", "LabReportTool", "test_kit.tools.lab_report_test"),
    ],
)
def test_custom_tools_keep_base_config(relative_path: str, class_name: str, module_name: str):
    module = _load_module(TEST_KIT_DIR / relative_path, module_name)
    tool_cls = getattr(module, class_name)

    tool = tool_cls()

    assert hasattr(tool, "config")
    assert tool.config is not None


def test_cli_runtime_command_probe_accepts_provider_detect_cmd_with_args():
    module = _load_module(CLI_RUNTIME_PATH, "test_kit.cli_runtime_test")

    assert module._is_command_available("python --version") is True


def test_cli_runtime_command_probe_rejects_missing_provider_detect_cmd_with_args():
    module = _load_module(CLI_RUNTIME_PATH, "test_kit.cli_runtime_test_missing")

    assert module._is_command_available("definitely-missing-provider-probe --version") is False


def test_sync_script_writes_missing_tool_defaults_without_overwriting_existing_values(tmp_path: Path):
    module = _load_module(SYNC_SCRIPT_PATH, "test_kit.sync_test_kit_module_configs_test")
    config_path = tmp_path / "config.yaml"
    cli_invoke_module = (TEST_KIT_DIR / "tools" / "cli_invoke.py").resolve()
    result_feedback_module = (TEST_KIT_DIR / "tools" / "result_feedback.py").resolve()
    config_path.write_text(
        yaml.safe_dump(
            {
                "name": "tmp-creature",
                "tools": [
                    {
                        "name": "cli_invoke",
                        "type": "custom",
                        "module": str(cli_invoke_module),
                        "class": "CliInvokeTool",
                        "timeout_s": 15,
                    },
                    {
                        "name": "result_feedback",
                        "type": "custom",
                        "module": str(result_feedback_module),
                        "class": "ResultFeedbackTool",
                    },
                ],
            },
            allow_unicode=False,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    summary = module._sync_config_file(config_path)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    cli_invoke = payload["tools"][0]
    result_feedback = payload["tools"][1]

    assert summary["changed"] is True
    assert "cli_invoke" in summary["changed_tools"]
    assert "result_feedback" in summary["changed_tools"]
    assert cli_invoke["timeout_s"] == 15
    assert cli_invoke["provider_name"] == "cli-anything"
    assert cli_invoke["token_budget_mode"] == "silent"
    assert cli_invoke["provider_detect_cmd"] == ""
    assert result_feedback["agent_format"] == "json"
