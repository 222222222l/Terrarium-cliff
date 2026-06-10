---
name: "autonomous-cli-builder"
description: "Builds or recommends CLI-Anything harnesses for software and services. Invoke when the user asks to create a CLI, or when a repetitive software task would be cheaper and more reliable as a CLI."
---

# Autonomous CLI Builder 

Use this skill when the user wants an agent-native CLI for a software product,
service, API, or internal tool, or when you detect that a custom CLI would
reduce token cost, improve determinism, and make repeated execution cheaper than
keeping the workflow inside free-form model reasoning.

This skill follows the official `CLI-Anything` harness methodology. The source
of truth is:

- `CLI-Anything/cli-anything-plugin/HARNESS.md`

If that file exists in the workspace, read it before implementation. Do not
invent a different harness format when the official SOP is available.

## Related Skills

Use the narrower or combined project-level skills when appropriate:

- `opencli-autonomous-builder`
  - use when the task is clearly OpenCLI-shaped
- `provider-aware-cli-builder`
  - use when provider fit is unclear or the user wants one entry covering both providers

Keep this skill focused on the CLI-Anything path. Do not silently broaden it
into a two-provider router.

## Primary Goal

Turn a target software or service into an agent-usable CLI with:

- a stable command surface
- JSON-readable output
- low-token execution paths
- reusable skill documentation
- explicit scope: reusable, package-local, or agent-local

## Invoke When

Use this skill in either of these cases:

1. The user explicitly asks to create a CLI for a software or service.
2. You identify a repeated task where:
   - the agent is repeatedly translating natural language into the same tool flow
   - the task is expensive in tokens
   - the task is better expressed as deterministic commands
   - a CLI wrapper would reduce cost or increase execution reliability

## Do Not Invoke When

Do not use this skill when:

- an existing CLI already solves the task well enough
- the workflow is truly one-off and will not be reused
- the target has no accessible code, API, backend, scripting surface, or stable automation path
- the user has not approved proactive CLI creation after you suggested it

## Mandatory Decision Order

Always follow this order before building anything:

1. **Check whether an existing CLI already exists**
2. **Only if missing, recommend building a new CLI**
3. **Get approval if the build was only a proactive suggestion**
4. **Choose scope**
5. **Build using the official `CLI-Anything` method**

Never skip the existing-CLI check.

## Phase 0: Existing CLI Check

Before creating a new harness, inspect these sources in order:

1. The local private provider mapping and registry in this workspace
2. `CLI-Anything/registry.json`
3. `CLI-Anything/public_registry.json`
4. The target project's own official CLI, SDK, REST API, or scripting entrypoint

If a suitable CLI already exists, prefer reuse over rebuilding.

## Proactive Recommendation Rule

If the user did **not** explicitly ask for a new CLI, but the task would clearly
benefit from one, present a short recommendation before building:

- why repeated execution is expensive now
- why a CLI will lower token cost
- why it improves accuracy or auditability
- what scope you recommend

Then wait for approval.

## Scope Selection

Every new CLI must be classified into exactly one scope.

### `reusable`

Choose this when the CLI is likely useful across multiple creatures, packages,
or projects.

Typical signals:

- generic business software
- common internal services
- tools likely to be reused by multiple top-level creatures
- candidate for future private registry indexing

Default expectation:

- clean package structure
- standalone install path
- SKILL.md included
- suitable for future registration

### `package-local`

Choose this when the CLI is mainly useful for one package or one terrarium, but
may still be reused by several creatures inside that package.

Typical signals:

- tightly coupled package workflow
- project-specific data model
- internal integration with one package's conventions

Default expectation:

- installable, but not globally promoted
- referenced by that package's creatures and workflows

### `agent-local`

Choose this when the CLI is only useful for one agent's narrow job and would
add maintenance burden if promoted further.

Typical signals:

- one-off domain role
- temporary workflow accelerator
- deeply specialized helper around one local process

Default expectation:

- minimal surface
- fastest path to correctness
- no global promotion unless reuse later becomes obvious

## Required Inputs

Collect or infer these inputs:

- target software or service name
- local path or repository URL if source exists
- what user task the CLI should optimize
- expected command groups
- backend availability:
  - source code
  - CLI
  - REST API
  - SDK
  - scripting interface
- desired scope:
  - `reusable`
  - `package-local`
  - `agent-local`

If scope is unclear, decide using the rules above and state the reason.

## Build Workflow

Follow the official `CLI-Anything` methodology. Compress it into this working
sequence:

1. **Analyze the target**
   - identify backend engine, APIs, data model, existing CLIs, and commandable actions
2. **Design the harness**
   - choose REPL, subcommands, or both
   - define command groups
   - define state model
   - define JSON output path
3. **Implement the harness**
   - prefer wrapping the real backend
   - avoid fake reimplementation unless unavoidable
4. **Plan tests**
   - create `TEST.md` first
5. **Implement tests**
   - unit tests
   - real backend E2E where applicable
   - subprocess CLI tests
6. **Generate the harness SKILL.md**
   - canonical `skills/cli-anything-<software>/SKILL.md`
7. **Validate installation and usage**
   - install locally
   - run help, JSON, and minimal workflow checks

## Output Requirements

When you build a CLI harness, produce these artifacts:

1. Harness source
2. Install entry point
3. `TEST.md`
4. test files
5. `README.md`
6. canonical `SKILL.md`
7. scope decision summary

## Scope Decision Output Contract

Whenever this skill is used, state the scope in this format:

```yaml
scope_decision:
  chosen_scope: reusable | package-local | agent-local
  reason: <one sentence>
  promotion_rule: <when this CLI should be promoted to a wider scope>
```

## Cost-Reduction Rule

Recommend building a CLI when most of these are true:

- the workflow repeats
- the steps are deterministic
- execution can be expressed as commands or stable API calls
- verbose natural-language control is wasting tokens
- the result benefits from structured output or artifacts

Do **not** recommend building a CLI if the task is highly ambiguous, unstable,
or not reusable enough to amortize the maintenance cost.

## Default Command Expectations

Prefer these conventions in generated harnesses:

- `cli-anything-<software>` entry point
- REPL mode when run without subcommands
- `--json` for machine-readable output
- clear command groups
- stable exit codes
- artifact-oriented workflows when relevant

## For Top-Level Creatures

Top-level creatures using this skill should behave like this:

1. Detect whether an existing CLI is enough.
2. If not, explain the cost/performance reason for building one.
3. Obtain approval when the creation was only suggested, not requested.
4. Select scope.
5. Create the harness using `CLI-Anything` rules.
6. Return:
   - what was built
   - where it lives
   - how to install it
   - how to test it
   - whether it is reusable or local-only

## Minimal Reporting Template

After using this skill, report with this structure:

```text
Target: <software/service>
Decision: reuse existing CLI | build new CLI
Scope: reusable | package-local | agent-local
Reason: <short reason>
Backend path: <source/API/backend path>
Generated artifacts:
- <path 1>
- <path 2>
Validation:
- <command 1>
- <command 2>
Open risks:
- <risk 1>
```

## Important Constraint

This skill is for **creating or recommending CLIs**, not for directly embedding
all software logic into a creature prompt. If a stable command interface can be
built, prefer that over repeated prompt-level orchestration.
