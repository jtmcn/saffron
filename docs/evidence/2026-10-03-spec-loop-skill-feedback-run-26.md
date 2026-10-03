# Feedback on run-saffron-spec-loop (run 26, 2026-10-02 to 10-03)

Run 26 ran the rest of the `SA-0161` chain: `SA-0170`, then `SA-0183`, then
`SA-0152`. The operator scoped it to all three and asked for b-d4e015 to be
fixed before any cell. Run 25's feedback is checked below.

**Outcome:** three specs reached `READY_FOR_REVIEW`, each on its first
attempt that reached the API.
- Two detours merged before the first cell. #642 fixed the idle kill, and
  #643 fixed a test that turned `main` red at midnight UTC.
- Three spec PRs merged: #645, #644 and #649.
- The stack is #647, then #648, then #650, with step 5 on top.
- The cells cost **$29.05** against $70 of budget, as the ledger records it.
  `SA-0170`'s cut session reads a floor, and `SA-0152`'s refused start read
  $0.00.

| Spec | PR | Spent | Peak turns | In-cell blockers | Seat blockers the critic passed | Review commits |
|---|---|---|---|---|---|---|
| `SA-0170` | #647 | $6.27 of $23 | 21 of 130, plus one cut session | 0 | 2 | 2 |
| `SA-0183` | #648 | $3.47 of $20 | 26 of 130 | 0 | 0 | 1 |
| `SA-0152` | #650 | $19.31 of $27 | 105 of 200 | 1, fixed in REBUT ($2.68) | 5 | 1 |

## What happened, in order

1. **b-d4e015 was fixed first (#642).** The runner asks the SDK for partial
   messages and emits a `progress` event at most once a minute. Measured
   live, the base runner was silent for 47 seconds while one reply
   streamed. `SA-0170`'s PLAN then passed, with progress events inside the
   cell.
2. **`main` went red at 2026-10-03T00:00Z.** A Jev test assumed a review
   round saved now predates `STARTS`. All three spec writers hit it. #643
   pinned the date.
3. **`SA-0170`'s spec took five rounds.** The operator dropped `--ready`,
   since a ready, open pull request reconciles as `APPROVED`. Rounds 3 to 5
   each found the same printed line false on one more path. The operator
   merged #645 without a sixth round.
4. **The wall bound cut `SA-0170`'s IMPLEMENT** at 1950 seconds, during the
   agent's own run of the whole suite (b-23a149). A repair turn went green.
5. **#647's Spec seat found two witness holes** after the writer had
   measured 25 wrong builds killed. A runner using the process's directory
   and a link refused only on exit 1 both passed.
6. **`SA-0183`'s parent-branch review found nothing**, the first in seven
   runs. `SA-0170` forbade `saffron/ledger.py`, so its parent left the file
   alone.
7. **`SA-0183`'s REVIEW expressed no wrong version** (b-7251b5). Its answer
   was not JSON, so all five read `unproven`, and REVIEW passed. The Spec
   seat ran all five by hand, and the witness killed each.
8. **A scratch build measured `SA-0152`'s criterion 4** at `SA-0183`'s head.
   It killed all eight named builds and found two existing tests the cell
   would break, plus a `types` failure (#649).
9. **`SA-0152`'s first cell never reached the API** (b-031ac2). Preflight
   passed, then every call was refused. The cell ended `NOT_IMPLEMENTED`,
   exit 1. The re-run by path went green.
10. **#650's Spec seat found five criterion 2 holes** after REVIEW expressed
    all 18 declared builds. A layer's state never rendered, and REBUT's own
    fix set a position equal to an index.

## Run 25's items, checked

1. **The idle bound must not kill a session that is still writing
   (b-d4e015)**: absorbed by #642, a runner change, before any cell.
2. **Run the spec's step 1b builds in REVIEW (b-ef8543)**: partly. Every
   queued spec now declares its builds, and two cells expressed all of them.
   The third lost all five to one malformed answer (b-7251b5).
3. **The parent-branch review belongs in `next`**: not absorbed. One of two
   found nothing. The other found a measurement owed, and the measurement
   found three defects.
4. **Keep holds across `snapshot --force` (b-8a6f43)**: not needed. One hold
   was released by the re-snapshot meant to release it.
5. **A child's tree and its prompt carry different spec texts (b-1068ea)**:
   seen again. `SA-0152`'s cell was cut from a tree with the spec before
   #649. The step 5 branch merged `main` to retire the current text.
6. **`driver.py status --line` (b-a7e315)**: not absorbed.

## Summary: what Saffron should absorb next

Each item moves a step the delegate did by hand into a gate, a lens or a
phase. The lines in `.saffron/rejections.md` are the evidence.

1. **Re-prompt a malformed wrong-version answer, and fail loud after
   (b-7251b5).** A phase change. One broken answer turned a measured check
   into none, and only the delegate's reading of the log caught it.
2. **Name a refused API connection infrastructure (b-031ac2).** A phase and
   state change. An unattended night reads it as a task that failed.
3. **A lens that walks each part of a claim to the assertion that tells it
   apart.** All seven seat blockers were a part of a claim no assertion could
   tell from a wrong build. Each got past every declared build, because no
   declared build broke that part. This is b-2750d5's shape at the assertion
   level.
4. **Leave the suite to GATE (b-23a149).** A prompt or phase change. The
   agent spent its wall on a check the host repeats.
5. **The parent-branch review belongs in `next`**, carried from run 23.
6. **Spec review checks each printed line on every path.** A spec-reviewer
   change. Three rounds each found one more path on one line.

## The loop's own gaps

- The seat prompt names the findings block by reference. One seat wrote YAML
  and another wrote rule names as criteria, and Jev refused both. Each was
  scored from a copy, and `REVIEW-PROMPT.md` should spell the JSON shape.
- `next` treats `NOT_IMPLEMENTED` as decided, so an infrastructure failure
  re-runs by path. Run 25 met the same.
- A failed pre-commit hook leaves files staged, so the next commit swept in
  another commit's files twice. Each was split by hand.
- This session's guard refuses edits to another worktree, so review fixes ran
  in the delegate's own worktree, one branch at a time.
- A branch cut before #643 carries the red test, so its push-run CI fails
  while its pull-request run passes. Two spec PRs merged on the second.
