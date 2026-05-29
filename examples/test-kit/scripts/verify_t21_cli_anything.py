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
        raise ValueError(f"Expected YAML object in {path}")
    return data


def load_registry(path: Path, source: str) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    result: list[dict[str, Any]] = []
    for item in payload.get("clis") or []:
        if isinstance(item, dict):
            entry = dict(item)
            entry["_registry_source"] = source
            result.append(entry)
    return result


def classify_entry(entry: dict[str, Any], provider_spec: dict[str, Any]) -> dict[str, Any]:
    name = str(entry.get("name", "")).strip().lower()
    category = str(entry.get("category", "")).strip().lower()

    for override in provider_spec.get("entry_overrides") or []:
        names = [str(item).strip().lower() for item in (override.get("names") or [])]
        if name in names:
            return {
                "capability": override.get("capability"),
                "preferred": bool(override.get("preferred", True)),
                "reason": f"name override:{name}",
            }

    for rule in provider_spec.get("capability_rules") or []:
        categories = [str(item).strip().lower() for item in (rule.get("categories") or [])]
        if category in categories:
            return {
                "capability": rule.get("capability"),
                "preferred": bool(rule.get("preferred", True)),
                "reason": f"category rule:{category}",
            }

    return {
        "capability": "unmapped",
        "preferred": False,
        "reason": f"unmapped category:{category or 'unknown'}",
    }


def build_report(
    provider_spec: dict[str, Any],
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    mapped = 0
    capability_counts: dict[str, int] = {}
    unmapped_names: list[str] = []
    browser_nonpreferred = 0

    for entry in entries:
        classification = classify_entry(entry, provider_spec)
        capability = str(classification["capability"])
        capability_counts[capability] = capability_counts.get(capability, 0) + 1
        if capability != "unmapped":
            mapped += 1
        else:
            unmapped_names.append(str(entry.get("name", "")))
        if capability == "browser_cli_task" and not classification["preferred"]:
            browser_nonpreferred += 1

    status = "PASS" if mapped == len(entries) and browser_nonpreferred >= 1 else "FAIL"
    return {
        "status": status,
        "provider_name": provider_spec.get("provider", {}).get("name"),
        "total_entries": len(entries),
        "mapped_entries": mapped,
        "unmapped_entries": len(unmapped_names),
        "browser_nonpreferred_entries": browser_nonpreferred,
        "capability_counts": capability_counts,
        "unmapped_cli_names": unmapped_names[:20],
        "sample_resolutions": [
            {
                "name": entry.get("name"),
                "category": entry.get("category"),
                "classification": classify_entry(entry, provider_spec),
            }
            for entry in entries[:5]
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify T21 CLI-Anything provider mapping.")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[3]),
        help="Repository root containing CLI-Anything/ and examples/test-kit/.",
    )
    parser.add_argument(
        "--include-public",
        action="store_true",
        help="Include public_registry.json in the verification run.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the report as JSON only.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve()
    provider_spec_path = repo_root / "examples" / "test-kit" / "providers" / "cli_anything.yaml"
    official_registry_path = repo_root / "CLI-Anything" / "registry.json"
    public_registry_path = repo_root / "CLI-Anything" / "public_registry.json"

    provider_spec = load_yaml(provider_spec_path)
    entries = load_registry(official_registry_path, "official")
    if args.include_public and public_registry_path.exists():
        entries.extend(load_registry(public_registry_path, "public"))

    report = build_report(provider_spec, entries)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"status: {report['status']}")
        print(f"provider: {report['provider_name']}")
        print(f"total_entries: {report['total_entries']}")
        print(f"mapped_entries: {report['mapped_entries']}")
        print(f"unmapped_entries: {report['unmapped_entries']}")
        print(f"browser_nonpreferred_entries: {report['browser_nonpreferred_entries']}")
        print("capability_counts:")
        for capability, count in sorted(report["capability_counts"].items()):
            print(f"  - {capability}: {count}")
        if report["unmapped_cli_names"]:
            print("unmapped_cli_names:")
            for name in report["unmapped_cli_names"]:
                print(f"  - {name}")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
