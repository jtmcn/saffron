# A second, mutation-verified number for the lens corpus

Written 2026-09-09. Companion to `docs/superpowers/specs/2026-09-08-lens-corpus-design.md`,
which is authoritative for why the corpus exists. This spec covers one addition: a second
number, measured rather than declared, and what it may and may not be read to mean.

## The problem, in the corpus's own numbers

Pass 1 filed 23 findings across eight fixtures — 10 adequacy, 8 contract, 5 correctness.
Four declared defects are matched, so the corpus reports **4/12 declared defects graded**.

That number is a targeting lottery. Each diff holds several vacuities and the corpus
declares one, so the score answers "did the lens find *this* vacuity" where the question
Track C is asking is "can the lens find vacuities at all". The mutation spike of 2026-09-09
measured the gap directly: four mutations the adequacy lens named were applied at their
fixture heads and the suite ran green on all four, so at least four verified-real vacuities
were found, only one of which was declared.

The four are recorded in `docs/evidence/2026-09-09-adequacy-probe-spike.md`
(`docs/BACKLOG.md` item 91, closed). `f76931df` and `91f56c69` are transcribed there from an
independent reproduction during review, to the exact figure; the `f9f007c4` pair was
reproduced again for that record and matches the original spike exactly. The original spike's
own four runs, at the time it made this case, remain unrecorded — a precondition of the plan
this spec leads to, not of this spec itself:

| Mutation the lens named | Fixture head | Suite |
|---|---|---|
| `safe = neutralize(text)` -> `safe = text` (`pr_body.py:391`) | `f76931df` | 1502 passed |
| drop `run_id > ?` from the query at `batch.py:72` | `91f56c69` | 1292 passed |
| `create_run` inserts `None` for `batch_id` | `f9f007c4` | 1250 passed |
| `batches.status` gains `NOT NULL` | `f9f007c4` | 1250 passed |

The ten adequacy findings account as: four verified above; one (`SA-0048`) matching a
declared defect already; three read and judged plausible but never run (`SA-0054`'s pair and
`SA-0063`'s `session.py:1616`); and two — both `SA-0062`'s, about `source_mutated`'s own
tests — that nothing has classified either way. The three read-but-not-run are not counted,
because "read, not run" is the standard this whole spike exists to replace. The two
unclassified are not counted either, and are named rather than rounded away.

## What is being added

For every adequacy finding in a pass: apply the mutant it names at the fixture head, run the
repo's declared `tests` gate, and record whether the suite stayed green. **A mutant that
survives is a verified-real vacuity** — the tests do not notice the behaviour breaking, which
is precisely what the finding claimed.

This inverts `witness_gate`'s verdict. That gate wants a mutant to *die*, because a witness
that stays green under its own mutant asserts nothing. Here a surviving mutant is the
positive result, for the same underlying reason read from the other side.

The corpus then reports two numbers:

- **Declared recall** (`4/12`) stays the primary, because it is the one comparable across
  passes and across prompt changes.
- **Verified-real vacuities** sits under it as the capability number.

Lens-found defects are **never promoted into the declared set**. Promoting them would bias
the corpus toward whichever prompt found them, so a later prompt that found different real
defects would score worse while being better.

## Why the machinery is small

Almost all of it exists.

`intake.Mutant` (`file`, `find`, `replace`) is §5.4.1's own model and is already the right
type. It is deliberately not line-numbered — *"a mutant naming line 51 stops meaning anything
the moment the implementation shifts by a line"* — which matters here more than it does for a
spec, because a lens's line number is exactly the thing pass 1 showed to be unreliable.

`worktree.source_mutated(container, mutant)` applies `find` -> `replace` inside a cell and
restores from a `finally`. It refuses **six** cases by yielding a reason instead of `None`: a
path outside the worktree, a path not tracked at `HEAD`, a path tracked as something other
than a regular file, a file carrying uncommitted work, a `find` that is absent, and a `find`
that matches more than once.

The count matters, because the two most easily overlooked are the two that do the most work
under model-authored input. `source_mutated`'s own docstring said "four" and omitted the
`ls-tree` pair — a symlink is worse than an untracked path, since the read and the write
follow it while `git checkout` restores the link, which never changed, and exits 0, so the
mutation survives inside a success. That docstring is corrected in the same change as this
spec.

The corpus driver already brings up a cell per fixture with `tree_base=fixture.head_sha` and
that head's own `.saffron/` exported as `gates_dir`. So the tree the mutation belongs in, and
the `tests` gate that judges it, are both already there for the duration of a pass.

`witness_gate` shows the composition: a `Mutated`, which is a callable *from* a `Mutant` *to*
a context manager — `witness.py` is careful about that phrasing because it is why the gate
holds no path of its own — and a
`RunTests = Callable[[list[str]], GateResult]`. An empty subset runs the whole suite —
checked in this repo's own gate (`.saffron/gates/tests.py` reads `subset = sys.argv[1:]` and
splices it into the pytest argv), not assumed. Another target repo's `tests` gate is its own
and owes only the JSON contract.

