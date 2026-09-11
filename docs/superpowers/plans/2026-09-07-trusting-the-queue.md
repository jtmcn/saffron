# Trusting the Queue — Tier 1, re-sorted by what decides a pull request's soundness

> **For agentic workers:** this plan is mostly **not** implemented through the
> factory. Most of its items are a condition, a flag, a `None` or a sentence in a
> protected document, and the record below says why an afternoon by hand beats a
> cell for each. The tracks that *do* go through a cell say so, and the reason is
> always the same: the change is also a measurement of the factory. Do not invoke
> `superpowers:subagent-driven-development` or `superpowers:executing-plans` on
> it — the tracks are the operator's, and each ends in a record under
> `docs/evidence/`, not a diff.

Written 2026-09-07 against `main` at `9dfbcf2`. Companion page:
<https://claude.ai/code/artifact/8b4c3fe1-674f-434d-9df2-b800aad96a97>.

**Goal:** a queue of specs whose `READY_FOR_REVIEW` pull requests can be merged
without each needing the human review round every one so far has needed. That is
§9's v1 criterion read from the second half — *merge at least half of what it
produces* — rather than the first.

**Why the order changes:** `docs/BACKLOG.md`'s index is sorted toward *a night
runs while you sleep*, and that sort is correct for its target. But of the
fifteen Tier 1 items only 69, 79 and 80 bear on whether a packaged pull request is
sound; the rest make a night honest about what it did. Running four specs in a
queue today produces four pull requests each owed the same round. The
verification has to improve before the queue multiplies anything but review load.

---

## Where things stand

The last eight spec runs, read off `~/.saffron/ledger.db`, each pull request's
commit list, and the critic's `findings.json` under `~/.saffron/batches/v0/`.
"Human round" is what the independent review after packaging found and either
committed or filed.

| PR | Spec | Cell cost | Human round found | Critic on the same diff |
|---|---|---:|---|---|
| #135 | `SA-0056` | $3.20 | 1 review-fix | 1 blocker |
| #136 | `SA-0057` | $7.33 | 2 review-fixes | 1 blocker |
| #139 | `SA-0058` | $5.65 | 1 review-fix; item 71 (gate cannot run) | blocker raised, then withdrawn |
| #148 | `SA-0060` | $7.06 | 2 review-fixes | 1 blocker |
| #150 | `SA-0061` | $8.62 | 1 review-fix; items 74, 75 | 2 concerns |
| #154 | `SA-0062` | $8.70 | **2 critical fixes** (worktree destroyed or poisoned); items 78, 79 | 0 blockers, 3 concerns |
| #158 | `SA-0063` | $11.96 | items 80, 81, 82, 84 | 2 blockers |
| #160 | `SA-0064` | $5.64 | 1 review-fix; items 85, 86 | 0 findings |

`SA-0057`'s cost includes the $3.75 attempt lost to a provider error
(`docs/evidence/2026-09-06-a-provider-error-inside-a-night.md`). `SA-0059`, not
shown, ran to `EXHAUSTED` at $26.75 against a $16 ceiling and produced items 71
through 73.

Three readings, each of which a track below acts on:

- **The critic is not measured against anything.** REVIEW filed 0 blockers on
  PR #154 and 0 findings on PR #160. Nobody knows what it would say about a diff
  with a known defect in it, because no such diff is kept. Every lens change so
  far has been argued, which `CLAUDE.md`'s own rule — a measured fact beats a
  reasoned one — forbids.
- **The mechanism that answers "would the tests notice" is built and unusable.**
  Item 69's `witness` gate runs now (`SA-0060`–`SA-0062`), but a spec author
  cannot declare a mutant safely: a mutant on existing code kills the task at
  baseline (83), one on new code cannot match (82), the agent reads the mutant off
  the worktree copy (80, 85), and `revert` calls a forbidden-subject witness
  theater (84). `SA-0064` dropped a mutant to survive preflight.
