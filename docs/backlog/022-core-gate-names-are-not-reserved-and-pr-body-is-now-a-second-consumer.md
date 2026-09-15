---
id: 22
title: Core gate names are not reserved, and `pr_body` is now a second consumer of that hole
status: done
tier: 3
specs: [SA-0011]
prs: []
commits: [2c3b231]
cites: []
related: [97]
---

## Problem

**Status:** **done**, by hand, 2026-09-10 — the gate-suite stack's second layer
(item 97). `CORE_GATE_NAMES` in `saffron/repos/policy.py`, held equal to
`factory:CoreGate` by a test, and a `field_validator` on `Policy.gates` that
fails preflight on any of them. Found by review of `SA-0011`.

`GateName` at `saffron/repos/policy.py:53` accepts any string matching
`^[A-Za-z0-9_-]+$`, so nothing stops a repo declaring `gates: {criteria: {...}}`.
Three consequences, all verified against the running code:

`saffron/phases/package.py:402`'s `reverify` runs only
`policy.gate_executables(...)` (`:468-469`) — no core gates. On a rebase
(`verified_on = "packaged"` at `:638`) the `gates` handed to `render_pr_body`
(`:673`) therefore contain no core `criteria` result, so a repo-declared gate
named `criteria` reporting `pass` is the one `pr_body._criteria` selects
(`saffron/report/pr_body.py:140`) and it ticks every box it never earned. This
is the defect `2c3b231` ("a repo-declared gate named criteria ticked every
box") fixed on the session path — `_suite` appends the host-constructed result
last, so it cannot be shadowed there — and it is still open on the reverify
path, which never runs `_suite` at all.

`_suite` also builds `advisory_gates` straight from `policy.gates`
(`saffron/cell/session.py:672-674`), so `gates: {criteria: {blocking: false}}`
makes the *core* `criteria` gate advisory — same hole for `census`. And
`suite_drift` keys both suites by bare gate name (`saffron/gates/baseline.py:84`),
so the same collision family reaches `scope`, `census` and `committed` there
too.

**Done looks like** a `frozenset` of core gate names and one `field_validator`
on `Policy.gates` in `saffron/repos/policy.py` rejecting them, which closes all
three call sites at once and gives the ontology's `CoreGateShape` an enforced
counterpart in code.
