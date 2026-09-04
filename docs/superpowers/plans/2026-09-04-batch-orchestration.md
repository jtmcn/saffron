# Batch orchestration Implementation Plan

> **For agentic workers:** this plan is **not** implemented by a subagent or
> by hand. Each task's deliverable is a Saffron spec file; the implementation
> is done by an agent in a cell driven by `saffron cell`. The steps here are
> the operator's. Do **not** invoke `superpowers:subagent-driven-development`
> or `superpowers:executing-plans` on it — that would hand-write the code
> these specs exist to have the factory write, in a repo whose point is that
> it writes its own.
>
> Subagents *are* used, twice per spec, and only to review: L3 reviews the
> spec before a cell spends money against it, and L7 reviews the diff per
> `superpowers:requesting-code-review` after the pull request is marked ready.

**Goal:** `saffron batch --repo . --budget 50 --until 06:30` runs a night
unattended and says how it ended — closing backlog item 58, the one gap that
makes §9's v1 criterion unreachable rather than merely unmet.

**Architecture:** The scan already exists and is not rewritten. `cli._queue`'s
resolve-mirror-export-scan is extracted so one answer to "what would run
tonight" serves both commands; `cli._run_cell`'s per-task preparation is
hoisted to run once per batch, plus `load_policy` validation, an auth check and
a disk-headroom check; a new `saffron/batch.py` holds a K=1 `for` loop over the
sorted candidates, calling the unchanged `run_one_cell` and stopping four ways.

