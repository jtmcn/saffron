# Spec Reviewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A read-only spec-review agent that runs before a spec's first cell, plus a
blind backtest that decides whether it earns a Saffron cell.

**Architecture:** One Claude Code agent (`.claude/agents/spec-reviewer.md`) runs six
checks on a spec, reading everything at a base commit. The numeric checks read a
deterministic `driver.py history` command, so the agent judges numbers but never
computes them. The loop skill and the spec-writing guide both call it. A script under
`docs/evidence/scripts/` backtests it against 34 recorded spec defects and 10 clean
controls, with the bar committed before the first review.

**Tech Stack:** Python 3.12, `uv`, pytest, the Saffron ledger (`saffron/ledger.py`),
the headless Claude Code CLI (`claude -p --agents … --agent …`).

**Spec:** `docs/superpowers/specs/2026-09-14-spec-reviewer-design.md`

## Global Constraints

- No file under `saffron/` changes. A spec-review cell is a later spec.
- The reviewer is read-only. Its tools are exactly `Read, Grep, Glob, Bash`, and Bash
  only for `git show`, `git log`, `git ls-tree`, `git grep` and `driver.py history`.
- `history` reads the ledger only, and is deterministic. `--before <commit>` drops
  every task whose first attempt started at or after that commit's committer time, and
  always drops the spec's own tasks.
- The reviewer reads at the base commit, never the working tree.
- Findings use severities `blocker`, `concern` and `note`. The report ends with one
  `checked:`/`found:` line per check and an assessment.
- The backtest bar is **at least 17 of 34 known defects caught, and at most 2 false
  blockers across the 10 controls**. The case list, control list and scoring rule are
  committed before the first review.
- `CONTEXT.md` vocabulary: "cell", not "sandbox"; a batch is not a run; "verdict" only
  for the critic's confirm-or-withdraw.
- Every new test must fail against the code before its change. For a property already
  true, it must fail against a named mutant, and the step says which.
- Run `make fmt` first; the code blocks below are not line-wrapped for ruff. Then
  `make check > /tmp/check.log 2>&1; echo "make exit: $?"` must print `make exit: 0`
  before each commit. Stage files by name.
- Commit subjects are lowercase `type(scope): …`, written about the defect.
- Work on branch `joel/spec-reviewer`, cut from `origin/main` once #260 merges.
  Until then, stack it on `joel/spec-reviewer-design` with `gh stack`.

---

## File Structure

| File | Responsibility |
|---|---|
| `.claude/skills/run-saffron-spec-loop/driver.py` (modify) | `PastCell`, `_known_specs`, `_commit_time`, `_past_cells`, `_history_lines`, `cmd_history`, and the `history` subparser |
| `tests/test_spec_loop_driver.py` (modify) | Tests for the history functions |
| `.claude/agents/spec-reviewer.md` (create) | The reviewer: its contract, the six checks, and the report shape |
| `tests/test_spec_reviewer.py` (create) | The reviewer has no writing tool |
| `.claude/skills/run-saffron-spec-loop/SKILL.md` (modify) | Step 1b |
| `docs/agents/issue-tracker.md` (modify) | One line: run the reviewer before a spec's PR merges |
| `docs/evidence/scripts/2026-09-14-spec-reviewer-backtest.py` (create) | Case list, control selection, one headless review per version |
| `docs/evidence/<date>-spec-reviewer-backtest.md` (create) | Pre-registration, then the results |
| `docs/evidence/spec-reviewer-backtest/` (created by the script) | One `.md` report and one `.json` cost record per review |

---

### Task 1: `driver.py history`

**Files:**
- Modify: `.claude/skills/run-saffron-spec-loop/driver.py` (add after `cmd_size`, and register in `main()`)
- Test: `tests/test_spec_loop_driver.py`

**Interfaces:**
- Consumes:
  - `Ledger.tasks_by_spec(repo_id) -> dict[tuple[str, str], list[Row]]` (rows carry `task_id`, `state`)
  - `Ledger.attempts(task_id) -> list[Row]` (`SELECT *`: `phase`, `num_turns`, `cost_usd_est`, `subtype`, `terminal_reason`, `started_at`)
  - `Ledger.task_results(task_id) -> list[GateResult]`
  - `Ledger.queue_lines()` (rows carry `task_id`, `budget_usd`)
  - `discover_specs(dir) -> (list[DiscoveredSpec], list[DiscoveryFailure])`
  - the driver's existing `_git(*args, cwd=REPO)` and `_ledger_and_repo()`
- Produces:
  - `PastCell` (dataclass)
  - `_known_specs() -> dict[str, Spec]`
  - `_commit_time(commit: str, cwd: Path = REPO) -> str`, formatted `YYYY-MM-DD HH:MM:SS` in UTC
  - `_past_cells(ledger, repo_id, specs, *, before=None, exclude=None) -> list[PastCell]`
  - `_history_lines(target: Spec, cells: list[PastCell], limit: int = 12) -> list[str]`
  - CLI: `driver.py history SA-NNNN [--before COMMIT] [--limit N]`

- [ ] **Step 1: Write the failing tests.** Append to `tests/test_spec_loop_driver.py`:

