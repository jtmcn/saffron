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
  in `touches`; every documentation correction is Task 7, by hand.
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

## Why seven specs

Item 56 is the measurement that sets the shape: `SA-0009` was §4.2.1's
*read-only* half as one spec, landed 990 changed lines against a 600-line
`feature` ceiling, and ended `EXHAUSTED` at $31.60 with zero lines merged. This
plan is §4.2.1's *executing* half, which is larger. Splitting it seven ways is
not caution — it is the recut that item 25 had to perform by hand afterwards,
performed first.

Each spec below is **one mechanism, one or two source files**. Where a spec
looks thin, that is deliberate.

## Stacking

The six run as **one linear stack**: `SA-0045` → `SA-0046` → `SA-0047` →
`SA-0048` → `SA-0050` → `SA-0051`. K=1 means they are serial regardless.

**`SA-0047`'s `depends_on` is a stacking edge, not a logical one.** It touches
only `saffron/scheduler.py` and would run correctly against `main`. It is
chained so the stack stays linear.

**No spec here declares `docs/BACKLOG.md` in `touches`**, which departs from
the precedent plan and removes the conflict its Task 12 warns about at source.
Nothing in these six needs to append to the backlog — items 16, 44 and 58 are
closed by hand in Task 7 — and a file in `touches` that no criterion asks for
is one an agent will either skip or pad.

---

## Task 1: `SA-0045` — a batch has nowhere to record that it happened

**Written: `.saffron/specs/SA-0045-a-batch-has-no-row.md`.** Not embedded here.
A plan carrying a copy of a spec that exists on disk is a drift vector, and this
one already drifted once — the copy below was replaced after L3.

**Interfaces:** produces the `batches` table and `runs.batch_id`. Consumed by
`SA-0050`'s loop and by part 3's pages.

- [x] **L1: Write the spec.**
- [x] **L2: Read it back** against §4.2.1's schema paragraph.
- [x] **L3: Spec review** — dispatched 2026-09-04, verdict **REVISE**. Four
      findings acted on, each verified against the code before acting:
      - **The migration note was wrong and would have broken the operator's
        ledger.** It said `ledger.py` has two migration shapes. It has three,
        and the one this spec needs — the guarded `PRAGMA table_info` +
        `ALTER TABLE ADD COLUMN` block — was the one omitted, with a comment
        above it stating the trap: *"an existing ledger predates these columns,
        and `IF NOT EXISTS` does not alter."* The spec steered toward
        `CREATE TABLE IF NOT EXISTS`, a silent no-op on every ledger that
        exists. It would have passed its own tests, merged, and failed the next
        `saffron cell` with `no such column`, taking the rest of the stack with
        it at exit `2`.
      - **The spec was two mechanisms.** Split — see Task 2.
      - **No `acceptance:` witnesses**, so `criteria` would have reported
        `skip` and nothing would have gated the criteria but human review. The
        last four merged specs all declare witnesses; this dropped back to
        prose. Now six witnessed claims.
      - **`create_run` has a caller in `saffron/replay.py`**, which is
        `forbidden` here — so a required parameter would break a caller the
        agent cannot legally repair. The spec now says the parameter defaults.
- [ ] **L4: Drive it.**

```bash
env CLAUDE_CODE_OAUTH_TOKEN=(bash -c 'source ~/.secrets; printf %s $CLAUDE_CODE_OAUTH_TOKEN') \
  uv run saffron cell .saffron/specs/SA-0045-a-batch-has-no-row.md --repo .
```

- [ ] **L5: Read the pull request body**, not the diff, first.
- [ ] **L6: `make check` on the branch.**
- [ ] **L7: Diff review** per `superpowers:requesting-code-review`.
- [ ] **L8: Mark ready.** `gh pr ready <n>`. Retiring the spec is Task 8.

---

## Task 2: `SA-0046` — a task cannot say which policy it ran under

**Written: `.saffron/specs/SA-0046-a-task-cannot-say-which-policy-it-ran-under.md`.**

**This task exists because L3 split Task 1.** `SA-0045` was the `batches`
schema *and* backlog item 16's policy lineage in one spec — three source files,
three test files, ten criteria. The two share a location (a migration in
`Ledger.__init__`) and no mechanism, which is the plan's own stated test for a
split, applied to `SA-0048` at its L2 and not to Task 1. Calibrated against
this repo's merged specs of comparable width — `SA-0019` at 592 changed lines
and `SA-0026` at 487, against a **blocking** 600-line ceiling for an `elevated`
`feature` — the unsplit version was a coin flip on item 56's exact failure.

