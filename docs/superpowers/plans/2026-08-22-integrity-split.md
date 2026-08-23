# Splitting `integrity` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `integrity` keeps only the two questions a diff can answer, and "was an existing test removed?" moves to a new core gate that compares the set of collected test names at `base_sha` against the set at head.

**Architecture:** `GateResult` gains one optional field, `collected`. The repo's `tests` gate populates it. A new host-side core gate, `census`, subtracts the two lists the host already holds — the baseline suite and the head suite both run `tests` today, so nothing extra is executed and no §2.1 exception is needed. `integrity` loses `_runs`/`_unreplaced_removals` and gains the `touches` exemption on its two surviving checks.

**Tech Stack:** Python 3.12, pydantic v2, pytest, `git` (2.50.1 measured). **No new dependencies.**

**Spec:** `docs/superpowers/specs/2026-08-22-integrity-split-design.md`

**Evidence:** `docs/evidence/2026-08-22-integrity-rejected-gate-measured.md` — the measurements the spec argues from. Read it before Task 5; it is why three of Appendix K's claims are not repeated here.

## Global Constraints

- **No new dependencies.** `uv.lock` is in `.saffron/policy.yaml`'s `protected` list.
- **`error` is not `fail`.** A gate that broke aborts the attempt and is charged to nobody; only the repo's code being wrong is `fail` (§5.4).
- **The `tool` field is obtained by executing the tool**, never a string literal (§5.4, Appendix H). Host-side core gates that execute nothing leave it `None`, as `scope_gate` already does.
- **Bare `§` cites `DESIGN.md`.** The spec's own sections are "part N".
- **`DESIGN.md` section numbers are an API.** Add subsections and rows; never renumber.
- **No language knowledge in `saffron/`.** No `def test_`, no `::` splitting, no file extensions. A collected name is an opaque string.
- **Vocabulary is enforced** (`CONTEXT.md`): "cell" not "sandbox", "gate result" not "gate run", a `Finding` carries a `claim`.
- **Commit subjects:** lowercase `type(scope): what changed`, written about the defect rather than the file.
- Run `make check` before every commit.
- **Branch:** `joel/integrity-split` already exists and carries the spec commit. Do not create another.

## File Structure

| File | Responsibility |
|---|---|
| `saffron/gates/contract.py` | **Modify.** `GateResult.collected` — the one contract change. |
| `saffron/gates/core/census.py` | **Create.** Set subtraction over two gate-result lists. No I/O, no diff, no execution. |
| `saffron/gates/core/integrity.py` | **Create.** Diff-only: added suppressions, gate-config edits. Both honour `touches`. |
| `saffron/cell/session.py` | **Modify.** `_suite` takes the prior results; `census` and `integrity` join the suite. |
| `.saffron/gates/tests.py` | **Modify.** Repo-side: report the collected node ids. |
| `tests/test_census.py` | **Create.** |
| `tests/test_integrity.py` | **Create.** Fixtures from real `git diff`, never synthetic strings. |
| `DESIGN.md` | **Modify.** §5.4, §2.1, a new appendix. Task 1, before any code. |
| `docs/BACKLOG.md` | **Modify.** Close item 1; strike the two claims measurement corrected. |

Task order: 1 (design) → 2 (contract) → 3 (repo gate) → 4 (`census`) → 5 (`integrity`) → 6 (wiring) → 7 (docs). Tasks 4 and 5 are independent of each other; both need 2.

---

### Task 1: `DESIGN.md` — the decisions, before any code

The spec's part 5. Written first because §5.4 currently describes a three-check `integrity` that this plan does not build, and code landing against a stale design is how the two drift.

**Files:**
- Modify: `DESIGN.md` — §2.1 table (line ~140), §5.4 `integrity` paragraph (line ~645), §5.4 gate-role table (line ~621), a new appendix after Appendix L (line ~1947 onward)

**Interfaces:**
- Consumes: nothing.
- Produces: the design text every later task cites. No code symbols.

- [ ] **Step 1: Replace §5.4's `integrity` paragraph**

Find the paragraph beginning `**`integrity` — the anti-gaming gate.**` (line ~645). Replace its first paragraph (up to and including "...cheapest path to green.") with:

```markdown
**`integrity` — the anti-gaming gate.** The dominant failure mode of a hard-gate self-repair loop is not the agent giving up; it is the agent *making the gate pass*. Deleting a failing test, adding `@pytest.mark.skip` or `xfail`, sprinkling `# type: ignore`, loosening `==` to `is not None`, lowering a threshold in config. Two of those are visible in the diff and one is not, so the work is split across two gates: `integrity` fails on any newly added suppression and any edit to gate configuration, **unless `touches` explicitly includes the file**; `census` (below) answers deletion, which a diff cannot. Without the pair, hard gates actively *train the loop toward test destruction*, because that's the cheapest path to green.

**The exemption binds `integrity`'s two checks and not `census`.** For a suppression or a gate-config edit the signal is *this file changed at all*, and a spec whose `touches` names the file has authorized exactly that. It is also the only defence a substring scan has against prose: a docstring quoting `@pytest.mark.skip` is a use of the token to core, and the file is in `touches` by construction or `scope` would have failed first. Deletion is the opposite case. `touches: tests/test_session.py` authorizes *editing* that file; it does not authorize deleting three unrelated tests inside it to reach green, which is the precise act being defended against. Exempting deletion would silence `census` on nearly every real task, since almost every spec names a test file.
```

- [ ] **Step 2: Add the `census` paragraph after `integrity`'s vocabulary block**

After the `integrity:` YAML excerpt and the sentence ending "keeps the check in core where it gets maintained.", insert:

```markdown
**`census` — which tests existed, and which exist now.** The set of test names collected at `base_sha`, minus the set collected at head. A name that was there and is not is a removed test, one failure each.

This is the same question `integrity` used to ask of the diff, asked where the answer actually lives. Three diff-shaped versions of it were written and all three were wrong, in three different ways: net line count is defeated by a comment longer than the test, run adjacency by *any* adjacent added line, and neither sees a test renamed out of collection — where nothing is removed, nothing is suppressed, the body survives intact, and the test never runs again. A set comparison has no false positive on a `parametrize` consolidation, because consolidation keeps the names.

**It executes nothing, and needs no exception to §2.1.** The repo's `tests` gate already runs at `base_sha` to build the baseline and again at head on every attempt. The names do not have to be fetched, only *reported*: the contract gains an optional `collected` field, the `tests` gate fills it, and core subtracts two lists it is already holding. Unlike `revert`, core invokes nothing here — it reads a field of a gate result, which is §2.1's original sentence rather than the exception to it. A repo whose runner cannot enumerate omits the field and `census` reports `skip`.

