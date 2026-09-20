# Feedback on run-saffron-spec-loop (tenth run after the rework, 2026-09-19)

Two specs: `SA-0111` (item 97's record half) and `SA-0112` (item b-281f0a's
ledger-reading half). Run 9's feedback is
`2026-09-19-spec-loop-skill-feedback-run-9.md`, cited here as "run 9,
observation N".

**Outcome:** two pull requests, #381 and #382, stacked as #383 and marked ready.
Two cells cost **$11.99** against $43 of budgets. Neither hit a bound, neither
needed a repair turn, and both plans were accepted at the checkpoint.

| Spec | PR | Spent | Changed lines | Review commit |
|---|---|---|---|---|
| `SA-0111` | #381 | $5.01 of $20. No bound hit | 238, then 254 after review | `a269ecd3` |
| `SA-0112` | #382 | $6.98 of $23. No bound hit | 237, then 256 after review | `b2ef88f6` |

`SA-0111` ran at `elevated` against a blocking `size` ceiling of 300 and
finished at 254. `SA-0112` ran at `standard` where `size` is advisory, ceiling
600, and finished at 256. One spec pull request merged mid-loop, #380, carrying
step 1b's five rounds across both specs.

## The goal this feedback is ranked by

The operator's framing, 2026-09-19: the skill exists to make itself
unnecessary. The recommendations are ranked by which delegate step Saffron
absorbs next.

## Summary: what to change first

1. **b-2750d5 — mutate the line behind each criterion, in the cell.** Run 10 is
   now its strongest evidence. Four of the four witness holes this run found
   were found by *probing*, and two of those four were found inside the cell by
   the adequacy lens, which is the half of b-2750d5 that already exists.
2. **b-865399 (new) — measure a fixture arrangement instead of reading it.**
   `SA-0112` took three step 1b rounds on one criterion and a two-minute
   measurement ended it. The measurement is what the cell then delivered.
3. **b-63ac52 — a spec cannot ask for pull request body text.** Second sighting,
   and worse than the first: this time the implementer's notes claimed
   compliance that had not happened.

## The adequacy lens went two for two, and the host's probe is why

Both cells produced exactly one blocker, both from `adequacy`, and the host ran
both probes and reported **survived** on each:

| Spec | The hole | Fixed in-cell |
|---|---|---|
| `SA-0111` | no test exercised the write *order*; swapping the two statements changed nothing | a call-order test spying on both ledger methods |
| `SA-0112` | the shortfall witness built all three rows with a pre-REVIEW total of exactly $0.00, so deleting the subtraction changed nothing | distinct non-zero totals, re-probed by the implementer |

Both implementers fixed rather than argued, and both lenses withdrew. This is
`SA-0109`'s probe runner (item 117) working in production on the second and
third cells after it landed, and it is the first run where the in-cell critic
caught a witness hole per cell before review.

Run 9 recorded the opposite: five of six blockers were witness holes the lenses
did not raise. The difference is worth naming, because it is the flywheel
working — the probe the host runs turns a lens's suspicion into a fact the
implementer cannot talk past.

**It did not make the seats redundant.** #381's review found two further witness
holes the lens did not, and both were found by probing rather than reading:
deleting `record_merged_head`'s commit survived all 2465 tests, and a headless
merge that never moved its row survived its own witness and died only outside
the spec's `touches`.

## Step 1b: five rounds, and three of the nine findings were the delegate's

| Round | Spec | Finding | Author of the defective text |
|---|---|---|---|
| 1 | SA-0111 | **blocker** — criterion 2's witness drove only `CHANGES_REQUESTED`, so `new_state in ("MERGED", "REJECTED")` passed both witnesses | the spec |
| 1 | SA-0111 | concern — "one statement doing both" invited widening `set_task_state`, whose callers are almost all forbidden | the spec |
| 1 | SA-0111 | concern — the §4.2.1 carve-out was argued only in Context, and the `SA-0099` precedent was narrower than presented | the spec |
| 1 | SA-0112 | concern — criterion 2's witness could not observe "closest in shape first" | the spec |
| 2 | SA-0111 | concern — the narrowing left "a new writer method" authorising one that writes state too, skipping `set_task_state`'s spend rollup | the delegate |
| 2 | SA-0111 | note — "nine test files outside `touches`"; seven are | the delegate |
| 2 | SA-0112 | concern — the new paragraph contradicted the untouched one above it | the delegate |
| 2 | SA-0112 | concern — "placed first" survived the date sort only by an unstated property of `_cell`'s defaults | the delegate |
| 3 | SA-0112 | concern — the other-type row is target-shaped and placed last, so the cut dropped it and the type filter went unwatched | the spec, uncovered by the rebuild |