- **Half the findings were the spec's fault.** Three consecutive specs boxed the
  agent in with `touches`; `SA-0063` forbade the one call site it needed. The loop
  skill records this as a standing gotcha. Nothing checks a spec before money is
  spent on it.

---

## The exit criterion

Decide what "trusted" means before starting, or the plan never ends. The threshold
is deliberately a count of things that already get written down, so it is read off
the record rather than felt.

**A queue is trusted when, over five consecutive spec pull requests at
`elevated`:**

1. the human review round commits nothing above a `concern` and files no new
   backlog item graded critical;
2. every declared mutant is killed by its named witness on the first attempt — no
   survivor, and no `skip` for a reason the spec author could have avoided; and
3. REVIEW grades at least **3** of the corpus's twelve declared defects — the
   count `docs/evidence/2026-09-09-lens-corpus-baseline.md` measured — **over two
   consecutive passes, or over one pass at a `--runs` high enough to state the
   spread** — and no fixture that graded a defect at baseline grades none.

   **`3` is one observation, and "at least 3" claims more than one observation
   can carry.** The baseline is a single pass under the current prompt, so it
   fixes the count and says nothing about its resolution. The margin clause is
   the whole criterion, not a caution attached to it: a pass reporting 3 is not
   evidence of anything until a second agrees, and a pass reporting 4 is not an
   improvement until a second does too.

   *This restores an instruction the 2026-09-09 rewrite of this criterion
   dropped.* The one-fixture version it replaced already said "raise n or require
   the same margin over two passes — a single 3/3 is within the spread already
   measured on a fixture nobody touched". That sentence applied more directly to
   `B` than to the number it was written for, and losing it is how the corpus
   version briefly asserted a floor off n=1.

   *Rewritten 2026-09-09 onto the corpus.* It read "both of PR #154's defects in
   3 of 3 runs", and its own revision note below had already recorded that
   statistic moving by a third between two passes of unmodified lenses. The
   corpus is eight fixtures and twelve defects, which is what it was built for.

   **`B = 3`, and pass 1's `4/12` is not evidence against it.** The adequacy
   prompt gained a required `probe` field between the two passes, adequacy owns
   **10 of the 12** declared defects, and both defects in the `4 → 3` difference
   are adequacy-owned. So the passes are one sample each of two configurations,
   not two samples of one: `4 → 3` is confounded, not noise and not a measured
   regression. `3` is the count under the prompt that runs from here on, which is
   the only configuration this criterion can be written against. The same fact
   bars the opposite claim — that requiring a probe cost adequacy nothing. It
   went 3/10 to 2/10 across the change, n=1 each side, and that is filed rather
   than guessed (`docs/BACKLOG.md` item 93).

   **The corpus is close to a single-lens measurement**, and the criterion should
   be read as one. Ten of twelve defects are adequacy's; `contract` and
   `correctness` own one each. A prompt change to either moves at most 1/12 here.

   Read it as a *difference* between two prompts, never as an absolute — the
   instruction the one-fixture version carried, and it survives the rewrite for
   the same reason. Item 88 is answered (2026-09-08): the harness reads harsher
   than production and the `gates.txt` was not why, so an absolute count off
   these fixtures is still not production's count.

   **One more reason not to read the vacuity number as an absolute**: 2 of the
   baseline's 8 verified vacuities rest on a cell baseline that was red for
   reasons nobody recorded — the same tree is green on the host. Item **94**.

   **The spread is now measured, at n=4.** `docs/evidence/2026-09-11-lens-corpus-spread.md`
   is a `--runs 3` pass under the same (post-probe) lenses as the baseline. Its three
   per-run totals — `1/12`, `2/12`, `3/12` — plus the baseline's `3/12` are four samples
   of one configuration, ranging `1/12` to `3/12`. That range is what "at least 3 …
   over two consecutive passes" is written against: a single pass reporting `3` is not
   distinguishable from this spread, which is the margin clause's whole point
   (`docs/BACKLOG.md` item 93).

