# Issue tracker: Saffron spec files

Saffron's own work is tracked as spec files, not GitHub issues. A spec is
`.saffron/specs/SA-NNNN-<slug>.md` — the `<slug>` is a short kebab-case phrase.
GitHub issues remain in use only for research/evidence records under
`docs/evidence/`; feature work never goes through the `gh` CLI.

## Conventions

- **One spec per file**: `.saffron/specs/SA-NNNN-<slug>.md`, numbered from the
  highest existing `SA-` id + 1 (e.g. after `SA-0011`, next is `SA-0012`).
- **Frontmatter** (YAML between `---` fences, required): `id`, `title`, `type`,
  `priority`, `depends_on`, `touches`, `forbidden`, `budget_usd`, `max_attempts`,
  `risk`. Do not leave a field out — the parser gates on all of them.
- **Body**: headings `## Context`, `## Problem`, `## Acceptance criteria` (as
  `- [ ]` boxes), `## Out of scope`, `## Notes for the agent`. The acceptance
  criteria are load-bearing: each drives a gate check.
- **Dependencies**: list blocked-by spec ids in `depends_on` (e.g. `[SA-0002, SA-0005]`).

## Driving a spec

```
uv run saffron cell .saffron/specs/SA-NNNN-<slug>.md --repo .
```

## When a skill says "publish to the issue tracker"

Create the next `SA-` spec file under `.saffron/specs/` and record the work in
`docs/BACKLOG.md` / `docs/evidence/` per the conventions there.

## When a skill says "fetch the relevant ticket"

Read the referenced `.saffron/specs/SA-NNNN-<slug>.md` (or the `SA-` id / number
the user passed, resolving to its file).

## Wayfinding operations

Used by `/wayfinder`. The **map** is a spec file; research/one-off records live
in `docs/evidence/` as markdown, each prefixed with the issue/record number. A
work item is a spec with a `depends_on` line. Triage state is read from the
spec's `priority`, `depends_on`, and whether its acceptance criteria are ticked,
not from a label string.
