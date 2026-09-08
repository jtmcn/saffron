# Lens Corpus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the lens harness eight fixtures carrying twelve declared defects and one aggregate number, so a prompt change can be read through something narrower than one fixture's noise.

**Architecture:** `harness/lens_scoring.py` keeps answering one question — did this run see this defect — unchanged. A new `harness/corpus.py` composes it: load every fixture under a root, calibrate them all before money is spent, score a pass across them, and render one aggregate. Two new scripts under `docs/evidence/scripts/` recover fixtures from the ledger and batch tree, and drive a pass over the corpus.

**Tech Stack:** Python 3.12, `uv`, pytest, pydantic (`GateResult`, `Finding`), `apple/container` via `saffron.cell.session`.

**Spec:** `docs/superpowers/specs/2026-09-08-lens-corpus-design.md`

## Global Constraints

- `harness/` is measurement, never shipped in `saffron/`. Nothing under `saffron/` may import it.
- Scripts that spend money live in `docs/evidence/scripts/`; the predicate they call lives in `harness/` where it is linted and tested.
- Fixture inputs are **frozen files on disk**, never rebuilt per pass. The thing being measured is the lens prompt; nothing else may vary.
- A new test is not trusted until it has been run against the unfixed code, or against a mutant that breaks the property.
- Commit subjects are lowercase `type(scope): what changed`, written as a sentence about the defect rather than the file.
- Every `docs/evidence/` record's published numbers are re-derived from committed run JSON by a test.
- Vocabulary is enforced: "cell" not "sandbox", "gate result" not "gate run". States in backticked caps, phases in bare caps.

## The corpus, as recovered

Every recorded `head_sha` is gone from live history. Head is the ledger's `pushed_sha`; base is the first ancestor where `git diff base..head` is byte-identical to the batch tree's `patch.diff`. All eight verified 2026-09-08.

| Spec | PR | base..head | Defects |
|---|---|---|---|
| SA-0045 | 115 | `2e563cf0..f9f007c4` | 1 |
| SA-0046 | 116 | `a79b680b..c71eeca9` | 1 |
| SA-0048 | 117 | `c71eeca9..64c71614` | 1 |
| SA-0050 | 121 | `5c103860..91f56c69` | 1 |
| SA-0054 | 123 | `fe39b41a..70091cd8` | 2 |
| SA-0055 | 131 | `aa8dfd17..e5a7cbe9` | 2 |
| SA-0062 | 154 | `91b6eda8..78a25a23` | 2 (shipped) |
| SA-0063 | 158 | `132a2f8d..f76931df` | 2 |

**SA-0063, not SA-0064.** The design named SA-0064 for item 86's two defects. That is wrong and this plan corrects it: `_notes` is *introduced* by SA-0063, whose diff touches `saffron/report/pr_body.py`; SA-0064's diff touches `package.py`, `tests/test_package.py` and `tests/test_session.py` and never reaches `pr_body.py`. A finding outside the diff cannot anchor, and an unanchored finding is never seen — so declared against SA-0064 both defects would score zero forever and read as a lens failure.

---

### Task 1: `load_corpus`, and a fixture with no defects is refused

**Files:**
- Create: `harness/corpus.py`
- Modify: `harness/lens_scoring.py` (in `load_fixture`, after `defects` is built)
- Test: `tests/test_corpus.py`, `tests/test_lens_scoring.py`

**Interfaces:**
- Consumes: `lens_scoring.load_fixture(root) -> Fixture`, `lens_scoring.FixtureError`
- Produces: `corpus.load_corpus(root: Path) -> list[Fixture]`, sorted by `spec_id`

- [ ] **Step 1: Write the failing test for `load_corpus`**

In `tests/test_corpus.py`:

```python
from pathlib import Path

import pytest

from harness import corpus, lens_scoring

FIXTURES = Path(__file__).parent.parent / "docs" / "evidence" / "fixtures"


def test_the_corpus_is_every_fixture_directory_under_the_root():
    """A directory, not a list in code: adding a fixture is a directory, and
    the harness is not edited to admit it."""
    loaded = corpus.load_corpus(FIXTURES)
    assert [f.spec_id for f in loaded] == sorted(f.spec_id for f in loaded)
    assert "SA-0062" in {f.spec_id for f in loaded}


def test_a_directory_without_a_fixture_toml_is_not_a_fixture(tmp_path):
    """`docs/evidence/fixtures/` may hold a README or a stray export; only a
    directory declaring itself is loaded."""
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "README.md").write_text("not a fixture")
    assert corpus.load_corpus(tmp_path) == []
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `uv run pytest tests/test_corpus.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'harness.corpus'`

- [ ] **Step 3: Write `harness/corpus.py`**

```python
"""A corpus of fixtures, and the one number a pass reports.

`lens_scoring` answers a question about one run and one defect. This composes
it across fixtures, because a prompt change cannot be read through one
fixture's noise (`docs/evidence/2026-09-08-lens-scoring-second-pass.md`: the
per-defect scores moved by a third between two passes that changed nothing
relevant, while the blocker count stayed identical).
"""

from __future__ import annotations

from pathlib import Path

from harness.lens_scoring import Fixture, load_fixture


def load_corpus(root: Path) -> list[Fixture]:
    """Every fixture under `root`, ordered by spec id.

    A directory declares itself a fixture by holding a `fixture.toml`; a
    README or a stray export beside them is not one. Ordered so a pass's
    fixtures, its output files and its table all agree without a caller
    sorting three times.
    """
    found = [
        load_fixture(child)
        for child in sorted(root.iterdir())
        if child.is_dir() and (child / "fixture.toml").is_file()
    ]
    return sorted(found, key=lambda fixture: fixture.spec_id)