Until the count is met, a batch night is a batch of pull requests each owed a
human round. Size nights by how many rounds you will do in the morning, not by
budget.

---

## The tracks

Lettered rather than numbered, because only some of them order each other; the
graph after them says which. Each names its backlog items, what done looks like
in the backlog's own words, and whether it goes through a cell or is done by hand.

### Housekeeping — first, one docs commit

**Items:** 71, 74, 78. **By hand.** Done in this branch.

Three Tier 1 items had moved on `main` without the index saying so. Verified
against the code and the ledger before marking, and one claim this plan's first
draft made did not hold:

- **74 is done.** `SA-0063` built the notes channel and `SA-0064` connected the
  production call; item 84 arrived through it, in `SA-0064`'s own `notes.json`.
  Caveat: no pull request body carries a notes section yet, because `SA-0064`
  packaged under `base_sha` code that predates its own wiring. The first task cut
  from a base at or after `bb9fd74` is the measurement.
- **71 is two-thirds done, not done.** `witness_gate` takes the injected mutator
  and `session._suite` supplies it; the ledger holds real `pass` verdicts for
  `SA-0063` and `SA-0064`. But PACKAGE's re-verification in
  `saffron/phases/package.py` passes neither `acceptance=` nor `mutate=` to
  `run_suite`, so `witness` is absent from that suite and `suite_drift` cannot
  say so. The remainder is a by-hand fix and is listed under Track B.
- **78 is done in code.** PR #154's own fixes made `source_mutated` yield a
  reason on a dirty file and restore from `HEAD` before a failed write re-raises.
  The `DESIGN.md` sentence is still owed and is listed under Track E.

The index's preamble now records the re-sort and cites this file.

### A — Build the scoring harness before touching a lens

**Items:** 79, 69 (evidence half), 86. **By hand**, host-side: a script under
`docs/evidence/scripts/` and a fixture directory of known-bad ranges.
**Size:** a day to assemble; about $8 in lens sessions per full scoring pass.

Item 79's "done looks like" is the whole track: keep PR #154's range as a
known-bad diff with its two graded defects and the independent review beside it,
and re-run REVIEW against it after every lens change, scored on how many of the
two it raises. Extend the corpus with the nine vacuous tests from item 69's table
(their commits are on `main`) and item 86's two unwitnessed properties. Each entry
is a `base..head`, the defect, its grade, and which lens should own it.

Mechanically this is feasible with the code as it stands. `phases.review.
run_review` takes a cell, the diff, the spec body and a gate summary and returns
the lens reviews; it does not care how the cell was built. The harness builds one
at the recorded head, drives the three lenses, and writes a table of raised/missed
per defect. Score before and after every change in Track C.

Nothing in this track changes the product, with one amendment. Its first output
is a record: the scoring table with the lenses as they are today, so Track C has
a baseline to move.

*Amended 2026-09-08.* The harness needs a cell at a recorded commit, so bringing
one up and tearing it down moved out of `_drive_cell` into `session.cell_up` and
`session.cell_down` — pure moves, no behaviour change, and the alternative was a
paraphrase of an order found by spike (Appendix I). Product code changed; what
the product *does* did not. Read the sentence as barring new behaviour, not
every line under `saffron/`.

*Delivered so far: item 79 only.* The corpus is one fixture,
`docs/evidence/fixtures/SA-0062/`. Item 69's nine vacuous tests and item 86's two
unwitnessed properties are still to come, and `load_fixture` takes a single root,
so aggregating across fixtures is unbuilt. The track stays open on those two.

### B — Make `witness` usable, then mandatory for bug-fix specs

**Items:** 83, 85 (closing 80), 84, 82, 81, 71 (remainder). **By hand**: one host pull request
for the gate and preflight conditions, one docs pull request for 82's
conventions. **Size:** two afternoons.