### The one genuinely new thing: trust

`witness_gate`'s §2.1 exception is stated narrowly and does not transfer unexamined:

> It is `revert`'s exception, not a new one (§2.1). This gate executes no tool: it applies a
> text edit the *spec* supplied — data, not code — through an injected `mutate` context
> manager, and then invokes a gate the repo already declared, through the same JSON contract
> every gate uses [...]

A spec is human-authored and reviewed before a task runs. **A lens's mutant is
model-authored**, produced by an agent inside a cell. The mechanism is identical; the trust
position is not, and this spec does not get to borrow the sentence.

What carries it here is confinement, not provenance: the mutant is applied and the suite runs
**inside the fixture's own cell**, which is untrusted by construction. Nothing runs on the
control plane that did not already run there. Precisely: the host executes the cell runtime
with argv it builds — argv, never a shell string, with the payload and the path both
`shlex.quote`d — and reads back a `GateResult` plus `ls-tree` and `status` output. It writes
nothing into the tree itself and interprets nothing the model wrote. That is a weaker
sentence than "the host executes nothing", and it is the true one.

The `find`-matches-exactly-once rule does real work under this weaker trust position. It does
not bound *what* is written — `replace` is arbitrary model text of arbitrary length — but it
bounds *where* the edit lands to a single site the model had to name exactly. Arbitrary model
text does reach a tree; it reaches a tree inside a cell, at one place, and that is the claim
this section can support.

### The harder problem: `CONTEXT.md` already refused this

`CONTEXT.md` defines the word:

> **Mutant**: A find-and-replace edit *a criterion declares* against its own subject, which
> its witness must fail on (`DESIGN.md` §5.4.1). [...] Withheld from the implementer's prompt
> on purpose: **a mutant a cell chooses is a mutant chosen to be killed.**

This spec proposes a mutant a cell chooses, under an inverted verdict where surviving is the
win. The existing sentence names the failure mode and this design is its mirror image: a
mutant a cell chooses under *this* verdict is a mutant chosen to **survive**.

That is not a hypothetical. The adequacy prompt (`review-adequacy.md`) currently says:

> name the smallest concrete edit — **to the source or to the test** — that would keep the
> test passing while the behaviour it claims to cover breaks

A mutant that deletes an assertion from a test survives trivially, and under the design as
first drafted it would be counted as a verified-real vacuity. The number would be satisfiable
by construction, and the prompt it is built on explicitly offers the route.

Two changes follow, and neither is optional:

1. **The mutant must target a file the diff does not add or modify as a test.** The declared
   `touches` and the diff are both already available to the harness; a mutant landing on a
   test file is a fourth outcome (below), never a survival. The adequacy prompt's "or to the
   test" clause stays — it is right for a human reader adjudicating a finding — but the
   *field* is narrower than the prose, and the prompt must say so.
