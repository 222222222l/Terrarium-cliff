from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "examples"
    / "test-kit"
    / "scripts"
    / "run_t9_t10_long_protocol_demo.py"
)


def _load_demo_module():
    module_name = "test_kit.run_t9_t10_long_protocol_demo_test"
    spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_extract_yaml_block_accepts_fenced_yaml():
    module = _load_demo_module()

    payload, block = module._extract_yaml_block(
        "```yaml\ntask_card:\n  goal: keep semantics\n  constraints:\n    - preserve evidence\n```"
    )

    assert payload["goal"] == "keep semantics"
    assert payload["constraints"] == ["preserve evidence"]
    assert block.startswith("task_card:")


def test_extract_yaml_block_accepts_named_fence_label():
    module = _load_demo_module()

    payload, block = module._extract_yaml_block(
        "```task_card\n"
        "task_id: keep_named_fence\n"
        "goal: accept custom fence labels\n"
        "```\n"
    )

    assert payload["task_id"] == "keep_named_fence"
    assert payload["goal"] == "accept custom fence labels"
    assert block.startswith("task_id:")


def test_extract_yaml_block_accepts_quad_backtick_named_fence_label():
    module = _load_demo_module()

    payload, block = module._extract_yaml_block(
        "````task_card\n"
        "task_id: keep_quad_fence\n"
        "goal: accept four backticks\n"
        "````\n"
    )

    assert payload["task_id"] == "keep_quad_fence"
    assert payload["goal"] == "accept four backticks"
    assert block.startswith("task_id:")


def test_extract_yaml_block_accepts_unclosed_opening_fence():
    module = _load_demo_module()

    payload, block = module._extract_yaml_block("```yaml\ntask_card:\n  goal: survive missing closing fence")

    assert payload["goal"] == "survive missing closing fence"
    assert block.startswith("task_card:")


def test_extract_yaml_block_strips_output_wrappers():
    module = _load_demo_module()

    payload, _ = module._extract_yaml_block(
        "[output_text]\n```yaml\nreview_result:\n  status: pass\n  confidence: high\n```\n[/output_text]"
    )

    assert payload["status"] == "pass"
    assert payload["confidence"] == "high"


def test_extract_yaml_block_raises_readable_error_for_invalid_yaml():
    module = _load_demo_module()

    with pytest.raises(RuntimeError, match="Unable to parse YAML block from role output"):
        module._extract_yaml_block("```yaml\n: definitely not yaml\n```")


def test_extract_yaml_block_recovers_from_truncated_tail_key():
    module = _load_demo_module()

    payload, block = module._extract_yaml_block(
        "```yaml\n"
        "task_card:\n"
        "  task_id: market_snapshot_600519\n"
        "  goal: Fetch and compare 600519 quote data against 000001 via public HTTP.\n"
        "  task_kind: service_cli_task\n"
        "  preferred\n"
    )

    assert payload["task_id"] == "market_snapshot_600519"
    assert payload["goal"].startswith("Fetch and compare 600519")
    assert payload["task_kind"] == "service_cli_task"
    assert "preferred" not in block


def test_score_handoff_marks_truncated_payload_as_incomplete():
    module = _load_demo_module()

    score = module._score_handoff(
        {
            "task_id": "market_snapshot_600519",
            "goal": "Create a market snapshot for stock 600519",
        }
    )

    assert score["is_structurally_complete"] is False
    assert score["missing_required_fields"] == [
        "deliverable",
        "task_kind",
        "preferred_provider",
    ]
    assert score["is_hard_fail"] is True


def test_score_handoff_marks_compact_complete_payload_as_complete():
    module = _load_demo_module()

    score = module._score_handoff(
        {
            "task_id": "market_snapshot_600519",
            "goal": "Generate a market snapshot for stock 600519 compared against 000001.",
            "deliverable": "Quote-based snapshot with benchmark comparison, one risk caveat, and one next-step question.",
            "task_kind": "service_cli_task",
            "preferred_provider": "cli-anything",
            "open_questions": [
                "Should comparison use latest quote or previous close?",
            ],
        }
    )

    assert score["is_structurally_complete"] is True
    assert score["missing_required_fields"] == []
    assert score["is_hard_fail"] is False


def test_score_review_marks_truncated_payload_as_incomplete():
    module = _load_demo_module()

    score = module._score_review(
        {
            "status": "revise",
            "context_basis": "compressed_context",
            "requirements_covered": ["Current snapshot for stock 600519 fetched"],
        }
    )

    assert score["is_structurally_complete"] is False
    assert score["missing_required_fields"] == [
        "missing_evidence",
        "required_changes",
        "route_to",
        "confidence",
    ]


def test_score_review_marks_compact_complete_payload_as_complete():
    module = _load_demo_module()

    score = module._score_review(
        {
            "status": "revise",
            "context_basis": "compressed_context",
            "requirements_covered": ["Current snapshot for stock 600519 fetched"],
            "missing_evidence": [
                "Benchmark quote for 000001 is missing",
                "Freshness basis for the comparison is missing",
            ],
            "required_changes": [
                "Fetch 000001 before claiming outperformance",
                "Remove unsupported buy/fundamental claims",
            ],
            "route_to": "worker-base",
            "confidence": "medium",
        }
    )

    assert score["is_structurally_complete"] is True
    assert score["missing_required_fields"] == []
