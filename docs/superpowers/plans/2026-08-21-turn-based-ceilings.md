# Turn-Based Ceilings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move saffron's cells from `ANTHROPIC_API_KEY` to a Claude Code subscription token, and re-base N2's ceilings from USD onto turns — the unit the host can still trust once nobody is being billed per token.

**Architecture:** The cell receives `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) instead of an API key. Because a subscription is not billed per token, the runtime's `total_cost_usd` stops being a quantity the supervisor can hold a ceiling against. The ceiling moves to `num_turns`, which the runtime already reports, which `AttemptResult` already carries, and which the in-cell `max_turns` bound already speaks. Host and cell then count the same unit for the first time. `cost_usd_est` is **kept as recorded telemetry everywhere it appears** — it stops being load-bearing, it does not get deleted.

**Tech Stack:** Python 3.12, `claude-agent-sdk` (in-cell only), `pydantic`, `sqlite3`, `pytest`, `apple/container` 1.2.2.

**Spec:** `DESIGN.md` — the N2 row (`:47`), the in-cell-vs-host ceiling argument (`:357`), and §5.1's credential exception (`:491`). This plan rewrites all three.

## Status — Task 1 has run, and it invalidated this plan's premise

`docs/evidence/2026-08-21-subscription-turn-accounting.md`, 2026-08-21.

**`total_cost_usd` is not zero under subscription auth.** It reports real per-turn figures ($3.88 across 65 turns for `SA-0004`). The plan was written on the assumption that the host had been left summing a meaningless number. It had not — the number stopped meaning *money*, not stopped existing.

Consequences, before executing anything below:

- **Tasks 3, 5, 6, 8 (the turn re-base) are not justified by the measurement.** They change a unit and buy no new guarantee. Do not execute them without a fresh decision.
- **Task 7 must not run.** Its own Step 1 guard fires: cost is non-zero, so `max_budget_usd` still works and deleting it would remove a functioning bound.
- **Task 2 (credential swap) stands** — it is coded, green, and correct on its own terms.
- **Task 4 (rate limit) is the finding worth having.** It is the only ceiling the cell is subject to rather than reporting, and discarding it currently misdiagnoses a provider limit as `EXHAUSTED`.

The §5.1 rewrite in Task 2 Step 3 remains correct as written: it argues from the rate limit, not from the dollar figure.

---

## Global Constraints

- **The host never imports `claude_agent_sdk`** (pyproject `:6`). Every SDK fact is asserted against a plain dict.
- **`cost_usd_est` / `cost_usd` fields are preserved**, in `AttemptResult`, `LensReview`, `RebuttalTurn`, `LensVerdicts`, `QueueLine`, and the ledger. They keep recording. They stop deciding.
- **Turns are integers.** `spent` becomes `int`; no float formatting on a turn count.
- **One credential in a cell, ever** (§5.1). `ANTHROPIC_API_KEY` must not reach a cell even when the host exports one.
- **Defaults in this plan are provisional** until Task 1 measures. Every one is commented as a calibration knob, per DESIGN.md's rule that a measured constant and an assumed one are different things.
- Run tests with `.venv/bin/python -m pytest`. `ruff` is not installed on the host — it runs in a cell via the `format`/`lint` gates.
- `tests/test_saffron_gates.py::test_a_red_run_is_a_failure_even_when_a_test_is_named_for_a_crash` **fails on `main` already**. It is not yours; do not fix it in this plan.

---

### Task 1: Measure what a subscription session actually reports

This gates every number in the plan. DESIGN.md's own standard (Appendix I, the vCPU offset) is that a constant is measured or it is a bug. Nothing after this task should invent a default.

**Files:**
- Create: `docs/evidence/2026-08-21-subscription-turn-accounting.md`

**Interfaces:**
- Consumes: nothing.
- Produces: three measured integers used as defaults in Tasks 3–5 — `BUDGET_TURNS_DEFAULT`, `REVIEW_FLOOR_TURNS`, and confirmation of whether `total_cost_usd` is zero, notional, or absent under subscription auth.

- [ ] **Step 1: Confirm the token is in the environment**

```bash
test -n "$CLAUDE_CODE_OAUTH_TOKEN" && echo "token present" || echo "run: claude setup-token"
```

Expected: `token present`. If not, stop — the rest of this task cannot run.

- [ ] **Step 2: Run one attended cell end to end**

```bash
.venv/bin/python -m saffron.cli cell <path/to/spec.md> --repo <path/to/repo>
```

Watch the `IMPLEMENT: N commit(s), $X.XX spent` lines. Record every one.

- [ ] **Step 3: Read the raw result events out of the run**

The `agent:` watch line in `saffron/phases/implement.py:156` prints `subtype`, `num_turns`, `total_cost_usd` and `terminal_reason` for every turn. Capture all of them.

- [ ] **Step 4: Write the evidence note**

Record, as a table with one row per turn: phase (PLAN / IMPLEMENT / REPAIR / REVIEW / REBUT), `num_turns`, `total_cost_usd`. Then state three conclusions explicitly:

1. Whether `total_cost_usd` is `0`, a notional dollar figure, or absent under subscription auth.
2. The summed `num_turns` for one complete task — this becomes `BUDGET_TURNS_DEFAULT`, rounded up with headroom.
3. Whether `max_budget_usd` fired at any point. If `total_cost_usd` is zero it cannot have, which is the evidence Task 7 rests on.

- [ ] **Step 5: Commit**

```bash
git add docs/evidence/2026-08-21-subscription-turn-accounting.md
git commit -m "docs(evidence): what a subscription session reports per turn"
```

---

### Task 2: Land the credential swap

The code for this is **already written and green** in the working tree. This task adds the documentation half so the commit is self-consistent.

**Files:**
- Modify: `saffron/cell/session.py:231-245` (already done — verify only)
- Modify: `tests/test_session.py:765-795` (already done — verify only)
- Modify: `DESIGN.md:474` and `DESIGN.md:491`

**Interfaces:**
- Consumes: nothing.
- Produces: `cell_env(proxy_ip: str, thread_env: Mapping[str, str]) -> dict[str, str]`, forwarding `CLAUDE_CODE_OAUTH_TOKEN` and never `ANTHROPIC_API_KEY`.

- [ ] **Step 1: Verify the existing change is green**

Run: `.venv/bin/python -m pytest tests/test_session.py -k cell_env -v`
Expected: PASS, 2 tests — `test_the_cell_env_carries_the_proxy_and_the_state_dir` and `test_the_cell_env_never_carries_an_api_key`.

- [ ] **Step 2: Update the §5.1 cell-construction block**

In `DESIGN.md`, in the fenced block at `:474`, replace the line `  -e ANTHROPIC_API_KEY \` with:

```
  -e CLAUDE_CODE_OAUTH_TOKEN \
