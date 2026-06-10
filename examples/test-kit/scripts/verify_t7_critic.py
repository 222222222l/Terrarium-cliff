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
    creature_names = [
        entry["name"] if isinstance(entry, dict) else entry for entry in creatures
    ]
    assert "critic" in creature_names, creature_names

    config_path = ROOT / "creatures" / "critic" / "config.yaml"
    prompt_path = ROOT / "creatures" / "critic" / "prompts" / "system.md"
    assert config_path.is_file(), config_path
    assert prompt_path.is_file(), prompt_path

    config = load_yaml(config_path)
    controller = config.get("controller", {})
    assert controller.get("model") == "${CRITIC_LLM_MODEL:deepseek/deepseek-chat-v3}"
    assert controller.get("temperature") == 0.1
    assert controller.get("base_url") == "https://openrouter.ai/api/v1"
    assert config.get("system_prompt_file") == "prompts/system.md"

    tool_names = [tool["name"] for tool in config.get("tools", [])]
    assert tool_names == [
        "read",
        "glob",
        "grep",
        "json_read",
        "scratchpad",
        "think",
        "ask_user",
        "info",
        "stop_task",
        "result_feedback",
        "lab_report",
    ], tool_names

    prompt_text = prompt_path.read_text(encoding="utf-8")
    for required_snippet in [
        "shared_context_packet",
        "Output exactly one fenced YAML block named `review_result`",
        "include unsupported claims or freshness gaps here when relevant",
        "explicitly lower confidence instead of inventing missing history.",
        "Borrow AutoGen's reflection protocol idea",
        "route_to",
    ]:
        assert required_snippet in prompt_text, required_snippet

    print("T7 critic verification passed")


if __name__ == "__main__":
    main()