Four conditions, each already specified in its item:

- **83.** A witness the suite cannot collect reports `skip`, not `error`. Better,
  per the item: do not apply a non-`preserves` witness's mutant at base at all —
  §5.4 already requires that witness to fail there, so the question is not worth
  asking. This unblocks every bug-fix spec.
- **85, closing 80.** Preflight compares the host's copy of the spec with the one
  exported at `base_sha` and names a difference in its own line. Strip `mutant:`
  from the copy the cell can reach, so the withholding stops being a prompt-level
  control standing in front of the anti-theater mechanism.
- **84.** `revert` skips a witness whose subject lies outside the spec's
  `touches`, with a summary saying so. Unproven, not theater.
- **81.** Assert the criterion-path property directly over every spec
  `discover_specs` finds, with no ledger and no refusal ordering in front of it.
  One loop.
- **71, the remainder.** PACKAGE's re-verification passes `acceptance=` and a
  `worktree.source_mutated` bound to the package cell's container, so the two
  suites have the same shape and `suite_drift` can compare them. Without it a
  witness verdict is never re-run against the rebased head.

Then state 82's constraint where an author meets it, in
`docs/agents/issue-tracker.md` beside the rest of the spec format: a mutant pins
text the existing code determines; a spec that creates new code declares a
witness and no mutant. Pair it with the one-line validator the item names —
`intake.py` refuses at parse a mutant whose `find` text appears in the spec body
it is declared in.

Once these land, require a mutant on every criterion whose subject exists at
base, and read the survivor rate off real runs. That is what converts item 69 from
a lens that reads into a gate that runs, which is the only thing the record says
works (`docs/evidence/2026-08-25-mutation-testing-vs-a-lens.md`, read alongside
item 69).

### C — Close the remit gap, scored on the harness

**Items:** 79, 60. **Either**: prompt edits by hand, scored with Track A; a
fourth lens is a spec touching `saffron/phases/review.py`. **Size:** half a day
per iteration; stop when the harness moves. **After:** Track A.

*What does the failure path leave behind* is a question no lens owns. Try the
cheap shape first: widen the correctness lens's remit and score it on PR #154's
range. If it raises neither graded defect after two prompt iterations, give the
question to a fourth lens. Either way the harness makes the decision, not the
pull request description.

Add item 60 in the same pull request: re-prompt a lens once on `NotSchema`,
carrying the validation error, the way `artifacts.py` already does for the plan.
A correct finding discarded for a missing `severity` field is a silent version of
the same problem, and it cost $3.61 on `SA-0053`.

Also from item 79: a finding that contradicts an acceptance criterion the pull
request body renders as satisfied is a candidate for `blocker`. Say so in the
adequacy prompt.

### D — Refuse a broken spec before money is spent

**Items:** 56 (its shape), 81, 83, 85. **By hand**: a preflight check in
`saffron/intake.py` or beside `preflight`, exit `2` with a named reason.
**Size:** an afternoon; part of it lands with Track B.

Every check is a comparison of things the run already holds at preflight:

- every `witness` path and every `mutant.file` is reachable under the spec's own
  `touches`, and under none of its `forbidden`;
- no mutant's `find` text appears in the spec body (82);
- the host copy and the `base_sha` copy of the spec agree (85);
- the spec's `touches` fit under the tier's size ceiling (item 56's original
  question).

The loop skill's gotcha — *every spec that runs will produce findings that are
the spec's fault* — becomes a refusal line instead of a morning's adjudication.

### E — Make the night honest about what it did

**Items:** 70, 73, 45, 47, 26, 7, 78 (`DESIGN.md` half); then 51, 46, 40.
**By hand**: two host pull requests, then one real night of two small specs.
**Size:** two days for the six small ones; 51, 46 and 40 each want a design
decision first. **After:** independent of A–D; run the night after B lands so its
specs carry mutants.

