---
id: 90
title: '`_drive_cell` has doubled since it was born and is over half its module'
status: open
tier: 3
specs: [SA-0003]
prs: []
commits: [0301518, 2b1afda, 3604f31, 851836a, ab8c9d4]
cites: []
related: [5, 97]
filed: 2026-09-08
by_hand: true
---

## Problem

**Status:** open. The gate-suite stack (item 97) takes `_suite`'s assembly and
the `current_tier`/`advisory_gates` pair out of `_drive_cell`; the rest of the
phase sequence stays here.

**Tier 3 — real, not urgent.** Nothing here fails at 03:00 and the function is
green. **Found 2026-09-08**, by static analysis and not by a run: this is a
measurement rather than a gap a live run exposed, and it is filed anyway
because the measurement is monotonic and the file it concerns is the one the
rest of the repo moves underneath.

`_drive_cell` (`saffron/cell/session.py:960`) is **1100 lines** — 53% of its
2059-line module, and 3.1x the next-longest function under `saffron/`
(`package`, 358). It has never been shorter:

| date | commit | module | `_drive_cell` |
|---|---|---|---|
| 2026-08-22 | `851836a` | 916 | 513 (born) |
| 2026-08-25 | `3604f31` | 1154 | 678 |
| 2026-08-31 | `0301518` | 1358 | 772 |
| 2026-09-03 | `2b1afda` | 1812 | 1082 |
| 2026-09-08 | `ab8c9d4` | 2059 | 1100 |

Seventeen days, 2.1x, every sample up. `session.py` is also the most-churned
file here — **93 of the 348 commits** touching `saffron/`, 1.8x the next
(`cli.py`, 53).

What makes it worth filing rather than noting: the function inlines the phase
sequence — preflight, `cell_up`, the baseline suite, the plan checkpoint,
IMPLEMENT, salvage, the repair loop, REVIEW, REBUT, teardown — while
`saffron/phases/` exists as the home for exactly that, and `implement.py`,
`review.py` and `rebut.py` are each already extracted. The seam is established
and this is what did not go through it.

Two costs are already on the record. **The distance is being paid in comments:**
`current_tier` and `advisory_gates` are bound at `:1113` and read at `:2016` —
903 lines apart — and the gap needs the seven-line comment at `:1105-1112`
arguing the path between them is unreachable. `ty` passes, but a checker
configured outside this repo reports both as possibly-unbound, which is what a
reader who has not found that comment sees. **And a patch's shelf life is
measured against this file:** item 5 records `SA-0003`'s patch no longer
applying because "three hours of commits moved `session.py` underneath it". The
most-churned file is the one a packaged patch is likeliest to be invalidated by,
and it is 27% of all movement under `saffron/`.

## Done looks like

`_drive_cell` reading as the phase sequence it drives, with
the phases that have no module of their own living beside `implement.py`,
`review.py` and `rebut.py`. Not a line count: the test is whether one phase can
be read without the 900 lines around it, and whether `current_tier`'s binding
and its use fit on one screen. Worth doing by hand rather than through a cell —
it is a pure refactor of the most load-bearing function in the control plane,
the suite guarding it is 1562 tests, and a cell's own diff here would be the
hardest this repo has asked a critic to read.