```

- [ ] **Step 4: Run it to confirm it passes**

Run: `uv run pytest tests/test_corpus.py -q`
Expected: PASS, 2 tests

- [ ] **Step 5: Write the failing test for the zero-defect refusal**

Append to `tests/test_lens_scoring.py`:

```python
def test_a_fixture_declaring_no_defects_is_refused(sa0062, tmp_path):
    """`score_pass` already refuses zero surviving runs because a table of
    zeroes reads like a measurement. Zero defects is the same shape one level
    out: it scores 0/0 and looks like a lens that found nothing."""
    for name in ("diff.patch", "spec_body.md", "gates.txt", "context.md",
                 "recorded-findings.json"):
        (tmp_path / name).write_text((sa0062.root / name).read_text())
    text = (sa0062.root / "fixture.toml").read_text()
    (tmp_path / "fixture.toml").write_text(text[: text.index("[[defects]]")])

    with pytest.raises(lens_scoring.FixtureError, match="declares no defects"):
        lens_scoring.load_fixture(tmp_path)
```

- [ ] **Step 6: Run it to confirm it fails**

Run: `uv run pytest tests/test_lens_scoring.py -k no_defects -q`
Expected: FAIL — `DID NOT RAISE`, because the fixture loads and would score `0/0`

- [ ] **Step 7: Add the refusal in `load_fixture`**

After the `defects` tuple is built and before the `Fixture(...)` is returned:

```python
    if not defects:
        raise FixtureError(
            f"{spec_id}: declares no defects. A fixture with none scores 0/0, "
            "which reads like a measurement and is not one."
        )
```

- [ ] **Step 8: Run both test files**

Run: `uv run pytest tests/test_corpus.py tests/test_lens_scoring.py -q`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add harness/corpus.py harness/lens_scoring.py tests/test_corpus.py tests/test_lens_scoring.py
git commit -m "feat(harness): a corpus was a list in code, and a fixture with no defects scored 0/0"
```

---

### Task 2: `score_corpus`, counting defects and naming what dropped

**Files:**
- Modify: `harness/corpus.py`
- Test: `tests/test_corpus.py`

**Interfaces:**
- Consumes: `lens_scoring.score_pass(fixture, runs, expect) -> dict[str, Score]`, `lens_scoring.LensErrored`
- Produces: `corpus.CorpusScore`, a frozen dataclass with two fields — `per_fixture: dict[str, dict[str, Score]]` and `dropped: tuple[str, ...]` — and three derived properties, `declared: int`, `seen: int`, `graded: int`. Derived rather than stored so the aggregate cannot disagree with the rows it is computed from. Plus `corpus.score_corpus(fixtures, runs, expect=tuple(LENSES)) -> CorpusScore`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_corpus.py`:

```python
from harness.lens_scoring import LensReview
from saffron.agents.findings import Finding
from saffron.phases.review import LENSES


def _run(findings=()):
    return [
        LensReview(lens=lens, findings=list(findings) if lens == "correctness" else [])
        for lens in LENSES
    ]


def _finding(file, line, claim):
    return Finding(
        lens="correctness", severity="blocker", file=file, line=line,
        claim=claim, anchored=True,
    )


def test_the_aggregate_counts_defects_and_not_fixtures(sa0062, one_defect_fixture):
    """A fixture carrying two defects is two observations. Averaging within it
    first would throw one away, and the corpus is deliberately uneven — five
    fixtures carry one defect and three carry two."""
    scored = corpus.score_corpus(
        [sa0062, one_defect_fixture],
        {sa0062.spec_id: [_run()], one_defect_fixture.spec_id: [_run()]},
    )
    assert scored.declared == 3
    assert scored.graded == 0


def test_a_fixture_whose_lens_errored_leaves_the_denominator(sa0062, one_defect_fixture):
    """At n=3 an errored lens costs a third of a fixture; at n=1 it costs the
    fixture. Counting its defects as misses reports a lens miss for an error,
    which is the distinction `LensErrored` exists to keep."""
    errored = [LensReview(lens="correctness", findings=[], error="boom")]
    scored = corpus.score_corpus(
        [sa0062, one_defect_fixture],
        {sa0062.spec_id: [errored], one_defect_fixture.spec_id: [_run()]},
    )
    assert scored.dropped == (sa0062.spec_id,)
    assert scored.declared == 1  # only the fixture that produced a scored run


def test_a_corpus_where_every_fixture_dropped_is_not_a_table_of_zeroes(sa0062):
    errored = [LensReview(lens="correctness", findings=[], error="boom")]
    with pytest.raises(lens_scoring.LensErrored, match="no fixture"):
        corpus.score_corpus([sa0062], {sa0062.spec_id: [errored]})
```

Add the `one_defect_fixture` fixture at the top of the file:

```python
@pytest.fixture
def sa0062():
    return lens_scoring.load_fixture(FIXTURES / "SA-0062")


