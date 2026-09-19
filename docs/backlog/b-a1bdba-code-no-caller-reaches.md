---
id: b-a1bdba
title: '46 symbols no production caller reached, and the `dead` gate only stops new ones'
status: done
closed: 2026-09-19
tier: 3
filed: 2026-09-18
specs: []
prs: [362, 363]
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

On `11224ec`, `make deadcode` reported 46:

| Kind      | Count |
| --------- | ----- |
| variable  | 23    |
| function  | 18    |
| method    | 3     |
| property  | 1     |
| attribute | 1     |

After the triage it reports none.

## Done looks like

Each of the 46 is removed, listed in an open spec's `pending_symbols`, or
whitelisted in `.saffron/deadcode-allow.py` with its reason. A symbol only tests call
moves into `tests/` instead. `make deadcode` reports `0 unused`.

## Record

- 2026-09-18: filed alongside the `dead` gate's declaration in
  `.saffron/policy.yaml` (Task 5 of the dead-code-gate plan).
- 2026-09-18: triaged on `joel/dead-code-triage`. Of the 58, four were
  removed. Five moved into `tests/`: `host_mutator` with its module,
  `visible_cpus`, and `check_all`, `merged_prs` and `building_pr` with
  `records/check.py`. 48 were whitelisted, each with its caller or reason, and
  none is deferred. The move surfaced `BacklogItem.related`, a pydantic field,
  which is whitelisted too. The whitelist holds 32 names. One remains:
  `saffron/events.py::read_log`, until `SA-0107` (PR #355) merges and gives
  it a caller.
- 2026-09-19: rebased onto `11224ec`, where SA-0107 gives `read_log` its
  caller and reads `timestamp`, so that entry left the whitelist. Of the 46,
  three were removed, five moved into `tests/` and 38 are whitelisted under 31
  names. `conforms` was removed as well, though `main` had already stopped it
  being reported. `make deadcode` reports `0 unused`, so the item is done.
