---
id: 50
title: '`revert` produces no evidence for the spec shape it was built for'
status: open
tier: 1
specs: [SA-0127]
prs: []
commits: []
cites: [§5.4]
related: [49]
---

## Problem

Its canonical case is a spec that lands a module *and* its tests together: the
revert removes the module, the new tests fail to import, and that is the gate's
success condition rather than a problem. This repo's `tests` gate cannot report
it as one. A collection error prints no line its regex or its `FAILED ` fallback
can key on, so it reports `error`; `revert` will not read an untrustworthy run
as a pass, so it reports **`skip`** — honest, non-blocking, and no evidence in
either direction. The gate therefore bites hardest on a diff that adds tests for
source that already existed, and says nothing at all about one that adds both.

## Done looks like

the `tests` role reporting a collection error inside the
contract it already fills — `failures` keyed on the node ids it was asked to run
and could not collect — which turns the case into the `fail` `revert` is waiting
for. A contract question, not core's: §5.4 already obliges the role to accept a
subset, and this obliges it to say what became of one. Until then the ceiling
lives in `revert.py`'s comment and one test, and nowhere an operator reads.

## Record

**Decided 2026-09-04: closed by the contract change item 49 now records.** A
`tests` role that reports the disposition of every name it was handed turns a
collection error into the `fail` `revert` is waiting for, which is exactly what
this item asks for. **Tier 1** with 51.

- 2026-09-19: hit in production, on the spec loop's run 9 (#377). Two witness
  modules bound `KINDS["adr"]` at module scope. The reverted run raised
  `KeyError` at import, pytest exited 2, and `revert` reported `skip`. The
  anti-theater gate then checked nothing for the whole diff, and no lens
  noticed. The spec carried a section ordering the lazy lookup, which is the
  instruction a gate makes unnecessary. The loop's review reran the reverted
  suite by hand. With the lookup made lazy the same run gives 6 failed and
  153 passed, every new witness failing by assertion.

