---
id: SA-0011
title: Every acceptance criterion is prose, and the PR body renders it as an unticked box
type: feature
priority: 1
depends_on: []
touches:
  - saffron/gates/core/criteria.py
  - saffron/gates/contract.py
  - saffron/intake.py
  - saffron/cli.py
  - saffron/cell/session.py
  - saffron/agents/context.py
  - saffron/agents/prompts/implement.md
  - saffron/report/pr_body.py
  - tests/test_criteria.py
  - tests/test_intake.py
  - tests/test_cli.py
  - tests/test_session.py
  - tests/test_context.py
  - tests/test_report.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - saffron/gates/core/scope.py
  - saffron/gates/core/integrity.py
  - saffron/gates/core/census.py
  - saffron/gates/runner.py
budget_usd: 14
max_attempts: 4
max_turns: 100
risk: elevated
---

## Context

`DESIGN.md` §5.4's founding lesson is `tool`: `{"status":"pass","failures":[]}` is
bit-for-bit identical whether the linter found nothing or the linter was not on
`PATH`, so the contract requires an identifier **obtained by executing the tool**
(Appendix H). A gate that cannot run its tool cannot produce the field.

Acceptance criteria have no `tool`. They are parsed by `intake.py`, injected into
the implementer's and the critic's prompts, and rendered by `pr_body.py:128` as:

```python
lines += [f"- [ ] {criterion}" for criterion in spec.acceptance_criteria]
```

Unticked, always, for every criterion, with no host-side component anywhere that
asks whether one was met. The PR body shows a checklist that nothing can tick,
which reads as evidence and is not.

`agents/artifacts.py` already knows the principle — it rejects a plan naming no
test file with the reason *"acceptance criteria that cannot fail are prose"* — and
enforces it at the coarsest available grain: whether the plan mentions **any** test
file. Never per criterion, and never against what the change actually did.

## Problem

The gap this closes is not that criteria go unchecked. It is that **an unchecked
criterion is indistinguishable from a met one** in the artifact the operator reads
to decide. That is the `tool` defect, one layer up, in the layer that decides
whether a PR is merged.

Three consequences, all live today:

- A task can satisfy every gate, produce a diff that meets no acceptance criterion,
  and reach `READY_FOR_REVIEW` with a PR body that looks identical to one that met
  all of them.
- `SA-0001`'s Q1 — *"the operator rejected on this criterion; did any gate or lens
  assert on it?"* — returns an unbound assertor for every criterion, because the
  vocabulary models criteria as `earl:TestCriterion` and **nothing produces the
  assertions**. The reader exists; the writer does not.
- The flywheel's bucket-1 triage (§8) asks which failures were mechanically
  checkable. A criterion that was never mechanically checked cannot answer.

## The shape

A criterion declares a **witness**: a test node id the host checks, not a claim the
model makes.

**`criteria` reads two gate results; it invokes nothing.** This repo has already
decided this question once, for `census` (`docs/BACKLOG.md`): *"It needed no §2.1
exception. This item assumed core would have to invoke the `tests` gate the way
`revert` does; it does not, because the baseline and head suites already run
`tests`, so the names needed reporting rather than fetching."* The same route is
open here and is strictly better. `census_gate(base, head)` is the shape
(`session.py:702`, over the baseline at `:896`), not `scope_gate`'s single tree.

Both suites already report what is needed. Measured, against this repo's own
`tests` gate on a two-test file with one failing:

```json
{"status": "fail", "collected": ["test_probe.py::test_ok", "test_probe.py::test_bad"],
 "failures": [{"code": "test_probe.py::test_bad", ...}]}
```

So *"did witness W pass on this side?"* is `W ∈ collected` and `W ∉ {f.code}` — two
lists the host is already holding. No subset argument, no second execution of the
suite, no §2.1 exception, and **`criteria` never executes repo code**, so
`CONTEXT.md` §4's definition of a core gate still holds with a seventh member.

The cost is one contract obligation, exactly parallel to the `collected` field
`census` added: a `tests` gate must report node ids in `failures[].code`. Where it
does not, `criteria` reports `skip` — the same degradation `census` already makes
when a runner does not enumerate.

**The direction is the load-bearing part.** A criterion that claims the change
*did* something must have a witness that **did not pass at `base_sha` and passes at
head** — a witness that was already green proves nothing about this change. A
criterion declaring `preserves: true` claims the opposite and is checked the
opposite way. A witness absent from `collected(base)` — because the diff adds it —
is simply not passing at base, which is the ordinary new-criterion shape and
produces no error anywhere.

**What actually stops the cell relaxing a witness**, stated correctly because the
first draft got it wrong: not `policy.protected`, which has no diff-time reader at
all (`artifacts.py` checks the model's own declared `files_to_change` at the plan
checkpoint, and `context.py` prints it into a prompt). It is that `cli.py`'s
`load_spec` parses the **operator's host-side copy** before the cell starts, so the
witnesses the gate checks were never in `/work`; and that `.saffron/**` is outside
this spec's `touches`, so `scope` fails any diff that edits it. The agent's only
lever is the body of the witness test — which is what `revert` exists for, and is
out of scope here.

**The witness node ids must reach the agent.** They are exact strings the
implementer has to name its tests, and today only `spec.body` — the markdown, not
the frontmatter — is substituted into a prompt (`agents/context.py`). A gate that
blocks on a target the agent was never shown burns every attempt for a reason no
repair turn can diagnose.

## The format

A new optional frontmatter key. Absent, nothing changes:

```yaml
acceptance:
  - claim: "a witness that was already green at base_sha fails the gate"
    witness: tests/test_criteria.py::test_a_witness_green_at_base_fails
  - claim: "a spec with no acceptance block parses exactly as it does today"
    witness: tests/test_intake.py::test_extracts_the_acceptance_criteria_as_a_checklist
    preserves: true
```

