# Feedback on run-saffron-spec-loop (second run after the rework, 2026-09-14)

Stack of four: SA-0087 → SA-0088 → SA-0089 (a chain), and SA-0086 on its own. Run
from the main checkout, driver as of `c527e64` (after #254). The first run's
feedback is `2026-09-14-spec-loop-skill-feedback.md`; its item numbers are cited
here as "run 1, item N".

**Outcome:** one reviewable pull request (#255, `SA-0086`), and $30.41 spent over
three cells: $7.99 on SA-0086 and $22.42 over SA-0087's two. The operator dropped
the SA-0087 chain after its second cell halted at `REBUTTING`. The backlog items
this run filed are 119–122.

## Summary: what to change first

Ranked by what each cost this run.

1. **The skill has no path for a cell that halts at a ceiling** (observations 3, 4,
   11, 13, 14). It cost three of the four specs and $22.42. GOTCHAS calls a
   turn-ceiling line non-terminal, though here it was terminal. `record` waits
   forever on a halted `REBUTTING`. Nothing says how raising a spec's ceilings
   gets a spec back into the order. Fix: Recording bullets for
   `cut_off_no_salvage_room` and for a `REBUTTING` halt. Each routes to the operator
   as "raise the ceilings and re-run, take the branch by hand, or drop the chain",
   and says that a child cannot stack on a `REBUTTING` parent. `record` should
   treat an in-flight state after the process exits as a halt.
2. **The Monitor** (observations 2, 7, 12). It expires at 30 minutes, which is
   shorter than a cell. `pattern` also leaves out the `budget:` line that says
   whether a turn-ceiling line is the end.
3. **Small refusals and gaps** (observations 1, 8, and run 1's item 2, still
   open). `snapshot` refuses to replace an order whose every PR merged. The dry
   `stack` errors on the first PR. The allowlist is still outside the command
   block.

**What worked and should stay:** the up-front push question, `snapshot`'s table,
`next`'s hold-back note, `record`'s spend line, `status`'s `reviewed` column, and the
two seats. Each seat found a defect on #255 that three clean lenses missed, and
they overlapped on only one finding.

## Run 1's items, checked against this run

| Run 1 item | Status here | Evidence |
|---|---|---|
| 1 sibling-note count | fixed | "2 specs declare no depends_on … `rebase` would chain the 1 above the bottom one" |
| 2 allowlist outside the command block | not fixed | 2a still names it in a sentence after the block; I put it on the command from memory |
| 3 push question asked twice | fixed | one multi-select up front (ordinary / leased force / step-5 branch + PR); all three granted |
| 5 queue never shown | fixed | `snapshot` printed titles, budgets, the $28 total and the §3 overrun note |
| 7 Monitor outlives the cell | documented | 2b says to stop it after `record` |
| 10/14 `next` names a child that can't start | fixed | `note: held back SA-0088: its parent SA-0087 is NOT_IMPLEMENTED, so a cell would cut it from main`, then `SA-0086` |
| 17 fan-out parent sorted last | fixed | SA-0087 (2 descendants) sorts first |
| 14 `status` can't say what's reviewed | fixed | after re-snapshot: `SA-0086  READY_FOR_REVIEW   #255   reviewed 50ae260e` |
| 18 spend against budget | fixed | `record`: `SA-0087  NOT_IMPLEMENTED  (no PR)  $8.39 of $8.00` |
| 22 `pattern` matches the agent's greps | fixed | I widened it with `[Ee]rror`; it fired on `agent: tool error` and an `agent: Edit` naming `CellSessionError`, neither of which the anchored pattern matches. Re-armed with `pattern` verbatim |

## Observations, in the order they happened

1. **`snapshot` refuses to replace an order whose every PR has merged.** The old
   order (stack #251) was 8/8 `MERGED`; `snapshot` said only
   `.saffron-loop/order.json exists — pass --force to re-snapshot`, exit 1, and I ran
   `status` to learn why it was safe to force. When every recorded outcome is merged or
   closed, `--force` keeps nothing, so the refusal protects nothing. Fix: overwrite an
   order with no open outcome, saying so ("previous order: 8/8 merged; replaced"), or
   put the merged count in the refusal.
2. **The Monitor expires before a cell ends.** Monitor caps at 30 minutes; the skill
   says a cell takes 30–60. Nothing in 2a says to re-arm it, and an expiry with no
   terminal line reads the same as a quiet cell. The background task's own completion
   notice is the real end signal (2b says so), so the Monitor is only for phase lines.
   Fix: 2a says "re-arm on expiry; the process exit, not the Monitor, ends the cell".
3. **GOTCHAS says a turn-ceiling line is not the end of a cell; here it was.** SA-0087's
   IMPLEMENT hit 60 turns with 0 commits and $8.39 of $8 spent, and the next lines were
   `budget: … cut off at the turn ceiling with nothing committed, no room left to salvage`
   and `NOT_IMPLEMENTED`. The Recording bullet is true only when something was committed
   and budget remains. Fix: "…unless it is followed by `budget: … no room left to
   salvage`, which is the end".
4. **The skill has no path for a parent that ran out of ceiling rather than failed.**
   The agent's last 30 turns ran the full suite, `ruff`, `types`, `ast-grep test`,
   `structure`, and a size check against the ceiling; turn 61 was `git diff --stat`, and
   no `git commit` ever ran. The plan checkpoint had taken 47 turns and $3.79 of the $8
   (`events.jsonl`, the first `result` event). `NOT_IMPLEMENTED` is decided, so GOTCHAS
   makes it final and `next` holds back both children: one spent ceiling took three of
   the loop's four specs with it. What the loop needs is the operator's call on raising
   the spec's ceilings, a spec edit that changes `spec_sha`, and a `snapshot --force`
   that re-queues it. Fix: a Recording bullet for `cut_off_no_salvage_room` (or any
   decided state reached at a ceiling) that routes it to the operator as "raise the
   ceilings and re-run, or drop the chain", and says how a re-run gets back into the order.
5. **The events log can't answer "what did the agent's last check say?".** Agent
   `tool_result` events carry only `is_error`, so the size check the agent ran before it
   was cut off left no record of the count it saw. The delegate can see what the agent
   tried, never what it learned. (A Saffron observation more than a skill one: step 5.)
6. **Both cells hit the turn ceiling with nothing committed; budget decided which one
   survived.** SA-0086 reached 40 turns at $4.15 of $6, and a salvage turn committed the
   work (`IMPLEMENT: cut off at the turn ceiling with nothing committed — spending one turn
   to salvage it`), then `READY_FOR_REVIEW` at $7.99 (33% over). SA-0087 reached its
   ceiling at $8.39 of $8, and a salvage turn was refused for budget. IMPLEMENT's prompt says "Implement it
   now and commit your work" (`saffron/phases/implement.py:43`); in both cells the agent
   verified everything first and never committed. Neither the skill nor `record` names
   this pattern, and it is the one that sank a chain. (For step 5, not the skill.)
7. **Confirmed: the Monitor expired mid-cell** (observation 2). SA-0086's watch expired
   at 30 minutes, after PACKAGE's PR line; the `READY_FOR_REVIEW` line was delivered
   after the expiry notice.
8. **2c.6's dry `stack` errors on the loop's first PR.** It prints `error: a stack needs
   two or more reviewable pull requests; have 1`. Here one reviewable PR is the whole
   loop so far. Fix: with one PR, print "1 reviewable PR; nothing to check against yet"
   and exit 0, or have 2c.6 say to skip it until there are two.
9. **Worked: the Standards seat found a regression the spec half-anticipated.** SA-0086's
   spec puts `pr_body.py`'s unreachable `"base"` branch out of scope. The seat found that
   the other branch's reason ("because the base moved") becomes false on every unmoved-base
   PR, and the in-cell critic missed it (three clean lenses). The skill's "fix
   incomplete without an outside change → operator" routing worked as written. The
   delegate's review commit edits a forbidden file, though, and nothing gates it:
   review commits run no `scope` gate. That's the same class as run 1's item 20 (size).
10. **Worked, again: the Spec seat's probe found a vacuous witness after three clean
    lenses.** Its P1d (`packaged_sha=pushed` → `outcome.cell_head_sha`) passed all 136
    tests in `test_package.py`, because the witness stubbed `reverify` with `lambda **_k`.
    I re-ran it before fixing and it survived, as reported. The seat's report also marked
    each probe's edit as confirmed-applied, which is run 1's item 11 working. The two seats
    overlapped on one finding (the PR-body sentence) and otherwise found disjoint sets,
    which again supports the two-seat split.
11. **The ceiling re-run path works mechanically; only the skill is silent on it**
    (observation 4). With the ceilings edit merged (#256), `snapshot --force` re-queued
    SA-0087 at its new `spec_sha`, kept SA-0086's `READY_FOR_REVIEW` and its `reviewed`
    SHA, and `next` named SA-0087. Two rough edges. First, the re-snapshot's table
    says `$44.00 in total`, which counts SA-0086's $6 though that cell has already run
    ($7.99). A "remaining" line would say what the loop can still spend. Second, the
    table doesn't mark which rows it kept.
12. **`pattern` omits the lines that decide a turn-ceiling cell.** `budget: $8.39 of
    $8.00 — … no room left to salvage` and `PLAN: accepted` are neither phase-prefixed
    nor states, so the Monitor never shows them. `budget:` is how the delegate learns a
    turn-ceiling line is terminal (observation 3). For SA-0087's re-run I added
    `^(budget:|PLAN)` to the Monitor. Fix: add both to `pattern`.
13. **`record` calls a halted `REBUTTING` task "still running".** SA-0087's second cell
    exited 1 with the task at `REBUTTING`, which DESIGN.md §5.6 (line 1067) defines as a
    halt: "A rebuttal that neither moved HEAD nor recorded an argument earns nothing and
    halts at `REBUTTING`". `record` printed `left pending: the cell is still running —
    wait for it to exit, then record again`, because the driver borrows
    `reconcile.IN_FLIGHT_STATES`, which lists `REBUTTING`. The process had already
    exited. A delegate following the skill would wait forever. Fix: after the process
    exits, an in-flight state is a halt, not a wait. `record` can take `--exited`, or
    check that no `saffron-cell-SA-NNNN` container is up. GOTCHAS then needs a Recording
    line for a `REBUTTING` halt: the branch is pushed with no PR, and a child can't
    stack on it (`DEPENDENCY_WAITING_STATES` excludes it), so it goes to the operator.
14. **Raising the ceilings fixed the turn problem and moved the budget problem to REBUT.**
    Second cell: plan 26 turns and $2.71, IMPLEMENT green with 1 commit at $8.64, lenses
    $2.21, which left REBUT $3.09 and it exhausted. The skill's budget advice is about
    whole cells (§3 overrun). It says nothing about the phases sharing one budget, so the
    last phase is starved first.
