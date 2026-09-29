---
id: 94
title: A probe's baseline failures are subtracted and then discarded
status: done
closed: 2026-09-29
tier: 1
by_hand: true
specs: [SA-0054, SA-0063]
prs: []
commits: [f76931df]
cites: []
related: [93, 106, 173]
filed: 2026-09-09
---

## Problem

**What is not done, and does not go quiet here:** the *explanation* for the two
cell-only skips. `baseline_summary` is the line that will carry them from the
next pass onward; nothing yet says why a tree that runs `1502 passed` on the
host reports `2 skipped` in the cell, and the unexplained 5.7x sits beside it.
This item bought the record, not the reason.

**The two unauditable vacuities stay unauditable, and that is now pinned rather
than promised.** `test_the_baseline_pass_s_verdicts_carry_no_baseline_and_never_will`
asserts every shipped verdict carries no baseline key.
The value was always entirely forward — the argument for landing it early.

**Tier 1 — it bears on whether a `survived` verdict means anything.** Filed as
tier 3 on 2026-09-09 and moved the same day, when the measurement below turned it
from an auditability gap into a correctness one.

**The cell's baseline can be red for reasons the host is not, and nothing records
which.** `SA-0063`'s head (`f76931df`) runs **`1502 passed`** on the host — run
directly, in a detached worktree, 107.31s — where the cell reports `1 failed,
1499 passed, 2 skipped` at the same 1502 collected. So one failure and two skips
exist only in the cell, and the failure's identity is written nowhere: not in
`gates.txt`, which carries the summary line only, and not in `probes.json`, which
keeps only what survives the subtraction. Every `survived` in the corpus is
computed against a baseline of that kind, and the two symptoms sit beside the
unexplained 5.7x in the same place.
`check_probe` holds the baseline `GateResult` to subtract from, and
`probes.json` persists only what survives the subtraction (`failures`). So a
`survived` over a head whose suite was already red cannot be checked by anyone
reading the record.

Measured at the baseline pass: the subtraction cancels that failure and both
probes record `failures: []`, which is correct — no *new* failure. But whether it
is in the very test that would have caught the mutation is undecidable from the
record, and if it is, the cancellation masks a kill. That is **2 of the
baseline's 8 verified vacuities**, and **no re-run can settle those two**: a probe
is authored by the lens per run — `SA-0054`'s re-run named two *different* edits —
so re-running yields different probes rather than an audit of these.

## Done looks like

`ProbeResult` carries the baseline's failure identities beside
the new ones, and `probes.json` writes them. Additive, and the value is already
in `check_probe`'s hand — the same shape as the `tool`/`collected`/`summary`
fields, which exist because a verdict that keeps nothing about the suite that
answered it cannot be re-read. **Land it before the next pass, not before pass
3**: item 93 needs a further pass to establish this metric's resolution, and that
pass should not be spent producing more verdicts nobody can audit. Adding the
field cannot retroactively populate a pass already run, so this baseline's two
stay unauditable whatever happens here — the value is entirely forward, which is
the argument for landing it early rather than the argument for deferring it.

Worth pairing with it: the cell's own baseline summary line, and an explanation
for the two cell-only skips. A `survived` over a baseline that skipped the
relevant test is the same defect wearing a different hat.

## Record

**Status:** **done bar the explanation**, 2026-09-09, by hand. The recording
half, which is what "done looks like" below specifies, is done: `ProbeResult`
carries a `BaselineRecord` — the baseline's failure identities, tool, collected
count and summary line — and `probes.json` writes it as `baseline_failures`,
`baseline_tool`, `baseline_collected` and `baseline_summary`. A `None` record
is not one with no failures, and on disk `null` is not `[]`: no baseline in
hand against one read and green. Every path records the baseline it had,
refusals and a raise out of `check_probe` included, and both spellings are
pinned, because collapsing them reads the baseline pass's ten silent verdicts
as ten green baselines.

- 2026-09-29: the explanation half is done, by hand. `f76931df` ran in
  `saffron/cell:saffron` and printed the pass's own line, `1 failed, 1499
  passed, 2 skipped, 21 deselected`.
- The failure is
  `test_structure_errors_when_its_tool_is_present_but_not_runnable`. Items 106
  and 173 found its cause, a cell image with no `/usr/bin/python3`.
- The two skips are `tests/test_intake.py:153` and `tests/test_policy.py:109`.
  Each tests an unreadable file and skips under uid 0. The cell sets no `USER`,
  so it runs as root. The host runs as a user and skips neither.
- Both `SA-0063` probes mutate the notes turn in `saffron/cell/session.py`.
  The failing test covers the `structure` gate, and the skipped ones cover spec
  and policy loading. None reaches the mutated code, so the subtraction masked
  no kill. The two survivals are vacuities, and the pass's `8` stands.
- Current `main` reads `2948 passed, 2 skipped` in the same image. The two root
  skips stay in every cell. A probe that mutates the unreadable-file error in
  `load_spec` or `load_policy` would survive there and die on the host.