**Interfaces:** consumes `SA-0045`'s migration. Produces `tasks.policy_sha`,
written at cell start and rewritten by PACKAGE. Makes §4.1's invalidation rule
computable for the first time.

- [x] **L1: Write the spec.**
- [ ] **L2: Read it back.** The fourth witness is the load-bearing one: *"when
      the two declarations are identical, PACKAGE leaves the row alone —
      `updated_at` does not move."* Without it, an unconditional write
      satisfies the third witness while being wrong, which L3 flagged on the
      unsplit spec as unfalsifiable.
- [ ] **L3: Spec review.**
- [ ] **L4–L8:** as Task 1.

---

## Task 3: `SA-0047` — withdrawn, the mechanism already exists

**Not written, and the id is left unused rather than recycled.** This task was
to make the scan stamp in-flight tasks `ORPHANED` before filtering, on the
premise that nothing did. `saffron/reconcile.py` already does: `IN_FLIGHT_STATES`
enumerates §4.2.1's eight states once, `reconcile(..., stamp_orphaned=True)`
stamps them, and `test_stamp_orphaned_only_fires_when_the_caller_asserts_the_premise`
drives both branches — including the property this plan cared most about, that
`saffron queue` must not stamp.

**The premise came from grepping one file.** `scheduler.py` names `ORPHANED`
only inside `REQUEUE_STATES`, and the conclusion "nothing stamps it" was drawn
from that without searching the tree. The design doc's table carried the error
too, and both are corrected.

**What is genuinely missing is a caller** — no code in `saffron/` passes
`stamp_orphaned=True`, because the parameter's own docstring is right that no
command here is a batch scan. That is one line in the loop, folded into Task 5
rather than given a spec, and Task 5's criteria now name it.

## Task 4: `SA-0048` — preflight is per task, and a night needs it per night

**Interfaces:** consumes `SA-0045`'s `runs.batch_id`. Produces
`batch_preflight(...)` returning a per-repo readiness result. Consumed by
`SA-0050`.

- [ ] **L1: Write the spec**

```markdown
---
id: SA-0048
title: every task pays for a preflight a night should pay once, and two checks a night needs do not exist
type: feature
priority: 1
depends_on:
  - SA-0047
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
**Calling it from a batch.** `SA-0050`.

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

## Task 5: `SA-0049` — the batches table has no writer

**Written: `.saffron/specs/SA-0049-a-batch-row-has-no-writer.md`.**

**This task exists because the loop's draft could not have run.** It forbade
`saffron/ledger.py` while carrying a criterion that a `batches` row is written
at start and completed at stop — and `SA-0045` had explicitly deferred
`create_batch` to "the spec that adds the loop". A criterion unsatisfiable
inside `touches` fails `scope` on every attempt with no legal repair, which is
the same defect L3 found in `SA-0048`'s draft. Found by writing it out rather
than by review.

**The split is also what keeps the widest spec off the strictest ceiling.**
`saffron/ledger.py` is in `elevate_on`, so any spec touching it runs elevated,
where `size` is **blocking** at 600 rather than advisory. Carrying the ledger
methods would have put the largest piece of this plan under the tightest
ceiling — item 56's arrangement exactly. This half is small and elevated; the
loop is large and standard.

**Interfaces:** produces the batch writer — open, close with a stop reason, and
a spend derived from the tasks rather than passed. Consumed by `SA-0050`.

- [x] **L1: Write the spec.**
- [ ] **L2: Read it back.** The fourth witness is the load-bearing one: the
      spend is summed from the tasks, never accepted from a caller — the same
      argument `set_task_state` already makes about a task and its attempts.
- [ ] **L3: Spec review.**
- [ ] **L4–L8:** as Task 1.

---

## Task 6: `SA-0050` — nothing runs the queue it prints

**Interfaces:** consumes `SA-0045`'s schema, `SA-0047`'s stamping and
`SA-0048`'s preflight. Produces `run_batch(...)` returning a stop reason.
Consumed by `SA-0051`.

- [ ] **L1: Write the spec**

```markdown
---
id: SA-0050
title: the scan resolves a queue and nothing executes it, so a night cannot happen
type: feature
priority: 1
depends_on:
  - SA-0048
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
  - saffron/scheduler.py
  - saffron/preflight.py
  - saffron/ledger.py
  - saffron/reconcile.py
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
- [ ] The scan the batch runs asserts §4.2.1's batch-scan premise —
      `reconcile(..., stamp_orphaned=True)` — so a corpse a dead scan left
      behind is stamped before filtering, and a test proves an `IMPLEMENTING`
      row is `ORPHANED` and re-queued. This is Task 3's whole content: the
      mechanism exists and has no caller
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
- [ ] A `batches` row is opened at start and closed at stop with the reason,
      through `SA-0049`'s writer — `saffron/ledger.py` is `forbidden` here, so
      this spec calls those methods and adds none
