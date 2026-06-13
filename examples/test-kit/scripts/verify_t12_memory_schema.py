from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


EXPECTED_LAYERS = {
    "user-preferences": "user",
    "project-rules": "project",
    "workspace-assets": "workspace",
    "task-archives": "session",
    "transient-context": "session",
}

EXPECTED_SOURCES = {
    "user",
    "session",
    "tool",
    "file",
    "mcp",
    "web",
    "inference",
    "curator",
}

REQUIRED_RECORD_FIELDS = {
    "id",
    "layer",
    "scope",
    "title",
    "content",
    "source",
    "source_ref",
    "confidence",
    "retention",
    "dedupe_key",
    "created_at",
    "updated_at",
    "status",
}


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
    parser = argparse.ArgumentParser(description="Verify T12 memory schema.")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[3]),
        help="Repository root containing examples/test-kit/.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve()
    schema_path = repo_root / "examples" / "test-kit" / "memory-schema" / "schema.yaml"
    schema = load_yaml(schema_path)

    check(schema.get("version") == 1, "schema version must be 1")
    check(
        schema.get("status") == "design-contract",
        "schema status must be design-contract",
    )

    boundaries = schema.get("identity_boundaries")
    check(isinstance(boundaries, dict), "identity_boundaries must be declared")
    for scope in ("user", "project", "workspace", "session"):
        check(scope in boundaries, f"missing identity boundary: {scope}")
        allowed_layers = boundaries[scope].get("allowed_layers")
        check(
            isinstance(allowed_layers, list), f"{scope} allowed_layers must be a list"
        )

    storage_layout = schema.get("storage_layout")
    check(isinstance(storage_layout, dict), "storage_layout must be declared")
    storage_layers = storage_layout.get("layers")
    check(isinstance(storage_layers, dict), "storage_layout.layers must be declared")
    check(
        set(EXPECTED_LAYERS).issubset(storage_layers),
        f"missing storage layers: {set(EXPECTED_LAYERS) - set(storage_layers)}",
    )

    record_contract = schema.get("record_contract")
    check(isinstance(record_contract, dict), "record_contract must be declared")
    required_fields = set(record_contract.get("required_fields") or [])
    check(
        REQUIRED_RECORD_FIELDS.issubset(required_fields),
        f"record contract missing: {REQUIRED_RECORD_FIELDS - required_fields}",
    )

    layers = schema.get("layers")
    check(isinstance(layers, list), "layers must be declared")
    layer_map = {
        layer.get("name"): layer for layer in layers if isinstance(layer, dict)
    }
    check(
        set(EXPECTED_LAYERS).issubset(layer_map),
        f"missing layers: {set(EXPECTED_LAYERS) - set(layer_map)}",
    )
    for layer_name, expected_scope in EXPECTED_LAYERS.items():
        layer = layer_map[layer_name]
        check(layer.get("scope") == expected_scope, f"{layer_name} has wrong scope")
        check(layer.get("storage_path"), f"{layer_name} must declare storage_path")
        check(layer.get("default_retention"), f"{layer_name} must declare retention")
        check(
            isinstance(layer.get("allowed_sources"), list) and layer["allowed_sources"],
            f"{layer_name} must declare allowed_sources",
        )
        check(
            set(layer["allowed_sources"]).issubset(EXPECTED_SOURCES),
            f"{layer_name} has unknown allowed_sources",
        )
        check(
            isinstance(layer.get("min_confidence_to_write"), float),
            f"{layer_name} must declare min_confidence_to_write as float",
        )

    transient = layer_map["transient-context"]
    check(
        transient.get("expires_after"), "transient-context must declare expires_after"
    )
    promotion_targets = set(transient.get("promotion_targets") or [])
    check(
        promotion_targets == set(EXPECTED_LAYERS) - {"transient-context"},
        "transient-context must promote only to durable layers",
    )

    dedupe = schema.get("dedupe_policy")
    check(isinstance(dedupe, dict), "dedupe_policy must be declared")
    check(
        dedupe.get("key_fields") == ["layer", "scope", "dedupe_key"],
        "dedupe key must be layer + scope + dedupe_key",
    )

    retention = schema.get("retention_policy")
    check(isinstance(retention, dict), "retention_policy must be declared")
    for policy_name in (
        "permanent",
        "until-changed",
        "project-lifetime",
        "task-lifetime",
        "ephemeral",
    ):
        check(policy_name in retention, f"missing retention policy: {policy_name}")

    source_policy = schema.get("source_policy")
    check(isinstance(source_policy, dict), "source_policy must be declared")
    check(
        EXPECTED_SOURCES.issubset(source_policy),
        f"missing source policy: {EXPECTED_SOURCES - set(source_policy)}",
    )

    docs_path = repo_root / "docs" / "zh-CN" / "dev" / "t12-memory-schema.md"
    check(docs_path.is_file(), "T12 memory schema doc is missing")

    report = {
        "status": "PASS",
        "schema": str(schema_path.relative_to(repo_root)),
        "layers": sorted(EXPECTED_LAYERS),
        "scopes": sorted(boundaries),
        "required_fields": sorted(REQUIRED_RECORD_FIELDS),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