```python
def _ledger_with_one_cell(tmp_path):
    from saffron.gates.contract import GateResult
    from saffron.ledger import Ledger

    ledger = Ledger(tmp_path / "ledger.db")
    repo_id = ledger.upsert_repo("r", "git@github.com:o/r.git", "/mirror", "policy")
    task_id = ledger.create_task(
        ledger.create_run(repo_id, "b" * 40),
        "SA-0001",
        "s" * 40,
        "saffron/SA-0001",
        budget_usd=6.0,
    )
    implement = None
    for phase, turns, cost, subtype in (
        ("IMPLEMENTING", 20, 1.82, "success"),  # the plan checkpoint
        ("IMPLEMENTING", 41, 2.33, "error_max_turns"),
        ("IMPLEMENTING", 3, 0.17, "success"),  # the salvage turn
        ("REVIEWING", 11, 0.80, "success"),
        ("REBUTTING", 32, 3.09, "error_max_budget_usd"),
    ):
        attempt = ledger.open_attempt(task_id, phase)
        ledger.close_attempt(
            attempt,
            session_id=None,
            subtype=subtype,
            terminal_reason=None,
            num_turns=turns,
            cost_usd_est=cost,
        )
        if phase == "IMPLEMENTING":
            implement = attempt
    ledger.record_gate_result(
        GateResult(
            gate="size",
            status="pass",
            tool="size 1",
            summary="269 changed lines within the bug ceiling of 300",
        ),
        attempt_id=implement,
    )
    ledger.set_task_state(task_id, "READY_FOR_REVIEW")
    return ledger, repo_id


def _spec(spec_id, spec_type="bug", touches=2, criteria=3):
    from saffron.intake import Spec

    return Spec(
        id=spec_id,
        title=spec_id,
        type=spec_type,
        touches=[f"f{i}.py" for i in range(touches)],
        acceptance_criteria=[f"c{i}" for i in range(criteria)],
    )


def test_history_splits_a_cells_spend_by_phase_and_names_how_attempts_ended(tmp_path):
    # SA-0087: 47 of 60 turns went to the plan checkpoint, and nothing showed
    # the operator that a cell of its shape needed more.
    ledger, repo_id = _ledger_with_one_cell(tmp_path)

    [cell] = driver._past_cells(ledger, repo_id, {"SA-0001": _spec("SA-0001")})

    assert cell.spec_id == "SA-0001"
    assert cell.state == "READY_FOR_REVIEW"
    assert cell.budget_usd == 6.0
    assert cell.plan == (20, pytest.approx(1.82))
    assert cell.implement == (44, pytest.approx(2.50))
    assert cell.review_usd == pytest.approx(0.80)
    assert cell.rebut_usd == pytest.approx(3.09)
    assert cell.endings == [
        "IMPLEMENTING error_max_turns",
        "REBUTTING error_max_budget_usd",
    ]
    assert cell.size == "269 changed lines within the bug ceiling of 300"


def test_history_before_a_commit_hides_later_cells_and_always_the_specs_own(tmp_path):
    # A blind review must not see the outcome it is being scored against.
    ledger, repo_id = _ledger_with_one_cell(tmp_path)
    specs = {"SA-0001": _spec("SA-0001")}

    assert driver._past_cells(ledger, repo_id, specs, before="2000-01-01 00:00:00") == []
    assert len(driver._past_cells(ledger, repo_id, specs, before="2999-01-01 00:00:00")) == 1
    assert driver._past_cells(ledger, repo_id, specs, exclude="SA-0001") == []


def test_history_lists_only_the_same_type_most_similar_shape_first():
    def cell(spec_id, spec_type, touches, criteria):
        return driver.PastCell(
            spec_id=spec_id,
            spec_type=spec_type,
            touches=touches,
            criteria=criteria,
            started_at="2026-09-14 12:00:00",
            state="READY_FOR_REVIEW",
            budget_usd=6.0,
            plan=(20, 1.82),
            implement=(44, 2.5),
            review_usd=0.8,
            rebut_usd=0.0,
            endings=[],
            size=None,
        )

    lines = driver._history_lines(
        _spec("SA-0009", touches=2, criteria=3),
        [
            cell("SA-0002", "feature", 2, 3),
            cell("SA-0003", "bug", 9, 9),
            cell("SA-0004", "bug", 2, 4),
        ],
    )

    assert lines[0].startswith("SA-0009  bug  touches=2 criteria=3")
    assert [line.split()[0] for line in lines[1:]] == ["SA-0004", "SA-0003"]


def test_commit_time_is_utc_in_the_ledgers_own_format(tmp_path):
    env = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_COMMITTER_DATE": "2026-09-14T12:00:00-07:00",
        "GIT_AUTHOR_DATE": "2026-09-14T12:00:00-07:00",
    }
    for argv in (
        ["git", "init", "-q", "-b", "main"],
        ["git", "-c", "user.email=t@example.com", "-c", "user.name=t",
         "commit", "-q", "--allow-empty", "-m", "c"],
    ):
        subprocess.run(argv, cwd=tmp_path, env=env, check=True)

    assert driver._commit_time("HEAD", cwd=tmp_path) == "2026-09-14 19:00:00"
```

- [ ] **Step 2: Run the tests to verify they fail.**

Run: `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_spec_loop_driver.py -k "history or commit_time"`
Expected: 4 failed, each with `AttributeError: module 'spec_loop_driver' has no attribute '_past_cells'` (or `PastCell`, `_history_lines`, `_commit_time`).

- [ ] **Step 3: Implement.** In `driver.py`, add `SPECS_DIR = REPO / ".saffron" / "specs"` beside `STATE_DIR`. Add these after `cmd_size`:

