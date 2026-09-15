---
id: 88
title: The scoring harness reads a lens three times as harsh as production, and the fixture is a suspect
status: done
tier: 1
closed: 2026-09-08
specs: []
prs: []
commits: ["6d2493d"]
cites: [§5.4, §5.5]
related: [79]
filed: 2026-09-07
---

## Problem

**Tier 1**, directly under 79 — it is 79's own measuring instrument, and 79's
exit criterion is written against an absolute this item puts in doubt.
**Found 2026-09-07**, in the first lens-scoring pass
(`docs/evidence/2026-09-07-lens-scoring-first-pass.md`). Over PR #154's exact
range, the harness's three runs filed anchored blockers 1, 2, 1 — every run
would have routed to REBUT (§5.5). The production run over the same range filed
**zero** blockers and three concerns, and reached `READY_FOR_REVIEW`. Same diff,
same three lenses, same prompts.

A harness that reads a lens as much harsher than production cannot score a
prompt change: the number it moves is not the number the night produces. This
is the harness's own version of item 79, and it sits under Track A rather than
Track C.

Three candidates, in the order they are worth eliminating:

**The frozen `gates.txt`.** All 14 lines read `no tool reported`, because
`gate_results` has no `tool` column to rebuild them from. §5.4 makes `tool`
exactly what separates a gate that ran from one that never did, and
`review.gate_summary` exists so "a critic told a gate passed should be able to
see which did". A lens told fourteen gates ran and not one named a tool has
structural reason to distrust them and dig harder — a bias in precisely the
direction observed. Cheapest to test and the leading suspect.

**Budget and turns.** The original had $3.30 and 90 turns; the pass gave $4.00
and 30. No lens came near either ceiling in either, so this is unlikely, but it
is not held constant and the record says so. *Still open after the second pass,
which held it constant with the first rather than matching production — moving
two inputs at once would have made that pass unreadable.*

**Genuine run-to-run variance**, of which the pass has n=3 over one fixture.
*The surviving candidate, and the second pass sharpened it: the harness now has
n=3 twice and production still has n=1. A single production run that filed zero
is not evidence that production files zero reliably, and no work on the harness
can settle that — only running the range through production again would.*

## Done looks like

a `tool` column on `gate_results`, or a fixture whose
`gates.txt` is captured at review time rather than rebuilt from the ledger —
then one more pass, and the blocker count compared against production's zero.
Until that is settled, the harness's absolute numbers steer nothing; only its
*differences* between two prompts over the same fixture do, which is what Track
C actually needs. Worth saying in the plan, because item 79's exit criterion is
written against an absolute. *Done as written, 2026-09-08: the column, the
repaired fixture and the pass. The comparison came back unchanged, so the
closing sentence is the operative one rather than the fallback it was written
as.*

## Record

*Corrected and repaired 2026-09-08.* Production named **7 of 14**, not 14: six
of the other seven are host-side core gates that execute nothing and report no
tool there too, and `witness` inherits the `tests` tool but skipped a spec that
declares no mutants — so the gap was 7 against 0. `gate_results` now carries a `tool`
column, but the 14 rows predate it and a nullable column is null for every one —
so the fixture was repaired instead, from the tools in the same run's
`baseline.json`, by `docs/evidence/scripts/2026-09-08-sa0062-gate-tools.py`.

**Status: the suspect is eliminated and the gap is unchanged, 2026-09-08**
(`docs/evidence/2026-09-08-lens-scoring-second-pass.md`, $4.84). With the tools
back in `gates.txt` and every other input held, anchored blockers per run are
1, 1, 2 against the first pass's 1, 2, 1 — four either way, every run of both
routing to REBUT against production's zero. Naming the tools moved the count by
**zero**. What is left is the two candidates below that the pass does not
narrow, and the item closes on its own fallback: the harness's absolute numbers
steer nothing, its differences over one fixture do. The `tool` column landed
anyway (`gate_results`, 2026-09-08) so the next fixture needs no splice.

Two things the pass found that the item did not predict, both in the plan now:
the per-defect scores *did* move — `dirty-restore` 2/3 → 1/3, `truncating-write`
3/3 → 2/3 seen — on an input change with no mechanism to make either defect
harder to see, so item 79's exit criterion is written on the noisier of the two
numbers; and production's side of the comparison is **n=1**, which no amount of
work on the harness fixes.