2. **This gets its own term, not a widened `Mutant`.** A find-and-replace edit a *lens* names
   under an inverted verdict is a different thing from the `Mutant` that entry defines, and
   the sentence about a cell's mutant being chosen to be killed is a live design commitment
   protecting the `witness` gate. Widening the word to cover both would delete its force
   exactly where it still does work. The new term is **vacuity probe**, with an `_Avoid_`
   line pointing back at `Mutant`, which is `CONTEXT.md`'s own idiom for a near-miss pair.

   Checked rather than assumed: `Mutant` is **not** one of the six closed sets
   (`tests/ontology/test_vocabulary_agrees_with_context.py`'s `CLOSED_SETS` names Terminal
   state, Batch stop reason, Severity, Risk tier, Gate role and Core gates), and
   `ontology.render.render_context` rewrites only those sets' backticked spans. So this entry
   is hand-maintained prose: no `ontology/saffron.ttl` edit, no render step, and — the reason
   it needs saying — no test that would catch the two terms drifting into each other later.
   An earlier draft of this spec said the opposite, having read `CLAUDE.md`'s rule without
   its "For the closed sets" qualifier.

## The schema change

`_Reported` splits per lens. Adequacy's variant requires `mutant: Mutant`; correctness's and
contract's do not carry the field at all.

Adequacy only, because only its prompt asks for a concrete edit, and only its defect class is
expressible as one. A timezone bug or a wire-format break is not "an edit that keeps the suite
green"; requiring the field there would push those lenses toward manufacturing one, which
their prompts explicitly forbid. Optional-everywhere was rejected for the same reason the
corpus exists: a field filled sometimes and not others makes the number a phrasing lottery one
level up.

**`Finding.mutant` is optional, and that is not a contradiction.** `_Reported` is what the
lens emits and what the host validates; `agents.findings.Finding` is what the host keeps, and
`lens_scoring.reviews_from_json` rebuilds it with `Finding(**f)` out of each fixture's
`recorded-findings.json`. `calibrate_corpus` runs that before every paid pass. A required
`mutant` on `Finding` would therefore make every existing fixture fail to load and every
future pass refuse to start. So: required on adequacy's `_Reported`, optional on `Finding`,
and round-tripped by `LensReview.as_dict`. The rejection of "optional everywhere" above is
about the lens output schema, which is where the phrasing lottery would live — not about the
downstream record, which has to keep reading passes recorded before the field existed.

The prompt change is one paragraph, and it is in the direction `review-adequacy.md` already
argues. It currently says:

> You cannot mutate a line and watch a test fail, which is the ordinary way a person would
> answer this question. [...] name it precisely enough that someone who *can* run something
> checks your claim in one command.

The field makes that literal instead of aspirational. It is still a prompt change, and it
therefore moves the baseline — so it **lands before pass 2, never between passes**, the same
rule the `Defect` locations change followed.

Three changes move the baseline, not two, and the third is easy to miss: the schema field,
the prompt paragraph, and **`extra="forbid"` on `_Reported`**, which makes an unexpected key
reject the whole report rather than be dropped. All three land together, before pass 2.

`extra="forbid"` is what makes the schema exact enough to be worth requiring — a lens that
answers `mutant` instead of `probe` must not read as a lens that answered — but it prices a
malformed finding at the whole report: one re-prompt follows, carrying pydantic's own message
(`f"{exc}\n\n{EXTRACTION_PROMPT}"`, so the missing field is named), and a second failure sets
`LensReview.error`, which drops all three lenses' findings for that run. **Pass 2's drop rate
is therefore newly sensitive to a schema the adequacy lens has never been asked for.** Watch
it on the first fixture rather than at the end of the pass: a lens dropping there is a prompt
problem to fix before seven more fixtures pay for it.

## What a run does, per fixture

1. Run the `tests` gate on the unmutated head tree once. This is the baseline.
2. For each adequacy finding, in turn: apply its mutant through `source_mutated`, run the
   `tests` gate over the whole suite, restore.
3. Compare each mutated run against the baseline with `gates.baseline.subtract_baseline`.

Step 3 is why the baseline is taken rather than assumed. A fixture head is a merged PR head
and its suite is expected green, but "expected" is not "measured", and a head carrying one
pre-existing failure would otherwise read every mutant as killed. Baseline subtraction counts,
and identities collide legitimately — one baseline failure cancels one head failure, never all
of them.

