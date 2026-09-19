# Feedback on run-saffron-spec-loop (eighth run after the rework, 2026-09-18/19)

Five specs: `SA-0101` (item 43), `SA-0102` (item 166, on `SA-0101`), `SA-0107`
and `SA-0108` (item b-946f03, `SA-0108` on `SA-0107`), and `SA-0106` (item
b-d6bff7). Run 7's feedback is `2026-09-18-spec-loop-skill-feedback-run-7.md`,
cited here as "run 7, observation N".

**Outcome:** five reviewable pull requests, linked and marked ready as the
stack #351 ← #360 ← #355 ← #366 ← #353. None is merged. Six cells cost
**$74.60** against $114 of budgets, including `SA-0107`'s first cell, which was
lost.

| Spec | PR | Spent | Changed lines | Review commit |
|---|---|---|---|---|
| `SA-0101` | #351 | $15.74 of $14. Hit 90 turns in IMPLEMENT, green on attempt 2 | 300, then 340 after review | `13f3dfa` |
| `SA-0107` | none | $5.07 of $20, lost. The 15-minute turn wall cut IMPLEMENT with 0 commits | 0 | none |
| `SA-0106` | #353 | $18.86 of $18. Hit 100 turns, and the salvage turn kept 1 commit | 633 | `9a8e7c4` |
| `SA-0107` | #355 | $13.10 of $20. Hit the wall again with 2 commits kept | 1049, then 1193 after review | `5bce64a` |
| `SA-0102` | #360 | $12.69 of $20. No bound hit | 266 | `1be044a` |
| `SA-0108` | #366 | $9.14 of $22. No bound hit | 494 | `5b838d4` |

Size decisions were the operator's. #351 merges at 340, over its blocking
ceiling of 300. #355 is 1193 against an advisory 600, accepted.

Three spec pull requests merged mid-loop so that a cell could run the edited
text: #350 (step 1b's round on all five), #352 (`SA-0107`'s commit-as-you-go
note and `SA-0102`'s parent-branch fixes) and #361 (`SA-0108`'s parent-branch
fixes). Fourteen backlog items are filed in the same pull request as this file.

## The goal this feedback is ranked by

The operator's framing, 2026-09-19: the skill exists to make itself
unnecessary. Saffron should produce a stack it can trust with no delegate
between the cell and the operator. Every step the delegate does by hand is a
step Saffron has not absorbed yet. So the recommendations below are ranked by
which delegate step Saffron absorbs next, and each names the item that tracks it.

## Summary: what to change first