- [ ] Every `run_one_cell` call is made through an injected callable, so every
      test above runs with no network and no cell
- [ ] No test in this spec carries the `cell` marker — if one needs a real
      cell, the seam is in the wrong place

## Out of scope
**The CLI.** `saffron/cli.py` is `forbidden`; `SA-0051` wires the command.

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

## Task 7: `SA-0051` — the command

**Interfaces:** consumes `SA-0050`'s `run_batch`. Produces `saffron batch`.

- [ ] **L1: Write the spec**

```markdown
---
id: SA-0051
title: run_batch has no caller, so a night still cannot be started
type: feature
priority: 1
depends_on:
  - SA-0050
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

## Task 8: The by-hand follow-ups

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

## Task 9: Link, check and merge the stack

- [ ] **Step 1: Link the pull requests, bottom to top — by hand.**

```bash
gh stack link <SA-0045-pr> <SA-0047-pr> <SA-0048-pr> <SA-0050-pr> <SA-0051-pr>
```

`link`, not `submit`: PACKAGE has already opened every pull request, and
`submit` force-pushes from a local stack that does not exist here.

- [ ] **Step 2: Check the merge, not the pull request page.** A stacked page
      renders a clean diff because GitHub computes it from the merge base.

```bash
git merge-tree --write-tree origin/saffron/SA-0045 origin/saffron/SA-0047
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
git mv .saffron/specs/SA-00[45][0-9]-*.md .saffron/specs/done/
```

- [ ] **Step 6: Re-anchor the two live-witness tests.**
      `tests/test_scheduler.py`'s `_real_corpus` promotes named ids out of
      `specs/done/`, and the smoke check asserts the active directory is
      empty. Retiring six specs changes both. This is expected and is the
      practice those tests were written for.

- [ ] **Step 7: Run the night.** The plan is not done when the stack merges.

```bash
env CLAUDE_CODE_OAUTH_TOKEN=(...) uv run saffron batch --repo . --budget 20 --until 23:59
```

§9's criterion is *a full night runs while you sleep*, and every property in
`SA-0050` was tested against a fake clock and a fake cell. **The first real
batch is the measurement**, and whatever it returns is `docs/evidence/`
material in the shape of `docs/evidence/2026-08-25-morning-queue-from-real-rows.md`.

---

## Self-review

**Spec coverage.** Every row of the design doc's built/unbuilt table maps to a
task: the `batches` schema to `SA-0045`; item 16's policy lineage to
`SA-0046`; the `ORPHANED` stamp to `SA-0047`; `load_policy` validation, the
auth check and disk headroom to `SA-0048`; the loop, the four stop conditions
and the breaker to `SA-0050`; the command and exit codes to `SA-0051`. Item
44's enforceable half is in Task 5.

**What L3 changed, recorded because the plan was wrong rather than incomplete.**
Task 1 as first written was two mechanisms and carried a migration note that
named two of `ledger.py`'s three shapes — omitting the only one that alters an
existing table. That note would have produced a no-op migration, green tests, a
merge, and then `no such column` on the operator's real ledger, at exit `2`,
taking the five dependent specs with it. The split and the correction are Tasks
1 and 2. **The plan applied its own width test to `SA-0050` and not to Task 1**,
which is the process defect worth keeping rather than the schema one.

**Placeholders.** None. Every acceptance criterion is checkable and names what
it is checked against.

**Naming consistency.** `run_batch` is produced by `SA-0050` and consumed by
`SA-0051` under that name in both. `batch_preflight` is named once, in
`SA-0048`'s interface line, and `SA-0050` consumes it only through
`SA-0048`'s result rather than by name — deliberate, because whether it is one
function or a small module is DIAGNOSE's answer, not this plan's.

**The known risk.** `SA-0050` is the widest spec here — nine criteria against
two files — and item 56 is the standing measurement of what happens when a
spec is too wide for its own repair loop. Task 4's L2 carries an explicit
instruction to split it at the stop-conditions/breaker seam if L3 reports two
mechanisms. That check is the plan's own application of the lesson that
produced item 56.
