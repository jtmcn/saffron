# Prompt Change Measurement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a prompt change scoreable — record what produced a number, and score the register of the claims a lens writes, without spending money.

**Architecture:** Two independent halves. `harness/register_scoring.py` reads claims already stored in `docs/evidence/passes/*/run-N.json` and scores them with the `prose` gate's own `check()`, so it costs nothing and re-derives. Separately, `tasks.prompt_sha` and `attempts.model` make an arm identifiable, and a pass manifest records it. Task 1 is a spike that can stop the first half.

**Tech Stack:** Python 3.12, pytest, `uv`, SQLite (`saffron/ledger.py`), the existing `.saffron/gates/prose.py` gate script.

**Spec:** `docs/superpowers/specs/2026-09-17-prompt-change-measurement-design.md`

## Global Constraints

- `saffron/` must never import `harness/`. The reverse is allowed and already done (`lens_scoring.py` imports `saffron.phases.review`).
- The scorer gets tests; a driver that spends money does not. Nothing in this plan spends money.
- Published numbers must re-derive from a pass's run JSON. `harness/**` and `docs/evidence/passes/**` are `elevate_on` in `.saffron/policy.yaml`.
- Compare arms as **hits per 1000 words of claim text**, never as a raw hit total. An arm that files fewer findings has fewer hits trivially.
- Commit subjects are lowercase `type(scope): what changed`, written as a sentence about the defect.
- A new test is not trusted until it has been watched failing.
- `DESIGN.md` and `CONTEXT.md` are `protected` in `.saffron/policy.yaml`. Task 6 touches `DESIGN.md` §4.1 and therefore cannot run in a cell.
- Run tests with `uv run pytest`. `make check` is lint plus the full suite.

---

### Task 1: Spike — does the register metric have signal?

**This task can stop Tasks 2–4.** It writes no committed code. Its output is a number and a decision.

**Files:**
- Create (throwaway, scratchpad, never committed): `noise_floor.py`
- Create: `docs/evidence/2026-09-17-register-noise-floor.md`

**Interfaces:**
- Consumes: nothing.
- Produces: a go/no-go decision for Tasks 2–4, and a recorded noise floor the decision rule in Task 9 reads.

- [ ] **Step 1: Write the throwaway in your scratchpad, not the repo**

```python
import importlib.util, json, sys, pathlib
from collections import Counter

REPO = pathlib.Path(".")
PASS = REPO / "docs/evidence/passes/2026-09-11-lens-corpus-spread"

spec = importlib.util.spec_from_file_location("pg", REPO / ".saffron/gates/prose.py")
gate = importlib.util.module_from_spec(spec); sys.modules["pg"] = gate
spec.loader.exec_module(gate)

per_run = {}
for fixture in sorted(p for p in PASS.iterdir() if p.is_dir()):
    for f in sorted(fixture.glob("run-*.json")):
        run = int(f.stem.split("-")[1])
        claims, words, hits = per_run.setdefault(run, [0, 0, Counter()])
        for lens in json.loads(f.read_text()):
            for finding in lens.get("findings") or []:
                text = finding.get("claim")
                if not text:
                    continue
                per_run[run][0] += 1
                per_run[run][1] += len(text.split())
                per_run[run][2].update(h.code for h in gate.check(text, "claim.md", "prose", root=REPO))

for run in sorted(per_run):
    claims, words, hits = per_run[run]
    total = sum(hits.values())
    print(f"run {run}: {claims} claims, {words} words, {total} hits, "
          f"{1000*total/words:.1f} per 1k  {dict(hits.most_common())}")
```

- [ ] **Step 2: Run it**

Run: `uv run python <scratchpad>/noise_floor.py`
Expected: three lines, one per run, each with a claim count and a per-1k figure. All three used identical prompts.

- [ ] **Step 3: Read the spread and decide**

The three runs differ only in sampling. The gap between the lowest and highest per-1k figure is the metric's noise floor.

Decide, and write the decision down before doing anything else:
- If the spread across three identical-prompt runs is **narrow**, the metric can see a prompt change larger than it. Continue to Task 2.
- If the spread is **wide** — as wide as a prompt edit could plausibly move it — B1 is dead. Stop. Tasks 2, 3 and 4 are abandoned; Tasks 5–9 still stand, because arm identity is worth having for the recall metric regardless.

- [ ] **Step 4: Write the evidence record**

