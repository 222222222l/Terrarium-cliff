# test-kit

`test-kit` is a minimal lab package for fast package and creature evaluation.
It gives you two testing layers:

- `lab-runner`: a single-creature flexible test harness
- `lab-smoke`: a minimal terrarium smoke shell for routing and feedback loops
- `task-team-minimal`: the shortest reusable `root -> coordinator -> worker -> critic -> root` loop

This package is designed for fast iteration. Use the single creature for most
experiments, and use the terrarium only when you need to validate multi-agent
wiring.

## 1. What This Solves

This package exists to reduce the cost of answering these questions:

- Does a new tool, plugin, or skill work at all?
- Does a package component behave correctly in isolation?
- Does a worker still behave correctly after swapping components?
- Does a multi-agent flow still route work and feedback correctly?

## 2. Layout

```text
examples/test-kit/
  kohaku.yaml
  README.md
  creatures/
    lab-runner/
    root-privileged/
    coordinator/
    worker-base/
    critic/
  skills/
    provider-aware-cli-builder/
  skill-policies/
    creature-creation/
  terrariums/
    lab-smoke/
    task-team-minimal/
  test_kit/
    tools/
      lab_report.py
```

## 3. Quick Start

### Run the single-creature lab

```bash
kt run ./examples/test-kit/creatures/lab-runner
```

Recommended first prompt:

```text
Inspect this creature config, tell me what is wired in, run one safe check,
and save the result with lab_report.
```

### Run the terrarium smoke shell

```bash
kt terrarium run ./examples/test-kit/terrariums/lab-smoke --seed "Run a minimal smoke check and report whether routing and feedback both work."
```

Use `lab-smoke` only when you need to test root-to-worker-to-critic
coordination.

### Run the minimal main-workflow team

```bash
kt terrarium run ./examples/test-kit/terrariums/task-team-minimal
```

Use `task-team-minimal` when you want to validate the full four-role baseline
workflow rather than only a smoke shell.

### Stable long-link scripts

For scripted validation of the reusable long-link control layer, use:

```bash
python .\examples\test-kit\scripts\run_t8_worker_shortest_demo.py
python .\examples\test-kit\scripts\run_t8_full_demo_stable.py
```

The current long-link runtime contract is:

- worker-facing turns use the formal `LocalTerrariumService.run_input_turn(...)`
- long-link scripts opt into `completion_scope="graph"`
- the service waits for the whole graph to settle idle, not only the injected
  creature

This matters for `task-team-minimal` because `worker -> critic -> root` is
driven by `output_wiring`. A single-creature idle check can return too early
and let the outer harness shut the terrarium down while downstream roles are
still processing.

For direct role calls used by the full demo:

- prefer `TASK_TEAM_BASE_URL` / `TASK_TEAM_API_KEY` / `TASK_TEAM_MODEL`
- otherwise fall back to `OPENROUTER_API_KEY` and optional `OPENROUTER_MODEL`
- if no API key is present, the script now fails explicitly and writes the
  reason into the summary JSON instead of hanging at `phase=init`

### Install as an editable package

```bash
kt install ./examples/test-kit -e
kt run @test-kit/creatures/lab-runner
kt terrarium run @test-kit/terrariums/lab-smoke --seed "Smoke test this package"
kt terrarium run @test-kit/terrariums/task-team-minimal
```

## 4. How to Use `lab-runner`

`lab-runner` is the default entry point for almost all future tasks.

Use it to test:

- built-in tool combinations
- new prompts
- memory behavior
- compaction behavior
- package tools
- plugins and runtime policy changes
- future `CLI-Anything` / `OpenCLI` compatibility work

It ships with a broad built-in toolset and these subagents:

- `plan`
- `worker`
- `critic`
- `research`
- `memory_read`
- `memory_write`
- `summarize`

It also ships with a custom tool:

- `lab_report`: save a structured Markdown report under `.kohaku/lab-reports/`

It also publishes package skills for CLI creation workflows:

- `autonomous-cli-builder`
- `opencli-autonomous-builder`
- `provider-aware-cli-builder`

`lab-runner` opts into `provider-aware-cli-builder` through its `skills:` list,
which makes the package skill discoverable in a real 2.0 creature config rather
than only in project-local metadata.

The package also ships a control-plane root template:

- `root-privileged`: user-facing privileged root for terrarium orchestration
- designed to inspect topology first, reuse existing nodes, and avoid doing
  worker execution itself

It also ships a lightweight routing template:

