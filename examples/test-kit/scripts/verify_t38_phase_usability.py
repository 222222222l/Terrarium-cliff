from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise AssertionError(f"Expected YAML object in {path}")
    return data


def load_module(module_path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {module_name} from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def plugin_by_name(config: dict[str, Any], name: str) -> dict[str, Any]:
    plugins = config.get("plugins") or []
    for plugin in plugins:
        if isinstance(plugin, dict) and plugin.get("name") == name:
            return plugin
    raise AssertionError(f"Missing plugin: {name}")


def tool_by_name(config: dict[str, Any], name: str) -> dict[str, Any]:
    tools = config.get("tools") or []
    for tool in tools:
        if isinstance(tool, dict) and tool.get("name") == name:
            return tool
    raise AssertionError(f"Missing tool: {name}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify T38 phase usability readiness gates."
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[3]),
        help="Repository root containing examples/test-kit/.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve()
    script_root = repo_root / "examples" / "test-kit" / "scripts"
    test_kit_root = repo_root / "examples" / "test-kit"

    suite_module = load_module(
        script_root / "verify_regression_suite.py",
        "verify_regression_suite",
    )
    default_ids = [script.task_id for script in suite_module.DEFAULT_SCRIPTS]
    external_ids = [script.task_id for script in suite_module.EXTERNAL_SCRIPTS]
    required_default_ids = {
        "T4",
        "T8",
        "T11-T14",
        "T15",
        "T16",
        "T17",
        "T18-T19",
        "T23",
        "T24",
        "T25",
        "T33",
        "T35",
        "T38",
        "T39",
        "T40",
    }
    check(
        required_default_ids.issubset(default_ids),
        f"default regression suite missing: {required_default_ids - set(default_ids)}",
    )
    check("T21" not in default_ids, "external T21 must not run by default")
    check("T22" not in default_ids, "external T22 must not run by default")
    check(external_ids == ["T21", "T22"], "external suite should only contain T21/T22")

    role_llm = load_module(
        test_kit_root / "test_kit" / "role_llm.py",
        "test_kit.role_llm",
    )
    settings = role_llm.resolve_role_llm_settings(
        {
            "TASK_TEAM_BASE_URL": "https://api.example.test/v1/",
            "TASK_TEAM_API_KEY": "task-key",
            "TASK_TEAM_MODEL": "phase-smoke-model",
            "OPENROUTER_BASE_URL": "https://openrouter.example/v1",
            "OPENROUTER_API_KEY": "openrouter-key",
            "OPENROUTER_MODEL": "fallback-model",
        }
    )
    check(
        settings.base_url == "https://api.example.test/v1",
        "TASK_TEAM_BASE_URL should override OPENROUTER_BASE_URL and strip trailing slash",
    )
    check(
        settings.api_key == "task-key",
        "TASK_TEAM_API_KEY should override OPENROUTER_API_KEY",
    )
    check(
        settings.model == "phase-smoke-model",
        "TASK_TEAM_MODEL should override OPENROUTER_MODEL",
    )
    check(
        role_llm.DEFAULT_ROLE_MAX_ATTEMPTS >= 3,
        "role LLM smoke path should retry transient provider failures",
    )
    curl_command = role_llm._build_curl_command(
        "https://api.example.test/v1/chat/completions",
        "redacted-key",
        "payload.json",
    )
    if os.name == "nt":
        check(
            "--ssl-no-revoke" in curl_command,
            "Windows curl fallback should disable certificate revocation lookup",
        )
    else:
        check(curl_command[0] == "curl", "POSIX curl fallback should use curl")

    role_script = (script_root / "run_t8_role_direct.py").read_text(encoding="utf-8")
    for token in (
        "T8_ROLE",
        "T8_USER_INPUT",
        "T8_USER_INPUT_PATH",
        "T8_MAX_TOKENS",
        "CALL_ROLE_LLM",
    ):
        check(token in role_script, f"run_t8_role_direct.py missing {token}")
    check(
        "coordinator" in role_script
        and "critic" in role_script
        and "root" in role_script,
        "role direct smoke should cover coordinator/critic/root prompts",
    )

    worker_config = load_yaml(
        test_kit_root / "creatures" / "worker-base" / "config.yaml"
    )
    permgate = plugin_by_name(worker_config, "permgate")
    gated_tools = set((permgate.get("options") or {}).get("gated_tools") or [])
    check(
        {"edit", "cli_invoke"}.issubset(gated_tools),
        "worker full tool-chain smoke should remain approval-gated",
    )
    cli_invoke = tool_by_name(worker_config, "cli_invoke")
    check(
        cli_invoke.get("token_budget_mode") == "silent",
        "cli_invoke should keep silent execution mode for phase usability",
    )

    minimal_terrarium = load_yaml(
        test_kit_root / "terrariums" / "task-team-minimal" / "terrarium.yaml"
    )
    root_controller = minimal_terrarium["terrarium"]["root"]["controller"]
    check(
        root_controller.get("base_url")
        == "${TASK_TEAM_BASE_URL:https://openrouter.ai/api/v1}",
        "task-team-minimal should support TASK_TEAM_BASE_URL override",
    )
    check(
        root_controller.get("api_key_env") == "TASK_TEAM_API_KEY",
        "task-team-minimal should use TASK_TEAM_API_KEY",
    )
    check(
        root_controller.get("model") == "${TASK_TEAM_MODEL:gemini-3-flash-preview}",
        "task-team-minimal should support TASK_TEAM_MODEL override",
    )

    docs_path = (
        repo_root / "docs" / "zh-CN" / "dev" / "t38-phase-usability-validation.md"
    )
    check(docs_path.is_file(), "T38 phase usability doc is missing")

    report = {
        "status": "PASS",
        "default_suite": {
            "count": len(default_ids),
            "contains": sorted(required_default_ids),
            "external_optional": external_ids,
        },
        "role_llm": {
            "base_url_override": settings.base_url,
            "model_override": settings.model,
            "retries": role_llm.DEFAULT_ROLE_MAX_ATTEMPTS,
            "curl_binary": curl_command[0],
            "windows_curl_ssl_no_revoke": os.name != "nt"
            or "--ssl-no-revoke" in curl_command,
        },
        "live_smoke_entry": "examples/test-kit/scripts/run_t8_role_direct.py",
        "full_tool_chain_guard": {
            "worker_gated_tools": sorted(gated_tools),
            "cli_invoke_mode": cli_invoke.get("token_budget_mode"),
        },
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
