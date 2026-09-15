---
id: 97
title: A delegate's review fixes reach a task's pull request and no gate, critic or record
status: done
tier: 1
closed: 2026-09-10
specs: []
prs: [189]
commits: []
cites: [§5.1, §5.4]
related: []
---

## Problem

**Status: the minimum is done, 2026-09-10; the re-gate is open.** `reconcile`
asks `gh` for `headRefOid` beside `state` and names every pending pull request
whose head is not the `pushed_sha` PACKAGE recorded, on every command that
prints a reconcile summary. It writes no state. Measured first: 34 of this
repo's 38 packaged pull requests merged at a head other than the one PACKAGE
pushed, 10 of them over a rewritten history
(`docs/evidence/2026-09-10-review-fixes-past-package.md`). Still owed: the
task's gates, from the same `base_sha` export, over the new head — and a
*record*. A merge over a moved head is printed once, by whichever command saw
it, and the row that becomes `MERGED` keeps no trace of the head it merged at.
The re-gate's first half is the gate-suite stack begun 2026-09-10: one module
that runs a gate suite on any tree and returns a suite comparison, adopted by the
session and then by PACKAGE, so the re-gate is its third caller rather than a
third hand-built suite (principle 54). The record stays this item's: a
`gate_results` row needs an attempt or a run, and a re-gate has neither.

**Tier 1 — soundness.** Found naming the delegate (PR #189, 2026-09-10).
`run-saffron-spec-loop` steps 2c–2e have a delegate check out `saffron/SA-NNNN`
after PACKAGE, act on the in-cell critic's findings, run `make check` on the host,
commit `review(SA-NNNN): …`, and push. The 2026-09-07 re-sort's premise — every
spec pull request needed a human review round after packaging — is these commits.

None of what judged the cell's work judges them:

- **Gates.** The cell's gates ran from `/gates`, `.saffron/` exported read-only at
  `base_sha`, with baseline subtraction (§5.1, §5.4). `make check` runs the
  branch's own tests and lint configuration, so a fix can weaken the check it is
  judged by.
- **`scope`.** Nothing compares the fix against the ratified `touches` set.
- **The critic.** The fix is never reviewed adversarially, and the next reader
  sees the findings as addressed.
- **The record.** The task's gate results describe the cell's diff, not the pull
  request's head, and `DelegateShape` forbids recording a delegate's work as an
  attempt — so nothing says who wrote the commits above the packaged ones. The
  merge train, which would re-gate at merge, is not built (*What is not here*),
  and the documented path is `gh pr ready` then `gh pr merge`.

**Done looks like** a pull request whose head has moved past what PACKAGE pushed
being visible as such — at minimum to `saffron reconcile` or the queue line, which
needs the packaged head recorded (whether the ledger already holds it is the first
thing to check). The fuller version runs the task's gates, from the same
`base_sha` export, over the new head before `READY_FOR_REVIEW` is allowed to
stand. Either way the review fix lands somewhere the record can see.
