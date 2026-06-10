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
    assert "root-privileged" in creature_names, creature_names

    config_path = ROOT / "creatures" / "root-privileged" / "config.yaml"
    prompt_path = ROOT / "creatures" / "root-privileged" / "prompts" / "system.md"
    assert config_path.is_file(), config_path
    assert prompt_path.is_file(), prompt_path

    config = load_yaml(config_path)
    assert config.get("system_prompt_file") == "prompts/system.md"

    tool_names = [tool["name"] for tool in config.get("tools", [])]
    assert tool_names == ["scratchpad", "think", "ask_user", "info", "stop_task", "lab_report"], tool_names

    subagent_names = [subagent["name"] for subagent in config.get("subagents", [])]
    assert subagent_names == ["plan", "summarize"], subagent_names

    prompt_text = prompt_path.read_text(encoding="utf-8")
    for required_snippet in [
        "control-plane creature",
        "Do not do worker work yourself.",
        "Prefer `group_status` first.",
        "Do not spawn another privileged node unless the user explicitly asks.",
    ]:
        assert required_snippet in prompt_text, required_snippet

    print("T4 root-privileged verification passed")


if __name__ == "__main__":
    main()
