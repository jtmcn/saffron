# Feedback on run-saffron-spec-loop (ninth run after the rework, 2026-09-19)

Two specs: `SA-0109` (item 117, on `SA-0102`) and `SA-0110` (item b-9ff0fd). Run 8's feedback is `2026-09-19-spec-loop-skill-feedback-run-8.md`,
cited here as "run 8, observation N".

**Outcome:** two merged pull requests, #375 and #377. Three cells cost
**$16.99** against $49 of budgets, including `SA-0110`'s first cell, which was
refused at PLAN and spent $1.20 for nothing. The operator merged each pull
request as it was reviewed, so the loop never had two open at once and steps 3
and 4 had nothing to do.

| Spec | PR | Spent | Changed lines | Review commit |
|---|---|---|---|---|
| `SA-0109` | #375 | $7.94 of $26. The 15-minute wall cut IMPLEMENT after the commit landed | 580, then 695 after review | `5782d910` |
| `SA-0110` | none | $1.20 of $23, lost. PLAN_REJECTED on the planner's own estimate | 0 | none |
| `SA-0110` | #377 | $7.85 of $23. No bound hit | 460, then 525 after review | `e1db4353` |

#375 merged at 695 against a blocking ceiling of 600, the operator's call
(item 40's precedent). Of the 115 lines the review added, 8 were the production
fix and the rest were three witnesses.

Two spec pull requests merged mid-loop so the cells could run the edited text:
#374 (step 1b's rounds on both specs) and #376 (`SA-0110`'s two size cuts).
Ten backlog items are filed in the same pull request as this file.

## The goal this feedback is ranked by

The operator's framing, 2026-09-19: the skill exists to make itself
unnecessary. Every step the delegate does by hand is a step Saffron has not
absorbed yet. So the recommendations are ranked by which delegate step Saffron
absorbs next, and each names the item that tracks it.

## Summary: what to change first

1. **b-408cf5 — make the plan checkpoint read the effective risk.** It refused
   `SA-0110` on a ceiling its own `size` gate would not have enforced, and the
   recovery cost a cell, two review rounds and two acceptance criteria.
2. **b-2750d5 — mutate the line behind each criterion, in the cell.** Run 9 is
   its strongest evidence yet: `SA-0109` shipped the lens's half (item 117,
   done), and the very next cell showed why that half is not enough — five of
   the six blockers this run found were witness holes the lenses did not raise.
3. **Item 50 — `revert` must not read a collection error as `skip`.** It hit
   production here: the gate checked nothing on #377 and said so in a summary
   nobody but the delegate read.

## Step 1b: three rounds, and every blocker after the first was the delegate's

Step 1b ran three rounds on `SA-0109` and two on `SA-0110`, merged as #374.
Counting blockers by who wrote the text they were in:

| Round | Spec | Blocker | Author of the defective text |
|---|---|---|---|
| 1 | SA-0109 | criterion 6's raise witness could not observe the claim it serves (two probes, the first raising) | the spec |
| 1 | SA-0110 | `Adr.supersedes` has no reader vulture can see, and `.saffron/**` is forbidden | the spec |
| 2 | SA-0109 | the three-probe edit left `## Problem` telling the cell to discard the verdicts criterion 6 protects | the delegate |
| 3 | SA-0109 | `Finding.probe_verdict` fails the `dead` gate — **false**, criterion 5 forces a reader | the reviewer |

Run 8's finding that "delegate edits introduced blockers twice" repeated here:
one in two of the delegate's three edit rounds. The edit that caused round 2's
blocker was a widening the reviewer itself specified, applied to the paragraph
it named and to nothing else. Nothing in the loop reads a spec edit against the
rest of the spec except the next review.

**Observation A.** The delegate's spec edit is the one artifact in the loop
with no gate and no second reader. A cell's diff has gates, a lens, a rebuttal
and two review seats. The prose that tells the cell what to build has one
reviewer, dispatched by the author of the edit, and only if the delegate
chooses to dispatch it.

## Round 3's false blocker, and what filtered it

Round 3 reported that `Finding.probe_verdict` would fail the blocking `dead`
gate, with a full derivation: vulture 2.16 has no `visit_keyword`, `tests/` is
not scanned, the whitelist is forbidden to the cell, the frontmatter declares
no `pending_symbols`. Every step was true. The conclusion was wrong, because
criterion 5 requires REBUT to show a survived probe and hide an `unproven` one,
which is a read of `finding.probe_verdict` in `saffron/phases/rebut.py`.

What settled it was a measurement, not a reading: a detached worktree at
`origin/main`, the field added alone (`unused variable 'probe_verdict'`), then
the field plus the read (clean). Two minutes.

The same measurement is what confirmed `SA-0110`'s round-1 blocker, and what
showed that `superseded_by`, `principles` and `appendices` needed nothing,
against a review that had reasoned the same conclusion from `git grep`.

**Observation B.** Both `dead`-gate questions this run were settled by running
the gate over a mutated worktree, and neither was settled by reading. The
delegate can do this in two minutes; the reviewer cannot, by instruction
(no tool execution). Backtest items 123-124 already say the reviewer's
forecasts need discounting. This run says which forecasts are cheap to convert
into measurements: anything a gate decides.

## The pre-existing `dead` failure at base

