# Project Skill Library For Creature Creation

This folder is the user-facing selection shelf for project-level skills that
may be attached when creating a creature.

Important constraint:

- callable Trae skills still live under `.trae/skills/<skill-name>/SKILL.md`
- this folder exists as a stable selection index, not as an alternate runtime discovery root

## Why This Folder Exists

The existing `autonomous-cli-builder` skill is a general reusable skill. It is
not a good place to keep project-specific selection guidance for creature
creation.

This folder keeps project-level selection material separate while preserving the
supported skill layout.

## Generic Attachment Rule

This folder is not only for CLI-related skills. It is the selection and policy
layer for any future system-level optional skill that may be mounted onto a
creature by default.

The generic rule is:

1. keep the callable skill in `.trae/skills/`
2. describe attachment metadata in `catalog.yaml`
3. follow the generic mounting rules in `attachment-policy.yaml`
4. materialize the final chosen skill set into the creature's `skills:` field when creating the creature

Important runtime constraint:

- per-creature controllable defaults should prefer package-shipped skills
- project and user skills are ambient by origin and should not be the only mechanism for creature-specific default mounting

## Current Creature-Creation Skill Set

1. `autonomous-cli-builder`
   - use when the user wants a CLI-Anything-first path
   - source file: `.trae/skills/autonomous-cli-builder/SKILL.md`
2. `opencli-autonomous-builder`
   - use when the task depends on OpenCLI-style browser, public web, desktop, or adapter automation
   - source file: `.trae/skills/opencli-autonomous-builder/SKILL.md`
3. `provider-aware-cli-builder`
   - use when one entry point should choose between CLI-Anything and OpenCLI
   - source file: `.trae/skills/provider-aware-cli-builder/SKILL.md`

## Selection Rule

Choose the narrowest correct skill:

- choose `autonomous-cli-builder` when provider fit is already CLI-Anything
- choose `opencli-autonomous-builder` when provider fit is already OpenCLI
- choose `provider-aware-cli-builder` when provider fit is unclear or the user wants one unified entry

## Default Mounting Rule

The default out-of-box bundle for new creatures should stay conservative:

- start from the `safe-default` bundle in `attachment-policy.yaml`
- only attach extra optional skills when the creature's role clearly benefits from them
- every optional skill must remain removable
- removing an optional skill must not make the creature fail to start or misreport its available capabilities

## Add / Remove Rule

When creating or updating a creature:

1. start from the role's default bundle
2. apply any user-selected bundles
3. apply explicit additions
4. apply explicit removals
5. write the final resolved set into the creature config's `skills:` list

Because `skills` is treated as a plain list in config inheritance, child
creatures should write the full final list they want, instead of assuming
incremental append/remove behavior.

## Maintenance Rule

When adding future project-level creature-creation skills:

1. add the actual callable skill under `.trae/skills/`
2. register it in `catalog.yaml` here
3. describe its default-attach and fallback behavior in `attachment-policy.yaml`
4. keep provider-specific or domain-specific skills independent
5. avoid turning optional project skills into hard system dependencies
