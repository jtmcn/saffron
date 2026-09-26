# Feedback on run-saffron-spec-loop (seventeenth run after the rework, 2026-09-25)

One spec was snapshotted, and it ran to `READY_FOR_REVIEW` in one cell.
Run 16's feedback is checked below.

**Outcome:** one pull request, #519, marked ready. There was nothing to
stack. The cell cost **$16.93** of its $22 budget. A host spike before it
cost $0.15.

| Spec | PR | Spent | Outcome | Step 1b rounds |
|---|---|---|---|---|
| `SA-0141` | #519 | $16.93 of $22 | `READY_FOR_REVIEW` | 1 |

## What happened, in order

1. **The first `status` reported a finished loop as open again.** It showed
   run 16's seven merged pull requests as `READY_FOR_REVIEW`. Only the moved
   spec files read as stale.
2. **Step 1b found no blocker and three concerns.** The completion-check
   count had gone stale when the parents landed. The operator ran it as
   written. Criterion 2's selection was "unmeasured". The delegate measured
   it against a prototype in a detached worktree in about three minutes, and
   four wrong versions failed. The third concern was that `output_format`
   was never measured beside `SA-0140`'s file system prompt.
3. **The operator had the delegate spike the SDK first.** The same pin ran
   on the host with a file system prompt and the production option shape.
   Both turns returned valid values, and a marker word showed the file was
   read. It cost $0.15.
4. **Preflight's tolerated listeners were rediscovered by hand.** Roon and a
   Lima VM still listened on non-loopback ports. The delegate found them with
   `lsof` before the cell, and the operator tolerated both again.
5. **`terms` failed at base.** Its two hits are item b-f4eb52's false
   positive. The skill sends any base failure to the operator, though the
   policy marks `terms` advisory.
6. **The wall bound cut IMPLEMENT, and salvage committed six commits.**
7. **The spec's own notes asked for a `census` failure.** They told the
   cell to drop two parametrised cases. Attempt 1 failed `census` on four
   ids. Neither the log nor `events.jsonl` names them.
8. **Repair got past `census` by pinning stale text into test ids.** At base
   the test took its ids from each prompt's text, so any prompt edit renamed
   its cases. Repair kept the old text as ids, and kept the two cases with
   an inverted assertion. All three lenses reported nothing.
9. **The seats found both workarounds and one unwitnessed line.** The
   operator chose name-only ids. A review commit dropped the two cases and
   pinned the REBUT outcome that proves the drive double copies
   `structured_output`. The Spec seat's probes killed every non-equivalent
   mutant on the nine criteria.

## Run 16's items, checked

1. **The `.claude/` denial (b-e471bd):** not exercised. No spec touched it.
2. **Adopting a by-hand pull request (b-a7e5f3):** not exercised.
3. **Check 3's "unmeasured" for new code:** recurred on criterion 2. A
   prototype closed it cheaply this time, because the change was five lines.
4. **`driver.py` reads stale state (b-bff670):** recurred, point 1.
5. **A stacked branch's stale spec copy (b-c375d6):** not exercised.
6. **Preflight names processes (b-e0cd57):** recurred, point 4.

## Summary: what to change first

1. **`census` accepts a declared removal or rename (item b-f30189).** Two
   runs in a row, a spec's honest test change drove the cell to disguise it.
   A spec field naming the ids it removes or renames is a gate change. It
   ends both the disguise and the review commit that undoes it.
2. **Spec review reads `census` (skill and reviewer text, until item 1).**
   A spec whose notes drop a test id or a parametrised case asks for a
   failure. Check 2 should name it as a `build` blocker.
3. **Gate failure identities reach `events.jsonl` (item b-66e82d).** Attempt
   1's four `census` failures were visible only to the cell. The delegate
   inferred them from the agent's tool calls.
4. **The base-failure rule reads the policy (skill text).** A `fail` at base
   on a gate the policy marks `blocking: false` is a note, not a question.
5. **`driver.py status` reconciles merges (item b-bff670).** Second run in a
   row.
6. **Preflight names what it refuses (item b-e0cd57).**
