# Feedback on run-saffron-spec-loop (run 23, 2026-09-30)

Run 23 queued twelve specs: `SA-0196` and the eleven of the `SA-0161`
chain. The operator chose `SA-0196` first, then the chain through
`SA-0162`. Four ran as attended cells, and all four reached
`READY_FOR_REVIEW`. `SA-0162` did not run. Its parent-branch review found
holes that need a spec revision, and the operator handed it to the next
loop. Run 22's feedback is checked below.

**Outcome:** a stack of four pull requests, #610 ← #618 ← #622 ← #608, with
step 5 on top. Every pair merges cleanly, and the whole stack merged onto
`main` at `6d756af9` passes `make check` (3047). The cells cost **$75.98**
against $86 of budget. `SA-0161`'s first start lost $14.63 to an
infrastructure failure. Two spec PRs merged mid-loop: #612 for `SA-0173` and
#619 for `SA-0165`.

| Spec | PR | Spent | Starts | In-cell blockers | Seat blockers the critic passed | Size after review |
|---|---|---|---|---|---|---|
| `SA-0196` | #608 | $9.67 of $24 | 2, one preflight refusal | 0 | 2 witness | 1310 of 3000 |
| `SA-0161` | #610 | $20.30 of $24, plus $14.63 orphaned | 2, one orphaned | 2, both fixed in REBUT | 2 witness | 3752 of 3000, accepted |
| `SA-0173` | #618 | $13.08 of $16 | 1 | 1 host probe, withdrawal refused | 1 witness, plus the host's | 947 of 3000 |
| `SA-0165` | #622 | $18.30 of $22 | 1 | 0 | 4 witness | 2331 of 3000 |

## What happened, in order

1. **`snapshot --new` put nine chain specs before `SA-0196` again.** One
   `hold` on `SA-0161` gave the operator's order (b-c07b92, second run in a
   row).
2. **`check` blocked `SA-0151` on size again**, 515 × 1.54 = 3176 of 3000.
   The operator kept run 22's call to run it as written.
3. **`SA-0196`'s first start exited 2 at preflight.** RAATServer (Roon)
   listened on `*:9200`. The refusal named the address and not the process.
   The operator tolerated it, spelled `RAATServe` after `lsof`'s truncation
   (b-2dc561).
4. **#606 made main's `tests` baseline green in cells** (b-7a70fd).
   `terms=fail` at base on one disavowal is all that stays red (b-4ddb5b).
5. **`SA-0161`'s first start went green, then died seeding its gate cell.**
   A loose object in the mirror read `Permission denied` once. The ledger
   recorded `ORPHANED`, and the $14.63 patch could not be resumed (b-f582ee).
6. **REBUT refused a lens's withdrawal of a host probe blocker** on
   `SA-0173`'s `preserves` criterion. #596 (b-cd5fd2) worked. The
   implementer was right that the gap predated the task, and the seat fixed
   the witness inside `touches`.
7. **Each parent-branch review found something a cell would have paid for.**
   - `SA-0173`'s found a wrong build its witness passed (#612).
   - `SA-0165`'s found a listed wrong version equal to the right build
     under the real walk (#619). Its round 3 found two false sentences in
     the delegate's own edit.
   - `SA-0162`'s found two witness holes and an undefined case reaching
     `SA-0173`'s `SY-90` test. The operator handed `SA-0162` to the next
     loop.
8. **The seats found a witness hole the critic passed on every PR.** That is
   10 blockers across four pull requests, besides doc fixes. `SA-0165`'s
   in-cell REVIEW was fully clean, and its Spec seat found four.
9. **`SA-0165`'s implementer used 129 of its 130 turns.** Its peak
   IMPLEMENT session finished one turn under the ceiling. `SA-0173` used 104
   of 130. The chain's next children carry similar ceilings.
10. **`main` moved six times mid-loop.** It took #607, #609, #611, #613 to
   #616, #620 and #621, as well as the two spec PRs. The order never went
   stale, and every branch merged cleanly onto the result.
11. **Auto mode refused `gh pr merge` on both spec PRs** (`Merge Without
    Review`), with the operator's yes. The operator merged each by hand.

## Run 22's items, checked

1. **b-8170eb**, an agent that never reached the API: no start hit it this
   run. Zero `api_retry` lines in five starts.
2. **b-a6bfb0**, refused API calls after preflight: not seen.
3. **b-66d1c3 and b-cd5fd2**, REVIEW changes merged before the stack:
   b-cd5fd2's REBUT fix was seen working (step 6 above). b-66d1c3 closes
   with `SA-0196` (#608).
4. **b-ef8543**, wrong builds in prose: open. `SA-0165`'s list held a
   version equal to the right build, which only a hand trace found.
5. **b-7a70fd**, main's in-cell red: closed by #606.
6. **b-c07b92**, `snapshot` takes the operator's order: not absorbed. One
   `hold` again.
7. **The handoff step**: followed, and started early.
8. **A step 1b note that names a surviving wrong build**: applied as a fix
   in both spec PRs.

## Summary: what Saffron should absorb next

Each item moves a step the delegate did by hand into a gate, a lens or a
phase. The rejection lines in `.saffron/rejections.md` are the evidence.

1. **REVIEW's adequacy lens misses most witness holes the Spec seat finds.**
   Ten seat blockers on four PRs, and a fully clean in-cell REVIEW on
   `SA-0165`. Every one was found the same way: mutate the line, run the
   named witness, watch it survive. That is mechanical. The host already
   runs criterion probes for declared wrong versions. A host pass that
   probes each criterion's satisfying lines, as the Spec seat does, would
   move most of this from bucket 3 to bucket 1.
2. **A transient failure after green is infrastructure, not an orphan**
   (b-f582ee). Retry the seed once and keep the patch packageable.
3. **The parent-branch review belongs in the loop's machinery.** Three of
   three runs found a real defect. Today the delegate dispatches it by hand
   and merges the fix through the operator. `next` could refuse a child
   whose spec has no clean review recorded at its parent's head.
4. **`snapshot` takes the operator's order** (b-c07b92). It is the third run
   in a row to need a `hold`.
5. **Preflight names the listener's process** (b-2dc561). It is cheap, and
   it costs a round trip every time a new listener appears.
6. **`terms` passes at base** (b-4ddb5b).

## Filed from the reviews

- b-f582ee: a transient seed failure after green orphans the task.
- b-00534f: `qualify` reads an unreadable path as absent.
- b-979dbe: three copies of the attempt charge, and two diff pinnings.
- b-4ddb5b: `terms` reads a disavowal as a use.
- b-2dc561: preflight names an address, not a process.
- b-a09d30: the loop's REVIEW lines miss a bug-type ancestor and disagree on
  staleness.
- Dated lines went on b-792ab2, b-466005, b-1adb50 and b-cd5fd2. b-66d1c3
  is closed.

## The loop's own gaps

- Merging a spec PR is blocked in auto mode, even with the operator's yes.
  Each spec PR costs a round trip.
- Saving a subagent's report verbatim still needs a transcript extractor.
  This run wrote one again.
- `driver.py probe` refuses a `--find` that matches twice. That is right,
  but the seats' indentation-specific strings were needed to reach a line.
- The step 5 branch sits on `SA-0196`, which was cut before two spec PRs
  edited the specs it retires. It merges `main` in to avoid a modify/delete
  conflict, so its diff shows `main`'s changes until the lower layers merge.
