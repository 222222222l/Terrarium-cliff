---
name: "opencli-autonomous-builder"
description: "Builds or reuses OpenCLI adapters and external integrations. Invoke when the task depends on browser sessions, public web adapters, desktop adapters, or OpenCLI-specific automation."
---

# OpenCLI Autonomous Builder

Use this skill when the user wants a custom OpenCLI path, or when the target
task clearly belongs to OpenCLI instead of a general-purpose CLI harness.

This skill is the OpenCLI-specific counterpart to `autonomous-cli-builder`.
Keep it separate so users can enable only the OpenCLI route without taking a
hard dependency on `CLI-Anything`.

## Source Of Truth

Read these workspace files before building:

- `OpenCLI/docs/adapters/index.md`
- `OpenCLI/src/external-clis.yaml`
- `examples/test-kit/providers/opencli.yaml`
- `docs/zh-CN/dev/cli-compatibility-abstraction.md`

If the local provider rules disagree with older assumptions, follow the local
provider rules in this repository.

## Primary Goal

Turn a browser, website, public API, desktop app, or OpenCLI-compatible
integration into an agent-usable interface with:

- explicit provider fit
- low-token execution paths
- stable invocation shape
- structured outputs or artifacts
- clear scope: reusable, package-local, or agent-local

## Invoke When

Use this skill when at least one of these is true:

1. The user explicitly asks for an OpenCLI-based CLI or adapter.
2. The task requires a live browser session, authenticated website flow, or CDP bridge.
3. The task targets a desktop app or adapter-shaped automation path.
4. The task is best served by an OpenCLI public adapter, not a general CLI harness.

## Do Not Invoke When

Do not use this skill when:

- the task is a normal local software or service CLI problem better served by `CLI-Anything`
- a stable existing CLI already solves the task with lower maintenance cost
- the target has no realistic browser, adapter, desktop, or external integration path
- provider choice is still ambiguous and the user has not selected one

## Mandatory Decision Order

Always follow this order:

1. Check whether an existing OpenCLI adapter or external integration already exists.
2. Only if missing, recommend building a new OpenCLI path.
3. Get approval if the build was only a proactive suggestion.
4. Choose scope.
5. Build using OpenCLI-compatible conventions.

Never create a new adapter first and check reuse later.

## Phase 0: Existing Route Check

Before creating anything new, inspect in this order:

1. `examples/test-kit/providers/opencli.yaml`
2. `OpenCLI/docs/adapters/index.md`
3. `OpenCLI/src/external-clis.yaml`
4. the target website, desktop app, public endpoint, or browser surface

If a usable existing route already exists, prefer reuse over creation.

## Capability Mapping

Map the target into exactly one primary capability:

- `browser_authenticated_task`
- `browser_public_task`
- `desktop_app_task`
- `external_cli_passthrough`

Rules:

- choose `browser_authenticated_task` for login state, session cookies, or live browser dependence
- choose `browser_public_task` for public website reads or public browser adapters
- choose `desktop_app_task` for desktop UI or desktop bridge workflows
- choose `external_cli_passthrough` only when OpenCLI is wrapping another external command

If the task could be either `browser_public_task` or a general CLI workflow,
do not guess. Escalate to the combined provider skill or ask the user.

## Proactive Recommendation Rule

If the user did not explicitly ask for OpenCLI, but the workflow clearly needs
browser session state or adapter-style automation, give a short recommendation:

- why the task fits OpenCLI
- why a general CLI harness is weaker here
- what scope you recommend

Then wait for approval.

## Scope Selection

Every created OpenCLI route must use exactly one scope:

- `reusable`
- `package-local`
- `agent-local`

Use the same scope rules as `autonomous-cli-builder`, but bias toward narrower
scope when the integration depends on one browser bridge, one adapter family,
or one project-specific desktop target.

## Required Inputs

Collect or infer these inputs:

- target site, app, or integration name
- access mode:
  - authenticated browser
  - public browser
  - desktop
  - external passthrough
- local source path or repository URL if it exists
- expected task the route should optimize
- expected artifacts:
  - text
  - JSON
  - screenshot
  - downloaded file
- desired scope:
  - `reusable`
  - `package-local`
  - `agent-local`

## Build Workflow

Follow this sequence:

1. Analyze the target surface.
   - identify browser, desktop, adapter, or passthrough path
2. Decide reuse or creation.
   - prefer adapter reuse first
3. Choose capability and scope.
4. Implement the route.
   - adapter, wrapper, or OpenCLI-compatible integration
5. Create validation docs first.
   - `TEST.md`
6. Add tests and command checks.
7. Generate route documentation and a canonical `SKILL.md`.
8. Validate installation and minimal execution.

## Output Requirements

When you build or recommend an OpenCLI route, produce:

1. route source or adapter wrapper
2. install or setup entry point
3. `TEST.md`
4. test files or check commands
5. `README.md`
6. canonical `SKILL.md`
7. capability and scope decision summary

## Capability Decision Output Contract

Always report the selected capability like this:

```yaml
provider_decision:
  provider: opencli
  capability: browser_authenticated_task | browser_public_task | desktop_app_task | external_cli_passthrough
  reason: <one sentence>
  user_choice_required: true | false
```

## Scope Decision Output Contract

Always report scope like this:

```yaml
scope_decision:
  chosen_scope: reusable | package-local | agent-local
  reason: <one sentence>
  promotion_rule: <when this route should be promoted>
```

## Cost-Reduction Rule

Recommend building an OpenCLI route when most of these are true:

- the workflow repeats
- browser or desktop state matters
- deterministic adapter actions exist
- free-form prompting is wasting tokens
- the result benefits from structured artifacts

Do not recommend creation if manual browser reasoning is still cheaper than
maintaining the route.

## Minimal Reporting Template

After using this skill, report like this:

```text
Target: <site/app/integration>
Decision: reuse existing route | build new OpenCLI route
Capability: <capability>
Scope: reusable | package-local | agent-local
Reason: <short reason>
Backend path: <adapter/source/target path>
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

This skill is OpenCLI-specific. Do not silently broaden it into the default
provider for general CLI work. If the task is not clearly OpenCLI-shaped,
switch to the combined provider skill or ask the user.