```

- [ ] **Step 3: Rewrite the credential exception paragraph**

Replace the paragraph at `DESIGN.md:491` (it begins `**The exception is \`ANTHROPIC_API_KEY\``) with:

```markdown
  **The exception is `CLAUDE_CODE_OAUTH_TOKEN`, and it is stated here because an unstated exception is an abandoned rule (Appendix F, principle 29).** The agent cannot run without a credential, so the cell holds exactly one, and the blast radius of that is the subscription's rate limit rather than data — which is why it is tolerable and why §2's boundary claim is written in terms of *target-repo* credentials. Rev 11 struck the API key in its favour, and the reason is the ceiling: a key's spend is bounded only by an accounting sum over numbers the cell reports, whereas a subscription's rate limit is enforced by the provider and holds **without the cell's cooperation** — the property this section previously had to reach for a monthly cap to obtain. The token comes from `claude setup-token`, which is minted for exactly this and is revocable on its own, so the "separate credential for the factory" mitigation is kept rather than lost: revoking it does not touch interactive work. What is genuinely given up is isolation of *contention* — a runaway cell burns the same rate-limit pool the operator is working in, so the failure mode moves from an unexpected bill to a tool that stops responding. That is a worse day and a cheaper one. A host `ANTHROPIC_API_KEY` is deliberately **not** forwarded even when present, and a test asserts it, because that is the regression that would restore the old design in silence. Moving custody into the proxy remains the principled fix and remains unavailable: `CONNECT` tunnels are opaque, so the proxy cannot inject a header it cannot see.
```

- [ ] **Step 4: Confirm no code path still reads the key**

Run: `grep -rn 'ANTHROPIC_API_KEY' saffron images --include='*.py' --include='*.Dockerfile'`
Expected: exactly one hit — the explanatory comment in `saffron/cell/session.py`. No `os.environ.get`.

- [ ] **Step 5: Commit**

```bash
git add saffron/cell/session.py tests/test_session.py DESIGN.md
git commit -m "feat(cell): a subscription token, not an API key

The ceiling is the reason. A key's spend is bounded only by the sum of
what the cell reports; a subscription's rate limit is provider-side and
holds without the cell's cooperation, which is the property §5.1 had to
reach for a monthly cap to get. setup-token keeps the credential
separately revocable. A host API key is no longer forwarded, and a test
asserts it — that is the regression that would be silent."
```

---

### Task 3: The ceiling itself

**Files:**
- Modify: `saffron/cell/session.py:43-55` (the floor constant and `critic_budget`)
- Modify: `saffron/cell/session.py:72` (`CellSpec.budget_usd`)
- Modify: `saffron/cell/session.py:508-520` (`_over_budget`)
- Modify: `saffron/cell/session.py:539-543`, `:585-589` (the `spent` accumulators)
- Test: `tests/test_session.py`

