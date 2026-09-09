# Mutation-Verified Capability Number Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the lens corpus a second, measured number — how many adequacy findings name a
`find`/`replace` edit that, applied at the fixture head, leaves the suite green.

**Architecture:** The adequacy lens gains a required `probe` field carrying an
`intake.Mutant`. During a corpus pass, while each fixture's cell is already up, a new
`harness/probe_check.py` applies each probe through `worktree.source_mutated` and asks that
head's own declared `tests` gate. Three verdicts are computed — `survived`, `killed`,
`unproven` — and the corpus table gains a second line under the declared-recall aggregate.

**Tech Stack:** Python 3.13, `uv`, pytest, pydantic v2, `apple/container` (cells),
`ruff` + `ty` + `ast-grep` via `make check`.

**Spec:** `docs/superpowers/specs/2026-09-09-mutation-verified-capability-design.md`

## Global Constraints

- **`error` is not `fail`.** A `tests` gate that could not start has said nothing. It is
  `unproven`, charged to nobody. Never collapse the two (`DESIGN.md` §5.4).
- **Core invokes declared gates, never tools** (§2.1). Nothing in this work may spell
  `pytest`. The repo's `tests` gate answers, through the JSON gate contract.
- **The host executes nothing model-authored.** Every probe is applied, and every suite run,
  *inside the fixture's cell*. `harness/` reads back a `GateResult` and nothing else.
- **`saffron/cell/runtime.py` is the only module permitted to spell the `apple/container`
  binary** (Appendix G, gated). Nothing in `harness/` may.
- **A new test is not trusted until it has been run against the unfixed code** — or, for one
  guarding a property already true, against a mutant that breaks it. Every task below names
  its mutant.
- **A measured fact beats a reasoned one, and the comment says which.** Do not write a
  factual claim into a comment, docstring or record without running the check first and
  letting the output write the sentence.
- **Commit subjects** are lowercase `type(scope): what changed`, written as a sentence about
  the defect rather than the file.
- **Vocabulary:** the new term is **vacuity probe**. Never "mutant" for one — a mutant is
  declared by a criterion and must be killed; a probe is named by a lens and counts when it
  survives.
- Run `make check` before every commit. Cell-marked tests are excluded by default; the
  `-m cell` suite needs images built by hand and is not part of any task's gate here.

---

## Task 1: The word, before anything uses it

`CONTEXT.md` already says "a mutant a cell chooses is a mutant chosen to be killed." This
work proposes exactly that under an inverted verdict, so the term has to exist before code
starts borrowing the wrong one.

**Files:**
- Modify: `CONTEXT.md` (the `**Mutant**` entry and a new one beside it)

**Interfaces:**
- Consumes: nothing.
- Produces: the term **vacuity probe**, used verbatim in every later task's prose,
  docstrings and commit messages.

- [ ] **Step 1: Confirm the entry is hand-maintained, not generated**

Run:
```bash
grep -n "CLOSED_SETS" -A 10 tests/ontology/test_vocabulary_agrees_with_context.py
grep -rn "utant" ontology/saffron.ttl
```

Expected: `CLOSED_SETS` names Terminal state, Batch stop reason, Severity, Risk tier, Gate
role, Core gates — and not Mutant. The second grep prints nothing. If either expectation
fails, **stop**: the spec's reasoning about this term is wrong and the plan needs revising
rather than working around.

- [ ] **Step 2: Add the entry**

In `CONTEXT.md`, immediately after the existing `**Mutant**` definition, add:

```markdown
**Vacuity probe**: A find-and-replace edit a *lens* names to show that the tests would not
notice the behaviour it describes breaking. Applied by the corpus harness inside a fixture's
cell, never by a gate and never during a task. Its verdict is inverted from a `Mutant`'s: a
vacuity probe that *survives* the suite is the finding confirmed, where a mutant that
survives its witness is the finding.
_Avoid_: "mutant" for one — a mutant is declared by a criterion, is withheld from the
implementer, and must be killed. _Avoid_ "mutation testing" for the corpus number: one probe
per finding, chosen by the lens to make its own case, is not a sample of the mutation space.
```

Then extend the existing `**Mutant**` entry's `_Avoid_` line with: `_Avoid_ "mutant" for the
edit a lens names in a review finding; that is a vacuity probe.`

- [ ] **Step 3: Run the vocabulary suite**

Run: `uv run pytest tests/ontology/ -q`
Expected: PASS, unchanged count. This term is outside the six closed sets, so nothing here
should move — the run is proof the entry did not accidentally land inside a rendered span.

- [ ] **Step 4: Commit**

```bash
git add CONTEXT.md
git commit -m "docs(context): a lens's edit and a criterion's mutant are opposite verdicts"
```

---

## Task 2: `probe_check`, against a fake cell

The verdict logic, with no cell and no container anywhere near it. This is the part that can
be silently wrong, so it is the part that gets tests.

**Files:**
- Create: `harness/probe_check.py`
- Create: `tests/test_probe_check.py`

**Interfaces:**
- Consumes: `intake.Mutant`, `gates.contract.GateResult`,
  `gates.baseline.subtract_baseline`.
- Produces:
  - `Verdict = Literal["survived", "killed", "unproven"]`
  - `@dataclass(frozen=True) ProbeResult(verdict: Verdict, reason: str, failures: tuple[str, ...])`
  - `check_probe(mutant: Mutant, *, baseline: GateResult, mutate: Mutated, run_tests: RunTests) -> ProbeResult`
  - `Mutated = Callable[[Mutant], AbstractContextManager[str | None]]` and
    `RunTests = Callable[[list[str]], GateResult]`, redeclared here rather than imported —
    `witness.py` and `revert.py` each redeclare them for the same reason: this module owes
    them a precedent, not a dependency.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_probe_check.py`:

```python
"""The verdict half of the corpus's second number (the design spec of 2026-09-09).

`probe_check` is where a lens's claim becomes a measurement, so it is where a
wrong answer would be invisible: a probe wrongly read as `survived` inflates
the number the whole exercise exists to produce, and one wrongly read as
`killed` charges a lens for a real vacuity. No cell here — `mutate` and
`run_tests` are the two injected callables, exactly as `witness_gate` takes
them, so every branch is reachable without a container.
"""

from __future__ import annotations

import contextlib

import pytest

from harness import probe_check
from saffron.gates.contract import Failure, GateResult
from saffron.intake import Mutant

PROBE = Mutant(file="saffron/report/pr_body.py", find="safe = neutralize(text)", replace="safe = text")


def _result(status: str, failures: tuple[Failure, ...] = ()) -> GateResult:
    return GateResult(gate="tests", status=status, summary="", failures=list(failures), tool="pytest 8.0.0")


def _fail(name: str) -> Failure:
    return Failure(file="tests/test_report.py", line=1, code=name, message="boom")


def _applies():
    @contextlib.contextmanager
    def mutate(mutant):
        yield None
    return mutate


def _refuses(reason: str):
    @contextlib.contextmanager
    def mutate(mutant):
        yield reason
    return mutate


def test_a_probe_that_leaves_the_suite_as_it_was_survived():
    """The positive result, and the inversion this module exists for: the tests
    did not notice, which is what the finding claimed."""
    got = probe_check.check_probe(
        PROBE,
        baseline=_result("pass"),
        mutate=_applies(),
        run_tests=lambda subset: _result("pass"),
    )
    assert got.verdict == "survived"


def test_a_probe_the_tests_notice_is_killed_and_names_what_failed():
    """A count is not enough. The record has to carry which tests died, because
    telling a real kill from program breakage is a person's call and they
    cannot make it from a number."""
    got = probe_check.check_probe(
        PROBE,
        baseline=_result("pass"),
        mutate=_applies(),
        run_tests=lambda subset: _result("fail", (_fail("test_a"), _fail("test_b"))),
    )
    assert got.verdict == "killed"
    assert got.failures == ("test_a", "test_b")


def test_a_failure_already_at_the_baseline_is_not_a_kill():
    """Baseline subtraction counts. A fixture head carrying one pre-existing
    failure would otherwise read every probe as killed."""
    pre_existing = _result("fail", (_fail("test_flaky"),))
    got = probe_check.check_probe(
        PROBE,
        baseline=pre_existing,
        mutate=_applies(),
        run_tests=lambda subset: pre_existing,
    )
    assert got.verdict == "survived"


def test_one_baseline_failure_cancels_one_head_failure_not_all_of_them():
    """Identities collide legitimately, so the subtraction counts rather than
    comparing sets — the opposite rule to `census`, and they sit beside each
    other in `baseline.py` for exactly this reason."""
    got = probe_check.check_probe(
        PROBE,
        baseline=_result("fail", (_fail("test_a"),)),
        mutate=_applies(),
        run_tests=lambda subset: _result("fail", (_fail("test_a"), _fail("test_a"))),
    )
    assert got.verdict == "killed"
    assert got.failures == ("test_a",)


def test_a_probe_that_did_not_apply_is_unproven_and_says_why():
    """`source_mutated` yields a reason rather than raising for the six cases it
    refuses. None of them is evidence about the lens."""
    got = probe_check.check_probe(
        PROBE,
        baseline=_result("pass"),
        mutate=_refuses("find text not found: 'safe = neutralize(text)'"),
        run_tests=lambda subset: pytest.fail("must not run the suite over an unapplied probe"),
    )
    assert got.verdict == "unproven"
    assert "find text not found" in got.reason


def test_a_tests_gate_that_errored_is_unproven_never_survived():
    """`error` is not `fail`, and here it is not `pass` either. A gate that could
    not start has said nothing — and reading it as `survived` would count a
    broken toolchain as a verified vacuity, which is the number inflating
    itself."""
    got = probe_check.check_probe(
        PROBE,
        baseline=_result("pass"),
        mutate=_applies(),
        run_tests=lambda subset: _result("error"),
    )
    assert got.verdict == "unproven"


def test_a_baseline_that_errored_is_unproven_without_running_the_probe():
    """Nothing to subtract from. Running the probe anyway would compare a real
    result against a non-result."""
    got = probe_check.check_probe(
        PROBE,
        baseline=_result("error"),
        mutate=_applies(),
        run_tests=lambda subset: pytest.fail("must not run without a baseline"),
    )
    assert got.verdict == "unproven"


def test_a_probe_that_moves_the_collection_is_unproven_not_killed():
    """The one mechanical half of the collateral problem. A probe that changes
    what the suite *collects* broke the program at import time, so the
    subtraction is untrustworthy rather than merely non-empty.

    A `fail`, not an `error`, so this reaches the collection check rather than
    stopping at the errored-gate branch above it — otherwise the test would
    pass for the wrong reason and prove nothing about collection at all.
    """
    baseline = _result("pass")
    baseline.collected = ["t.py::a", "t.py::b"]
    mutated = _result("fail", (_fail("t.py::a"),))
    mutated.collected = ["t.py::a"]
    got = probe_check.check_probe(
        PROBE, baseline=baseline, mutate=_applies(), run_tests=lambda subset: mutated
    )
    assert got.verdict == "unproven"
    assert "t.py::b" in got.reason


def test_a_suite_that_collected_more_is_not_drift():
    """One-directional, like `census`: a name that stopped being collected is a
    removal, a name that appeared is not. A probe cannot add a test, but a
    parametrised id can shift, and reading that as breakage would report the
    harness's own noise as a refusal."""
    baseline = _result("pass")
    baseline.collected = ["t.py::a"]
    mutated = _result("pass")
    mutated.collected = ["t.py::a", "t.py::b"]
    got = probe_check.check_probe(
        PROBE, baseline=baseline, mutate=_applies(), run_tests=lambda subset: mutated
    )
    assert got.verdict == "survived"


def test_a_gate_that_enumerates_nothing_is_not_read_as_a_removal():
    """`None` means the runner does not enumerate; `[]` means it enumerated
    nothing, and `GateResult`'s own docstring says those are not the same fact.
    Neither is evidence that a probe removed a test."""
    baseline = _result("pass")
    baseline.collected = ["t.py::a"]
    mutated = _result("pass")
    mutated.collected = None
    got = probe_check.check_probe(
        PROBE, baseline=baseline, mutate=_applies(), run_tests=lambda subset: mutated
    )
    assert got.verdict == "survived"


def test_a_probe_aimed_at_a_test_file_is_refused_before_it_is_applied():
    """The number would otherwise be satisfiable by construction: the adequacy
    prompt offers an edit "to the source or to the test", and deleting an
    assertion survives trivially. Refused before `mutate`, so nothing is
    written for a question that must not be asked."""
    got = probe_check.check_probe(
        Mutant(file="tests/test_report.py", find="assert head == plain", replace=""),
        baseline=_result("pass"),
        mutate=_applies(),
        run_tests=lambda subset: pytest.fail("must not run a probe aimed at a test"),
        test_paths=("tests/",),
    )
    assert got.verdict == "unproven"
    assert "test" in got.reason


def test_the_whole_suite_is_asked_not_a_subset():
    """A probe's question is whether *anything* notices, unlike `witness_gate`,
    which asks one named witness. A subset here would answer a narrower
    question and read as the broader one."""
    asked: list[list[str]] = []
    probe_check.check_probe(
        PROBE,
        baseline=_result("pass"),
        mutate=_applies(),
        run_tests=lambda subset: (asked.append(subset), _result("pass"))[1],
    )
    assert asked == [[]]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_probe_check.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'harness.probe_check'`.