`ontology/design_record.py:33`'s `APPENDIX_OPENS` is reported by `dead` at
`origin/main`, so every cell's baseline carries it and subtraction spares them
all. Its only reader is `tests/ontology/test_design_record.py:244`, and the
gate does not scan `tests/`, so it is the `_.related` shape and wants a
whitelist line. Left by `4c0a46e`. The operator's call, 2026-09-19: file it,
do not fix it mid-loop.

Found incidentally, by running the gate for something else, and then confirmed
by `SA-0109`'s own `baseline:` line. Item 173's reporting is what made the
second sighting legible.

## The plan checkpoint spends a cell to say what a reviewer said for free

`SA-0110`'s first cell died at PLAN with `PLAN_REJECTED`: the plan's own
estimate of 620 changed lines against the 600 feature ceiling
(`saffron/agents/artifacts.py:288-292`), $1.20 spent, nothing edited. Step 1b's
review had priced the same spec at ~565 and named the cut to make if the margin
went the wrong way — criterion 8, the CLI — a full cell earlier, for nothing.

The ceiling that killed it is not the one that would have judged the diff.
`size` is **advisory** for this spec, because nothing it touches is in
`.saffron/policy.yaml`'s `elevate_on`. So a 620-line diff would have shipped.
The plan checkpoint reads `_CEILINGS` without asking whether the gate blocks.

**Observation C.** A spec's own size estimate is knowable before the cell, from
the spec text, by a reviewer that already reads it. The loop has one: step 1b's
check 5 is "size vs ceiling", and it ran. What it lacked was authority — its
estimate is advice to the operator, and the number that decides is the
planner's, produced $1.20 later inside a cell.

**Item to file:** make the plan checkpoint's refusal read the effective risk,
so an advisory `size` gate does not block a plan the gate would have passed.

## Token counts are emitted and nothing keeps them

Asked mid-run (2026-09-19) whether the loop tracks tokens and time per cell.
Time and money are first-class: `attempts.started_at`/`ended_at`,
`attempts.num_turns`, `attempts.cost_usd_est` summed into
`tasks.spent_usd_est`, and `gate_results.duration_ms`. Both are ceilings the
scheduler enforces.

Tokens are not. `images/agent_runner.py:28-37` declares the usage keys and
attaches them at `:126` (the result's cumulative four) and `:133-137` (a
step's three, once per assistant `message_id`). They reach `events.jsonl` and
stop there: no `input_tokens` anywhere under `saffron/`, and no token column
in the ledger.

The emission is also newer than the machinery. Every task from `SA-0102`
through `SA-0108` has zero `input_tokens` lines in its event log. `SA-0109`,
run today, has them from the start — the same runner, a different SDK build
underneath it. So the loop's only token record is a per-task file whose
contents changed silently between runs.

**Item to file:** carry the result event's totals onto `attempts` beside
`cost_usd_est`, so a task's token cost is queryable and a cache-read
regression is visible across runs. The operator's call, 2026-09-19: file it
with this run's batch, not mid-loop.

## What the review round found, and what the cell's own critic did not

Six blockers across the two pull requests. The in-cell lenses raised one of
them, as a concern:

| Where | Blocker | Raised in the cell? |
|---|---|---|
| #375 | a probe cell that never came up escaped as an exception, discarding a paid REVIEW | no |
| #375 | duplicate-probe grouping and dedupe untested | yes, as a concern, and its probe survived |
| #375 | `probes.json`'s entry shape pinned by nothing | no |
| #377 | a module-scope `KINDS` lookup made `revert` skip | no |
| #377 | the `--status` witness could not fail for its criterion's reason | no |
| #377 | two criteria planted half the cases their claims list | no |

Five of the six are witness holes, which is item b-2750d5's whole subject. The
sixth is a spec-body behaviour with no criterion, which no gate asks about.

## `SA-0109` ran in production on the next cell of the same loop

`SA-0110`'s cell is the first task to have its adequacy probe run by the host.
The line reads `REVIEW: probes: 0 survived, 0 killed, 1 unproven`, and the
reason is `tests/records/check.py is a declared test path`.

That is criterion 4 working exactly as written, and it is also the mechanism
declining to answer the only question that mattered. The three `check_adr_*`
functions the spec delivers live in that file, because this repo puts its
record-checking logic under `tests/`. Applied by hand, the probe survives: the
concern was a real hole, and it became a blocker in review (item b-98dc4d).

So the first production use of the probe runner produced a correct `unproven`
on a finding that a person then confirmed by hand. The loop is still the thing
that closed it.

## The delegate's own edits, again

Run 8 recorded that delegate edits introduced blockers twice. Run 9 repeated
it, in a sharper form: the round-2 blocker on `SA-0109` was created by the
round-1 fix, and the round-3 concerns were created by the round-2 fix. Each fix
was correct in the paragraph it touched and wrong about a paragraph it did not.

Three rounds on one spec is not a cost the loop can carry per spec. What made
each round terminate was a re-review dispatched on the *whole* spec, not the
edit — the instruction the skill already carries, and the reason the run
converged at all.

One round-3 blocker was itself wrong: it derived, correctly step by step, that
`Finding.probe_verdict` would fail the `dead` gate, missing that criterion 5
forces a reader. Two minutes with a scratch worktree settled it — see
observation B.