Two exposures the plan owes an answer to, named here so they are not discovered late. **A
flaky test reads as `killed`** — one `tests` gate run per mutant, no repeats, and a mutant
that survives is the positive result, so flake biases the number downward. **A probe that
breaks collection changes the suite**, which makes the subtraction untrustworthy rather than
merely non-empty; step 3 as written does not compare `collected`, and the outcomes section
below says it must.

### Three computed verdicts, and a fourth a person writes

- **survived** — no new failures against the baseline. A verified-real vacuity. Counted.
- **killed** — new failures. The tests *may* have noticed, or the probe may have broken the
  program; the record itemises the failures so a reader can tell. Counted, as a negative.
- **unproven** — the probe did not apply (any of `source_mutated`'s six refusals), the
  `tests` gate could not answer, the probe targeted a test file, or the suite's *collection*
  drifted. Named in the record, counted toward neither.
- **collateral** — not computed. What a person writes next to a `killed` they judge to be
  program breakage rather than a test doing its job. See below for why it cannot be the
  harness's call.

`error` is not `fail`. A `tests` gate that could not start has said nothing about the
mutant and is charged to nobody. Collapsing unproven into killed would let a mutant that
never ran read as a lens that was wrong, which is the exact shape the corpus exists to
refuse.

**`collateral` is not a hypothetical, and it is not cheap to detect.** Measured on one of the
four mutations this spec argues from. SA-0050's recorded adequacy claim names its edit as
dropping `run_id > ?` from the query at `batch.py:72`. Applied literally at `91f56c69` —
`"SELECT run_id FROM runs WHERE run_id > ? AND batch_id IS NULL"` becomes
`"SELECT run_id FROM runs WHERE batch_id IS NULL"`, leaving the `(high_water,)` binding in
place — the suite goes **2 failed, 1290 passed** with
`sqlite3.ProgrammingError: Incorrect number of bindings supplied` at `batch.py:71`. The
*intended* mutation, which also removes the binding, survives green at **1292 passed**.

So the design as first drafted scores one of its own motivating examples `killed`, and
charges the lens for a vacuity that is real. Expressing that edit correctly needs a
multi-line `find` spanning the collateral change — which the lens's prose does not produce
and which no field yet asks it for.

**`collateral` is adjudicated, not computed, and that is the answer rather than a deferral.**
No mechanical test separates it from `killed` in general: the SA-0050 case fails at runtime
inside two pre-existing tests, so it is indistinguishable by shape from a probe the tests
genuinely noticed. Inventing a heuristic here would put a silently-wrong step inside the one
number that exists because reading is not running.

So the harness computes three verdicts and reports the fourth as an annotation:

- The mutated run's `GateResult.collected` is compared against the baseline's, as a **set**.
  A probe that changes what the suite collects has broken the program at import time, and
  that is `unproven` — mechanical, sound, and it catches the whole syntax-error family.

  A set difference, and deliberately not `subtract_baseline`'s counting rule: a node id is
  unique in a suite, so a name that stopped being collected is a removal, where two failures
  can share an identity legitimately. `census` already draws exactly this distinction on
  exactly this field, and the two rules sit beside each other in `baseline.py` for that
  reason. (`gates.baseline.suite_drift` is *not* the right tool here and an earlier draft
  said it was: it compares one gate's `tool` identity against another's and catches a gate
  that stopped running, across a suite of gates. It never looks at `collected`.)
- Anything still failing is reported as `killed` **with its failure identities itemised** in
  the record, so a person reads the kills rather than a count. The bucket is small — nine
  unmatched adequacy findings in pass 1 — so this costs one screen, not a morning.
- `collateral` is what a person writes next to a kill they judge to be program breakage.

The number the corpus reports is therefore a **lower bound on capability**, and the record
carries what it would take to raise it. That is the honest shape, and it is the one this repo
takes everywhere else: name the limit rather than collapse it.

## Where it lives

- `harness/probe_check.py` — new. Composes `source_mutated` and the `tests` gate, applies
  the three-way verdict, aggregates per fixture. It measures rather than gates, so `harness/`
  and not `saffron/gates/core/`, per CLAUDE.md's split — and it is the part that can be
  silently wrong, so it is the part with tests.
- `harness/corpus.py` — the second number joins the rendered table under the aggregate.
- `saffron/agents/` + `saffron/phases/review.py` — the per-lens `_Reported` split.
- `saffron/agents/prompts/review-adequacy.md` — one paragraph.
- `CONTEXT.md` — the **vacuity probe** entry, hand-maintained prose beside `Mutant`, with an
  `_Avoid_` line each way. No ontology edit and no render step; see above.
- `docs/evidence/scripts/2026-09-08-lens-corpus.py` — calls the check while each fixture's
  cell is still up.

`saffron/` gains a schema field and a prompt paragraph. Nothing else about the product moves.

## What this number does not measure

Stated here so it cannot be read as more than it is, wherever it is rendered:

- **It says nothing about contract or correctness findings** — 10 of pass 1's 18 unmatched
  findings. It is a vacuity-capability number only and must be labelled as one. (Counted per
  finding against the corrected predicate, not derived: five findings match a declared
  defect, because SA-0048's `refusal-codes-unpinned` is matched by the correctness *and* the
  adequacy lens at `preflight.py:315`. An earlier draft said "13 of 19" by subtracting from
  the defect count and taking contract + correctness whole, which double-counts the three of
  them that did match.)
- **It cannot be computed for pass 1.** The recorded runs carry no `mutant` field. Pass 1's
  four verified mutations were transcribed by hand during the spike and stay a record, not a
  number. The second number starts at pass 2 with no continuity backwards.
- **A surviving mutant proves a test gap, not that the change should not merge.** Severity
  is still the lens's judgement and is still adjudicated by a person.
- **It is not a mutation-testing score.** One mutant per finding, chosen by the lens to make
  its own case, is not a sample of the mutation space and must never be reported as coverage.

## Caching: no

A later pass re-verifies every probe, even where the fixture head has not moved. Caching is
cheaper and is also the shape that lets a stale verdict outlive the code it was measured
against — and the verdict here depends on the whole suite at that head, not just on the
mutated line, so "the head has not moved" is not the invariant a cache would need.

The cost is bounded, and now measured. The probes run inside a cell a pass already brings up
per fixture, so they add no model spend and no image build. They add suite runs — one
baseline plus one per adequacy finding.

**Measured 2026-09-09, one fixture end to end** (`SA-0045`, head `f9f007c4`, the plan's Task
5 Step 4): the pass took **499.8s** and cost **$1.58**. The adequacy lens filed **two**
probes. Probing began at 453.9s, the first probe's verdict landed at 483.5s and the second
at 497.5s — so **14.0s per probe**, and the baseline is **~15.6s** by subtracting one probe
interval from the first, which covers baseline plus probe 1. The whole probe phase was
**45.9s of 499.8s, about 9%**.

One fixture, not eight, and one whose two probes are near the corpus mean of 1.25 adequacy
findings per fixture in pass 1. Scaling that shape to eight fixtures puts the probes at
roughly six minutes on a pass that already runs about eighty — not the half hour an earlier
draft of this paragraph projected.

That draft was wrong for a reason worth recording. It scaled from five host suite runs
timed at 78-104 seconds during this branch's review — but those ran while several review
subagents were working on the same machine, so they measured contention as much as the
suite. The `tests` gate's own comment at `f9f007c4` puts a full run there at **~36s**, and
in-cell it is 14s including the `--collect-only` pass, on a host doing nothing else. A
timing taken under unstated load is not a measurement of the thing it names.

**Still not recorded per probe: which suite answered.** A verdict of `survived` means "no new
failure against the baseline", and nothing in `probes-*.json` says how many tests the gate
collected to reach it. Both runs collecting the same set is checked — a drift makes the probe
`unproven` — but both collecting *few* is not. Persisting the `GateResult`'s `collected`
count and `tool` beside each verdict would close that, and is worth doing before the number is
read as a capability score.
