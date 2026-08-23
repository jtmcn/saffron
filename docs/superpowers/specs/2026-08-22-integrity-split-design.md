# Splitting `integrity` — design

Sub-project D of v1 (`DESIGN.md` §9), or the first half of it. Backlog item 1:
the rejected `SA-0004` gate asks one question it can answer from a diff and one
it cannot, and the second one is answerable exactly somewhere else.

> **Citations:** a bare `§` cites `DESIGN.md`, per repo convention. This spec's
> own sections are cited as *part N*.

> **The batch-tree patch is not the patch Appendix K reviewed.** `SA-0004`'s
> export is post-rebuttal — `rebuttal.json` records `head_moved: true` and one
> blocker withdrawn after a fix. Every claim below about what that patch does was
> re-measured against it, running the module against real `git diff` output
> taken with `worktree.DIFF_FLAGS`. Three of Appendix K's statements do not hold
> against it (part 1). None of them changes the conclusion; two sharpen it.

## What was measured, and what it corrects

The rejected gate, run against real git output with this repo's declared
`IntegrityPatterns`:

| Scenario | Result |
|---|---|
| delete one test, nothing in its place | `fail` ✓ |
| delete one test, leave a comment in its place | `pass` ✗ |
| gut a body in place (`assert x == 5` → `pass`) | `pass` — see part 2 |
| consolidate two tests into one `parametrize` | `pass` ✓ |
| delete the whole test file | `fail` ✓ |
| rename `test_b` → `check_b`, body intact, never collected again | `pass` ✗ |
| `\ No newline at end of file`, all four positions git emits it | parses cleanly ✓ |

**Correction 1 — defect A is already fixed.** Appendix K reports that the
no-newline marker was handled "in the one position git does not use", aborting
any task whose diff touches a file without a trailing newline. That was true of
the reviewed patch; it is not true of the exported one. All four shapes git
emits — marker after a `-` line, after a `+` line, after both, and in a
single-line file — parse without error. There is nothing to fix here, and the
backlog line that says a branch exists in the wrong place should be struck.

**Correction 2 — the heuristic is run adjacency, not net line count.** The
rebuttal turn replaced the whole-hunk `+`/`-` comparison with
`_unreplaced_removals`: a maximal run of `-` lines counts only when no `+` run
sits immediately on either side. Two consequences, both measured:

- **The false positive is gone.** A `parametrize` consolidation passes. Appendix
  K's "wrong in both directions on one comparison" no longer describes this code.
  Principle 47's *biased coin* is the wrong indictment of it, and principle 52
  below is the right one: the coin is not biased, the diff simply does not carry
  the answer.
- **The evasion got cheaper.** Appendix K's move is to out-write the deleted
  test with a comment. Under adjacency, *one* `+` line of any kind, anywhere
  against the removal, is enough — `pass`, a comment, a blank-line change git
  folds into the run. The gate does not ask what the added line says, because
  asking is the language knowledge §2.1 forbids.

**Correction 3 — an unrecorded defect, and it blocks this repo's own merges.**
Suppressions are substring-matched against every added line in every file.
Prose therefore fails. Measured on `d1141d0`, the merge of PR #5: `fail`, with
two `added-suppression` failures, both docstrings explaining that a critic's
claim routinely quotes `` `@pytest.mark.skip` `` (`saffron/report/pr_body.py:100`,
`tests/test_report.py:266`). This is also what the "sixteen violations on its own
pull request" were — `integrity.py` and its fixtures quote every token in the
repo's `suppressions` list. Appendix K attributes those to the missing `touches`
exemption, which is true and incomplete: the exemption is what *rescues* a
substring scan that has no other defence, and that is an argument about which
checks the exemption must bind (part 3).

## The shape of the answer

Two questions are wearing one gate.

**"Was a suppression added, or gate config edited?"** is a question about diff
text. It needs no execution, no repo knowledge beyond the tokens `policy.yaml`
declares, and it is right where it is.

**"Was an existing test removed?"** is not a question about a diff at all. It is
a question about two sets, and the diff is a lossy projection of the answer. Every
diff-shaped proxy for it fails in the same direction: adjacency misses a deletion
with any neighbour, net lines miss a deletion under a comment, and neither sees
`test_b` → `check_b`, where nothing is removed, nothing is suppressed, the body
survives intact, and the test is never collected again.

> 52. **When a check keeps needing a better heuristic, the question is in the
>     wrong coordinate system.** Three rewrites of "was a test removed?" against
>     diff text produced three different wrong answers, because the diff does not
>     contain the answer — it contains a shadow of it. The set of collected tests
>     does contain it, exactly, and comparing two sets needs no heuristic at all.

## 1. `integrity` keeps two checks and loses one

Core, diff-only, unchanged in shape. `_runs` and `_unreplaced_removals` are
deleted along with `removed-test`; the parser, the pinned-header validation, the
suppression scan and the `gate_config` check all survive, because review was
explicit that they are correct and measurement agrees.