These are the items the index was sorted for, and none of them decides whether a
pull request is sound. They decide whether an unattended night tells the truth
about itself. Most are an afternoon each and cheaper by hand than through a $6–$12
cell plus a review round:

- **70.** An in-flight terminal state changes the stop reason and the exit code.
  Leave the breaker alone, per the item's own argument.
- **73.** Take the *say it accurately* option: amend §3, `CONTEXT.md` and item 44
  to name the attempt as the overshoot unit and $26.75 against $16 as the
  measurement.
- **45.** Push the branch on any terminal state that made commits, record
  `pushed_sha`, say so on the way out.
- **47.** `commits` and `spent_usd_est` become `int | None` and `float | None`,
  set only where measured; rebuttal events carry the attempt number they ran at.
- **26.** `discover_specs` raises `SpecError` on a missing or non-directory path.
- **7.** Inject `CLAUDE.md` host-side from the mirror, the way `CONTEXT.md`
  already is.
- **78.** What is left is a sentence in `DESIGN.md` §5.4: a gate that mutates the
  tree self-guards against dirtiness, because `committed` runs after `run_suite`.
  Right now that ordering is load-bearing and written nowhere.

**51, 46 and 40** each carry a decision the item spells out — a `tests` contract
addition, the log's size cap and `secrets` reach, whether `size` counts test
lines. Take each decision in its own short pull request, then fix. Do not fold
them into the six above.

---

## What orders what

```
Housekeeping ─► A (harness) ─► C (remit gap) ─────────────┐
                                                          │
B (witness usable) ─► mutants required on bug-fix specs ─►│
   │                                                      ├─► exit criterion
   └─► D (spec preflight) ────────────────────────────────┤     (5 consecutive PRs)
                                                          │
E (night honesty) ─► one real night, two small specs ─────┘
```

A and B are independent and can start the same day. E is independent of both and
is the work to pick up while a harness pass or a night is running.

---

## Through a cell, or by hand

**Through a cell** when the change is also a measurement of the factory — a spec
that declares mutants once Track B lands, or a fourth lens once Track A can score
it; when the touched surface is one the spec can name honestly under `touches`
with the call site inside it; and when you are willing to do the human round,
because every one so far has needed it.

**By hand** for a condition, a flag, a docstring, a `None` — items 26, 47, 83,
84, 85 and most of Track E; the backlog's own history is mostly these. For
anything touching `DESIGN.md` or `CONTEXT.md`, which are `protected` and cannot
be a spec's to change. For evidence and harness scripts, which are not product.

The cost argument is plain. A cell run in the table above cost $3–$12 plus a
review round that found something every time. An afternoon by hand for an item
whose "done looks like" is already written is cheaper on both counts, and the
factory's own quality is not what an afternoon is meant to test.

---

## What to record

Each track produces a measurement, and each goes in `docs/evidence/` under the
existing rule:

- **A:** the harness's first scoring table, before any lens change.
- **B:** the mutant survivor rate over the first five specs that declare them,
  and how many `skip`s each reason produced.
- **C:** the scoring table after each prompt iteration, beside the diff of the
  prompt.
- **D:** which preflight refusal fired on the next ten specs written — the count
  says whether spec authoring improved or the check is too strict.
- **E:** the night's log, ledger rows and exit code, the way the three September
  records already do.

---

## What this parks, deliberately

Tier 2's operator-visibility pages (`SA-0032`–`SA-0039`) stay parked: they render
numbers this plan does not yet trust, and item 47 says the log they would read is
a column of zeros. Tier 3's ontology items stay where they are. The `tests`
contract change item 51 wants is real and is the one Tier 1 item this plan leaves
undecided, because it costs every onboarded repo and §9's v1 target lands before
v2's does.

If the exit criterion is met and the morning review rounds are still finding
critical defects, the criterion is wrong, not the order. Re-argue the criterion,
in this file, before re-sorting the items again.
