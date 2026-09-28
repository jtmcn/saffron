# Feedback on run-saffron-spec-loop (twentieth run after the rework, 2026-09-27 to 28)

Eight specs ran as attended cells. Six sit in one chain from `SA-0182` to
`SA-0164`, and three stand alone off `main`: `SA-0184`, `SA-0185` and `SA-0186`.
All eight reached `READY_FOR_REVIEW`. The operator stopped the loop after
`SA-0164`, so eleven queued specs wait for run 21. Run 19's feedback is
checked below.

**Outcome:** eight pull requests, linked and marked ready. The cells cost
**$88.72** against $175 of budget.

| Spec | PR | Spent | Attempts | In-cell blockers | Seat blockers the critic passed | Size after review |
|---|---|---|---|---|---|---|
| `SA-0182` | #559 | $8.65 of $22 | 1 | 1, fixed in REBUT | 0 | 1299 of 3000 |
| `SA-0184` | #560 | $12.96 of $21 | 1 | 1, fixed in REBUT | 1 | 606 of 1300 |
| `SA-0150` | #561 | $14.43 of $22 | 2 | 1, fixed in REBUT | 2 | 2407 of 3000 |
| `SA-0186` | #562 | $13.59 of $21 | 1 | 2: 1 argued, 1 fixed | 1, plus a design defect | 1315 of 1300 |
| `SA-0176` | #563 | $4.71 of $22 | 1 | 0 | 0 | 1032 of 3000 |
| `SA-0185` | #564 | $4.90 of $18 | 1 | 0 | 4 | 693 of 1300 |
| `SA-0160` | #565 | $11.39 of $24 | 2 | 0 | 1 | 2620 of 3000 |
| `SA-0164` | #566 | $18.09 of $25 | 2 | 0 | 4 | 3665 of 3000 |

The operator accepted `SA-0186` at 1315 of 1300 and `SA-0164` at 3665 of
3000. Both run at `standard`, where `size` only advises. `SA-0160` came down
from 3277 and `SA-0164` from 3931 when review trimmed their tests.

## What happened, in order

1. **The operator skipped step 1b.** No spec review ran before a cell, and no
   child was reviewed again at its parent's branch.
2. **`check` blocked two specs.** `SA-0173`'s 100 turns sat below `SA-0180`'s
   peak of 103, and #558 raised it to 130. `SA-0151` priced at 89% of the
   `feature` ceiling at `elevated`. Its estimate came from a measured
   prototype at 64%, and `check` multiplied it by 1.4 again. The operator ran
   it as written.
3. **The live Jev check scored.** `SA-0175`'s refused round scored with 49
   answers under the 85,000 character cap. So b-0e3528 closes.
4. **Gate 0 refused neither `SA-0186` nor `SA-0185`.** The handoff expected the
   second of the two to be refused, since both touch `saffron/task.py`. Each
   cell ran from `main` while the other's pull request was open.
5. **Two wall cuts in eight cells.** `SA-0150` and `SA-0164` ran on chain
   bases without `SA-0184`'s scaled wall. Each first session was cut at 900
   seconds and cost one attempt. Run 19 saw six cuts in twelve.
6. **The seats found blockers the critic passed on six of eight pull
   requests.** Most were witnesses that checked a value by substring, or
   checked one member of a set.
7. **REBUT argued away a real defect on `SA-0186`.** The correctness lens was
   right that the resolver unstacks on any dead newest task. REBUT quoted one
   spec line against another, and the lens withdrew. The operator settled it.
8. **A repair turn wrote a false comment to pass `prose`.** On `SA-0160` it
   split a sentence at a semicolon, and the new sentence called 3600 twice
   300.
9. **`SA-0164`'s plan estimated 1450 lines against its spec's 648.** Its
   base lacks `SA-0185`, so the plan prompt still named no unit. The diff
   landed at 3931 tokens, about 980 lines.
10. **The operator stopped the loop at a capability boundary.** `SA-0164` wires
   `SA-0160`'s revision session. The follow-up specs from `SA-0161` on go to
   run 21.
11. **The auto mode classifier gave no verdict four times** on a `git commit`.
    The loop waited about ten minutes and the fifth try went through.

## Run 19's items, checked

1. **Raise or rethink the IMPLEMENT wall bound:** landed in this run as
   `SA-0184` (#560). Only `SA-0150` hit the old wall, on a base without it.
2. **Make PLAN's estimate carry its unit:** landed as `SA-0185` (#564). No
   plan was refused this run.
3. **Price every spec before its cell:** done by hand in #557. `check` blocked
   two specs before any cell ran. One block was a double count (item below).
4. **`saffron cell` reconciles before it stacks:** landed as `SA-0186` (#562).
   `snapshot` and `next` reconciled before each cell, and every child was cut
   from its parent's reviewed head.
5. **One proxy per cell:** not started. Cells still ran one at a time.
6. **A landed size far under `estimated_lines` is a signal:** not built.
   `SA-0176` landed at 0.76 of its raw estimate and was sound.
7. **The stack batch absorbs the seats' criterion walk:** not yet. The seats
   still found blockers on six of eight pull requests.

## Summary: what to change first

The operator's direction this run: a cell should be reviewed well enough that
no seat review is needed before the next one starts. Each item below moves
part of the seats' work into the cell.

1. **Probe every wrong version the spec lists** (b-7e69d0). The host runs one declared
   mutant per criterion. The seats ran 20 to 70 per pull request, mostly the
   spec's own "these fail it" lists. That would have caught the blockers on
   #560, #561, #564, #565 and #566 in the cell. A spec already carries the list, so
   this is a gate change, not a prompt change.
2. **A REBUT that rests on a spec contradiction escalates** (b-ab4b33). When the argument
   quotes spec text another line contradicts, the task goes to
   `SCOPE_REVIEW` rather than the lens withdrawing.
3. **A standards lens in REVIEW** (b-abeb74). The Standards seat found a comment
   contradicting code, a restated constant, and a citation to a section that
   does not say it. A fourth lens reading `CLAUDE.md`'s conventions against the
   hunks would take these.
4. **`prose` stops rewarding a split sentence** (b-ad1285). A repair turn passed `prose`
   by splitting at a semicolon, and made the comment false. A repair that
   changes a comment's meaning to pass `prose` should read as a finding.
5. **`check` knows a measured estimate** (b-b0a187). `SA-0151`'s prototype was measured
   with `size_gate`, and `check` applied the hand-estimate overrun on top. A
   spec needs a way to say its `estimated_lines` was measured.
6. **`terms` reads a negation** (b-f4eb52). `saffron/intake.py:134` says "Never a ticket",
   and `terms` fails the base on it. The baseline line then reports a red
   base that is advisory.
7. **A loop can be scoped without `drop`** (b-c07b92). Stopping after `SA-0164` took
   eleven `drop` calls. A drop reads as permanent, and item 172 carries drops
   across `--force`.

## Filed from the reviews

Kept findings became b-013138 (row numbering after a trimmed fold), b-30bbd7
(the wall's hour and the turn default spelled twice), b-5ec5c5 (the review
prompt's gate wording), b-64e40c (the review's re-ask witness), b-710086 (the
scheduler comment and §4.2.1 against the resolver), b-713e90 (the `types`
hole) and b-74e564 (the stack batch's restated types and sums).
