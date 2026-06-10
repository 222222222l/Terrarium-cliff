---
name: "review-protocol"
description: "Reviews worker outputs into a stable review_result with explicit evidence gaps and next-step routing. Invoke when critic-style feedback must stay compact, typed, and reusable."
---

# Review Protocol

Use this skill when you must judge a worker result without letting the review
balloon into a long transcript.

## Invoke When

Use this skill when at least one of these is true:

1. A worker output must be accepted, revised, or rejected.
2. The review must survive another upstream handoff without replaying full logs.
3. Evidence is partial and confidence must be stated explicitly.
4. You need compact machine-readable feedback instead of free-form commentary.

## Core Contract

Output exactly one fenced YAML block named `review_result` with these 7 fields:

- `status`
- `context_basis`
- `requirements_covered`
- `missing_evidence`
- `required_changes`
- `route_to`
- `confidence`

## Content Rules

- `status`: `pass`, `revise`, or `fail`
- `context_basis`: `shared_context`, `compressed_context`, or `artifact_only`
- `requirements_covered`: only supported items; max 2 bullets
- `missing_evidence`: concrete proof gaps; max 3 bullets
- `required_changes`: smallest next-step changes; max 3 bullets
- `route_to`: `worker-base`, `coordinator`, `root-privileged`, or `user`
- `confidence`: `low`, `medium`, or `high`
- Only mark a requirement as covered if evidence supports it.
- Mention unsupported claims or policy violations inside `missing_evidence` or `required_changes`.
- Mention freshness gaps inside `missing_evidence`.

## Brevity Rules

- Do not include `risks`, `next_iteration_goal`, `root_feedback_summary`, `root_context_patch`, `user_interrupt_recommended`, or `user_interrupt_reason` unless the caller explicitly asks for extended review.
- Mention route intent only in `route_to`.
- Keep the whole YAML block under 18 lines when possible.

## Minimal Example

```yaml
review_result:
  status: revise
  context_basis: compressed_context
  requirements_covered:
    - README section was updated
  missing_evidence:
    - no proof that the quick-start example was re-run
    - benchmark comparison still lacks fresh evidence
  required_changes:
    - re-run the quick-start path and confirm the example command matches current docs
    - remove unsupported claims until evidence exists
  route_to: worker-base
  confidence: medium
```
