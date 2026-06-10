from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def main() -> None:
    manifest = load_yaml(ROOT / "kohaku.yaml")
    manifest_skills = {entry["name"]: entry["path"] for entry in manifest.get("skills", [])}
    expected_skills = {
        "autonomous-cli-builder": "skills/autonomous-cli-builder/SKILL.md",
        "opencli-autonomous-builder": "skills/opencli-autonomous-builder/SKILL.md",
        "provider-aware-cli-builder": "skills/provider-aware-cli-builder/SKILL.md",
    }
    assert manifest_skills == expected_skills, manifest_skills

    for rel_path in expected_skills.values():
        assert (ROOT / rel_path).is_file(), rel_path

    lab_runner = load_yaml(ROOT / "creatures" / "lab-runner" / "config.yaml")
    assert lab_runner.get("skills") == ["provider-aware-cli-builder"], lab_runner.get("skills")

    terrarium = load_yaml(ROOT / "terrariums" / "lab-smoke" / "terrarium.yaml")
    for channel_name, channel_config in terrarium.get("terrarium", {}).get("channels", {}).items():
        assert "type" not in channel_config, f"{channel_name} still declares type"

    policy_root = ROOT / "skill-policies" / "creature-creation"
    assert (policy_root / "attachment-policy.yaml").is_file()
    assert (policy_root / "catalog.yaml").is_file()
    assert (policy_root / "README.md").is_file()

    print("T30-T32 verification passed")


if __name__ == "__main__":
    main()
