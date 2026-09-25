# Feedback on run-saffron-spec-loop (sixteenth run after the rework, 2026-09-23 to 25)

Nine specs were snapshotted. Seven ran to `READY_FOR_REVIEW` as cells, and
one more was taken by hand after its cell could not edit its own `touches`.
`SA-0140` merged ahead of the others by the operator's call, and `SA-0129`
merged by hand. Run 15's feedback is checked below.

**Outcome:** stack of seven pull requests (#507, #510, #514, #504, #512,
#515, #505), linked, chained and marked ready. #501 and #502 merged ahead of
it. Cells cost **$79.61** against $214 of their budgets.

| Spec | PR | Spent | Outcome | Step 1b rounds |
|---|---|---|---|---|
| `SA-0140` | #501, merged | $12.08 of $20 | `READY_FOR_REVIEW` | 4 |
| `SA-0129` | #502, merged | $1.77 of $20 | `NOT_IMPLEMENTED`, taken by hand | 2 |
| `SA-0134` | #507 | $3.59 of $20 | `READY_FOR_REVIEW` | 4, two at the parent |
| `SA-0135` | #510 | $9.12 of $27 | `READY_FOR_REVIEW` | 2, one at the parent |
| `SA-0136` | #514 | $7.80 of $36 | `READY_FOR_REVIEW` | 4, three at the parent |
| `SA-0139` | #504 | $8.42 of $20 | `READY_FOR_REVIEW` | 1 |
| `SA-0133` | #512 | $16.22 of $25, plus $4.91 rate-limited | `READY_FOR_REVIEW` | 3, two at the parent |
| `SA-0138` | #515 | $13.19 of $30 | `READY_FOR_REVIEW` | 3, two at the parent |
| `SA-0137` | #505 | $2.51 of $16 | `READY_FOR_REVIEW` | 1 |

## What happened, in order

1. **The first `status` reported a finished loop as open.** It read run
   15's snapshot and showed five merged pull requests as `READY_FOR_REVIEW`.
   It named the moved spec files as stale, but not the merges.
2. **Step 1b found one blocker in nine specs, and every review raised the
   same two concerns.** Four specs cited the `size` ceiling SA-0128 had
   replaced. Every spec whose code is new drew an "unmeasured arrangement"
   concern, which the delegate can close only by writing the implementation.
   The delegate measured SA-0137's, the one whose helpers existed, in two
   minutes.
3. **The delegate's own edits carried findings again.** SA-0134's round 3
   found the round-2 edit left a false sentence about a sibling spec.
   SA-0136's round 3 found the delegate's own review commit on the parent
   had made the spec's description of `run_task` false. SA-0140 took four
   rounds, each closing a witness hole the last edit left.
4. **A merged sibling broke a queued spec's witness.** SA-0140 put a random
   `uuid4` path into every request. SA-0133's criterion 4, reviewed at
   `main` before SA-0140 merged, claimed two cells log equal request digests.
   The parent-branch review caught it before the cell ran.
5. **The operator merged SA-0140 before any other cell.** Its verdict prompt
   fix only helps once the host runs it. The first cell after it, SA-0129,
   was the first to run on the new host code.
6. **Three cells failed to start, at no cost.** The container service was
   down (XPC). Then preflight's N1 probe refused on Roon's RAATServer at
   `*:9200` and a Lima VM at `*:53`. The operator chose to tolerate both.
   `lsof` truncates the first to `RAATServe`, and the refusal names ports,
   not processes. Each failed start left an `ORPHANED` row.
7. **SA-0129's cell could not edit `.claude/`.** The cell's CLI refuses
   every write under `.claude/` in `dontAsk` mode. SA-0116's cell hit the
   same denial on 2026-09-21 and wrote the file with `python3` from Bash.
   SA-0129's agent stopped instead. A host A/B on the cell's SDK pin
   denied the edit with the system prompt as a string and as a file, so
   SA-0140 was cleared. The operator had SA-0129 taken by hand.
8. **A by-hand merge could not satisfy a child.** `saffron queue` refused
   SA-0134 because SA-0129's only row read `NOT_IMPLEMENTED`. Retiring the
   parent's spec to `done/` early was the way through (#503).
9. **SA-0133 hit the plan's rate limit, then its turn ceiling.** Its first
   run stopped `RATE_LIMITED` at $4.91. The limit reset early, and the
   re-run spent all 160 turns in IMPLEMENT before a repair turn went green.
10. **SA-0126's salvage turn recovered work twice.** SA-0135's and
    SA-0138's IMPLEMENT sessions were cut by the wall bound. Salvage
    committed what they had.
11. **SA-0138's defect showed up live, twice, before SA-0138 merged.** On
    SA-0133 and on SA-0138 itself, the adequacy lens's probe was counted
    `killed` by a test other than the criterion's witness, and its finding
    was demoted to a note. The Spec seat showed both probes survive their
    own witness.
12. **Every pull request needed a review commit.** The seats found five
    blockers and a set of concerns the critic missed, each verified with
    `driver.py probe` before and after the fix.
13. **The auto-mode classifier refused `gh pr merge`** under the operator's
    standing grant for spec-edit pull requests. An in-chat approval
    cleared it each time after that.
14. **The linked stack was seven siblings, not a chain.** The step 5 branch
    could not hold the pull requests below it, so its queue smoke test
    pinned the wrong state. The operator had step 4 run: every layer's
    patch-id matched, and one leased push moved all seven.

## Run 15's items, checked

- **b-19b255** (a probe killed by any failing test): SA-0138 delivered it
  (#515). Point 11 is its evidence from this run.
- **b-8487de** (the verdict prompt on argv): SA-0140 delivered it and
  merged (#501). No verdict session halted this run.
- **b-6377cf** (a survivor at base subtracted): SA-0139 delivered it (#504).
- **Step 1b fixes a witness concern in the spec:** done for every spec. It
  cost more rounds, point 3.
- **b-440f17:** did not recur.

## Summary: what to change first

1. **The `.claude/` denial (item b-e471bd).** A spec whose `touches`
   include `.claude/**` depends on the agent routing around a denial.
   Either the host grants those paths explicitly, or intake refuses such a
   spec. A gate or phase change, not skill text.
2. **Adopting a by-hand pull request (item b-a7e5f3).** The ledger has
   no way to say a task's spec merged through a pull request its cell did
   not open. The early retirement in #503 is the workaround.
3. **Check 3 stops raising "unmeasured" for code that does not exist at
   base (skill and reviewer text).** Every new-code spec drew it, and only
   the Spec seat's probes can close it. Point 2.
4. **`driver.py` reads what changed (item b-bff670, with b-e8027b).** `status` reconciles
   merges, `snapshot --force` keeps a hold whose pull request is open, and
   `history`/`check` read the spec from the branch under review.
5. **A stacked branch's own spec copy is stale (item b-c375d6).** The
   Spec seat on #514 read the branch's copy and raised a concern the merged
   spec had already dropped.
6. **Preflight names what it refuses (item b-e0cd57).** Name the
   process behind each port, and check the runtime before creating a task
   row.
