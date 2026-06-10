from __future__ import annotations

from pathlib import Path

import yaml

from kohakuterrarium.skills.discovery import load_skill_from_path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_KIT_ROOT = PROJECT_ROOT / "examples" / "test-kit"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def test_test_kit_manifest_declares_t9_t10_skills():
    manifest = _load_yaml(TEST_KIT_ROOT / "kohaku.yaml")
    entries = {
        entry["name"]: entry
        for entry in manifest.get("skills", [])
        if isinstance(entry, dict)
    }

    assert entries["structured-handoff"]["path"] == "skills/structured-handoff/SKILL.md"
    assert entries["review-protocol"]["path"] == "skills/review-protocol/SKILL.md"


def test_test_kit_t9_t10_skill_docs_load_via_runtime_loader():
    structured = load_skill_from_path(
        TEST_KIT_ROOT / "skills" / "structured-handoff" / "SKILL.md",
        origin="package:test-kit",
        default_name="structured-handoff",
    )
    review = load_skill_from_path(
        TEST_KIT_ROOT / "skills" / "review-protocol" / "SKILL.md",
        origin="package:test-kit",
        default_name="review-protocol",
    )

    assert structured is not None
    assert structured.name == "structured-handoff"
    assert "Invoke When" in structured.body
    assert review is not None
    assert review.name == "review-protocol"
    assert "review_result" in review.body


def test_structured_handoff_skill_enforces_six_field_skeleton():
    skill_text = (TEST_KIT_ROOT / "skills" / "structured-handoff" / "SKILL.md").read_text(encoding="utf-8")

    assert "Output exactly one fenced block whose opening line is exactly ````task_card`." in skill_text
    assert "It must contain only these 6 fields in this exact order:" in skill_text
    assert "Use the fence label `task_card` instead of a nested `task_card:` wrapper key." in skill_text
    assert "Keep every field on exactly one physical line." in skill_text
    assert "Prefer the exact source anchor `qt.gtimg.cn`" in skill_text
    assert "Keep `goal` anchored to the smallest honest execution path" in skill_text
    assert "Keep `deliverable` anchored to the acceptance test" in skill_text
    assert "Keep `deliverable` as a short noun phrase" in skill_text
    assert "Keep `open_questions` to one short blocker when possible." in skill_text
    assert 'Encode `open_questions` on one line as `[]` or `["short blocking question"]`.' in skill_text
    assert "Do not add a nested `task_card:` wrapper key under the fence." in skill_text
    assert "Do not emit `constraints`, `inputs`, `evidence_needed`, or any extra field." in skill_text


def test_coordinator_and_critic_mount_protocol_skills():
    coordinator = _load_yaml(TEST_KIT_ROOT / "creatures" / "coordinator" / "config.yaml")
    critic = _load_yaml(TEST_KIT_ROOT / "creatures" / "critic" / "config.yaml")

    assert coordinator.get("skills") == ["structured-handoff"]
    assert critic.get("skills") == ["review-protocol"]


def test_coordinator_prompt_matches_t9_skeleton_contract():
    prompt_text = (TEST_KIT_ROOT / "creatures" / "coordinator" / "prompts" / "system.md").read_text(encoding="utf-8")

    assert "opening line is exactly ````task_card`" in prompt_text
    assert "Use the fence label `task_card` instead of a nested `task_card:` wrapper key." in prompt_text
    assert "Keep every field on exactly one physical line." in prompt_text
    assert "preserve quote-only, no-fabrication, or other worker-shaping limits" in prompt_text
    assert "prefer exact source anchors such as `qt.gtimg.cn`" in prompt_text
    assert "preserve evidence or fetch-proof language when reviewer verification matters" in prompt_text
    assert "keep it as a short noun phrase" in prompt_text
    assert "Keep `deliverable` shorter than `goal` when possible." in prompt_text
    assert "Keep `open_questions` to one short blocker when possible." in prompt_text
    assert 'Encode `open_questions` on one line as `[]` or `["short blocking question"]`.' in prompt_text
    assert "Do not add a nested `task_card:` wrapper key under the fence." in prompt_text
    assert "Do not emit `constraints`, `inputs`, `evidence_needed`, or any extra field." in prompt_text


def test_review_protocol_skill_stays_compact_for_injection():
    skill_text = (TEST_KIT_ROOT / "skills" / "review-protocol" / "SKILL.md").read_text(encoding="utf-8")

    assert "Output exactly one fenced YAML block named `review_result`" in skill_text
    assert "Only mark a requirement as covered if evidence supports it." in skill_text
    assert "Mention freshness gaps inside `missing_evidence`." in skill_text
    assert len(skill_text) < 2800
