from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEST_KIT_ROOT = PROJECT_ROOT / "examples" / "test-kit"
KT_HOME = PROJECT_ROOT / ".tmp-kt-home"
os.environ.setdefault("KT_CONFIG_DIR", str(KT_HOME))
(KT_HOME / "logs").mkdir(parents=True, exist_ok=True)

from kohakuterrarium.skills.discovery import load_skill_from_path
from kohakuterrarium.skills.user_slash import build_user_skill_turn


COORDINATOR_SYSTEM = (
    TEST_KIT_ROOT / "creatures" / "coordinator" / "prompts" / "system.md"
).read_text(encoding="utf-8")
CRITIC_SYSTEM = (
    TEST_KIT_ROOT / "creatures" / "critic" / "prompts" / "system.md"
).read_text(encoding="utf-8")
STRUCTURED_HANDOFF_SKILL = TEST_KIT_ROOT / "skills" / "structured-handoff" / "SKILL.md"
REVIEW_PROTOCOL_SKILL = TEST_KIT_ROOT / "skills" / "review-protocol" / "SKILL.md"
HANDOFF_MAX_TOKENS = 2048


def _load_role_llm_helpers():
    try:
        from test_kit.role_llm import call_role_llm, resolve_role_llm_settings  # type: ignore

        return call_role_llm, resolve_role_llm_settings
    except Exception:
        module_path = TEST_KIT_ROOT / "test_kit" / "role_llm.py"
        module_name = "test_kit.role_llm"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load role_llm helper from {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module.call_role_llm, module.resolve_role_llm_settings


CALL_ROLE_LLM, RESOLVE_ROLE_LLM_SETTINGS = _load_role_llm_helpers()


def _load_skill(path: Path, origin: str) -> Any:
    skill = load_skill_from_path(path, origin=origin, default_name=path.parent.name)
    if skill is None:
        raise RuntimeError(f"Unable to load skill from {path}")
    return skill


def _strip_markdown_code_fence(text: str) -> str:
    stripped = text.strip()
    fenced_match = re.search(r"(`{3,})[^\r\n`]*[ \t]*\r?\n([\s\S]*?)\r?\n\1", stripped)
    if fenced_match:
        return fenced_match.group(2).strip()

    lines = stripped.splitlines()
    if lines and re.match(r"^`{3,}[^\r\n`]*\s*$", lines[0].strip()):
        lines = lines[1:]
    if lines and re.match(r"^`{3,}\s*$", lines[-1].strip()):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _safe_load_yaml_prefix(block: str) -> tuple[dict[str, Any] | Any, str]:
    try:
        return yaml.safe_load(block) or {}, block
    except yaml.YAMLError as exc:
        lines = block.splitlines()
        mark = getattr(exc, "problem_mark", None)
        if len(lines) < 2 or mark is None or mark.line < max(0, len(lines) - 2):
            raise

        # Recover from tail truncation like a dangling final key (`preferred`)
        # by dropping incomplete trailing lines until a valid YAML prefix remains.
        for end in range(len(lines) - 1, 0, -1):
            candidate = "\n".join(lines[:end]).rstrip()
            if not candidate:
                continue
            try:
                return yaml.safe_load(candidate) or {}, candidate
            except yaml.YAMLError:
                continue
        raise


def _extract_yaml_block(text: str) -> tuple[dict[str, Any], str]:
    cleaned = re.sub(r"\[/?output_[^\]]+\]", "", text)
    cleaned = re.sub(r"</?output_[^>]+>", "", cleaned)
    block = _strip_markdown_code_fence(cleaned)
    try:
        payload, block = _safe_load_yaml_prefix(block)
    except yaml.YAMLError as exc:
        raise RuntimeError(
            "Unable to parse YAML block from role output. "
            f"Candidate block: {block[:1200]!r}"
        ) from exc
    if isinstance(payload, dict) and len(payload) == 1:
        only_value = next(iter(payload.values()))
        if isinstance(only_value, dict):
            return only_value, block
    return payload if isinstance(payload, dict) else {"raw": payload}, block


def _serialize_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _count_keyword_buckets(text: str, buckets: dict[str, list[str]]) -> dict[str, bool]:
    haystack = text.lower()
    return {
        name: any(keyword.lower() in haystack for keyword in keywords)
        for name, keywords in buckets.items()
    }


def _score_handoff(payload: dict[str, Any]) -> dict[str, Any]:
    text = _serialize_payload(payload)
    coverage = _count_keyword_buckets(
        text,
        {
            "primary_symbol": ["600519"],
            "benchmark_symbol": ["000001"],
            "quote_url": ["qt.gtimg.cn", "quote_url"],
            "no_fabrication_constraint": [
                "fundamental",
                "earnings",
                "news",
                "fabricat",
            ],
            "comparison_deliverable": ["comparison", "benchmark", "relative"],
            "evidence_requirement": ["evidence", "raw quote", "result_path", "source"],
            "open_question": [
                "open_question",
                "benchmark window",
                "previous close",
                "intraday",
            ],
            "provider_choice": ["cli-anything"],
            "task_kind": ["service_cli_task"],
        },
    )
    required_fields = {
        "task_id": payload.get("task_id"),
        "goal": payload.get("goal"),
        "task_kind": payload.get("task_kind"),
        "preferred_provider": payload.get("preferred_provider"),
        "deliverable": payload.get("deliverable"),
        "open_questions": payload.get("open_questions", []),
    }
    missing_required_fields = [
        name
        for name, value in required_fields.items()
        if value in (None, "", []) and not (name == "open_questions" and value == [])
    ]
    return {
        "bucket_hits": coverage,
        "covered_bucket_count": sum(1 for value in coverage.values() if value),
        "total_bucket_count": len(coverage),
        "semantic_loss_count": sum(1 for value in coverage.values() if not value),
        "missing_required_fields": missing_required_fields,
        "is_structurally_complete": not missing_required_fields,
        "is_hard_fail": bool(missing_required_fields),
        "preferred_provider": payload.get("preferred_provider"),
        "task_kind": payload.get("task_kind"),
        "open_questions": payload.get("open_questions"),
    }


def _score_review(payload: dict[str, Any]) -> dict[str, Any]:
    text = _serialize_payload(payload)
    coverage = _count_keyword_buckets(
        text,
        {
            "benchmark_evidence_gap": ["000001", "benchmark", "comparison"],
            "unsupported_recommendation_risk": [
                "buy",
                "unsupported",
                "fundamental",
                "investment advice",
            ],
            "freshness_gap": ["stale", "freshness", "intraday", "latest"],
            "route_present": ["worker-base", "user", "root-privileged", "coordinator"],
            "required_change_present": [
                "required_changes",
                "fetch",
                "remove",
                "revise",
            ],
            "confidence_present": ["low", "medium", "high"],
        },
    )
    required_fields = {
        "status": payload.get("status"),
        "context_basis": payload.get("context_basis"),
        "requirements_covered": payload.get("requirements_covered"),
        "missing_evidence": payload.get("missing_evidence"),
        "required_changes": payload.get("required_changes"),
        "route_to": payload.get("route_to"),
        "confidence": payload.get("confidence"),
    }
    missing_required_fields = [
        name for name, value in required_fields.items() if value in (None, "", [])
    ]
    return {
        "bucket_hits": coverage,
        "covered_bucket_count": sum(1 for value in coverage.values() if value),
        "total_bucket_count": len(coverage),
        "feedback_gap_count": sum(1 for value in coverage.values() if not value),
        "missing_required_fields": missing_required_fields,
        "is_structurally_complete": not missing_required_fields,
        "status": payload.get("status"),
        "route_to": payload.get("route_to"),
        "confidence": payload.get("confidence"),
    }


def _handoff_request() -> str:
    return """
User goal:
Create a compact worker handoff for a market snapshot task on stock 600519.

Durable constraints:
- Use only public quote endpoints.
- Treat https://qt.gtimg.cn/q=sh600519 as the primary source.
- Compare against 000001 if the comparison basis can be stated honestly.
- Do not fabricate fundamentals, earnings, valuation, sector, or news claims not supported by quote data.
- Keep the execution path deterministic and cheap.
- The deliverable must include: current snapshot, benchmark comparison, one risk caveat, and one next-step question for the user.
- Evidence must preserve enough source detail that a reviewer can tell whether both instruments were actually fetched.

One-off context:
- The worker should prefer the smallest public HTTP GET path.
- The user is okay with a concise answer.
- If the benchmark window is unclear, surface that ambiguity instead of guessing.

Potential ambiguity:
- The user says "compare against the index" but only gives code 000001.
- The user did not say whether comparison means latest quote, previous close, or same-day move.

Please compile this into a worker-ready handoff.
""".strip()


def _review_request(task_card_block: str) -> str:
    return f"""
Original user goal:
Produce a quote-based snapshot for stock 600519, compare it against 000001, avoid unsupported fundamentals,
and include one risk caveat plus one next-step question.

Current task_card:
```yaml
{task_card_block}
```

Worker execution packet:
```yaml
execution_packet:
  provider_name: cli-anything
  capability: http_fetch
  fetched_symbols:
    - 600519
  command:
    - curl
    - https://qt.gtimg.cn/q=sh600519
  claims_made:
    - 600519 outperformed 000001 today
    - strong buy because the company has strong fundamentals
  evidence_paths:
    - .kohaku/cli-runs/demo-600519/result.json
  missing_artifacts:
    - benchmark quote for 000001
    - freshness note explaining whether the comparison is intraday or previous close
```

Review the result and decide whether it passes, should be revised, or should be escalated.
""".strip()


def _invoke(
    system_prompt: str, user_message: str, *, max_tokens: int
) -> tuple[str, dict[str, Any], str]:
    raw = CALL_ROLE_LLM(system_prompt, user_message, max_tokens=max_tokens)
    payload, block = _extract_yaml_block(raw)
    return raw, payload, block


def _run_handoff_case(skill_enabled: bool) -> dict[str, Any]:
    request = _handoff_request()
    if skill_enabled:
        skill = _load_skill(STRUCTURED_HANDOFF_SKILL, "package:test-kit")
        request = build_user_skill_turn(skill, request)
    raw, payload, block = _invoke(
        COORDINATOR_SYSTEM, request, max_tokens=HANDOFF_MAX_TOKENS
    )
    return {
        "raw_output": raw,
        "payload": payload,
        "yaml_block": block,
        "score": _score_handoff(payload),
    }


def _run_review_case(task_card_block: str, skill_enabled: bool) -> dict[str, Any]:
    request = _review_request(task_card_block)
    if skill_enabled:
        skill = _load_skill(REVIEW_PROTOCOL_SKILL, "package:test-kit")
        request = build_user_skill_turn(skill, request)
    raw, payload, block = _invoke(CRITIC_SYSTEM, request, max_tokens=1100)
    return {
        "raw_output": raw,
        "payload": payload,
        "yaml_block": block,
        "score": _score_review(payload),
    }


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# T9/T10 Long Protocol Demo",
        "",
        "## Handoff",
        "",
        f"- baseline covered buckets: {summary['handoff']['baseline']['score']['covered_bucket_count']} / {summary['handoff']['baseline']['score']['total_bucket_count']}",
        f"- skill covered buckets: {summary['handoff']['skill_guided']['score']['covered_bucket_count']} / {summary['handoff']['skill_guided']['score']['total_bucket_count']}",
        f"- baseline semantic loss count: {summary['handoff']['baseline']['score']['semantic_loss_count']}",
        f"- skill semantic loss count: {summary['handoff']['skill_guided']['score']['semantic_loss_count']}",
        f"- baseline structurally complete: {summary['handoff']['baseline']['score']['is_structurally_complete']}",
        f"- skill structurally complete: {summary['handoff']['skill_guided']['score']['is_structurally_complete']}",
        f"- baseline hard fail: {summary['handoff']['baseline']['score']['is_hard_fail']}",
        f"- skill hard fail: {summary['handoff']['skill_guided']['score']['is_hard_fail']}",
        f"- baseline missing required fields: {', '.join(summary['handoff']['baseline']['score']['missing_required_fields']) or 'none'}",
        f"- skill missing required fields: {', '.join(summary['handoff']['skill_guided']['score']['missing_required_fields']) or 'none'}",
        "",
        "## Review",
        "",
        f"- baseline covered buckets: {summary['review']['baseline']['score']['covered_bucket_count']} / {summary['review']['baseline']['score']['total_bucket_count']}",
        f"- skill covered buckets: {summary['review']['skill_guided']['score']['covered_bucket_count']} / {summary['review']['skill_guided']['score']['total_bucket_count']}",
        f"- baseline feedback gap count: {summary['review']['baseline']['score']['feedback_gap_count']}",
        f"- skill feedback gap count: {summary['review']['skill_guided']['score']['feedback_gap_count']}",
        f"- baseline structurally complete: {summary['review']['baseline']['score']['is_structurally_complete']}",
        f"- skill structurally complete: {summary['review']['skill_guided']['score']['is_structurally_complete']}",
        f"- baseline missing required fields: {', '.join(summary['review']['baseline']['score']['missing_required_fields']) or 'none'}",
        f"- skill missing required fields: {', '.join(summary['review']['skill_guided']['score']['missing_required_fields']) or 'none'}",
        "",
        "## Observed Outputs",
        "",
        "### Skill-Guided task_card",
        "",
        "```yaml",
        summary["handoff"]["skill_guided"]["yaml_block"],
        "```",
        "",
        "### Skill-Guided review_result",
        "",
        "```yaml",
        summary["review"]["skill_guided"]["yaml_block"],
        "```",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    RESOLVE_ROLE_LLM_SETTINGS(os.environ)
    output_path = Path(
        os.environ.get(
            "T9_T10_DEMO_OUTPUT_PATH",
            str(KT_HOME / "reports" / "t9-t10-long-protocol-demo.json"),
        )
    )
    report_path = Path(
        os.environ.get(
            "T9_T10_DEMO_REPORT_PATH",
            str(KT_HOME / "reports" / "t9-t10-long-protocol-demo.md"),
        )
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    baseline_handoff = _run_handoff_case(skill_enabled=False)
    skill_handoff = _run_handoff_case(skill_enabled=True)
    baseline_review = _run_review_case(skill_handoff["yaml_block"], skill_enabled=False)
    skill_review = _run_review_case(skill_handoff["yaml_block"], skill_enabled=True)

    summary = {
        "handoff": {
            "baseline": baseline_handoff,
            "skill_guided": skill_handoff,
            "semantic_loss_delta": baseline_handoff["score"]["semantic_loss_count"]
            - skill_handoff["score"]["semantic_loss_count"],
        },
        "review": {
            "baseline": baseline_review,
            "skill_guided": skill_review,
            "feedback_quality_delta": skill_review["score"]["covered_bucket_count"]
            - baseline_review["score"]["covered_bucket_count"],
        },
        "artifacts": {
            "summary_json": str(output_path),
            "report_markdown": str(report_path),
        },
    }

    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_report(report_path, summary)

    print(
        "[t9-t10-demo] handoff baseline="
        f"{baseline_handoff['score']['covered_bucket_count']}/{baseline_handoff['score']['total_bucket_count']} "
        "skill="
        f"{skill_handoff['score']['covered_bucket_count']}/{skill_handoff['score']['total_bucket_count']}"
    )
    print(
        "[t9-t10-demo] handoff structural baseline="
        f"{baseline_handoff['score']['is_structurally_complete']} "
        "skill="
        f"{skill_handoff['score']['is_structurally_complete']}"
    )
    print(
        "[t9-t10-demo] handoff gate baseline="
        f"{'FAIL' if baseline_handoff['score']['is_hard_fail'] else 'PASS'} "
        "skill="
        f"{'FAIL' if skill_handoff['score']['is_hard_fail'] else 'PASS'}"
    )
    print(
        "[t9-t10-demo] handoff missing fields baseline="
        f"{','.join(baseline_handoff['score']['missing_required_fields']) or 'none'} "
        "skill="
        f"{','.join(skill_handoff['score']['missing_required_fields']) or 'none'}"
    )
    print(
        "[t9-t10-demo] review baseline="
        f"{baseline_review['score']['covered_bucket_count']}/{baseline_review['score']['total_bucket_count']} "
        "skill="
        f"{skill_review['score']['covered_bucket_count']}/{skill_review['score']['total_bucket_count']}"
    )
    print(
        "[t9-t10-demo] review structural baseline="
        f"{baseline_review['score']['is_structurally_complete']} "
        "skill="
        f"{skill_review['score']['is_structurally_complete']}"
    )
    print(
        "[t9-t10-demo] review missing fields baseline="
        f"{','.join(baseline_review['score']['missing_required_fields']) or 'none'} "
        "skill="
        f"{','.join(skill_review['score']['missing_required_fields']) or 'none'}"
    )
    print(f"[t9-t10-demo] summary_json={output_path}")
    print(f"[t9-t10-demo] report_markdown={report_path}")
    print(
        "T9_T10_DEMO_SCORECARD="
        + json.dumps(
            {
                "handoff": {
                    "baseline": baseline_handoff["score"]["covered_bucket_count"],
                    "skill": skill_handoff["score"]["covered_bucket_count"],
                    "structural_baseline": baseline_handoff["score"][
                        "is_structurally_complete"
                    ],
                    "structural_skill": skill_handoff["score"][
                        "is_structurally_complete"
                    ],
                    "gate_baseline": (
                        "FAIL" if baseline_handoff["score"]["is_hard_fail"] else "PASS"
                    ),
                    "gate_skill": (
                        "FAIL" if skill_handoff["score"]["is_hard_fail"] else "PASS"
                    ),
                },
                "review": {
                    "baseline": baseline_review["score"]["covered_bucket_count"],
                    "skill": skill_review["score"]["covered_bucket_count"],
                    "structural_baseline": baseline_review["score"][
                        "is_structurally_complete"
                    ],
                    "structural_skill": skill_review["score"][
                        "is_structurally_complete"
                    ],
                },
            },
            ensure_ascii=False,
        )
    )
    print(f"T9_T10_DEMO_JSON={json.dumps(summary, ensure_ascii=False)}")
    if os.environ.get("T9_T10_DEMO_RAISE_SUMMARY", "").strip() in {"1", "true", "True"}:
        raise RuntimeError(
            f"T9_T10_DEMO_JSON={json.dumps(summary, ensure_ascii=False)}"
        )


if __name__ == "__main__":
    main()
