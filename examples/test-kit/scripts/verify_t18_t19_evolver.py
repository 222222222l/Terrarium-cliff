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
    assert "evolution-draft-protocol" in skills, sorted(skills)
    assert (
        skills["evolution-draft-protocol"]["path"]
        == "skills/evolution-draft-protocol/SKILL.md"
    )

    creatures = [
        entry["name"] if isinstance(entry, dict) else entry
        for entry in manifest.get("creatures", [])
    ]
    assert "evolver" in creatures, creatures

    schema_path = ROOT / "evolution-schema" / "draft-protocol.yaml"
    skill_path = ROOT / "skills" / "evolution-draft-protocol" / "SKILL.md"
    config_path = ROOT / "creatures" / "evolver" / "config.yaml"
    prompt_path = ROOT / "creatures" / "evolver" / "prompts" / "system.md"
    docs_path = ROOT.parents[1] / "docs" / "zh-CN" / "dev" / "t18-t19-evolver.md"
    for path in [schema_path, skill_path, config_path, prompt_path, docs_path]:
        assert path.is_file(), path

    schema = load_yaml(schema_path)
    required_fields = set(
        schema.get("proposal_contract", {}).get("required_fields", [])
    )
    for field in [
        "proposal_id",
        "proposal_type",
        "scope",
        "source_refs",
        "risk_level",
        "approval_required",
        "audit_required",
        "rollback_plan",
        "status",
    ]:
        assert field in required_fields, field
    assert schema.get("output_contract_name") == "evolution_proposal"

    config = load_yaml(config_path)
    assert config.get("skills") == ["evolution-draft-protocol"]
    tool_names = [tool["name"] for tool in config.get("tools", [])]
    assert "write" not in tool_names
    assert "edit" not in tool_names
    for required_tool in [
        "read",
        "glob",
        "grep",
        "json_read",
        "result_feedback",
        "lab_report",
    ]:
        assert required_tool in tool_names, required_tool

    prompt_text = prompt_path.read_text(encoding="utf-8")
    for snippet in [
        "draft-only",
        "Do not edit active files",
        "approval",
        "audit",
        "rollback",
        "evolution_proposal",
    ]:
        assert snippet in prompt_text, snippet

    print("T18-T19 evolver verification passed")


if __name__ == "__main__":
    main()
