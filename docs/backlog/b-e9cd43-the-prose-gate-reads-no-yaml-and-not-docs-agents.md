---
id: b-e9cd43
title: "The `prose` gate reads no `.yaml` file and nothing under `docs/agents/`, so new prose there passes unread"
status: open
tier: 3
filed: 2026-10-19
specs: []
prs: []
commits: []
cites: [§5.4]
related: [161, b-86fa07]
---

## Problem

Found by the Standards seats on #908 and #911, in the spec loop's run 44.

`in_scope` admits a `.py` file under a code directory and a `.md` file under
the listed roots (`.saffron/gates/prose.py:198-203`). A `.yaml` file is never
read. `docs/agents/` is not in `INCLUDED_DIRS` (`:36-45`).

`SA-0280` (#908) added a four-line comment with a semicolon to the setup
template, `.claude/skills/setup-saffron/templates/policy.yaml`. `SA-0283`
(#911) added a semicolon and a sentence past 25 words to
`docs/agents/issue-tracker.md`. Both passed the gate. The seats caught both,
and review fixed them.

## Done looks like

`prose` reads the comments in a `.yaml` file, and `docs/agents/` is in scope.
A test feeds each a hit and asserts the gate reports it.

## Record

- 2026-10-19: filed from the spec loop's run 44.
