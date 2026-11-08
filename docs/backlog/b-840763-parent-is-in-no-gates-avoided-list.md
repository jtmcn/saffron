---
id: b-840763
title: '"parent" is in no gate''s avoided list, so a retired-first entry called a parent passes'
status: open
tier: 3
filed: 2026-11-08
specs: []
prs: []
commits: []
cites: []
related: [174, b-4b386f]
---

## Problem

Found reviewing `SA-0350` (#1089), in the spec loop's run 55.

`CONTEXT.md`'s **Retired-first entry** avoids "parent", since that word names
a `depends_on` entry. `AVOIDED` in `.saffron/gates/prose.py` lacks it. #1089's
tests called a retired-first entry a parent in four places, and no gate
caught one. The criterion 3 witness name the spec fixed,
`test_a_stack_night_refuses_the_spec_whose_retired_first_parents_are_in_its_order`,
says it too.

## Done looks like

A gate flags "parent" where `CONTEXT.md`'s entries avoid it, scoped so a
`depends_on` parent still passes. The witness above is renamed.

## Record

- 2026-11-08: filed from the spec loop's run 55.
