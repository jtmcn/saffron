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
  # Two `SimpleNamespace` stand-ins for `Spec` live here and drift silently
  # whenever `Spec` gains a field; `pr_body` reading `acceptance` is what breaks
  # them. Declared, or `scope` fails the only diff that can fix them (item 21).
  - tests/test_package.py
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
model makes. What a ticked box then means, exactly: *a test by this name ran at
head and passed, and if it existed at base it was not green there*. It does not
mean the criterion was met — the witness's body is out of reach here (`revert`,
below, and the fourth soundness edge). That is a narrower claim than "criteria are
checked", and it is still the whole distance from today's box, which means nothing
at all.

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

**How core knows the field carries node ids, without parsing one.** It cannot look
for a separator: `census` is categorical that a collected name is opaque — *"never
split, never parsed, never assumed to contain a path or a separator"* — and a gate
that recognises `::` has learned a language. The whole test is set membership:
**a side is readable iff its `failures` list is empty, or some `failures[].code`
appears in that side's `collected`.** A code in the enumeration is a node id
because the enumeration says so; nothing else is inspected. Failures present and
disjoint from `collected` means the runner keys failures on something else, and
that side is `skip`.

This is not hypothetical, which is why it is a stated rule and not left to the
implementer. Measured against this repo's own `tests` gate: node ids reach
`failures[].code` only through a fallback (`.saffron/gates/tests.py:89`) that runs
when a regex over the whole output matched nothing — and one printed line of the
shape `path:N: word: message` inside a failing test satisfies that regex.

```
def test_tool_output():
    print("saffron/gates/runner.py:147: error: gate reported no tool")
    assert False
→ failures[0].code == "error"
```

Every node id vanishes from the field for that whole run. Without the membership
guard the naive rule reads *W was collected and `W ∉ {"error"}`* and reports
**`pass` for a witness that failed**. Worse where the printing test is a
pre-existing failure: the baseline subtracts it, `tests` blocks nothing, and the
wrong `pass` is the only thing the operator sees. A ticked box over a red test is
this spec's own defect, reintroduced by the gate that closes it.

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

**The unticked box says which kind of unticked it is.** The gate is opt-in and ten
specs predate it, so on the day this ships `criteria` reports `skip` for nearly
every task. If `skip` renders the checklist exactly as today, the Problem section's
defect is closed for opted-in specs and left standing everywhere else — the
operator still cannot tell an unchecked criterion from a met one. Labelling the
skip case is a line in `_criteria` (`pr_body.py:124`), needs no gate, and is the
half of this spec that pays off before any spec declares a witness.

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

**One list or the other, never both.** `intake` already parses the markdown
`## Acceptance criteria` section into `spec.acceptance_criteria`, so a spec
carrying that section *and* `acceptance:` holds two lists of criteria with nothing
keeping them in sync, and `pr_body` has no way to say which one it is ticking.
Intake raises `SpecError` when both are present: where `acceptance:` is declared it
**is** the acceptance criteria, `claim` is the prose the PR body renders, and the
markdown section is omitted. (The alternative — hanging the witness off the
existing checklist line, needing no new frontmatter key at all — was rejected
because it puts an exact node id inside a regex-parsed prose line, where a typo is
a silent mis-parse instead of a validation error.)

**This spec does not use the key**, and §3.2 now says why: a spec cannot introduce
the frontmatter it is written in, because `Spec` sets `extra="forbid"`
(`intake.py:35`) and a spec declaring `acceptance:` today is refused at intake as
malformed. The standing answer §3.2 gives is a fixture in the same change, asserted
by one acceptance criterion — which is the last criterion below.

## Acceptance criteria

- [ ] A spec declaring `acceptance:` parses into structured criteria — `claim`,
      `witness`, optional `preserves` — and a spec declaring only the markdown
      section parses exactly as it does today
- [ ] `criteria` reports `skip` for a spec that declares no witnesses, and every
      spec from `SA-0001` to `SA-0010` still parses and gates unchanged
- [ ] `criteria` reports `skip` when either side carries no `collected` list, or
      carries failures whose `code`s are **all** absent from that side's
      `collected` — the membership guard, reached without inspecting a name; a
      runner that keys failures on something else is not a repo doing something
      wrong
- [ ] A witness that is collected at head and failed at head is never reported
      `pass` because the runner keyed that failure on something other than a node
      id — the measured `path:N: word: message` case, with the failing test
      pre-existing so the baseline subtracts it and `tests` blocks nothing
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
- [ ] The gate reports no `tool` in any status, as every host-side core gate does,
      and none of its results reach `run_gate`'s requirement (`runner.py:147`)