The two sides are not symmetric. No names at base is `skip` — nothing to compare. Names at base and none at head is `error`: a suite that enumerated before the task and stopped after it is grounds to distrust the comparison, not to report every test as deleted. A head `tests` that errored has already aborted the attempt before `census` is consulted, so a truncated collection can never be read as a mass deletion.

A test that leaves collection by any route is caught, including one moved behind a marker the run deselects. That is deliberate: silencing and deleting have the same effect on the suite, and `census` measures the suite.
```

- [ ] **Step 3: Add the `census` row to the gate-role table**

In the table at line ~621, insert directly after the `integrity` row:

```markdown
| `census` | **core** | yes | collected test names at `base_sha` vs head (below) |
```

- [ ] **Step 4: Add the `collected` field to the contract prose**

In §5.4, after the paragraph beginning "**`tool` is what distinguishes**", add:

```markdown
**`collected` is optional, and only `census` reads it.** A gate may report the identifiers it enumerated — for a test runner, its node ids. Core treats them as opaque strings: it never splits one, never assumes a separator, never infers a path from one. Absence is not a failure; it means the runner does not enumerate, and `census` reports `skip`. Unlike `tool`, this field is not a trust signal — it is data one core gate subtracts, and it is transient: `gate_results` has no column for it, so the comparison happens in memory within a run.
```

- [ ] **Step 5: Update the §2.1 concern table**

Replace the `integrity` row (line ~140) and add one:

```markdown
| `integrity` gate logic | **Core**, patterns from repo | "Was a suppression added, or gate config edited?" is universal; *what a suppression comment looks like* is not |
| `census` gate | **Core** | Subtracts two lists of names the repo's `tests` gate already reported — reads a gate result, invokes nothing |
```

- [ ] **Step 6: Extend §2.1's "seam to watch" paragraph**

Append one sentence to the paragraph beginning "**The seam to watch.**":

```markdown
And before reaching for `revert`'s exception, ask the cheaper question first: *does a gate the repo already declares produce this data?* `census` needed collected test names and got them by adding a field to a result that was already being returned, which is not an exception to the boundary at all.
```

- [ ] **Step 7: Add the appendix**

Append after Appendix L, with the next available appendix letter (`M`), and check the tail of `DESIGN.md` first in case one has been added since. Principles 45–51 are taken; the new one is **52**.

```markdown
## Appendix M — rev 15: what running the rejected gate found

Backlog item 1 said to read `SA-0004`'s rejected patch and its review before writing anything. Executing it as well took twenty minutes and returned three corrections, one of which nothing had recorded. Full record in `docs/evidence/2026-08-22-integrity-rejected-gate-measured.md`.

**The batch tree holds a later patch than the one Appendix K reviewed.** `rebuttal.json` records `head_moved: true`: the implementer changed the removal check during REBUT and the lens withdrew its blocker. Appendix K describes the code as applied and reviewed; the export is one fix past it. Both are honest about different artifacts, which is the shelf-life problem of Appendix K's own "patches perish" note arriving in a second form.

- **The `\ No newline at end of file` defect is already fixed.** All four positions git emits the marker parse cleanly. The backlog line claiming a branch sits in the wrong place is struck.
- **The removal check is run adjacency, not net line count.** So the `parametrize` false positive is gone — and the evasion is *cheaper* than Appendix K says, not harder. Not a comment longer than the test: one adjacent added line of any content, because the gate never asks what the added line says.
- **The suppression scan fails this repository's own merges.** Substring matching over every added line in every file means prose containing a token fails. `d1141d0`, the merge of PR #5, returns `fail` on two docstrings that quote `@pytest.mark.skip` while explaining that a critic's claim routinely quotes it. This is also what the "sixteen violations on its own pull request" were.

52. **When a check keeps needing a better heuristic, the question is in the wrong coordinate system.** Three rewrites of "was a test removed?" against diff text produced three different wrong answers, because the diff does not contain the answer — it contains a shadow of it. The set of collected tests contains it exactly, and comparing two sets needs no heuristic at all. The tell is not that a heuristic is imperfect; it is that each repair moves the failure somewhere else rather than shrinking it.

The corollary is the cheaper half: **the data a core gate needs may already be in a result it is holding.** Item 1 assumed test-set comparison required `revert`'s §2.1 exception — core invoking the repo's `tests` gate twice more. It did not. The baseline and head suites already run `tests`; the names needed reporting, not fetching, and the whole exception dissolved into one optional field.
```

- [ ] **Step 8: Verify no renumbering happened**

Run: `git diff DESIGN.md | grep -E '^-.*^(#{2,4} [0-9]|\| \`)' | head`
Expected: no removed section headings. Removed table rows are fine (the `integrity` row is replaced in place).

- [ ] **Step 9: Commit**

```bash
git add DESIGN.md
git commit -m "docs(design): integrity keeps what a diff can answer, census takes the rest"
```

---

### Task 2: `collected` on `GateResult`

One optional field. Nothing reads it yet — Task 4 does.

**Files:**
- Modify: `saffron/gates/contract.py:33-47` (the `GateResult` model)
- Test: `tests/test_saffron_gates.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `GateResult.collected: list[str] | None`, default `None`. Read by `census_gate` (Task 4), written by `.saffron/gates/tests.py` (Task 3).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_saffron_gates.py`:

```python
def test_a_gate_may_report_the_names_it_collected():
    raw = json.dumps(
        {
            "gate": "tests",
            "status": "pass",
            "tool": "pytest 8.3.2",
            "collected": ["tests/test_a.py::test_one", "tests/test_a.py::test_two"],
        }
    )
    result = parse_gate_json(raw, "tests")
    assert result.collected == [
        "tests/test_a.py::test_one",
        "tests/test_a.py::test_two",
    ]


def test_a_gate_that_reports_no_names_is_not_a_gate_that_collected_none():
    """`None` and `[]` are different facts: a runner that does not enumerate,
    versus a suite that is genuinely empty. `census` skips on the first and
    would report every base name removed on the second."""
    result = parse_gate_json(json.dumps({"gate": "lint", "status": "pass"}), "lint")
    assert result.collected is None
```

Check the file's existing imports; add `json` and `parse_gate_json` only if absent.

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_saffron_gates.py -k collected -v`
Expected: FAIL — `assert None == ['tests/test_a.py::test_one', ...]`, because pydantic ignores the unknown key.

- [ ] **Step 3: Add the field**

In `saffron/gates/contract.py`, inside `GateResult`, directly after the `tool` docstring and before `failures`:

```python
    collected: list[str] | None = None
    """Identifiers this gate enumerated — for a test runner, its node ids.

    Opaque to core: never split, never parsed, never assumed to contain a
    path (§2.1). Only `census` reads it. `None` means the runner does not
    enumerate, which is a `skip`; `[]` means it enumerated nothing, which is
    not the same fact (§5.4)."""
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_saffron_gates.py -k collected -v`
Expected: PASS, 2 tests.

- [ ] **Step 5: Full suite, then commit**

```bash
make check
git add saffron/gates/contract.py tests/test_saffron_gates.py
git commit -m "feat(contract): a gate may report the names it enumerated"
```

---

### Task 3: the repo's `tests` gate reports its node ids

Repo-side, in `.saffron/`. This is the half that would be rewritten per repo; core learns nothing from it.

**Files:**
- Modify: `.saffron/gates/tests.py`
- Test: manual, by running the gate — it is a standalone script, not importable, and the repo has no harness for `.saffron/gates/*`.

**Interfaces:**
- Consumes: `GateResult.collected` from Task 2.
- Produces: a `collected` key in the `tests` gate's JSON — a list of pytest node ids, or the key absent when collection failed.

- [ ] **Step 1: Add the collection step**

In `.saffron/gates/tests.py`, after the block that computes `subset` and before the `proc = subprocess.run([...])` that runs the suite, insert:

```python
# §5.4's `census` compares the names collected before the task against the
# names collected after. `-q --collect-only` prints one node id per line;
# 0.38s against this suite, measured, against a full run of ~36s.
#
# Same argv as the run below, so both see the same selection — pyproject's
# `-m "not cell"` deselects thirteen tests, and a census comparing a
# deselected list against a full one would report every cell test removed.
collect = subprocess.run(
    ["pytest", "-q", "--collect-only", "-p", "no:cacheprovider", *subset],
    capture_output=True,
    text=True,
)
# A collection that failed reports no names at all rather than a short list:
# a partial census is a mass deletion (§5.4, "partial results are not
# results"). `census` turns names-at-base and none-at-head into `error`.
collected = (
    [line for line in collect.stdout.splitlines() if "::" in line]
    if collect.returncode == 0
    else None
)
```

- [ ] **Step 2: Attach it to every result that ran the suite**

The `tests` gate has five `emit(...)` calls. Add `"collected": collected` to **only the final one** — the `pass`/`fail` result. The four `error` paths must not carry it: an errored gate produced no trustworthy result, and a `collected` on an `error` invites a future reader to use it.

The final `emit` becomes:

```python
emit(
    {
        "gate": "tests",
        "status": "fail" if failures else "pass",
        "tool": tool,
        "collected": collected,
        "failures": failures,
        "summary": summary or f"exit {proc.returncode}",
    }
)
```

- [ ] **Step 3: Run the gate and read its output**

Run:
```bash
uv run python .saffron/gates/tests.py 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['status'], d['tool'], len(d['collected']), d['collected'][0])"
```
Expected: `pass pytest <version> 464 tests/test_agent_runner.py::test_assistant_text_becomes_a_text_event` — the count matching `uv run pytest --collect-only -q | tail -1`.

- [ ] **Step 4: Verify a failed collection reports no names**

Run:
```bash
echo "def test_broken(:" > tests/test_zz_broken.py
uv run python .saffron/gates/tests.py 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['status'], d.get('collected'))"
rm tests/test_zz_broken.py
```
Expected: `collected` is `None` (or the gate reports `error` before emitting it — either is correct; what must not happen is a short list). Confirm `tests/test_zz_broken.py` is gone afterwards.

- [ ] **Step 5: Commit**

```bash
make check
git add .saffron/gates/tests.py
git commit -m "feat(gates): the tests gate reports the node ids it collected"
```

---

### Task 4: the `census` core gate

**Files:**
- Create: `saffron/gates/core/census.py`
- Test: `tests/test_census.py`

**Interfaces:**
- Consumes: `GateResult.collected` (Task 2).
- Produces: `census_gate(base: list[GateResult], head: list[GateResult]) -> GateResult`. Called by `_suite` in Task 6.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_census.py`:

```python
from __future__ import annotations

from saffron.gates.contract import GateResult
from saffron.gates.core.census import census_gate


def _tests(*names: str) -> GateResult:
    return GateResult(
        gate="tests", status="pass", tool="pytest 8.3.2", collected=list(names)
    )


def test_a_name_that_disappeared_fails_and_names_itself():
    result = census_gate(
        base=[_tests("t.py::test_a", "t.py::test_b")], head=[_tests("t.py::test_a")]
    )
    assert result.status == "fail"
    assert [f.file for f in result.failures] == ["t.py::test_b"]
    assert result.failures[0].code == "removed-test"


def test_a_test_renamed_out_of_collection_is_a_removal():
    """The case no diff-reading version could see: the body survives, nothing
    is deleted, and the test never runs again (Appendix M)."""
    result = census_gate(
        base=[_tests("t.py::test_b")], head=[_tests("t.py::check_b")]
    )
    assert result.status == "fail"
    assert [f.file for f in result.failures] == ["t.py::test_b"]


def test_a_parametrize_consolidation_that_keeps_the_names_passes():
    result = census_gate(
        base=[_tests("t.py::test_a", "t.py::test_b")],
        head=[_tests("t.py::test_ab[1]", "t.py::test_ab[2]", "t.py::test_a", "t.py::test_b")],
    )
    assert result.status == "pass"


def test_added_tests_alone_pass():
    result = census_gate(
        base=[_tests("t.py::test_a")], head=[_tests("t.py::test_a", "t.py::test_new")]
    )
    assert result.status == "pass"


def test_no_names_at_base_skips():
    """The baseline call, and a runner that does not enumerate. Both are a
    gate with nothing to compare, not a gate with nothing to report."""
    assert census_gate(base=[], head=[_tests("t.py::test_a")]).status == "skip"


def test_names_at_base_and_none_at_head_errors():
    """A suite that enumerated before the task and stopped after it. Reporting
    every test removed would charge the task for the toolchain (§5.4)."""
    result = census_gate(
        base=[_tests("t.py::test_a")],
        head=[GateResult(gate="tests", status="pass", tool="pytest 8.3.2")],
    )
    assert result.status == "error"
    assert result.failures == []


def test_an_empty_collection_at_head_is_a_removal_not_an_error():
    """`[]` and `None` are different facts: the runner ran and found nothing."""
    result = census_gate(
        base=[_tests("t.py::test_a")],
        head=[GateResult(gate="tests", status="pass", tool="pytest 8.3.2", collected=[])],
    )
    assert result.status == "fail"
    assert [f.file for f in result.failures] == ["t.py::test_a"]