- [ ] **Step 3: Write the implementation**

Create `harness/probe_check.py`:

```python
"""Does a lens's vacuity probe survive the suite? (the design spec of 2026-09-09)

**A green suite is the positive result** — the inversion of `witness_gate`,
which applies a mutant a criterion declared and reads a `fail` as the answer it
wanted. Here the edit comes from a lens's finding, and a suite that stays green
under it is the finding confirmed: the tests do not notice the behaviour
breaking, which is what the finding said.

This module holds the verdict and no I/O. `mutate` and `run_tests` are injected
exactly as `witness_gate` takes them, so every branch below is reachable without
a container — and so the host never holds a path into a cell.

**Three verdicts, and a fourth that is not this module's to give.** A `killed`
probe may be a test doing its job or a probe that broke the program; measured on
`SA-0050`, an edit applied as its claim literally reads leaves a dangling sqlite
binding and takes down two pre-existing tests at runtime. Nothing here can tell
that from a real kill, so `killed` carries its failure identities and a person
annotates the ones that are collateral. A heuristic in this spot would be a
silently-wrong step inside the one number that exists because reading is not
running.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Literal

from saffron.gates.baseline import subtract_baseline
from saffron.gates.contract import GateResult
from saffron.intake import Mutant

# Redeclared rather than imported from `witness`/`revert`, which each redeclare
# it from the other for the same reason: this module owes them a precedent, not
# a dependency.
RunTests = Callable[[list[str]], GateResult]
Mutated = Callable[[Mutant], AbstractContextManager[str | None]]

Verdict = Literal["survived", "killed", "unproven"]

# The whole suite, never a subset. `witness_gate` asks one named witness because
# a criterion names one; a probe asks whether *anything* notices.
WHOLE_SUITE: list[str] = []


def _no_longer_collected(baseline: GateResult, mutated: GateResult) -> list[str]:
    """Node ids the baseline collected and the mutated run did not.

    A **set** difference, and deliberately not `subtract_baseline`'s counting
    rule: a node id is unique in a suite, so a name that stopped collecting is
    a removal, where two failures can share an identity legitimately. `census`
    draws the same distinction on the same field. One-directional for the same
    reason it is there — a name that *appeared* is not breakage.

    `None` is not `[]` (`GateResult.collected`): a runner that does not
    enumerate has said nothing about which tests exist, which is not evidence
    that a probe removed one.

    Not `suite_drift`, which answers a different question — whether a *gate*
    stopped running or changed tool between two suites — and never reads
    `collected`.
    """
    if baseline.collected is None or mutated.collected is None:
        return []
    return sorted(set(baseline.collected) - set(mutated.collected))


@dataclass(frozen=True)
class ProbeResult:
    """One probe, applied and asked."""

    verdict: Verdict
    reason: str
    """Why, in the lens's own terms where there is one. Always populated for
    `unproven`, where the reason is the whole content of the result."""
    failures: tuple[str, ...] = ()
    """The new failure identities behind a `killed`. Itemised rather than
    counted: telling a real kill from program breakage is a person's call and
    they cannot make it from a number."""


def check_probe(
    mutant: Mutant,
    *,
    baseline: GateResult,
    mutate: Mutated,
    run_tests: RunTests,
    test_paths: Sequence[str] = (),
) -> ProbeResult:
    """Apply one probe at the head tree and ask the repo's declared `tests` gate."""
    if test_paths and any(mutant.file.startswith(p) for p in test_paths):
        # The number is otherwise satisfiable by construction: the adequacy
        # prompt offers an edit "to the source or to the test", and deleting an
        # assertion survives trivially. Refused before `mutate`, so nothing is
        # written for a question that must not be asked.
        return ProbeResult("unproven", f"{mutant.file} is a test; a probe must target source")
    if baseline.status == "error":
        return ProbeResult("unproven", "the baseline tests gate errored, so there is nothing to subtract from")

    with mutate(mutant) as refusal:
        if refusal is not None:
            # One of `source_mutated`'s six refusals. None is evidence about
            # the lens, and the tree is untouched.
            return ProbeResult("unproven", refusal)
        mutated = run_tests(WHOLE_SUITE)

    if mutated.status == "error":
        # `error` is not `fail`, and here it is not `pass` either: reading a
        # gate that could not start as `survived` would count a broken
        # toolchain as a verified vacuity.
        return ProbeResult("unproven", f"the tests gate errored under the probe: {mutated.summary}")
    gone = _no_longer_collected(baseline, mutated)
    if gone:
        # Broke the program at import time. The subtraction below is
        # untrustworthy rather than merely non-empty.
        return ProbeResult("unproven", f"the probe stopped these collecting: {', '.join(gone)}")

    new = subtract_baseline([mutated], [baseline])
    if not new:
        return ProbeResult("survived", "no new failure against the baseline")
    return ProbeResult(
        "killed",
        f"{len(new)} new failure(s) against the baseline",
        tuple(n.failure.code for n in new),
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_probe_check.py -q`
Expected: PASS, 13 tests.