**Interfaces:**
- Consumes: `BUDGET_TURNS_DEFAULT` and `REVIEW_FLOOR_TURNS` measured in Task 1.
- Produces: `REVIEW_FLOOR_TURNS: int`; `critic_turns(budget_turns: int, spent: int) -> int`; `CellSpec.budget_turns: int`. `CellSpec.budget_usd` ceases to exist.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_session.py`:

```python
def test_critic_turns_is_the_remainder_never_below_the_floor():
    """REVIEW is not gated on the ceiling — a green diff nobody reviewed is
    not a product — so a critic gets what is left, and never nothing."""
    assert session.critic_turns(150, 100) == 50
    assert session.critic_turns(150, 149) == session.REVIEW_FLOOR_TURNS
    assert session.critic_turns(150, 400) == session.REVIEW_FLOOR_TURNS


def test_critic_turns_returns_a_whole_number_of_turns():
    """A turn count that formats as 12.5 is a USD ceiling wearing a new name."""
    budget = session.critic_turns(150, 100)
    assert isinstance(budget, int)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_session.py -k critic_turns -v`
Expected: FAIL with `AttributeError: module 'saffron.cell.session' has no attribute 'critic_turns'`

- [ ] **Step 3: Replace the floor constant and the helper**

In `saffron/cell/session.py`, replace the `REVIEW_FLOOR_USD` block and `critic_budget` (`:43-55`) with:

```python
# REVIEW is deliberately not gated on the ceiling — a green diff nobody
# reviewed is not a product — so its sessions are capped at what is left rather
# than at the whole task budget, which is how a 150-turn task spends 400. The
# floor is what keeps "not gated" true when nothing is left: below it a lens
# would be refused for having no room, and the task would reach the operator
# unreviewed. REBUT *is* gated (`_over_turns` before the rebuttal turn): by then
# the findings are written and the operator has something to read either way.
# ponytail: 25 is a sixth of the default budget, the ratio the USD floor had.
# Re-measure it with the budget — docs/evidence/2026-08-21-subscription-turn-accounting.md.
REVIEW_FLOOR_TURNS = 25


def critic_turns(budget_turns: int, spent: int) -> int:
    """The per-session turn cap for one critic turn: the remainder, never zero."""
    return max(budget_turns - spent, REVIEW_FLOOR_TURNS)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_session.py -k critic_turns -v`
Expected: PASS, 2 tests

- [ ] **Step 5: Move `CellSpec` onto turns**

In `saffron/cell/session.py:72`, replace `budget_usd: float = 12.0` with:

```python
    # Per *task*, summed across every session by the host. `max_turns` below is
    # per *session* and is evaluated in the cell — different scope, same unit,
    # which is the point of the change (§4.3).
    # ponytail: provisional until measured; see the Task 1 evidence note.
    budget_turns: int = 150
```

- [ ] **Step 6: Write the failing test for the host ceiling**

Add to `tests/test_session.py`:

```python
def test_the_host_ceiling_counts_turns_not_dollars(monkeypatch):
    """N2's ceiling has to hold when every cost field reads zero — which is
    what a subscription session reports (§5.1)."""
    spec = _cell_spec(budget_turns=10)
    assert spec.budget_turns == 10
    assert not hasattr(spec, "budget_usd")
```

If `tests/test_session.py` has no `_cell_spec` helper, construct a `session.CellSpec` inline with the required positional fields (`spec_id`, `spec_sha`, `branch`, `base_sha`, `touches`, `spec_type`, `body`) instead.

- [ ] **Step 7: Run it to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_session.py -k counts_turns_not_dollars -v`
Expected: FAIL — `budget_usd` still present, or `budget_turns` unknown.

- [ ] **Step 8: Convert the gate and the accumulators**

In `saffron/cell/session.py`, replace the `_over_budget` definition (`:510-520`) with:

```python
        def _over_turns() -> bool:
            """The host-side ceiling. `max_turns` is per session and is
            evaluated inside the cell; this is the sum the supervisor holds
            against the task's own budget (§4.3). Turns, not dollars: a
            subscription session reports no cost to hold a ceiling against."""
            if spent < spec.budget_turns:
                return False
            watch(f"budget: {spent} of {spec.budget_turns} turns — stopping")
            return True
```

Then, in the same function:
- change the `spent = 0.0` initialisation to `spent = 0`
- replace both `spent += implemented.cost_usd_est` and `spent += repaired.cost_usd_est` with `spent += implemented.num_turns` and `spent += repaired.num_turns`
- replace both `if _over_budget():` call sites with `if _over_turns():`
- change the watch line `f"IMPLEMENT: {commits} commit(s), ${spent:.2f} spent"` to `f"IMPLEMENT: {commits} commit(s), {spent} turns spent"`
- leave `last_cost = implemented.cost_usd_est` and `last_cost = repaired.cost_usd_est` **exactly as they are** — `last_cost_usd` is the crashed-turn cost fallback in `implement.py:302`, it is telemetry, and it is not a ceiling.

- [ ] **Step 9: Convert the plan checkpoint**

