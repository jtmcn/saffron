# v0 — the harness, agent-free

Records only the decisions `DESIGN.md` §9 leaves open. Everything not stated here
is already fixed by `DESIGN.md`; where the two disagree, `DESIGN.md` wins and this
file is the defect.

Vocabulary is `CONTEXT.md`'s, without exception.

## What v0 is

A host-side replay harness. It takes an already-merged pull request from a target
repo, treats it as though a task had produced it, and runs the part of the pipeline
that has no model in it: spec parse → gate contract runner → baseline subtraction →
PR body → index.

No agent, no cell, no cell runtime, no proxy, no push, no PR. The deliverable is a
rendered file.

**Success criterion** (§9, unchanged): replay a merged PR, and the gate table plus
PR body tell you something you'd have had to read the diff to learn.

## Target repo

`thermal-edge`. It is the only candidate — `saffron` has no code for a gate to run
against, and v0's whole purpose is meeting real tool output.

Three pull requests, chosen small and dissimilar rather than useful:

| PR | Files | Shape |
|---|---|---|
| #172 | 10 | weather CLI behaviour change |
| #169 | 4 | test-infrastructure scoping |
| #165 | 4 | dbt hook removal |

Each gets a spec written retroactively at `.saffron/specs/TE-9001…9003-*.md`. The
`9000` block is reserved for replay specs so they never collide with real ones.

## Decision 1 — the ledger exists in v0, with five tables

`repos`, `runs`, `tasks`, `gate_results`, `failures`, exactly as §4.1 declares them.
The other five tables wait for an agent to have something to put in them.

`failures` is a table in v0 rather than a log line for the reason §4.1 gives:
baseline subtraction keys on `(gate, file, code)`, and an identity that has to be
queryable is not one you re-derive by parsing files. The alternative — render
straight from memory — makes v1 retrofit a database underneath a working renderer,
which is the painful direction.

`gate_results.attempt_id` is null for baseline results and `run_id` is null for
task results, per §4.1. v0 has no `attempts` table, so v0 sets `attempt_id` to the
`task_id`; the column is renamed and backfilled when `attempts` lands in v1. Stated
because a silent type pun here is exactly the kind of thing that survives a
revision.

## Decision 2 — contract gates plus `scope`

Declared in the repo, satisfying the gate contract (§5.4): `format`, `lint`,
`types`, `tests`.

One core gate: `scope`, because it is a set-subset test over `git diff --name-only`
and it is the only core gate that makes a replayed gate table more informative than
the repo's own CI would be.

`size`, `secrets`, `integrity` and `revert` wait for v1. `integrity` and `revert`
both exist to catch an agent gaming a gate, and there is no agent.

`tests` accepts a test-subset argument from day one even though `revert` is not
built. It is the single most constraining line in the contract (§5.4) and it costs
nothing to honour before the gate that needs it exists.

**`tests` runs unit tests only** — `pytest -m unit`. thermal-edge's integration
suite needs Postgres, and a replay that depends on a live database is not
reproducible. Integration coverage is a v0.5 concern, where fixture services live
inside a cell image.

## Decision 3 — onboarding is written into `thermal-edge`

`.saffron/policy.yaml`, `.saffron/gates/*`, `.saffron/specs/*` land in the target
repo on a branch cut for the purpose, left uncommitted in the working tree until
the operator has read them.

This is the §2.1 test running for the first time: if writing them requires a line
of Saffron, the boundary has already failed. Time it.

## Decision 4 — `touches` is written ex-ante, not derived

Deriving each spec's `touches` from its pull request's own changed files makes the
`scope` gate pass by construction, which measures nothing.

`touches` is therefore written as the declaration a person would plausibly have
made *before* seeing the diff. A pull request that wandered outside it produces a
red `scope` gate, and that is a true statement about that pull request.

## Decision 5 — no Jinja, no CLI framework

`pydantic`, `pyyaml`, and the standard library: `sqlite3`, `argparse`,
`subprocess`.

§10 specifies `report/templates/` and §6 says "~50 lines of Jinja". v0's PR body
has no findings, no rebuttals, no disagreement section and no critic assessment,
because none of those have a producer yet — so f-strings cover it and Jinja earns
its place in v1 when they arrive. Marked in-place with a `ponytail:` comment naming
the upgrade.

## The mechanism v0 is actually built to test

Baseline subtraction, keyed on `(gate, file, code)`, with `line` carried for
display and excluded from the identity (§5.4).

§9 names this as one of two defects a single replayed pull request surfaces in an
hour and no amount of rereading surfaces at all. So it gets the load-bearing test:
a fixture in which the head diff inserts thirty lines at the top of a file, every
pre-existing failure shifts line number, and the subtraction must yield the empty
set. A line-keyed implementation fails that test loudly.

The second mechanism, and the second real test: `error` is not `fail`. A gate whose
stdout will not parse, that times out, or whose toolchain is missing returns
`error`, aborts, and is charged to nobody. The runner is tested against fixture
executables that actually misbehave — a malformed emitter and a hanging one — not
against a mocked `subprocess`.

## Data flow

```
spec  ──intake──▶  Task
policy ──────────▶  gate declarations

  worktree @ base_sha ──runner──▶ gate results ──▶ ledger   (baseline; run_id set)
  worktree @ head_sha ──runner──▶ gate results ──▶ ledger   (task; attempt_id set)
                                 + core `scope` over git diff --name-only
                      │
                      ▼
  new failures = head − baseline, on (gate, file, code)
                      ▼
              pr_body.md  +  index.html
```

Both worktrees are cut from a bare mirror at `~/.saffron/mirrors/<repo>.git`, so v0
already cannot reach the real remote. The property is free here and expensive to
retrofit.

## Layout

Only the files v0 executes, in §10's positions:

```
saffron/
  cli.py                 # replay, index
  ledger.py              # the five tables + DAO
  intake.py              # spec frontmatter → validated model
  repos/policy.py        # policy.yaml → validated model
  gates/contract.py      # the gate result schema
  gates/runner.py        # shell out, parse, time out, error ≠ fail
  gates/core/scope.py    # changed files ⊆ touches
  report/pr_body.py  report/index.py
  replay.py              # v0 only — v1 deletes it for scheduler.py + supervisor.py
```

`replay.py` is named as scaffolding deliberately. Everything beside it survives
into v1 untouched; it does not.

## Out of scope

Cells, the cell runtime, the proxy, the mirror's write path, `DIAGNOSE`, the plan
checkpoint, the repair loop, critics, lenses, findings, rebuttal, the merge train,
conflict sets, stacking, budgets, `saffron gc`, and the `batches`, `attempts`,
`findings` and `decisions` tables.

Each of them needs an agent to mean anything, and v0 has none.
