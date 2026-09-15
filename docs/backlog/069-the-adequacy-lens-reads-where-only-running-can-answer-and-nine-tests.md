---
id: 69
title: The adequacy lens reads where only running can answer, and nine tests got through
status: partial
tier: 1
specs: [SA-0056, SA-0057, SA-0058]
prs: [135, 136, 139]
commits: []
cites: [§5.4]
related: [65, 71]
---

## Problem

**Tier 1.** Measured across one session, 2026-09-05: the batch orchestration
stack and the two pull requests after it.

**Nine tests shipped naming a behaviour they did not guard.** Each passed the
gates, passed three review lenses including the one built for this question,
and passed a human read. Every one was found by running a mutation:

| Where | The mutant that survived |
|---|---|
| `SA-0045`, `SA-0046` | reflow one `SCHEMA` line — both migration guards assert what `replace` removed |
| `SA-0048` | `exc.code not in (401, 403)` -> `not in (999,)`; 89 tests green |
| `SA-0050` | delete the breaker reset; suite green |
| `SA-0054` | `parent_branch=None`; 76/76 green — every stacked child would target `main` |
| `SA-0054` | `print(f"batch: {stop}")` -> `pass`; 76/76 green |
| item 65 | delete `sh:in`; every case decided by `sh:class` instead |
| `SA-0055` | `pinned=derived` invisible to an assertion matching only `ast.Constant` |
| `SA-0055` | delete the `readiness.ok` guard; the narrowing assert raises and exit 2 still holds |

Two of them were written by review agents, and one by the operator's own
session while fixing the others.

**This is not a diligence problem, and "review harder" cannot fix it.** A
vacuous test and a sound one are textually identical: nobody writes a test
intending it not to guard. Vacuity is not a property of the test's text — it is
a property of how the *pair* responds to perturbation, and reading examines one
object while the defect lives in the relation between two. Every row above
required simulating an execution: that `str.replace` removes all occurrences,
that a stub two files away discards `**kwargs`, that no test in 1260 captures
stdout, which SHACL constraint fires first.

`saffron/agents/prompts/review-adequacy.md` states the compromise in its own
words — *"You cannot mutate a line and watch a test fail, which is the ordinary
way a person would answer this question."* The lens was built knowing it was
substituting reading for running. This session is the evidence that the
substitution does not hold: on `SA-0055` the adequacy lens returned **0
findings** while two of seven witnesses were weak.

**This contradicts a standing decision, and the decision was reasonable.**
`docs/evidence/2026-08-25-mutation-testing-vs-a-lens.md` recommended the
prompted lens over a tool, and its arguments still hold about *tools*:
`cosmic-ray` returned 11 survivors of which 10 were one annotation mutated ten
ways, `mutmut` cannot scope below a function and cannot run over a suite that
gates its own tree. But that record's lens evidence was n=5, sonnet, one repo,
and — its own words — "a prompt written after the defect was known". It should
be read alongside this item rather than as settled.

## Done looks like

a mutation check that is *spec-guided rather than
syntactic*, which is the thing the review agents actually did and the thing
neither tool does. Saffron already holds the targets as structured data: each
`acceptance:` entry is a claim plus the witness that guards it. For each
witness, break the property the claim names and require **that named witness**
to fail — a stronger assertion than any tool's "something failed". Cost is one
scoped test run per witness, not a suite run per syntactic mutant, which is
what put mutation testing out of the window in the first place.

Note this is the granularity `revert` (§5.4) is missing rather than a
replacement for it: that gate stashes the whole patch and asks whether the new
tests test *anything*. This asks whether they test *each thing*, which is where
all nine of the above live.

**Two constraints on the design, both learned the hard way here.**

*The mutant must be minimal.* Deleting `sh:class` and `sh:in` together proved
one of them was load-bearing, not which, and shipped a vacuous test anyway. One
claim, one mutant.

*It must not become the only reader.* Everything else the review round found —
an unmeasured request shape on the token probe, a write lock held after a
designed raise, a batch row left open on Ctrl-C, three docstrings claiming more
than their code — was found by reading, and no mutation would have surfaced any
of it. The two answer different questions. Only one of them has a mechanical
answer, and it is currently being guessed at.

## Record

**Partly built, not done.** `SA-0056` (PR #135), `SA-0057` (#136) and `SA-0058`
(#139) merged 2026-09-06 and built the whole mechanism: a `mutant` beside a
claim, an applier, the `witness` gate, and the wiring. **It runs on nothing** —
`witness_gate` mutates a host path and a cell's worktree has none, so
`run_suite`'s `tree` parameter is one no production caller can supply. Item
**71** is that seam and `SA-0059` is its fix; this item is not done until a
`witness` result appears on a real attempt.

Two things the chain produced that are worth having anyway: `mutation.py`'s
applier, whose whole-file digest refuses a restore into a tree that moved, and
`run_witness`'s pre-flight probe, which tells "this repo's `tests` gate cannot
be filtered" apart from "the mutant killed its witness" and was not asked for.

**Its table is now a scored corpus, 2026-09-09, and that closes nothing here.**
`docs/evidence/2026-09-09-lens-corpus-baseline.md` grades adequacy at **2 of the
10 declared defects it owns**, and separately verifies **8 vacuity probes** whose
named edit left the fixture's suite green — the first numbers this item's
question has ever had. Both are measurements of the gap. The mechanism is still
item **71**'s seam: a `witness` result on a real attempt is what closes this.
