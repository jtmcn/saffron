# A prompt change that nothing can score

2026-09-17. Designed with the operator after the stack of #310, #312, #313 and
#317, which rewrote five prompts a cell reads on every task and shipped with no
measurement of the effect.

**Status:** designed, not built.

## Why

PRs #310 and #317 changed how a critic is told to write `claim`, `reason` and
`argument`. The pull request bodies say plainly that the effect is unmeasured,
and they are right: `harness/lens_scoring.py` scores whether a declared defect
was caught, not how the finding reads. Nothing in `make check` would notice if
the rewrite made a lens worse.

The gap is narrower than it first looks. The machinery for comparing two prompt
versions already exists and has been used once. `docs/evidence/2026-09-11-lens-corpus-spread.md`
ran the corpus three times with unchanged lenses to establish the metric's noise
floor. `docs/evidence/2026-09-11-lens-corpus-claude-md.md` ran the identical
corpus after `CLAUDE.md` reached the lenses, against a decision rule fixed in a
plan before either number existed. That pair is the experiment #310 wanted.

Three things stopped it being run again.

- **No arm is identifiable.** No `prompt_sha` exists in the ledger, in a pass's
  run JSON, or in a fixture. `attempts.model` is declared in `SCHEMA` and never
  written. A pass pins its prompts by prose in the evidence record, so a number
  cannot be joined to what produced it.
- **The metric is recall-shaped.** `seen` and `graded` measure whether a
  declared defect was found. Register has no reason to move them, so the
  instrument is blind to the change that prompted this design.
- **A pass costs money.** $16.53 and about 80 minutes for eight fixtures, so a
  guard that runs per pull request is a tax nobody pays.

## What this is not

It does not measure whether the house style helps a person adjudicate. That is
the honest question and it is a study of a reader, not of a model. It is out of
scope here and worth its own design.

It does not measure precision. Nothing today counts a finding that is wrong, and
control fixtures would be a corpus change with its own spend. Backlog item 130's
backtest has the shape, with ten controls and a bar of two false blockers. Hold
it until junk findings are observed rather than supposed, which is §8's ordering.

It does not yet supply a real `model` at the one place that writes it.
`attempts.model` is writable through `close_attempt`, but no call site
supplies a value, because `images/agent_runner.py` uses
`hasattr(message, "model")` only as a branch check and never extracts it, and
`AttemptResult` carries no such field. Closing it means the runner emitting
the model in its event schema and `implement.py` carrying it to the close.
Until then a prompt comparison cannot tell whether the model moved underneath
it. This wants a backlog item, and one could not be filed on this branch: the
records check requires contiguous ids, and every id between here and the open
pull requests is already claimed.

## The design

### 1. What identifies an arm

`tasks` already carries `spec_sha` and `policy_sha`: the spec a cell was given
and the policy it ran under. The prompt tree is the third input that decides
what a cell was told, and it is the only one unrecorded. So `tasks.prompt_sha`
is a hole in an existing pattern rather than a new concept.

The hash covers `saffron/agents/prompts/**` as authored, tracked files only,
sorted, content-hashed. Not the assembled prompt: that carries the spec body and
the per-phase `CONTEXT.md` sections, so it varies per task and identifies
nothing. The function belongs in `context.py`, which owns the tree through
`PROMPTS_DIR`.

`attempts.model` is written at the same time. A prompt comparison means nothing
if the model moved underneath it, and recording `prompt_sha` while `model` stays
null buys a number that is still unattributable.

A pass gains a manifest beside its `run-N.json` files: `prompt_sha`, model,
fixture ids, driver path, date. Today that provenance is prose in the evidence
record, which is the kind of claim `elevate_on` exists to keep from drifting.

This records what ran. It does not version a prompt and it does not gate one.

### 2. Scoring register, mechanically first

`.saffron/gates/prose.py` already holds a scorer. Its `check()` takes a string
and returns hits by rule: sentence length, hedge, filler, em-dash, semicolon,
contraction, perfect tense. Every `claim` a lens wrote is stored verbatim in
`docs/evidence/passes/*/run-N.json`. Running `check()` over those strings is
deterministic, costs nothing, needs no calibration, and measures the properties
#310 asked for. `tests/test_prose_gate.py` loads that script by path, so
reaching it from outside the gate is established.

