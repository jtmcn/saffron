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
budget_usd: 12
max_attempts: 4
max_turns: 100
risk: elevated
---

## Context
`DESIGN.md` §4.2.1 decided the first night's scheduler in full — what a batch
reads, how the queue is filtered, what the refusal gate refuses, `K = 1`, the
stop conditions, the schema and the command. **None of it is built.** §9's v1
success criterion is a full night running unattended, and today `saffron cell`
takes one spec path on the command line.

§4.2.1 is too large for one task. This spec is its first half: **decide what a
batch would run, and be able to look at it.** The half that runs it — the loop,
the `batches` row, the stop conditions, the breaker and the exit codes — is a
separate spec, and this one deliberately leaves the ledger unwritten.

The split is where it is because both halves need a reader. A `batches` table
nothing queries, or a queue nothing prints, would be the seventh instance of
`docs/BACKLOG.md` item 18's pattern: a thing that is computed, correct, and read
by nobody. `--dry-run` is this half's reader, and it is independently useful —
it is how an operator checks tonight's queue before trusting a night to it.

## Problem
Three pieces are missing, and §10 already says where two of them live.

- **`intake.py` is half a module.** §10 calls it *"spec discovery, parse,
  validate"*; it does the last two. Its own docstring says it knows specs and not
  tasks, which is exactly the boundary discovery sits on.
- **`scheduler.py` does not exist.** §10 declares it.
- **The ledger cannot answer "has this spec been attempted?"** `queue_lines`
  reads every task in every repo with no filter, which is the morning queue's
  question, not the scheduler's.

## Acceptance criteria
- [ ] `intake.py` discovers specs: given a directory, it returns the parsed specs
      and, separately, the paths that failed to parse with their reason — a
      malformed spec must not raise past discovery and end a batch
- [ ] `ledger.py` answers, for one repo, which tasks exist per `spec_id` and
      `spec_sha` with their state
- [ ] `scheduler.py` returns an ordered queue and a list of refusals, each refusal
      carrying its spec id and one line of reason
- [ ] A spec is queued unless a task **at that `spec_sha`** is in a state done
      with it; `CHANGES_REQUESTED`, `RATE_LIMITED`, `GATE_ERROR`,
      `PREFLIGHT_FAILED` and `ORPHANED` re-queue, and a re-queued spec reports the
      existing `task_id` it would resume rather than a new one
- [ ] All six refusal conditions of §4.2.1, each with a test that produces exactly
      that refusal: an open pull request from another task, a `touches` overlap
      with an open pull request's files, a malformed spec or a moved `spec_sha`,
      a failed preflight, acceptance criteria outside `touches`, and a non-empty
      `depends_on`
- [ ] The criteria/`touches` refusal matches with `scope.matches` and is **skipped
      when `touches` is empty**
- [ ] Ordering is priority ascending, then first-seen; a test asserts it against
      at least three specs at two priorities
- [ ] The two refusals that need GitHub take an injected runner in the
      `GhRunner` shape `package.py` already uses, and every scheduler test runs
      without network
- [ ] `saffron batch --repo . --dry-run` prints the queue and the refusals and
      exits `0`; `2` if the repo cannot be read at all
- [ ] A test asserting the dry run **writes nothing** — no task row, no state
      change, no `ORPHANED` stamp

## Out of scope
**Nothing runs a cell, and nothing writes to the ledger.** No `batches` table, no
`runs.batch_id`, no scheduler loop, no stop conditions, no infrastructure breaker,
and no exit code other than the two above. `--dry-run` is not a flag on a
half-built batch; for this spec it is the only mode `saffron batch` has, and
invoking it without the flag should say so rather than do something partial.

**`intake.parse_spec` must keep accepting `depends_on`.** §4.2.1 refuses that
field at the refusal gate, deliberately and not at parse: `SA-0006` and `SA-0007`
both carry it, and raising at parse regresses `saffron cell` on two specs in this
repository. Refusing it in `scheduler.py` is the criterion; refusing it in
`intake.py` fails this spec.

**In-flight states are reported, not repaired.** §4.2.1 says the scan stamps a
task left in `IMPLEMENTING` or `REVIEWING` as `ORPHANED` before filtering. That is
a write, and it belongs to the half that writes. Here, report such a task as one
that *would* be re-queued and say why.

`saffron/phases/**`, `saffron/cell/**` and `saffron/report/**` are forbidden.
Nothing in the pipeline needs to change for a batch to decide what it would run,
and a diff reaching into them means the seam was drawn in the wrong place.

## Notes for the agent
**Which tree the specs come from is settled and is not the working copy.**
§4.2.1: the scan reads `.saffron/specs/*.md` from the export
`mirror.export_saffron_dir(mirror, base_sha, dest)` already takes — it exports the
whole `.saffron/`, so `specs/` arrives with the gates. Do not read
`repo/.saffron/specs` off disk; a spec on a branch is a draft, and this is the
same `base_sha` rule item 13 settled for gates and policy.

**The refusal gate is the cheapest gate in the system and its value is that it
costs nothing.** §4.2: *"every condition you can check without starting a cell,
check without starting a cell."* A refusal that needs a container has been written
in the wrong place.

**`depends_on` will refuse two of this repository's own specs**, and that is the
correct result, not a bug to work around. A dry run here should show `SA-0006` and
`SA-0007` refused by name.

**The criteria/`touches` check is the one with a corpse behind it.** `SA-0005`
burned $5.34 and died at turn 61 because its acceptance criteria named files its
`touches` did not cover, and the adjudication was that the fault was the spec's.
`scope.matches`, not string equality — `touches` is glob-matched in every gate
that enforces it.

**A test that constructs the value it then asserts on proves nothing about the
caller.** That is the defect that shipped `SA-0005` green (`docs/BACKLOG.md` item
18) and the one the critic caught in `SA-0007`. The dry-run test belongs at the
CLI, with the queue arriving from the scheduler rather than being handed in.

Commit after each coherent step. Uncommitted work dies with the cell.
