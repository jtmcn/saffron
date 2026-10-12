---
id: SA-0275
title: "A re-gate of a pull request's head has nowhere to be recorded, so `reconcile` can only say that no gate judged the tree"
type: feature
priority: 2
depends_on: [SA-0268, SA-0265, SA-0269]
estimated_lines: 283
estimate_measured: true
touches:
  - saffron/ledger.py
  - saffron/reconcile.py
  - saffron/cli.py
  - tests/test_ledger.py
  - tests/test_reconcile.py
  - tests/test_cli.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - harness/**
  - records/**
  - hooks/**
  - images/**
  - saffron/record/**
  - saffron/scheduler.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/finish.py
  - saffron/phases/**
  - saffron/report/**
  - saffron/view/**
  - saffron/cell/**
  - saffron/gates/**
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
  - tests/test_record_migrate.py
pending_symbols:
  - saffron/ledger.py::record_regate
budget_usd: 30
max_attempts: 3
max_turns: 150
risk: standard
acceptance:
  - claim: >-
      `Ledger.record_regate(task_id, *, head_sha, baseline_sha,
      new_failures)` files one `task_regate` fact under the task, with
      those three values as its payload. It commits one `regates` row per
      task, and a later call for the same task replaces that row whole.
      An id that names no task raises `ValueError` and writes no row and
      no fact. `Ledger.regate(task_id)` returns the task's row as a
      `sqlite3.Row`, or `None` for a task with no row. It returns `None`
      on a fresh ledger before any write, too. A fold of the record into
      a fresh ledger rebuilds every row, and so does a fold into the
      ledger that wrote them. `fold_task` with no facts removes the row
      its key filed. A ledger file whose table was dropped gains it again
      on open. The witness drives two tasks. It writes the second one
      twice and then the first. Every write uses three values that differ
      from each other and from every other write's. Each read uses a fresh
      `Ledger` on the same path.
    witness: tests/test_ledger.py::test_a_regate_is_one_fact_that_folds_back_as_the_tasks_newest_row
    wrong_versions:
      - A write that commits the row and appends no fact, so a fold into a fresh ledger rebuilds nothing.
      - A plain `INSERT`, which raises on the second write for one task.
      - An `INSERT OR IGNORE`, which keeps the first write's values.
      - A `_drop_task_rows` that leaves `regates` alone, so `fold_task(key, [])` keeps the row.
      - A read not scoped to the task, which returns the other task's row.
      - A table the write creates, not `SCHEMA`, so a read before any write raises.
      - A write or an `_apply` that swaps `head_sha` and `baseline_sha`.
  - claim: >-
      For every row `reconcile` asks GitHub about, it reads the task's
      re-gate. Those are the rows in `READY_FOR_REVIEW`, `APPROVED`,
      `CHANGES_REQUESTED` or `EXHAUSTED` that carry a `pr_url`. When the
      re-gate's `head_sha` equals the `headRefOid` GitHub answered, the
      task id, that head and the re-gate's `new_failures` land in a new
      `regated` list on the result. A green re-gate and a red one both
      land there. A re-gate at any other head lands nowhere, and so does a
      task with none. The re-gate moves no state. The witness drives nine
      rows. Six are `READY_FOR_REVIEW`. A moved head re-gated red keeps
      its draft state. An unmoved head re-gated green keeps it too. A
      re-gate at the commit PACKAGE pushed reports nothing once the head
      has moved past it. A moved head with no re-gate reports nothing. A
      merged answer over a red re-gate still moves the row to `MERGED`. A
      ready, non-draft answer over a red re-gate still moves it to
      `APPROVED`. The other three are an `APPROVED` row answered ready, an
      `EXHAUSTED` row answered as an open draft, and a
      `CHANGES_REQUESTED` row answered with changes requested. Each is
      re-gated red at the answered head, is reported, and keeps its
      state.
    witness: tests/test_reconcile.py::test_a_regate_at_the_current_head_is_reported_and_moves_no_state
    wrong_versions:
      - A version that reports the task's re-gate whatever its head.
      - A version that compares the re-gate's head with `pushed_sha` rather than `headRefOid`.
      - A version that reads the re-gate after the state check, so a row whose state does not move is skipped.
      - A version that reports only a red re-gate.
      - A version that moves a red re-gate's task to `CHANGES_REQUESTED`.
      - A version that withholds `APPROVED` from a task whose re-gate is red.
      - A version that reads the re-gate only for `READY_FOR_REVIEW` rows.
  - claim: >-
      `_print_reconcile_summary` gives the re-gate's new failures on the
      head-moved line of a task re-gated at that same head. The line keeps
      its text up to the two shortened shas, and then ends `; re-gated,
      new failures: N` for a red re-gate or `; re-gated, no new failures`
      for a green one, in place of `; no gate judged that tree`. A moved
      head with no re-gate at it keeps the old ending. A re-gate with no
      head-moved line for its task and head prints `reconcile: task <id>'s
      pull request head <head, 12 characters> re-gated, ` and then the same
      count. A result that holds a re-gate alone does not print
      `reconcile: nothing moved`. The witness drives a red and a green
      re-gate on moved heads, a moved head with none, and a re-gate at a
      head other than its task's moved head. It also drives a re-gate with
      no moved line at all, once beside the others and once alone. That
      one shares its head with another task's moved line.
    witness: tests/test_cli.py::test_a_regated_head_prints_its_new_failures_in_place_of_no_gate_judged
    wrong_versions:
      - A version that keeps `no gate judged that tree` on every head-moved line.
      - A version that matches a re-gate to its line by task id alone, so task 9's re-gate at another head lands on task 9's line.
      - A version that matches a re-gate to its line by head alone, so task 10's re-gate lands on task 7's line.
      - A version that prints no line for a re-gate with no head-moved line.
      - 'A version that still prints `reconcile: nothing moved` when the result holds only a re-gate.'
      - 'A version that prints `new failures: 0` for a green re-gate.'
---

## Context

Backlog item **97**, with the re-gate half of item **40**, which the
operator folded into it. Item 97 cites `DESIGN.md` §5.1 and §5.4, and the
change touches §5.7 and §6.1. Every line number below was read at
`bc879e2c`. This spec is the first of two, split on size. `SA-0284` is the
second. It adds `saffron regate <task id>`, which runs the task's gates
over the pull request's head and calls `record_regate`. This spec gives
that run a fact, a ledger row and a reader, and has `reconcile` print what
it found.

**A review fix reaches no gate.** The spec loop's delegate commits review
fixes onto `saffron/SA-NNNN` after PACKAGE. Measured on 2026-09-10, 34 of
38 packaged pull requests merged at a head other than the one PACKAGE
pushed (`docs/evidence/2026-09-10-review-fixes-past-package.md`). Item 40
records `SA-0029` and `SA-0080` merging over the `size` ceiling, and
`SA-0086` merging an edit to a forbidden path. Each happened in such a
round, and nothing recorded it.

**`reconcile` already names the moved head.** It asks `gh` for
`headRefOid` (`saffron/reconcile.py:101-113`). For each row it asks, it
compares that head with `pushed_sha` and appends a `HeadMoved` when the two
differ (`saffron/reconcile.py:175-179`). It does this before the state
check, so a merged answer reports too. `_print_reconcile_summary` prints
one line per `HeadMoved`, which ends `no gate judged that tree`
(`saffron/cli.py:2338-2343`). `saffron batch`, `saffron queue` and
`saffron reconcile` all print that summary (`saffron/cli.py:1922`, `:2167`,
`:2194`). Once `SA-0284` re-gates a head, the line is false for it.

**Two callers run the engine.** `reverify` runs the whole gate suite
on a commit in a gate-only cell. It judges that run against a fresh baseline in a second cell
(`saffron/phases/package.py:482-591`). Its callers are PACKAGE
(`saffron/phases/package.py:834`) and `_finish_verify`
(`saffron/cli.py:770-790`). `SA-0284` makes `regate` a third caller. It
reads the policy and gates from the export at the task's `base_sha`, as
item 97 asks. It records the head it judged, the commit its baseline ran
at, and the count of new failures. This spec stores those three values
and reads them. It runs no gate itself.

**A re-gate is a fact.** A `gate_results` row needs an attempt or a
run, and its `CHECK` requires exactly one of the two
(`saffron/ledger.py:195`). A re-gate has neither, as item 97's record
says. So the operator decided the re-gate is a record fact in a table of
its own. A red one leaves the task's state alone.

**The fact kind is already in.** This spec's own commit adds
`task_regate` to `KINDS` (`saffron/record/contract.py:45`), to
`ontology/factory.ttl` and, by render, to `CONTEXT.md`'s **Fact kind**
entry. That is how `729133f6` added `stack_finish` and `30636ea7`
added `spec_text`. So `Fact(kind="task_regate", ...)` constructs at the
tree base, and this spec edits no file of the record. The same commit
adds a **Re-gate** entry to `CONTEXT.md`, beside **Suite comparison**. Use
its words. A re-gate yields new failures, as a suite comparison does.

**What the base offers, and the shape to copy.** `SA-0177` gave the
finishing layer a fact and a table, and this spec copies that shape.
- `stack_finishes` is a table in `SCHEMA` with no reference to another
  table (`saffron/ledger.py:314-321`).
- `record_stack_finish` builds its fact with `_build_fact` and passes it
  to `_commit_and_append` (`saffron/ledger.py:1649-1675`).
- `_build_fact` raises `ValueError` for a task id that names no task,
  before anything is written (`saffron/ledger.py:569-588`).
- `_commit_and_append` applies the fact, commits, then appends it
  (`saffron/ledger.py:596-601`).
- `_apply`'s `stack_finish` branch runs one `INSERT OR REPLACE`
  (`saffron/ledger.py:969-983`). A kind with no branch reaches the
  `ValueError` at `saffron/ledger.py:997`.
- `_drop_task_rows` deletes the rows of seven key-filed tables before the
  task's own (`saffron/ledger.py:611-640`).
- `SCHEMA` runs on every open, and each table in it is `IF NOT EXISTS`
  (`saffron/ledger.py:388-395`).

## Problem

Build four things.

1. **The table.** Add `regates` to `SCHEMA` in `saffron/ledger.py`, with no
   reference to another table:

   | column | type |
   |---|---|
   | `task_key` | `TEXT PRIMARY KEY` |
   | `head_sha` | `TEXT NOT NULL` |
   | `baseline_sha` | `TEXT NOT NULL` |
   | `new_failures` | `INTEGER NOT NULL` |

   One row a task holds its newest re-gate. A fold replays a task's facts
   in order, so the last one wins.

2. **The write and the read.** Add `record_regate(task_id, *, head_sha,
   baseline_sha, new_failures)`. It builds a `task_regate` fact with
   `_build_fact`, the three values as its payload under their own names.
   It passes the fact to `_commit_and_append`. `_apply` gains a `task_regate`
   branch that replaces the task's row with the fact's `task_key` and the
   three payload values. `_drop_task_rows` deletes `regates` rows under
   the key with the other key-filed tables. `regate(task_id)` returns the
   row of the task that `task_id` names, or `None`.

3. **`reconcile` reads it.** Add `Regated`, a `NamedTuple` of `task_id`,
   `head` and `new_failures`, beside `HeadMoved` in
   `saffron/reconcile.py`. Add a `regated` list to `ReconcileResult`. For
   each row the loop asks GitHub about, read `ledger.regate` before the
   state check. Append a `Regated` when the re-gate's `head_sha` equals
   the `headRefOid` answered. Nothing about it reaches the state.

4. **The summary prints it.** Change `_print_reconcile_summary`. A
   head-moved line whose task and head match a `Regated` ends with that
   re-gate's new failures, as the third criterion words it. Print a line of its
   own for each `Regated` that no head-moved line took. Count `regated`
   among the lists that suppress `reconcile: nothing moved`.

**Docstrings the change makes false.** The ledger's module docstring says
"Only the eighteen kinds `_append` writes fold back"
(`saffron/ledger.py:6-7`). Make it nineteen. It names `stack_finishes` as
a sixteenth table outside the count (`saffron/ledger.py:16`). Add a short
sentence of its own after that one, naming `regates` as a seventeenth. The
`prose` gate identifies a sentence by a hash of its text, so a longer
sentence counts as a new one. `_drop_task_rows`' docstring names seven
tables and says "all seven deletes run first" (`saffron/ledger.py:614-616`).
Name `regates` too, and make it eight.

## Out of scope

- **Running the gates.** `SA-0284` adds `saffron regate`, which calls
  `reverify` and then `record_regate`. Here no production code calls
  `record_regate`, so it is a `pending_symbols` entry.
- **`migrate`.** `saffron/record/migrate.py` writes six key-filed tables
  into the record (`saffron/record/migrate.py:475-584`). It does not carry
  `regates`, so `saffron migrate` drops a re-gate row written before the
  record is wired. That stays open.
- **Any state change.** A red re-gate does not hold `APPROVED`, and a
  green one does not mark a pull request ready. The operator decided this,
  and also that the re-gate is not deferred to a merge train.
- **A row `reconcile` does not ask about.** A row with `merged_head_sha`
  already set moves without asking (`saffron/reconcile.py:164-170`). It
  reports no re-gate.
- **History.** The table keeps the newest re-gate alone. The record keeps
  every fact.
- **Protected text.** `DESIGN.md` §6.1 gains its sentence on the command
  with `SA-0284`, written by hand.

## Notes for the agent

**Every criterion is new code.** No text at the tree base names the
table, either method, `Regated` or the new summary text. So each criterion
declares a witness and no mutant, and `witness` reports `skip` for each.

**Imports.** Import nothing at a witness module's top that the change
adds. The reverted run would then be a collection error, which `revert`
reads as `skip`. `tests/test_cli.py` and `tests/test_reconcile.py` import
`HeadMoved` at the top already. Import `Regated` inside the test that
builds one. Compare `result.regated` with plain tuples, since a
`NamedTuple` equals the tuple of its fields.

**The ledger witness** copies the arrangement of
`tests/test_ledger.py::test_a_stack_finish_is_one_fact_under_the_top_layer_and_folds_back_by_batch`.
- A `MemoryRecord` is the record (`saffron/record/memory.py`).
- The writer is `Ledger(tmp_path / "ledger.db", record=record)`, left open.
  Each read opens a fresh `Ledger` on that path and closes it.
- Create two tasks, `TE-1` and then `TE-2`, each on its own run, and keep
  each record key right after `create_task`.
- Give every write its own `head_sha` and `baseline_sha`, different from
  each other and from every other write's.
- Read `TE-1` first, before any write, and get `None`.
- Write `TE-2` with 2 new failures. Read `TE-2`'s values, and `None` for
  `TE-1`.
- Write `TE-2` again with 0 and new shas, and read the new values.
- Write `TE-1`, then read both. `TE-2`'s row is unchanged.
- `record_regate(999, ...)` raises `ValueError`, and the table still holds
  two rows.
- The record holds two `task_regate` payloads under `TE-2`'s key, in
  order, and one under `TE-1`'s.
- Fold the record into a fresh ledger, and into the writer again. Both
  tables equal the writer's, all four columns, read with a `sqlite3`
  connection of the test's own.
- `fresh.fold_task(<TE-2's key>, [])` leaves only `TE-1`'s row there.
- Last, close every ledger, drop `regates` with `sqlite3`, and open a
  `Ledger` on the path. Its `regate` for `TE-1` returns `None`.

**The reconcile witness** uses `tests/test_reconcile.py`'s `_repo`,
`_task`, `_state` and `_FakeGh`, and its `_PUSHED` and `_FIXED`. Every row
has a `pr_url` and a pushed sha. `_task` takes the row's state. `_FakeGh` prints
only the fields `--json` asked for (`tests/test_reconcile.py:55-81`).
Each answer carries `state`, `reviewDecision`, `isDraft` and
`headRefOid`. Give each row a distinct pull request URL.
- A pushed `_PUSHED`, open draft at `_FIXED`, re-gated at `_FIXED` with 2.
  It is reported, and its state stays.
- An open draft at the pushed sha, re-gated there with 0. It is reported,
  and its state stays.
- A draft whose head moved, re-gated at the pushed sha with 3. It is not
  reported, and its state stays.
- A draft whose head moved, with no re-gate. It is not reported.
- A merged answer at a moved head, re-gated there with 1. It is reported,
  and the row is `MERGED`.
- An open answer with `isDraft` false at a moved head, re-gated there
  with 4. It is reported, and the row is `APPROVED`.

The other three rows start in the state named, each at a moved head and
re-gated there red.
- `APPROVED`, answered open with `isDraft` false. It is reported, and
  stays `APPROVED`.
- `EXHAUSTED`, answered as an open draft. It is reported, and stays
  `EXHAUSTED`.
- `CHANGES_REQUESTED`, answered open with `reviewDecision`
  `CHANGES_REQUESTED`. It is reported, and stays `CHANGES_REQUESTED`.

Assert `result.regated` equals the seven reported rows in task order, as
tuples.

**The summary witness** calls `cli._print_reconcile_summary` directly,
as `test_a_moved_head_is_named_with_both_shas` does
(`tests/test_cli.py:3405-3416`).
- Moved heads: task 7 to `b`×40, task 8 to `c`×40 and task 9 to `d`×40,
  each from `a`×40.
- Re-gates: task 7 at `b`×40 with 2, task 8 at `c`×40 with 0, task 9 at
  `f`×40 with 1, and task 10 at `b`×40 with 3. Task 10 shares task 7's
  head, so a match by head alone puts the wrong count on task 7's line.

Compare the printed lines, sorted, with exactly five expected lines.
Task 9 gets two lines: its moved line keeps `no gate judged that tree`,
and its re-gate at `f`×40 prints a line of its own. Then call it again
with one green re-gate alone. The output is exactly that re-gate's one
line.

**Wrong versions.** Each criterion lists the ones its witness must kill.
A prototype's witnesses killed all 20 on `bc879e2c` and passed with the
change. Do not run them yourself.

**The `prose` gate** reads every new comment and docstring, and the SQL
comment inside `SCHEMA` too. Write none with an em dash, a semicolon, a
contraction, the perfect tense, a hedge or a sentence over 25 words. Keep
the table's SQL comment to two lines, as for every table beside it.

**Size.** `saffron/ledger.py` is in `elevate_on`, so `size` blocks at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). A
prototype of all three criteria measured 1131 tokens with `size_gate`'s
counter on 2026-10-11. The source was 307 of them and the three witnesses
824. It held the table, both methods, the `_apply` branch, the drop, the
docstring edits, `Regated`, the reconcile read and the summary lines.
`estimated_lines` is that count over four.