Create `docs/evidence/2026-09-17-register-noise-floor.md` with: the three per-run figures verbatim, the per-rule breakdown, the command that produced them, the pass it read, the decision, and the reasoning. State plainly that the throwaway is not committed and the numbers re-derive by re-running the snippet above against the same pass.

- [ ] **Step 5: Commit the record only**

```bash
git add docs/evidence/2026-09-17-register-noise-floor.md
git commit -m "docs(evidence): the register metric's noise floor, measured on three runs of one prompt"
```

---

### Task 2: Load claims out of a pass

**Files:**
- Create: `harness/register_scoring.py`
- Test: `tests/test_register_scoring.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `Claim(fixture: str, run: int, lens: str, text: str)` frozen dataclass, and `claims_in(pass_dir: Path) -> list[Claim]`.

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

import json
from pathlib import Path

from harness.register_scoring import Claim, claims_in

REPO = Path(__file__).resolve().parent.parent
SPREAD = REPO / "docs/evidence/passes/2026-09-11-lens-corpus-spread"


def _pass(root: Path, runs: dict[str, dict[int, list[dict]]]) -> Path:
    for fixture, by_run in runs.items():
        (root / fixture).mkdir(parents=True)
        for run, lenses in by_run.items():
            (root / fixture / f"run-{run}.json").write_text(json.dumps(lenses))
    return root


def test_a_claim_carries_its_fixture_run_and_lens(tmp_path):
    directory = _pass(
        tmp_path,
        {"SA-0001": {1: [{"lens": "correctness", "findings": [{"claim": "a claim"}]}]}},
    )
    assert claims_in(directory) == [Claim("SA-0001", 1, "correctness", "a claim")]


def test_a_lens_that_errored_contributes_no_claim(tmp_path):
    directory = _pass(
        tmp_path,
        {"SA-0001": {1: [{"lens": "contract", "error": "boom", "findings": None}]}},
    )
    assert claims_in(directory) == []


def test_a_finding_with_no_claim_is_skipped(tmp_path):
    directory = _pass(
        tmp_path, {"SA-0001": {1: [{"lens": "adequacy", "findings": [{"claim": ""}]}]}}
    )
    assert claims_in(directory) == []


def test_the_real_spread_pass_yields_every_claim_it_holds():
    """Pins the published corpus: 8 fixtures, 3 runs each."""
    claims = claims_in(SPREAD)
    assert len(claims) == 64
    assert {c.run for c in claims} == {1, 2, 3}
    assert len({c.fixture for c in claims}) == 8
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_register_scoring.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'harness.register_scoring'`

- [ ] **Step 3: Write the minimal implementation**