- `coordinator`: compiles ambiguous requests into stable `task_card` handoffs
- designed to stay tool-light, reuse provider routing rules, and avoid verbose
  manager chatter

It also ships a narrow execution template:

- `worker-base`: executes bounded tasks with a small deterministic tool surface
- designed for local 8B-9B class models that benefit from low temperature,
  explicit task cards, and minimal tool choice

It also ships a structured review template:

- `critic`: reviews worker outputs with shared or compressed context
- designed to feed compact review packets back into `root-privileged` or
  `coordinator` while keeping a user-interrupt path open

It also ships a reusable minimal team recipe:

- `task-team-minimal`: fixed `root -> coordinator -> worker -> critic -> root`
- designed to prove the shortest reusable closed loop before adding learning,
  policy, or evolution layers
- supports recipe-level model overrides so all four roles can be switched to one
  cheap strong model during integration tests
- long-link harnesses should treat it as a graph-scoped workflow, not a
  single-role workflow

## 5. Recommended Testing Loop

### Mode A: Isolated component test

Use this when testing a single package, tool, prompt, plugin, or skill.

Suggested prompt pattern:

```text
Goal: verify whether <component> works.
Constraints: keep execution deterministic and low-token.
Steps:
1. Inspect the target.
2. State the test plan briefly.
3. Run the minimum safe checks.
4. Save the result with lab_report.
```

### Mode B: Smoke route test

Use `lab-smoke` when the thing you are testing depends on:

- task routing
- role boundaries
- feedback loops
- final result review

## 6. How to Swap Components Quickly

### Swap tools

Edit the `tools:` list in the target creature config.

Typical patterns:

- add a built-in tool
- remove a built-in tool
- replace a custom tool module path
- switch to a package tool after editable install

### Sync module defaults into creature configs

Custom tools in `test-kit` can self-describe their configurable defaults via:

- `option_schema()`
- `default_options()`

After adding a new custom tool or new default option, write the defaults back to
every personalized creature config with:

```bash
python .\examples\test-kit\scripts\sync_test_kit_module_configs.py
```

This keeps module configuration editable in `config.yaml` instead of hiding it
in Python code.

Current `test-kit` sync scope:

- scans `examples/test-kit/creatures/*/config.yaml`
- loads each custom tool class
- reads default options from the tool
- writes missing keys into the matching creature config

Recommended rule:

- define module defaults once in the module class
- sync them into creature configs
- let per-agent customization happen only in YAML

### Swap plugins

Add or remove entries in `plugins:`.

Recommended pattern:

- keep `lab-runner` as the stable harness
- test one plugin change at a time
- record impact with `lab_report`

### Swap prompts

Change `system_prompt_file`, or duplicate the creature folder and edit only
the prompt.

### Swap provider compatibility components

When `T21-T25` land, plug provider adapters into the same harness rather than
creating a new testing creature.

## 7. Using `lab_report`

Example request to the creature:

```text
After the check, call lab_report with:
- title: a short test name
- status: pass, fail, or note
- summary: one-line result
- details: what was tested and why it passed or failed
- artifacts: any file paths worth reviewing
```

Reports are written to:

```text
.kohaku/lab-reports/
```

This keeps execution logs and evaluation notes outside the main conversation
history.

## 8. When to Use Which Harness

Use `lab-runner` when:

- you are testing one creature
- you are testing one package tool, plugin, or skill
- you want the fastest evaluation loop
- you do not need channel routing

Use `lab-smoke` when:

- you need root orchestration
- you need worker execution plus reviewer feedback
- you need to validate a minimal terrarium flow

Use `task-team-minimal` plus the stable scripts when:

- you need the full `root -> coordinator -> worker -> critic -> root` chain
- you need to validate long-link completion semantics
- you need to confirm downstream `output_wiring` does not get cut off by early
  shutdown
- you need a reusable baseline before adding more modules or personalized agents

Note:

- `lab-smoke` no longer uses `type: queue` or `type: broadcast` in channel
  declarations
- routing is expressed through `listen` / `can_send` only, which matches the
  current 2.0 terrarium semantics

## 9. Review Checklist

After each experiment, check:

- Was the right component loaded?
- Did the creature use the minimum necessary tools?
- Did execution stay mostly silent unless analysis was needed?
- Did `lab_report` capture enough evidence?
- If testing a terrarium, did routing and feedback both happen?

## 10. Suggested Next Uses

This package should be the first place you validate:

- `CLI-Anything` provider integration
- `OpenCLI` provider integration
- silent execution policy
- provider routing fields in task cards
- feedback-analysis protocols
