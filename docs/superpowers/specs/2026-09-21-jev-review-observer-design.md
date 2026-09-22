# Jev observes the review loops, and nothing reads its scores yet

Spec review and code review end when a reviewer runs out of findings. Review
round count is the only stop signal, and it says nothing about whether the
last review round mattered. Jev is TypeSafe's System One model. It returns
typed, calibrated answers with no prose. This design adds Jev as an observer
of every review round. It scores what each reviewer produced and writes the
scores to disk.

Nothing reads the scores in this phase. They never change a gate result, a
verdict, a queue order or a stop decision. The source note is
`~/temp/jev-review-logging.md`.

## Decisions taken in design

1. **Jev lives outside core.** The scorer is `harness/jev_observe.py`, and
   `saffron/` never imports it. Onboarding a vendor this way touches zero lines
   of core, as §2.1 requires.
2. **The spec loop driver runs it.** A new `driver.py jev` command scores one
   review round. The cell's REVIEW phase is scored after the task ends, from
   `findings.json`, so `run_task` stays unchanged.
3. **Reviewers emit a JSON block.** Both report formats end with a fenced
   `json` block of findings. The scorer never parses prose.
4. **The record is EARL Turtle.** One `earl:Assertion` per answer, as
   `DESIGN.md` §4 item 2 already uses for gate results and critic findings.
5. **Failure never blocks a loop.** A failed Jev call is noted and the loop
   carries on.

Three loops are observed. The spec loop's spec review uses the `spec-reviewer`
agent. The spec loop's code review is step 2c, where the Spec seat and the
Standards seat each review a PR. The cell's own REVIEW phase runs lenses and
then REBUT.

## Questions

Every question below is asked in one Jev call per review round (Changed while
planning, item 3). `Noul` is the SDK's name for a yes-or-no question and
returns the probability of yes.

| Code | Asked of | Question | Type |
|---|---|---|---|
| Q1 | each finding | Which criterion does this affect? | Choice over the spec's criteria and `noMatch` |
| Q2 | each finding | Severity | Score: 3 blocking, 2 should-fix, 1 nit, 0 noise |
| Q3 | each finding | Would fixing it change the criterion's outcome? | Noul |
| Q4 | each finding | Is it materially new against every earlier review round? | Noul |
| Q5 | each earlier finding | Does this review round's diff address it? | Noul |
| Q6 | each review round | Would another review round surface a blocker? | Noul |
| Q7 | each criterion | Is it testable as written? | Noul |
| Q8 | each criterion | Does it define an evidence path? | Noul |
| Q9 | each criterion | Does it conflict with another criterion? | Choice over `none` and the other criteria |

Which questions apply depends on the loop.

| Loop | Questions |
|---|---|
| `spec-review` | Q1 to Q9 |
| `pr-review` | Q1 to Q6 |
| `cell` | Q1, Q2, Q3, Q6 |

The cell's REVIEW is a single pass, so it has no earlier review round for Q4
and Q5.

The state Jev sees for a review round is the spec, the review round's
findings, the diff since the previous review round, and every earlier review
round's findings.

## The record

Each review round writes one `jev.ttl`. Every answer becomes one `earl:Assertion` with
these parts.

- `earl:assertedBy jev:jev`.
- `earl:subject`, the finding or criterion the question is about.
- `earl:test`, the question, named by its code.
- `earl:mode earl:automatic`.
- A result whose outcome is always `earl:cantTell`, because a choice or a score
  has no pass or fail.
- The full probability distribution, as an `rdf:JSON` literal.
- The model name from the response, the review round number and the commit reviewed.

The distribution is kept whole because a flat split says the question was
ambiguous, which the top answer alone hides.

A finding's identity is a hash of the loop kind, the spec id, the review round
number and the finding's index in the JSON block. Re-scoring a review round
therefore keeps every id.

The terms live in their own namespace, `urn:software-factory:jev#`, not
`ontology/factory.ttl`. `jev:jev`, one individual per question, and the
distribution property are declared inline in `to_turtle`, not by
`ontology.render` (Changed while planning, item 1).

### Where the files live

| Loop | Directory |
|---|---|
| `spec-review` | `~/.saffron/batches/spec-loop/SA-NNNN/spec-review/round-N/` |
| `pr-review` | `~/.saffron/batches/spec-loop/SA-NNNN/pr-review/round-N/` |
| `cell` | `~/.saffron/batches/v0/SA-NNNN/` |

A review round directory holds one `report-N.md` per seat, one `round.json`
with the resolved commit and the diff's start, one merged `findings.json`,
and `jev.ttl`. A `pr-review` review round holds two reports, and both seats
share the review round number and the one findings file.

## The JSON block

`.claude/agents/spec-reviewer.md` and
`.claude/skills/run-saffron-spec-loop/REVIEW-PROMPT.md` each gain one last
report item.

```json
{"findings": [{"severity": "blocker", "criterion": 3, "file": "saffron/ledger.py", "line": 230, "claim": "..."}]}
```

`severity` is `blocker`, `concern` or `note`, the words both reviewers already
use. `criterion` is the spec's criterion number, or `null`. A report with no
findings carries an empty list. The prose report does not change.

## The driver command

```
driver.py jev SA-NNNN --kind spec-review|pr-review|cell [--report <path> ...]
```

- `spec-review` and `pr-review` take the saved reviewer reports. `pr-review`
  takes one per seat.
