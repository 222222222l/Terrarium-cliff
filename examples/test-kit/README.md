# test-kit

`test-kit` is a minimal lab package for fast package and creature evaluation.
It gives you two testing layers:

- `lab-runner`: a single-creature flexible test harness
- `lab-smoke`: a minimal terrarium smoke shell for routing and feedback loops

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
  terrariums/
    lab-smoke/
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

### Install as an editable package

```bash
kt install ./examples/test-kit -e
kt run @test-kit/creatures/lab-runner
kt terrarium run @test-kit/terrariums/lab-smoke --seed "Smoke test this package"
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
