from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def main() -> None:
    manifest = load_yaml(ROOT / "kohaku.yaml")
    terrariums = manifest.get("terrariums", [])
    terrarium_names = [entry["name"] if isinstance(entry, dict) else entry for entry in terrariums]
    assert "task-team-minimal" in terrarium_names, terrarium_names

    recipe_path = ROOT / "terrariums" / "task-team-minimal" / "terrarium.yaml"
    assert recipe_path.is_file(), recipe_path
    recipe = load_yaml(recipe_path).get("terrarium", {})
    assert recipe.get("name") == "task-team-minimal"

    root_cfg = recipe.get("root", {})
    assert root_cfg.get("name") == "root"
    assert root_cfg.get("base_config") == "../../creatures/root-privileged/"
    assert root_cfg.get("controller", {}).get("model") == "${TASK_TEAM_MODEL:gemini-3-flash-preview}"

    creatures = {entry["name"]: entry for entry in recipe.get("creatures", [])}
    assert set(creatures) == {"coordinator", "worker", "critic"}, set(creatures)

    assert creatures["coordinator"].get("output_wiring") == [{"to": "worker"}]
    assert creatures["worker"].get("output_wiring") == [{"to": "critic"}]
    assert creatures["critic"].get("output_wiring") == [{"to": "root"}]

    for prompt_name in ["root", "coordinator", "worker", "critic"]:
        prompt_path = ROOT / "terrariums" / "task-team-minimal" / "prompts" / f"{prompt_name}.md"
        assert prompt_path.is_file(), prompt_path

    worker_prompt = (ROOT / "terrariums" / "task-team-minimal" / "prompts" / "worker.md").read_text(
        encoding="utf-8"
    )
    for snippet in [
        "execution_packet",
        "cli_invoke",
        "curl.exe",
        "stock snapshot request",
    ]:
        assert snippet in worker_prompt, snippet

    print("T8 task-team-minimal verification passed")


if __name__ == "__main__":
    main()
