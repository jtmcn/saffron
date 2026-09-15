---
id: 51
title: A cell can buy `revert` a `skip` for one printed line
status: open
tier: 1
specs: []
prs: []
commits: []
cites: [§2.1, §5.4, §9]
related: [50]
---

## Problem

**Decided 2026-09-04: the §5.4 contract change, and this item is why it is
Tier 1.** A cell switches the anti-theater gate off for an attempt with one
printed line, needing no `conftest.py`, so the `gate_config` routing that
exists for this class never fires. That is a control reading as present while
not applying — Appendix I's founding defect — and the item is explicit that no
name filter closes it, because telling a real node id from an invented one is
language knowledge §2.1 keeps out of core. **Contract or nothing.**

The cost is real and is accepted: every onboarded repo's `tests` gate has to
implement the addition, and v2's success criterion is an afternoon-long
onboarding. Under §9's v1 target that cost lands later than this defect does.

`revert` is the only gate that *executes* a name the cell produced, so it is the
only one where a collection line is an argument rather than a string to compare.
Names reading as command-line options are dropped (`_argv_safe`), which closes
the shape that would force a false `pass` — a `--deselect=` line deselecting the
one test the gate is asking about. **It does not close the family.**

Measured against this repo's own gates. A test file registering an `atexit`
handler that prints `zzz::bogus` leaks that line onto `pytest --collect-only`'s
stdout: the handler runs after pytest tears its capture down, so a plain
module-level `print` does *not* leak and this does. The collection still exits
0, and `.saffron/gates/tests.py` calls any line holding `::` a collected name.
The name is new at head, joins the subset, matches no file, the reverted run
exits 4 with no parsed failures, the `tests` gate reports `error`, and `revert`
reads an untrustworthy run as `skip`. **One line in a new test file, and the
anti-theater gate is off for that attempt.** It needs no `conftest.py`, so the
`gate_config` routing in `.saffron/policy.yaml` — which exists for exactly this
class, and says so — never fires.

**No name filter closes it.** A bogus id spells as easily inside the repo's
declared `test_paths` as outside them, and telling a real node id from an
invented one is the language knowledge §2.1 keeps out of core. **Done looks
like** the contract addition item 50 wants for the opposite reason: a `tests`
role that reports what became of each name it was handed, so a name it could not
collect is a fact the gate can read rather than a silence it must interpret.
Until then the dropped names are named in the gate's summary — which makes the
*other* shape visible to an operator, and leaves this one invisible.
