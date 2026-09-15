---
id: 128
title: '`by_hand` names who does the work, when what it records is that a cell cannot'
status: open
filed: 2026-09-15
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

`by_hand: true` means that the work that closed an item, or the work still
left, cannot go through a cell (`docs/backlog/README.md`;
`docs/superpowers/specs/2026-09-14-backlog-as-records-design.md`). The name
says something else: that a person does the work. In practice a delegate
session on the host does it, not a person, so a reader who takes the name at
its word misreads 28 records.

The field reaches five live surfaces besides those records: `records/kinds.py`,
`tests/records/test_records_kinds.py`, `tests/records/test_records_load.py`,
the README's "How to add an item", and `docs/agents/issue-tracker.md`. The
plans, design docs and retired specs that name it are history, and stay as
written.

## Done looks like

the field renamed, with its meaning unchanged, across the model, its tests,
the README, the tracker doc and every record that sets it, in one commit. A
record that still says `by_hand` is refused on load rather than silently
dropped. The new name is decided in that pull request; `outside_cell` fits the
README's definition.

## Record

**Filed 2026-09-15**, after PR #263 brought the 28 values into line with the
README's definition, so the rename is mechanical.
