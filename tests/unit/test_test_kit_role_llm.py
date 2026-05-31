from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[3]
    / "examples"
    / "test-kit"
    / "test_kit"
    / "role_llm.py"
)
TEST_KIT_DIR = MODULE_PATH.parent
CLI_RUNTIME_PATH = TEST_KIT_DIR / "cli_runtime.py"


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
