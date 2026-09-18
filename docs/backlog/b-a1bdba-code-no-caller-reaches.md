---
id: b-a1bdba
title: '56 symbols no production caller reaches, and the `dead` gate only stops new ones'
status: open
tier: 3
filed: 2026-09-18
specs: []
prs: []
commits: []
cites: [§5.4]
related: []
---

## Problem

The `dead` gate (`docs/superpowers/specs/2026-09-18-dead-code-gate-design.md`)
blocks new dead code. The 55 symbols vulture reported at `66c71ca` are its
baseline, so nothing removes them. `Spec.pending_symbols`, the field the gate
reads to defer a symbol an open spec names, is itself read by nothing but its
own tests. That is the 56th, added on this branch.

As of this branch, `make deadcode` reports:

| Kind      | Count |
| --------- | ----- |
| variable  | 32    |
| function  | 16    |
| method    | 6     |
| property  | 1     |
| attribute | 1     |

## Done looks like

Each of the 56 is removed, listed in an open spec's `pending_symbols`, or
whitelisted in `.saffron/deadcode-allow.py` with its reason. `make deadcode`
reports `0 unused`.

## Record

- 2026-09-18: filed alongside the `dead` gate's declaration in
  `.saffron/policy.yaml` (Task 5 of the dead-code-gate plan).
