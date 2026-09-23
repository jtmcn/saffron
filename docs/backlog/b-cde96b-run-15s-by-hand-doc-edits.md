---
id: b-cde96b
title: Run 15's merges leave protected docs stating the old behaviour
status: open
tier: 2
by_hand: true
filed: 2026-09-23
specs: []
prs: []
commits: []
cites: [§3.2, §4.2.1, §5.4]
related: [b-149df3]
---

## Problem

Found in the spec loop's run 15, 2026-09-23. Each spec forbade these files,
and each left its edit to the operator.

- `DESIGN.md` §3.2 (`:235`) says `No estimated_diff_lines`. `SA-0125` gates
  the plan's estimate at `elevated`, and `SA-0129` adds an author's estimate.
- `DESIGN.md` §4.2.1 (`:390`) lists two admissions for a landed parent.
  `SA-0131` adds a third, a recorded push that reached the default branch.
- `DESIGN.md` §5.4's table row (`:815`) still gives line ceilings. `SA-0128`
  counts tokens: `bug` 1300, `feature` 3000, `refactor` 4200. Line `:784`
  says only `census` and `criteria` read `collected`. `revert` reads it too.
- `saffron/agents/prompts/implement.md:27-29` says a plan over the ceiling is
  rejected. After `SA-0125` that holds only at `elevated`.
- `CONTEXT.md`'s Risk tier entry (`:231`) names only the diff's paths. `SA-0125`
  adds a forecast tier from the plan's files.
- `CLAUDE.md:217-218` calls an edit the implementer writes a mutant.
  `CONTEXT.md` reserves the word for a declared edit.
- `.claude/agents/spec-writer.md:59`, `.claude/agents/spec-reviewer.md:122`,
  `.claude/skills/create-saffron-spec/references/preflight.md:106` and the
  driver's `size` help text size in lines. The spec-loop skill says `check`
  applies two blocker rules, and `SA-0129` will add a third.

## Done looks like

Each passage above says what the merged code does. The prompt edit goes
through a measured pass, as `.github/pull_request_template.md` asks.

## Record

- 2026-09-23: filed from the spec loop's run 15.