@pytest.fixture
def one_defect_fixture(sa0062, tmp_path):
    """SA-0062 with its second defect removed — a one-defect fixture built from
    a real one, so the uneven-corpus test is not scoring a hand-built stub."""
    for name in ("diff.patch", "spec_body.md", "gates.txt", "context.md",
                 "recorded-findings.json"):
        (tmp_path / name).write_text((sa0062.root / name).read_text())
    text = (sa0062.root / "fixture.toml").read_text()
    first, second = text.index("[[defects]]"), text.rindex("[[defects]]")
    (tmp_path / "fixture.toml").write_text(text[:second].replace('spec_id = "SA-0062"', 'spec_id = "SA-0062-one"'))
    assert first != second  # otherwise this fixture is the whole thing
    return lens_scoring.load_fixture(tmp_path)
```

- [ ] **Step 2: Run to confirm they fail**

Run: `uv run pytest tests/test_corpus.py -q`
Expected: FAIL, `AttributeError: module 'harness.corpus' has no attribute 'score_corpus'`

- [ ] **Step 3: Implement `CorpusScore` and `score_corpus`**

```python
@dataclass(frozen=True)
class CorpusScore:
    """A pass over the corpus. `declared` counts the defects of fixtures that
    produced a scored run, never all of them: a dropped fixture leaves the
    denominator rather than contributing misses."""

    per_fixture: dict[str, dict[str, Score]]
    dropped: tuple[str, ...]

    @property
    def declared(self) -> int:
        return sum(len(scores) for scores in self.per_fixture.values())

    @property
    def seen(self) -> int:
        return sum(s.seen > 0 for scores in self.per_fixture.values() for s in scores.values())

    @property
    def graded(self) -> int:
        return sum(s.graded > 0 for scores in self.per_fixture.values() for s in scores.values())


def score_corpus(
    fixtures: Sequence[Fixture],
    runs: Mapping[str, Sequence[Sequence[LensReview]]],
    expect: Collection[str] = tuple(LENSES),
) -> CorpusScore:
    """k/n per fixture, and one aggregate over defects.

    `seen` and `graded` count *defects*, not runs: at n=1 a defect contributes
    0 or 1, and at higher n a defect seen in any run counts once. That keeps
    the aggregate comparable across passes of different depth, which is the
    whole reason it exists.
    """
    per_fixture: dict[str, dict[str, Score]] = {}
    dropped: list[str] = []
    for fixture in fixtures:
        try:
            per_fixture[fixture.spec_id] = score_pass(
                fixture, runs.get(fixture.spec_id, []), expect
            )
        except LensErrored:
            dropped.append(fixture.spec_id)
    if not per_fixture:
        raise LensErrored(
            f"no fixture survived scoring — {len(fixtures)} fixture(s), "
            f"{len(dropped)} dropped. Nothing here is a measurement."
        )
    return CorpusScore(per_fixture=per_fixture, dropped=tuple(dropped))
```

Add the imports this needs at the top of `harness/corpus.py`:

```python
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass

from harness.lens_scoring import Fixture, LensErrored, Score, load_fixture, score_pass
from saffron.phases.review import LENSES, LensReview
```

- [ ] **Step 4: Run to confirm they pass**

Run: `uv run pytest tests/test_corpus.py -q`
Expected: PASS

- [ ] **Step 5: Prove the denominator test fires**

Temporarily change `score_corpus` to record a dropped fixture's defects in `per_fixture` as zero scores. Run `uv run pytest tests/test_corpus.py -k leaves_the_denominator -q` and confirm FAIL with `assert 3 == 1`. Revert.

- [ ] **Step 6: Commit**

```bash
git add harness/corpus.py tests/test_corpus.py
git commit -m "feat(harness): a dropped fixture reported a lens miss where a lens had errored"
```

---

### Task 3: `anchored_blockers` and `render_corpus_table`

**Files:**
- Modify: `harness/corpus.py`
- Test: `tests/test_corpus.py`

**Interfaces:**
- Consumes: `CorpusScore` from Task 2
- Produces: `corpus.anchored_blockers(runs) -> dict[str, list[int]]`, `corpus.render_corpus_table(fixtures, score, blockers) -> str`

- [ ] **Step 1: Write the failing tests**

```python
def test_anchored_blockers_are_counted_per_run_not_per_pass(sa0062):
    """The number item 88 showed is stable across passes, and the only one
    production can be compared against. Per run, because §5.5 routes any single
    anchored blocker to REBUT — a total hides which runs would have blocked."""
    blocking = _finding("saffron/cell/worktree.py", 418, "truncating write")
    counts = corpus.anchored_blockers({sa0062.spec_id: [_run([blocking]), _run()]})
    assert counts == {sa0062.spec_id: [1, 0]}


def test_an_unanchored_blocker_is_not_counted(sa0062):
    """Unanchored means reconciliation could not place it in the diff. It is
    kept in the record because the drop rate is signal, but it would not have
    routed the pull request anywhere."""
    dropped = Finding(
        lens="correctness", severity="blocker", file="x.py", line=1,
        claim="c", anchored=False,
    )
    assert corpus.anchored_blockers({sa0062.spec_id: [_run([dropped])]}) == {sa0062.spec_id: [0]}


def test_the_table_reports_the_aggregate_and_every_fixture(sa0062, one_defect_fixture):
    fixtures = [sa0062, one_defect_fixture]
    runs = {f.spec_id: [_run()] for f in fixtures}
    table = corpus.render_corpus_table(fixtures, corpus.score_corpus(fixtures, runs),
                                       corpus.anchored_blockers(runs))
    assert "0/3" in table  # graded / declared, per defect
    assert sa0062.spec_id in table and one_defect_fixture.spec_id in table