```python
@dataclass
class PastCell:
    """One past cell's spend by phase, for the reviewer's ceilings and size checks."""

    spec_id: str
    spec_type: str
    touches: int
    criteria: int
    started_at: str
    state: str
    budget_usd: float | None
    plan: tuple[int, float] | None  # the first IMPLEMENTING attempt: the plan checkpoint
    implement: tuple[int, float]  # every other IMPLEMENTING and REPAIRING attempt
    review_usd: float
    rebut_usd: float
    endings: list[str]  # "<phase> <subtype>" for every attempt that did not succeed
    size: str | None  # the last `size` gate summary, verbatim: it names the ceiling


def _known_specs() -> dict[str, Spec]:
    """Every spec by id, live or retired. The ledger's `spec_sha` is not a git
    blob, so a past spec's shape is read from its text as it stands now."""
    from saffron.intake import discover_specs

    found: dict[str, Spec] = {}
    for directory in (SPECS_DIR / "done", SPECS_DIR):
        specs, _failures = discover_specs(directory)
        found.update({d.spec.id: d.spec for d in specs})
    return found


def _commit_time(commit: str, cwd: Path = REPO) -> str:
    """`commit`'s committer time the way the ledger writes `started_at`:
    UTC, `YYYY-MM-DD HH:MM:SS`, so the two compare as strings."""
    epoch = int(_git("log", "-1", "--format=%ct", commit, cwd=cwd))
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(epoch))


def _past_cells(
    ledger,
    repo_id: int,
    specs: dict[str, Spec],
    *,
    before: str | None = None,
    exclude: str | None = None,
) -> list[PastCell]:
    budgets = {row["task_id"]: row["budget_usd"] for row in ledger.queue_lines()}
    cells = []
    for (spec_id, _sha), rows in ledger.tasks_by_spec(repo_id).items():
        if spec_id == exclude or spec_id not in specs:
            continue
        spec = specs[spec_id]
        for row in rows:
            attempts = ledger.attempts(row["task_id"])
            if not attempts or (before is not None and attempts[0]["started_at"] >= before):
                continue
            implementing = [
                a for a in attempts if a["phase"] in ("IMPLEMENTING", "REPAIRING")
            ]
            first = implementing[0] if implementing else None
            rest = implementing[1:]
            sizes = [r.summary for r in ledger.task_results(row["task_id"]) if r.gate == "size"]
            cells.append(
                PastCell(
                    spec_id=spec_id,
                    spec_type=spec.type,
                    touches=len(spec.touches),
                    criteria=len(spec.acceptance) or len(spec.acceptance_criteria),
                    started_at=attempts[0]["started_at"],
                    state=row["state"],
                    budget_usd=budgets.get(row["task_id"]),
                    plan=(first["num_turns"] or 0, first["cost_usd_est"] or 0.0)
                    if first is not None
                    else None,
                    implement=(
                        sum(a["num_turns"] or 0 for a in rest),
                        sum(a["cost_usd_est"] or 0.0 for a in rest),
                    ),
                    review_usd=sum(
                        a["cost_usd_est"] or 0.0 for a in attempts if a["phase"] == "REVIEWING"
                    ),
                    rebut_usd=sum(
                        a["cost_usd_est"] or 0.0 for a in attempts if a["phase"] == "REBUTTING"
                    ),
                    endings=[
                        f"{a['phase']} {a['subtype']}"
                        for a in attempts
                        if a["subtype"] not in (None, "success")
                    ],
                    size=sizes[-1] if sizes else None,
                )
            )
    return cells


def _cell_line(c: PastCell) -> str:
    plan = f"plan {c.plan[0]}t ${c.plan[1]:.2f}" if c.plan else "plan -"
    budget = f"${c.budget_usd:.2f}" if c.budget_usd is not None else "-"
    ended = f"  ended: {'; '.join(c.endings)}" if c.endings else ""
    size = f"  size: {c.size}" if c.size else ""
    return (
        f"{c.spec_id}  {c.spec_type}  touches={c.touches} criteria={c.criteria}  "
        f"{c.started_at[:10]}  {c.state}  budget {budget}  {plan}  "
        f"implement {c.implement[0]}t ${c.implement[1]:.2f}  "
        f"review ${c.review_usd:.2f}  rebut ${c.rebut_usd:.2f}{size}{ended}"
    )


def _history_lines(target: Spec, cells: list[PastCell], limit: int = 12) -> list[str]:
    """The target's own shape and ceilings, then past cells of its type, the
    closest in `touches` and criteria count first, newest first on a tie."""
    criteria = len(target.acceptance) or len(target.acceptance_criteria)
    header = (
        f"{target.id}  {target.type}  touches={len(target.touches)} "
        f"criteria={criteria}  max_turns={target.max_turns} "
        f"budget_usd={target.budget_usd}  max_attempts={target.max_attempts}"
    )
    same = [c for c in cells if c.spec_type == target.type]
    same.sort(key=lambda c: c.started_at, reverse=True)
    same.sort(key=lambda c: abs(c.touches - len(target.touches)) + abs(c.criteria - criteria))
    return [header, *(_cell_line(c) for c in same[:limit])]


def cmd_history(args) -> int:
    """What cells of this spec's shape spent before, for the spec reviewer."""
    specs = _known_specs()
    target = specs.get(args.spec_id)
    if target is None:
        return _fail(f"no spec declares {args.spec_id}")
    before = _commit_time(args.before) if args.before else None
    ledger, repo_id, _url = _ledger_and_repo()
    try:
        if repo_id is None:
            return _fail("this repo has no ledger row yet")
        cells = _past_cells(ledger, repo_id, specs, before=before, exclude=args.spec_id)
    finally:
        ledger.close()
    print("\n".join(_history_lines(target, cells, args.limit)))
    return 0
```

