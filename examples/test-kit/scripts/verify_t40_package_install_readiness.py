from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml


SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise AssertionError(f"Expected YAML object in {path}")
    return data


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def names_from_entries(entries: Any) -> list[str]:
    check(isinstance(entries, list), "manifest entries must be lists")
    names: list[str] = []
    for entry in entries:
        if isinstance(entry, str):
            name = entry
        elif isinstance(entry, dict):
            name = str(entry.get("name", "") or "").strip()
        else:
            raise AssertionError(f"unsupported manifest entry: {entry!r}")
        check(bool(name), f"manifest entry missing name: {entry!r}")
        names.append(name)
    return names


def relative_manifest_path(path_text: str, field_name: str) -> Path:
    check(path_text.strip() == path_text, f"{field_name} should not have padding")
    check(path_text, f"{field_name} is required")
    check("\\" not in path_text, f"{field_name} should use POSIX separators")
    path = Path(path_text)
    check(not path.is_absolute(), f"{field_name} should be relative")
    check(".." not in path.parts, f"{field_name} should not escape package root")
    return path


def module_to_path(module_name: str, field_name: str) -> Path:
    check(module_name.startswith("test_kit."), f"{field_name} must be in test_kit")
    check(
        "\\" not in module_name and "/" not in module_name,
        f"{field_name} is not a module path",
    )
    return Path(*module_name.split(".")).with_suffix(".py")


def verify_manifest_targets(
    package_root: Path, manifest: dict[str, Any]
) -> dict[str, list[str]]:
    resolved: dict[str, list[str]] = {
        "creatures": [],
        "terrariums": [],
        "skills": [],
        "tools": [],
        "plugins": [],
    }

    for name in names_from_entries(manifest.get("creatures")):
        path = package_root / "creatures" / name / "config.yaml"
        check(path.is_file(), f"creature config missing: {path}")
        resolved["creatures"].append(str(path.relative_to(package_root)))

    for name in names_from_entries(manifest.get("terrariums")):
        path = package_root / "terrariums" / name / "terrarium.yaml"
        check(path.is_file(), f"terrarium config missing: {path}")
        resolved["terrariums"].append(str(path.relative_to(package_root)))

    skills = manifest.get("skills")
    check(isinstance(skills, list) and skills, "manifest skills must be non-empty")
    for skill in skills:
        check(isinstance(skill, dict), f"skill entry must be an object: {skill!r}")
        name = str(skill.get("name", "") or "").strip()
        path = relative_manifest_path(
            str(skill.get("path", "") or ""), f"skill {name} path"
        )
        check((package_root / path).is_file(), f"skill path missing: {path}")
        check(path.name == "SKILL.md", f"skill path should point to SKILL.md: {path}")
        check(
            str(skill.get("description", "") or "").strip(),
            f"skill {name} needs description",
        )
        resolved["skills"].append(str(path))

    for section in ("tools", "plugins"):
        entries = manifest.get(section)
        check(
            isinstance(entries, list) and entries,
            f"manifest {section} must be non-empty",
        )
        for entry in entries:
            check(
                isinstance(entry, dict), f"{section} entry must be an object: {entry!r}"
            )
            name = str(entry.get("name", "") or "").strip()
            module_name = str(entry.get("module", "") or "").strip()
            class_name = str(entry.get("class", "") or "").strip()
            check(name, f"{section} entry missing name")
            check(class_name, f"{section} {name} missing class")
            module_path = module_to_path(module_name, f"{section} {name} module")
            check(
                (package_root / module_path).is_file(),
                f"{section} module missing: {module_path}",
            )
            resolved[section].append(str(module_path))

    return resolved


def verify_release_checklist(
    package_root: Path, checklist: dict[str, Any]
) -> dict[str, Any]:
    check(checklist.get("package") == "test-kit", "release checklist package mismatch")
    platforms = set(checklist.get("supported_platforms") or [])
    check(
        {"windows", "linux"}.issubset(platforms),
        "release checklist must support windows and linux",
    )

    required_verifiers = checklist.get("required_verifiers")
    check(
        isinstance(required_verifiers, list) and required_verifiers,
        "required_verifiers must be non-empty",
    )
    commands = [
        str(item.get("command", "") or "")
        for item in required_verifiers
        if isinstance(item, dict)
    ]
    check(
        any("verify_regression_suite.py --json" in command for command in commands),
        "release checklist must require default regression suite",
    )
    check(
        any(
            "verify_t39_linux_windows_compatibility.py" in command
            for command in commands
        ),
        "release checklist must require Linux / Windows compatibility gate",
    )

    required_fields = set(checklist.get("release_notes_required_fields") or [])
    expected_fields = {
        "package",
        "version",
        "release_track",
        "changed_creatures",
        "changed_terrariums",
        "changed_skills",
        "changed_tools",
        "changed_plugins",
        "changed_policies",
        "validation",
        "rollback_target",
        "known_limitations",
    }
    check(
        expected_fields.issubset(required_fields),
        f"release notes fields missing: {expected_fields - required_fields}",
    )

    blockers = set(checklist.get("private_release_blockers") or [])
    check(
        "unresolved manifest target" in blockers,
        "release blockers must include unresolved manifest targets",
    )
    check(
        "Linux / Windows compatibility gate failure" in blockers,
        "release blockers must include dual-platform gate failure",
    )
    return {
        "supported_platforms": sorted(platforms),
        "verifier_count": len(required_verifiers),
        "release_notes_fields": sorted(required_fields),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify T40 package install readiness."
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
    checklist = load_yaml(package_root / "release-checklist.yaml")

    check(manifest.get("name") == "test-kit", "manifest package name mismatch")
    check(
        SEMVER_PATTERN.match(str(manifest.get("version", "") or "")) is not None,
        "manifest version must be MAJOR.MINOR.PATCH",
    )
    distribution = manifest.get("distribution")
    check(isinstance(distribution, dict), "manifest distribution is required")
    check(
        distribution.get("governance_policy") == "release-policy.yaml",
        "manifest should point to release-policy.yaml",
    )
    check(
        (package_root / "release-policy.yaml").is_file(), "release-policy.yaml missing"
    )

    resolved = verify_manifest_targets(package_root, manifest)
    checklist_summary = verify_release_checklist(package_root, checklist)

    readme = (package_root / "README.md").read_text(encoding="utf-8")
    check(
        "kt install ./examples/test-kit -e" in readme,
        "README must document editable install",
    )
    check(
        "verify_regression_suite.py" in readme,
        "README must document the default regression suite",
    )

    docs_path = (
        repo_root / "docs" / "zh-CN" / "dev" / "t40-package-install-readiness.md"
    )
    check(docs_path.is_file(), "T40 install readiness doc is missing")

    report = {
        "status": "PASS",
        "package": manifest.get("name"),
        "version": manifest.get("version"),
        "resolved_counts": {key: len(value) for key, value in resolved.items()},
        "release_checklist": checklist_summary,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