**B1, mechanical.** Per-claim hits by rule, aggregated per pass. No cell and no
spend, so it re-derives from stored JSON the way `--score-only` already does and
fits the published-numbers convention as written. The spread pass holds 64
findings with claims, which is the sample step 1 works from.

**B1 reaches `claim` and nothing else.** The corpus runs REVIEW, so a pass holds
lens findings. `reason` comes from a verdict turn and `argument` from the
rebuttal extraction turn, and neither runs in the corpus. Two of the five
prompts #310 edited therefore stay unmeasured under this design. Measuring them
needs a corpus that exercises REBUT, which is a larger change and not proposed
here.

**B2, judged.** Analogies, a fact restated, praise, and whether a claim is
specific enough to check at its line. No regex sees these. B2 needs a rubric, a
model, and calibration against operator labels on a sample, in the shape
`calibrate` already uses. It is deferred until B1 is shown insufficient.

The scorer lives in `harness/register_scoring.py`, beside `lens_scoring.py`, and
`saffron/` never imports it.

### 3. The protocol

An arm is the tuple from section 1. A comparison is two arms differing in one
element. The decision rule is written before either number exists, as the
2026-09-11 pair did.

The rule reads against the noise floor: a change counts as measured only when it
moves the metric further than the same metric wanders with nothing changed, in
the direction named in advance. Anything smaller is recorded as **unmeasured**.

That outcome is first class rather than a failure. `error` is not `fail` and
`RATE_LIMITED` is not `EXHAUSTED`, and an unmeasured change is not a failed one.
It is a change whose effect this instrument cannot see. #310 and #317 are both
in that class, and saying so is more useful than a number nobody should trust.

Eight fixtures is a small corpus. §8 already says the statistics are noise at
this volume and to reread monthly rather than weekly. This is a guard against a
large regression, not an instrument for a small win, and the evidence record
says so in its own text.

**Cadence.** B1 runs on every pass and costs nothing. The paid comparison runs
once per stack of prompt changes, when they are ready to land, rather than per
pull request.

**Where the requirement lives.** `.github/pull_request_template.md`, under
Verification, which already asks for a measured fact. Not `CLAUDE.md`: the file
is at 206 lines against §8's ~200, and Appendix S names layout and reference as
the first bucket to cut. Promote the requirement to a gate after convention is
ignored once, per §8's ordering, and not before.

## The order of work, and who does each piece

The first step is free and can kill the design, so it comes first.

1. **Score the spread pass for register. By hand, no spend.** The three runs of
   `2026-09-11-lens-corpus-spread` used unchanged prompts, so scoring them gives
   the new metric's noise floor from data already on disk. If register hits are
   stable across identical prompts, B1 has signal. If they wander as far as a
   prompt edit would plausibly move them, B1 is dead and the cost of learning
   that is nothing. A throwaway script, and an evidence record of the result.
2. **Build the scorer. A spec.** `harness/register_scoring.py` and its tests.
   The cell spends nothing, calls no model, and reads passes from disk, so the
   witnesses are ordinary test node ids. It lands `elevated` through
   `harness/**`, which is correct: the policy's own note for that entry says the
   scorer decides whether a lens change looks better.
3. **Record the arm. By hand.** `tasks.prompt_sha`, `attempts.model`, and the
   pass manifest. The code is reachable by a cell and `ledger.py` already
   migrates additively. `DESIGN.md` §4.1 documents the schema and is protected,
   no test holds §4.1 against it, and a cell would therefore add the column, go
   green, and leave the design record wrong. That is backlog item 30's failure
   mode and the reason item 160 is `by_hand`. Splitting it so a cell writes the
   code and the operator lands §4.1 leaves the document a pull request behind,
   which is the same defect, so the whole piece is by hand.
4. **Cite a pass. A spec, and it can ride with any other work.** One line in the
   pull request template.

Nothing in this design spends until step 1 has said the metric has signal. Step
1 is free, it runs against data already on disk, and it can say stop.

Two things are never a spec. The paid pass spends money and must not run while a
batch is live, because the proxy and the network are shared. And whether a
number clears the decision rule is a judgement, which is the operator's.

## What would have happened to #310

B1 would have scored the `claim` strings of the arm that shipped the prohibition
against the arm that shipped the recipe, for the three lens prompts. Whether it
would have separated them is exactly what step 1 measures and nobody knows yet.
The `reason` and `argument` edits would still be unmeasured, because no corpus
runs those turns. Recall would have said nothing about any of the five, which is
the finding that started this.