Add `from saffron.intake import Spec` under the existing `if TYPE_CHECKING:` block, beside `GateResult`. Register the command in `main()` before `pattern`:

```python
    p = sub.add_parser("history", help="what cells of this spec's shape spent before")
    p.add_argument("spec_id")
    p.add_argument("--before", help="only cells that started before this commit")
    p.add_argument("--limit", type=int, default=12)
    p.set_defaults(func=cmd_history)
```

- [ ] **Step 4: Run the tests, then a mutant.**

Run: `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_spec_loop_driver.py -k "history or commit_time"`
Expected: 4 passed.

Mutant: in `_past_cells`, change `attempts[0]["started_at"] >= before` to `attempts[0]["started_at"] <= before`. Confirm the edit applied with `grep -n 'started_at"\] <= before' .claude/skills/run-saffron-spec-loop/driver.py`, then re-run. Expected: `test_history_before_a_commit_hides_later_cells_and_always_the_specs_own` FAILS. Restore the `>=`.

- [ ] **Step 5: Run it for real.**

Run: `uv run .claude/skills/run-saffron-spec-loop/driver.py history SA-0087 --before 24edb32`
Expected: a header line `SA-0087  bug  touches=2 criteria=6  max_turns=90 budget_usd=14.0 …` (the header shows today's text; `--before` filters cells only), then up to 12 `bug` cells, none of them SA-0087 and none started after 24edb32's commit time.

- [ ] **Step 6: Check and commit.**

```bash
make check > /tmp/check.log 2>&1; echo "make exit: $?"; tail -3 /tmp/check.log
git add .claude/skills/run-saffron-spec-loop/driver.py tests/test_spec_loop_driver.py
git commit -m "feat(spec-loop): nothing told a spec's author what cells of its shape spent, so ceilings were guessed and SA-0087's were short"
```

---

### Task 2: the reviewer agent

**Files:**
- Create: `.claude/agents/spec-reviewer.md`
- Test: `tests/test_spec_reviewer.py`

**Interfaces:**
- Consumes: `driver.py history SA-NNNN [--before COMMIT]` (Task 1)
- Produces: an agent named `spec-reviewer`. It is prompted with `spec: <path>`, `base: <commit>`, and either `history: run it yourself` or `history (precomputed): …`. It returns a markdown report in the shape defined below.

- [ ] **Step 1: Write the failing test.** Create `tests/test_spec_reviewer.py`:

```python
"""The spec reviewer's definition. Its prose is judged by the backtest; this
holds the one property a reader cannot see from a report: it can write nothing."""

from __future__ import annotations

import re
from pathlib import Path

AGENT = Path(__file__).resolve().parents[1] / ".claude" / "agents" / "spec-reviewer.md"


def test_the_spec_reviewer_has_no_tool_that_writes():
    front = AGENT.read_text().split("---")[1]
    tools = re.search(r"^tools:(.*)$", front, re.MULTILINE)
    assert tools is not None
    assert {t.strip() for t in tools.group(1).split(",")} == {"Read", "Grep", "Glob", "Bash"}
```

- [ ] **Step 2: Run it to verify it fails.**

Run: `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_spec_reviewer.py`
Expected: FAIL with `FileNotFoundError`.

- [ ] **Step 3: Write the agent.** Create `.claude/agents/spec-reviewer.md` with exactly this content:

````markdown
---
name: spec-reviewer
description: Reviews one Saffron spec (.saffron/specs/SA-NNNN-*.md) at a base commit, before any cell runs it, on six checks, and reports findings with severities. Read-only — never edits a file and never runs tests. Use before a spec's PR merges, and in the spec loop before a spec's first cell.
tools: Read, Grep, Glob, Bash
---

You review one Saffron spec before a cell spends money on it. A cell is an
agent in a container, driven through gates and an adversarial critic, and a
defect in the spec is paid for by the cell that runs into it. SA-0087 cost
$22.42 over two cells to show its ceilings were too low. Your job is to find
defects like that first.

## Inputs, in your prompt

- `spec:` the spec's path.
- `base:` the commit a cell would be cut from.
- `history:` either output already computed for you (use it and do not run the
  command), or "run it yourself", in which case run
  `uv run .claude/skills/run-saffron-spec-loop/driver.py history <SPEC-ID> --before <base>`.

## Rules

- Read everything at `base`: `git show <base>:<path>`, `git ls-tree -r <base>`,
  `git grep <pattern> <base> -- <paths>`, `git log <base>`. When `base` is
  `HEAD` in a checkout made for you, the working tree is the base, and plain
  Read, Grep and Glob are fine. Never use `git log --all`, and never read a
  commit newer than `base`.
- Bash is for those git commands and `driver.py history` only. You write no
  file and run no test: a spec has no implementation to probe yet.
- Every finding carries evidence you read: a file:line at `base` and the
  quoted text. A claim you could not check is marked **unverified**.

## Read first

1. The spec, frontmatter and body.
2. `CLAUDE.md`, especially "Invariants worth knowing before editing", and
   `CONTEXT.md`, especially the _Avoid_ lines.
3. `docs/agents/issue-tracker.md`'s conventions for `acceptance`, `witness`,
   `mutant` and `preserves`.
4. Every `DESIGN.md` section the spec cites.
5. Every file the spec names, and every file that calls, imports or reads what
   the spec changes. Find them with `git grep` at `base`.

## The six checks

A **blocker** is a defect that, built exactly as the spec says, gets a cell
wrong. A **concern** needs the operator's judgement. A **note** is true but
trivial.

1. **Criteria vs invariants.** For each acceptance claim, ask whether building
   it to the letter breaks a `CLAUDE.md` invariant or a `DESIGN.md` principle.
   If so, it is a blocker; quote both. Example: a criterion ending an
   unappliable patch as `EXHAUSTED`, charged to the task, when the export
   cannot carry a binary change, breaks `error` ≠ `fail`.
2. **Scope reaches the change.** List every file the change must edit:
   callers of any signature it changes, consumers of any value whose meaning
   it changes (a rendered sentence that becomes false counts), tests that
   assert the old behaviour, fixtures. Each one outside `touches` or inside
   `forbidden` is a blocker. Name the line at `base` that makes the file
   necessary.
3. **Witness/mutant discipline.** A spec whose change edits existing code
   declares a `mutant` per criterion. Where one is missing, name a plausible
   wrong implementation its witness would pass; if you can, that is a
   blocker. A `preserves: true` witness must already exist at `base` (use
   `git grep` for the test name). A non-`preserves` witness must not already
   pass at `base`: if the behaviour it claims is already true there, that is
   a blocker.
4. **Ceilings vs history.** Compare `max_turns` and `budget_usd` with the
   `history` rows closest in shape: their plan checkpoint plus IMPLEMENT
   turns and cost. It is a blocker if the spec's ceilings are below what
   similar cells needed for those two phases. It is a concern if what remains
   cannot cover REVIEW and REBUT at the rows' usual cost. Cite the rows you
   compared.
5. **Size vs ceiling.** Estimate the changed lines the criteria, `touches`,
   and the tests they demand imply. Compare with the `size:` summaries in
   similar `history` rows and the ceiling those summaries name. It is a
   blocker when the estimate clearly exceeds the ceiling. Show the estimate.
6. **Claims about current code.** Check every sentence that says what the
   code does now ("Today …", "X returns …", "only when …") against `base`.
   If it is false and a criterion depends on it, it is a blocker; otherwise a
   concern.

## Report

1. **Findings**, most severe first, one bullet each: severity; file:line; the
   rule or criterion it breaks, quoted with its own file:line; what is wrong;
   the evidence; the fix.
2. **Checks**: exactly six lines, one per check, each either
   `checked: <check> — <what you read>` or `found: <check> — findings <n, …>`.
   A check you could not complete says so. It never reads as `checked`.
3. **Assessment**, one sentence: runnable, runnable after the listed fixes, or
   not runnable.
````

- [ ] **Step 4: Run the test.**

Run: `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_spec_reviewer.py`
Expected: 1 passed.

Mutant: add `, Edit` to the `tools:` line, re-run, and expect FAIL. Then restore the line.

- [ ] **Step 5: Smoke-review one live spec.** In the working session, dispatch one background subagent. Use `subagent_type: spec-reviewer` if the session lists it. Otherwise use `general-purpose` with the agent file's body as its instructions. Prompt:
`spec: .saffron/specs/SA-0088-rebut-verdicts-run-in-the-implementers-container.md`, `base: origin/main`, `history: run it yourself`.
Expected: a report with a Findings section, exactly six `checked:`/`found:` lines, and an Assessment. If the shape is off, fix the prompt and re-run once. Save the report to `/tmp/spec-reviewer-smoke.md` for the PR description. It is not committed.

- [ ] **Step 6: Check and commit.**

```bash
make check > /tmp/check.log 2>&1; echo "make exit: $?"; tail -3 /tmp/check.log
git add .claude/agents/spec-reviewer.md tests/test_spec_reviewer.py
git commit -m "feat(agents): no reviewer read a spec before a cell paid to find its defects, so one reads it at its base on six checks"
```

---

### Task 3: where the reviewer runs

**Files:**
- Modify: `.claude/skills/run-saffron-spec-loop/SKILL.md` (a new `## 1b.` between step 1's **Done when** and `## 2. Run each spec`)
- Modify: `docs/agents/issue-tracker.md` (a bullet at the end of `## Conventions`)

**Interfaces:**
- Consumes: the `spec-reviewer` agent (Task 2) and `driver.py history` (Task 1)
- Produces: documentation only

- [ ] **Step 1: Add step 1b to SKILL.md.** Insert this text after step 1's **Done when** paragraph:

```markdown
## 1b. Review each spec before its first cell

Every spec in the order gets one spec review before any cell runs: one
background subagent per spec, dispatched together. Use `subagent_type:
spec-reviewer`, or `general-purpose` handed the body of
`.claude/agents/spec-reviewer.md` if the session started before that file
existed. Prompt each with its spec's path, `base: origin/main`, and
`history: run it yourself`.

Verify each blocker before acting on it: read its line at `origin/main`. A
verified blocker goes to the operator before that spec's cell, as a question:
fix the spec, run it as written, or drop it. Concerns and notes are kept for
step 5. A spec edited here changes its `spec_sha`, so run `snapshot --force`
after the edit merges.

**Done when** every spec in the order has a report with six check lines, and
every verified blocker has the operator's answer.
```

- [ ] **Step 2: Add the spec-writing line to `docs/agents/issue-tracker.md`.** Append this bullet to the end of `## Conventions`:

```markdown
- **Run the spec reviewer before a spec's pull request merges.** It is
  `.claude/agents/spec-reviewer.md`, with `base: origin/main` and
  `history: run it yourself`. Fix its verified blockers in the same pull
  request. Every defect it finds there is a cell that never has to find it
  (`docs/superpowers/specs/2026-09-14-spec-reviewer-design.md`).
```

- [ ] **Step 3: Check and commit.**

```bash
make check > /tmp/check.log 2>&1; echo "make exit: $?"; tail -3 /tmp/check.log
git add .claude/skills/run-saffron-spec-loop/SKILL.md docs/agents/issue-tracker.md
git commit -m "docs(spec-loop): the reviewer existed and nothing ran it, so the loop and the spec guide now do"
```

---

### Task 4: the backtest script and its pre-registration

**Files:**
- Create: `docs/evidence/scripts/2026-09-14-spec-reviewer-backtest.py`
- Create: `docs/evidence/<date>-spec-reviewer-backtest.md`, where `<date>` is `date +%F` on the day of the pre-registration commit

**Interfaces:**
- Consumes: `driver.py` (`_ledger_and_repo`, `history`), `.claude/agents/spec-reviewer.md`, the design's Appendix A
- Produces:
  - `controls` subcommand: prints the 10 controls as markdown rows
  - `review` subcommand: one headless review per case and control, writing `docs/evidence/spec-reviewer-backtest/<SPEC>-<version>.md` and `.json`

- [ ] **Step 1: Write the script.** Create `docs/evidence/scripts/2026-09-14-spec-reviewer-backtest.py`:

```python
"""Backtest the spec reviewer (docs/superpowers/specs/2026-09-14-spec-reviewer-design.md).

    uv run docs/evidence/scripts/2026-09-14-spec-reviewer-backtest.py controls
    uv run docs/evidence/scripts/2026-09-14-spec-reviewer-backtest.py review [--only SA-NNNN@sha]

Spends money: one headless `claude -p` session per spec version, each in a
detached worktree at that version, so the reviewer can read nothing newer.
`history` is computed here with `--before` and handed in, because the driver at
an old version has no `history` command.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
DRIVER = REPO / ".claude" / "skills" / "run-saffron-spec-loop" / "driver.py"
AGENT = REPO / ".claude" / "agents" / "spec-reviewer.md"
OUT = REPO / "docs" / "evidence" / "spec-reviewer-backtest"
TOOLS = "Read,Grep,Glob,Bash(git show:*),Bash(git log:*),Bash(git ls-tree:*),Bash(git grep:*)"
FIRST_CELL_OK = {"READY_FOR_REVIEW", "APPROVED", "MERGE_TRAIN", "MERGED"}

# The design's Appendix A, minus its four excluded rows: (spec, pre-cell version, defects).
CASES = [
    ("SA-0005", "351bdd3", ["touches lacked cli.py and package.py, which its criteria needed"]),
    ("SA-0009", "ad94fd2", ["too wide: 990 lines against a 600 ceiling"]),
    ("SA-0011", "1e069af", ["tests/test_package.py Spec fakes outside touches"]),
    ("SA-0014", "e1090dc", ["false claim about SA-0005's criteria"]),
    ("SA-0016", "e1090dc", ["false claim that its refusal fires on SA-0005"]),
    ("SA-0018", "366e377", ["forbade DESIGN.md/CONTEXT.md, which the change made false"]),
    ("SA-0019", "6f8e0d7", ["orphan criterion broke an invariant"]),
    ("SA-0020", "86f0c6e", ["forbade saffron/phases/**, which the fix needed"]),
    ("SA-0025", "2e4f2e6", ["too wide for its ceilings"]),
    ("SA-0026", "0301518", ["test file holding a guard outside touches"]),
    ("SA-0029", "3ed6f83", ["too wide: plan at 1100 lines against 600"]),
    ("SA-0029", "98ce586", ["14 criteria demand tests past the 600 ceiling"]),
    ("SA-0031", "0bcf5ac", ["turn and budget ceilings too low for its width"]),
    ("SA-0043", "a205a90", ["golden fixture, test_events.py, test_session.py outside touches"]),
    ("SA-0044", "6ceb5ba", [
        "criterion 2's witness proves only the half already true",
        "criterion 4's real witness needs tests/test_worktree.py, outside touches",
    ]),
    ("SA-0051", "5177edb", ["three mechanisms; 650 lines against 600"]),
    ("SA-0059", "ab42114", ["nine files at elevated: too wide for its ceilings"]),
    ("SA-0063", "6527f73", [
        "forbade saffron/phases/**, home of the only call site",
        "the body dictates the literals its mutants pin",
    ]),
    ("SA-0065", "d84cab3", ["forbidden excludes a caller the change breaks"]),
    ("SA-0079", "1e2209a", ["missing mutant: the memo witness only answers 'present'"]),
    ("SA-0080", "1e2209a", ["missing mutant: headline witness passes a full re-parse"]),
    ("SA-0081", "1e2209a", ["missing mutant: a misplaced boundary passes"]),
    ("SA-0082", "c0e84c3", ["its table calls a non-equivalent alternative equivalent"]),
    ("SA-0083", "c0e84c3", ["missing mutant: deleting the override stays green"]),
    ("SA-0084", "c0e84c3", ["missing mutant: a partial strip passes 'every control character'"]),
    ("SA-0085", "c0e84c3", ["missing mutant: two witnesses each cover half a claim"]),
    ("SA-0086", "8811f3a", [
        "forbade pr_body.py, which the change made false",
        "no mutants on an edit, so a witness that cannot fail ships",
        "'verdict' used in the sense CONTEXT.md forbids",
    ]),
    ("SA-0087", "24edb32", [
        "60 turns / $8 against a 47-turn plan checkpoint",
        "criterion 3 charges an unappliable binary stub to the task",
    ]),
    ("SA-0087", "14f6357", ["criterion 2's witness passes with read_head on the wrong container"]),
]
# Appendix A and B ids: no control comes from either.
BLAMED = {spec for spec, _v, _d in CASES} | {
    "SA-0001", "SA-0013", "SA-0017", "SA-0021", "SA-0022", "SA-0041", "SA-0042",
    "SA-0045", "SA-0046", "SA-0048", "SA-0049", "SA-0050", "SA-0052", "SA-0058",
    "SA-0064", "SA-0066", "SA-0067", "SA-0068", "SA-0069", "SA-0070", "SA-0071",
    "SA-0072", "SA-0073", "SA-0077", "SA-0088", "SA-0089",
}
# Filled from `controls` in the pre-registration commit, never after a review.
CONTROLS: list[tuple[str, str]] = []


def _git(*args: str, cwd: Path = REPO) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def _driver():
    spec = importlib.util.spec_from_file_location("spec_loop_driver", DRIVER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def cmd_controls(_args) -> int:
    """The 10 most recent done/ specs in neither appendix whose first cell reached
    READY_FOR_REVIEW, each at the last commit touching it before that cell."""
    from saffron.intake import discover_specs

    driver = _driver()
    done = {d.spec.id for d in discover_specs(REPO / ".saffron" / "specs" / "done")[0]}
    ledger, repo_id, _url = driver._ledger_and_repo()
    try:
        first: dict[str, tuple[int, str]] = {}
        for (spec_id, _sha), rows in ledger.tasks_by_spec(repo_id).items():
            for row in rows:
                if spec_id not in first or row["task_id"] < first[spec_id][0]:
                    first[spec_id] = (row["task_id"], row["state"])
        picked = []
        for spec_id, (task_id, state) in first.items():
            if spec_id not in done or spec_id in BLAMED or state not in FIRST_CELL_OK:
                continue
            attempts = ledger.attempts(task_id)
            if attempts:
                picked.append((attempts[0]["started_at"], spec_id))
    finally:
        ledger.close()
    for started, spec_id in sorted(picked, reverse=True)[:10]:
        version = _git(
            "log", "-1", "--format=%h", f"--before={started} +0000", "--",
            f":(glob).saffron/specs/**/{spec_id}-*.md", f":(glob).saffron/specs/{spec_id}-*.md",
        )
        print(f"| {spec_id} | {version} | {started} |")
    return 0


def _agent_json() -> str:
    _, front, body = AGENT.read_text().split("---", 2)
    meta = yaml.safe_load(front)
    return json.dumps({"spec-reviewer": {"description": meta["description"], "prompt": body.strip()}})


def _spec_path(spec_id: str, version: str) -> str:
    names = _git("ls-tree", "-r", "--name-only", version, ".saffron/specs").splitlines()
    match = [n for n in names if n.rsplit("/", 1)[-1].startswith(f"{spec_id}-")]
    if len(match) != 1:
        raise SystemExit(f"{spec_id}@{version}: {len(match)} spec files, expected 1")
    return match[0]


def _review(spec_id: str, version: str) -> None:
    path = _spec_path(spec_id, version)
    history = subprocess.run(
        ["uv", "run", str(DRIVER), "history", spec_id, "--before", version],
        cwd=REPO, check=True, capture_output=True, text=True,
    ).stdout
    prompt = (
        f"spec: {path}\nbase: HEAD (this checkout is the base commit)\n"
        f"history (precomputed; do not run the command):\n{history}"
    )
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / f"{spec_id}-{version}"
        _git("worktree", "add", "-q", "--detach", str(tree), version)
        try:
            done = subprocess.run(
                ["claude", "-p", "--agents", _agent_json(), "--agent", "spec-reviewer",
                 "--output-format", "json", "--permission-prompts", "none",
                 "--allowedTools", TOOLS, prompt],
                cwd=tree, capture_output=True, text=True, timeout=1800,
            )
        finally:
            _git("worktree", "remove", "--force", str(tree))
    if done.returncode != 0:
        raise SystemExit(f"{spec_id}@{version}: claude exited {done.returncode}: {done.stderr[-500:]}")
    result = json.loads(done.stdout)
    OUT.mkdir(parents=True, exist_ok=True)
    stem = OUT / f"{spec_id}-{version}"
    stem.with_suffix(".md").write_text(result.get("result") or "")
    keep = {k: result.get(k) for k in ("total_cost_usd", "num_turns", "is_error", "subtype")}
    stem.with_suffix(".json").write_text(json.dumps(keep, indent=1) + "\n")
    print(f"{spec_id}@{version}  ${keep['total_cost_usd'] or 0:.2f}  {keep['num_turns']} turns")


def cmd_review(args) -> int:
    targets = [(s, v) for s, v, _d in CASES] + CONTROLS
    if args.only:
        targets = [t for t in targets if f"{t[0]}@{t[1]}" == args.only]
    for spec_id, version in targets:
        if (OUT / f"{spec_id}-{version}.md").exists():
            continue  # resumable: a finished review is never re-bought
        _review(spec_id, version)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("controls").set_defaults(func=cmd_controls)
    p = sub.add_parser("review")
    p.add_argument("--only", help="SA-NNNN@sha")
    p.set_defaults(func=cmd_review)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Check that every case resolves before spending anything.**

Run: `uv run python -c "import importlib.util,sys; s=importlib.util.spec_from_file_location('b','docs/evidence/scripts/2026-09-14-spec-reviewer-backtest.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); [print(c[0], c[1], m._spec_path(c[0], c[1])) for c in m.CASES]; print(len(m.CASES), sum(len(c[2]) for c in m.CASES))"`
Expected: 29 lines, one spec path each, then `29 34`. A `SystemExit` naming a case means that version is wrong. Fix it from `git log -- '.saffron/specs/**/<SPEC>-*'`, and note the correction in the evidence file.

- [ ] **Step 3: Select the controls.**

Run: `uv run docs/evidence/scripts/2026-09-14-spec-reviewer-backtest.py controls`
Expected: 10 rows of the form `| SA-00NN | <sha> | <started_at> |`. Paste the ten `(spec, sha)` pairs into `CONTROLS`, in the printed order.

- [ ] **Step 4: Smoke-review one case.**

Run: `uv run docs/evidence/scripts/2026-09-14-spec-reviewer-backtest.py review --only SA-0087@24edb32`
Expected: a line `SA-0087@24edb32  $<cost>  <n> turns`, and a report at `docs/evidence/spec-reviewer-backtest/SA-0087-24edb32.md` with six check lines. Confirm that the `.json` has a non-null `total_cost_usd`. If the CLI's JSON keys differ, fix `keep` to match. **Do not read this report to adjust the prompt:** that would tune the reviewer against a scored case. Delete both files so the review is rerun cleanly with the others.

- [ ] **Step 5: Write the pre-registration.** Create `docs/evidence/<date>-spec-reviewer-backtest.md`:

```markdown
# Spec reviewer backtest

Pre-registered <date>, before any scored review, in the commit that adds this
file. Design: `docs/superpowers/specs/2026-09-14-spec-reviewer-design.md`.
Script: `docs/evidence/scripts/2026-09-14-spec-reviewer-backtest.py`.

## The bar

The reviewer passes if it catches **at least 17 of the 34 known defects** and
raises **at most 2 false blockers across the 10 controls**.

## Scoring

- A known defect is **caught** when a `blocker` or `concern` names the same file
  or criterion and the same kind of defect. Blocker-only recall is reported
  as well.
- A blocker on a control is **false** when its claim does not hold on reading
  the code at the control's version. A blocker whose claim holds is a new find,
  not a false alarm. The operator settles any disputed call.
- Each version is reviewed once, blind: a detached worktree at the version,
  `history --before` the version, and no outcome in the prompt.

## Known defects

<the 29 CASES rows as a table: spec | version | defects>

## Controls

<the 10 rows `controls` printed>

## Results

Not yet run.
```

Fill the two tables from `CASES` and `controls`' output. The tables are data, not placeholders.

- [ ] **Step 6: Check and commit the pre-registration, before any scored review.**

```bash
make check > /tmp/check.log 2>&1; echo "make exit: $?"; tail -3 /tmp/check.log
git add docs/evidence/scripts/2026-09-14-spec-reviewer-backtest.py docs/evidence/<date>-spec-reviewer-backtest.md
git commit -m "docs(evidence): the spec reviewer's backtest bar, cases and controls, committed before any review so the result cannot move them"
git push -q origin HEAD
```

The push is what makes the ordering verifiable to someone other than the delegate.

---

### Task 5: run, score, record

**Files:**
- Modify: `docs/evidence/<date>-spec-reviewer-backtest.md` (the `## Results` section)
- Create: `docs/evidence/spec-reviewer-backtest/*.md` and `*.json`, 39 pairs

**Interfaces:**
- Consumes: Task 4's script and pre-registration
- Produces: pass or fail against the bar, for the operator to decide on promotion

- [ ] **Step 1: Run every review.**

Run: `uv run docs/evidence/scripts/2026-09-14-spec-reviewer-backtest.py review`, in the background. It can be resumed; re-run it after any failure.
Expected: 39 lines, and 39 `.md`/`.json` pairs in `docs/evidence/spec-reviewer-backtest/`.

- [ ] **Step 2: Score the known defects.** For each of the 29 versions, read its report and each recorded defect. Mark each defect `blocker`, `concern` or `missed`, citing the finding's number. The rule is the pre-registered one: same file or criterion, and the same kind. Count the caught (blocker plus concern) and the blocker-only.

- [ ] **Step 3: Score the controls.** For each blocker on a control, read its cited line at the control's version. Mark it `false` or `new find`, with the evidence. List any disputed call for the operator rather than settling it.

- [ ] **Step 4: Write the results.** Replace `Not yet run.` with:
  - a per-case table: spec | version | defect | caught as | finding;
  - a per-control table: spec | version | blockers | false | new finds;
  - the totals, `caught N/34 (blocker-only M/34)` and `false blockers K/10 controls`;
  - one line, **PASS** or **FAIL** against the bar;
  - total cost from the `.json` files;
  - each new find, as a candidate backlog item.

- [ ] **Step 5: Check and commit.**

```bash
make check > /tmp/check.log 2>&1; echo "make exit: $?"; tail -3 /tmp/check.log
git add docs/evidence/<date>-spec-reviewer-backtest.md docs/evidence/spec-reviewer-backtest/
git commit -m "docs(evidence): the spec reviewer caught N of 34 recorded spec defects with K false blockers, against a bar of 17 and 2"
```

Write the real N and K into the subject.

- [ ] **Step 6: Report to the operator.** Give them the result, the two rates, the cost, and the new finds. Promotion to a spec-review cell (DESIGN.md §3.3/§5.2 by hand, then a spec) is their decision, and so is trying two seats on a FAIL.