In `plan_checkpoint` (`saffron/cell/session.py:134-170`), change `spent = 0.0` to `spent = 0`, `spent = attempt.cost_usd_est` to `spent = attempt.num_turns`, and `spent += attempt.cost_usd_est` to `spent += attempt.num_turns`. Leave the `replace(prior, cost_usd_est=spent + prior.cost_usd_est)` line — change it to carry turns instead:

```python
        prior = failed.attempt or _failed_turn(failed, "")
        failed.attempt = replace(prior, num_turns=spent + prior.num_turns)
        raise
```

Update its return type annotation from `tuple[AttemptResult, str, float]` to `tuple[AttemptResult, str, int]`.

- [ ] **Step 10: Run the full suite**

Run: `.venv/bin/python -m pytest tests/test_session.py -v`
Expected: PASS. Any failure naming `budget_usd` is a call site Task 5 or 5 owns — note it and continue.

- [ ] **Step 11: Commit**

```bash
git add saffron/cell/session.py tests/test_session.py
git commit -m "feat(cell): the ceiling counts turns

A subscription session reports no cost to hold a dollar ceiling against.
num_turns is already reported, already on AttemptResult, and already what
the in-cell max_turns bound speaks — so host and cell now count the same
unit. cost_usd_est keeps recording; it stops deciding."
```

---

### Task 4: Surface the rate limit the cell is actually subject to

**Discovered during Task 1's run, not designed in advance.** The stream carries `agent: passthrough RateLimitEvent` — the runtime reports rate-limit state under subscription auth, and `agent_runner.events()` drops it on the floor. That matters twice over. It is the first ceiling in this design that the cell is genuinely *subject to* rather than merely *reporting*, which is the property §5.1 has always wanted. And discarding it is now a live bug: a `rejected` window makes every turn fail, so the repair loop burns four attempts against a wall and reports `EXHAUSTED` — a provider limit misdiagnosed as task difficulty, which is exactly the one-state-for-two-causes failure §3.3 exists to prevent.

`RateLimitInfo` (verified in `claude_agent_sdk` inside `saffron/cell-base:python`) carries `status` (`allowed` / `allowed_warning` / `rejected`), `utilization` (0.0–1.0), `resets_at` (unix timestamp), and `rate_limit_type`.

**Files:**
- Modify: `images/agent_runner.py:68-103` (the `events` mapping)
- Modify: `saffron/phases/implement.py:64-77` (`AttemptResult`), and its event reader
- Modify: `saffron/cell/session.py` (the terminal state), `saffron/cli.py:26` (`CELL_EXIT`)
- Modify: `DESIGN.md:47`
- Test: `tests/test_agent_runner.py`, `tests/test_implement.py`, `tests/test_session.py`

**Interfaces:**
- Consumes: `AttemptResult` from Task 3.
- Produces: a `{"type": "rate_limit", ...}` event; `AttemptResult.rate_limit_status: str | None` and `AttemptResult.rate_limit_resets_at: int | None`; the terminal state `RATE_LIMITED`.

- [ ] **Step 1: Write the failing test for the event mapping**

Add to `tests/test_agent_runner.py`:

```python
def test_a_rate_limit_event_is_not_a_passthrough():
    """The one ceiling the cell is subject to rather than reporting. Dropped,
    a rejected window reads to the host as four hard repair attempts."""

    class FakeInfo:
        status = "allowed_warning"
        utilization = 0.82
        resets_at = 1755800000

    class FakeEvent:
        rate_limit_info = FakeInfo()
        uuid = "u"
        session_id = "s"

    (event,) = agent_runner.events(FakeEvent())
    assert event["type"] == "rate_limit"
    assert event["status"] == "allowed_warning"
    assert event["utilization"] == 0.82
    assert event["resets_at"] == 1755800000
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_agent_runner.py -k rate_limit -v`
Expected: FAIL — `assert 'passthrough' == 'rate_limit'`

- [ ] **Step 3: Map the event**

In `images/agent_runner.py`, insert at the top of `events()`, immediately after the docstring and **before** the result branch (a `RateLimitEvent` carries `session_id` but no `num_turns`, so it cannot collide with the result check — the ordering comment there stays true):

```python
    # The provider's own ceiling, and the only one the cell is subject to
    # rather than merely reporting (§5.1). A passthrough here is a rejected
    # window arriving at the host as four failed repair attempts (§3.3).
    if (info := getattr(message, "rate_limit_info", None)) is not None:
        return [
            {
                "type": "rate_limit",
                "status": getattr(info, "status", None),
                "utilization": getattr(info, "utilization", None),
                "resets_at": getattr(info, "resets_at", None),
            }
        ]
```

- [ ] **Step 4: Run it to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_agent_runner.py -k rate_limit -v`
Expected: PASS

- [ ] **Step 5: Write the failing test for the terminal state**

Add to `tests/test_session.py`:

```python
def test_a_rejected_window_is_not_exhaustion():
    """§3.3: a provider limit and a task that could not pass its own gates are
    different outcomes, and one state for both is how the operator is misled."""
    assert session.terminal_for_rate_limit("rejected") == "RATE_LIMITED"
    assert session.terminal_for_rate_limit("allowed_warning") is None
    assert session.terminal_for_rate_limit("allowed") is None
    assert session.terminal_for_rate_limit(None) is None
