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

The four, **not reproduced for this spec**. They are transcribed from that spike's own
record, and that record is a session ledger rather than a file under `docs/evidence/`.
Landing it there is a precondition of the plan, not of this spec — a number this document
argues from should not live only in a scratch directory:

| Mutation the lens named | Fixture head | Suite |
|---|---|---|
| `safe = neutralize(text)` -> `safe = text` (`pr_body.py:391`) | `f76931df` | 1502 passed |
| drop `run_id > ?` from the query at `batch.py:72` | `91f56c69` | 1292 passed |
| `create_run` inserts `None` for `batch_id` | `f9f007c4` | 1250 passed |
| `batches.status` gains `NOT NULL` | `f9f007c4` | 1250 passed |

Four more adequacy findings were read and judged plausible but never run. They are not
counted, because "read, not run" is the standard this whole spike exists to replace.

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
restores from a `finally`. It refuses four cases by yielding a reason instead of `None`: a
path outside the worktree, a file carrying uncommitted work, a `find` that is absent, and a
`find` that matches more than once.

The corpus driver already brings up a cell per fixture with `tree_base=fixture.head_sha` and
that head's own `.saffron/` exported as `gates_dir`. So the tree the mutation belongs in, and
the `tests` gate that judges it, are both already there for the duration of a pass.

`witness_gate` shows the composition: a `Mutated` context manager and a
`RunTests = Callable[[list[str]], GateResult]`. An empty subset runs the whole suite —
checked in this repo's own gate (`.saffron/gates/tests.py` reads `subset = sys.argv[1:]` and
splices it into the pytest argv), not assumed. Another target repo's `tests` gate is its own
and owes only the JSON contract.

### The one genuinely new thing: trust

`witness_gate`'s §2.1 exception is stated narrowly and does not transfer unexamined:

> It is `revert`'s exception, not a new one (§2.1). This gate executes no tool: it applies a
> text edit the *spec* supplied — data, not code — through an injected `mutate` context
> manager.

A spec is human-authored and reviewed before a task runs. **A lens's mutant is
model-authored**, produced by an agent inside a cell. The mechanism is identical; the trust
position is not, and this spec does not get to borrow the sentence.

What carries it here is confinement, not provenance: the mutant is applied and the suite runs
**inside the fixture's own cell**, which is untrusted by construction. The host writes
nothing, executes nothing, and reads only a `GateResult`. Nothing runs on the control plane
that did not already run there.

The `find`-matches-exactly-once rule does real work under this weaker trust position: a
model-authored `find` that is absent or ambiguous applies nothing and is reported unproven.
It is the difference between a bounded text substitution and arbitrary model text reaching a
tree, and it is inherited rather than re-derived.

## The schema change

`_Reported` splits per lens. Adequacy's variant requires `mutant: Mutant`; correctness's and
contract's do not carry the field at all.

Adequacy only, because only its prompt asks for a concrete edit, and only its defect class is
expressible as one. A timezone bug or a wire-format break is not "an edit that keeps the suite
green"; requiring the field there would push those lenses toward manufacturing one, which
their prompts explicitly forbid. Optional-everywhere was rejected for the same reason the
corpus exists: a field filled sometimes and not others makes the number a phrasing lottery one
level up.

The prompt change is one paragraph, and it is in the direction `review-adequacy.md` already
argues. It currently says:

> You cannot mutate a line and watch a test fail, which is the ordinary way a person would
> answer this question. [...] name it precisely enough that someone who *can* run something
> checks your claim in one command.

The field makes that literal instead of aspirational. It is still a prompt change, and it
therefore moves the baseline — so it **lands before pass 2, never between passes**, the same
rule the `Defect` locations change followed.

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

### The three outcomes, which are not two

- **survived** — no new failures against the baseline. A verified-real vacuity. Counted.
- **killed** — new failures. The tests *do* notice; the finding was wrong about that.
  Counted, as a negative.
- **unproven** — the mutant did not apply (`find` absent or ambiguous, path outside the tree,
  file not clean at `HEAD`), or the `tests` gate could not answer. Named in the record,
  counted toward neither.

`error` is not `fail`. A `tests` gate that could not start has said nothing about the
mutant and is charged to nobody. Collapsing unproven into killed would let a mutant that
never ran read as a lens that was wrong, which is the exact shape the corpus exists to
refuse.

## Where it lives

- `harness/mutation_check.py` — new. Composes `source_mutated` and the `tests` gate, applies
  the three-way verdict, aggregates per fixture. It measures rather than gates, so `harness/`
  and not `saffron/gates/core/`, per CLAUDE.md's split — and it is the part that can be
  silently wrong, so it is the part with tests.
- `harness/corpus.py` — the second number joins the rendered table under the aggregate.
- `saffron/agents/` + `saffron/phases/review.py` — the per-lens `_Reported` split.
- `saffron/agents/prompts/review-adequacy.md` — one paragraph.
- `docs/evidence/scripts/2026-09-08-lens-corpus.py` — calls the check while each fixture's
  cell is still up.

`saffron/` gains a schema field and a prompt paragraph. Nothing else about the product moves.

## What this number does not measure

Stated here so it cannot be read as more than it is, wherever it is rendered:

- **It says nothing about contract or correctness findings** — 13 of pass 1's 19 unmatched.
  It is a vacuity-capability number only and must be labelled as one.
- **It cannot be computed for pass 1.** The recorded runs carry no `mutant` field. Pass 1's
  four verified mutations were transcribed by hand during the spike and stay a record, not a
  number. The second number starts at pass 2 with no continuity backwards.
- **A surviving mutant proves a test gap, not that the change should not merge.** Severity
  is still the lens's judgement and is still adjudicated by a person.
- **It is not a mutation-testing score.** One mutant per finding, chosen by the lens to make
  its own case, is not a sample of the mutation space and must never be reported as coverage.

## Open, and deliberately not decided here

Whether a *later* pass should re-verify a mutant whose fixture head has not moved, or cache
the verdict. Caching is obviously cheaper and equally obviously the shape that lets a stale
verdict outlive the code it was measured against. Left to the plan, where the cost of a
re-run will be measured rather than estimated.
