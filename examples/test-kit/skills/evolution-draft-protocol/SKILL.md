---
name: "evolution-draft-protocol"
description: "Produces draft-only evolution proposals with source refs, risk, approval, audit, validation, and rollback fields."
---

# Evolution Draft Protocol

Use this skill when repeated failures, user corrections, or completed task
archives suggest a future change to a skill, prompt, policy, memory rule,
package template, or terrarium template.

## Required Schema

Read the draft protocol before proposing changes:

```text
examples/test-kit/evolution-schema/draft-protocol.yaml
```

## Hard Rules

- Produce proposals only.
- Do not edit active skills, prompts, policies, memory files, or templates.
- Do not mark a proposal approved.
- Do not omit source references.
- Do not omit rollback plan.
- Treat approval and audit as mandatory for any applied change.

## Output Contract

Return exactly one fenced YAML block named `evolution_proposal`:

```yaml
evolution_proposal:
  proposal_id: t18-example
  proposal_type: skill
  scope: package
  source_refs:
    - session:example
  problem: repeated handoff drift in long tasks
  proposed_change: tighten structured-handoff examples
  expected_benefit: less semantic loss
  risk_level: medium
  approval_required: true
  audit_required: true
  rollback_plan: restore prior SKILL.md from previous package tag
  status: draft
```

Keep proposals compact. If evidence is weak, set `status: draft` and lower the
risk confidence in the prose fields instead of pretending the change is ready.