```

- [ ] **Step 2: Run to confirm they fail**

Run: `uv run pytest tests/test_corpus.py -q`
Expected: FAIL, `AttributeError: ... 'anchored_blockers'`

- [ ] **Step 3: Implement both**

```python
def anchored_blockers(
    runs: Mapping[str, Sequence[Sequence[LensReview]]],
) -> dict[str, list[int]]:
    """Anchored blockers per run, per fixture.

    Unanchored findings are excluded: reconciliation could not place them in
    the diff, so they would not have routed the pull request anywhere (§5.5).
    """
    return {
        spec_id: [
            sum(
                finding.severity == "blocker" and finding.anchored
                for review in run
                for finding in review.findings
            )
            for run in fixture_runs
        ]
        for spec_id, fixture_runs in runs.items()
    }


def render_corpus_table(
    fixtures: Sequence[Fixture],
    score: CorpusScore,
    blockers: Mapping[str, list[int]],
) -> str:
    """The pass as markdown, for pasting into a `docs/evidence/` record.

    The aggregate leads, because it is the number Track C reads; the per-fixture
    rows are under it so a moved aggregate can be attributed.
    """
    lines = [
        f"**{score.graded}/{score.declared} declared defects graded** "
        f"({score.seen}/{score.declared} seen) across "
        f"{len(score.per_fixture)} fixture(s).",
        "",
        "| Fixture | Defect | Seen | Graded | Anchored blockers |",
        "|---|---|---|---|---|",
    ]
    for fixture in fixtures:
        scores = score.per_fixture.get(fixture.spec_id)
        if scores is None:
            continue
        counts = ", ".join(str(n) for n in blockers.get(fixture.spec_id, []))
        for defect in fixture.defects:
            entry = scores[defect.id]
            lines.append(
                f"| {fixture.spec_id} | `{defect.id}` "
                f"| {entry.seen}/{entry.runs} | {entry.graded}/{entry.runs} "
                f"| {counts} |"
            )
    if score.dropped:
        lines += [
            "",
            f"**{len(score.dropped)} fixture(s) dropped** — a lens errored, so "
            f"they say nothing about their diff and are in no n above: "
            f"{', '.join(score.dropped)}.",
        ]
    return "\n".join(lines)
```

- [ ] **Step 4: Run to confirm they pass**

Run: `uv run pytest tests/test_corpus.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add harness/corpus.py tests/test_corpus.py
git commit -m "feat(harness): a pass printed per-defect scores and not the number a pull request turns on"
```

---

### Task 4: The recovery script

**Files:**
- Create: `docs/evidence/scripts/2026-09-08-recover-fixture.py`
- Modify: `docs/evidence/scripts/2026-09-08-sa0062-gate-tools.py` (extract the splice)
- Test: `tests/test_corpus.py`

**Interfaces:**
- Consumes: `Ledger.queue_lines()`, `Ledger.attempts(task_id)`, `Ledger.attempt_results(attempt_id)`, `review.gate_summary(results, advisory=())`
- Produces: `recover.splice_tools(results, baseline) -> list[GateResult]`, `recover.recover_range(spec_id, home, repo) -> tuple[str, str]`

`2026-09-08-sa0062-gate-tools.py` **stays**: `fixture.toml` and the second-pass record cite it by name as the provenance of SA-0062's restored tools, and a deleted script makes those citations unfollowable. It imports `splice_tools` from the new script instead of holding its own copy.

- [ ] **Step 1: Write the failing test for the range recovery**

```python
def test_a_recovered_range_reproduces_the_recorded_patch_byte_for_byte():
    """The acceptance test for the archaeology. Every recorded `head_sha` is
    gone from live history, so each range is rebuilt — and a range that does
    not reproduce the recorded diff exactly would grade a lens against a tree
    it never saw."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "recover",
        Path(__file__).parent.parent / "docs" / "evidence" / "scripts"
        / "2026-09-08-recover-fixture.py",
    )
    recover = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(recover)

    base, head = recover.recover_range("SA-0063", Path.home() / ".saffron", Path.cwd())
    assert (base[:8], head[:8]) == ("132a2f8d", "f76931df")
```

- [ ] **Step 2: Run to confirm it fails**

Run: `uv run pytest tests/test_corpus.py -k recovered_range -q`
Expected: FAIL — the script does not exist

- [ ] **Step 3: Write the recovery script**

```python
"""Rebuild a fixture directory from the ledger and the batch tree.

`docs/superpowers/specs/2026-09-08-lens-corpus-design.md`. Every `head_sha`
recorded in `patch.json` is gone from live history — the branch was deleted
after merge — so a fixture's range is recovered rather than read off:

    head  the ledger's `pushed_sha` for the task
    base  the first ancestor of that head where `git diff base..head` is
          byte-identical to the batch tree's recorded `patch.diff`

Byte-identity is the acceptance test, not a heuristic. Four of the eight
fixtures need the walk because their recorded `tree_base` is not an ancestor of
their head at all: they were stacked pull requests, and SA-0048's true base is
SA-0046's head (backlog item 33, visible in the archive).

The `[[defects]]` blocks are deliberately NOT generated. The backlog row is the
only place the mutation that proves a defect is written down, and a generated
guess would be a predicate nobody chose.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from saffron.gates.contract import GateResult  # noqa: E402
from saffron.ledger import Ledger  # noqa: E402
from saffron.phases import review  # noqa: E402

WALK_DEPTH = 60


class RecoveryError(RuntimeError):
    """A range that cannot be reproduced exactly. Never a warning."""


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    ).stdout