```python
"""Score the register of the claims a lens wrote, from passes already on disk.

`lens_scoring.py` answers whether a declared defect was caught. It says nothing
about how the finding reads, so a prompt change that moves register alone is
invisible to it (`docs/superpowers/specs/2026-09-17-prompt-change-measurement-design.md`).

This module holds no I/O beyond reading a pass directory and it spends nothing:
every claim it scores is already stored in `docs/evidence/passes/*/run-N.json`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Claim:
    """One `claim` string, tagged with what produced it."""

    fixture: str
    run: int
    lens: str
    text: str


def claims_in(pass_dir: Path) -> list[Claim]:
    """Every claim in a pass, in fixture then run then file order.

    A lens that errored carries `findings: null`, and a finding with an empty
    claim is nothing to score. Neither is a miss, so neither raises.
    """
    found = []
    for fixture in sorted(p for p in pass_dir.iterdir() if p.is_dir()):
        for path in sorted(fixture.glob("run-*.json")):
            run = int(path.stem.split("-")[1])
            for lens in json.loads(path.read_text()):
                for finding in lens.get("findings") or []:
                    text = finding.get("claim")
                    if text:
                        found.append(Claim(fixture.name, run, lens["lens"], text))
    return found
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_register_scoring.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add harness/register_scoring.py tests/test_register_scoring.py
git commit -m "feat(harness): the claims a lens wrote are on disk and nothing reads them"
```

---

### Task 3: Score a claim with the house style

**Files:**
- Modify: `harness/register_scoring.py`
- Test: `tests/test_register_scoring.py`

**Interfaces:**
- Consumes: `Claim`, `claims_in` from Task 2.
- Produces: `load_gate(repo: Path)` returning the loaded `prose.py` module; `score_claim(gate, text: str, repo: Path) -> tuple[str, ...]` returning rule codes.

- [ ] **Step 1: Write the failing test**

```python
from harness.register_scoring import load_gate, score_claim


def test_a_claim_is_scored_by_the_house_rules():
    gate = load_gate(REPO)
    codes = score_claim(gate, "The cell stops; it restarts.", REPO)
    assert codes == ("semicolon",)


def test_a_saffron_term_is_never_filler_in_a_claim():
    """`protected_words` reads CONTEXT.md, so the root must be the repo."""
    gate = load_gate(REPO)
    assert "filler" not in score_claim(gate, "The task is elevated.", REPO)


def test_a_claim_is_not_read_as_a_spec_instruction():
    """`trailing-condition` is spec-only. A claim is not a spec."""
    gate = load_gate(REPO)
    codes = score_claim(gate, "- Run the gate when the cell stops.", REPO)
    assert "trailing-condition" not in codes
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_register_scoring.py -v -k "house_rules or filler or spec_instruction"`
Expected: FAIL — `ImportError: cannot import name 'load_gate'`

- [ ] **Step 3: Write the minimal implementation**

```python
import importlib.util
import sys

# Not a spec and not a root document: `trailing-condition` is spec-only and
# `_rendered` looks for spans only in DESIGN.md and CONTEXT.md. A claim is
# neither, and naming one here would score it as something it is not.
_CLAIM_PATH = "claim.md"


def load_gate(repo: Path):
    """The `prose` gate script, loaded by path as `tests/test_prose_gate.py` does."""
    script = repo / ".saffron" / "gates" / "prose.py"
    spec = importlib.util.spec_from_file_location("saffron_prose_gate", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered first: `Hit` is a dataclass under postponed annotations.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def score_claim(gate, text: str, repo: Path) -> tuple[str, ...]:
    """The house-style rule codes this claim carries.

    `root` is the repo because `protected_words` reads `CONTEXT.md`: Saffron's
    own vocabulary must not read as filler.
    """
    return tuple(hit.code for hit in gate.check(text, _CLAIM_PATH, "prose", root=repo))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_register_scoring.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add harness/register_scoring.py tests/test_register_scoring.py
git commit -m "feat(harness): the house style already scores prose and no one pointed it at a claim"
```

---

### Task 4: Aggregate a run, and report the spread across runs

**Files:**
- Modify: `harness/register_scoring.py`
- Test: `tests/test_register_scoring.py`

**Interfaces:**
- Consumes: `Claim`, `claims_in`, `load_gate`, `score_claim`.
- Produces: `RunScore(run: int, claims: int, words: int, hits: Counter[str])` with a `per_1k: float` property; `score_pass(pass_dir: Path, repo: Path) -> list[RunScore]`; `spread(scores: Sequence[RunScore]) -> dict[str, tuple[int, int]]`.

- [ ] **Step 1: Write the failing test**

```python
from collections import Counter

from harness.register_scoring import RunScore, score_pass, spread


def test_a_run_is_scored_per_thousand_words_not_per_hit():
    """An arm that files fewer findings has fewer hits trivially."""
    score = RunScore(run=1, claims=2, words=500, hits=Counter({"em-dash": 1}))
    assert score.per_1k == 2.0


def test_a_run_with_no_words_scores_zero_rather_than_dividing_by_zero():
    assert RunScore(run=1, claims=0, words=0, hits=Counter()).per_1k == 0.0


def test_a_pass_is_scored_one_row_per_run(tmp_path):
    directory = _pass(
        tmp_path,
        {
            "SA-0001": {
                1: [{"lens": "correctness", "findings": [{"claim": "It stops; it goes."}]}],
                2: [{"lens": "correctness", "findings": [{"claim": "It stops."}]}],
            }
        },
    )
    scores = score_pass(directory, REPO)
    assert [s.run for s in scores] == [1, 2]
    assert scores[0].hits["semicolon"] == 1
    assert scores[1].hits["semicolon"] == 0


def test_the_spread_is_the_lowest_and_highest_count_per_rule():
    scores = [
        RunScore(1, 1, 100, Counter({"em-dash": 2})),
        RunScore(2, 1, 100, Counter({"em-dash": 5})),
        RunScore(3, 1, 100, Counter({"em-dash": 3, "hedge": 1})),
    ]
    assert spread(scores) == {"em-dash": (2, 5), "hedge": (0, 1)}
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_register_scoring.py -v -k "per_thousand or dividing or one_row or lowest"`
Expected: FAIL — `ImportError: cannot import name 'RunScore'`

- [ ] **Step 3: Write the minimal implementation**

```python
from collections import Counter
from collections.abc import Sequence


@dataclass(frozen=True)
class RunScore:
    """One run's claims, scored. `per_1k` is the comparable number."""

    run: int
    claims: int
    words: int
    hits: Counter[str]

    @property
    def per_1k(self) -> float:
        if not self.words:
            return 0.0
        return 1000 * sum(self.hits.values()) / self.words


def score_pass(pass_dir: Path, repo: Path) -> list[RunScore]:
    """Every run in a pass, scored, in run order."""
    gate = load_gate(repo)
    claims: dict[int, list[Claim]] = {}
    for claim in claims_in(pass_dir):
        claims.setdefault(claim.run, []).append(claim)
    scores = []
    for run in sorted(claims):
        hits: Counter[str] = Counter()
        words = 0
        for claim in claims[run]:
            hits.update(score_claim(gate, claim.text, repo))
            words += len(claim.text.split())
        scores.append(RunScore(run, len(claims[run]), words, hits))
    return scores


def spread(scores: Sequence[RunScore]) -> dict[str, tuple[int, int]]:
    """The lowest and highest count of each rule across runs.

    With the prompts unchanged this is the metric's noise floor: a prompt
    change counts as measured only when it moves a rule further than this.
    """
    codes = {code for score in scores for code in score.hits}
    return {
        code: (min(s.hits[code] for s in scores), max(s.hits[code] for s in scores))
        for code in sorted(codes)
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_register_scoring.py -v`
Expected: 11 passed

- [ ] **Step 5: Run the full check**

Run: `make check`
Expected: the suite passes with 4 more tests than before this plan started.

- [ ] **Step 6: Commit**

```bash
git add harness/register_scoring.py tests/test_register_scoring.py
git commit -m "feat(harness): a raw hit total compares two arms that filed different numbers of findings"
```

---

### Task 5: Hash the prompt tree

**Files:**
- Modify: `saffron/agents/context.py`
- Test: `tests/test_context.py`

**Interfaces:**
- Consumes: `PROMPTS_DIR` from `saffron/agents/context.py`.
- Produces: `prompt_sha() -> str`, a 64-character hex digest over the prompt tree.

- [ ] **Step 1: Write the failing test**

```python
def test_the_prompt_sha_covers_every_prompt_file(tmp_path, monkeypatch):
    """The digest is over the tree as authored, so editing any prompt moves it."""
    tree = tmp_path / "prompts"
    (tree / "turns").mkdir(parents=True)
    (tree / "implement.md").write_text("system\n")
    (tree / "turns" / "plan.md").write_text("turn\n")
    monkeypatch.setattr(context, "PROMPTS_DIR", tree)

    before = context.prompt_sha()
    assert len(before) == 64

    (tree / "turns" / "plan.md").write_text("turn, edited\n")
    assert context.prompt_sha() != before


def test_the_prompt_sha_is_stable_across_calls():
    assert context.prompt_sha() == context.prompt_sha()


def test_the_prompt_sha_ignores_a_file_that_is_not_a_prompt(tmp_path, monkeypatch):
    tree = tmp_path / "prompts"
    tree.mkdir(parents=True)
    (tree / "implement.md").write_text("system\n")
    monkeypatch.setattr(context, "PROMPTS_DIR", tree)

    before = context.prompt_sha()
    (tree / "notes.txt").write_text("not a prompt\n")
    assert context.prompt_sha() == before
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_context.py -v -k prompt_sha`
Expected: FAIL — `AttributeError: module 'saffron.agents.context' has no attribute 'prompt_sha'`

- [ ] **Step 3: Write the minimal implementation**

```python
import hashlib


def prompt_sha() -> str:
    """A digest over the prompt tree as authored (§5.3 to §5.6).

    `tasks` already records `spec_sha` and `policy_sha`. The prompt tree is the
    third input that decides what a cell was told, and a number measured against
    one prompt version means nothing without it.

    Over the files, never the assembled prompt: that carries the spec body and
    the per-phase `CONTEXT.md` sections, so it varies per task.
    """
    digest = hashlib.sha256()
    for path in sorted(PROMPTS_DIR.rglob("*.md")):
        digest.update(path.relative_to(PROMPTS_DIR).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_context.py -v`
Expected: all pass, 3 more than before

- [ ] **Step 5: Commit**

```bash
git add saffron/agents/context.py tests/test_context.py
git commit -m "feat(agents): the prompt tree is the one input to a task that nothing records"
```

---

### Task 6: Record the arm in the ledger — BY HAND, NOT A CELL

**This task edits `DESIGN.md`, which `.saffron/policy.yaml` lists as `protected`. It cannot run in a cell.** A cell would add the column, pass every gate, and leave §4.1 describing a schema that no longer exists — backlog item 30's failure mode.

**Files:**
- Modify: `saffron/ledger.py` (SCHEMA, the additive migration block near :172, and the task writer)
- Modify: `saffron/cell/session.py` (write `model` when an attempt opens)
- Modify: `DESIGN.md` §4.1
- Test: `tests/test_ledger.py`

**Interfaces:**
- Consumes: `context.prompt_sha()` from Task 5.
- Produces: `create_task(..., prompt_sha: str | None = None)` and `close_attempt(..., model: str | None)`. Read back with the existing `tasks_by_repo` and `attempts` readers.

- [ ] **Step 1: Write the failing test**

`tests/test_ledger.py` already has a `ledger` fixture and a `task` fixture; these follow their shape.

```python
def test_a_task_records_the_prompt_tree_that_ran_it(ledger):
    """`spec_sha` and `policy_sha` are already here. The prompts were not."""
    repo_id = ledger.upsert_repo("thermal-edge", "/o", "/m.git", policy_sha="p" * 64)
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    task_id = ledger.create_task(
        run_id,
        spec_id="TE-9001",
        spec_sha="s" * 64,
        branch="saffron/TE-9001",
        prompt_sha="c" * 64,
    )
    (row,) = [r for r in ledger.tasks_by_repo(repo_id) if r["task_id"] == task_id]
    assert row["prompt_sha"] == "c" * 64


def test_a_task_written_by_a_caller_predating_the_column_still_records(ledger, task):
    """`policy_sha`'s own rule: a caller that predates the parameter still
    records a task, just one that cannot say what prompts it ran under."""
    _, task_id = task
    (row,) = [
        r
        for r in ledger.tasks_by_repo(1)
        if r["task_id"] == task_id
    ]
    assert row["prompt_sha"] is None


def test_an_older_ledger_gains_the_column_without_losing_a_row(tmp_path):
    """Additive only — never a migration that can lose a row (`ledger.py`)."""
    path = tmp_path / "ledger.db"
    first = Ledger(path)
    repo_id = first.upsert_repo("thermal-edge", "/o", "/m.git", policy_sha="p" * 64)
    run_id = first.create_run(repo_id, base_sha="a" * 40)
    first.create_task(
        run_id, spec_id="TE-9001", spec_sha="s" * 64, branch="saffron/TE-9001"
    )
    first._db.execute("ALTER TABLE tasks DROP COLUMN prompt_sha")
    first._db.commit()
    first.close()

    second = Ledger(path)
    assert [r["spec_id"] for r in second.tasks_by_repo(repo_id)] == ["TE-9001"]
    columns = {r["name"] for r in second._db.execute("PRAGMA table_info(tasks)")}
    assert "prompt_sha" in columns
    second.close()


def test_an_attempt_records_the_model_it_ran_on(ledger, task):
    """Declared in SCHEMA since v0.5 and never written. A prompt comparison
    means nothing if the model moved underneath it."""
    _, task_id = task
    attempt_id = ledger.open_attempt(task_id, phase="REVIEW")
    ledger.close_attempt(
        attempt_id,
        session_id="s",
        model="claude-opus-5",
        subtype="success",
        terminal_reason=None,
        num_turns=3,
        cost_usd_est=0.4,
    )
    (row,) = ledger.attempts(task_id)
    assert row["model"] == "claude-opus-5"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_ledger.py -v -k "prompt_tree or before_this_column or gains_the_column or records_the_model"`
Expected: FAIL — `TypeError: create_task() got an unexpected keyword argument 'prompt_sha'`

- [ ] **Step 3: Write the minimal implementation**

Add the column to the `tasks` table in `SCHEMA`, beside `policy_sha`:

```sql
    prompt_sha  TEXT,
```

Extend the additive migration tuple (`ledger.py`, the block whose comment reads "Additive only — never a migration that can lose a row"):

```python
        for column in ("pushed_sha", "pr_url", "policy_sha", "prompt_sha"):
            if column not in existing:
                self._db.execute(f"ALTER TABLE tasks ADD COLUMN {column} TEXT")
```

Thread it through `create_task`, defaulting to `None` for the same reason `policy_sha` does — a caller that predates the parameter still records a task:

```python
    def create_task(
        self,
        run_id: int,
        spec_id: str,
        spec_sha: str,
        branch: str,
        risk: str = "standard",
        budget_usd: float | None = None,
        policy_sha: str | None = None,
        prompt_sha: str | None = None,
    ) -> int:
        cursor = self._db.execute(
            """INSERT INTO tasks
                   (run_id, spec_id, spec_sha, state, risk, branch, budget_usd,
                    policy_sha, prompt_sha)
               VALUES (?, ?, ?, 'QUEUED', ?, ?, ?, ?, ?)""",
            (run_id, spec_id, spec_sha, risk, branch, budget_usd, policy_sha,
             prompt_sha),
        )
        self._db.commit()
        return _inserted_id(cursor)
```

Write the model where the session id is already written, in `close_attempt`:

```python
    def close_attempt(
        self,
        attempt_id: int,
        *,
        session_id: str | None,
        model: str | None = None,
        subtype: str,
        terminal_reason: str | None,
        num_turns: int,
        cost_usd_est: float,
    ) -> None:
        self._db.execute(
            """UPDATE attempts
                  SET ended_at = datetime('now'), session_id = ?, model = ?,
                      subtype = ?, terminal_reason = ?, num_turns = ?,
                      cost_usd_est = ?
                WHERE attempt_id = ?""",
            (session_id, model, subtype, terminal_reason, num_turns,
             cost_usd_est, attempt_id),
        )
        self._db.commit()
```

Then at the call sites in `saffron/cell/session.py`: pass `prompt_sha=context.prompt_sha()` where `create_task` is called, and pass the model the runner reported where `close_attempt` is called. `context` is already imported inside `_drive_cell`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_ledger.py tests/test_session.py -v`
Expected: all pass

- [ ] **Step 5: Update DESIGN.md §4.1**

Add `prompt_sha` to §4.1's description of the `tasks` table, beside `spec_sha` and `policy_sha`, and say what it covers: a digest of `saffron/agents/prompts/**` as authored. Note in the same edit that `attempts.model` is now written. Do not renumber any section.

- [ ] **Step 6: Run the full check**

Run: `make check`
Expected: passes

- [ ] **Step 7: Commit**

```bash
git add saffron/ledger.py saffron/cell/session.py tests/test_ledger.py DESIGN.md
git commit -m "feat(ledger): a number measured against a prompt version could not name the version"
```

---

### Task 7: A pass records its own arm

**Files:**
- Modify: `harness/register_scoring.py`
- Test: `tests/test_register_scoring.py`

**Interfaces:**
- Consumes: `RunScore` from Task 4.
- Produces: `Manifest(prompt_sha: str, model: str, fixtures: tuple[str, ...], driver: str, date: str)` and `read_manifest(pass_dir: Path) -> Manifest | None`.

- [ ] **Step 1: Write the failing test**

```python
import json

from harness.register_scoring import Manifest, read_manifest


def test_a_pass_manifest_names_the_arm(tmp_path):
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "prompt_sha": "b" * 64,
                "model": "claude-opus-5",
                "fixtures": ["SA-0045"],
                "driver": "docs/evidence/scripts/2026-09-08-lens-corpus.py",
                "date": "2026-09-17",
            }
        )
    )
    assert read_manifest(tmp_path) == Manifest(
        "b" * 64, "claude-opus-5", ("SA-0045",),
        "docs/evidence/scripts/2026-09-08-lens-corpus.py", "2026-09-17",
    )


def test_a_pass_written_before_manifests_existed_reads_as_none(tmp_path):
    """The five passes on disk predate this. They are not errors."""
    assert read_manifest(tmp_path) is None
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_register_scoring.py -v -k manifest`
Expected: FAIL — `ImportError: cannot import name 'Manifest'`

- [ ] **Step 3: Write the minimal implementation**

```python
@dataclass(frozen=True)
class Manifest:
    """What produced a pass. Prose in an evidence record until now."""

    prompt_sha: str
    model: str
    fixtures: tuple[str, ...]
    driver: str
    date: str


def read_manifest(pass_dir: Path) -> Manifest | None:
    """The pass's arm, or `None` for a pass written before manifests existed."""
    path = pass_dir / "manifest.json"
    if not path.exists():
        return None
    raw = json.loads(path.read_text())
    return Manifest(
        raw["prompt_sha"],
        raw["model"],
        tuple(raw["fixtures"]),
        raw["driver"],
        raw["date"],
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_register_scoring.py -v`
Expected: 13 passed

- [ ] **Step 5: Commit**

```bash
git add harness/register_scoring.py tests/test_register_scoring.py
git commit -m "feat(harness): a pass pins its prompts in prose, which is the claim elevate_on exists to hold"
```

---

### Task 8: Ask a prompt change to cite a pass

**Files:**
- Modify: `.github/pull_request_template.md`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing code depends on.

- [ ] **Step 1: Add the line under Verification**

In the `## Verification` comment block, after the bullet naming `uv run ast-grep test`, add:

```
- The pass a prompt change was measured against, when the diff reaches
  `saffron/agents/prompts/`: name the two arms and the decision rule, and say
  it was fixed before the numbers existed. An effect smaller than the noise
  floor is recorded as unmeasured, which is an answer.
```

Do not add this to `CLAUDE.md`. The file is at 206 lines against §8's ~200, and Appendix S names reference the tree already states as the first bucket to cut.

- [ ] **Step 2: Verify the template still renders**

Run: `uv run pytest tests/ -q -k template`
Expected: pass, or no tests collected if none exist for the template.

- [ ] **Step 3: Commit**

```bash
git add .github/pull_request_template.md
git commit -m "docs(github): a prompt change could claim a measurement nobody could find"
```

---

### Task 9: Record the decision rule before the first comparison

**Files:**
- Create: `docs/evidence/2026-09-17-register-decision-rule.md`

**Interfaces:**
- Consumes: the noise floor recorded in Task 1.
- Produces: the rule the first real comparison is judged against.

- [ ] **Step 1: Write the rule, with no numbers from any comparison in hand**

The two figures marked below come from Task 1's record. Every other word is written before any comparison exists.

```markdown
# The rule a register comparison is judged against

2026-09-17. Written before any two-arm comparison has been run.

## The metric

`RunScore.per_1k` from `harness/register_scoring.py`: house-style hits per
thousand words of claim text, over one pass. Hits per claim would move with a
prompt that files longer claims, and a raw total moves with one that files
fewer findings.

## The noise floor

Three runs of `2026-09-11-lens-corpus-spread` used one unchanged prompt tree.
Their `per_1k` figures spanned <LOW> to <HIGH>, a range of <RANGE>
(`docs/evidence/2026-09-17-register-noise-floor.md`).

## The rule

A prompt change counts as **measured** when the treatment arm's `per_1k` differs
from the control arm's by more than <RANGE>, in the direction stated in the pull
request before the arms were run. Both arms use one model, one corpus and one
driver, and differ only in `prompt_sha`.

Anything smaller is recorded as **unmeasured**. That is not a failure and it is
not "no effect": it is a change this instrument cannot see. `error` is not
`fail` and `RATE_LIMITED` is not `EXHAUSTED`.

## What this rule is not

Eight fixtures is a small corpus. §8 already says the statistics are noise at
this volume and to reread monthly rather than weekly. This is a guard against a
large regression, not an instrument for a small win, and a delta near the floor
should be reported as unmeasured rather than argued up.
```

- [ ] **Step 2: Commit**

```bash
git add docs/evidence/2026-09-17-register-decision-rule.md
git commit -m "docs(evidence): a threshold chosen after seeing the number is not a threshold"
```

---

## Notes for the executor

- Tasks 2, 3 and 4 are abandoned if Task 1 says the metric has no signal. Tasks 5 to 9 stand either way: arm identity is worth having for the recall metric regardless of whether register is scoreable.
- Task 6 cannot run in a cell. Every other code task can, and each will land `elevated` through `harness/**` or `saffron/ledger.py` in `.saffron/policy.yaml`.
- Nothing in this plan spends money or calls a model. The paid two-arm comparison is out of scope here and is run by hand.
- `reason` and `argument` are not reachable. The corpus runs REVIEW, so a pass holds lens findings only. Two of the five prompts #310 edited stay unmeasured, and the spec records this.
