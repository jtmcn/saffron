---
id: SA-0009
title: a batch has no way to find out what it would run
type: feature
priority: 1
touches:
  - saffron/intake.py
  - saffron/scheduler.py
  - saffron/ledger.py
  - saffron/cli.py
  - tests/test_intake.py
  - tests/test_scheduler.py
  - tests/test_cli.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - docs/**
  - saffron/cell/**
  - saffron/phases/**
  - saffron/report/**
budget_usd: 18
max_attempts: 4
max_turns: 100
risk: elevated
---

## Context
`DESIGN.md` §4.2.1 decided the first night's scheduler in full. **None of it is
built.** §9's v1 criterion is a full night running unattended; today `saffron
cell` takes one spec path on the command line.

§4.2.1 entire is more than `SA-0005` attempted before it died at turn 61 with no
commits. This spec is its first half — **decide what a batch would run, and print
it** — as `saffron queue`, which §10 already declares. The half that *runs* a
batch (the loop, the `batches` row, the stop conditions, the breaker, the exit
codes, and the two refusals below that need a batch to exist) is a separate spec.

The split keeps a reader on each side. A `batches` table nothing queries, or a
queue nothing prints, is `docs/BACKLOG.md` item 18's pattern again. `saffron
queue` is this half's reader and is independently useful: it is how an operator
checks tonight's queue before trusting a night to it.

## Problem
- **`saffron/intake.py` is half a module.** §10 calls it *"spec discovery, parse,
  validate"*; it does the last two.
- **`saffron/scheduler.py` does not exist.** §10 declares it.
- **`saffron/ledger.py` cannot answer "has this spec been attempted?"**
  `queue_lines` reads every task in every repo unfiltered — the morning queue's
  question, not the scheduler's.
- **`saffron/intake.py` truncates acceptance criteria at the first line.**
  `_CRITERION` is line-anchored under `re.MULTILINE`, so a wrapped criterion keeps
  only its first line. Measured on `SA-0005`: none of its seven parsed criteria
  contains a path token, because `saffron/cli.py` and `saffron/phases/package.py`
  — the paths that made it unsatisfiable — sit on continuation lines. **A refusal
  gate built on this value is blind to the case it exists for.**

## Acceptance criteria
- [ ] `saffron/intake.py` joins a wrapped acceptance criterion into one string, and a test asserts a multi-line criterion in the `SA-0005` shape yields the path token from its continuation line
- [ ] `saffron/intake.py` discovers specs in a directory, returning parsed specs and, separately, the paths that failed with their reason — a malformed spec must not raise past discovery
- [ ] Discovery orders specs by filename, so a tie in priority resolves the same way on every machine
- [ ] `saffron/ledger.py` answers, for one repo, which tasks exist per `spec_id` and `spec_sha` with their state, and resolves a repo to its id **without inserting one**
- [ ] `saffron/scheduler.py` returns an ordered queue and a list of refusals, each refusal naming its spec id — or its path, when the spec was too malformed to have an id — plus one line of reason
- [ ] A spec is queued unless a task **at that `spec_sha`** is in a state done with it; `CHANGES_REQUESTED`, `RATE_LIMITED`, `GATE_ERROR`, `PREFLIGHT_FAILED` and `ORPHANED` re-queue, and a re-queued spec reports the existing `task_id` it would resume rather than a new one
- [ ] Five refusals, each with a test producing exactly that refusal: an open pull request from another task, a `touches` overlap with an open pull request's files, a spec that failed to parse, acceptance criteria naming a path outside `touches`, and a non-empty `depends_on`
- [ ] A criterion "names a path" when it contains a repo-relative path token; the token is matched against `touches` with `scope.matches`, a bare filename is **not** matched against a `touches` entry that differs by directory, and the whole check is skipped when `touches` is empty
- [ ] The two refusals needing GitHub take an injected runner in the `GhRunner` shape the packaging phase already uses, and every test in `tests/test_scheduler.py` and `tests/test_cli.py` runs with no network and no cell
- [ ] `saffron queue --repo .` prints the queue and the refusals and exits `0`; `2` when the repo cannot be read
- [ ] A test asserting `saffron queue` writes nothing at all — no `repos` row, no task row, no state change, no `ORPHANED` stamp — against a ledger the repo has never been seen in

## Out of scope
**Nothing runs a cell and nothing writes to the ledger.** No `batches` table, no
`runs.batch_id`, no loop, no stop conditions, no breaker, no `saffron batch`.

**Two of §4.2.1's six refusals are deferred**, because neither can be produced by
a scan:

- **A failed preflight** is batch-level and exits `2` for the whole batch (§4.2.1).
  It has no spec to name, so it cannot satisfy the refusal shape above. Its
  implementation is also unreachable here: §4.2.1 defines preflight as what
  `_run_cell` does hoisted, and the `load_policy` half of that lives in
  `saffron/cell/session.py`, which is **forbidden**.
- **A moved `spec_sha`** is §4.1's per-task invalidation *at cell start* — a spec
  edited while its task is in flight. A single scan cannot observe it, and reading
  it as a scan-time rule contradicts the `spec_sha` filter directly: that filter
  exists so an edited spec **re-queues**, and §4.2.1 says dropping the key "costs
  the edit case".

**`saffron/intake.parse_spec` must keep accepting `depends_on`.** §4.2.1 refuses
that field at the refusal gate deliberately, not at parse: `SA-0006` and `SA-0007`
carry it, and raising at parse regresses `saffron cell` on two specs here.
Refusing it in `saffron/scheduler.py` is the criterion; refusing it in
`saffron/intake.py` fails this spec.

**In-flight states are reported, not repaired.** §4.2.1 stamps a task left in
`IMPLEMENTING` as `ORPHANED` before filtering. That is a write, and it belongs to
the half that writes.

`saffron/phases/**`, `saffron/cell/**` and `saffron/report/**` are forbidden.
Nothing in the pipeline changes for a batch to decide what it would run.

## Notes for the agent
**The specs come from `base_sha`, not the working copy.** §4.2.1: the scan reads
`.saffron/specs/*.md` from the export `mirror.export_saffron_dir(mirror, base_sha,
dest)` already takes — it exports the whole `.saffron/`, so `specs/` arrives with
the gates. **Discovery must take a directory, not a repo**, which is what keeps
every test in this spec offline: the caller does the export, and a test hands
discovery a temporary directory.

**The criteria/`touches` refusal is the one with a corpse behind it**, and it is
also the one most likely to be built blind. `SA-0005` burned $5.34 and died at
turn 61 because its acceptance criteria named files its `touches` did not cover,
and the adjudication was that the fault was the spec's. Two ways to get it wrong,
both measured on the real spec:

- Built on today's `spec.acceptance_criteria`, it **passes `SA-0005` clean**,
  because the truncation drops the lines the paths are on. Fix the parse first,
  then the gate; a test whose fixture is a single-line criterion proves nothing.
- `scope.matches("intake.py", "saffron/intake.py")` is `False`. A gate that
  quietly resolves bare filenames against `touches` by suffix is a *different,
  more permissive rule* than the one `scope` enforces, and the two must not drift.

**What `saffron queue` should print on this repository, measured 2026-08-26
against `~/.saffron/ledger.db`:** `SA-0001` and `SA-0008` queued, everything else
filtered out with a `READY_FOR_REVIEW` task at the same `spec_sha`, **and nothing
refused**. In particular the `depends_on` refusal will not fire on `SA-0006` or
`SA-0007` — the filter removes them first, because both have a task at exactly
their current sha. Use this as a smoke check, not as proof the refusals work; the
refusals need their own fixtures.

**The injected-runner shape already exists**: `GhRunner` in
`saffron/phases/package.py`, read for its signature only — that file is forbidden.

**A test that constructs the value it then asserts on proves nothing about the
caller.** That is the defect that shipped `SA-0005` green (item 18) and the one
the critic caught in `SA-0007`. The `saffron queue` test belongs at the CLI, with
the queue arriving from `saffron/scheduler.py` rather than being handed in.

Commit after each coherent step. Uncommitted work dies with the cell.
