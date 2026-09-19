---
id: SA-0108
title: The projection is never compared with the checked walk, so Appendix T's decision rule has no instrument
type: feature
priority: 2
depends_on: [SA-0107]
touches:
  - saffron/chain_walk.py
  - saffron/cli.py
  - tests/test_chain_walk.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/report/**
  - saffron/phases/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/projection.py
  - saffron/batch.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/task.py
  - saffron/replay.py
  - saffron/events.py
budget_usd: 22
max_turns: 120
acceptance:
  - claim: >-
      The checked walk calls a merged task's chain whole only when its ledger
      rows reach an attempt holding a gate result and a pull request, and its
      stored plan and diff exist. A task lacking any one of the four is broken.
      A task lacking only some other stored file, or its event log, is whole.
      The walk reads no event log and states no edge.
    witness: tests/test_chain_walk.py::test_the_checked_walk_needs_the_rows_and_the_files_and_nothing_else
  - claim: >-
      Every merged task Q4 drops while the checked walk calls its chain whole
      is printed, naming its task id and spec id. One Q4 drops that the walk
      also calls broken is not printed. A task whose pull request another task
      shares is judged on its own. A merged task the projection left out,
      including one missing a stored file, never reaches the comparison: it is
      counted apart by reason and never printed as a break. The output states
      how many merged tasks were compared, so a zero over zero compared cannot
      read as a refutation.
    witness: tests/test_chain_walk.py::test_the_output_names_only_breaks_the_checked_walk_calls_whole
  - claim: >-
      `saffron chains` materializes the projection over the whole ledger,
      prints the comparison with its count of tasks compared, and exits 0,
      whatever number of breaks it found. A materialization that raises prints a
      line naming the exception and exits 2, since the instrument broke rather
      than the chains.
    witness: tests/test_chain_walk.py::test_saffron_chains_prints_its_count_and_exits_0_or_2_on_a_raise
---

## Context

Appendix T (rev 24) and backlog item b-946f03 reopened the emitter.
The appendix names a decision rule. Q4 must drop at least one merged pull
request that the checked walk reports as whole. `SA-0107` builds the projection
Q4 runs over. This spec builds the other half of the comparison and a command
that runs it once over the merged history. Read the appendix and
`saffron/projection.py` as `SA-0107` landed it before writing anything.
Item b-606ea3 owns the terms this spec's code uses and the glossary lacks,
"checked walk" and the `chains` verb among them.

The rule measures history recorded before backlog item 170. That item moves
artifacts to a store named by content hash, so no later task can overwrite an
earlier one's plan or diff. The case this command looks for then cannot arise.
Its answer feeds item 170's choice to migrate or abandon the tasks already
recorded.

## Problem

Nothing compares the projection with anything. The checked walk the rule names
does not exist. The projection is not materialized by any command, so the rule
never runs over the merged history. `main` dispatches every subcommand
(`saffron/cli.py:155-178`), and none of them reaches the projection.

## Out of scope

- **The projection itself.** `SA-0107` owns `saffron/projection.py`, and it is
  forbidden here. A defect found in it is reported, not fixed in this spec.
- **A check at every batch end.** It would check today's batch tree until
  item 170 lands. After that it would need to read the record, where the
  overwrite case cannot arise. `saffron batch` and `saffron/batch.py` stay as
  they are.
- **`CLAUDE.md`'s command list.** It is forbidden here, so the operator adds
  `saffron chains` to its *Running the CLI* block at merge.
- **Nothing here controls execution.** §1.4's bullet stands. No scheduling
  decision reads the projection or the comparison.
- **The recorded diff length.** A diff overwritten by one of the same length is
  not detected (`SA-0107`, *Out of scope*). The printed result says so once, so
  a zero is not read as stronger than it is.

## Notes for the agent

This spec creates `saffron/chain_walk.py` and its tests, and edits
`saffron/cli.py`. No criterion pins text the existing code determines, so each
declares a witness and no mutant, and `witness` will report `skip` for them.

**Check the second criterion's witness by hand.** In `saffron/projection.py`,
find the line comparing the diff's length with the span's recorded length. Make
it assign `True` and run the witness, which must go red. Do not declare this
as a mutant, since its find text sits in this spec and intake refuses it. It
kills only if the overwritten task's recorded plan hash equals the plan on
disk, so that only the diff differs. Build the fixture that way.

**Commit as you go.** Each turn has a 15-minute wall clock
(`TURN_TIMEOUT_S`, `saffron/cell/session.py:58`). `SA-0107`'s first cell hit it
with nothing committed, and the work was lost. Commit once the walk passes, and
again each time a criterion's test passes.

**The parent's API.** `materialize(ledger, out_dir, output_path, *,
shapes_path=DEFAULT_SHAPES)` returns `Projection(kept, left_out)`. `kept` is
`dict[int, str | None]`, task id to PullRequest IRI. `left_out` is
`dict[int, LeftOut]`, whose `reason` is a `LeftOutReason`. Import that type
and never restate its members, since
`tests/test_closed_sets_are_spelled_once.py` fails on a second spelling. It
raises `ProjectionError`. `saffron/projection.py` does not read Q4. Load the
query the way `tests/test_projection.py:219-220` does. Import the parent's
builders as `from tests.test_projection import T, build, spec_text`, inside the
test body. `build()` runs once per `tmp_path`.

**The comparator.** The checked walk follows the ledger's foreign keys (the
`runs`, `tasks`, `attempts` and `gate_results` tables,
`saffron/ledger.py:53-117`). Whole needs four things: a `runs` row, at least
one `attempts` row that `gate_results.attempt_id` points at, a `pr_url`, and a
`plan.json` and `patch.diff` in the task's batch-tree directory. The attempt
rule matches the projection's: the last attempt holding gate results generated
the diff. `export_patch` writes `patch.diff` (`saffron/cell/session.py:704,751`)
and `_drive_cell` writes `plan.json` (`:1587`). Q4 reads no other stored file,
so the walk does not ask for one, `patch.json` included, though it is written
beside `patch.diff` (`:752`). Appendix T records that
narrowing. The walk must not read `events.jsonl` or compare hashes. Doing so
would make it the projection, and the comparison would say nothing.

**Run Q4 yourself.** `SA-0107`'s materialization returns task ids and reasons,
not Q4's result. Run the committed `ontology/queries/Q4-derivation-chain.rq`
over the graph it wrote. Read the query from Saffron's own source tree, the way
`SA-0107` reads it, never from a target repo. Q4 returns pull requests
(`ontology/queries/Q4-derivation-chain.rq:25`), and several tasks can share one
`pr_url` (`saffron/scheduler.py:645-650`). `SA-0107` mints the pull request
node per task, never from `pr_url`, and returns each kept task's IRI in its
result, keyed by task id. Key the comparison by that mapping, and never spell
the IRI format here. Were it minted from `pr_url`, a whole sibling would hide
an overwritten task, which is why the second criterion's fixture includes a
shared one.

**Compare like with like.** Run the walk over the merged tasks the projection
kept. A merged task the projection left out is counted apart by its reason and
never printed as a break. Count only merged tasks. Take the reasons from
`left_out`, rather than deciding them again. A task missing its `plan.json` or
`patch.diff` is left out as `missing_artifact` rather than raising. Old tasks
lacking files are counted, and `saffron chains` still exits 0.

**Where things are.** `saffron/cli.py:152` resolves the batch tree from
`--home`. Pass that path, the ledger and an output path under `--home` into the
materialization. Never spell `~/.saffron` in `saffron/chain_walk.py`.

**Add the subcommand beside the others** (`saffron/cli.py:76-148`). It takes
`--home` like the rest and no `--repo`, because the projection covers every
repo in the ledger. Put its dispatch branch after `watch`'s
(`saffron/cli.py:167-168`) and its helper directly after `_watch`
(`saffron/cli.py:868`). Name the subcommand in the module docstring's list
(`saffron/cli.py:1-2`). Import `saffron.chain_walk` inside its branch, not at
the top of `saffron/cli.py`. The graph libraries are still `dev`-only
(`pyproject.toml:35-37`), and a module-scope import would break every command
on a host without them.

A raise needs no handler of its own. `main`'s catch-all already prints the
exception and returns 2 (`saffron/cli.py:179-186`). The third criterion's 0
path runs over the second criterion's fixture, so it finds at least one break.
It asserts the break line, the count line and exit 0. An implementation that
returns 1 when it finds breaks, copying `CELL_EXIT`'s "did not make it"
(`saffron/cli.py:40-49`), must fail it. Build its fixture with
`ledger=Ledger(home / "ledger.db")` and the batch tree at `home/batches/v0`,
since `saffron/cli.py:152` reads it there. `build()` hard-codes its output
directory, so build into `tmp_path` and then move `tmp_path/"batches"` to
`home/"batches"/"v0"`. The mirror path is absolute and survives the move. Force the raise by monkeypatching
`saffron.projection.materialize`, so `saffron/chain_walk.py` must call it
through the module. It must not catch `SystemExit`: with the
source reverted, argparse exits on the unknown subcommand, and a caught exit
would turn the raise half green.

`SA-0101` and `SA-0102` also list `saffron/cli.py`. `SA-0106` edits it in
`_batch`. The queue refuses this spec
only while `SA-0106` has a pull request open at scan time. Two candidates of one
scan are not compared, so both can edit the file the same night. The placement
above keeps the hunks apart for a rebase.

**Drive every condition in the first criterion's test.** Build one task per
missing piece: no attempt holding a gate result, no `pr_url`, no `plan.json`,
no `patch.diff`. Assert each broken. Remove an unrelated stored file from
another and assert it whole. Build one whole task with no `events.jsonl` (or
`no_ceilings=True`), so a walk that reads the log fails. Build one with
`gate_result=False` and then give it `ledger.open_attempt(task_id,
phase="IMPLEMENT")` with no gate result, as `tests/test_projection.py:324-328`
does, and assert it broken. `gate_result=False` alone writes no attempt row, and
zero attempts cannot tell a walk that asks for gate results from one that asks
for any attempt.

**Build the second criterion's fixture with three merged tasks.** One is whole.
One has a later task of the same spec overwriting its diff, and shares its
`pr_url` with a whole task. One has its diff deleted. Only the second is
printed. Add a merged task with a `pr_url` and matching plan and diff lines and
files but no attempt holding a gate result (the builder's `gate_result=False`).
The projection keeps it and Q4 drops it, but the walk calls it broken, so it is
not printed and it counts among tasks compared. Add a task the projection
returned as unattributable (`no_ceilings=True`), and one whose `spec_sha`
matches no committed version. Make both walk-whole, with a `pr_url`,
`gate_result=True` and plan and diff files, so only a comparison that skips
left-out tasks passes. Add two tasks that never merged. One is kept, in
`REJECTED`, with a `pr_url`, `gate_result=True` and matching plan and diff
lines and files. It is walk-whole and absent from Q4. The other is left out, in
`RUNNING` (`unsupported_end_state`). Neither is printed. Assert the count of
tasks compared and every per-reason count exactly. Never edit `tests/test_projection.py`. Put
a non-ASCII character in every fixture diff, for the reason `SA-0107`'s notes
give.

**Import anything new inside the test body.** Module scope does not work. A
module-scope import of a name this change adds turns `revert`'s reverted run
into a collection error. `revert` reads that error as `skip`, and the
anti-theater gate then checks nothing.

Write each test against the unfixed code before trusting it.