def recover_range(spec_id: str, home: Path, repo: Path) -> tuple[str, str]:
    """`(base, head)` for a spec, verified against its recorded patch."""
    recorded = (home / "batches" / "v0" / spec_id / "patch.diff").read_text()
    ledger = Ledger(home / "ledger.db")
    try:
        rows = [r for r in ledger.queue_lines() if r["spec_id"] == spec_id]
    finally:
        ledger.close()
    if len(rows) != 1:
        raise RecoveryError(f"{len(rows)} tasks for {spec_id}, want 1")
    head = rows[0]["pushed_sha"]
    if not head:
        raise RecoveryError(f"{spec_id} has no pushed_sha; its branch is unrecoverable")
    for candidate in _git(repo, "rev-list", f"--max-count={WALK_DEPTH}", head).split():
        if _git(repo, "diff", f"{candidate}..{head}") == recorded:
            return candidate, head
    raise RecoveryError(
        f"{spec_id}: no ancestor within {WALK_DEPTH} of {head[:8]} reproduces the "
        "recorded patch. The range is not recoverable and the fixture must not ship."
    )


def splice_tools(
    results: list[GateResult], baseline: list[dict]
) -> list[GateResult]:
    """Head-suite results carrying the tools the same run's baseline recorded.

    Base and head ran the same binaries from the same cell image in the same
    run, so a version string in the baseline suite is the version string at
    head. `revert` skipped at base and inherits the tool of the `tests` re-run
    it performs (`revert.py:307`); every other miss is a host-side core gate
    that executes nothing, and None renders as "no tool reported".
    """
    tools = {row["gate"]: row["tool"] for row in baseline if row["tool"]}
    return [
        result.model_copy(
            update={
                "tool": tools.get(
                    result.gate,
                    tools.get("tests") if result.gate == "revert" else None,
                )
            }
        )
        for result in results
    ]
```

Add a `main()` taking `--spec`, `--home`, `--repo`, `--out` (default `docs/evidence/fixtures`) and `--write`, which calls `recover_range` and then writes exactly six files into `<out>/<SPEC>/`:

| File | Content |
|---|---|
| `diff.patch` | `<home>/batches/v0/<SPEC>/patch.diff`, copied verbatim — it is what `recover_range` just verified |
| `recorded-findings.json` | `<home>/batches/v0/<SPEC>/findings.json`, copied verbatim |
| `gates.txt` | `review.gate_summary(splice_tools(results, baseline))`, no trailing newline — `gate_summary` returns none, `session.py` hands the lens what it returns, and `load_fixture` reads the file verbatim |
| `spec_body.md` | `git show <base>:.saffron/specs/<SPEC>-*.md` plus `context.criteria_section(spec.acceptance)`, the way `session.py`'s REVIEW call assembles it |
| `context.md` | `git show <base>:CONTEXT.md` |
| `fixture.toml` | `spec_id`, `pr` from the ledger's `pr_url`, `base_sha` and `head_sha` in full (never abbreviated — `git show <sha>:<path>` is one collision away from ambiguous), `source`, `recorded_seen = 0`, `recorded_graded = 0` |

No `[[defects]]` blocks: they are Task 6's, and `load_fixture` refuses the fixture until they exist, so a half-recovered fixture cannot be scored by accident.

- [ ] **Step 4: Run to confirm it passes**

Run: `uv run pytest tests/test_corpus.py -k recovered_range -q`
Expected: PASS

- [ ] **Step 5: Point the SA-0062 script at the shared splice**

In `2026-09-08-sa0062-gate-tools.py`, replace its inline `model_copy` comprehension with `splice_tools(results, baseline)` imported from the new script, and re-run it in dry-run mode:

Run: `uv run python docs/evidence/scripts/2026-09-08-sa0062-gate-tools.py --fixture docs/evidence/fixtures/SA-0062`
Expected: `7 of 14 lines name a tool`, and the shipped fixture unchanged

- [ ] **Step 6: Commit**

```bash
git add docs/evidence/scripts tests/test_corpus.py
git commit -m "feat(evidence): a fixture's range was read off a head that no longer exists"
```

---

### Task 5: Recover the seven fixtures

**Files:**
- Create: `docs/evidence/fixtures/SA-0045/`, `SA-0046/`, `SA-0048/`, `SA-0050/`, `SA-0054/`, `SA-0055/`, `SA-0063/` (five frozen files plus `fixture.toml` each)
- Test: `tests/test_corpus.py`

**Interfaces:**
- Consumes: `recover_range`, `splice_tools` from Task 4

- [ ] **Step 1: Run the recovery for all seven**

```bash
for spec in SA-0045 SA-0046 SA-0048 SA-0050 SA-0054 SA-0055 SA-0063; do
  uv run python docs/evidence/scripts/2026-09-08-recover-fixture.py --spec "$spec" --write
done
```

Expected: seven directories, each with `diff.patch`, `spec_body.md`, `gates.txt`, `context.md`, `recorded-findings.json`, `fixture.toml`. The ranges must match the table at the top of this plan exactly.

- [ ] **Step 2: Write the byte-identity test over every shipped fixture**

```python
def test_every_shipped_fixture_reproduces_its_own_declared_range():
    """What makes the archaeology auditable rather than claimed. A fixture
    whose `diff.patch` is not `git diff base..head` at the range its own
    `fixture.toml` declares is grading a lens against a tree nobody has."""
    for fixture in corpus.load_corpus(FIXTURES):
        live = subprocess.run(
            ["git", "diff", f"{fixture.base_sha}..{fixture.head_sha}"],
            capture_output=True, text=True, check=True,
        ).stdout
        assert live == fixture.diff, fixture.spec_id