1. **A1. Move the Spec seat's vacuity probes into the cell** (b-2750d5). After
   each cell the delegate mutates the line that satisfies each criterion and
   runs its witness. That found a witness hole in all five pull requests, and
   the in-cell lenses passed every one. In #353 three lenses were clean with
   zero findings. `SA-0109` (#358) runs the probes a lens names. This runs one
   per criterion, whether a lens thought of it or not.
2. **A3. Run a change whose subject is history over a real ledger** (b-a8270f).
   #355 left out 75 of 76 merged tasks, because its spec lookup missed
   `.saffron/specs/done/`. Four spec reviews and three lenses missed it. Only a
   run over a copy of `~/.saffron/ledger.db` found it. #366's run over the same
   copy found item b-952c34.
3. **A2. Make `prose` judge each block, not a count per file** (b-044ae7, with
   item 174 for `terms`). #353 grew five over-limit docstrings and paid for
   three new comment blocks by cutting three older comments' reasons. The gate
   passed it, with the rule and the `CLAUDE.md` line both in force.
4. **A4. A spec phase before the cell.** Step 1b is the delegate's largest
   manual step: five first reviews, then re-reviews on branches and at parent
   branches, for every spec. No item is filed for Saffron doing it. Items 56
   and 130 are the nearest. Observations 3 to 12 are its requirements.
5. **A5. The loop cuts its own branch, and `saffron cell --base`** (b-65e7e2,
   the operator's proposal). Run 8 merged three spec pull requests to `main`
   mid-loop. Each stopped the loop for an operator merge.
6. **A6. Commit as you go, and a salvage turn for the wall** (b-36b551). Four
   of six cells hit a turn or wall bound in IMPLEMENT, and two had nothing
   committed. The per-criterion commit note worked in both specs that carried
   it.

The driver's own defects are b-4589be. They cost time, not trust, and rank
below all six.

**What worked and should stay:**
- The two seats. They found a defect in every pull request that the critic
  did not raise, and each became a review commit.
- The raised ceilings from a parent's measured run. `SA-0102` and `SA-0108`
  hit no bound (observation 11).
- The commit-per-criterion note. `SA-0107`'s second cell was cut by the wall
  again and kept two commits.
- REBUT. `SA-0107` and `SA-0102` each had an adequacy blocker fixed in the
  cell, and `SA-0107`'s lens withdrew its blocker after checking the fix.
- `hold`, from run 7, observation 6. It kept `next` off every edited spec.
- `snapshot --force` after #346. It kept the order at five.
- Measuring a literal before it goes into a spec (observation 9).

## Run 7's items, checked against this run

- **Observation 1, `snapshot --force` widening the loop.** Fixed by #346.
  `snapshot --force` after #350 kept the order at five and added nothing.
- **Observation 6, `next` and an edit in flight.** `hold` shipped and worked.
  Each round needed five `hold` commands (observation 5).
- **Observation 7, comment preambles.** The `CLAUDE.md` line (#346) and the
  `comment-block` and `docstring-length` rules (#347) were both in force. #353
  and #366 still wrote long docstrings (observation 16).
- **Observation 9, the delegate's probes failing silently.** `driver.py probe`
  shipped and refuses a find that misses. A new silent path appeared: its
  verdict shares a line with uv's warning (observation 13).
- **Observations 2 to 4, step 1b's stop rule and the delegate's edits.** Neither
  is solved. The stop rule did not converge, and delegate edits introduced
  blockers again (observations 6 to 9).
- **Observation 8, stale line numbers.** Recurred in all five specs.
- **Observation 10, size estimates.** `SA-0101` landed at exactly 300, its
  blocking ceiling, and the first reviews treated size as advisory
  (observation 7).
- **Observation 11, step 5 and `new-id`.** Used here.
- **Item 173, `main` red in the cell.** Every run-8 baseline still showed
  `tests=fail` and `prose=fail`. Every cell was cut before #354 merged.

## Observations

1. **`snapshot --new` worked, and two start-of-session messages read as
   alarms.** The previous loop's order listed five specs as "gone" after they
   retired to `done/`. On a finished loop that is expected, and `status` prints
   it like an error. `saffron queue` printed five "head differs from what
   PACKAGE pushed" warnings, one per merged pull request that had a review
   commit. Also expected in this loop, and also read as an alarm every time.

2. **Step 1b found three verified blockers, and every spec needed an edit.**
   `SA-0101`'s junk `resets_at` was dropped by `_shape_ok`. `SA-0102` had a
   zero in an aborted suite. `SA-0108` had an exit-0 fixture with no break.
   All five specs got edits, so no cell could start until #350 merged. Every
   spec had stale line cites again (run 7, observation 8), five of five.

3. **Two reviews found the same cross-spec gap.** The reviews of `SA-0107` and
   `SA-0108` each found that a shared `pr_url` needs a `PullRequest` IRI.
   Reviewing parent and child apart means the child's review discovers the
   parent's gaps. Step 1b could hand a child's reviewer the parent's review.

4. **The child contract surfaced piecemeal, across four rounds.** `SA-0108`
   forbids `SA-0107`'s module. Round after round found one more thing the
   parent had to pin for the child: IRI minting, raising on a missing file,
   returning the IRI, then the spec version not found, the finding's subject on
   a mismatch, and the IRI in the claim. A child that forbids its parent's
   module turns every parent gap into a dead end. Two fixes:
   - A step 1b check: for each child, list what it needs from the parent's
     public surface, and confirm a parent criterion pins each.
   - Or let a child edit its parent's module when the parent-branch review
     finds a gap, in place of the delegate guessing the whole contract ahead.

5. **`hold` takes one id.** Each round edited five specs and took five `hold`
   commands. `hold --all`, or holding by pull request, would do (b-4589be).

6. **`prek run --files` on unstaged files passed, and the commit then failed.**
   Spec edits went to five parallel forks in one worktree. `prek run --files`
   passed on the unstaged files, and the commit hook then failed `prose-limit`
   on 20 lines. The hook reads only staged files (`hooks/prose_limit.py`,
   `staged()`), so an unstaged run compares nothing. The skill should say to
   run `git add`, then `prek run prose-limit`, before committing a spec edit.
   A fork's prompt for a spec edit should name the prose gate.

7. **The first reviews called size advisory at an elevated tier.** Round 2
   found that `SA-0101`'s `size` blocks, because its `touches` includes
   `saffron/cell/**` and `.saffron/policy.yaml` elevates that. The first
   review and the spec both treated size as advisory. The spec reviewer's
   check 5 should read `elevate_on` against `touches` before calling size
   advisory. `SA-0101` then landed at exactly 300 and dropped the "ten"
   docstring rewrites its spec asked for, which the size pressure likely
   caused. Its review commit, mostly line-neutral rewrites, took it to 340. A
   review commit at an elevated tier always reopens the size question (item 40).

8. **The stop rule never converged.** Run 7 ended step 1b at "a review with no
   blocker and no concern". Round 3 here found no blocker on `SA-0101`,
   `SA-0106` or `SA-0107`, and three to five new concerns on each. `SA-0107`'s
   round 4 found three more. The operator chose: fix every finding, and
   re-review only a spec whose child forbids its module. That is the proposed
   rule for the skill. Stop at no blocker, except for a parent whose child
   forbids its files.

9. **The delegate's own edits introduced blockers.**
   - `SA-0107`'s round 2 found four blockers. One, `PhaseStart` given `step`
     where the kind has `label`, came from the delegate's edit. The other three
     were fixes written as notes with no witness.
   - `SA-0102` had three reviews at its parent branch, and each found a
     blocker. Two came from the delegate's instructions: the advice to append
     `_JOINED` rows, carried over from `SA-0101`, which pass with the source
     reverted, and a "fold into one drive" literal that cannot express the
     identical-failure case.
   - A relayed reviewer note moved a cite from `pyproject.toml:35-37` to
     `:34-36` without checking it. Round 3 caught the new stale cite.

   Three rules follow. Every fix the operator approves lands in a criterion's
   claim or a witness, never only in notes. A step 1b edit states what a
   witness must kill, never a fixture literal the delegate has not run. And
   "verify every blocker" becomes "verify every finding you act on", notes
   included. Measuring the `SA-0102` literal is what ended that review loop.

10. **A stacked child's review is where the parent's real code first shows.**
    `SA-0102`'s review at `origin/saffron/SA-0101` found a blocker no review at
    `origin/main` could see: the `_JOINED` rows the spec prescribed would pass
    with the source reverted, because the renderer existed at base and the
    fixture sits under `tests/**`. `SA-0101`'s rows escaped only because its
    kind was new. `SA-0108`'s review at `SA-0107`'s branch found a fixture that
    never separates the walk from the projection.

11. **The parent's actual run is the history a child's ceilings should use.**
    `SA-0102`'s and `SA-0108`'s ceilings were both below their parent's
    measured floor, and each parent-branch review found it. Raised to 120 turns
    and $20 and $22, neither child hit a bound. `SA-0101`'s 90 turns sat 9
    over a floor, and every review flagged the margin as a concern. The
    operator kept 90, because the backtest says to discount ceiling claims, and
    attempt 1 hit it. The difference between a floor and what a run uses
    deserved more weight.

12. **The operator's proposal: the loop's own branch** (b-65e7e2). `saffron
    cell` cuts from the default branch or a parent's pushed branch, and has no
    `--base`. A spec edit must merge to `main` before its cell, or the cell's
    worktree carries the old text: `spec_drift` reports and does not refuse.
    With a loop branch, the spec edits are the stack's bottom layer. The
    operator ratifies them in the stack review, and step 1b's answers stay the
    approval before money is spent.

13. **The delegate's probes and reads still fail quietly.**
    - `probe` prints its verdict on the line with uv's `VIRTUAL_ENV` warning.
      On #351 a `grep -v VIRTUAL_ENV` hid a "survived".
    - The delegate's own first spend assertion on #351 was vacuous (`0.0 ==
      0.0` on the plan-turn path), and `probe` caught it.
    - `history` reads the spec in the checkout it runs from. A reviewer
      running it from `main` saw `SA-0102`'s old ceilings, 90 turns and $14.
      `history --spec <path>` would fix it.
    - `next` named `SA-0102` while its parent-branch review was still out, so
      the delegate ran `SA-0106` first by hand.
    - The Monitor pattern still misses the CLI's error line (item 158). The
      `Error` users add also matches agent lines.

    All five are b-4589be.

14. **Four of six cells hit a turn or wall bound in IMPLEMENT, and two had
    nothing committed** (b-36b551).
    - `SA-0107`'s first cell was cut by `TURN_TIMEOUT_S` (900 s,
      `saffron/cell/session.py:58`) while it formatted uncommitted files. It
      ended `NOT_IMPLEMENTED` with 0 commits and $5.07 spent. No spec review
      checks a turn's wall-clock need. The size estimate, 650 to 750 new lines,
      was the signal.
    - `SA-0106` hit 100 turns with 0 commits at $10.03, and the salvage turn
      kept one commit. The salvage exists for the turn ceiling and not for the
      wall.
    - `NOT_IMPLEMENTED` is a `DONE_STATES` member, so `record` settled
      `SA-0107` and held `SA-0108`. A wall cut is a ceiling, not a verdict.
      `record` should call it a halt, like `REBUTTING`.
    - The implement prompt already asks for a commit after each coherent step.
      A spec note asking for one commit per criterion worked in both specs that
      carried it. So the prompt needs the unit, not the request.

15. **Tokens are not recorded** (b-5e443c). The operator asked whether time and
    tokens per step are recorded. Time, turns and cost are. Tokens are not:
    `saffron/cell-base:python` was built 2026-08-29, and `SA-0090`'s usage fields
    in `images/agent_runner.py` merged 2026-09-16. No run-8 event log carries a
    token count, nothing warns that the image predates the runner, and the
    ledger has no token column.

16. **Comment preambles recurred with the rule and the gate in force**
    (b-044ae7, b-122686). #353's cell grew five over-limit docstrings,
    `run_batch`'s from 33 lines to 53. It added three comment blocks and cut
    three older comments' reasons (item 70's among them), so the gate's count
    per file stayed level. #366's docstrings restated its spec. A cell reads
    the `CLAUDE.md` line and still restates the spec's notes.

17. **Only running against real data found #355's largest defect** (b-a8270f).
    The Spec seat ran the projection over a backup of the real ledger and found
    75 of 76 merged tasks left out, because the spec lookup missed
    `.saffron/specs/done/`. For a spec whose subject is history (projection,
    report, reconcile), the Spec seat's prompt should say to run it over a copy
    of the real ledger. Step 1b can ask of any spec citing `.saffron/specs/`
    paths whether the code needs `done/`.

18. **Spec text alone did not stop a forbidden shape.** #355 authored a
    `Phase` and an `Attempt` with `n=1` for every task. Appendix T forbids
    exactly that, and the spec's notes named it.

19. **A stacked child's branch carries its spec as of the parent's cut.** The
    #360 Standards seat read the pre-#352 `SA-0102` spec on the branch, and
    raised a concern the merged spec contradicts. `REVIEW-PROMPT.md` should
    say to read the spec at `origin/main`. b-65e7e2 removes the cause.

20. **The instrument cannot see the one case it exists for** (b-952c34,
    b-60d804). #366's run over the real ledger: 76 merged tasks, 38 compared,
    0 breaks, 35 unattributable and 3 `spec_unusable`. The one real overwrite
    in history, `SA-0013` task 8 (PR #51), is among the 3. `SA-0013` is a
    `test` spec, and `factory:SpecType` has no `test`.

21. **The seats found three witness blockers on #366, and the critic raised
    one as a concern.** The ledger's `pr_url` read and the break line's task id
    had no witness. The critic raised the per-reason lines as a concern.

22. **Merge-time hand edits pile up outside the stack** (b-e0bbbf). `SA-0107`
    makes four sentences about graph imports false, and needs a dependency
    move that touches the `protected` `uv.lock`. `SA-0108` needs `saffron
    chains` in `CLAUDE.md`. `SA-0106` needs four `DESIGN.md` lines, already in
    b-d6bff7. None of them can go through a cell.

23. **A spec that adds an event kind can never get `revert`'s check**
    (b-5d5b56). Module-scope parametrize lists in `tests/test_events.py` make
    the reverted run a collection error, so `revert` skips. `SA-0101` was the
    first case.
