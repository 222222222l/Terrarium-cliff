from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def main() -> None:
    manifest = load_yaml(ROOT / "kohaku.yaml")

    skills = {
        entry["name"]: entry
        for entry in manifest.get("skills", [])
        if isinstance(entry, dict)
    }
    assert "memory-curation" in skills, sorted(skills)
    assert skills["memory-curation"]["path"] == "skills/memory-curation/SKILL.md"

    creatures = [
        entry["name"] if isinstance(entry, dict) else entry
        for entry in manifest.get("creatures", [])
    ]
    assert "curator" in creatures, creatures

    terrariums = [
        entry["name"] if isinstance(entry, dict) else entry
        for entry in manifest.get("terrariums", [])
    ]
    assert "task-team-learning" in terrariums, terrariums

    schema_path = ROOT / "memory-schema" / "schema.yaml"
    skill_path = ROOT / "skills" / "memory-curation" / "SKILL.md"
    curator_config_path = ROOT / "creatures" / "curator" / "config.yaml"
    curator_prompt_path = ROOT / "creatures" / "curator" / "prompts" / "system.md"
    learning_path = ROOT / "terrariums" / "task-team-learning" / "terrarium.yaml"
    for path in [
        schema_path,
        skill_path,
        curator_config_path,
        curator_prompt_path,
        learning_path,
    ]:
        assert path.is_file(), path

    curator_config = load_yaml(curator_config_path)
    assert curator_config.get("skills") == ["memory-curation"]
    assert (
        curator_config.get("memory", {}).get("schema")
        == "../../memory-schema/schema.yaml"
    )
    tool_names = [tool["name"] for tool in curator_config.get("tools", [])]
    for required_tool in [
        "read",
        "write",
        "edit",
        "grep",
        "json_read",
        "result_feedback",
    ]:
        assert required_tool in tool_names, required_tool

    prompt_text = curator_prompt_path.read_text(encoding="utf-8")
    for snippet in [
        "memory-curation",
        "schema.yaml",
        "source references",
        "confidence",
        "retention",
        "dedupe_key",
        "curation_result",
    ]:
        assert snippet in prompt_text, snippet

    skill_text = skill_path.read_text(encoding="utf-8")
    for snippet in [
        "examples/test-kit/memory-schema/schema.yaml",
        "user-preferences",
        "project-rules",
        "workspace-assets",
        "task-archives",
        "transient-context",
        "layer + scope + dedupe_key",
    ]:
        assert snippet in skill_text, snippet

    recipe = load_yaml(learning_path).get("terrarium", {})
    assert recipe.get("name") == "task-team-learning"
    creatures_by_name = {entry["name"]: entry for entry in recipe.get("creatures", [])}
    assert set(creatures_by_name) == {"coordinator", "worker", "critic", "curator"}
    assert creatures_by_name["coordinator"].get("output_wiring") == [{"to": "worker"}]
    assert creatures_by_name["worker"].get("output_wiring") == [{"to": "critic"}]
    assert creatures_by_name["critic"].get("output_wiring") == [
        {"to": "root"},
        {"to": "curator"},
    ]
    assert creatures_by_name["curator"].get("output_wiring") == [{"to": "root"}]

    for channel_config in recipe.get("channels", {}).values():
        assert "type" not in channel_config, channel_config

    for prompt_name in ["root", "coordinator", "worker", "critic", "curator"]:
        prompt_path = (
            ROOT / "terrariums" / "task-team-learning" / "prompts" / f"{prompt_name}.md"
        )
        assert prompt_path.is_file(), prompt_path

    print("T11-T14 memory learning verification passed")


if __name__ == "__main__":
    main()
