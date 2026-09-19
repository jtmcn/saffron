---
id: b-a1bdba
title: '46 symbols no production caller reaches, and the `dead` gate only stops new ones'
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

Review then added `records/`, `ontology/` and `hooks/` to the scanned roots,
which brought nine more. One earlier symbol dropped out. vulture matches names
across the whole scan, and `records/` reads an attribute named `date`. So the
unused `date` in `harness/register_scoring.py` is no longer reported. The
gate then stopped reporting pydantic validators by decorator, which dropped six.
Rebased onto `11224ec`, twelve more dropped out: SA-0107's projection calls
`read_log` and reads `timestamp` from ten event fields, and `conforms` in
`.saffron/gates/shacl.py` now shares a name something on `main` reads.

As of this branch, `make deadcode` reports:

| Kind      | Count |
| --------- | ----- |
| variable  | 23    |
| function  | 18    |
| method    | 3     |
| property  | 1     |
| attribute | 1     |

## Done looks like

Each of the 46 is removed, listed in an open spec's `pending_symbols`, or
whitelisted in `.saffron/deadcode-allow.py` with its reason. `make deadcode`
reports `0 unused`.

## Record

- 2026-09-18: filed alongside the `dead` gate's declaration in
  `.saffron/policy.yaml` (Task 5 of the dead-code-gate plan).
- 2026-09-18: triaged on `joel/dead-code-triage`. Of the 64, four were
  removed. Two moved into `tests/`: `host_mutator` with its module, and
  `visible_cpus`. 57 were whitelisted under 40 names, each with its caller or
  reason, and none is deferred. One remains:
  `saffron/events.py::read_log`, until `SA-0107` (PR #355) merges and gives
  it a caller.
