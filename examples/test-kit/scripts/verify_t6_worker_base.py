from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def main() -> None:
    manifest = load_yaml(ROOT / "kohaku.yaml")
    creatures = manifest.get("creatures", [])
    creature_names = [entry["name"] if isinstance(entry, dict) else entry for entry in creatures]
    assert "worker-base" in creature_names, creature_names

    config_path = ROOT / "creatures" / "worker-base" / "config.yaml"
    prompt_path = ROOT / "creatures" / "worker-base" / "prompts" / "system.md"
    assert config_path.is_file(), config_path
    assert prompt_path.is_file(), prompt_path

    config = load_yaml(config_path)
    controller = config.get("controller", {})
    assert controller.get("model") == "${WORKER_LLM_MODEL:qwen3.5:9b}"
    assert controller.get("temperature") == 0.0
    assert controller.get("base_url") == "${WORKER_LLM_BASE_URL:http://127.0.0.1:11434/v1}"
    assert config.get("system_prompt_file") == "prompts/system.md"

    tool_names = [tool["name"] for tool in config.get("tools", [])]
    assert tool_names == [
        "read",
        "edit",
        "glob",
        "grep",
        "json_read",
        "cli_invoke",
        "result_feedback",
        "stop_task",
    ], tool_names
    assert len(tool_names) == 8

    prompt_text = prompt_path.read_text(encoding="utf-8")
    for required_snippet in [
        "optimized for small local models",
        "Prefer one tool call at a time.",
        "Prefer tokenized `cli_invoke` commands over shell-style free text.",
        "Use `token_budget_mode: silent` by default.",
        "The upstream handoff should contain a `task_card`",
        "Keep the tool count small enough for 8B-9B local models to stay reliable.",
    ]:
        assert required_snippet in prompt_text, required_snippet

    print("T6 worker-base verification passed")


if __name__ == "__main__":
    main()