The second is a real `preserves` case and shows what the flag is for: an existing,
already-green test, named because the criterion is *"do not break this"*. A new
test can never be `preserves`, because it did not pass at base.

**This spec does not use the key, and that is a finding rather than an oversight.**
`Spec` sets `extra="forbid"` (`intake.py:35`), so a spec declaring `acceptance:`
today is refused at intake as malformed — the first spec to declare witnesses
cannot be the one that builds them. The recursion is closed by a fixture instead.
Worth carrying into `DESIGN.md` §3.2: **a spec cannot introduce the frontmatter it
is written in**, and the standing answer is a fixture in the same change.

## Acceptance criteria

- [ ] A spec declaring `acceptance:` parses into structured criteria — `claim`,
      `witness`, optional `preserves` — and a spec declaring only the markdown
      section parses exactly as it does today
- [ ] `criteria` reports `skip` for a spec that declares no witnesses, and every
      spec from `SA-0001` to `SA-0010` still runs unchanged
- [ ] `criteria` reports `skip` when the head `tests` result carries no `collected`
      list, or carries no node ids in `failures[].code` — a runner that does not
      report them is not a repo doing something wrong
- [ ] A witness absent from `collected` at head **fails**: it names nothing the
      suite ran, and a criterion nothing ran is the defect this gate exists for
- [ ] **A witness that passed at `base_sha` and passes at head fails**, unless the
      criterion declares `preserves: true`
- [ ] A criterion declaring `preserves: true` fails unless its witness passed at
      **both** sides
- [ ] A witness absent from `collected(base)` because the diff adds it, and passing
      at head, is the ordinary successful shape — and no `error` is produced
      anywhere, so the baseline suite (§4.4) is unaffected and no task reaches
      `PREFLIGHT_FAILED` because of this gate
- [ ] The gate's `tool` is the one the head `tests` result reported, and is absent
      only when the gate reports `error`
- [ ] The declared witnesses reach the IMPLEMENT prompt verbatim, so the
      implementer can name its tests to match
- [ ] For a spec that declares `acceptance:`, `pr_body` ticks a criterion's box
      only from a `criteria` gate result and an unticked box carries the reason;
      for a spec that does not, the rendering is unchanged
- [ ] A fixture spec carrying the `acceptance:` block above parses and passes
      `criteria` — the recursion the frontmatter cannot close

## Out of scope

The `revert` gate. It is designed (§5.4), unbuilt (`review.py:42`), and answers the
question this gate deliberately cannot: whether a witness *test body* still fails
without the source hunks. `criteria` judges a witness by its name and its outcome
on two sides; it cannot see that a test's assertions were weakened. That is the
narrower claim, and it is stated here so the gate is not read as catching test
theatre in general.

Amending `DESIGN.md` §5.4's role table, §3.2's spec format and `CONTEXT.md` §4's
core-gate enumeration for a seventh core gate. All three are `forbidden` here, as
in every spec `SA-0001` onward: the document being amended is the specification,
so the cell is barred and the operator writes it (PR #44's shape).

Migrating `SA-0001`–`SA-0010` to declared witnesses. They keep the markdown
section and the gate reports `skip`, which is what `skip` is for.

Any change to `ontology/`. The vocabulary already models a criterion as an
`earl:TestCriterion` and a gate result as an `earl:Assertion` over it; this spec
produces the assertions and stores them in the ledger. Emitting them as triples is
`v2.5` and conditional (Appendix O).

Checking prose anywhere other than a spec's criteria — commit messages, PR body
narrative, `DESIGN.md`. That is the same defect class and a much larger question.

## Notes for the agent

**`skip` is not a failure and is the common case.** Ten specs predate this one. A
spec with no `acceptance:` block must leave every existing behaviour unchanged, and
there is a criterion for that. Reaching for a default witness would be worse than
skipping: a criterion checked against an invented test is the defect this spec
exists to close, wearing the fix's clothes.

**Read two results; invoke nothing.** `census_gate(base, head)` is the model to
copy, down to its asymmetry. The temptation is to run the witnesses — that path
needs a §2.1 exception, a second suite execution charged to every task, and it
turns an absent witness at base into a baseline `error`, which `session.py` turns
into `PREFLIGHT_FAILED` and §4.4 turns into a skipped repo for the whole night.
`docs/BACKLOG.md`'s `census` entry is the precedent and the reasoning.

**`error` is not `fail`, and this gate has almost no `error` to produce.** Reading
lists cannot break. A `tests` gate that errored already aborts the attempt before
this gate is reached; a runner that reports no node ids is `skip`, not `error`. If
an implementation finds itself synthesising an `error`, it has probably reached for
the invocation route.

**`tool` comes from the result you read**, not from anything this gate executes.
Do not synthesise one, and do not report `pass` with the field absent — that is the
exact shape Appendix H is about.

**Three soundness edges the direction rule does not close.** State them; do not try
to fix them here. A **flaky** witness that happened to fail at base makes a no-op
criterion read as met — the rule has no repetition or quarantine, unlike baseline
subtraction, which tolerates flakes by cancelling them. A **refactor** spec has no
behaviour change, so every criterion is `preserves` and the rule yields no signal
for that spec type. And a witness that **exists at base and is modified by the
diff** is judged on its name, not its body.

**Size.** `risk: elevated` makes `size` blocking at the 600-line feature ceiling,
and this touches fourteen files. The reading route is what makes it plausible — the
gate itself should be near `census`'s size. If it will not fit, the separable half
is `pr_body` rendering and its tests; the prompt plumbing is not separable, because
a witness the implementer never sees makes the gate unbuildable rather than
unpolished. If dropping `pr_body` is not enough, stop and raise it.