Three runs in a row now: run 8 two, run 9 two, run 10 three. Run 9's
observation A stands unchanged — the delegate's spec edit is the one artifact
in the loop with no gate and no second reader, and it is reviewed only because
the delegate chooses to dispatch one.

What is new is the *shape* of the delegate's defects. All three were true about
the paragraph edited and false about one not edited, or about a fixture default
never stated. Two of the three were caught only because the re-review reads the
whole spec, which item 159 put in the skill after run 5.

## What ended `SA-0112`'s rounds was a measurement, not a fourth review

Round 3 asked whether the rebuilt fourteen-row arrangement actually kills the
three wrong implementations. That is answerable by running it:

```
printed: SA-T00 … SA-T11          (the twelve low-peak rows)
far printed?  False                → the correct selection returns 0
last printed? False
no-sort selection includes far? True
no-cut includes last?           True
no-type-filter selection includes off? True
```

About two minutes, against `_history_lines` at `origin/main`. Round 4 was not
dispatched. The cell then delivered exactly that arrangement, and #382's Spec
seat killed all three wrong implementations separately with its own probes.

Run 9's observation B said the delegate can settle a *gate* question by running
the gate. This run says the same for a *witness-adequacy* question, which is the
more common kind. Filed as **b-865399**.

Three reviews at roughly six minutes each preceded a two-minute measurement that
settled what they were circling. The reviewer cannot do this: its Bash is
limited to git and `driver.py history` by instruction.

## `SA-0112` shipped the command that replaces check 4, and it was run against the live ledger

The delivered `driver.py check SA-NNNN` reproduces, from the ledger, what step
1b's reviewers computed by eye this very run:

```
SA-0031  exit 1  both blockers and the concern
SA-0044  exit 1  turns blocker and the concern
SA-0099  exit 1  turns blocker and the concern
SA-0092  exit 0  clean verdict
SA-0102  exit 0  clean verdict
SA-0112  exit 0  clean verdict
SA-0059  exit 1  `error: no spec declares` — the documented usage 1, not a verdict
```

`SA-0111`'s and `SA-0112`'s lines match the ceilings each spec review wrote out
by hand. Nothing calls it yet: the prompt half is b-281f0a's remaining work, and
a worktree on `joel/reword-check-4-concern` was already open in this checkout
while run 10 ran, which looks like that half in flight.

The one thing to watch when the prompt half lands: an exit 1 from `_fail` (a
spec no file declares) and an exit 1 from a blocker verdict are the same status,
distinguished only by the output. The spec chose that deliberately.

## Steps 3 and 4

`stack --execute` linked #382 onto #381 and marked both ready, both bases read
back. Unlike run 9, the operator had not merged either pull request as it was
reviewed, so step 3 had work to do for the first time since run 8. Step 4 was
not run; the operator asks for it.

## Smaller things

- **The `prose` hook caught the delegate's own spec prose** on the first commit
  of #380: three em-dashes and nine sentences over the 25-word limit, all in
  text written that minute. `make check` had passed. This is item b-08a36a's
  shape from the other side — the hook sees staged content the gate's per-file
  subtraction does not.
- **`dead` is clean at base again.** Run 9 found `APPENDIX_OPENS` failing on
  `main` and the operator filed rather than fixed it mid-loop; #379 closed it
  (item b-17fb8b), and both cells this run show `dead=pass` in their baseline.
  The only baseline failure is `prose`, which fails at base by design.
- **No `PLAN_REJECTED` this run.** Run 9 lost a cell and $1.20 to the plan
  checkpoint reading a ceiling its own gate would not enforce (b-408cf5). Both
  plans were accepted here, so the item has no new evidence and no
  contradiction either: neither spec was near its ceiling at plan time.
- **Stale worktrees.** `git worktree list` in this checkout shows five
  `.claude/worktrees/agent-*` entries from earlier sessions, two scratchpad
  worktrees from run 9, and the locked `joel/reword-check-4-concern`. Only the
  last is live. Not the loop's to clean, but a review seat cutting a worktree
  meets them.

## Items this run filed

| Item | Tier | What |
|---|---|---|
| b-865399 | 2 | step 1b reads a fixture arrangement it could run |
| b-1c7019 | 2 | the guard against a column nothing reads asserts two names and claims the schema |
| b-3e0dbe | 2 | a crash between `reconcile`'s two writes strands the row in `unasked` |
| b-bbf663 | 3 | §4.1's `tasks` tuple disagrees with the schema in both directions |
| b-6a9707 | 3 | the driver calls a gate result and a probe outcome a verdict |

Nine rejections are appended to `.saffron/rejections.md` under today's date.
Item 97 stays `partial` on the re-gate; b-281f0a stays open on the prompt half;
b-63ac52 gains `SA-0111` and a second dated sighting.