```

- [ ] **Step 3: Run it**

Run: `uv run pytest tests/test_corpus.py -k reproduces_its_own_declared_range -q`
Expected: PASS for all eight fixtures

- [ ] **Step 4: Prove it fires**

Temporarily edit `docs/evidence/fixtures/SA-0045/fixture.toml` to set `base_sha` to SA-0046's base (`a79b680b...`). Re-run: expect FAIL naming SA-0045. Revert.

- [ ] **Step 5: Commit**

```bash
git add docs/evidence/fixtures tests/test_corpus.py
git commit -m "fix(evidence): seven known-bad ranges existed only as a table in a backlog item"
```

---

### Task 6: Declare the ten defects

**Files:**
- Modify: the seven new `fixture.toml` files
- Test: `tests/test_corpus.py`

**Interfaces:**
- Consumes: `corpus.load_corpus`, `lens_scoring.calibrate`
- Produces: `corpus.calibrate_corpus(fixtures) -> None`

Each defect below gives the backlog row verbatim, the file, a starting line range and starting `must_mention` phrases. **Both the range and the phrases are corrected by pass 1 (Task 8), which exists for exactly that** — this is the fixture's first draft, not its final predicate.

**The anchoring rule, learned from SA-0062.** `truncating-write` was first declared over `_write_file`'s own lines and every run filed it at the *call site*; the range was widened to cover both. Item 69's defects are vacuous tests, so they are declared over the test, but if pass 1 shows lenses anchoring on the source the test fails to guard, widen to cover both rather than scoring the defect missed.

| Spec | id | file | lines | Row |
|---|---|---|---|---|
| SA-0045 | `reflow-defeats-guard` | `tests/test_ledger.py` | 639–686 | reflow one `SCHEMA` line — both migration guards assert what `replace` removed |
| SA-0046 | `reflow-defeats-guard` | `tests/test_ledger.py` | 717–773 | the same, on `policy_sha` |
| SA-0048 | `refusal-codes-unpinned` | `saffron/preflight.py` | 295–320 | `exc.code not in (401, 403)` → `not in (999,)`; 89 tests green |
| SA-0050 | `breaker-reset-unguarded` | `saffron/batch.py` | 130–190 | delete the breaker reset; suite green |
| SA-0054 | `parent-branch-unpinned` | `saffron/cli.py` | 590–600 | `parent_branch=None`; 76/76 green — every stacked child would target `main` |
| SA-0054 | `stop-line-unwitnessed` | `saffron/cli.py` | 790–805 | `print(f"batch: {stop}")` → `pass`; 76/76 green |
| SA-0055 | `pinned-base-unwitnessed` | `saffron/cli.py` | 685–730 | `pinned=derived` invisible to an assertion matching only `ast.Constant` |
| SA-0055 | `readiness-guard-unwitnessed` | `saffron/cli.py` | 930–950 | delete the `readiness.ok` guard; the narrowing assert raises and exit 2 still holds |
| SA-0063 | `notes-neutralization-unwitnessed` | `saffron/report/pr_body.py` | 377–395 | neutralization on the notes path is asserted nowhere |
| SA-0063 | `empty-notes-heading-unwitnessed` | `saffron/report/pr_body.py` | 377–395 | make `_notes` render a heading over empty notes and the named witness stays green |

Starting phrases, one line per defect, chosen from the row's own words and **never from a run**:

```toml
# SA-0045 / SA-0046
must_mention = ["replace", "whitespace", "reflow"]
# SA-0048
must_mention = ["401", "403", "status code"]
# SA-0050
must_mention = ["reset", "consecutive", "breaker"]
# SA-0054 parent-branch-unpinned
must_mention = ["parent_branch", "parent branch", "stacked"]
# SA-0054 stop-line-unwitnessed
must_mention = ["stdout", "printed", "capsys"]
# SA-0055 pinned-base-unwitnessed
must_mention = ["ast.Constant", "keyword", "not a literal"]
# SA-0055 readiness-guard-unwitnessed
must_mention = ["readiness", "guard", "exit 2"]
# SA-0063 notes-neutralization-unwitnessed
must_mention = ["neutraliz", "mention", "defang"]
# SA-0063 empty-notes-heading-unwitnessed
must_mention = ["empty", "heading", "no notes"]
```

- [ ] **Step 1: Check the two phrase-collision rules already enforced for SA-0062**

`tests/test_lens_scoring.py` holds `test_two_defects_may_not_share_a_phrase` and `test_one_defects_phrase_may_not_contain_anothers`. SA-0054's and SA-0055's pairs each sit in one file with overlapping ranges, so run them first:

Run: `uv run pytest tests/test_lens_scoring.py -k "share_a_phrase or contain_anothers" -q`
Expected: PASS. If it fails, the two phrases in that pair are the discriminator and must be made specific — that is the failure the rule exists for.

- [ ] **Step 2: Write the corpus calibration test**

```python
def test_the_predicate_reproduces_every_fixture_s_recorded_answer():
    """`calibrate`'s guard, over all eight. Every declared defect is one a lens
    should have raised and did not, so every fixture's recorded answer is
    0 seen / 0 graded — and a predicate loosened until a missed defect starts
    scoring fails here before any money is spent."""
    corpus.calibrate_corpus(corpus.load_corpus(FIXTURES))
