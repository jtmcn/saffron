# Feedback on run-saffron-spec-loop (run 28, 2026-10-05)

Run 28 ran five specs: `SA-0200` to `SA-0204`. Four of them fix bugs runs 24
and 26 filed against the loop's own path. Run 27's feedback is checked below.

**Outcome:** four specs reached `READY_FOR_REVIEW`, and one ended `EXHAUSTED`.
- Spec PRs #665 to #668 merged before the cells. #677 carried `SA-0204`'s
  parent-branch edits. #664 merged `SA-0205` from another session.
- The stack is #679: #673, then #675, #676, #678 and #674, with step 5 on top.
- The cells cost **$114.09** against $132 of budget, as the ledger records it.
  `SA-0204` spent $38.72 of $33.

| Spec | PR | Spent | Peak turns | In-cell blockers | Seat findings the critic passed | Review commits |
|---|---|---|---|---|---|---|
| `SA-0201` | #673 | $18.91 of $22 | 121 of 120, one repair | 0 | 3 | 1 |
| `SA-0202` | #675 | $19.93 of $31 | 139 of 180 | 0 | 3, one filed | 1 |
| `SA-0203` | #676 | $27.23 of $32 | 78 of 150 | 1, fixed by REBUT ($3.85) | 4, one filed | 1 |
| `SA-0204` | #678 | $38.72 of $33 | 181 of 180, repairs | 3, REBUT refused on budget | 2 | 1 |
| `SA-0200` | #674 | $9.30 of $14 | 46 of 60 | 0 | 1 | 1 |

One more finding, three stale sentences, belongs to both #676 and #678
(b-edcab7). The seat counts are the lines in `.saffron/rejections.md`.

## What happened, in order

1. **The cells ran bottom up.** `SA-0201` started at 23:10 on 2026-10-04.
   `SA-0200` and `SA-0202` followed, each green on its first start.
2. **`SA-0203`'s first start exited 2 while it seeded its worktree.** Git in
   the cell got "Permission denied" on `f61da02f`. The task read `ORPHANED`
   at $0.00, and a retry a minute later worked (b-6ac0cd).
3. **`SA-0203`'s REVIEW and REBUT worked in the cell.** The adequacy lens filed
   one blocker on a probe that survived. REBUT fixed it for $3.85.
4. **A parent-branch spec review found a real defect in #676.** `SA-0204`'s
   review read `SA-0203`'s code. A REBUT session the SDK cut at the cap never
   marked the cap refused, so the task halted at `REBUTTING`.
5. **The delegate's own edits to `SA-0204` opened witness holes.** A spec review
   caught them before the cell, and #677 carried the fix.
6. **`SA-0204`'s first cell hit b-031ac2 live.** Its plan turn ended
   `success/api_error` at $0.00 after ten `api_retry` events. The host ran
   without #673, so the task ended `NOT_IMPLEMENTED`.
7. **`SA-0204`'s second cell hit b-4c5dc7, then b-038aef.** REVIEW ran past the
   budget, and REBUT was refused on budget. The task ended `EXHAUSTED` with no
   pull request. These are the bugs the stack below it fixes.
8. **The delegate opened #678 as a draft by hand.** `stack`, `size` and
   `rebase` refuse an `EXHAUSTED` task (b-2247dd). The delegate linked the layer
   by hand and measured 2921 of 3000 tokens with `size._changed_lines`.
9. **REVIEW measured nothing on `SA-0200`.** Its fix is to two test files. All
   14 wrong versions ended `unproven`, and the line read "13 expressed"
   (b-34d743).
10. **A Standards seat called an alias redundant.** The alias captured a
    monkeypatch, and removing it broke the test.
11. **The seats found eleven changes the critic passed.** Six were witnesses
    that could not fail. Four were false docstrings, comments or citations.
    One was the `REBUTTING` halt.
12. **Jev scored no round.** The worktree guard refuses sourcing
    `TYPESAFE_API_KEY`, so every review round went unscored.
13. **The token reached each cell through a user-settings allow rule.** The
    rule names a token-only env file.

## Run 27's items, checked

1. **A check that each witness drives its claim and notes (b-20043f)**: not
   absorbed. Seen again: six of the eleven seat changes were witness holes.
2. **Read an interrupted pytest session as `fail` (b-970f53)**: not absorbed.
   Run 28 recorded no sighting.
3. **Refuse a second `depends_on` entry at intake (b-c94a2f)**: not absorbed.
   Seen again: `SA-0204` names `SA-0198` second. It was merged, so it cost
   nothing this time.
4. **Show the operator which criterion failed (b-3b8eb2)**: not absorbed.
5. **Probe the host before a cell starts (b-835bfb)**: not absorbed. No host
   listener stopped a cell.
6. **Tell a test-side wrong version from an unproven one (b-3c17ab)**: seen
   again, worse. `SA-0200` expressed 13 versions against tests, and the probe
   refused every one (b-34d743).

Run 27's loop gaps:

- **The delegate's witness edits need a measurement**: seen again on `SA-0204`.
  A review caught the holes before the cell.
- **The session's guard refuses** loops over a variable and heredocs with
  backticks. It refused step 5's own scripts, and Jev's key.
- **`bookkeeping` could not step the ordinal**: half fixed. `SA-0200` lets a
  retirement owe no change. Adding a spec still needs an ordinal that
  `_ORDINAL_PHRASE` cannot read (b-7eb6d3).

## Summary: what Saffron should absorb next

Each item moves a step the delegate did by hand into a gate, a lens or a
phase. The lines in `.saffron/rejections.md` are the evidence.

1. **Run a wrong version against a test file (b-34d743).** A REVIEW change.
   A spec whose subject is a test gets no measured check, and the line hides it.
2. **Let `reconcile` read an `EXHAUSTED` row with a pull request (b-8e30bd).**
   A reconcile change. `SA-0204` now opens such drafts, and each merged one
   leaves its dependents refused.
3. **A check that each witness drives every part of its claim (b-20043f).** A
   lens change. Six seat changes in run 28 were witnesses that could not fail.
4. **Print no stopping line before a REBUT that runs (b-444bed).** A session
   change. One log now reads stop, then run.
5. **One re-prompt helper for REVIEW (b-708c8a).** A refactor that item 97
   keeps out of a review commit.
6. **Find why git in a cell is refused a loose object (b-6ac0cd).** It cost a
   whole cell in run 23 and a start in run 28.

## The loop's own gaps

- **The driver treats only `READY_FOR_REVIEW` as a layer (b-2247dd).** Every
  `EXHAUSTED` draft `SA-0204` opens will need `stack`, `size` and `rebase` by
  hand.
- **Jev cannot run from a worktree.** The guard refuses sourcing its key, so
  `labels` has nothing to grade.
- **A seat's advice needs a run before the delegate takes it.** The redundant
  alias held a monkeypatch, and only the test said so.
- **A parent-branch spec review reads code already reviewed.** It found the
  `REBUTTING` halt in #676. `next` should run it.