```

- [ ] **Step 6: Run it to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_session.py -k rejected_window -v`
Expected: FAIL with `AttributeError: module 'saffron.cell.session' has no attribute 'terminal_for_rate_limit'`

- [ ] **Step 7: Carry the status onto `AttemptResult` and act on it**

In `saffron/phases/implement.py`, add two fields to `AttemptResult` beside `bound: str = ""`:

```python
    # The last rate-limit status the turn reported, and when its window
    # reopens. Not a cost: a ceiling the provider enforces (§5.1).
    rate_limit_status: str | None = None
    rate_limit_resets_at: int | None = None
```

In the function that folds the event stream into an `AttemptResult` (the one reading `result.get("num_turns")` around `:280`), track the most recent `rate_limit` event seen and pass its `status` and `resets_at` into the constructed `AttemptResult`.

In `saffron/cell/session.py`, add beside the other helpers:

```python
def terminal_for_rate_limit(status: str | None) -> str | None:
    """The provider said no. That is not the task failing its own gates, and
    reporting it as EXHAUSTED is how an operator retries a wall (§3.3)."""
    return "RATE_LIMITED" if status == "rejected" else None
```

Then, in `run_one_cell`, after each `agent(...)` call returns, check it before the ceiling:

```python
        if stopped := terminal_for_rate_limit(implemented.rate_limit_status):
            resets = implemented.rate_limit_resets_at
            watch(f"rate limit: rejected, window reopens at {resets} — stopping")
            ledger.set_task_state(task_id, stopped)
            ledger.finish_run(run_id, "COMPLETE")
            return stopped
```

Apply the same guard in `_repair`, returning `stopped` so the repair loop halts rather than spending its remaining attempts.

- [ ] **Step 8: Give the new state an exit code**

In `saffron/cli.py:26`, extend `CELL_EXIT`:

```python
CELL_EXIT = {
    "READY_FOR_REVIEW": 0,
    "PREFLIGHT_FAILED": 2,
    "GATE_ERROR": 2,
    # Not the task's failure and not the operator's — retry after the window.
    "RATE_LIMITED": 2,
}
```

- [ ] **Step 9: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_session.py tests/test_agent_runner.py tests/test_implement.py -v`
Expected: PASS

- [ ] **Step 10: Record the state in DESIGN.md**

In `DESIGN.md:47`, extend the N2 row written in Task 7 with a second sentence:

```markdown
The runtime reports `RateLimitInfo` (`status`, `utilization`, `resets_at`) and the supervisor acts on it: `rejected` is the terminal state `RATE_LIMITED`, never `EXHAUSTED`, because a provider limit and a task that could not pass its gates are different outcomes (§3.3).
```

- [ ] **Step 11: Commit**

```bash
git add images/agent_runner.py saffron/phases/implement.py saffron/cell/session.py saffron/cli.py DESIGN.md tests/
git commit -m "feat: act on the rate limit rather than discarding it

The runtime reports RateLimitInfo and agent_runner dropped it as a
passthrough. It is the only ceiling the cell is subject to rather than
reporting — and discarded, a rejected window reached the host as four
failed repair attempts and reported EXHAUSTED. RATE_LIMITED is its own
state because §3.3 is about not having one state for two causes."
```

---

### Task 5: The spec surface and the ledger

**Files:**
- Modify: `saffron/intake.py:47`
- Modify: `saffron/cli.py:53`, `saffron/cli.py:117`
- Modify: `saffron/ledger.py:42`, `:129-135`, `:189`
- Modify: `saffron/replay.py:63`
- Test: `tests/test_intake.py`, `tests/test_ledger.py`

**Interfaces:**
- Consumes: `CellSpec.budget_turns` from Task 3.
- Produces: `Spec.budget_turns: int`; `Ledger.create_task(..., budget_turns: int | None = None) -> int`; CLI flag `--budget-turns`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_intake.py`:

```python
def test_a_spec_declares_its_budget_in_turns():
    spec = intake.parse_spec(
        "---\n"
        "id: TE-0142\n"
        "title: t\n"
        "type: feature\n"
        "budget_turns: 80\n"
        "---\n"
        "body\n"
    )
    assert spec.budget_turns == 80
```

Add to `tests/test_ledger.py`:

```python
def test_a_task_records_its_turn_budget(tmp_path):
    ledger = Ledger(tmp_path / "l.db")
    try:
        repo_id = ledger.upsert_repo("r", "/r", "/m", "sha")
        run_id = ledger.create_run(repo_id, "base")
        ledger.create_task(
            run_id, "TE-0142", "sha", branch="b", budget_turns=80
        )
        (line,) = ledger.queue_lines()
        assert line["budget_turns"] == 80
    finally:
        ledger.close()
```

