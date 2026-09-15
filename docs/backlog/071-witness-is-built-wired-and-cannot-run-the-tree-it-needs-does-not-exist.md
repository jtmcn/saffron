---
id: 71
title: '`witness` is built, wired, and cannot run — the `tree` it needs does not exist in a cell'
status: done
tier: 1
closed: 2026-09-08
specs: [SA-0058, SA-0060, SA-0061, SA-0062, SA-0063, SA-0064]
prs: [139, 148]
commits: []
cites: [§5.4.1]
related: [69, 83, 97]
---

## Problem

**Status: done, 2026-09-08.** The third landed: `phases/package.py`'s
re-verification now passes `acceptance=` and a `worktree.source_mutated` bound
to each package cell's own container, on both the baseline and the head suite,
so the two suites have the same shape. (Corrected 2026-09-10: this said
`suite_drift` could then compare `witness` across the two call sites. Nothing in
PACKAGE calls `suite_drift`, so no comparison ran; the gate-suite stack named in
item 97 closes that.) Safe to pass only because item 83 landed first: a
witness whose test does not exist at the rebased base is `unproven` there rather
than an abort.

**Prior status: two of the three below were done, 2026-09-07.** `SA-0060` (PR #148)
gave `witness_gate` the injected mutator; `SA-0061` (#150) and `SA-0062` (#154)
made `session._suite` pass `acceptance=` and a real `worktree.source_mutated`,
and `advisory_gates` now reads `contract.witness_blocking`. Measured on real
attempts: `SA-0063` and `SA-0064` each recorded `witness` as `pass` — *"2 of 2"*
and *"1 of 1 witness(es) died under their own mutant"* — in the ledger's
`gate_results`. **The third is open:** PACKAGE's re-verification
(`phases/package.py`, the `run_suite` call under `re-verify:`) passes neither
`acceptance=` nor `mutate=`, so `witness` is left out of that suite entirely and
`suite_drift` has nothing to compare it against. A by-hand fix: the package
cell's container is already in hand there.

**Tier 1.** Found reviewing `SA-0058` (PR #139), 2026-09-06. Item 69's chain
built the gate over three specs and the headline problem is unchanged: nothing
invokes it.

**The shape defect, which is the real one.** `witness_gate` takes `tree: Path`
and mutates it with host file I/O — `apply_mutant` calls `read_bytes` and
`write_bytes` on a host path. During a cell run there is no such path:
`saffron/cell/worktree.py` says it outright, *"Work happens on the volume, not
a bind mount"*. So `run_suite(..., tree=...)` is not a parameter no caller
supplies **yet**; it is one no production caller can ever supply.

`revert` solved this and the solution is sitting one file over: it takes an
injected `Reverted = Callable[[list[str]], AbstractContextManager[None]]` and
mutates *through* the container. `witness_gate` takes a raw `Path` and does the
writing itself.

`SA-0058`'s spec anticipated exactly this — *"if wiring reveals the gate needs
a different shape, that is a finding to file rather than an edit to make"* —
and the finding was not filed. A review lens raised it as a blocker and
withdrew it on the correct observation that `saffron/cell/**` is `forbidden`,
which answers whether to *edit* and not whether to *record*. This item is the
record that was owed.

**The blocking level is decided in prose and contradicted in effect.**
`contract.witness_blocking` returns `tier == "elevated"`, and its docstring
says *"whichever caller decides what an attempt does with a blocking `witness`
failure reads this"*. No caller does — grep finds only `tests/test_gates.py`.
The caller that would is `session._blocking`, which is `failure.gate not in
advisory_gates`, and `advisory_gates` adds only `size` at non-elevated tiers.
So a `witness` failure is **blocking at `standard`**, the opposite of §5.4.1
and of the function that exists to say so.

**Done looks like** three things, and the first gates the others:

- `witness_gate` taking an injected tree-mutation callable in `revert`'s shape,
  so a cell run can supply it. Needs a spec owning `saffron/gates/core/
  witness.py`.
- `session._suite` passing `tree=` and `acceptance=`, and `advisory_gates`
  gaining `witness` at non-elevated tiers — or `_blocking` consulting
  `witness_blocking`. Needs `saffron/cell/session.py`, which is `elevate_on`.
- PACKAGE's re-verification (`phases/package.py`) supplying the same, or the
  two suites differ in shape and `suite_drift` does not compare across those
  call sites, so nothing would say so.

**Not** a reason to revert `SA-0058`. `run_witness`, the pre-flight probe and
the ordering are sound and are what the fix builds on; what is missing is a
seam only a spec that owns `witness.py` and `session.py` together can cut.

**A note on how three specs produced this.** Each was scoped so its `forbidden`
list kept it honest, and the seam that needed changing was outside all three.
The chain could not have found this before `SA-0058` tried to wire it, which is
an argument for wiring early rather than last — the spec that connects a
mechanism to its caller is the one that discovers the mechanism cannot be
connected.