What is kept is worth naming, since deleting a third of a file invites deleting
more: count-driven hunk consumption with a fixture containing diff-shaped
content; line numbers derived from the `@@` header rather than counted; `error`
distinct from `fail`; the `a/ b/` prefix refusal that backlog item 2's close
installed in `scope`; and suppression detection over added lines only, with the
context-line and removed-line cases both tested and both right.

**The `-diff` gitattribute case, from item 2's close.** A text file with `-diff`
renders as `Binary files a/x and b/x differ` — content hidden, path not. `scope`
is unaffected because it reads paths. `integrity` must treat such a section as
**unreadable**, not as *no change*: a file whose added lines cannot be read is a
file whose suppressions cannot be counted. That is `error`, charged to nobody,
never `pass`.

Two details measured while planning it, both of which change the code. The
`Binary files` line *replaces* the `---`/`+++` headers rather than joining them,
so the path has to be taken from that line or it never arrives — and without a
path the exemption cannot be applied. And the check belongs **after** the
`touches` exemption, not during the parse: a committed binary fixture the spec
declared is not a gate that cannot read its input, and erroring on it would abort
the attempt over a PNG. What remains after the exemption is content hidden in a
file nobody authorized changing, which is the case the rule exists for.

## 2. `census` — the new core role

Names collected at `base_sha`, minus names collected at head. Present at base and
absent at head is a removed test, reported one failure per name.

This answers the question exactly. No false positive on a consolidation, because
`parametrize` keeps the collected names. No evasion by padding, commenting, or
adjacency, because the comparison never looks at the diff. And it catches
rename-out-of-collection, which every diff-shaped version blesses.

**What it does not catch, deliberately.** A test gutted in place — `assert
compute() == 5` rewritten to `pass` — is still collected under the same name, so
`census` sees nothing. That is `revert`'s mechanism, not this one: stash the
source hunks, run the new and changed tests, require them to fail. A test gutted
to `pass` passes against reverted source and `revert` catches it for exactly that
reason. The rejected gate's rebuttal argued this boundary and the lens accepted
it; it is restated here so it does not read as an oversight in a second gate.

### 2.1 It needs no §2.1 exception

Backlog item 1 assumes this half must adopt `revert`'s sanctioned exception —
core invoking the repo's `tests` gate with a subset argument, twice more. It does
not, and the reason is that the runs already happen.

`session.py:560` runs the repo's full declared suite inside the cell at
`base_sha` to build the baseline, and `repair_loop` runs it again at head on
every attempt. Both already execute `tests`. So the collected names do not need
to be fetched — they need to be *reported*, and the host compares two lists it
already holds.

```python
# saffron/gates/contract.py — GateResult
collected: list[str] | None = None
"""Identifiers this gate enumerated, opaque to core. Only `tests` populates it
today. Absent means the runner does not enumerate, which is a `skip` for
`census`, not a failure."""
```

Core executes nothing and invokes nothing. It reads a field of a gate result,
which is squarely inside §2.1's original sentence — *Saffron knows the shape of a
gate result* — rather than the exception to it. The cost is zero additional cell
time and one optional field.

**The names are opaque.** Core never splits them, never parses a node id, never
assumes a separator. `Failure.file` carries the collected name verbatim; a runner
that reports `tests/test_x.py::test_b` and one that reports `pkg.TestFoo` are
both fine, and neither teaches core anything about a language.

### 2.2 Statuses

The two sides are not symmetric, and saying "absent on either side" would collapse
the case that matters into the case that does not:

- **`skip`** — no `collected` on the **base** side. Either the repo does not
  enumerate, or there is no base side yet because this is the baseline call
  itself (part 4). Both are a gate with nothing to compare, which is a `skip`
  (§5.4), not a failure.
- **`error`** — `collected` on the base side and none at head. A suite that
  enumerated before the task and stopped after it is the same class of fact
  `suite_drift` exists for: grounds to distrust the comparison rather than
  report it.
- **`pass` / `fail`** — both sides present, on the set difference.
- **`tool`** is `None`, as `scope_gate` already leaves it. A gate that executes
  nothing cannot obtain a tool identifier by executing one, and §5.4's rule is
  about gates that run tools.

A head `tests` that errored aborts the attempt before `census` is consulted
(`aborted_gates`, `repair_loop`), so a truncated collection can never be read as
a mass deletion. That is §5.4's "partial results are not results" already doing
the work; this spec adds no second mechanism for it.

## 3. The `touches` exemption binds two checks, not three

§5.4 reads *"fail on any deletion of an existing test, any newly added
suppression, and any edit to gate configuration, unless `touches` explicitly
includes it."* The rejected gate omitted the clause entirely and failed its own
pull request sixteen times. Restoring it verbatim across all three checks is the
obvious repair and it is wrong.

