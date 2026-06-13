---
name: "memory-curation"
description: "Curates session output into layered long-term memory records using source, confidence, retention, and dedupe rules."
---

# Memory Curation

Use this skill when a completed task, review result, or user instruction may
need to become durable memory.

## Invoke When

Use this skill when at least one of these is true:

1. A completed task should be archived.
2. A repeated user preference should be preserved.
3. A repository rule or package policy was confirmed.
4. A workspace asset, generated artifact, or sibling checkout state matters for
   future work.
5. Transient context must be expired, promoted, or explicitly kept as draft.

## Required Schema

Read the memory schema before writing:

```text
examples/test-kit/memory-schema/schema.yaml
```

The schema defines these layers:

- `user-preferences`
- `project-rules`
- `workspace-assets`
- `task-archives`
- `transient-context`

## Curation Steps

1. Identify candidate facts from the task context.
2. Classify each candidate into exactly one layer.
3. Assign `scope`, `source`, `source_ref`, `confidence`, `retention`, and
   `dedupe_key`.
4. Check existing memory for the same `layer + scope + dedupe_key`.
5. Write, supersede, skip, or keep as draft.
6. Expire transient context after task completion unless it is promoted.

## Hard Rules

- Do not write raw logs as memory.
- Do not write inference-only records as active durable memory.
- Do not store workspace-local paths as user preferences.
- Do not duplicate records with the same dedupe key.
- Do not make `transient-context` permanent.
- Do not hard-code schema fields in prompt text beyond the schema contract.

## Output Contract

Return exactly one fenced YAML block named `curation_result`:

```yaml
curation_result:
  status: pass
  schema_version: 1
  records_written:
    - task-archives:t12-memory-schema
  records_skipped: []
  records_superseded: []
  transient_expired: []
  next_review: none
```
