from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise AssertionError(f"Expected YAML object in {path}")
    return data


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify T35 package and marketplace governance policy."
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[3]),
        help="Repository root containing examples/test-kit/.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve()
    package_root = repo_root / "examples" / "test-kit"
    manifest = load_yaml(package_root / "kohaku.yaml")
    distribution = manifest.get("distribution")
    check(isinstance(distribution, dict), "kohaku.yaml must declare distribution")
    check(
        distribution.get("lifecycle_stage") == "lab",
        "test-kit should remain a lab-stage package",
    )
    check(
        distribution.get("release_channel") == "experimental",
        "test-kit should use the experimental release channel",
    )
    check(
        distribution.get("marketplace_eligible") is False,
        "test-kit should not be marketplace eligible yet",
    )

    policy_rel = distribution.get("governance_policy")
    check(isinstance(policy_rel, str) and policy_rel, "governance_policy is required")
    policy_path = package_root / policy_rel
    check(policy_path.is_file(), f"governance policy is missing: {policy_rel}")
    policy = load_yaml(policy_path)
    check(policy.get("package") == manifest.get("name"), "policy package mismatch")

    tracks = policy.get("release_tracks")
    check(isinstance(tracks, list) and tracks, "release_tracks must be non-empty")
    tracks_by_name = {
        track.get("name"): track for track in tracks if isinstance(track, dict)
    }
    expected_tracks = {"local-dev", "private-release", "marketplace-candidate"}
    check(
        expected_tracks.issubset(tracks_by_name),
        f"missing release tracks: {expected_tracks - set(tracks_by_name)}",
    )
    for name in expected_tracks:
        track = tracks_by_name[name]
        check(track.get("install_spec"), f"{name} must declare install_spec")
        check(track.get("publish_gate"), f"{name} must declare publish_gate")
        rollback = track.get("rollback")
        check(isinstance(rollback, dict), f"{name} must declare rollback object")
        check(rollback.get("mode"), f"{name} rollback must declare mode")
        check(rollback.get("action"), f"{name} rollback must declare action")

    promotion_gates = policy.get("promotion_gates")
    check(isinstance(promotion_gates, dict), "promotion_gates must be declared")
    check(promotion_gates.get("lab_to_private"), "lab_to_private gate is required")
    check(
        promotion_gates.get("private_to_marketplace"),
        "private_to_marketplace gate is required",
    )

    version_policy = policy.get("version_policy")
    check(isinstance(version_policy, dict), "version_policy must be declared")
    check(version_policy.get("scheme") == "semver", "version scheme must be semver")
    check(
        str(manifest.get("version", "")).count(".") == 2,
        "manifest version should be MAJOR.MINOR.PATCH",
    )

    contract = policy.get("marketplace_entry_contract")
    check(isinstance(contract, dict), "marketplace_entry_contract must be declared")
    required_fields = set(contract.get("required_fields") or [])
    expected_fields = {
        "name",
        "repo",
        "description",
        "tags",
        "author",
        "license",
        "framework",
        "versions",
    }
    check(
        expected_fields.issubset(required_fields),
        f"marketplace contract missing: {expected_fields - required_fields}",
    )
    version_fields = set(contract.get("version_fields") or [])
    check(
        {"tag", "released", "framework", "yanked"}.issubset(version_fields),
        "marketplace version contract must include tag/released/framework/yanked",
    )

    docs_path = (
        repo_root / "docs" / "zh-CN" / "dev" / "t35-package-marketplace-governance.md"
    )
    check(docs_path.is_file(), "T35 governance doc is missing")

    report = {
        "status": "PASS",
        "package": manifest.get("name"),
        "distribution": {
            "lifecycle_stage": distribution.get("lifecycle_stage"),
            "release_channel": distribution.get("release_channel"),
            "marketplace_eligible": distribution.get("marketplace_eligible"),
        },
        "release_tracks": sorted(expected_tracks),
        "rollback_modes": {
            name: tracks_by_name[name]["rollback"]["mode"] for name in expected_tracks
        },
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