**Suppressions and `gate_config`: exempt.** The signal there is *this file
changed at all*. A spec whose `touches` names `pyproject.toml` has authorized the
edit, and the gate has nothing left to say. This is also the only defence a
substring scan has against prose (correction 3): a task quoting a token in a
docstring has that file in `touches` by construction, because `scope` would
otherwise have failed it first.

**Removal: not exempt.** `touches: tests/test_session.py` authorizes *editing*
that file. It does not authorize deleting three unrelated tests inside it to get
to green, and that is the precise act the gate exists for. Exempting removal
would leave `census` silent on almost every real task, since `touches` names a
test file for nearly all of them (all four specs in `.saffron/specs/` do).

**The ceiling this leaves.** A task that legitimately removes a test cannot pass,
and there is no override. The upgrade path is a spec field — `may_remove_tests`,
or a per-name allowance — and it stays unbuilt: no task has needed it, and spec
schema added before the case arrives is schema designed against a guess. It gets
a `ponytail:` comment naming the ceiling and a backlog line, so the day it bites,
the reason it was left is on the record.

## 4. Wiring

`census` goes into the suite rather than beside `suite_drift`, so that it lands
in `gate_results`, in the PR body's gate table, and in the subtraction without a
second mechanism for any of them.

The suite closure gains the prior results as an argument — `[]` for the baseline
call, `baseline` for every head call. `census` returns `skip` when handed an empty
prior, which is what makes the baseline call correct rather than special-cased.

**`repair_loop`'s signature does not change.** An earlier draft said it would.
It does not: `_run_gates` is defined at `session.py:726`, after `baseline` is
bound at 560, so it closes over the baseline directly and
`run_gates: Callable[[], list[GateResult]]` stands as it is. The host-side loop
stays ignorant of which gates the suite contains, which is the property worth
keeping.

Three existing mechanisms then behave correctly with no change, and each was
checked against its code rather than assumed:

- **`suite_drift`** skips gates present only at head (`baseline.py:88`), so a
  head-only `census` is ignored. Its `tool` comparison is guarded by `ran_both`,
  which requires `pass`/`fail` on both sides, so a `skip` at baseline and a
  `pass` at head never trips it.
- **`subtract_baseline`** finds no baseline counterpart for a `census` failure and
  counts it as new, which is correct: a test removed by this task is this task's
  problem by definition.
- **`aborted_gates`** already turns a `census` `error` into `GATE_ERROR`, charged
  to nobody.

## 5. `DESIGN.md`, before any code

New subsections and new rows; nothing renumbered.

- **§5.4, `integrity` paragraph** — two checks, not three, and the removal check's
  departure with principle 52 as the reason. The exemption sentence gains the
  split from part 3.
- **§5.4, gate-role table** — a `census` row, core, blocking.
- **§5.4, a paragraph beside `revert`'s** — what `census` compares, why the diff
  could not answer it, and the `revert` boundary from part 2.
- **§5.4, the contract** — the `collected` field, and that its absence is a `skip`.
- **§2.1, the concern table** — `census` as core, with the note that it needs no
  exception because it reads a gate result rather than invoking a gate. The
  "seam to watch" paragraph gains a sentence: *a core gate that needs data from
  the repo should first ask whether a gate already produces it.*
- **Appendix** — the three corrections in part 1, in the appendix idiom, plus
  principle 52.

## 6. Testing

Every fixture is real `git diff` output taken with `worktree.DIFF_FLAGS`, built
the way `tests/test_scope.py` already builds `_hostile_repo`/`_diff`. Synthetic
diff strings are what let the rejected gate's thirty-one tests agree with its
blind spots (principle 45).

The seven scenarios in part 1 are the regression suite, including the two that
currently pass and must not: *delete a test and leave a comment in its place*,
and *rename `test_b` → `check_b`*. Both are `census` cases; both assert a `fail`
that no version of the diff-reading gate produces, so both are red against
today's code and green after — which is what makes them the tests worth having.

Plus: the four `\ No newline` positions, as characterization tests, so correction
1 cannot silently regress; a `-diff` gitattribute section reported `error` and not
`pass`; `collected` absent → `skip`; present at base and absent at head →
`error`; the `touches` split, one test per side; and `d1141d0`'s own diff passing
`integrity` once the exemption binds suppressions.

Mutation testing is not planned. Principle 45 scopes it to agent-authored work —
*a test written by the author of the code certifies agreement, not correctness* —
and the failure mode it defends against is a suite agreeing with the same blind
spots that produced the code. Fixtures taken from real git output and two tests
that fail before the change are the cheaper form of the same evidence here.

## 7. Success criterion

`census` fails a diff that renames `test_b` to `check_b`, which no version of the
diff-reading gate could see; `integrity` passes `d1141d0`, which the rejected
gate fails; and `saffron/gates/core/integrity.py` is shorter than the file it
replaces.
