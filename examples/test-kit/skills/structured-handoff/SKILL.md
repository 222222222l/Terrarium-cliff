---
name: "structured-handoff"
description: "Compiles long or ambiguous requests into a stable task_card with low semantic loss. Invoke when coordinator-style handoff needs compression, routing, or explicit execution contracts."
---

# Structured Handoff

Use this skill when a request must be handed from one creature to another
without losing the real goal, routing choice, deliverable, or blocking
ambiguity.

## Invoke When

Use this skill when at least one of these is true:

1. Long context may collapse into vague instructions.
2. Provider choice or task kind matters.
3. Comparison basis, evidence, or constraints must survive the handoff.
4. Blocking ambiguity must stay visible.

## Core Contract

Output exactly one fenced block whose opening line is exactly ````task_card`.

It must contain only these 6 fields in this exact order:

- `task_id`
- `goal`
- `task_kind`
- `preferred_provider`
- `deliverable`
- `open_questions`

## Brevity Rules

- Use the fence label `task_card` instead of a nested `task_card:` wrapper key.
- Keep the whole block at 7 lines: the opening fence plus the 6 required fields.
- Keep every field on exactly one physical line.
- Use one-line scalar values for `goal`, `task_kind`, `preferred_provider`, and `deliverable`.
- Prefer the exact source anchor `qt.gtimg.cn` over a looser host mention when the source matters.
- Keep the highest-value safety semantics inside existing fields instead of adding new ones.
- Keep `goal` anchored to the smallest honest execution path, and preserve quote-only or no-fabrication limits when they change what the worker may claim.
- Keep `deliverable` anchored to the acceptance test, and preserve evidence or fetch-proof language when the reviewer must verify the comparison.
- Keep `deliverable` as a short noun phrase, not a full sentence.
- Keep `open_questions` to one short blocker when possible.
- Encode `open_questions` on one line as `[]` or `["short blocking question"]`.
- Put comparison-basis ambiguity inside `open_questions`.
- If the task is a deterministic public HTTP or CLI-style call, prefer
  `task_kind: service_cli_task` and `preferred_provider: cli-anything`.

## Hard Rules

- Do not invent details.
- Do not restate the whole conversation.
- Do not hide comparison ambiguity.
- Do not omit `task_kind` or `preferred_provider`.
- Do not add a nested `task_card:` wrapper key under the fence.
- Do not emit `constraints`, `inputs`, `evidence_needed`, or any extra field.
- If space is tight, shorten values but never drop a required field.

## Minimal Example

```task_card
task_id: docs_fix_readme
goal: Update the package README without inventing extra setup steps.
task_kind: docs_task
preferred_provider: none
deliverable: README update with install proof.
open_questions: []
```