- The command numbers the review round as one past the last recorded review
  round.
- It records the reviewed commit. That commit is the spec branch head for a spec
  review and the PR head for a code review. The diff Jev sees runs from the
  previous review round's commit to this one.
- `cell` reads `findings.json` from the batch tree and takes no report. The loop
  runs it right after `record`.
- Re-scoring a review round overwrites its `jev.ttl`.

Exit codes follow `saffron/cli.py`. A missing or malformed JSON block exits
`1` and writes no review round directory. A missing key or a failed Jev call
exits `2`.

`SKILL.md` gains three lines, one after the spec review, one after step 2c's
seats and one after `record`. Each line gives the command and says that a
non-zero exit is noted and the loop continues.

## The key and the dependency

`TYPESAFE_API_KEY` is in `~/.secrets`. It is scoped to the one command, the same
way `CLAUDE_CODE_OAUTH_TOKEN` is.

```
env TYPESAFE_API_KEY=(bash -c 'source ~/.secrets; printf %s $TYPESAFE_API_KEY') \
  uv run .claude/skills/run-saffron-spec-loop/driver.py jev SA-NNNN --kind cell
```

`typesafe-sdk` is pinned in the existing `dev` dependency group, not a new
`harness` group (Changed while planning, item 2). `ty` checks every file,
including `.claude/`, so a group `make install` does not sync would fail
the `types` gate. The `dev` group never ships in the `saffron` wheel. The
driver imports it only inside `jev`, so a command that never calls Jev
never runs that import. No cell receives the key.

The request sends the alias `jev-latest` (Changed while planning, item 7), and
`response.model` records the build that answered.

## Testing

No test calls the network. `jev_observe` takes a client object, and tests pass a
fake that returns fixed answers.

| Code | Test | Proves |
|---|---|---|
| T1 | The fake answers every question, and pyoxigraph loads the Turtle | One assertion per answer, each distribution round-trips, the outcome is `cantTell`, the model is recorded, and a SPARQL query checks the shape |
| T2 | The questions built for each loop | Q1's choices are the criteria and `noMatch`, `cell` asks no Q4 or Q5, only `spec-review` asks Q7 to Q9 |
| T3 | Reading the JSON block | The last fenced `json` block wins, and a missing or malformed block exits `1` with no review round directory |
| T4 | Two review rounds, then review round 1 again | Review rounds self-number, the diff spans the recorded commits, and ids survive a re-score |
| T5 | `jev` with no key, and `status` with the SDK blocked | The first exits `2` before any call, and the second runs |
| T6 | dropped (Changed while planning, item 1) | Jev's `.ttl` files sit outside the `shacl` gate's tree, so pyshacl has nothing to run against |

Each test runs once against a mutant it must catch. T1 runs against a writer
that drops the distribution. T4 runs against ids that include a timestamp.

One real call is made by hand, `--kind cell` on `SA-0117`. The response shape in
this document comes from TypeSafe's docs, not from a measurement. The call's
output goes to `docs/evidence/2026-09-21-jev-first-call.md`.

## Changed while planning

1. **Jev terms use their own namespace, `urn:software-factory:jev#`, not
   `factory:`.** `tests/ontology/test_no_dead_terms.py` requires every
   `factory:` term to have a query or shape that reads it. The design
   assumed nothing reads these scores yet, so a `factory:` term would fail
   that test. The `.ttl` files live under `~/.saffron/`, outside the
   `shacl` gate's tree. T6 (pyshacl) is dropped. T1's SPARQL query checks
   the shape instead.
2. **`typesafe-sdk` goes in the `dev` group, not a new `harness` group.**
   `ty` checks every file, including `.claude/`. A group `make install`
   does not sync would fail the `types` gate. The `dev` group never ships
   in the `saffron` wheel.
3. **One Jev call per review round, not one per question group.** TypeSafe's
   parallel-questions cookbook measured one batched call as 12.2x cheaper
   and 10x faster, with no change to each answer.
4. **Q4 is skipped in a review round with no earlier review round.** Every
   finding in review round 1 is new by definition.
5. **Q1 is skipped when the spec has no criteria, and Q9 when it has only
   one.** A choice with one option carries no information.
6. **`--commit` is passed by the delegate.** It is the commit the reviewer
   read. For `cell` it comes from `patch.json`'s `head_sha`.
7. **The request sends `jev-latest`, not a dated name.** `models.list()`
   offered only aliases on 2026-09-21 (`jev-latest`, `jev-preview`), no dated
   build. `response.model`, for example `jev-1.13.0`, records which build
   answered.
8. **`typesafe-sdk` also lands in the cell image.** `.saffron/Dockerfile`
   syncs the `dev` group for the cell too, so item 2's placement installs the
   package there as well. No key reaches a cell, so this is accepted
   knowingly rather than moved to a group of its own.

## Out of scope

- Any reader of the scores. Stopping rules come after the log-only phase.
- Scoring inside `run_task`. That needs an ADR, because it puts a vendor call in
  core.
- Folding `jev.ttl` into the ledger or the record on git refs.

## Open for the next phase

The source note's exit criteria stand, with two additions from its review.

1. Jev's stop call must beat the reviewer's own severity. Without that
   comparison, calibration alone cannot show that Jev adds anything.
2. Hand-labelling needs review rounds run past the stop point. A loop that
   stopped never shows whether one more review round would have found a
   blocker.