- [ ] **Step 5: Prove the two tests guarding an already-true property**

`test_a_tests_gate_that_errored_is_unproven_never_survived` and
`test_a_probe_that_did_not_apply_is_unproven_and_says_why` would pass against several wrong
implementations, so each needs a mutant.

Copy `harness/probe_check.py` to a scratch path first so it can be restored byte-for-byte:

```bash
cp harness/probe_check.py /tmp/probe_check.pristine.py
```

Mutant A — delete the `if mutated.status == "error":` block. Run
`uv run pytest tests/test_probe_check.py -q`.
Expected: FAIL on `test_a_tests_gate_that_errored_is_unproven_never_survived` (it reads
`survived`, since an errored gate reports no failures).

Mutant B — change `if refusal is not None:` to `if refusal is not None and False:`. Run the
same command.
Expected: FAIL on `test_a_probe_that_did_not_apply_is_unproven_and_says_why`, via the
`pytest.fail` in its `run_tests`.

Restore and verify:
```bash
cp /tmp/probe_check.pristine.py harness/probe_check.py
cmp /tmp/probe_check.pristine.py harness/probe_check.py && echo restored
uv run pytest tests/test_probe_check.py -q
```
Expected: `restored`, then PASS.

- [ ] **Step 6: Commit**

```bash
make check
git add harness/probe_check.py tests/test_probe_check.py
git commit -m "feat(harness): a lens's edit surviving the suite is the finding confirmed"
```

