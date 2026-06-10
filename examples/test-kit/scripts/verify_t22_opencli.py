from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_adapters(path: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    section: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if line.startswith("## "):
            section = line.removeprefix("## ").strip()
            continue
        if not section or not line.startswith("| **["):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        name_cell = cells[0]
        if "](" not in name_cell:
            continue
        display_name = name_cell.split("[", 1)[1].split("]", 1)[0].strip()
        commands_cell = cells[1]
        mode = cells[2]
        target_type = "browser" if section == "Browser Adapters" else "public_api"
        if section == "Desktop Adapters":
            target_type = "desktop"
            commands_cell = cells[2]
            mode = "Desktop"
        commands = []
        rest = commands_cell
        while "`" in rest:
            try:
                _, after = rest.split("`", 1)
                command, rest = after.split("`", 1)
                commands.append(command)
            except ValueError:
                break
        results.append(
            {
                "name": display_name.lower(),
                "section": section,
                "target_type": target_type,
                "mode": mode,
                "commands": commands,
                "_source_type": "adapter",
            }
        )
    return results


def classify_entry(item: dict[str, Any], provider_spec: dict[str, Any]) -> dict[str, Any]:
    name = str(item.get("name", "")).strip().lower()
    section = str(item.get("section", "")).strip()
    mode = str(item.get("mode", "")).strip()
    source_type = item.get("_source_type")

    for override in provider_spec.get("entry_overrides") or []:
        names = [str(v).strip().lower() for v in (override.get("names") or [])]
        if name in names:
            return {
                "capability": override.get("capability"),
                "preferred": bool(override.get("preferred", True)),
                "reason": f"name override:{name}",
            }

    for rule in provider_spec.get("capability_rules") or []:
        if source_type == "external" and rule.get("source") == "external-clis":
            return {
                "capability": rule.get("capability"),
                "preferred": bool(rule.get("preferred", True)),
                "reason": "source rule:external-clis",
            }
        if section and rule.get("section") == section:
            mode_contains = rule.get("mode_contains") or []
            if mode_contains and not any(token in mode for token in mode_contains):
                continue
            return {
                "capability": rule.get("capability"),
                "preferred": bool(rule.get("preferred", True)),
                "reason": f"section rule:{section}",
            }

    return {"capability": "unmapped", "preferred": False, "reason": "unmapped"}


def build_report(provider_spec: dict[str, Any], adapters: list[dict[str, Any]], external_clis: list[dict[str, Any]]) -> dict[str, Any]:
    browser_targets = [item for item in adapters if item["target_type"] == "browser"]
    public_targets = [item for item in adapters if item["target_type"] == "public_api"]
    desktop_targets = [item for item in adapters if item["target_type"] == "desktop"]
    all_targets = adapters + external_clis

    unmapped: list[str] = []
    preferred_external = 0
    browser_preferred = 0
    desktop_preferred = 0
    public_preferred = 0

    for item in all_targets:
        classification = classify_entry(item, provider_spec)
        if classification["capability"] == "unmapped":
            unmapped.append(str(item.get("name", "")))
        if item.get("_source_type") == "external" and classification["preferred"]:
            preferred_external += 1
        if item.get("target_type") == "browser" and classification["preferred"]:
            browser_preferred += 1
        if item.get("target_type") == "desktop" and classification["preferred"]:
            desktop_preferred += 1
        if item.get("target_type") == "public_api" and classification["preferred"]:
            public_preferred += 1

    status = "PASS"
    if unmapped:
        status = "FAIL"
    if not browser_targets or not public_targets or not desktop_targets or not external_clis:
        status = "FAIL"
    if preferred_external != 0:
        status = "FAIL"
    if browser_preferred == 0 or public_preferred == 0 or desktop_preferred == 0:
        status = "FAIL"

    return {
        "status": status,
        "browser_count": len(browser_targets),
        "public_api_count": len(public_targets),
        "desktop_count": len(desktop_targets),
        "external_count": len(external_clis),
        "unmapped_count": len(unmapped),
        "preferred_external_count": preferred_external,
        "preferred_browser_count": browser_preferred,
        "preferred_public_api_count": public_preferred,
        "preferred_desktop_count": desktop_preferred,
        "unmapped_names": unmapped[:20],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify T22 OpenCLI provider mapping.")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[3]),
        help="Repository root containing OpenCLI/ and examples/test-kit/.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve()
    provider_spec = load_yaml(repo_root / "examples" / "test-kit" / "providers" / "opencli.yaml")
    adapters = load_adapters(repo_root / "OpenCLI" / "docs" / "adapters" / "index.md")
    external_clis = load_yaml(repo_root / "OpenCLI" / "src" / "external-clis.yaml") or []
    for item in external_clis:
        if isinstance(item, dict):
            item["_source_type"] = "external"

    report = build_report(provider_spec, adapters, [item for item in external_clis if isinstance(item, dict)])

    print(f"status: {report['status']}")
    print(f"browser_count: {report['browser_count']}")
    print(f"public_api_count: {report['public_api_count']}")
    print(f"desktop_count: {report['desktop_count']}")
    print(f"external_count: {report['external_count']}")
    print(f"unmapped_count: {report['unmapped_count']}")
    print(f"preferred_external_count: {report['preferred_external_count']}")
    print(f"preferred_browser_count: {report['preferred_browser_count']}")
    print(f"preferred_public_api_count: {report['preferred_public_api_count']}")
    print(f"preferred_desktop_count: {report['preferred_desktop_count']}")
    if report["unmapped_names"]:
        print("unmapped_names:")
        for name in report["unmapped_names"]:
            print(f"  - {name}")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