```

- [ ] **Step 3: Run to confirm it fails**

Run: `uv run pytest tests/test_corpus.py -k reproduces_every_fixture -q`
Expected: FAIL, `AttributeError: ... 'calibrate_corpus'`

- [ ] **Step 4: Implement `calibrate_corpus`**

```python
def calibrate_corpus(fixtures: Sequence[Fixture]) -> None:
    """Every fixture's own recorded answer, before any money is spent.

    Raises on the first failure rather than collecting them: a pass must not
    start with one predicate known wrong, and the message names which.
    """
    for fixture in fixtures:
        calibrate(fixture)
```

- [ ] **Step 5: Run the whole suite**

Run: `uv run pytest -q`
Expected: PASS. A `CalibrationError` here names a fixture whose recorded findings match a declared defect — fix the phrases, not the calibration.

- [ ] **Step 6: Commit**

```bash
git add docs/evidence/fixtures harness/corpus.py tests/test_corpus.py
git commit -m "fix(evidence): ten known defects had no predicate, so no pass could score them"
```

---

### Task 7: The corpus driver

**Files:**
- Create: `docs/evidence/scripts/2026-09-08-lens-corpus.py`

**Interfaces:**
- Consumes: `corpus.load_corpus`, `corpus.calibrate_corpus`, `corpus.score_corpus`, `corpus.anchored_blockers`, `corpus.render_corpus_table`, `session.cell_up`, `session.cell_down`, `review.run_review`
- Produces: `<out>/<SPEC>/run-<n>.json` per fixture, and `<out>/table.md`

Model it on `docs/evidence/scripts/2026-09-07-lens-scoring.py`, which stays exactly as it is so both recorded passes remain reproducible by the file that produced them. Three differences:

- [ ] **Step 1: Calibrate the whole corpus before the first cell**

```python
    fixtures = corpus.load_corpus(args.fixtures)
    try:
        corpus.calibrate_corpus(fixtures)
    except lens_scoring.CalibrationError as exc:
        print(f"calibration failed, nothing was run:\n{exc}", file=sys.stderr)
        return 1
```

- [ ] **Step 2: Loop fixtures, one cell each, writing as you go**

```python
    for fixture in fixtures:
        out = args.out / fixture.spec_id
        if args.skip_existing and (out / "run-1.json").is_file():
            print(f"{fixture.spec_id}: already run, skipping")
            continue
        out.mkdir(parents=True, exist_ok=True)
        created: set[str] = set()
        try:
            session.cell_up(
                repo=args.repo, mirror=mirror, tree_base=fixture.head_sha,
                branch=f"lens-corpus/{fixture.spec_id}", network=network,
                volume=volume, state=state, container=container,
                gates_dir=mirror_ops.export_saffron_dir(
                    mirror, fixture.head_sha, out / "gates"
                ),
                thread_env={}, created=created,
                note=lambda step, detail: print(f"  {step}: {detail}"),
            )
            for index in range(1, args.runs + 1):
                reviews = review.run_review(
                    container,
                    diff=fixture.diff,
                    read_head=_read_head_at(args.repo, fixture.head_sha),
                    spec_body=fixture.spec_body,
                    gates=fixture.gates,
                    context_md=fixture.context_md,
                    # Off the script's own root, not the CWD: a relative
                    # resolve puts the failure inside the loop, after a cell
                    # has already started.
                    prompts_dir=ROOT / "saffron" / "agents" / "prompts",
                    max_turns=args.max_turns,
                    budget_usd=args.budget_usd,
                    agent=agent,
                    spec_id=f"{fixture.spec_id}-lenscorpus-{index}",
                    emit=lambda event: print(f"  {events.describe(event)}"),
                )
                (out / f"run-{index}.json").write_text(
                    json.dumps([r.as_dict() for r in reviews], indent=2)
                )
        finally:
            session.cell_down(
                network=network, volume=volume, state=state,
                container=container, created=created,
                note=lambda _s, _ok, d: print(f"  {d}", file=sys.stderr),
            )
```

The image builds once — `image.cell_tag` keys off the repo path, not the tree — so each later fixture pays only for a worktree at its own head.

- [ ] **Step 3: Score and render across fixtures**

```python
    runs = {
        fixture.spec_id: [
            lens_scoring.reviews_from_json(path.read_text())
            for path in sorted((args.out / fixture.spec_id).glob("run-*.json"))
        ]
        for fixture in fixtures
    }
    scored = corpus.score_corpus(fixtures, runs)
    table = corpus.render_corpus_table(fixtures, scored, corpus.anchored_blockers(runs))
    (args.out / "table.md").write_text(table + "\n")
    print(f"\n{table}")
```

- [ ] **Step 4: Dry-run against the already-recorded SA-0062 data**

```bash
mkdir -p /tmp/corpus-dry/SA-0062
cp docs/evidence/passes/2026-09-08-lens-scoring-second-pass/run-1.json /tmp/corpus-dry/SA-0062/
uv run python docs/evidence/scripts/2026-09-08-lens-corpus.py \
  --fixtures docs/evidence/fixtures --out /tmp/corpus-dry --skip-existing --score-only
