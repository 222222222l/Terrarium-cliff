---
name: "provider-aware-cli-builder"
description: "Chooses between CLI-Anything and OpenCLI for CLI creation or reuse. Invoke when user wants one entry for both providers or provider fit is unclear."
---

# Provider-Aware CLI Builder

Use this skill as the unified entry point when a user wants CLI creation
capability but the correct provider is not obvious up front.

This skill does not replace the provider-specific skills. It routes work into
the right path while preserving:

- `autonomous-cli-builder` for CLI-Anything-first creation
- `opencli-autonomous-builder` for OpenCLI-first creation

## Source Of Truth

Read these files before making a provider decision:

- `examples/test-kit/test_kit/provider_selection.py`
- `examples/test-kit/providers/cli_anything.yaml`
- `examples/test-kit/providers/opencli.yaml`
- `docs/zh-CN/dev/cli-compatibility-abstraction.md`
- `examples/test-kit/skills/autonomous-cli-builder/SKILL.md`
- `examples/test-kit/skills/opencli-autonomous-builder/SKILL.md`

## Primary Goal

Choose the cheapest correct provider for a requested CLI path or reusable
automation surface, then delegate to the corresponding build workflow.

## Invoke When

Use this skill when at least one of these is true:

1. The user wants a single entry point covering both `CLI-Anything` and `OpenCLI`.
2. The user asks to create a custom CLI but does not specify the provider.
3. The task may fit either a general CLI harness or an OpenCLI route.
4. You need to decide whether to reuse an existing provider route or build a new one.

## Do Not Invoke When

Do not use this skill when:

- the user already explicitly chose `CLI-Anything`
- the user already explicitly chose `OpenCLI`
- provider fit is already obvious and there is no routing ambiguity

In those cases, jump directly to the provider-specific skill.

## Mandatory Decision Order

Always follow this order:

1. Check whether an existing CLI or adapter already exists.
2. Determine the normalized task kind.
3. Determine provider fit using local routing rules.
4. If clear, delegate to the matching provider-specific skill.
5. If overlap remains, ask the user instead of guessing.
6. Only then build anything new.

## Normalized Task Kinds

Map the request into one primary task kind:

- `local_software_task`
- `service_cli_task`
- `browser_cli_task`
- `browser_authenticated_task`
- `browser_public_task`
- `desktop_app_task`
- `external_cli_passthrough`

## Routing Rules

Use these rules unless the user explicitly overrides them:

- prefer `CLI-Anything` for:
  - `local_software_task`
  - `service_cli_task`
- prefer `OpenCLI` for:
  - `browser_authenticated_task`
  - `desktop_app_task`
  - `external_cli_passthrough`
- require user choice for:
  - `browser_public_task`
  - any case where browser-public and general CLI paths both look plausible

If overlap remains, do not guess.

## Existing Route Check

Before creation, inspect in this order:

1. local project provider rules and registry files
2. `CLI-Anything/registry.json`
3. `CLI-Anything/public_registry.json`
4. `OpenCLI/docs/adapters/index.md`
5. `OpenCLI/src/external-clis.yaml`
6. the target project's own official CLI, API, SDK, or scripting surface

If a suitable route exists, prefer reuse over rebuilding.

## Delegation Rule

After provider choice:

- if provider is `cli-anything`, follow `autonomous-cli-builder`
- if provider is `opencli`, follow `opencli-autonomous-builder`
- if `needs_user_choice`, stop and ask the user to pick

Do not blend both build workflows into one generated implementation unless the
user explicitly asks for both outputs.

## Scope Rule

This skill must preserve the provider decision separately from the scope
decision. First choose provider, then choose one scope:

- `reusable`
- `package-local`
- `agent-local`

## Provider Decision Output Contract

Always report provider choice like this:

```yaml
provider_decision:
  decision_status: selected | needs_user_choice
  preferred_provider: cli-anything | opencli | none
  task_kind: <normalized task kind>
  reason: <one sentence>
  user_choice_required: true | false
```

If user choice is required, also report:

```yaml
candidate_providers:
  - provider_name: cli-anything
    reason: <why it may fit>
  - provider_name: opencli
    reason: <why it may fit>
```

## Scope Decision Output Contract

After provider selection, report:

```yaml
scope_decision:
  chosen_scope: reusable | package-local | agent-local
  reason: <one sentence>
  promotion_rule: <when this should be promoted>
```

## Proactive Recommendation Rule

If the user did not explicitly ask for CLI creation, but a CLI or adapter would
clearly reduce cost and improve determinism, explain:

- why repeated execution is expensive now
- why a provider-backed route is cheaper
- which provider you recommend
- what scope you recommend

Then wait for approval.

## Minimal Reporting Template

After using this skill, report like this:

```text
Target: <software/service/site/app>
Decision: reuse existing route | build new route
Provider: cli-anything | opencli | user choice required
Task kind: <normalized task kind>
Scope: reusable | package-local | agent-local
Reason: <short reason>
Delegated workflow:
- autonomous-cli-builder | opencli-autonomous-builder | ask user
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

This skill is a router and orchestrator. Its job is to choose the right
provider path, not to erase the independent value of the provider-specific
skills. Keep the three-skill model intact:

1. `autonomous-cli-builder`
2. `opencli-autonomous-builder`
3. `provider-aware-cli-builder`