---

## Task 3: The adequacy lens emits a probe

The schema and the prompt. `_Reported` splits per lens; `Finding` gains an optional field so
every recorded pass still loads.

**Files:**
- Modify: `saffron/phases/review.py` (the `_Reported` model and wherever `run_lens` validates)
- Modify: `saffron/agents/findings.py` (the `Finding` model)
- Modify: `saffron/agents/prompts/review-adequacy.md`
- Modify: `tests/test_review.py`
- Modify: `tests/test_findings.py` if it exists, otherwise `tests/test_review.py`

**Interfaces:**
- Consumes: `intake.Mutant` (Task 0 of the repo's history, already present).
- Produces: `Finding.probe: Mutant | None = None`, round-tripped by `LensReview.as_dict`.
  Task 4 reads `finding.probe`.

- [ ] **Step 1: Read what is there before changing it**

Run:
```bash
grep -n "class _Reported" -A 20 saffron/phases/review.py
grep -n "_Reported\|model_validate\|LENS_MODELS\|as_dict" saffron/phases/review.py
grep -n "class Finding" -A 15 saffron/agents/findings.py
```

Write down the exact shape of how `run_lens` validates a reported finding and how
`LensReview.as_dict` serialises one. The code below must match it; if `run_lens` validates
through a single model with no lens parameter, the split needs a `dict[str, type[BaseModel]]`
keyed by lens name, and `run_lens` already receives the lens name.

- [ ] **Step 2: Write the failing tests**

Add to `tests/test_review.py`:

```python
def test_an_adequacy_finding_without_a_probe_is_not_the_schema():
    """The field is required where it means something. An adequacy finding that
    names no edit is the hunch about coverage the prompt already refuses — and
    the corpus's second number cannot be computed from it."""
    reported = {"file": "a.py", "line": 1, "severity": "concern", "claim": "c"}
    with pytest.raises(ValidationError):
        review.reported_model("adequacy").model_validate(reported)


def test_a_correctness_finding_carries_no_probe_field_at_all():
    """Only adequacy's defect class is expressible as an edit that keeps the
    suite green. A timezone bug is not, so requiring one there would push the
    lens toward manufacturing it — which its own prompt forbids."""
    reported = {"file": "a.py", "line": 1, "severity": "concern", "claim": "c"}
    assert review.reported_model("correctness").model_validate(reported)
    with pytest.raises(ValidationError):
        review.reported_model("correctness").model_validate(
            reported | {"probe": {"file": "a.py", "find": "x", "replace": "y"}}
        )


def test_a_finding_recorded_before_probes_existed_still_loads():
    """`lens_scoring.reviews_from_json` rebuilds every fixture's recorded
    findings with `Finding(**f)`, and `calibrate_corpus` runs that before every
    paid pass. A required `probe` on `Finding` would make eight shipped
    fixtures unloadable and refuse to start every future pass."""
    old = {"lens": "adequacy", "severity": "note", "file": "a.py", "line": 1, "claim": "c"}
    assert Finding(**old).probe is None


def test_a_probe_survives_the_round_trip_through_as_dict():
    """The host keeps what the lens said, or the corpus scores a pass against a
    field that silently became `None` between the cell and the record."""
    probe = Mutant(file="a.py", find="x", replace="y")
    finding = Finding(lens="adequacy", severity="note", file="a.py", line=1, claim="c", probe=probe)
    written = LensReview(lens="adequacy", findings=[finding]).as_dict()
    assert written["findings"][0]["probe"] == {"file": "a.py", "find": "x", "replace": "y"}
    assert lens_scoring.reviews_from_json(json.dumps([written]))[0].findings[0].probe == probe
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/test_review.py -k "probe" -q`
Expected: FAIL — `AttributeError: module 'saffron.phases.review' has no attribute
'reported_model'`, and `ValidationError` for the unknown `probe` field on `Finding`.

- [ ] **Step 4: Implement the schema change**

In `saffron/agents/findings.py`, add to `Finding`:

```python
    probe: Mutant | None = None
    """The edit this finding says would keep the tests green (a *vacuity
    probe*, `CONTEXT.md`). Required of the adequacy lens on the way in and
    optional here on purpose: every fixture recorded before this field existed
    is rebuilt through `Finding(**f)`, and `calibrate_corpus` runs that before
    every paid pass."""
```

In `saffron/phases/review.py`, replace the single `_Reported` with a per-lens pair and a
lookup:

```python
class _Reported(BaseModel):
    """One finding as a critic emits it.

    No `lens` field: the host stamps that. A lens that names its own lens can
    file under someone else's remit, and the drop rate would still read clean.
    """

    model_config = ConfigDict(extra="forbid")

    file: str
    line: int
    severity: Severity
    claim: str


class _ReportedWithProbe(_Reported):
    """Adequacy's variant. The probe is required because the number it feeds is
    only computable when every finding carries one — an optional field filled
    sometimes and not others makes the measurement a phrasing lottery, which is
    the failure the corpus exists to catch."""

    probe: Mutant


_REPORTED: dict[str, type[_Reported]] = {"adequacy": _ReportedWithProbe}


def reported_model(lens: str) -> type[_Reported]:
    """The schema this lens's findings are validated against.

    Per lens rather than one shape with an optional field: only adequacy's
    prompt asks for an edit and only its defect class is expressible as one.
    """
    return _REPORTED.get(lens, _Reported)
```

Then change `run_lens` to validate through `reported_model(lens)` rather than `_Reported`,
and to carry `probe` onto the `Finding` it stamps.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_review.py -q && uv run pytest tests/test_lens_scoring.py tests/test_corpus.py -q`
Expected: PASS. The second command is the one that matters — it proves the eight shipped
fixtures still load.

- [ ] **Step 6: Add the prompt paragraph**

In `saffron/agents/prompts/review-adequacy.md`, in the "What to emit" list, after the `claim`
bullet, add:

```markdown
- `probe` (object) — the edit from your `claim`, as data rather than prose, with exactly
  three string fields: `file` (repository-relative), `find` (the exact text as it appears in
  the file today), and `replace` (what it becomes; `""` to delete). `find` must appear in
  that file **exactly once** — if the text you want to change appears twice, widen it with
  surrounding lines until it is unique, or the probe is discarded unapplied.

  **`file` must be source, not a test.** Your `claim` may name an edit to either, and often
  the clearest explanation is the test-side one — keep that in the prose. But a probe that
  deletes an assertion proves nothing that can be checked, so the field takes the source-side
  edit: the one that breaks the behaviour while the tests stay green.

  Make it the *whole* edit. If removing the text you named leaves the surrounding code
  broken — an argument with nothing to bind to, a name with no definition — widen `find` to
  cover the collateral change too. A probe that crashes the program is discarded, and your
  finding goes uncounted with it.
```

- [ ] **Step 7: Verify the prompt is still well-formed where a test reads it**

Run: `uv run pytest tests/test_review.py tests/test_context.py -q`
Expected: PASS. Several tests assert the prompt's placeholders (`{vocabulary}`, `{gates}`,
`{diff}`, `{spec}`) survive; this confirms none was disturbed.

- [ ] **Step 8: Commit**

```bash
make check
git add saffron/ tests/
git commit -m "feat(review): the adequacy lens named its edit in prose nobody could apply"
```

---

## Task 4: The corpus driver runs the probes

Wire `probe_check` into the pass, inside the cell that is already up.

**Files:**
- Modify: `harness/corpus.py` (the aggregate and the rendered table)
- Modify: `docs/evidence/scripts/2026-09-08-lens-corpus.py`
- Modify: `tests/test_corpus.py`

**Interfaces:**
- Consumes: `probe_check.check_probe`, `probe_check.ProbeResult`, `Finding.probe`.
- Produces: `corpus.score_probes(reviews_by_fixture, results) -> ProbeScore` with
  `.survived: int`, `.killed: int`, `.unproven: int`, and the second line in
  `render_corpus_table`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_corpus.py`:

```python
def test_the_second_number_counts_probes_not_findings():
    """A finding with no probe is not a probe that failed — it is a finding
    from a lens that was never asked for one. Contract and correctness
    findings are 10 of pass 1's 18 unmatched, and none of them owes an edit."""
    results = {
        "SA-0063": [probe_check.ProbeResult("survived", ""), probe_check.ProbeResult("killed", "", ("t",))],
        "SA-0045": [probe_check.ProbeResult("unproven", "find text not found")],
    }
    score = corpus.score_probes(results)
    assert (score.survived, score.killed, score.unproven) == (1, 1, 1)


def test_the_rendered_table_says_what_the_second_number_is_not():
    """A capability number beside a recall number will be read as comparable
    unless the table says otherwise, and it is not: it covers one lens."""
    results = {"SA-0063": [probe_check.ProbeResult("survived", "")]}
    rendered = corpus.render_probe_summary(corpus.score_probes(results))
    assert "1 verified" in rendered
    assert "adequacy" in rendered


def test_an_unproven_probe_is_in_no_denominator():
    """The same rule as a dropped run one level out. A probe that never applied
    says nothing about the lens, so counting it against the lens would report
    the harness's own refusals as a capability score."""
    results = {"SA-0045": [probe_check.ProbeResult("unproven", "not tracked at HEAD")]}
    rendered = corpus.render_probe_summary(corpus.score_probes(results))
    assert "0 of 0" in rendered
    assert "1 unproven" in rendered
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_corpus.py -k "probe or second_number" -q`
Expected: FAIL — `AttributeError: module 'harness.corpus' has no attribute 'score_probes'`.

- [ ] **Step 3: Implement the aggregate and the rendering**

In `harness/corpus.py`:

```python
@dataclass(frozen=True)
class ProbeScore:
    """The corpus's second number: how many vacuity probes survived their suite."""

    survived: int
    killed: int
    unproven: int

    @property
    def asked(self) -> int:
        """Probes that produced an answer. Never the number filed — an
        `unproven` probe says nothing about the lens, so it is in no
        denominator, exactly as a dropped run is in no n."""
        return self.survived + self.killed


def score_probes(results: dict[str, list[ProbeResult]]) -> ProbeScore:
    flat = [r for rs in results.values() for r in rs]
    return ProbeScore(
        survived=sum(r.verdict == "survived" for r in flat),
        killed=sum(r.verdict == "killed" for r in flat),
        unproven=sum(r.verdict == "unproven" for r in flat),
    )


def render_probe_summary(score: ProbeScore) -> str:
    """The second line, and what it is not.

    Rendered under the declared-recall aggregate, never beside it: the two are
    not comparable. Recall is over every lens's declared defects; this is one
    lens's vacuity capability, and it is a lower bound — a `killed` probe may
    be a test doing its job or a probe that broke the program, and only a
    person reading the itemised failures can tell.
    """
    return (
        f"**{score.survived} verified vacuities** of {score.asked} probe(s) asked "
        f"({score.unproven} unproven, in no denominator). Adequacy lens only, and a "
        f"lower bound: a killed probe may have broken the program rather than been "
        f"noticed, which is adjudicated per probe and not computed."
    )
```

Then append `render_probe_summary(...)` to `render_corpus_table`'s output, after the
per-fixture rows and before the dropped-fixture note.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_corpus.py -q`
Expected: PASS.

- [ ] **Step 5: Wire the driver, and prove the wiring without a cell**

In `docs/evidence/scripts/2026-09-08-lens-corpus.py`, inside the per-fixture `try:` block
after `run_review` returns and **before** `cell_down`, add:

```python
                probes = [
                    f.probe
                    for review in reviews
                    for f in review.findings
                    if f.probe is not None
                ]
                baseline = run_tests_in_cell(container, [])
                probe_results[fixture.spec_id] = [
                    probe_check.check_probe(
                        probe,
                        baseline=baseline,
                        mutate=lambda m: worktree.source_mutated(container, m),
                        run_tests=lambda subset: run_tests_in_cell(container, subset),
                        test_paths=("tests/",),
                    )
                    for probe in probes
                ]
```

where `run_tests_in_cell` invokes the repo's declared `tests` gate through
`gates.runner.run_gate` with a `CellExecutor(container)` — **never** by spelling `pytest`.
Read `saffron/gates/runner.py`'s `run_gate` signature and the driver's existing `gates_dir`
handling to get the cell-side path right.

Add `--skip-probes` for a scoring-only re-run, defaulting to off.

- [ ] **Step 6: Prove the driver path with the cell mocked**

Add to `tests/test_corpus.py` a test that imports the driver by path (the existing tests
already do this for the dated scripts — copy that idiom rather than inventing one),
monkeypatches `cell_up`, `cell_down`, `run_review` and `run_gate`, and asserts that a
fixture whose adequacy finding carries a probe produces one `ProbeResult`, and that
`--skip-probes` produces none and calls `run_gate` zero times.

Run: `uv run pytest tests/test_corpus.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
make check
git add harness/corpus.py docs/evidence/scripts/2026-09-08-lens-corpus.py tests/test_corpus.py
git commit -m "feat(harness): a pass measured recall and left the cell's own answer unasked"
```

---

## Task 5: Land the spike record, then measure the added cost

The spec argues from four mutations whose record lives in a scratch session ledger, and two
of them have been reproduced by nobody. `docs/BACKLOG.md` item 91 is this task.

**Files:**
- Create: `docs/evidence/2026-09-09-adequacy-probe-spike.md`
- Modify: `docs/BACKLOG.md` (close item 91)
- Modify: `docs/superpowers/specs/2026-09-09-mutation-verified-capability-design.md` (cite the
  record instead of saying it is missing)

- [ ] **Step 1: Reproduce the two nobody has run**

Both are at fixture head `f9f007c4` (SA-0045). Their claims are in
`~/.saffron/lens-scoring/corpus-calibration/SA-0045/run-1.json`, at `ledger.py:364` and
`ledger.py:43`.

```bash
git worktree add --detach /tmp/spike-f9f007c4 f9f007c4
```

Read each claim, apply the edit it names by hand in `/tmp/spike-f9f007c4`, then:
```bash
cd /tmp/spike-f9f007c4 && uv run pytest -q
```
Record the exact figure. Restore the file between the two, and confirm with `git -C
/tmp/spike-f9f007c4 status --porcelain` that only the intended file is dirty each time.

Expected per the ledger: 1250 passed, both green. **If either differs, record what actually
happened** — the spec's table is then wrong and the finding is that, not the number you
hoped for.

Clean up: `git worktree remove --force /tmp/spike-f9f007c4`.

- [ ] **Step 2: Write the record**

Create `docs/evidence/2026-09-09-adequacy-probe-spike.md` carrying, per mutation: the
fixture, the head SHA, the recorded claim verbatim, the exact edit applied, the command run,
the exact suite output line, and who ran it and when. Follow the shape of an existing file
under `docs/evidence/`.

State plainly which two were reproduced during review on 2026-09-09 and which two were
reproduced in this task, and that the original spike's own runs are not independently
recorded.

- [ ] **Step 3: Close the backlog item and update the spec**

In `docs/BACKLOG.md`, mark item 91 done with a one-line pointer to the new file. In the spec,
replace the sentence saying the record is a session ledger with a citation of the new file.

- [x] **Step 4: Measure what the probes cost a pass** — run 2026-09-09 by the operator over
      `SA-0045`: 499.8s, $1.58, two probes, 14.0s each, baseline ~15.6s, probe phase 9% of
      the pass. Figures in the spec's "Caching: no"; raw log at
      `~/.saffron/lens-scoring/step4/run.log`.

Run one fixture end to end with a real cell — this needs `CLAUDE_CODE_OAUTH_TOKEN` scoped to
the invocation and `SAFFRON_ALLOW_HOST_PROCESS=rapportd`, per `CLAUDE.md`. **Do not run this
while a batch is live.** Record: wall-clock for the baseline `tests` run, wall-clock per
probe, and the count of probes filed.

Add the measured figures to the spec's "Caching: no" section, replacing the estimate, and say
they were measured on one fixture rather than eight.

- [ ] **Step 5: Commit**

```bash
git add docs/
git commit -m "docs(evidence): four mutations argued a design from a scratch directory"
```

---

## Task 6: The pass-2 readiness gate

Everything the spec says must land **before** pass 2 and never between passes. This task is
the check that it did.

**Files:**
- Modify: `tests/test_corpus.py`

- [ ] **Step 1: Write the failing test**

```python
def test_every_shipped_fixture_is_ready_for_a_probe_pass():
    """The spec's own precondition, as a test rather than a sentence.

    Every change that moves the baseline — the schema field, the prompt
    paragraph, the `Defect` locations — lands before pass 2 or not at all.
    This asserts the state a pass-2 run requires, so a half-landed change
    fails here rather than producing a number nobody can compare.
    """
    assert review.reported_model("adequacy") is not review.reported_model("correctness")
    prompt = REPO / "saffron" / "agents" / "prompts" / "review-adequacy.md"
    assert "`probe` (object)" in prompt.read_text()
    for fixture in corpus.load_corpus(FIXTURES):
        for defect in fixture.defects:
            assert defect.locations, f"{fixture.spec_id}/{defect.id} declares no location"
```

- [ ] **Step 2: Run it**

Run: `uv run pytest tests/test_corpus.py::test_every_shipped_fixture_is_ready_for_a_probe_pass -q`
Expected: PASS if Tasks 1-4 landed. If it fails, the failure names which half is missing.

- [ ] **Step 3: Prove it fires**

Temporarily delete the `probe` bullet from `review-adequacy.md`, re-run, confirm FAIL,
restore, confirm PASS and `git diff` empty for that file.

- [ ] **Step 4: Commit**

```bash
make check
git add tests/test_corpus.py
git commit -m "test(corpus): a half-landed schema change would produce an incomparable pass"
```

---

## Self-review notes

**Spec coverage.** Every section of the spec maps to a task: the schema change and prompt →
Task 3; the cell-side verification and the three verdicts → Task 2 and Task 4; the mutant
target constraint → Task 2 Step 1's `test_a_probe_aimed_at_a_test_file_is_refused` and Task 3
Step 6's prompt text; the vocabulary → Task 1; the spike record → Task 5; caching → resolved
in the spec, measured in Task 5 Step 4; "what this number does not measure" → Task 4's
`render_probe_summary` prose and its test.

**Not covered, deliberately.** The spec's `collateral` annotation has no task, because it is
a person's note on a record rather than code. Task 4's rendering carries the itemised
failures that make it possible; nothing automates it.

**Known soft spot.** Task 4 Steps 5 and 6 are the least specified in this plan, because the
driver's cell-side gate invocation depends on details of `run_gate` and the driver's
`gates_dir` handling that must be read rather than assumed. Task 4 Step 5 says so and names
what to read. An implementer who finds the shape different from the sketch should follow the
code, not the plan, and say so in their report.

**Two signatures every code block here was checked against**, because they are copied
verbatim: `Failure(file: str, line: int | None, code: str, message: str = "")` and
`GateResult(gate, status, tool, collected, failures, summary, duration_ms)`. Task 3's
`_Reported` sketch was **not** checked against `review.py` — Step 1 exists to read it first,
and the sketch is a shape to match, not text to paste.

**One correction already made to this plan.** An earlier draft used
`gates.baseline.suite_drift` for the collection check. It does not read `collected` at all —
it compares one gate's `tool` against another's and catches a gate that stopped running
across a suite of gates. The check here is a set difference on `collected`, which is what
`census` does, and Task 2's test for it uses a `fail` rather than an `error` so it reaches
that branch instead of stopping at the errored-gate one above.