def test_the_gate_names_no_role_it_reads_whatever_reported():
    """Core does not know which role enumerates; §2.1. A repo reporting from
    a gate called anything else is read the same way."""
    other = GateResult(gate="spec-suite", status="pass", collected=["a::b"])
    assert census_gate(base=[other], head=[]).status == "error"


def test_it_executes_nothing_so_it_claims_no_tool():
    assert census_gate(base=[], head=[]).tool is None


def test_removed_names_are_reported_in_a_stable_order():
    result = census_gate(
        base=[_tests("t.py::test_c", "t.py::test_a", "t.py::test_b")], head=[_tests()]
    )
    assert [f.file for f in result.failures] == [
        "t.py::test_a",
        "t.py::test_b",
        "t.py::test_c",
    ]
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_census.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'saffron.gates.core.census'`.

- [ ] **Step 3: Write the gate**

Create `saffron/gates/core/census.py`:

```python
"""The `census` gate: which tests existed before, and which exist now? (§5.4)

Core, and it executes nothing. The repo's `tests` gate already runs at
`base_sha` to build the baseline and again at head on every attempt, so the
collected names do not have to be fetched — only reported. Core subtracts two
lists it is already holding, which is §2.1's original rule rather than
`revert`'s exception to it (Appendix M).

Every name is opaque: never split, never parsed, never assumed to contain a
path or a separator. A runner reporting `tests/test_x.py::test_b` and one
reporting `pkg.TestFoo` are read identically, and neither teaches core
anything about a language.
"""

from __future__ import annotations

from saffron.gates.contract import Failure, GateResult


def _collected(results: list[GateResult]) -> list[str] | None:
    """Every name any gate enumerated, or `None` if none reported.

    Core does not name the `tests` role here. A gate reports `collected` or it
    does not; which role it fills is the repo's business (§2.1). Reporting
    gates are unioned, so a repo splitting its suite across two of them needs
    no special case.
    """
    reported = [r.collected for r in results if r.collected is not None]
    if not reported:
        return None
    return [name for names in reported for name in names]


# ponytail: a task that legitimately removes a test cannot pass — the `touches`
# exemption binds `integrity` and deliberately not this gate (§5.4), so there is
# no override. The upgrade path is a spec field (`may_remove_tests`, or a
# per-name allowance); unbuilt because no task has needed one, and schema
# designed against a guess is schema designed wrong.


def census_gate(base: list[GateResult], head: list[GateResult]) -> GateResult:
    """Names collected at `base_sha`, minus names collected at head.

    The two sides are deliberately not symmetric. No names at base is a gate
    with nothing to compare; no names at head after some at base is a suite
    that stopped enumerating, which is infrastructure and charged to nobody
    (§5.4) — never a report that every test was deleted.
    """
    before = _collected(base)
    after = _collected(head)

    if before is None:
        return GateResult(
            gate="census",
            status="skip",
            summary="no gate reported collected tests at base_sha",
        )
    if after is None:
        return GateResult(
            gate="census",
            status="error",
            summary=(
                f"{len(before)} tests were enumerated at base_sha and none at "
                "head; the comparison is not trustworthy"
            ),
        )

    # A set, unlike the baseline subtraction it sits beside: failure identities
    # collide legitimately and must be counted (§5.4), but a name is unique in
    # a suite by construction. Sorted so the failure order does not depend on
    # the runner's.
    removed = sorted(set(before) - set(after))
    if not removed:
        return GateResult(
            gate="census",
            status="pass",
            summary=f"{len(after)} tests collected, none of {len(before)} removed",
        )

    return GateResult(
        gate="census",
        status="fail",
        failures=[
            Failure(
                file=name,
                code="removed-test",
                message="collected at base_sha, absent at head",
            )
            for name in removed
        ],
        summary=f"{len(removed)} of {len(before)} collected tests no longer collected",
    )
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_census.py -v`
Expected: PASS, 10 tests.

- [ ] **Step 5: Commit**

```bash
make check
git add saffron/gates/core/census.py tests/test_census.py
git commit -m "feat(gates): census answers test removal where the answer lives"
```

---

### Task 5: `integrity`, diff-only and two checks

Port from `~/.saffron/batches/v0/SA-0004/patch.diff` — apply it to a scratch directory to read it (`git init` a temp dir, `git apply`), do not copy it into the repo wholesale. `_runs`, `_unreplaced_removals` and `removed-test` do not come across. Read `docs/evidence/2026-08-22-integrity-rejected-gate-measured.md` first.

**Files:**
- Create: `saffron/gates/core/integrity.py`
- Test: `tests/test_integrity.py`

**Interfaces:**
- Consumes: `matches` from `saffron.gates.core.scope`, `IntegrityPatterns` from `saffron.repos.policy`, `DIFF_FLAGS` from `saffron.cell.worktree` (tests only).
- Produces: `integrity_gate(diff: str, patterns: IntegrityPatterns, touches: list[str]) -> GateResult`. Called by `_suite` in Task 6.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_integrity.py`. Fixtures come from real `git diff`, never synthetic strings — synthetic diffs are what let the rejected gate's thirty-one tests agree with its blind spots (principle 45).

