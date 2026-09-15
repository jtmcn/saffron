---
id: 47
title: Every gate attempt in `events.jsonl` claims zero commits and zero spend, and part 3 is built to read it
status: done
tier: 1
closed: 2026-09-11
specs: [SA-0034, SA-0035, SA-0039, SA-0041, SA-0042]
prs: []
commits: []
cites: [§6]
related: [97]
by_hand: true
---

## Problem

`cell/session.py` emits an `Attempt` for each GATE and REBUT decision with
`commits=0, spent_usd_est=0.0` — four call sites — and the rebuttal-time gate
events additionally hardcode `attempt=1`, which is wrong whenever the repair
loop has already reached attempt N.

None of it is visible. `describe`'s `Attempt` branches return on `aborted`,
`drift`, `new_failures`+`decision`, or `new_failures` before ever reaching the
fallthrough that renders `commits` and `spent_usd_est`, so the terminal is
correct, the golden fixture is indifferent, and no test can see the fields at
all. The defect is entirely in what the log *keeps*.

This is filed now because of who reads it next. `SA-0035`–`SA-0039` build §6's
pages from exactly this data, and a page that sums a column of zeros and one
running total will render a confident wrong number rather than fail. `SA-0034`
is the neighbouring case for the ledger; this is the same question for the log.

Done looks like `commits` and `spent_usd_est` being `int | None` and
`float | None` on `Attempt`, set only where they were measured, and the
rebuttal path carrying the attempt number it actually ran at. That needs
`saffron/events.py`, which `SA-0041` and `SA-0042` both forbid — so it is
either a spec of its own or the first thing part 3's first spec does.

## Record

Two consequences, both for a reader rather than an operator:

- **`0` cannot be told from "not computed".** `events.py` sets the opposite
  convention two dataclasses away, in as many words: *"`None`, never `0`: a
  skipped or errored gate had no count computed."* `Attempt.commits: int`
  cannot express it, so a consumer reads a real zero and a missing measurement
  identically.
- **Summing `spent_usd_est` across rows is wrong twice over** — the gate rows
  contribute nothing, and the IMPLEMENT row is *cumulative*, not incremental.
  Measured on `SA-0041`, 2026-09-02: it emitted `IMPLEMENT: 6 commit(s), $11.31
  spent`, and the ledger's attempts for that task read $2.457 and $8.856. The
  line is the running total, so two IMPLEMENT rows in one run double-count.

**Status:** **done**, by hand, 2026-09-11 — the gate-suite stack's last layer
(item 97). `Attempt.commits`/`spent_usd_est` are `int | None`/`float | None`,
required, and `None` on every GATE and REBUT line; only the IMPLEMENT turn
measures them. The rebuttal's gate check carries the loop's final attempt + 1,
continuing the gate count — decided over the ledger row's `n` and over keeping
`1`. The IMPLEMENT row's spend is still the running total, not an increment.
Every `events.jsonl` written before this carries `0` on its GATE and REBUT
lines, still indistinguishable from a measurement: a reader of old logs (§6's
pages) must treat those two fields there as unmeasured.
