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
    assert "coordinator" in creature_names, creature_names

    config_path = ROOT / "creatures" / "coordinator" / "config.yaml"
    prompt_path = ROOT / "creatures" / "coordinator" / "prompts" / "system.md"
    assert config_path.is_file(), config_path
    assert prompt_path.is_file(), prompt_path

    config = load_yaml(config_path)
    assert config.get("system_prompt_file") == "prompts/system.md"

    tool_names = [tool["name"] for tool in config.get("tools", [])]
    assert tool_names == [
        "scratchpad",
        "think",
        "info",
        "stop_task",
        "provider_select",
        "lab_report",
    ], tool_names

    subagent_names = [subagent["name"] for subagent in config.get("subagents", [])]
    assert subagent_names == ["plan", "explore", "summarize"], subagent_names

    prompt_text = prompt_path.read_text(encoding="utf-8")
    for required_snippet in [
        "task_card",
        "Do not execute the task yourself.",
        "Use `provider_select` only when provider choice is relevant.",
        "Avoid AutoGen-style turn churn",
        "preferred_provider",
        "artifact_expectation",
    ]:
        assert required_snippet in prompt_text, required_snippet

    print("T5 coordinator verification passed")


if __name__ == "__main__":
    main()