```python
from __future__ import annotations

import subprocess

from saffron.cell import worktree
from saffron.gates.core.integrity import integrity_gate
from saffron.repos.policy import IntegrityPatterns

PATTERNS = IntegrityPatterns(
    test_paths=["tests/**"],
    suppressions=["@pytest.mark.skip", "# type: ignore"],
    gate_config=["pyproject.toml"],
)

TESTS = "def test_a():\n    assert 1 == 1\n\n\ndef test_b():\n    assert 2 == 2\n"


def _repo(tmp_path, files):
    run = lambda *a: subprocess.run(a, cwd=tmp_path, check=True, capture_output=True)  # noqa: E731
    run("git", "init", "-q", "-b", "main")
    run("git", "config", "user.email", "t@example.com")
    run("git", "config", "user.name", "t")
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    run("git", "add", "-A")
    run("git", "commit", "-qm", "base")
    return run


def _diff(tmp_path, run, changes):
    for name, content in changes.items():
        path = tmp_path / name
        if content is None:
            path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    run("git", "add", "-A")
    return subprocess.run(
        ["git", "diff", "--cached", *worktree.DIFF_FLAGS],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_an_added_suppression_fails_and_names_the_token(tmp_path):
    run = _repo(tmp_path, {"src/a.py": "x = 1\n"})
    diff = _diff(tmp_path, run, {"src/a.py": "x = 1  # type: ignore\n"})
    result = integrity_gate(diff, PATTERNS, touches=["src/b.py"])
    assert result.status == "fail"
    assert result.failures[0].code == "added-suppression"
    assert "# type: ignore" in result.failures[0].message


def test_a_suppression_in_a_file_the_spec_declared_is_exempt(tmp_path):
    """The only defence a substring scan has against prose: a docstring that
    quotes a token is a use of it to core, and the file is in `touches` by
    construction or `scope` would have failed first (Appendix M)."""
    run = _repo(tmp_path, {"src/a.py": "x = 1\n"})
    diff = _diff(tmp_path, run, {"src/a.py": 'x = 1\n"""quotes # type: ignore"""\n'})
    assert integrity_gate(diff, PATTERNS, touches=["src/a.py"]).status == "pass"


def test_a_gate_config_edit_fails(tmp_path):
    run = _repo(tmp_path, {"pyproject.toml": "[tool.x]\n"})
    diff = _diff(tmp_path, run, {"pyproject.toml": "[tool.x]\ny = 1\n"})
    result = integrity_gate(diff, PATTERNS, touches=["src/a.py"])
    assert result.status == "fail"
    assert result.failures[0].code == "gate-config-changed"


def test_a_gate_config_edit_the_spec_declared_is_exempt(tmp_path):
    run = _repo(tmp_path, {"pyproject.toml": "[tool.x]\n"})
    diff = _diff(tmp_path, run, {"pyproject.toml": "[tool.x]\ny = 1\n"})
    assert integrity_gate(diff, PATTERNS, touches=["pyproject.toml"]).status == "pass"


def test_a_deleted_test_is_not_this_gate_s_business(tmp_path):
    """`census` owns removal. A diff-reading gate answering it was wrong three
    times in three different ways (Appendix M, principle 52)."""
    run = _repo(tmp_path, {"tests/test_x.py": TESTS})
    diff = _diff(tmp_path, run, {"tests/test_x.py": None})
    assert integrity_gate(diff, PATTERNS, touches=["src/a.py"]).status == "pass"


def test_a_suppression_on_a_removed_line_does_not_count(tmp_path):
    run = _repo(tmp_path, {"src/a.py": "x = 1  # type: ignore\n"})
    diff = _diff(tmp_path, run, {"src/a.py": "x = 1\n"})
    assert integrity_gate(diff, PATTERNS, touches=["src/b.py"]).status == "pass"


def test_a_suppression_on_a_context_line_does_not_count(tmp_path):
    run = _repo(tmp_path, {"src/a.py": "x = 1  # type: ignore\ny = 2\n"})
    diff = _diff(tmp_path, run, {"src/a.py": "x = 1  # type: ignore\ny = 3\n"})
    assert integrity_gate(diff, PATTERNS, touches=["src/b.py"]).status == "pass"


def test_a_file_with_no_trailing_newline_parses(tmp_path):
    """Four positions git emits `\\ No newline at end of file`; the reviewed
    patch died on one and had no test (Appendix K). Characterization."""
    run = _repo(tmp_path, {"src/a.py": "x = 1"})
    diff = _diff(tmp_path, run, {"src/a.py": "x = 2"})
    assert "\\ No newline" in diff
    assert integrity_gate(diff, PATTERNS, touches=["src/b.py"]).status == "pass"


def test_a_marker_between_a_removal_and_an_addition_parses(tmp_path):
    run = _repo(tmp_path, {"src/a.py": "x = 1"})
    diff = _diff(tmp_path, run, {"src/a.py": "x = 1\n"})
    assert integrity_gate(diff, PATTERNS, touches=["src/b.py"]).status != "error"


def test_a_bent_prefix_errors_rather_than_passing(tmp_path):
    run = _repo(tmp_path, {"src/a.py": "x = 1\n"})
    run("git", "config", "diff.srcPrefix", "x/")
    run("git", "config", "diff.dstPrefix", "y/")
    for name, content in {"src/a.py": "x = 1  # type: ignore\n"}.items():
        (tmp_path / name).write_text(content)
    run("git", "add", "-A")
    bent = subprocess.run(
        ["git", "diff", "--cached"], cwd=tmp_path, capture_output=True, text=True
    ).stdout
    assert integrity_gate(bent, PATTERNS, touches=[]).status == "error"


def test_a_binary_section_is_unreadable_not_unchanged(tmp_path):
    """A `-diff` gitattribute renders a text file as `Binary files ... differ`,
    hiding content but not paths. A file whose added lines cannot be read is a
    file whose suppressions cannot be counted (BACKLOG item 2's close)."""
    run = _repo(tmp_path, {"src/a.py": "x = 1\n", ".gitattributes": "*.py -diff\n"})
    diff = _diff(tmp_path, run, {"src/a.py": "x = 1  # type: ignore\n"})
    assert "Binary files" in diff
    result = integrity_gate(diff, PATTERNS, touches=[])
    assert result.status == "error"
    assert "src/a.py" in result.summary


def test_a_declared_binary_file_is_exempt_rather_than_an_abort(tmp_path):
    """The exemption is applied before the unreadable check, so a committed
    binary fixture the spec named does not abort the attempt. It also proves
    the path survives: `Binary files ...` replaces the `---`/`+++` headers, so
    a gate reading paths only from those would exempt nothing."""
    run = _repo(tmp_path, {"src/a.py": "x = 1\n", ".gitattributes": "*.py -diff\n"})
    diff = _diff(tmp_path, run, {"src/a.py": "x = 1  # type: ignore\n"})
    assert integrity_gate(diff, PATTERNS, touches=["src/a.py"]).status == "pass"


def test_an_empty_diff_passes():
    assert integrity_gate("", PATTERNS, touches=[]).status == "pass"


def test_no_declared_patterns_skips():
    empty = IntegrityPatterns(test_paths=[], suppressions=[], gate_config=[])
    assert integrity_gate("", empty, touches=[]).status == "skip"
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_integrity.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'saffron.gates.core.integrity'`.

- [ ] **Step 3: Write the gate**

Create `saffron/gates/core/integrity.py`. The parser — `_FILE_HEADER`, `_OLD_PATH`, `_NEW_PATH`, `_HUNK_HEADER`, `_DiffError`, `_FileDiff`, `_split_blocks`, `_parse_block` — is carried over unchanged from the rejected patch, because review was explicit that it is correct and measurement agrees: count-driven hunk consumption, line numbers from the `@@` header, `error` distinct from `fail`, and the pinned-prefix refusal. Three things change: `_runs` and `_unreplaced_removals` are gone, `_parse_block` raises on a binary section, and `integrity_gate` takes `touches`.