**Tech Stack:** Python (uv), pytest, stdlib `sqlite3`, `apple/container` for
cell-marked tests. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-04-batch-orchestration-design.md`

## Global Constraints

- **`DESIGN.md` §4.2.1 is authoritative.** It settles K, the stop conditions,
  the breaker's membership, the schema, the command and the exit codes. Where a
  spec below and §4.2.1 disagree, §4.2.1 wins.
- **`DESIGN.md` and `CONTEXT.md` are `protected`.** No spec here may name them
  in `touches`; every documentation correction is Task 6, by hand.
- **`.saffron/**` is `protected`** — a spec cannot edit the spec directory or
  `policy.yaml`.
- **Exit code `1` is reserved and never emitted by `batch`.** `0` for
  `DRAINED`, `BUDGET`, `UNTIL`; `2` for `INFRASTRUCTURE` and for a preflight
  failure that takes the batch.
- **`RATE_LIMITED` is not `EXHAUSTED`** (`CLAUDE.md`). The breaker counts the
  first and resets on the second.
- **`error` ≠ `fail`** (`CLAUDE.md`). Step 3 of §4.4 rests on it.
- **The `tool` field must be obtained by executing the tool**, never a literal.
- Commit subjects are lowercase `type(scope): what changed`, written as a
  sentence about the defect.

---

## Why five specs

Item 56 is the measurement that sets the shape: `SA-0009` was §4.2.1's
*read-only* half as one spec, landed 990 changed lines against a 600-line
`feature` ceiling, and ended `EXHAUSTED` at $31.60 with zero lines merged. This
plan is §4.2.1's *executing* half, which is larger. Splitting it five ways is
not caution — it is the recut that item 25 had to perform by hand afterwards,
performed first.

Each spec below is **one mechanism, one or two source files**. Where a spec
looks thin, that is deliberate.

## Stacking

The five run as **one linear stack**: `SA-0045` → `SA-0046` → `SA-0047` →
`SA-0048` → `SA-0049`. K=1 means they are serial regardless.

**`SA-0046`'s `depends_on` is a stacking edge, not a logical one.** It touches
only `saffron/scheduler.py` and would run correctly against `main`. It is
chained because `docs/BACKLOG.md` is in four of the five specs' `touches` and
is append-only, so an unstacked spec conflicts there — the precedent plan's
Task 12 records that exact failure. Stated rather than disguised.

---

## Task 1: `SA-0045` — a batch has nowhere to record that it happened

**Interfaces:** produces the `batches` table, `runs.batch_id`, and
`tasks.policy_sha`. Consumed by `SA-0047`, `SA-0048` and by part 3's pages.

- [ ] **L1: Write the spec**

```markdown
---
id: SA-0045
title: a batch has no row, and a task cannot say which policy it ran under
type: feature
priority: 1
depends_on: []
touches:
  - saffron/ledger.py
  - saffron/cell/session.py
  - saffron/phases/package.py
  - tests/test_ledger.py
  - tests/test_session.py
  - tests/test_package.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cli.py
  - saffron/scheduler.py
  - saffron/report/**
  - saffron/gates/**
  - saffron/events.py
budget_usd: 10
max_attempts: 3
max_turns: 80
risk: elevated
---

## Context
§4.2.1 names the schema a batch needs and says why it is not the same call as
`tasks.priority`: *"The batch's window and its stop reason have to survive for
§6's morning queue to render the night."* Neither exists. `ledger.py` declares
`repos`, `runs`, `tasks`, `attempts`, `gate_results`, `failures` and
`findings`, and no `batches`.

Backlog item 16 is the second half. `repos.policy_sha` is per repo and written
once at cell start; when the default branch has moved, PACKAGE re-verifies
under `fetch_head`'s policy — a different declaration, correctly so — and
nothing records that. §4.1's invalidation rule (*change a repo's gate
declarations mid-batch and its in-flight tasks are invalidated*) is the same
question from the other end, and it has no reader until batches exist.

## Problem
- **A night cannot be rendered.** §6's batch header needs the window and the
  stop reason, and there is no row carrying either.
- **`runs` cannot be grouped.** Every run is standalone, so nothing can ask
  which runs belonged to one night.
- **A task cannot say what it ran under.** The sha is already in hand at
  PACKAGE's call site and discarded as `policy, _`.

## Acceptance criteria
- [ ] A `batches` table exists with `batch_id`, `started_at`, `ended_at`,
      `budget_usd`, `spent_usd_est`, `until_ts` and `status`
- [ ] `status` accepts exactly `DRAINED`, `BUDGET`, `UNTIL` and
      `INFRASTRUCTURE`, and a test asserts a fifth value is rejected
- [ ] `runs` carries a nullable `batch_id`, and a run created outside a batch
      leaves it NULL rather than inventing one
- [ ] `tasks` carries a nullable `policy_sha`
- [ ] `session.py` writes `tasks.policy_sha` at cell start from the same
      export `load_policy(gates_dir)` already reads
- [ ] `package.py` rewrites `tasks.policy_sha` when re-verification runs under
      a different policy, and leaves it alone when it does not — a test drives
      both branches
- [ ] `concurrency` is **not** a column, and `tasks.priority` is **not** added
      (§4.2.1: a column written at scan and read by nobody)
- [ ] A ledger created before this change opens and reads without error, and a
      test asserts it
- [ ] Every new test runs with no network and no cell

## Out of scope
**Writing a `batches` row from a running batch.** Nothing runs one yet;
`SA-0048` does. This lands the schema and the two writes that have call sites
today.

**Rendering any of it.** `saffron/report/**` is `forbidden`.

**Backfilling existing rows.** A value invented for a night nobody observed is
the failure §4.1 warns about.

## Notes for the agent
`repos.policy_sha` **stays**. It answers a different question — what the repo
declared when it was last seen — and removing it would break `upsert_repo`'s
callers for no gain. The new column is per task and additive.

The migration pattern to follow is `ledger.py`'s existing
`CREATE TABLE IF NOT EXISTS` plus the `gate_results_new` rebuild at `:192`;
read that before writing a third style.

`risk: elevated` because `saffron/ledger.py` is in `elevate_on`.
```

- [ ] **L2: Read it back** against §4.2.1's schema paragraph. Every column it
      names is present; nothing it excludes has crept in.
- [ ] **L3: Spec review** — dispatch a subagent to review the spec *as a spec*:
      are the criteria checkable, is `touches` sufficient to satisfy them, does
      any criterion name a path outside it (which gate 0 refuses).
- [ ] **L4: Drive it.**

```bash
env CLAUDE_CODE_OAUTH_TOKEN=(bash -c 'source ~/.secrets; printf %s $CLAUDE_CODE_OAUTH_TOKEN') \
  uv run saffron cell .saffron/specs/SA-0045-a-batch-has-no-row.md --repo .
```

- [ ] **L5: Read the pull request body**, not the diff, first. It is the
      artifact the factory exists to produce; if it does not tell you what
      changed, that is a finding about the factory.
- [ ] **L6: `make check` on the branch.**
- [ ] **L7: Diff review** per `superpowers:requesting-code-review`.
- [ ] **L8: Mark ready.** `gh pr ready <n>`. Retiring the spec to
      `.saffron/specs/done/` is deferred to Task 7.

---

## Task 2: `SA-0046` — the scan trusts an in-flight state that cannot be true

**Interfaces:** consumes nothing. Produces a scan that stamps corpses before
filtering. Consumed by `SA-0048`.

- [ ] **L1: Write the spec**

```markdown
---
id: SA-0046
title: a task left IMPLEMENTING by a host crash is neither done nor requeued, so the scan drops it forever
type: bug
priority: 1
depends_on:
  - SA-0045
envelope:
  - saffron/scheduler.py
  - tests/**
touches:
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cli.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/report/**
  - saffron/gates/**
budget_usd: 8
max_attempts: 3
max_turns: 70
risk: elevated
---

## Context
§4.2.1 states the rule in a block quote: *"The in-flight states are not on
either list, and the scan must not treat that as 'queue it'. `DRAFT`,
`QUEUED`, `DIAGNOSING`, `IMPLEMENTING`, `GATING`, `REPAIRING`, `REVIEWING` and
`REBUTTING` at scan time mean a corpse: one batch runs at a time, so nothing is
legitimately in flight when a scan happens. `ORPHANED` covers only the deaths
the supervisor stamped (§4.5) — a host power cut leaves the task in
`IMPLEMENTING`. **The scan stamps any in-flight task `ORPHANED` before
filtering**, which is §4.3's reconcile step doing the job it is already named
for, and the task then re-queues by the ordinary rule."*

`scheduler.py` names `ORPHANED` only inside `REQUEUE_STATES`. Nothing stamps
it at scan time.

## Problem
- **An in-flight state at scan time is silently neither.** It is not in
  `DONE_STATES`, so the spec is not filtered out; it is not in
  `REQUEUE_STATES`, so no task resumes. What the scan does with it today is
  undefined by §4.2.1's own reading and is decided by fallthrough.
- **The failure mode is invisible and permanent.** A host power cut mid-cell
  leaves `IMPLEMENTING`. Unattended, nobody sees it. On every subsequent night
  the same row is read the same way.
- **This becomes load-bearing exactly when batches land.** Attended, the
  operator sees the cell die and can act.

## Acceptance criteria
- [ ] The scan stamps every task in an in-flight state `ORPHANED` before the
      `DONE_STATES` / `REQUEUE_STATES` filter runs
- [ ] The eight in-flight states are enumerated from one place, not written
      twice, and a test asserts the enumeration matches §4.2.1's list exactly
- [ ] A stamped task then re-queues by the ordinary rule, resuming its own
      `task_id` rather than minting a new one — §4.2.1's *"resolves to a task,
      not to a spec"*
- [ ] A task already `ORPHANED` is not re-stamped and its `updated_at` does not
      move
- [ ] The stamp is written only when a caller asserts a scan is happening —
      `saffron queue` must **not** stamp, for the reason `cli.py:557` already
      records about `reconcile`, and a test asserts `queue` leaves the row
      untouched
- [ ] Terminal states and requeue states are untouched
- [ ] Every new test runs with no network and no cell

## Out of scope
**Preventing the crash.** This reclaims a corpse; it does not stop one.

**`saffron gc` (§4.5).** Volume reclamation is deferred at K=1. This is the
ledger half only.

**Changing `DONE_STATES` or `REQUEUE_STATES`.** Both are correct as they
stand; the gap is the third category.

## Notes for the agent
Read `cli.py:557` first — *"Never `ORPHANED`, for the same reason `queue` never
asserts it"* — and preserve that property. A scan that stamps is a *batch*
scan; a scan that prints is not. The distinction is the whole of the fifth
criterion.

This is a bug spec with an `envelope` and no `touches` because whether the
stamp belongs in `build_queue`, beside it, or in a `Ledger` method is what
DIAGNOSE answers.
```

- [ ] **L2–L8:** as Task 1, substituting this spec's path.

---

## Task 3: `SA-0047` — preflight is per task, and a night needs it per night

**Interfaces:** consumes `SA-0045`'s `runs.batch_id`. Produces
`batch_preflight(...)` returning a per-repo readiness result. Consumed by
`SA-0048`.

- [ ] **L1: Write the spec**

```markdown
---
id: SA-0047
title: every task pays for a preflight a night should pay once, and two checks a night needs do not exist
type: feature
priority: 1
depends_on:
  - SA-0046
touches:
  - saffron/preflight.py
  - saffron/cli.py
  - tests/test_preflight.py
  - tests/test_cli.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cell/**
  - saffron/phases/**
  - saffron/report/**
  - saffron/gates/**
  - saffron/scheduler.py
budget_usd: 12
max_attempts: 3
max_turns: 90
risk: elevated
---

## Context
§4.2.1: *"Preflight is what a task already does, hoisted, plus two. `_run_cell`
today does the mirror fetch, the origin refusal and the default-branch pin per
task; a batch does them once per run. Added: `load_policy` validation, and an
auth check."*

The auth check is the one with a corpse behind it. Appendix J measured that a
cell whose agent cannot authenticate returns `subtype: "success"`,
`is_error: true`, `total_cost_usd: 0.0`. **Unattended, an expired token at
22:00 produces a night of clean-looking nothing against a budget that never
counts down.**

§4.2.1 also refuses to defer the disk-headroom check alongside `saffron gc`:
*"with gc deferred the accumulation is still unbounded, so dropping the
detection as well turns a warned failure into a silent one."*

## Problem
- **Per-task preparation is paid per task.** `_run_cell` fetches the mirror,
  refuses a non-forge origin and pins the default branch on every invocation.
- **Nothing validates `policy.yaml` before the night starts.** A malformed
  policy is discovered by the first cell, after an image build.
- **Nothing checks auth.** The measured failure is silent and costs a night.
- **Nothing checks disk.** The leak is bounded at K=1 and still unbounded over
  weeks.

## Acceptance criteria
- [ ] A single entry point performs, in order: auth check, mirror fetch, origin
      refusal, default-branch pin, `load_policy` validation, disk headroom
- [ ] It returns a result naming which check failed, never a bare boolean
- [ ] The auth check fails when `CLAUDE_CODE_OAUTH_TOKEN` is absent or empty,
      and a test drives the empty-string case specifically — `_run_cell`'s own
      check uses `.strip()` for that reason
- [ ] A failing check returns rather than raising, so a caller can record it
      and skip the repo (§4.4 step 1: *a repo that fails preflight is skipped,
      not fatal*)
- [ ] `saffron cell` continues to work unchanged, and its existing tests pass
      untouched — this extracts, it does not alter behaviour
- [ ] The disk-headroom threshold is a named constant with a comment saying
      what it was chosen against
- [ ] No check silently passes when it cannot run: a check that cannot execute
      returns failure, the rule `host_probe_ports` already follows
- [ ] Every new test runs with no network and no cell, except any that must
      drive a real session, which carries the `cell` marker

## Out of scope
**Calling it from a batch.** `SA-0048`.

**`saffron gc` (§4.5).** Deferred at K=1, deliberately; the disk *check* is
not.

**The host-binding probes.** `assert_host_is_unreachable` and
`assert_proxy_reaches_upstream` are per-cell and stay per-cell — they assert
properties of a container that does not exist until a task starts.

## Notes for the agent
`preflight.py` today is host-binding probes only. Whether the new entry point
belongs there or in a new module is a judgement call; `preflight.py` is the
name that already means this, and §4.2.1 calls the step "preflight".

**Do not move the origin refusal's timing.** `_run_cell` reads `github_slug`
*for its refusal, not its value*, and the comment says why: PACKAGE needs the
slug and only reaches it after the budget is spent.
```

- [ ] **L2–L8:** as Task 1.

---

## Task 4: `SA-0048` — nothing runs the queue it prints

**Interfaces:** consumes `SA-0045`'s schema, `SA-0046`'s stamping and
`SA-0047`'s preflight. Produces `run_batch(...)` returning a stop reason.
Consumed by `SA-0049`.

- [ ] **L1: Write the spec**

```markdown
---
id: SA-0048
title: the scan resolves a queue and nothing executes it, so a night cannot happen
type: feature
priority: 1
depends_on:
  - SA-0047
touches:
  - saffron/batch.py
  - tests/test_batch.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cli.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/report/**
  - saffron/gates/**
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/preflight.py
budget_usd: 16
max_attempts: 4
max_turns: 110
risk: elevated
---

## Context
§4.2.1: *"K = 1, and the scheduler is a `for` loop over a sorted list."* The
scan resolves candidates today and `saffron queue` prints them. Nothing runs
them, so §9's v1 criterion is unreachable.

## Problem
- **The queue is printed and abandoned.** Every mechanism up to the sort
  exists; the consumer does not.
- **A batch has four ways to end and no way to say which.** §4.2.1: *"The queue
  drains, the budget is gone, `--until` hits, or the breaker fires."*
- **Two consecutive aborts should stop a night** and today would burn a
  preflight and a baseline suite per remaining task to learn the same thing.

## Acceptance criteria
- [ ] `run_batch` iterates the sorted candidates, calling `run_one_cell` once
      per task, and returns a stop reason
- [ ] It stops on all four conditions and the returned reason distinguishes
      them: `DRAINED`, `BUDGET`, `UNTIL`, `INFRASTRUCTURE`
- [ ] The budget gate is **one comparison before each task** — uncommitted
      budget against the task's `budget_usd` — with no reserved-budget
      arithmetic (§4.2.1 at K=1)
- [ ] A task admitted under the budget gate and overshooting its own
      `budget_usd` does not fail the batch; the *batch* ceiling is what binds,
      and a test drives an overshooting task
- [ ] The breaker counts exactly `GATE_ERROR`, `PREFLIGHT_FAILED` and
      `RATE_LIMITED`, and fires on **two consecutive**
- [ ] The breaker **resets on any state a task earned, including
      `EXHAUSTED`** — a test asserts an `EXHAUSTED` between two aborts prevents
      the fire. This is the criterion most likely to be got wrong: "resets on
      any terminal state" would never reach two
- [ ] `--until` is compared against an injected clock, never `time.time()`
      read inside the loop, so the condition is testable without waiting
- [ ] A `batches` row is written at start and completed at stop, carrying the
      window, the spend and the status
- [ ] Every `run_one_cell` call is made through an injected callable, so every
      test above runs with no network and no cell
- [ ] No test in this spec carries the `cell` marker — if one needs a real
      cell, the seam is in the wrong place

## Out of scope
**The CLI.** `saffron/cli.py` is `forbidden`; `SA-0049` wires the command.

**Concurrency.** K=1. No pool, no `--concurrency`, no reserved budget.

**Multi-repo.** v2. `run_batch` takes one repo.

**`saffron gc`.** Deferred at K=1 (§4.2.1).

## Notes for the agent
**The scan is not yours to rewrite.** `cli._queue` already resolves the mirror,
exports `.saffron/` at `base_sha` and calls `build_queue`. `cli.py` is
`forbidden` here, so `run_batch` must take the resolved candidates as an
argument rather than re-deriving them — which is also what makes every test
injectable.

**The injected clock and the injected cell callable are the whole test
strategy.** An eight-hour window and a real cell are both untestable; a fake
clock and a callable returning canned `CellOutcome`s are not. If a criterion
above seems to need a real night, the seam is wrong.

`risk: elevated` is not from `elevate_on` — `saffron/batch.py` is a new file
— but declared, because this is the module that spends money unattended.
```

- [ ] **L2: Read it back** and count: nine acceptance criteria against two
      files. This is the widest spec in the plan and the one item 56's
      measurement is about. If L3 reports it is two mechanisms, **split it
      before driving it** — the stop conditions and the breaker are the natural
      seam.
- [ ] **L3–L8:** as Task 1.

---

## Task 5: `SA-0049` — the command

**Interfaces:** consumes `SA-0048`'s `run_batch`. Produces `saffron batch`.

- [ ] **L1: Write the spec**

```markdown
---
id: SA-0049
title: run_batch has no caller, so a night still cannot be started
type: feature
priority: 1
depends_on:
  - SA-0048
touches:
  - saffron/cli.py
  - tests/test_cli.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/batch.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/report/**
  - saffron/gates/**
  - saffron/scheduler.py
budget_usd: 10
max_attempts: 3
max_turns: 80
risk: standard
---

## Context
§4.2.1 gives the command and its exit codes exactly:

```
saffron batch --repo . --budget 50 --until 06:30
```

*"No `--repos`, because multi-repo is v2. No `--concurrency`, because a flag
for a knob with one position is the same defect in a CLI that item 18 found in
a spec. `--repo` defaults to the working directory, matching `saffron cell`.
`--until` takes `HH:MM` and resolves to the next occurrence. `--budget`
defaults to 50."*

And: *"`0` for `DRAINED`, `BUDGET` and `UNTIL`, `2` for `INFRASTRUCTURE` and
for a preflight failure that takes the whole batch. Never `1`. A batch that
drains with three failed tasks did its job."*

## Problem
- **`run_batch` has no caller.** The night exists as a function nobody invokes.
- **The scan is about to be written twice.** `_queue` resolves it for printing;
  a batch needs the same value.

## Acceptance criteria
- [ ] `saffron batch --repo . --budget 50 --until 06:30` runs a batch
- [ ] `--repo` defaults to the working directory; `--budget` defaults to 50
- [ ] `--until HH:MM` resolves to the **next** occurrence, and a test drives a
      time earlier in the day than now, which must resolve to tomorrow
- [ ] There is **no** `--concurrency` and **no** `--repos` flag
- [ ] Exit `0` for `DRAINED`, `BUDGET` and `UNTIL`; exit `2` for
      `INFRASTRUCTURE` and for a preflight failure that takes the batch
- [ ] **Exit `1` is never returned by `batch`**, and a test asserts it across
      every stop reason
- [ ] The scan is extracted so `queue` and `batch` call one function; `queue`'s
      existing output is unchanged, asserted against its current test
- [ ] Every new test runs with no network and no cell

## Out of scope
**Changing `run_batch`.** `saffron/batch.py` is `forbidden`.

**The morning queue's rendering.** `saffron/report/**` is `forbidden`.

**`launchd` scheduling.** §4.4 names it; it is a plist on the host, not code,
and belongs in Task 6's documentation.

## Notes for the agent
The extraction in criterion 7 is the point of ordering this last: by now
`_queue` is the only remaining copy of the scan, and both callers exist, so the
right shape is visible rather than guessed.

**`queue`'s output must not change.** It is what an operator reads before
trusting a night, and a test pins it.
```

- [ ] **L2–L8:** as Task 1.

---

## Task 6: The by-hand follow-ups

Protected documents no cell can correct, plus the host artifact that is not
code.

- [ ] **Step 1: Correct §4.2.1's built/unbuilt claims.** It describes the
      scheduler in the present tense throughout. Once this plan lands, the
      sentences that read as design become descriptions — check each and
      correct the ones that no longer match, without renumbering.
- [ ] **Step 2: State that `budget_usd` is best-effort** where a spec's
      ceilings are declared, per backlog item 44's decision. §4.2.1's budget
      gate paragraph is the natural home; `CONTEXT.md`'s entry for the term is
      the other half.
- [ ] **Step 3: Write the `launchd` plist and document it.** §4.4 names
      `launchd` specifically — *"not cron — `launchd` handles wake and won't
      silently skip a sleeping Mac."* Belongs in `docs/HOST-HARDENING.md`
      beside the other host prerequisites.
- [ ] **Step 4: Close backlog items 16, 44 and 58**, each with the commit that
      closed it — the shape items 1 and 29 use.
- [ ] **Step 5: Commit.**

```bash
git add DESIGN.md CONTEXT.md ontology/ docs/BACKLOG.md docs/HOST-HARDENING.md
git commit -m "docs(design): a batch runs, and three documents described a factory that could not"
```

---

## Task 7: Link, check and merge the stack

- [ ] **Step 1: Link the pull requests, bottom to top — by hand.**

```bash
gh stack link <SA-0045-pr> <SA-0046-pr> <SA-0047-pr> <SA-0048-pr> <SA-0049-pr>
```

`link`, not `submit`: PACKAGE has already opened every pull request, and
`submit` force-pushes from a local stack that does not exist here.

- [ ] **Step 2: Check the merge, not the pull request page.** A stacked page
      renders a clean diff because GitHub computes it from the merge base.

```bash
git merge-tree --write-tree origin/saffron/SA-0045 origin/saffron/SA-0046
```

Run it for each adjacent pair. `docs/BACKLOG.md` is in four of the five
specs' `touches` and is append-only, so it is where a conflict will be. **Any
conflict means a spec ran unstacked** — find which cell printed no
`stacked on …` line rather than resolving it.

- [ ] **Step 3: Merge the stack.** One command, all-or-nothing, bottom-up:

```bash
gh stack merge <top-pr> --yes --squash
```

- [ ] **Step 4: Update the local checkout.**

```bash
git checkout main && git pull --ff-only
git branch --merged main | grep '^  saffron/SA-' | xargs -r git branch -d
```

- [ ] **Step 5: Retire the stack's specs** — the L8 deferred from each task.

```bash
git mv .saffron/specs/SA-004[5-9]-*.md .saffron/specs/done/
```

- [ ] **Step 6: Re-anchor the two live-witness tests.**
      `tests/test_scheduler.py`'s `_real_corpus` promotes named ids out of
      `specs/done/`, and the smoke check asserts the active directory is
      empty. Retiring five specs changes both. This is expected and is the
      practice those tests were written for.

- [ ] **Step 7: Run the night.** The plan is not done when the stack merges.

```bash
env CLAUDE_CODE_OAUTH_TOKEN=(...) uv run saffron batch --repo . --budget 20 --until 23:59
```

§9's criterion is *a full night runs while you sleep*, and every property in
`SA-0048` was tested against a fake clock and a fake cell. **The first real
batch is the measurement**, and whatever it returns is `docs/evidence/`
material in the shape of `docs/evidence/2026-08-25-morning-queue-from-real-rows.md`.

---

## Self-review

**Spec coverage.** Every row of the design doc's built/unbuilt table maps to a
task: the schema and `tasks.policy_sha` to `SA-0045`; the `ORPHANED` stamp to
`SA-0046`; `load_policy` validation, the auth check and disk headroom to
`SA-0047`; the loop, the four stop conditions and the breaker to `SA-0048`; the
command and exit codes to `SA-0049`. Item 16 lands in Task 1, item 44's
enforceable half in Task 4.

**Placeholders.** None. Every acceptance criterion is checkable and names what
it is checked against.

**Naming consistency.** `run_batch` is produced by `SA-0048` and consumed by
`SA-0049` under that name in both. `batch_preflight` is named once, in
`SA-0047`'s interface line, and `SA-0048` consumes it only through
`SA-0047`'s result rather than by name — deliberate, because whether it is one
function or a small module is DIAGNOSE's answer, not this plan's.

**The known risk.** `SA-0048` is the widest spec here — nine criteria against
two files — and item 56 is the standing measurement of what happens when a
spec is too wide for its own repair loop. Task 4's L2 carries an explicit
instruction to split it at the stop-conditions/breaker seam if L3 reports two
mechanisms. That check is the plan's own application of the lesson that
produced item 56.