- [ ] **Step 2: Run them to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_intake.py tests/test_ledger.py -k budget -v`
Expected: FAIL — `budget_turns` is not a field / not a column.

- [ ] **Step 3: Change the spec model**

In `saffron/intake.py:47`, replace `budget_usd: float = 10.0` with:

```python
    # ponytail: provisional until measured; see the Task 1 evidence note.
    budget_turns: int = 150
```

Note `model_config = ConfigDict(extra="forbid")` — an existing spec file carrying `budget_usd` will now be **rejected**, not ignored. That is intended: a silently-ignored budget is worse than a loud one. It also means every spec already on disk breaks until Step 4a converts it.

- [ ] **Step 4a: Convert the specs already on disk**

All four checked-in specs carry `budget_usd` and will fail to parse after Step 3:

| Spec | `budget_usd` | `budget_turns` |
|---|---|---|
| `.saffron/specs/SA-0001-factory-ontology.md` | 10 | 150 |
| `.saffron/specs/SA-0002-size-gate.md` | 8 | 120 |
| `.saffron/specs/SA-0003-attempts-table.md` | 6 | 90 |
| `.saffron/specs/SA-0004-integrity-gate.md` | 4.5 | 70 |

The turn figures preserve each spec's ratio to the 150-turn default, the same way the dollar figures sat against $12. Replace the `budget_usd:` line in each file's frontmatter with the `budget_turns:` value above.

**Re-derive these from the Task 1 evidence note before accepting them.** They are a proportional translation of numbers that were themselves guesses; Task 1 measured what one real task costs in turns, and that measurement outranks this table.

Verify all four still parse:

```bash
for f in .saffron/specs/*.md; do
  .venv/bin/python -c "
import sys, pathlib
from saffron import intake
spec = intake.parse_spec(pathlib.Path(sys.argv[1]).read_text())
print(f'{spec.id}: {spec.budget_turns} turns')
" "$f"
done
```

Expected: four lines, no traceback.

- [ ] **Step 4: Change the ledger schema and the insert**

In `saffron/ledger.py:42`, replace `budget_usd REAL,` with `budget_turns INTEGER,`.

In `create_task` (`:129-135`), change the parameter `budget_usd: float | None = None` to `budget_turns: int | None = None`, and update the statement:

```python
        cursor = self._db.execute(
            """INSERT INTO tasks (run_id, spec_id, spec_sha, state, risk, branch, budget_turns)
               VALUES (?, ?, ?, 'QUEUED', ?, ?, ?)""",
            (run_id, spec_id, spec_sha, risk, branch, budget_turns),
        )
```

In `queue_lines` (`:189`), change `t.budget_usd` to `t.budget_turns`.

`CREATE TABLE IF NOT EXISTS` will not alter an existing `ledger.db`. Delete the dev ledger rather than writing a migration — v0.5 is attended and the ledger is not yet durable state anyone depends on.

- [ ] **Step 5: Change the CLI flag**

In `saffron/cli.py:53`, replace the `--budget` argument with:

```python
    cell_parser.add_argument("--budget-turns", type=int, default=150)
```

In `saffron/cli.py:117`, replace `budget_usd=args.budget,` with `budget_turns=args.budget_turns,`.

In `saffron/replay.py:63`, replace `budget_usd=spec.budget_usd,` with `budget_turns=spec.budget_turns,`.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_intake.py tests/test_ledger.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add saffron/intake.py saffron/cli.py saffron/ledger.py saffron/replay.py tests/
git commit -m "feat(intake,ledger): a budget is declared and recorded in turns

extra='forbid' means an old spec carrying budget_usd is now rejected
rather than ignored. A silently-dropped budget is the worse failure."
```

---

### Task 6: The critic phases

**Files:**
- Modify: `saffron/phases/review.py:132`, `:141`, `:176`, `:197`
- Modify: `saffron/phases/rebut.py:264`, `:274`, `:357`, `:379-381`, `:438`
- Modify: `saffron/cell/session.py:613` (the `critic_budget` call site)
- Test: `tests/test_review.py`, `tests/test_rebut.py`

**Interfaces:**
- Consumes: `critic_turns` from Task 3.
- Produces: `run_review(..., budget_turns: int, ...)` and `run_rebut(..., budget_turns: int, ...)`. `LensReview.cost_usd`, `RebuttalTurn.cost_usd` and `LensVerdicts.cost_usd` are **unchanged** — they keep recording.

- [ ] **Step 1: Write the failing test that guards the critic's tools**

The collapse below rewrites the `agent_options` call, and the argument most easily lost in that edit is `tools=REVIEW_TOOLS`. Its default is `IMPLEMENT_TOOLS`, which carries `Write`, `Edit` and `Bash` — so dropping it hands the critic write access to the tree it is reviewing, silently, in a green test run. Pin it first.

Add to `tests/test_review.py`:

```python
def test_a_lens_never_receives_a_writing_tool():
    """REVIEW_TOOLS is read-only and agent_options defaults to IMPLEMENT_TOOLS,
    so an omitted `tools=` is a §2 boundary violation that passes its tests."""
    captured = {}

    def fake_agent(container, *, prompt, options, watch, **kwargs):
        captured.update(options)
        raise AssertionError("stop here — options is all this test needs")

    try:
        review.run_lens(
            "c", lens="correctness", system_prompt="s",
            budget_turns=25, agent=fake_agent,
        )
    except AssertionError:
        pass

    assert captured["tools"] == ["Read", "Glob", "Grep"]
    for forbidden in ("Write", "Edit", "Bash"):
        assert forbidden not in captured["allowed_tools"]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_review.py -k never_receives_a_writing_tool -v`
Expected: FAIL with `TypeError: run_lens() got an unexpected keyword argument 'budget_turns'`

- [ ] **Step 3: Collapse the critic's two bounds into one**

`run_lens` (`:129-145`) and `run_review` (`:176`) each take **both** `max_turns: int` and `budget_usd: float`. The critic's turn cap now *is* its budget, so the two become one parameter — two knobs for one bound is how they drift apart.

In `saffron/phases/review.py`, delete **both** `max_turns: int` and `budget_usd: float` from the `run_lens` and `run_review` signatures and add `budget_turns: int` in their place. Then rewrite the `agent_options` call at `:139-144`:

```python
    options = implement.agent_options(
        system_prompt=system_prompt,
        max_turns=budget_turns,
        # Read-only, and stated at every call: the default is IMPLEMENT_TOOLS.
        tools=REVIEW_TOOLS,
    )
```

Keep `tools=REVIEW_TOOLS`. Apply the same collapse at `:197`, preserving whatever `tools=` argument is already there.

- [ ] **Step 4: Run it to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_review.py -k never_receives_a_writing_tool -v`
Expected: PASS

- [ ] **Step 5: Thread turns through rebut**

In `saffron/phases/rebut.py`, rename `budget_usd: float` to `budget_turns: int` at `:264` and `:357`, and `:274`/`:438` accordingly. At `:379-381`, replace:

```python
        options=options | {"max_budget_usd": budget_usd},
```

with:

```python
        # The rebuttal resumes the IMPLEMENT session, whose `max_turns` is the
        # whole task's; this narrows it to what the critic phase has left.
        options=options | {"max_turns": budget_turns},
```

- [ ] **Step 6: Update the session call site**

In `saffron/cell/session.py:605-618`, the `run_review` call passes **two** arguments that are now one. Delete the `max_turns=spec.max_turns,` line and replace `budget_usd=critic_budget(spec.budget_usd, spent),` with:

```python
                budget_turns=critic_turns(spec.budget_turns, spent),
```

Leaving `max_turns=spec.max_turns` in place is a `TypeError` after Step 3, not a silent bug — but delete it deliberately rather than letting the traceback find it. Apply the same two-line edit at the `run_rebut` call site in the same function.

- [ ] **Step 7: Run the suite**

Run: `.venv/bin/python -m pytest tests/test_review.py tests/test_rebut.py -v`
Expected: PASS. Update any test asserting `max_budget_usd` in an options dict to assert `max_turns`, and any test calling `run_lens`/`run_review`/`run_rebut` with `max_turns=` or `budget_usd=` to pass `budget_turns=`.

- [ ] **Step 8: Commit**

```bash
git add saffron/phases/review.py saffron/phases/rebut.py saffron/cell/session.py tests/
git commit -m "feat(phases): the critic's turn cap is its budget

One bound, not two. max_turns and a separate budget for the same session
is how the two drift apart."
```

---

### Task 7: Delete the inert in-cell dollar ceiling

Task 1 measured whether `max_budget_usd` can fire under subscription auth. If it reports zero cost, it cannot — and a ceiling that cannot fire is worse than no ceiling, because it reads as protection.

**Files:**
- Modify: `saffron/phases/implement.py:80-107`
- Modify: `DESIGN.md:47`, `DESIGN.md:357`
- Test: `tests/test_implement.py`

**Interfaces:**
- Consumes: the Task 1 evidence note.
- Produces: `agent_options(*, system_prompt, cwd=WORKTREE_MOUNT, max_turns, tools=IMPLEMENT_TOOLS) -> dict`. The `budget_usd` parameter is gone.

- [ ] **Step 1: Confirm from the evidence note that it never fired**

Re-read `docs/evidence/2026-08-21-subscription-turn-accounting.md`, conclusion 3. If `total_cost_usd` was a real non-zero figure, **stop and re-plan this task** — the knob still works and deleting it is wrong.

- [ ] **Step 2: Write the failing test**

Add to `tests/test_implement.py`:

```python
def test_agent_options_carry_no_dollar_ceiling():
    """A ceiling that cannot fire is worse than none: it reads as protection.
    Under subscription auth the runtime reports no cost to measure (§4.3)."""
    options = implement.agent_options(system_prompt="s", max_turns=60)
    assert "max_budget_usd" not in options
    assert options["max_turns"] == 60
```

- [ ] **Step 3: Run it to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_implement.py -k no_dollar_ceiling -v`
Expected: FAIL — `TypeError: agent_options() missing 1 required keyword-only argument: 'budget_usd'`

- [ ] **Step 4: Remove the parameter**

In `saffron/phases/implement.py`, drop `budget_usd: float,` from the signature at `:80-87`, and delete the `max_budget_usd` entry with its three-line comment at `:105-107`. Replace the `max_turns` comment with:

```python
        # In-cell and per *session*. The per-task ceiling is the host's sum in
        # session.py, in the same unit — which is the whole point: a ceiling the
        # cell evaluates is on the untrusted side of §2 and only saves turns.
        "max_turns": max_turns,
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_implement.py -v`
Expected: PASS

- [ ] **Step 6: Rewrite the N2 row**

In `DESIGN.md:47`, replace the N2 row with:

```markdown
| N2 | Bounded spend | Per-attempt, per-task, and per-batch **turn** ceilings; hard stop, enforced host-side against reported turns (§4.1). The provider's rate limit is the ceiling underneath, and it is the only one that holds without the cell's cooperation (§5.1) |
```

- [ ] **Step 7: Rewrite the in-cell-vs-host argument**

In `DESIGN.md:357`, replace the paragraph beginning `**Note the order of the spend row` with:

```markdown
**Note the order of the spend row, because it inverts the obvious one.** The agent runtime offers a per-session ceiling, and it is tempting to treat that as *the* budget enforcement. It is not: it is evaluated by the runtime process, which runs **inside the cell**. That places it on the untrusted side of §2's boundary — the same category as the `PreToolUse` path check (§5.3), valuable for cutting off a runaway attempt a few seconds earlier, worthless as a guarantee. The ceiling that holds is the supervisor's, because the supervisor is on the host and stops the cell rather than asking it to stop itself. **Rev 11 changed the unit and, in doing so, the shape of the argument.** Both ceilings now count turns, so the host is no longer summing a quantity the cell reports in a currency nobody is billed in: under a subscription the runtime reports no meaningful cost, and a dollar ceiling that cannot fire is worse than none because it reads as protection. It was deleted rather than ported. The in-cell turn bound is still worth setting, for the same reason the path check is: it saves turns. It is just not what N2 rests on — and underneath both sits the provider's rate limit, which is the one ceiling the cell cannot spend past whatever it reports.
```

- [ ] **Step 8: Commit**

```bash
git add saffron/phases/implement.py DESIGN.md tests/test_implement.py
git commit -m "refactor(implement): delete the in-cell dollar ceiling

Measured inert under subscription auth (see the evidence note). A ceiling
that cannot fire is worse than no ceiling — it reads as protection."
```

---

### Task 8: The report surface

**Files:**
- Modify: `saffron/report/index.py:41`, `:94`, and the header row
- Modify: `saffron/replay.py:122`, `:201`
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `QueueLine` gains `turns_used: int | None`. `cost_usd_est` **stays** on `QueueLine` and in the rendered table.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_report.py`:

```python
def test_the_index_shows_turns_and_still_shows_cost():
    """Cost keeps recording after it stops deciding — a run whose cost reads
    zero is itself a fact worth seeing in the table."""
    line = index.QueueLine(
        repo="r", spec_id="TE-0142", state="READY_FOR_REVIEW",
        attempts=1, cost_usd_est=0.0, turns_used=112, concerns=0,
        added=10, removed=2, link="TE-0142/pr_body.md",
    )
    html_out = index.render_index([line], header={})
    assert "112 turns" in html_out
    assert "$0.00" in html_out
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_report.py -k shows_turns -v`
Expected: FAIL — `QueueLine` has no `turns_used`.

- [ ] **Step 3: Add the field and the cell**

In `saffron/report/index.py:41`, add below `cost_usd_est: float | None`:

```python
    turns_used: int | None = None
```

In `_row` (`:94`), after the `cost` line add:

```python
    turns = f"{line.turns_used} turns" if line.turns_used is not None else "—"
```

and insert `turns` into the `cells` list immediately after the `f"{line.attempts} att"` entry. Add a matching `<th>Turns</th>` to the header row of the table template.

- [ ] **Step 4: Update replay**

In `saffron/replay.py:122`, add `turns_used=None,` beside `cost_usd_est=None,`. At `:201`, add `"turns": "—",` to the header dict beside `"spend": "—",`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_report.py -v`
Expected: PASS

- [ ] **Step 6: Run the whole suite**

Run: `.venv/bin/python -m pytest -q`
Expected: 1 failed (the pre-existing `test_saffron_gates.py` failure named in Global Constraints), everything else passing.

- [ ] **Step 7: Commit**

```bash
git add saffron/report/index.py saffron/replay.py tests/test_report.py
git commit -m "feat(report): the index shows turns beside cost

Cost keeps recording after it stops deciding. A run whose cost reads zero
is itself a fact worth seeing."
```