```python
"""The `integrity` gate: was a suppression added, or gate config edited? (§5.4)

Core, because both questions are about diff text and are identical in every
language — no execution of repo code, the same shape as `scope.py`. The
*vocabulary* is not universal, so `IntegrityPatterns` arrives from the repo's
`.saffron/policy.yaml` (§2.1) rather than being guessed here.

**Removal is not asked here.** "Was an existing test removed?" is a question
about which tests exist, and a diff is a lossy projection of that: three
diff-shaped versions of the check were written and all three were wrong, in
three different ways (Appendix M, principle 52). `census` answers it exactly,
by subtracting two sets of collected names.

The `touches` exemption binds both surviving checks. For a suppression or a
gate-config edit the signal is *this file changed at all*, and a spec whose
`touches` names the file has authorized exactly that. It is also the only
defence a substring scan has against prose: a docstring quoting a token is a
use of it to core.
"""

from __future__ import annotations

import re

from saffron.gates.contract import Failure, GateResult
from saffron.gates.core.scope import matches
from saffron.repos.policy import IntegrityPatterns

# Same pinned-prefix contract as scope.py: the host runs `git diff` with
# `worktree.DIFF_FLAGS`, so every file header must be exactly this shape.
# Anything else means git did not honour the flags, and a gate that cannot
# recognise its own input reports `error` rather than a `pass` nobody checked.
_FILE_HEADER = re.compile(r'^diff --git (?:a/.+ b/.+|"a/.+" "b/.+")$')

# `--- a/path` / `--- /dev/null` and `+++ b/path` / `+++ /dev/null`, quoted or
# not. Only trusted before the first hunk of a block — after that an
# identical-looking line may be real content (a removed line whose own text
# starts with `--- `), not a path header.
_OLD_PATH = re.compile(r'^--- (?:"?a/(.+?)"?|/dev/null)$')
_NEW_PATH = re.compile(r'^\+\+\+ (?:"?b/(.+?)"?|/dev/null)$')

# `@@ -12,7 +12,9 @@ optional trailing context` — the only shape a hunk header
# is allowed to take. A `@@` line that does not match means the gate cannot
# trust where a hunk begins or ends.
_HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")

# A `-diff` gitattribute renders a *text* file this way: content hidden, path
# not. `scope` reads paths and is unaffected; this gate reads added lines, and
# a file whose added lines cannot be read is a file whose suppressions cannot
# be counted (BACKLOG item 2).
#
# Measured: this line *replaces* the `--- `/`+++ ` headers rather than joining
# them, so the path has to come from here or it does not arrive at all — and
# without a path the `touches` exemption cannot be applied to it.
_BINARY = re.compile(
    r'^Binary files (?:"?a/(.+?)"?|/dev/null) and (?:"?b/(.+?)"?|/dev/null) differ$'
)


class _DiffError(Exception):
    """The diff isn't the shape this gate is entitled to trust. → `error`."""

    def __init__(self, summary: str) -> None:
        self.summary = summary


class _FileDiff:
    __slots__ = ("old_path", "new_path", "hunks", "unreadable")

    def __init__(self, old_path: str | None, new_path: str | None) -> None:
        self.old_path = old_path
        self.new_path = new_path
        # Content hidden as binary. Recorded rather than raised, so that a file
        # the spec declared in `touches` can be exempted before it is judged —
        # a committed PNG fixture must not abort the attempt.
        self.unreadable = False
        # Each hunk: a list of (kind, content, new_line) where kind is one of
        # "+"/"-"/" ", and new_line is the line's number in the post-image —
        # only meaningful (not None) for "+" and " " lines.
        self.hunks: list[list[tuple[str, str, int | None]]] = []

    @property
    def path(self) -> str:
        """The path an operator would recognise: new side, or old if deleted."""
        return self.new_path if self.new_path is not None else (self.old_path or "")

    def matches_any(self, patterns: list[str]) -> bool:
        candidates = [p for p in (self.old_path, self.new_path) if p is not None]
        return any(
            matches(candidate, pattern)
            for candidate in candidates
            for pattern in patterns
        )


def _split_blocks(diff: str) -> list[str]:
    """Split on `diff --git` header lines, validating each as we go."""
    lines = diff.splitlines()
    starts = []
    for index, line in enumerate(lines):
        if line.startswith("diff --git "):
            if not _FILE_HEADER.match(line):
                raise _DiffError(
                    f"diff prefixes are not a/ b/, so paths are unreadable: {line[:120]}"
                )
            starts.append(index)
    blocks = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        blocks.append("\n".join(lines[start:end]))
    return blocks


def _parse_block(block: str) -> _FileDiff:
    lines = block.splitlines()
    old_path: str | None = None
    new_path: str | None = None
    saw_hunk = False
    file_diff: _FileDiff | None = None
    current: list[tuple[str, str, int | None]] | None = None
    new_line = 0

    for line in lines:
        if not saw_hunk:
            if binary := _BINARY.match(line):
                # Measured: git emits this before any `@@`, and in place of the
                # path headers — so the paths come from the match itself.
                file_diff = _FileDiff(binary.group(1), binary.group(2))
                file_diff.unreadable = True
                return file_diff
            if line.startswith("--- ") and old_path is None:
                header = _OLD_PATH.match(line)
                if header is None:
                    raise _DiffError(f"unreadable old-file header: {line[:120]}")
                old_path = header.group(1)
                continue
            if line.startswith("+++ ") and new_path is None:
                header = _NEW_PATH.match(line)
                if header is None:
                    raise _DiffError(f"unreadable new-file header: {line[:120]}")
                new_path = header.group(1)
                continue

        if line.startswith("@@"):
            if file_diff is None:
                file_diff = _FileDiff(old_path, new_path)
            header = _HUNK_HEADER.match(line)
            if header is None:
                raise _DiffError(f"unreadable hunk header: {line[:120]}")
            saw_hunk = True
            new_line = int(header.group(1))
            current = []
            file_diff.hunks.append(current)
            continue

        if not saw_hunk or current is None:
            continue  # mode lines, index lines, "rename from/to", etc.

        if line.startswith("+"):
            current.append(("+", line[1:], new_line))
            new_line += 1
        elif line.startswith("-"):
            current.append(("-", line[1:], None))
        elif line.startswith(" "):
            current.append((" ", line[1:], new_line))
            new_line += 1
        elif line.startswith("\\"):
            pass  # "\ No newline at end of file" — measured in all four positions
        else:
            raise _DiffError(f"unrecognised hunk content line: {line[:120]}")

    if file_diff is None:
        file_diff = _FileDiff(old_path, new_path)
    return file_diff


def integrity_gate(
    diff: str, patterns: IntegrityPatterns, touches: list[str]
) -> GateResult:
    """`pass`/`fail` over a unified diff, the repo's patterns, and the spec's
    `touches`.

    `diff` is the export the reviewer reads, produced with the pinned
    `worktree.DIFF_FLAGS` — the same contract `scope_gate` relies on. A diff
    this gate cannot parse is `error`, never a `pass` nobody checked (§5.4).
    """
    if not patterns.suppressions and not patterns.gate_config:
        return GateResult(
            gate="integrity",
            status="skip",
            summary="no integrity patterns declared",
        )

    try:
        files = [_parse_block(block) for block in _split_blocks(diff)]
    except _DiffError as exc:
        return GateResult(gate="integrity", status="error", summary=exc.summary)

    failures: list[Failure] = []

    for file_diff in files:
        # The spec authorized this file, and both checks below ask only
        # whether the file changed. Removal is `census`'s, and `census` is
        # deliberately not exempt (§5.4).
        if any(matches(file_diff.path, pattern) for pattern in touches):
            continue

        # Checked after the exemption, deliberately: a committed binary fixture
        # the spec declared is not a gate that cannot read its input. What is
        # left here is content hidden in a file nobody authorized changing, and
        # unreadable is not the same fact as unchanged (BACKLOG item 2).
        #
        # ponytail: a genuine binary outside `touches` still aborts the attempt.
        # The upgrade path is `policy.yaml` declaring binary paths, or a
        # `--numstat` cross-check; not worth building before a repo has one.
        if file_diff.unreadable:
            return GateResult(
                gate="integrity",
                status="error",
                summary=(
                    f"content hidden as binary, so added lines are unreadable: "
                    f"{file_diff.path}"
                ),
            )

        if patterns.gate_config and file_diff.matches_any(patterns.gate_config):
            failures.append(
                Failure(
                    file=file_diff.path,
                    code="gate-config-changed",
                    message=f"changed gate configuration: {file_diff.path}",
                )
            )

        if patterns.suppressions:
            for hunk in file_diff.hunks:
                for kind, content, line_number in hunk:
                    if kind != "+":
                        continue
                    for token in patterns.suppressions:
                        if token in content:
                            failures.append(
                                Failure(
                                    file=file_diff.path,
                                    line=line_number,
                                    code="added-suppression",
                                    message=f"added suppression {token!r} in {file_diff.path}",
                                )
                            )

    if not failures:
        return GateResult(
            gate="integrity",
            status="pass",
            summary=f"{len(files)} changed files clean of suppression and gate-config edits",
        )

    return GateResult(
        gate="integrity",
        status="fail",
        failures=failures,
        summary=f"{len(failures)} integrity violation(s) across {len(files)} changed files",
    )
```

