from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def load_provider_selection(repo_root: Path):
    module_path = repo_root / "examples" / "test-kit" / "test_kit" / "provider_selection.py"
    spec = importlib.util.spec_from_file_location("test_kit.provider_selection", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load provider_selection module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify T24 provider selection rules.")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[3]),
        help="Repository root containing examples/test-kit/.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve()
    module = load_provider_selection(repo_root)
    select_provider_for_task = module.select_provider_for_task

    cli_anything_case = select_provider_for_task(
        {
            "task_kind": "service_cli_task",
            "artifact_expectation": ["tmp/service.json"],
        },
        repo_root,
    )
    opencli_case = select_provider_for_task(
        {
            "access_mode": "browser",
            "needs_browser_session": True,
            "target_hint": "website",
        },
        repo_root,
    )
    overlap_case = select_provider_for_task(
        {
            "task_kind": "browser_public_task",
            "target_hint": "website",
        },
        repo_root,
    )
    explicit_case = select_provider_for_task(
        {
            "task_kind": "browser_public_task",
            "preferred_provider": "opencli",
        },
        repo_root,
    )

    check(cli_anything_case["decision_status"] == "selected", "service task should auto select")
    check(cli_anything_case["preferred_provider"] == "cli-anything", "service task should prefer cli-anything")
    check(opencli_case["decision_status"] == "selected", "browser session task should auto select")
    check(opencli_case["preferred_provider"] == "opencli", "browser session task should prefer opencli")
    check(overlap_case["decision_status"] == "needs_user_choice", "overlap case should return user choice")
    check(overlap_case["user_choice_required"] is True, "overlap case should require user choice")
    check(overlap_case["candidate_providers"] == ["cli-anything", "opencli"], "overlap candidates should include both providers")
    check(explicit_case["decision_status"] == "selected", "explicit preferred provider should be respected")
    check(explicit_case["preferred_provider"] == "opencli", "explicit preferred provider should win")

    report = {
        "status": "PASS",
        "service_case": {
            "decision_status": cli_anything_case["decision_status"],
            "preferred_provider": cli_anything_case["preferred_provider"],
        },
        "browser_session_case": {
            "decision_status": opencli_case["decision_status"],
            "preferred_provider": opencli_case["preferred_provider"],
        },
        "overlap_case": {
            "decision_status": overlap_case["decision_status"],
            "candidate_providers": overlap_case["candidate_providers"],
        },
        "explicit_case": {
            "decision_status": explicit_case["decision_status"],
            "preferred_provider": explicit_case["preferred_provider"],
        },
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
