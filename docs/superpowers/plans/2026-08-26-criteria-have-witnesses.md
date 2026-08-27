# SA-0011 — Criteria Have Witnesses: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every acceptance criterion a host-checked witness, so a ticked box in the PR body means a named test ran and turned green — and an unticked one says which kind of unticked it is.

**Architecture:** A new optional `acceptance:` frontmatter key carries `claim` / `witness` / `preserves` per criterion. A seventh host-side core gate, `criteria`, reads the `collected` and `failures[].code` lists that the baseline and head suites already reported — it invokes nothing, exactly as `census` does — and decides each witness by name and outcome on two sides. `pr_body` ticks a box only from that gate result, and labels the checklist *not mechanically checked* wherever the gate skipped.

**Tech Stack:** Python 3.12+, pydantic v2, pytest, `uv`, ruff. No new dependencies (`uv.lock` is in `policy.yaml`'s `protected` list).

**Spec:** `.saffron/specs/SA-0011-criteria-have-witnesses.md` — read it before Task 1 and keep it open. This plan argues from it and cites it; where the two disagree, the spec wins.

## Global Constraints

- **`touches`** — only these paths may change. `scope` fails any diff that leaves them:
  `saffron/gates/core/criteria.py`, `saffron/gates/contract.py`, `saffron/intake.py`,
  `saffron/cli.py`, `saffron/cell/session.py`, `saffron/agents/context.py`,
  `saffron/agents/prompts/implement.md`, `saffron/report/pr_body.py`,
  `tests/test_criteria.py`, `tests/test_intake.py`, `tests/test_cli.py`,
  `tests/test_session.py`, `tests/test_context.py`, `tests/test_report.py`.
- **`forbidden`** — never edit: `DESIGN.md`, `CONTEXT.md`, `.saffron/**`, `ontology/**`,
  `saffron/gates/core/scope.py`, `saffron/gates/core/integrity.py`,
  `saffron/gates/core/census.py`, `saffron/gates/runner.py`.
- **No new files outside `touches`.** In particular **no `tests/fixtures/*.md`** — `touches`
  lists individual test paths, so a new fixture file falls outside it and `scope` fails the
  diff that adds it. The fixture spec in Task 2 is a **string literal in the test module**.
- **`risk: elevated`** makes `size` blocking at the **600-line feature ceiling**. Fourteen
  files is a lot of surface for that budget. The reading route (no invocation) is what makes
  it plausible; the gate itself should land near `census`'s ~92 lines. If the diff approaches
  the ceiling, the separable half is **`preserves`** (Task 2 Step 7 and Task 5 Step 5) —
  dropping it costs its two acceptance criteria and nothing else. Stop and raise it before
  cutting anything else.
- **Ceilings:** `budget_usd: 14`, `max_attempts: 4`, `max_turns: 100`.
- **`error` ≠ `fail`.** `fail` means the repo's code is wrong; `error` means the gate broke
  and aborts the attempt charged to nobody. `criteria` produces **no `error` in any status**.
  If you find yourself synthesising one, you have reached for the invocation route.
- **`criteria` reports no `tool`, ever**, in any status — as `scope`, `integrity`, `size` and
  `census` all do. It is constructed in `_suite`, never declared in `.saffron/gates`, so it
  never reaches `run_gate`'s `tool` requirement (`saffron/gates/runner.py:147`).
- **Names are opaque.** Never split a witness or a collected name, never parse it, never
  assume it contains a path or a separator. A gate that recognises `::` has learned a
  language (§2.1, `census`'s module docstring).
- **Vocabulary is enforced** (`CONTEXT.md`, including its `_Avoid_` lists): "cell" not
  "sandbox", "gate result" not "gate run", "batch" ≠ "run". Statuses lowercase in backticks
  (`` `skip` ``), states in backticked caps (`` `READY_FOR_REVIEW` ``), phases in bare caps
  (IMPLEMENT).
- **Comment style** (user's global CLAUDE.md): terse inline comments, 1–2 lines, only the
  non-obvious *why*. Rationale goes in the commit message, not stacked above a line.
- **Commit subjects** are lowercase `type(scope): what changed`, written as a sentence about
  the defect rather than the file. See `git log`.
- **Verify before claiming.** Run the command and read the output before saying a step
  passed. `make check` is the real gate — CI in this repo has never passed.

**Run tests with:** `uv run pytest <path> -v` (cell-marked tests are excluded by default via
`pyproject` addopts, which is what you want here — nothing in this plan needs a container).

---

### Task 1: `Criterion`, the `acceptance:` key, and the one-list-or-the-other refusal

Intake learns the new frontmatter shape. Nothing reads it yet — that is Task 2 onward — but
a spec declaring `acceptance:` today is refused at intake as malformed (`Spec` sets
`extra="forbid"`, `saffron/intake.py:35`), so this has to land first or nothing downstream
is testable.

**Files:**
- Modify: `saffron/intake.py` (add `Criterion`, add `Spec.acceptance`, add the both-lists guard in `parse_spec`)
- Test: `tests/test_intake.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `saffron.intake.Criterion` — pydantic `BaseModel`, `model_config = ConfigDict(extra="forbid")`, fields `claim: str`, `witness: str`, `preserves: bool = False`.
  - `saffron.intake.Spec.acceptance: list[Criterion]` — defaults to `[]`.
  - `parse_spec` raises `SpecError` when frontmatter `acceptance` and a markdown `## Acceptance criteria` section are both non-empty.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_intake.py`:

```python
def test_a_declared_acceptance_block_parses_into_structured_criteria():
    spec = parse_spec(
        "---\nid: TE-1\ntitle: t\ntype: feature\n"
        "acceptance:\n"
        "  - claim: the gate reports skip with no witnesses\n"
        "    witness: tests/test_criteria.py::test_no_witnesses_skips\n"
        "  - claim: today's parse is unchanged\n"
        "    witness: tests/test_intake.py::test_extracts_the_acceptance_criteria_as_a_checklist\n"
        "    preserves: true\n"
        "---\n\nbody only\n"
    )
    assert [c.claim for c in spec.acceptance] == [
        "the gate reports skip with no witnesses",
        "today's parse is unchanged",
    ]
    assert spec.acceptance[0].witness == "tests/test_criteria.py::test_no_witnesses_skips"
    assert (spec.acceptance[0].preserves, spec.acceptance[1].preserves) == (False, True)


def test_a_spec_with_no_acceptance_block_parses_exactly_as_it_does_today():
    """Ten specs predate this key. Absent, nothing changes — and the markdown
    section still populates `acceptance_criteria`."""
    spec = parse_spec(
        "---\nid: TE-1\ntitle: t\ntype: bug\n---\n\n"
        "## Acceptance criteria\n- [ ] it works\n"
    )
    assert spec.acceptance == []
    assert spec.acceptance_criteria == ["it works"]


def test_a_spec_declaring_both_lists_is_refused_as_malformed():
    """Two lists of criteria with nothing keeping them in sync, and no way for
    `pr_body` to say which one it is ticking."""
    with pytest.raises(SpecError, match="both"):
        parse_spec(
            "---\nid: TE-1\ntitle: t\ntype: feature\n"
            "acceptance:\n"
            "  - claim: c\n    witness: t.py::test_w\n"
            "---\n\n## Acceptance criteria\n- [ ] it works\n"
        )


def test_an_unknown_key_inside_a_criterion_is_refused():
    """A typo in a witness key is a validation error, not a silent mis-parse —
    which is the whole reason the witness is not hung off the checklist line."""
    with pytest.raises(SpecError):
        parse_spec(
            "---\nid: TE-1\ntitle: t\ntype: feature\n"
            "acceptance:\n"
            "  - claim: c\n    witness: t.py::test_w\n    preserve: true\n"
            "---\n\nbody\n"
        )


def test_a_criterion_missing_its_witness_is_refused():
    with pytest.raises(SpecError):
        parse_spec(
            "---\nid: TE-1\ntitle: t\ntype: feature\n"
            "acceptance:\n  - claim: c\n---\n\nbody\n"
        )
```

Check the top of `tests/test_intake.py` already imports `pytest`, `parse_spec` and
`SpecError`. It does (see `test_a_reserved_acceptance_criteria_key_is_rejected` at line 101);
add nothing to the imports.

- [ ] **Step 2: Run them and confirm they fail**

Run: `uv run pytest tests/test_intake.py -v -k "acceptance or criterion or witness"`

Expected: the four new tests FAIL. `test_a_declared_acceptance_block_parses_into_structured_criteria`
fails with `SpecError: spec frontmatter is invalid: ... Extra inputs are not permitted`
(that is `extra="forbid"` doing its job — the recursion §3.2 names). `test_a_spec_with_no_acceptance_block_parses_exactly_as_it_does_today`
fails on `spec.acceptance` not existing. The two refusal tests fail because no `SpecError` is
raised for the *right* reason.

- [ ] **Step 3: Add `Criterion` to `saffron/intake.py`**

Insert immediately above `class Spec(BaseModel):` (after the `SpecError` class):

```python
class Criterion(BaseModel):
    """One acceptance criterion and the witness the host checks it by.

    `witness` is a test node id, opaque here as everywhere else: intake never
    splits it and the gate never parses it (§5.4).
    """

    model_config = ConfigDict(extra="forbid")

    claim: str
    """The prose the PR body renders. Where `acceptance:` is declared it *is*
    the acceptance criteria, and the markdown section is omitted."""
    witness: str
    preserves: bool = False
    """The criterion claims the change did *not* break this, so its witness is
    checked the opposite way — green at both sides. A new test can never
    preserve: it did not pass at base."""
```

- [ ] **Step 4: Add the field to `Spec`**

In `class Spec`, directly under `acceptance_criteria` (currently `saffron/intake.py:63`):

```python
    acceptance: list[Criterion] = Field(default_factory=list)
```

Note this is a *declared* frontmatter key, not a reserved one — `acceptance_criteria` above
it stays reserved and markdown-derived. The two are never both populated; Step 5 is why.

- [ ] **Step 5: Add the both-lists guard to `parse_spec`**

In `parse_spec`, after the reserved-key loop and before `Spec.model_validate` (currently
between `saffron/intake.py:86` and `:88`):

```python
    # One list or the other. Both is two sets of criteria with nothing keeping
    # them in sync, and no way for `pr_body` to say which one it ticks.
    if fields.get("acceptance") and reserved["acceptance_criteria"]:
        raise SpecError(
            "spec declares both `acceptance:` and a `## Acceptance criteria` "
            "section; where `acceptance:` is declared it is the criteria"
        )
```

- [ ] **Step 6: Run the tests and confirm they pass**

Run: `uv run pytest tests/test_intake.py -v`

Expected: PASS, all of them — the pre-existing tests included. Confirm
`test_extracts_the_acceptance_criteria_as_a_checklist` is still green; it is the `preserves`
witness the fixture in Task 2 names, so it must not move or be renamed for the rest of this
plan.

- [ ] **Step 7: Confirm every existing spec still parses**

The second acceptance criterion says every spec from `SA-0001` to `SA-0010` still parses.
Run:

```bash
uv run python -c "
from pathlib import Path
from saffron.intake import load_spec
for p in sorted(Path('.saffron/specs').glob('*.md')):
    spec, _ = load_spec(p)
    print(f'{spec.id}  acceptance={len(spec.acceptance)}  markdown={len(spec.acceptance_criteria)}')
"
```

Expected: all eleven print, every one with `acceptance=0` and a non-zero `markdown` count.
Any `SpecError` here means Step 5's guard is too eager.

- [ ] **Step 8: Lint and commit**

```bash
make fmt
uv run pytest tests/test_intake.py -q
git add saffron/intake.py tests/test_intake.py
git commit -m "feat(intake): a criterion had no witness, so nothing host-side could ever check one"
```

---

### Task 2: The `criteria` gate

The gate itself, plus the contract obligation it rests on, plus the fixture spec that closes
the recursion the frontmatter cannot. This is the largest task and the one to read the spec's
"The shape" section for twice.

**Files:**
- Create: `saffron/gates/core/criteria.py`
- Create: `tests/test_criteria.py`
- Modify: `saffron/gates/contract.py` (docstring on `Failure.code` only — no behaviour change)

**Interfaces:**
- Consumes: `saffron.intake.Criterion` from Task 1 (`.claim`, `.witness`, `.preserves`).
- Produces:
  - `saffron.gates.core.criteria.criteria_gate(acceptance: Sequence[Criterion], base: list[GateResult], head: list[GateResult]) -> GateResult` — result `gate="criteria"`, `tool` always `None`, status in `pass` / `fail` / `skip`, never `error`.
  - Failure shape: `Failure(file=<the witness>, code=<one of the four codes below>, message=...)`. `pr_body` (Task 5) keys on `file`, so the witness must go there.
  - The four codes, exactly: `witness-not-collected`, `witness-failed`, `witness-green-at-base`, `witness-not-preserved`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_criteria.py`. Note the name `test_a_witness_green_at_base_fails` is
load-bearing — the fixture spec in Step 8 names it as a witness, so it must exist under
exactly that name.

```python
from __future__ import annotations

from saffron.gates.contract import Failure, GateResult
from saffron.gates.core.criteria import criteria_gate
from saffron.intake import Criterion


def _tests(*names: str, failed: tuple[str, ...] = ()) -> GateResult:
    """One enumerating gate result: what it collected, and which of those it
    keyed as failures — the two lists the host is already holding.

    `file` is a constant. The gate reads `failures[].code` and nothing else, and
    deriving a path from a node id here would be this module splitting a name
    that core is forbidden to split.
    """
    return GateResult(
        gate="tests",
        status="fail" if failed else "pass",
        tool="pytest 8.3.2",
        collected=list(names),
        failures=[Failure(file="t.py", code=n) for n in failed],
    )


def _c(witness: str, *, preserves: bool = False) -> Criterion:
    return Criterion(claim=f"a claim about {witness}", witness=witness, preserves=preserves)


def test_no_witnesses_skips():
    """`skip` is the common case and is not a failure: ten specs predate this
    key and must gate exactly as they did before."""
    result = criteria_gate([], base=[_tests("t.py::test_a")], head=[_tests("t.py::test_a")])
    assert result.status == "skip"
    assert result.failures == []


def test_a_new_witness_passing_at_head_is_the_ordinary_shape():
    """Absent from `collected(base)` because the diff adds it, green at head."""
    result = criteria_gate(
        [_c("t.py::test_new")],
        base=[_tests("t.py::test_a")],
        head=[_tests("t.py::test_a", "t.py::test_new")],
    )
    assert result.status == "pass"


def test_a_witness_green_at_base_fails():
    """The direction rule: a witness that already passed proves nothing about
    this change."""
    result = criteria_gate(
        [_c("t.py::test_a")],
        base=[_tests("t.py::test_a")],
        head=[_tests("t.py::test_a")],
    )
    assert result.status == "fail"
    assert [f.code for f in result.failures] == ["witness-green-at-base"]
    assert result.failures[0].file == "t.py::test_a"


def test_a_witness_absent_from_collected_at_head_fails():
    """It names nothing the suite ran, and a criterion nothing ran is the
    defect this gate exists for."""
    result = criteria_gate(
        [_c("t.py::test_missing")],
        base=[_tests("t.py::test_a")],
        head=[_tests("t.py::test_a")],
    )
    assert result.status == "fail"
    assert [f.code for f in result.failures] == ["witness-not-collected"]


def test_a_witness_that_failed_at_head_fails():
    result = criteria_gate(
        [_c("t.py::test_new")],
        base=[_tests("t.py::test_a")],
        head=[_tests("t.py::test_a", "t.py::test_new", failed=("t.py::test_new",))],
    )
    assert result.status == "fail"
    assert [f.code for f in result.failures] == ["witness-failed"]


def test_a_preserves_witness_green_at_both_sides_passes():
    result = criteria_gate(
        [_c("t.py::test_a", preserves=True)],
        base=[_tests("t.py::test_a")],
        head=[_tests("t.py::test_a")],
    )
    assert result.status == "pass"


def test_a_preserves_witness_not_green_at_base_fails():
    """A new test can never preserve: it did not pass at base."""
    result = criteria_gate(
        [_c("t.py::test_new", preserves=True)],
        base=[_tests("t.py::test_a")],
        head=[_tests("t.py::test_a", "t.py::test_new")],
    )
    assert result.status == "fail"
    assert [f.code for f in result.failures] == ["witness-not-preserved"]


def test_a_preserves_witness_broken_at_head_fails():
    result = criteria_gate(
        [_c("t.py::test_a", preserves=True)],
        base=[_tests("t.py::test_a")],
        head=[_tests("t.py::test_a", failed=("t.py::test_a",))],
    )
    assert result.status == "fail"


def test_no_collected_at_either_side_skips():
    """The baseline call hands `base=[]`, and a runner that does not enumerate
    looks the same. Neither is a gate with anything to compare."""
    head = [_tests("t.py::test_a")]
    assert criteria_gate([_c("t.py::test_a")], base=[], head=head).status == "skip"
    assert criteria_gate([_c("t.py::test_a")], base=head, head=[]).status == "skip"


def test_failures_all_absent_from_collected_skips():
    """The membership guard, reached without inspecting a name: a side is
    readable iff its failures are empty or at least one `code` appears in that
    side's `collected`. A runner keying failures on something else is not a
    repo doing something wrong."""
    keyed_elsewhere = GateResult(
        gate="tests",
        status="fail",
        tool="pytest 8.3.2",
        collected=["t.py::test_a", "t.py::test_b"],
        failures=[Failure(file="saffron/gates/runner.py", line=147, code="error")],
    )
    result = criteria_gate(
        [_c("t.py::test_b")], base=[_tests("t.py::test_a")], head=[keyed_elsewhere]
    )
    assert result.status == "skip"


def test_a_witness_that_failed_at_head_is_never_passed_because_the_runner_keyed_elsewhere():
    """The measured case, with the printing test pre-existing so the baseline
    subtracts it and `tests` blocks nothing. Without the membership guard the
    naive rule reads *`test_b` was collected and `test_b` not in {"error"}* and
    reports `pass` for a witness that failed — a ticked box over a red test,
    this spec's own defect reintroduced by the gate that closes it."""
    printing_test_swallows_the_node_ids = GateResult(
        gate="tests",
        status="fail",
        tool="pytest 8.3.2",
        collected=["t.py::test_prints", "t.py::test_b"],
        failures=[Failure(file="saffron/gates/runner.py", line=147, code="error")],
    )
    result = criteria_gate(
        [_c("t.py::test_b")],
        base=[_tests("t.py::test_prints", failed=("t.py::test_prints",))],
        head=[printing_test_swallows_the_node_ids],
    )
    assert result.status != "pass"
    assert result.status == "skip"


def test_an_empty_failures_list_is_readable():
    """A green side has no `code` to test membership on, and is readable — the
    guard is `failures empty OR some code collected`, not `some code collected`."""
    result = criteria_gate(
        [_c("t.py::test_new")],
        base=[_tests("t.py::test_a")],
        head=[_tests("t.py::test_a", "t.py::test_new")],
    )
    assert result.status == "pass"


def test_it_reads_whatever_gate_enumerated_and_names_no_role():
    """Core does not know which role enumerates; §2.1. Two gates splitting the
    suite are unioned, as in `census`."""
    result = criteria_gate(
        [_c("b::test_new")],
        base=[_tests("a::test_a"), GateResult(gate="spec-suite", status="pass", collected=["b::test_b"])],
        head=[_tests("a::test_a"), GateResult(gate="spec-suite", status="pass", collected=["b::test_b", "b::test_new"])],
    )
    assert result.status == "pass"


def test_it_executes_nothing_so_it_claims_no_tool():
    """As `scope`, `integrity`, `size` and `census` all do — which is why
    `run_gate`'s tool requirement never applies to them."""
    for base, head in (([], []), ([_tests("t.py::test_a")], [_tests("t.py::test_a")])):
        assert criteria_gate([_c("t.py::test_a")], base=base, head=head).tool is None


def test_it_never_errors():
    """Reading lists cannot break. A `tests` gate that errored already aborted
    the attempt before this runs, so no task reaches `PREFLIGHT_FAILED`
    because of this gate and the baseline suite (§4.4) is unaffected."""
    broken = [GateResult(gate="tests", status="error", summary="toolchain missing")]
    for base, head in (([], []), (broken, broken), ([_tests()], [_tests()])):
        assert criteria_gate([_c("t.py::test_a")], base=base, head=head).status != "error"


def test_every_unmet_criterion_is_named_with_its_own_reason():
    result = criteria_gate(
        [_c("t.py::test_a"), _c("t.py::test_missing"), _c("t.py::test_new")],
        base=[_tests("t.py::test_a")],
        head=[_tests("t.py::test_a", "t.py::test_new")],
    )
    assert result.status == "fail"
    assert [(f.file, f.code) for f in result.failures] == [
        ("t.py::test_a", "witness-green-at-base"),
        ("t.py::test_missing", "witness-not-collected"),
    ]
    assert "a claim about t.py::test_a" in result.failures[0].message
```

- [ ] **Step 2: Run them and confirm they fail**

Run: `uv run pytest tests/test_criteria.py -v`

Expected: collection ERROR — `ModuleNotFoundError: No module named 'saffron.gates.core.criteria'`.

- [ ] **Step 3: Write the gate's module docstring and the two readers**

Create `saffron/gates/core/criteria.py`:

```python
"""The `criteria` gate: did each criterion's witness run, and turn green? (§5.4)

Core, and it executes nothing — the route `census` took, and `docs/BACKLOG.md`'s
reasoning applies unchanged. Both suites already ran the repo's tests, at
`base_sha` for the baseline and at head on every attempt, so what a witness did
on each side is two lists the host is already holding. Fetching it would need a
§2.1 exception, a second suite execution charged to every task, and it would
turn an absent witness at base into a baseline `error` — which `session.py`
turns into `PREFLIGHT_FAILED` and §4.4 turns into a skipped repo for the night.

What a `pass` here means, exactly: *a test by this name ran at head and passed,
and if it existed at base it was not green there.* It does not mean the criterion
was met. The witness's body is out of reach — `revert` is the gate that reads it
(§5.4), and `def test_w(): assert True` satisfies everything expressible here.

Every name is opaque, as in `census`: never split, never parsed, never assumed to
contain a path or a separator. A gate that recognises `::` has learned a language.
"""

from __future__ import annotations

from collections.abc import Sequence

from saffron.gates.contract import Failure, GateResult
from saffron.intake import Criterion

# (collected, failed) for one tree.
_Side = tuple[set[str], set[str]]


def _side(results: list[GateResult]) -> _Side | None:
    """What one tree's enumerating gates reported, or `None` if unreadable.

    Readable iff some gate enumerated *and* its failures are empty or at least
    one `failures[].code` appears in that enumeration. That membership test is
    the whole of how core learns the field carries node ids — no name is
    inspected, because a gate that looks for a separator has learned a language.

    Measured, which is why it is not optional: this repo's own `tests` gate
    reaches node ids only through a fallback that runs when a regex over the
    whole output matched nothing, and one printed `path:N: word: message` line
    inside a failing test satisfies that regex. Every node id vanishes from
    `code` for that run, and the naive rule then reports `pass` for a witness
    that failed.
    """
    enumerating = [r for r in results if r.collected is not None]
    if not enumerating:
        return None
    collected = {name for r in enumerating for name in r.collected}
    failed = {f.code for r in enumerating for f in r.failures}
    if failed and not (failed & collected):
        return None
    return collected, failed


def _green(side: _Side, witness: str) -> bool:
    """Ran on this side and did not fail. Two set lookups, no subset argument."""
    collected, failed = side
    return witness in collected and witness not in failed
```

- [ ] **Step 4: Run the tests and confirm they still fail, now on the gate itself**

Run: `uv run pytest tests/test_criteria.py -v`

Expected: collection ERROR — `ImportError: cannot import name 'criteria_gate'`. The module
now exists; the entry point does not.

- [ ] **Step 5: Write the per-criterion judgement**

Append to `saffron/gates/core/criteria.py`:

```python
def _fail(criterion: Criterion, code: str, why: str) -> Failure:
    # The witness goes in `file`, as `census` puts a name there: it is what the
    # baseline subtraction and `pr_body` both key on.
    return Failure(
        file=criterion.witness, code=code, message=f"{why} — {criterion.claim}"
    )


def _judge(criterion: Criterion, before: _Side, after: _Side) -> Failure | None:
    """`None` when the criterion holds.

    The direction is the load-bearing part: a criterion claiming the change
    *did* something must name a witness that was not green at `base_sha`,
    because one that already passed proves nothing about this change.
    `preserves: true` claims the opposite and is checked the opposite way.
    """
    collected, _ = after
    if criterion.witness not in collected:
        return _fail(
            criterion, "witness-not-collected", "names nothing the suite ran at head"
        )
    if not _green(after, criterion.witness):
        return _fail(criterion, "witness-failed", "collected at head and failed there")
    if criterion.preserves:
        if _green(before, criterion.witness):
            return None
        return _fail(
            criterion,
            "witness-not-preserved",
            "declared `preserves` but was not green at base_sha",
        )
    if _green(before, criterion.witness):
        return _fail(
            criterion,
            "witness-green-at-base",
            "passed at base_sha, so it proves nothing about this change",
        )
    return None
```

- [ ] **Step 6: Write `criteria_gate`**

Append to `saffron/gates/core/criteria.py`:

```python
def criteria_gate(
    acceptance: Sequence[Criterion],
    base: list[GateResult],
    head: list[GateResult],
) -> GateResult:
    """Each criterion's witness, judged on two sides by name and outcome.

    `skip` is the common case and is not a failure: ten specs predate this key,
    and a spec that declares no witness must gate exactly as it did before.
    Reaching for a default witness would be worse — a criterion checked against
    an invented test is the defect this gate exists to close, wearing the fix's
    clothes.

    There is almost no `error` to produce. Reading lists cannot break; a `tests`
    gate that errored already aborted the attempt before this runs, and a runner
    that keys failures on something other than a node id is `skip`.
    """
    if not acceptance:
        return GateResult(
            gate="criteria", status="skip", summary="the spec declares no witnesses"
        )

    before, after = _side(base), _side(head)
    if before is None or after is None:
        # Both sides degrade the same way, as `census` does when a runner does
        # not enumerate: never report `pass` on a field you could not read.
        return GateResult(
            gate="criteria",
            status="skip",
            summary=(
                f"no readable enumeration at {'base_sha' if before is None else 'head'}: "
                "the runner reported no collected tests, or keyed its failures "
                "on something other than a node id"
            ),
        )

    unmet = [f for f in (_judge(c, before, after) for c in acceptance) if f is not None]
    if not unmet:
        return GateResult(
            gate="criteria",
            status="pass",
            summary=f"{len(acceptance)} criteria witnessed at head",
        )
    return GateResult(
        gate="criteria",
        status="fail",
        failures=unmet,
        summary=f"{len(unmet)} of {len(acceptance)} criteria have no passing witness",
    )
```

- [ ] **Step 7: Run the tests and confirm they pass**

Run: `uv run pytest tests/test_criteria.py -v`

Expected: PASS, every test. If `test_a_witness_that_failed_at_head_is_never_passed_because_the_runner_keyed_elsewhere`
is the one that fails, the membership guard in `_side` is wrong — reread the spec's "How core
knows the field carries node ids" paragraph before touching it.

- [ ] **Step 8: Add the fixture spec test — the recursion the frontmatter cannot close**

This spec cannot declare `acceptance:` in its own frontmatter (Task 1 Step 2 showed why:
`extra="forbid"` refuses it at intake before this change exists). §3.2's standing answer is a
fixture in the same change. It is a **string literal**, not a file: `touches` lists individual
test paths, so a new `tests/fixtures/*.md` falls outside it and `scope` fails the diff.

Append to `tests/test_criteria.py`:

```python
_FIXTURE_SPEC = """---
id: TE-11
title: A spec that declares the key this spec introduces
type: feature
acceptance:
  - claim: "a witness that was already green at base_sha fails the gate"
    witness: tests/test_criteria.py::test_a_witness_green_at_base_fails
  - claim: "a spec with no acceptance block parses exactly as it does today"
    witness: tests/test_intake.py::test_extracts_the_acceptance_criteria_as_a_checklist
    preserves: true
---

The `acceptance:` block above is the one from SA-0011's own `## The format`
section. A string literal, not a file: `touches` names individual test paths.
"""


def test_the_fixture_spec_parses_and_passes_the_gate():
    """SA-0011 cannot declare `acceptance:` in its own frontmatter — `Spec` sets
    `extra="forbid"`, so a spec declaring the key it introduces is refused at
    intake as malformed (§3.2). This is the fixture that closes the recursion:
    the first witness is a test this change adds (absent at base, green at
    head), the second an existing one named because the criterion is *do not
    break this*."""
    from saffron.intake import parse_spec

    spec = parse_spec(_FIXTURE_SPEC)
    assert len(spec.acceptance) == 2
    assert spec.acceptance_criteria == []

    new, preserved = (c.witness for c in spec.acceptance)
    result = criteria_gate(
        spec.acceptance,
        base=[_tests(preserved)],
        head=[_tests(preserved, new)],
    )
    assert result.status == "pass", result.summary


def test_the_fixture_spec_names_witnesses_that_exist():
    """A witness naming a test nobody wrote is exactly what this gate fails
    tasks for. Asserted rather than trusted: both names are string literals no
    import checks, and a rename would leave the fixture pointing at nothing."""
    from saffron.intake import parse_spec

    from tests import test_intake

    assert {c.witness for c in parse_spec(_FIXTURE_SPEC).acceptance} == {
        "tests/test_criteria.py::test_a_witness_green_at_base_fails",
        "tests/test_intake.py::test_extracts_the_acceptance_criteria_as_a_checklist",
    }
    assert callable(test_a_witness_green_at_base_fails)
    assert callable(test_intake.test_extracts_the_acceptance_criteria_as_a_checklist)
```

- [ ] **Step 9: Run the fixture tests**

Run: `uv run pytest tests/test_criteria.py -v -k fixture`

Expected: both PASS. If the import of `tests.test_intake` fails, confirm `tests/__init__.py`
exists — it does.

- [ ] **Step 10: Document the contract obligation on `Failure.code`**

This is the one cost of the reading route, exactly parallel to the `collected` field `census`
added. Docstring only — **no behaviour change** in `contract.py`.

In `saffron/gates/contract.py`, the `Failure` model currently reads:

```python
    file: str
    line: int | None = None
    code: str
    message: str = ""
```

Change the `code` line to carry a field docstring, matching the style `GateResult.tool` and
`GateResult.collected` already use:

```python
    code: str
    """The gate's own identifier for this failure — a rule id, an exception
    type, or, for a gate that enumerates, the node id of the test that failed.
    `criteria` can read a witness's outcome only where an enumerating gate keys
    its failures that way; where it does not, `criteria` skips (§5.4)."""
```

- [ ] **Step 11: Run the whole suite and commit**

```bash
make fmt
uv run pytest -q
git add saffron/gates/core/criteria.py saffron/gates/contract.py tests/test_criteria.py
git commit -m "feat(gates): an unchecked criterion was indistinguishable from a met one"
```

Expected: the full suite green. `tests/test_contract.py` must still pass — the `code`
docstring changes nothing at runtime.

---

### Task 3: `criteria` runs in the suite, and the witnesses reach the cell

The gate exists and is unreachable. `_suite` is where the two sides meet, and `CellSpec` is
the boundary the witnesses have to cross from the operator's host-side spec.

**Files:**
- Modify: `saffron/cell/session.py` (`CellSpec.acceptance`, the `_drive_cell` import, `_suite`'s return)
- Modify: `saffron/cli.py` (pass `acceptance` into `CellSpec`)
- Test: `tests/test_session.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `criteria_gate(acceptance, base, head)` from Task 2; `Criterion` and `Spec.acceptance` from Task 1.
- Produces:
  - `session.CellSpec.acceptance: list[Criterion]`, defaulting to `[]`.
  - A `GateResult(gate="criteria", ...)` present in every suite result list, and therefore in `CellOutcome.gates` (`saffron/cell/session.py:1089`, `gates=green`) — which is what Task 5 reads.

- [ ] **Step 1: Write the failing test for the cli half**

Append to `tests/test_cli.py`. `_ceiling_spec` cannot be used here — it always appends a
`## Acceptance criteria` section, which Task 1's guard now refuses alongside `acceptance:`.

```python
def test_a_specs_declared_witnesses_reach_the_cell(tmp_path, monkeypatch, capsys):
    """`cli.load_spec` parses the operator's host-side copy before the cell
    starts, so the witnesses the gate checks were never in `/work` — that, and
    `.saffron/**` being outside `touches`, is what stops the cell relaxing one.
    Parsed and then discarded would leave the gate with nothing to check."""
    repo = _local_origin(tmp_path)
    args = _namespace(repo, tmp_path)
    spec = tmp_path / "SY-3.md"
    spec.write_text(
        "---\nid: SY-3\ntitle: Three\ntype: feature\ntouches: ['src/**']\n"
        "acceptance:\n"
        "  - claim: it works\n"
        "    witness: tests/test_x.py::test_it_works\n"
        "---\n\nbody\n"
    )
    args.spec = spec

    cell_spec, _printed = _capture_cell_spec(monkeypatch, repo, tmp_path, args, capsys)

    assert [c.witness for c in cell_spec.acceptance] == [
        "tests/test_x.py::test_it_works"
    ]
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run pytest tests/test_cli.py::test_a_specs_declared_witnesses_reach_the_cell -v`

Expected: FAIL with `AttributeError: 'CellSpec' object has no attribute 'acceptance'`.

- [ ] **Step 3: Add the field to `CellSpec` and pass it from `cli`**

In `saffron/cell/session.py`, add the import beside the other top-level ones (after
`from saffron.gates.contract import GateResult`):

```python
from saffron.intake import Criterion
```

In `class CellSpec`, after `forbidden` (currently `saffron/cell/session.py:155`):

```python
    # From the operator's host-side copy, parsed by `cli.load_spec` before the
    # cell exists — so what `criteria` checks was never in /work (§5.4).
    acceptance: list[Criterion] = field(default_factory=list)
```

In `saffron/cli.py`, in the `CellSpec(...)` construction (currently around `:176`), add
after `forbidden=spec.forbidden,`:

```python
        acceptance=spec.acceptance,
```

- [ ] **Step 4: Run the cli test and confirm it passes**

Run: `uv run pytest tests/test_cli.py -v`

Expected: PASS, the whole file. Confirm `test_a_specs_declared_risk_reaches_the_cell` and
both ceiling tests are still green — `_ceiling_spec` is untouched.

- [ ] **Step 5: Write the failing test for the suite half**

Append to `tests/test_session.py`:

```python
def test_the_criteria_gate_reads_both_suites_and_invokes_nothing(monkeypatch, tmp_path):
    """`census_gate(base, head)` is the shape, not `scope_gate`'s single tree.
    The baseline call hands `prior=[]`, so the gate skips there and no task
    reaches `PREFLIGHT_FAILED` because of it."""
    from saffron.intake import Criterion

    base = [
        GateResult(gate="tests", status="pass", tool="pytest 8", collected=["t.py::test_a"])
    ]
    head = [
        GateResult(
            gate="tests",
            status="pass",
            tool="pytest 8",
            collected=["t.py::test_a", "t.py::test_new"],
        )
    ]
    cell = _stub_the_runtime(monkeypatch, suites=(base, head, head))
    outcome = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
        spec=_spec(
            acceptance=[
                Criterion(claim="it works", witness="t.py::test_new"),
            ]
        ),
    )
    result = next(r for r in outcome.gates if r.gate == "criteria")
    assert result.status == "pass"
    assert result.tool is None


def test_the_criteria_gate_skips_for_a_spec_that_declares_no_witnesses(
    monkeypatch, tmp_path
):
    """Ten specs predate this key. `skip` is what they get, and every existing
    behaviour is unchanged."""
    cell = _stub_the_runtime(monkeypatch)
    outcome = _drive(
        monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PLAN)), _turn()]
    )
    result = next(r for r in outcome.gates if r.gate == "criteria")
    assert result.status == "skip"
```

Read `_drive`'s signature (`tests/test_session.py:502`) and `_stub_the_runtime`'s
(`:390`) before writing these — `suites` is an iterable of *declared* gate result lists, one
per `run_suite` call, and the first call is the baseline. `_turn`, `_block` and `_PLAN` are
already defined in the module; add no imports beyond the local `Criterion` one.

- [ ] **Step 6: Run them and confirm they fail**

Run: `uv run pytest tests/test_session.py -v -k criteria`

Expected: FAIL with `StopIteration` from the `next(...)` — no result named `criteria` is in
`outcome.gates`, because the gate is not wired in.

- [ ] **Step 7: Wire the gate into `_suite`**

In `saffron/cell/session.py`, inside `_drive_cell`'s local import block (currently `:491`,
where `census_gate` is imported), add beside it:

```python
    from saffron.gates.core.criteria import criteria_gate
```

Then change `_suite`'s return (currently `saffron/cell/session.py:702-703`) from:

```python
            # `prior` is empty on the baseline call, and census skips.
            return [*results, census_gate(prior, results)]
```

to:

```python
            # `prior` is empty on the baseline call, so both skip there. Both
            # read two suites and invoke nothing (§5.4).
            return [
                *results,
                census_gate(prior, results),
                criteria_gate(spec.acceptance, prior, results),
            ]
```

- [ ] **Step 8: Run the session tests and confirm they pass**

Run: `uv run pytest tests/test_session.py -v`

Expected: PASS, the whole file. Watch two in particular:
- `test_a_gate_that_stopped_running_between_the_suites_is_not_a_green` — `suite_drift`
  compares gate names across suites; `criteria` is present in both, so it must not trip.
- `test_an_errored_gate_aborts_rather_than_counting_against_the_task` — `criteria` never
  produces `error`, so `aborted_gates` must not gain a member.

- [ ] **Step 9: Run the whole suite and commit**

```bash
make check
git add saffron/cell/session.py saffron/cli.py tests/test_session.py tests/test_cli.py
git commit -m "spec(SA-0011): the gate existed and no suite ever called it"
```

---

### Task 4: The witnesses reach the IMPLEMENT prompt

A gate that blocks on a target the agent was never shown burns every attempt for a reason no
repair turn can diagnose. Today only `spec.body` — the markdown, not the frontmatter — is
substituted into a prompt, and the witnesses live in frontmatter.

**Files:**
- Modify: `saffron/agents/context.py` (add `witnesses_block`)
- Modify: `saffron/agents/prompts/implement.md` (add the `{witnesses}` placeholder)
- Modify: `saffron/cell/session.py` (pass the value at the `build_system_prompt` call, `:741`)
- Test: `tests/test_context.py`, `tests/test_session.py`

**Interfaces:**
- Consumes: `Criterion` from Task 1; `CellSpec.acceptance` from Task 3.
- Produces: `saffron.agents.context.witnesses_block(acceptance: Sequence[Criterion]) -> str` — the empty string for a spec declaring none, heading included in the returned block (never in the template).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_context.py`:

```python
def test_the_declared_witnesses_reach_the_prompt_verbatim():
    """They are exact strings the implementer has to name its tests. A gate
    that blocks on a target the agent was never shown burns every attempt for
    a reason no repair turn can diagnose."""
    from saffron.intake import Criterion

    block = context.witnesses_block(
        [
            Criterion(claim="the box ticks", witness="tests/test_criteria.py::test_a"),
            Criterion(claim="nothing broke", witness="tests/test_intake.py::test_b", preserves=True),
        ]
    )
    assert "tests/test_criteria.py::test_a" in block
    assert "tests/test_intake.py::test_b" in block
    assert "the box ticks" in block
    assert "preserves" in block


def test_a_spec_declaring_no_witnesses_gets_no_witness_heading():
    """A heading over nothing reads as withheld and invites an invented list —
    `constraints_block`'s own rule, and a default witness is exactly the defect
    SA-0011 exists to close."""
    assert context.witnesses_block([]) == ""
```

Confirm `tests/test_context.py` imports the module as `context` — check the file's imports
before writing, and match whatever name is already bound.

Append to `tests/test_session.py`:

```python
def test_the_implement_prompt_names_the_witnesses_it_is_judged_against(
    monkeypatch, tmp_path
):
    """Only `spec.body` — the markdown, not the frontmatter — was ever
    substituted, and the witnesses live in frontmatter."""
    from saffron.intake import Criterion

    cell = _stub_the_runtime(monkeypatch)
    _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
        spec=_spec(
            acceptance=[
                Criterion(claim="the box ticks", witness="tests/test_x.py::test_ticks")
            ]
        ),
    )
    prompt = cell.system_prompts[0]
    assert "tests/test_x.py::test_ticks" in prompt
    assert "the box ticks" in prompt


def test_a_spec_with_no_witnesses_shows_no_witness_heading(monkeypatch, tmp_path):
    cell = _stub_the_runtime(monkeypatch)
    _drive(monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PLAN)), _turn()])
    assert "witnesses you are judged against" not in cell.system_prompts[0]
```

- [ ] **Step 2: Run them and confirm they fail**

Run: `uv run pytest tests/test_context.py tests/test_session.py -v -k witness`

Expected: FAIL with `AttributeError: module 'saffron.agents.context' has no attribute 'witnesses_block'`.

- [ ] **Step 3: Add `witnesses_block` to `saffron/agents/context.py`**

Insert after `constraints_block` (which ends at `:70`) and before `build_system_prompt`. Add
`from collections.abc import Sequence` and `from saffron.intake import Criterion` to the
module's imports.

```python
def witnesses_block(acceptance: Sequence[Criterion]) -> str:
    """The witnesses `criteria` checks, as prompt text.

    Verbatim, because they are exact strings the implementer has to name its
    tests. Returned as a substituted value, like `constraints_block` — the
    caller hands it to `build_system_prompt`, which passes it to `.format` as an
    argument and never as a format string (§5.3). Empty for a spec declaring
    none: a heading over nothing invites an invented list.
    """
    if not acceptance:
        return ""
    lines = [
        "## The witnesses you are judged against",
        "",
        "Each criterion names a test node id the host checks after you finish, "
        "by reading what the suite collected and what it failed — at the base "
        "commit and at head. Name your tests exactly these strings.",
        "",
        "A witness marked `preserves` must already pass at the base commit and "
        "still pass. Every other witness must **not** pass at the base commit "
        "and must pass when you are done: a test that was already green proves "
        "nothing about this change.",
        "",
    ]
    lines += [
        f"- `{c.witness}`{' *(preserves)*' if c.preserves else ''} — {c.claim}"
        for c in acceptance
    ]
    return "\n".join(lines)
```

- [ ] **Step 4: Add the placeholder to `saffron/agents/prompts/implement.md`**

The template currently ends:

```
{constraints}

## The task

{spec}
```

Change it to:

```
{constraints}

{witnesses}

## The task

{spec}
```

The heading lives inside the block, not here — `witnesses_block` returns `""` for a spec
declaring none, and a bare blank line is the right residue.

- [ ] **Step 5: Pass the value at the call site**

In `saffron/cell/session.py`, the `build_system_prompt` call (currently `:741`) ends with the
`constraints=` argument. Add after it:

```python
            witnesses=context.witnesses_block(spec.acceptance),
```

- [ ] **Step 6: Run the tests and confirm they pass**

Run: `uv run pytest tests/test_context.py tests/test_session.py -v`

Expected: PASS, both files whole. `test_a_template_missing_the_spec_placeholder_raises` and
`test_the_spec_body_with_a_bare_brace_never_raises` must stay green — `build_system_prompt`
is unchanged, and `{witnesses}` is an ordinary `.format` key on the non-spec parts.

- [ ] **Step 7: Commit**

```bash
make fmt
uv run pytest -q
git add saffron/agents/context.py saffron/agents/prompts/implement.md \
        saffron/cell/session.py tests/test_context.py tests/test_session.py
git commit -m "feat(agents): the gate blocked on witnesses the implementer was never shown"
```

---

### Task 5: The PR body ticks from the gate, and says which kind of unticked it is

The half that pays off from day one. `pr_body.py:128` renders every criterion unticked,
always, with no host-side component anywhere that asks whether one was met — a checklist that
reads as evidence and is not.

**Files:**
- Modify: `saffron/report/pr_body.py` (`_criteria` and its call site)
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: `Spec.acceptance` (Task 1) and the `GateResult(gate="criteria", ...)` that Task 3 put into `results`. `render_pr_body`'s signature does **not** change — it already receives both `spec` and `results`.
- Produces: `_criteria(spec: Spec, results: Sequence[GateResult]) -> str`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_report.py`. `SPEC` and `RESULTS` at the top of that file are unchanged;
these tests build their own.

```python
def _witness_spec():
    return parse_spec(
        "---\nid: TE-11\ntitle: Witnessed\ntype: feature\n"
        "acceptance:\n"
        "  - claim: the first criterion\n"
        "    witness: t.py::test_ticks\n"
        "  - claim: the second criterion\n"
        "    witness: t.py::test_missing\n"
        "---\n\nbody\n"
    )


def _witness_body(*results):
    return render_pr_body(
        _witness_spec(),
        list(results),
        [],
        base_sha="a" * 40,
        head_sha="b" * 40,
        added=10,
        removed=1,
        transcript_path="~/.saffron/batches/1/r/1",
    )


def test_a_met_criterion_is_ticked_only_from_a_gate_result():
    rendered = _witness_body(
        GateResult(gate="criteria", status="pass", summary="2 criteria witnessed at head")
    )
    assert "- [x] the first criterion" in rendered
    assert "- [x] the second criterion" in rendered


def test_an_unmet_criterion_is_unticked_and_carries_the_reason():
    rendered = _witness_body(
        GateResult(
            gate="criteria",
            status="fail",
            failures=[
                Failure(
                    file="t.py::test_missing",
                    code="witness-not-collected",
                    message="names nothing the suite ran at head",
                )
            ],
            summary="1 of 2 criteria have no passing witness",
        )
    )
    assert "- [x] the first criterion" in rendered
    assert "- [ ] the second criterion" in rendered
    assert "witness-not-collected" in rendered


def test_a_skipped_gate_never_ticks_a_declared_criterion():
    """`skip` means nobody looked. A box ticked from it would be the defect
    this spec exists to close, wearing the fix's clothes."""
    rendered = _witness_body(
        GateResult(gate="criteria", status="skip", summary="no readable enumeration at head")
    )
    assert "- [x]" not in rendered
    assert "not mechanically checked" in rendered.lower()


def test_a_spec_predating_the_key_is_marked_not_mechanically_checked():
    """The ten specs from SA-0001 to SA-0010 keep the markdown section and the
    gate skips — an unticked box meaning *nobody looked* must not render
    identically to one meaning *the witness failed*."""
    rendered = body()
    assert "- [ ] A regression test exists that fails on the current `main`" in rendered
    assert "not mechanically checked" in rendered.lower()
    assert "- [x]" not in rendered


def test_a_spec_with_no_criteria_at_all_renders_no_section():
    spec = parse_spec("---\nid: TE-0\ntitle: t\ntype: chore\n---\n\nbody\n")
    rendered = render_pr_body(
        spec,
        [],
        [],
        base_sha="a" * 40,
        head_sha="b" * 40,
        added=1,
        removed=0,
        transcript_path="/tmp/x",
    )
    assert "Acceptance criteria" not in rendered
```

Check `tests/test_report.py`'s imports at the top of the file for `parse_spec`, `GateResult`
and `Failure` — all three are already imported (`SPEC` uses `parse_spec`, `RESULTS` uses the
other two). Add nothing.

- [ ] **Step 2: Run them and confirm they fail**

Run: `uv run pytest tests/test_report.py -v -k "criterion or mechanically or witness or no_criteria"`

Expected: FAIL. `test_a_met_criterion_is_ticked_only_from_a_gate_result` fails because
`_criteria` reads `spec.acceptance_criteria` — empty for a witness spec — and renders nothing.
`test_a_spec_predating_the_key_is_marked_not_mechanically_checked` fails on the missing label.

- [ ] **Step 3: Rewrite `_criteria` in `saffron/report/pr_body.py`**

Add the label constant beside `_BODY_LIMIT` / `_TRUNCATED` near the top of the module:

```python
_UNCHECKED = (
    "> **Not mechanically checked.** No `criteria` gate result stands behind these "
    "boxes: an unticked one means nobody looked, not that the criterion failed. A "
    "spec declares witnesses with an `acceptance:` block."
)
```

Replace `_criteria` (currently `saffron/report/pr_body.py:124-130`) with:

```python
def _criteria(spec: Spec, results: Sequence[GateResult]) -> str:
    """The checklist, and which kind of unticked each box is.

    Every box was unticked always, for every criterion, with nothing host-side
    that could ever tick one — a checklist that reads as evidence and is not
    (§5.4's `tool` defect, one layer up). A box ticks only from a `criteria`
    gate result; `skip` means nobody looked and must not render as a failure.
    """
    result = next((r for r in results if r.gate == "criteria"), None)
    if spec.acceptance and result is not None and result.status in ("pass", "fail"):
        unmet = {f.file: f for f in result.failures}
        lines = ["### Acceptance criteria", ""]
        for criterion in spec.acceptance:
            failure = unmet.get(criterion.witness)
            box = "- [ ]" if failure else "- [x]"
            why = f": `{failure.code}`" if failure else ""
            lines.append(f"{box} {criterion.claim} — `{criterion.witness}`{why}")
        lines.append("")
        return "\n".join(lines)

    claims = [c.claim for c in spec.acceptance] or spec.acceptance_criteria
    if not claims:
        return ""
    return "\n".join(
        ["### Acceptance criteria", "", _UNCHECKED, ""]
        + [f"- [ ] {claim}" for claim in claims]
        + [""]
    )
```

The claims and witnesses are spec-authored — human text from the operator's host-side copy,
never the cell's — so they are not routed through `_cell`, exactly as `spec.title` is not. The
failure `code` is one of four host literals from `criteria.py`.

- [ ] **Step 4: Update the call site**

In `render_pr_body`'s `sections` list (currently `saffron/report/pr_body.py:93`), change:

```python
        _criteria(spec),
```

to:

```python
        _criteria(spec, results),
```

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `uv run pytest tests/test_report.py -v`

Expected: PASS, the whole file. `test_acceptance_criteria_render_as_an_unchecked_checklist`
(line 73) must stay green — its `SPEC` declares no `acceptance:`, so it takes the second
branch and the `- [ ]` line it asserts on is unchanged, now with the label above it.

- [ ] **Step 6: Run the whole suite and commit**

```bash
make check
git add saffron/report/pr_body.py tests/test_report.py
git commit -m "feat(report): the checklist read as evidence and nothing could ever tick it"
```

---

### Task 6: Final verification against the spec's own criteria

No new code. This is the pass that checks the change against `SA-0011`'s thirteen acceptance
criteria and its size ceiling before the branch is offered for review.

**Files:** none modified.

- [ ] **Step 1: The full suite, clean**

Run: `make check`

Expected: lint clean, every test passing. Paste the tail of the output into the PR body draft
— *evidence before assertions*, and CI in this repo has never passed, so `make check` is the
only gate that means anything.

- [ ] **Step 2: Confirm the diff stays inside `touches`**

```bash
git diff --name-only $(git merge-base HEAD main)..HEAD
```

Expected: only the fourteen paths in Global Constraints. Any other path — a `tests/fixtures/`
file above all — is a `scope` failure waiting to happen.

- [ ] **Step 3: Confirm the size ceiling**

```bash
git diff --shortstat $(git merge-base HEAD main)..HEAD
```

`risk: elevated` makes `size` blocking at **600 lines** for a `feature`. If the total is over,
stop and raise it rather than cutting: the spec names `preserves` as the one separable half
(Task 2's `witness-not-preserved` branch, its three tests, and Task 5's handling), worth two
of the thirteen acceptance criteria.

- [ ] **Step 4: Walk the spec's acceptance criteria**

Open `.saffron/specs/SA-0011-criteria-have-witnesses.md` at `## Acceptance criteria` and check
each against a named test. The map:

| Criterion | Test |
|---|---|
| Structured parse; markdown-only unchanged | `test_a_declared_acceptance_block_parses_into_structured_criteria`, `test_a_spec_with_no_acceptance_block_parses_exactly_as_it_does_today` |
| `skip` with no witnesses; SA-0001–0010 still parse and gate | `test_no_witnesses_skips`, `test_the_criteria_gate_skips_for_a_spec_that_declares_no_witnesses`, Task 1 Step 7 |
| `skip` on no `collected`, or failures all absent from it | `test_no_collected_at_either_side_skips`, `test_failures_all_absent_from_collected_skips` |
| Never `pass` when the runner keyed elsewhere | `test_a_witness_that_failed_at_head_is_never_passed_because_the_runner_keyed_elsewhere` |
| Absent from `collected(head)` fails | `test_a_witness_absent_from_collected_at_head_fails` |
| Green at base fails unless `preserves` | `test_a_witness_green_at_base_fails`, `test_a_preserves_witness_green_at_both_sides_passes` |
| `preserves` fails unless green at both | `test_a_preserves_witness_not_green_at_base_fails`, `test_a_preserves_witness_broken_at_head_fails` |
| New witness at head is the ordinary shape; no `error` anywhere | `test_a_new_witness_passing_at_head_is_the_ordinary_shape`, `test_it_never_errors` |
| No `tool`, never reaches `run_gate`'s requirement | `test_it_executes_nothing_so_it_claims_no_tool`, plus `_suite` constructing it host-side |
| Witnesses reach the IMPLEMENT prompt verbatim | `test_the_implement_prompt_names_the_witnesses_it_is_judged_against` |
| Both lists refused at intake | `test_a_spec_declaring_both_lists_is_refused_as_malformed` |
| Ticks only from a gate result; unticked carries the reason | `test_a_met_criterion_is_ticked_only_from_a_gate_result`, `test_an_unmet_criterion_is_unticked_and_carries_the_reason` |
| `skip` renders as not mechanically checked | `test_a_skipped_gate_never_ticks_a_declared_criterion`, `test_a_spec_predating_the_key_is_marked_not_mechanically_checked` |
| Fixture spec parses and passes, as a string literal | `test_the_fixture_spec_parses_and_passes_the_gate`, `test_the_fixture_spec_names_witnesses_that_exist` |

Any row with no green test is unfinished work, not a judgement call.

- [ ] **Step 5: Note what the operator still owes**

These are `forbidden` here and are the operator's, on the PR — do not edit them, and say so
in the PR body (PR #44's shape):

- `DESIGN.md` §5.4's role table gains a seventh core gate.
- `CONTEXT.md` §4's core-gate enumeration gains `criteria`.

And the four soundness edges the direction rule does not close, which belong in the PR body
as stated limits rather than as work: **vacuous** (`assert True` in a new witness — `revert`'s
job), **flaky** (a witness that happened to fail at base), **refactor** (every criterion is
`preserves`, so the rule yields no signal), and **modified-at-head** (judged by name, not by
body).

---

## Notes for whoever executes this

**Read two results; invoke nothing.** The temptation is to run the witnesses. That path needs
a §2.1 exception, a second suite execution charged to every task, and it turns an absent
witness at base into a baseline `error` — which `session.py` turns into `PREFLIGHT_FAILED` and
§4.4 turns into a skipped repo for the whole night. `docs/BACKLOG.md`'s `census` entry is the
precedent and the reasoning.

**`skip` is not a failure and is the common case.** A spec with no `acceptance:` block must
leave every existing behaviour unchanged.

**Do not "simplify" the membership guard.** It exists because a measured case in this repo's
own `tests` gate makes the naive rule report `pass` for a witness that failed. `docs/evidence/`
and the spec's "How core knows the field carries node ids" paragraph are the record.