Note `IntegrityPatterns.test_paths` is now unread by this module. Leave the field on the model — `.saffron/policy.yaml` declares it and removing it is a policy-schema change this task does not own. If `make check` reports it unused, that is a lint on the model, not on this gate; do not delete the field to silence it.

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_integrity.py -v`
Expected: PASS, 14 tests.

- [ ] **Step 5: Verify the gate passes this repository's own merge**

The measured defect from Appendix M. Run:

```bash
uv run python -c "
import pathlib, subprocess
from saffron.gates.core.integrity import integrity_gate
from saffron.repos.policy import load_policy
from saffron.cell.worktree import DIFF_FLAGS
policy, _ = load_policy(pathlib.Path('.'))
diff = subprocess.run(['git','diff',*DIFF_FLAGS,'d1141d0^','d1141d0'],
                      capture_output=True, text=True).stdout
r = integrity_gate(diff, policy.integrity, touches=['saffron/report/pr_body.py','tests/test_report.py'])
print(r.status, [f.code for f in r.failures])
"
```
Expected: `pass []`. The rejected gate returns `fail ['added-suppression','added-suppression']` on this diff.

- [ ] **Step 6: Commit**

```bash
make check
git add saffron/gates/core/integrity.py tests/test_integrity.py
git commit -m "feat(gates): integrity keeps the two checks a diff can answer"
```

---

### Task 6: wire both gates into the suite

**Files:**
- Modify: `saffron/cell/session.py:537-560` (`_suite` and the baseline call), `:726-733` (`_run_gates`)
- Test: `tests/test_session.py`

**Interfaces:**
- Consumes: `census_gate` (Task 4), `integrity_gate` (Task 5).
- Produces: nothing new. `repair_loop`'s signature is **unchanged** — `_run_gates` is a closure defined after `baseline`, so it captures it directly and `run_gates: Callable[[], list[GateResult]]` stays as it is.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_session.py`, matching the file's existing fixture style for `_suite`-level tests:

```python
def test_the_baseline_suite_skips_census_because_there_is_no_base_yet():
    """`_suite([])` is the baseline call. A census with nothing to compare is
    a skip, not a report that every test was removed."""
    from saffron.gates.core.census import census_gate

    assert census_gate(base=[], head=[]).status == "skip"


def test_census_joins_the_head_suite_and_not_the_baseline():
    """A head-only gate: `suite_drift` ignores it (baseline.py's `was is None`
    branch) and `subtract_baseline` counts its failures as new, both without
    changes."""
    from saffron.gates.baseline import subtract_baseline, suite_drift
    from saffron.gates.contract import Failure, GateResult

    baseline = [GateResult(gate="tests", status="pass", tool="pytest 8.3.2")]
    head = [
        GateResult(gate="tests", status="pass", tool="pytest 8.3.2"),
        GateResult(
            gate="census",
            status="fail",
            failures=[Failure(file="t.py::test_a", code="removed-test")],
        ),
    ]
    assert suite_drift(head, baseline) == []
    assert [n.gate for n in subtract_baseline(head, baseline)] == ["census"]
```

- [ ] **Step 2: Run to verify**

Run: `uv run pytest tests/test_session.py -k "census" -v`
Expected: the first FAILs on `ModuleNotFoundError` only if Task 4 was skipped; otherwise both PASS immediately. They are characterization tests over Tasks 4's gate and existing `baseline.py` behaviour — they pin the three claims Task 6's wiring rests on so a later change to `suite_drift` cannot silently break the census. If both pass on first run, that is correct; do not manufacture a failure.

- [ ] **Step 3: Give `_suite` the prior results**

In `saffron/cell/session.py`, change the `_suite` definition (line ~537) from `def _suite() -> list[GateResult]:` to:

```python
        def _suite(prior: list[GateResult]) -> list[GateResult]:
```