- [ ] The declared witnesses reach the IMPLEMENT prompt verbatim, so the
      implementer can name its tests to match
- [ ] A spec declaring both `acceptance:` and a markdown `## Acceptance criteria`
      section is refused at intake as malformed — one list, never two
- [ ] For a spec that declares `acceptance:`, `pr_body` ticks a criterion's box
      only from a `criteria` gate result and an unticked box carries the reason
- [ ] Where `criteria` reports `skip`, `pr_body` renders the checklist marked as
      not mechanically checked — the ten specs predating this key included. An
      unticked box meaning *nobody looked* must not render identically to one
      meaning *the witness failed*
- [ ] A fixture spec carrying the `acceptance:` block above parses and passes
      `criteria` — the recursion the frontmatter cannot close. The fixture is a
      string literal in the test module, not a file: `touches` lists individual
      test paths, so a new `tests/fixtures/*.md` falls outside it and `scope`
      fails the diff that adds it

## Out of scope

The `revert` gate. It is designed (§5.4), unbuilt (`review.py:42`), and answers the
question this gate deliberately cannot: whether a witness *test body* still fails
without the source hunks. `criteria` judges a witness by its name and its outcome
on two sides; it cannot see that a test's assertions were weakened. `criteria` is
the narrower claim, and it is stated here so the gate is not read as catching test
theatre in general. `revert` is also what closes the vacuous-witness edge below: an
`assert True` witness passes without the source hunks, which is precisely what
`revert` fails and `criteria` cannot see.

Amending `DESIGN.md` §5.4's role table and `CONTEXT.md` §4's core-gate enumeration
for a seventh core gate. Both are `forbidden` here, as in every spec `SA-0001`
onward: the document being amended is the specification, so the cell is barred and
the operator writes it (PR #44's shape). §3.2 is already amended — it carries the
frontmatter-recursion rule this spec found.

Migrating `SA-0001`–`SA-0010` to declared witnesses. They keep the markdown
section and the gate reports `skip`, which is what `skip` is for — their PR bodies
gain the not-mechanically-checked label, which is the whole benefit they get here.

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

**`criteria` reports no `tool`, exactly like `census`.** An earlier draft said to
copy the head `tests` result's identifier; that is wrong twice. It names a repo
role core is blind to — `census` unions `collected` over *any* gate reporting it
precisely so core never has to ask which gate is "the tests one" (§2.1) — and it
stamps one execution's identifier onto a second result that executed nothing.
Appendix H's concern does not arise: a host-side gate is constructed in `_suite`,
so a `criteria` result that never ran does not exist to be misread, which is why
`scope`, `integrity`, `size` and `census` all carry no `tool` and `run_gate`'s
requirement never applies to them. What Appendix H does demand here is the
membership guard: never report `pass` on the strength of a field you could not
read.

**Four soundness edges the direction rule does not close.** State them; do not try
to fix them here. The largest is the **vacuous** witness: a new test is absent from
`collected(base)`, so "did not pass at base" is free, and `def test_w(): assert
True` satisfies every criterion this gate can express. The direction rule only
bites where the agent points at a test that already existed and was already green —
a real evasion, but the narrower one. `revert` closes the vacuous case; nothing
here does. A **flaky** witness that happened to fail at base makes a no-op
criterion read as met — the rule has no repetition or quarantine, unlike baseline
subtraction, which tolerates flakes by cancelling them. A **refactor** spec has no
behaviour change, so every criterion is `preserves` and the rule yields no signal
for that spec type. And a witness that **exists at base and is modified by the
diff** is judged on its name, not its body.

**Size.** `risk: elevated` makes `size` blocking at the 600-line feature ceiling,
and this touches fourteen files. The reading route is what makes it plausible — the
gate itself should be near `census`'s size. `pr_body` is no longer the separable
half: the skip labelling pays off on every task from day one, while the gate pays
off only on a spec that declares a witness. Nor is the prompt plumbing separable —
a witness the implementer never sees makes the gate unbuildable rather than
unpolished. The separable half is **`preserves`**: a `preserves` witness that
breaks is already a new failure from the `tests` gate, so the flag carries no
independent signal and exists only to exempt its criterion from the direction rule.
Dropping it costs its two criteria and nothing else. If that is not enough, stop
and raise it.
