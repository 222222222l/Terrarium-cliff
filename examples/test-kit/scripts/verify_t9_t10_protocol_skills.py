from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def main() -> None:
    manifest = _load_yaml(ROOT / "kohaku.yaml")
    skills = {entry["name"]: entry for entry in manifest.get("skills", []) if isinstance(entry, dict)}
    assert "structured-handoff" in skills, sorted(skills)
    assert "review-protocol" in skills, sorted(skills)
    assert skills["structured-handoff"]["path"] == "skills/structured-handoff/SKILL.md"
    assert skills["review-protocol"]["path"] == "skills/review-protocol/SKILL.md"

    structured_skill = ROOT / "skills" / "structured-handoff" / "SKILL.md"
    review_skill = ROOT / "skills" / "review-protocol" / "SKILL.md"
    assert structured_skill.is_file(), structured_skill
    assert review_skill.is_file(), review_skill

    coordinator_config = _load_yaml(ROOT / "creatures" / "coordinator" / "config.yaml")
    critic_config = _load_yaml(ROOT / "creatures" / "critic" / "config.yaml")
    assert coordinator_config.get("skills") == ["structured-handoff"]
    assert critic_config.get("skills") == ["review-protocol"]

    coordinator_prompt = (ROOT / "creatures" / "coordinator" / "prompts" / "system.md").read_text(
        encoding="utf-8"
    )
    critic_prompt = (ROOT / "creatures" / "critic" / "prompts" / "system.md").read_text(encoding="utf-8")
    assert "`structured-handoff`" in coordinator_prompt
    assert "`review-protocol`" in critic_prompt

    demo_script = ROOT / "scripts" / "run_t9_t10_long_protocol_demo.py"
    assert demo_script.is_file(), demo_script
    print("T9/T10 protocol skill verification passed")


if __name__ == "__main__":
    main()