and extend its docstring's first line to `"""The repo's declared gates plus the core gates the host runs.`

Then replace the `return [...]` body with:

```python
            changed = worktree.changed_files(container, spec.base_sha)
            diff = worktree.export_patch(container, spec.base_sha)
            results = [
                # The diff goes with the paths: it is what proves the export the
                # reviewer will read still has the shape the host pinned.
                scope_gate(changed, spec.touches, diff=diff),
                integrity_gate(diff, policy.integrity, spec.touches),
                *run_suite(gates, cwd=repo, executor=executor),
            ]
            # Last, and given the whole suite: it reads `collected` off whatever
            # gate reported it, which means it has to run after them (§5.4).
            # `prior` is empty on the baseline call, and census skips.
            return [*results, census_gate(prior, results)]
```

- [ ] **Step 4: Update the three call sites**

Line ~560: `baseline = _suite()` becomes `baseline = _suite([])`.

Line ~727, inside `_run_gates`: `results = _suite()` becomes `results = _suite(baseline)`.

There is no third call — `_rebut_gates` calls `_run_gates`, not `_suite`. Confirm with `grep -n "_suite(" saffron/cell/session.py`; expected exactly three lines (the `def` and two calls).

- [ ] **Step 5: Add the imports**

These are **function-local**, not module-level. `_run_one_cell`'s body opens with a block of deferred imports at line ~421; `from saffron.gates.core.scope import scope_gate` is line 424. Add beside it, keeping the block's alphabetical order:

```python
    from saffron.gates.core.census import census_gate
    from saffron.gates.core.integrity import integrity_gate
    from saffron.gates.core.scope import scope_gate
```

Do not hoist any of them to module scope — the block is deferred deliberately, and moving one is a change this task does not own.

- [ ] **Step 6: Verify the comment above the baseline call is still true**

The comment at line ~558 reads "At base_sha the diff is empty, so `scope` passes with no failures". Extend it, because two more gates now run there:

```python
        # At base_sha the diff is empty, so `scope` and `integrity` pass with no
        # failures, and `census` has no prior to compare and skips — nothing for
        # the subtraction to cancel a real escape against.
```

- [ ] **Step 7: Run the full suite**

Run: `make check`
Expected: PASS. If `tests/test_session.py` has fixtures that call `_suite()` or stub `run_gates`, they need the new argument — fix them rather than reverting the signature.

- [ ] **Step 8: Commit**

```bash
git add saffron/cell/session.py tests/test_session.py
git commit -m "feat(session): the core gates that can actually fire now run in the cell"
```

---

### Task 7: close the backlog item and record what measurement changed

**Files:**
- Modify: `docs/BACKLOG.md:18-95` (item 1)
- Modify: `CLAUDE.md` — the invariants list

**Interfaces:**
- Consumes: everything above.
- Produces: no code symbols.

- [ ] **Step 1: Close item 1**

Append to item 1 in `docs/BACKLOG.md`, in the idiom item 2's close already uses (a bold `**Done, <date>.**` paragraph that says what was built *and* what the item's own text got wrong):

```markdown
**Done, 2026-08-22.** Split, and three of this item's claims were wrong —
measured, not re-reasoned (`docs/evidence/2026-08-22-integrity-rejected-gate-measured.md`,
Appendix M). The batch tree holds a **post-rebuttal** patch, one fix past the
one Appendix K reviewed. Defect A was already fixed in it: all four positions
git emits `\ No newline at end of file` parse cleanly, so there was nothing to
move and nothing to test. The removal check was run adjacency, not net line
count, so the `parametrize` false positive was already gone and "wrong in both
directions" no longer described the code — while the evasion was *cheaper* than
this item says, taking one adjacent added line of any content rather than a
comment longer than the test. And a defect nothing had recorded: the suppression
scan substring-matches every added line in every file, so `d1141d0` — this
repository's own merge of PR #5 — failed `integrity` on two docstrings that
quote `@pytest.mark.skip` while explaining that a critic's claim quotes it.

What shipped: `integrity` keeps suppressions and gate-config, both honouring the
`touches` exemption, and treats a `Binary files ... differ` section as
unreadable rather than unchanged. Test removal became `census`, a set
comparison of collected test names — which also catches a test renamed out of
collection, the case every diff-shaped version blessed. **It needed no §2.1
exception.** This item assumed core would have to invoke the `tests` gate the
way `revert` does; it does not, because the baseline and head suites already run
`tests`, so the names needed reporting rather than fetching. The contract gained
one optional field, `collected`, and core subtracts two lists it already holds.

Still open, deliberately: a task that *legitimately* removes a test cannot pass,
since the exemption does not bind `census`. The upgrade path is a spec field,
left unbuilt until a task needs it. And a genuine binary fixture trips
`integrity`'s unreadable-section rule; both ceilings carry `ponytail:` comments.
```

- [ ] **Step 2: Update `CLAUDE.md`'s invariants**

The "Invariants worth knowing before editing" list describes gates. Add one bullet after the "Baseline subtraction counts" bullet:

```markdown
- **`census` compares sets; the baseline subtraction counts.** They sit beside each
  other and the rule is opposite, for a reason: failure identities collide
  legitimately, so one baseline failure cancels one head failure — but a test name
  is unique in a suite, so removal is a set difference. Do not make them match.
```

And update the `saffron/gates/` layout line to name `census.py` and `integrity.py` alongside `scope`:

```markdown
  `baseline.py` subtracts pre-existing failures; `core/` holds the host-side gates
  (`scope`, `integrity` read the diff; `census` reads other gates' results).
```

- [ ] **Step 3: Verify the line budget**

`CLAUDE.md` has a stated ~200-line budget. Run: `wc -l CLAUDE.md`
Expected: still under 200. If it is over, promote a rule to a gate rather than trimming these.

- [ ] **Step 4: Commit**

```bash
make check
git add docs/BACKLOG.md CLAUDE.md
git commit -m "docs(backlog): item 1 closed, and three of its own claims corrected"
```

---

## Final verification

- [ ] `make check` passes.
- [ ] `uv run pytest tests/test_census.py tests/test_integrity.py -v` — 24 tests.
- [ ] `git diff main --stat -- saffron/replay.py` is empty: this sub-project touches no v0 code.
- [ ] `grep -rn "removed-test" saffron/gates/core/integrity.py` is empty — removal left this gate.
- [ ] `grep -rn "def test_\|::" saffron/gates/core/census.py` finds nothing outside docstrings — no language knowledge, no node-id parsing.
- [ ] `grep -c "" DESIGN.md` and confirm §5.4's numbered subsections are unchanged: `grep -n "^### 5\." DESIGN.md`.
- [ ] The success criterion from the spec's part 7, checked by hand: `census` fails a diff that renames `test_b` to `check_b`; `integrity` passes `d1141d0`; and `saffron/gates/core/integrity.py` is shorter than the 305-line file it replaces.