```

Expected: a table naming SA-0062 with its real scores, and seven fixtures dropped. This exercises calibration, loading, scoring and rendering without a cell or a dollar. Add `--score-only` for it.

- [ ] **Step 5: Commit**

```bash
git add docs/evidence/scripts/2026-09-08-lens-corpus.py
git commit -m "feat(evidence): a pass over eight fixtures had to be eight invocations and a hand-summed table"
```

---

### Task 8: Pass 1 — disposable, and its only job is the predicates

**Files:**
- Modify: the seven `fixture.toml` files
- Create: `docs/evidence/passes/2026-09-08-lens-corpus-calibration/`

**This pass's numbers are discarded.** They are not published as a baseline and no test pins them. Its output is corrected predicates.

- [ ] **Step 1: Check the host and run it**

Non-loopback listeners must be rapportd alone, and `.env` must exist in the worktree — `dotenv_if_exists` fails silent, so a worktree without it reports `tolerating nothing` and fails preflight on rapportd's port.

```fish
env CLAUDE_CODE_OAUTH_TOKEN=(bash -c 'source ~/.secrets; printf %s $CLAUDE_CODE_OAUTH_TOKEN') \
    SAFFRON_ALLOW_HOST_PROCESS=rapportd PYTHONUNBUFFERED=1 \
  uv run python docs/evidence/scripts/2026-09-08-lens-corpus.py \
    --fixtures docs/evidence/fixtures --runs 1 \
    --out ~/.saffron/lens-scoring/corpus-calibration
```

Expected: ~$13, ~80 minutes. Do not start a batch while it runs — it takes the proxy and the `saffron-cells` network.

- [ ] **Step 2: Triage every miss by hand**

For each defect scored 0, read that fixture's `run-1.json` and decide: did the lens miss it, or did the predicate fail to recognise a finding that describes it? Record the decision per defect. A finding that describes the defect in words the phrases do not contain is a **predicate** failure; silence, or a finding about something else, is a **lens** miss.

- [ ] **Step 3: Correct the predicates, and say so in the file**

Beside each corrected defect, a comment naming what was wrong and that the correction was made after seeing runs — the form `docs/evidence/fixtures/SA-0062/fixture.toml` uses. Ranges widen the way `truncating-write`'s did when lenses anchored on the call site.

- [ ] **Step 4: Re-run calibration and the phrase-collision rules**

Run: `uv run pytest tests/test_corpus.py tests/test_lens_scoring.py -q`
Expected: PASS. A widened range that now overlaps a sibling makes the phrases the only discriminator, which is what `test_two_defects_may_not_share_a_phrase` checks.

- [ ] **Step 5: Commit the corrections and the raw runs**

```bash
git add docs/evidence/fixtures docs/evidence/passes/2026-09-08-lens-corpus-calibration
git commit -m "fix(evidence): ten predicates were declared from a backlog row and never read against a lens"
```

---

### Task 9: Pass 2 — the baseline, and the criterion it replaces

**Files:**
- Create: `docs/evidence/passes/2026-09-08-lens-corpus-baseline/`, `docs/evidence/2026-09-08-lens-corpus-baseline.md`
- Modify: `docs/superpowers/plans/2026-09-07-trusting-the-queue.md`, `docs/BACKLOG.md` (items 79, 69, 86)
- Test: `tests/test_corpus.py`

- [ ] **Step 1: Run pass 2 with the predicates frozen**

Same command as Task 8 with `--out ~/.saffron/lens-scoring/corpus-baseline`. **No fixture may be edited after this runs** — that is what makes it a baseline rather than a second calibration.

- [ ] **Step 2: Copy the run JSON into the repo**

One directory per fixture under `docs/evidence/passes/2026-09-08-lens-corpus-baseline/`, so the record's numbers are re-derivable by anyone.

- [ ] **Step 3: Write the record**

Sections: what was run, the corpus table, the aggregate, per-fixture anchored blockers, and a Deviations list carrying the recovery rule, the SA-0063-not-SA-0064 correction, and the excluded `sh:in` row.

- [ ] **Step 4: Pin every number**

```python
def test_the_baseline_pass_s_published_aggregate_is_re_derivable():
    fixtures = corpus.load_corpus(FIXTURES)
    runs = {
        f.spec_id: [
            lens_scoring.reviews_from_json(p.read_text())
            for p in sorted((BASELINE / f.spec_id).glob("run-*.json"))
        ]
        for f in fixtures
    }
    scored = corpus.score_corpus(fixtures, runs)
    record = RECORD.read_text()
    assert f"{scored.graded}/{scored.declared}" in record
    assert scored.dropped == ()
```

Plus the dollar-figure test in the strong form written for the second pass: every `$N.NN` the record prints must be one the run JSON or a declared budget produces.

- [ ] **Step 5: Rewrite the exit criterion with the measured threshold**

In `docs/superpowers/plans/2026-09-07-trusting-the-queue.md`, criterion 3 becomes:

> REVIEW grades at least **B** of the corpus's twelve declared defects, where **B** is this baseline's measured count, and no fixture that graded a defect at baseline grades none.

`B` is filled in from pass 2 and not before.

- [ ] **Step 6: Update the backlog**

Item 79's Track A half is delivered; items 69 and 86 gain a line saying their tables are now a scored corpus and that neither item is thereby closed — 69's mechanism is still item 71's seam, and 86's two assertions are still unwritten.

- [ ] **Step 7: Run everything**

Run: `uv run pytest -q && uv run ast-grep test -c .saffron/sgconfig.yml`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add docs/evidence docs/superpowers/plans docs/BACKLOG.md tests/test_corpus.py
git commit -m "feat(evidence): Track C had no baseline it could read a prompt change against"
```
