---
id: SA-0198
title: The batch header shows no trailing accept rate, though `reconcile` now records `MERGED`
type: feature
priority: 2
depends_on: [SA-0152]
estimated_lines: 360
touches:
  - saffron/scheduler.py
  - saffron/ledger.py
  - saffron/report/index.py
  - saffron/task.py
  - saffron/phases/package.py
  - saffron/report/stack.py
  - tests/test_accept_rate.py
  - tests/test_task.py
  - tests/test_stack_view.py
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
  - images/**
  - harness/**
  - records/**
  - saffron/replay.py
  - saffron/report/pr_body.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/reconcile.py
  - saffron/record/**
  - saffron/cell/**
  - saffron/gates/**
  - tests/test_report.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_package.py
  - tests/test_replay.py
  - tests/test_cli.py
budget_usd: 31
max_attempts: 3
max_turns: 180
acceptance:
  - claim: >-
      `saffron.scheduler.SETTLED_STATES` holds exactly `MERGED`,
      `REJECTED`, `MERGE_FAILED`, `EXHAUSTED`, `NOT_IMPLEMENTED`,
      `PLAN_REJECTED` and `SPEC_WITHHELD`, the seven §6 names. The witness
      holds a table that marks each of the 24 `TaskState` values settled or
      not. It asserts the table's keys equal the whole `TaskState` set, so a
      state added later fails it until someone marks that state. It asserts
      the states the table marks settled equal the seven names above, each
      spelled out in the test. It asserts `SETTLED_STATES` equals them too.
    witness: tests/test_accept_rate.py::test_every_task_state_is_marked_settled_or_not_and_the_set_agrees
    wrong_versions:
      - "`SETTLED_STATES` as `DONE_STATES` minus `DEPENDENCY_WAITING_STATES`, which keeps `SCOPE_REVIEW`."
      - "`SETTLED_STATES` as `DONE_STATES` whole, which keeps the four states whose outcome waits on the operator."
      - "`SETTLED_STATES` that also holds `ORPHANED`, a state the scheduler re-queues on its own `task_id`."
      - "`SETTLED_STATES` and the table both marking `SCOPE_REVIEW` or `ORPHANED` settled, which the seven spelled-out names refuse."
      - A table compared to `TaskState` as a subset, so a state missing from the table passes.
  - claim: >-
      `trailing_accept_rate(ledger)` in `saffron/report/index.py` returns
      the share of the window's tasks in `MERGED`, as a whole percent, a
      half rounding up. Its window holds settled tasks only. With twenty in
      it the value is the percent alone, as `75%`. With one to nineteen it
      adds `of` and the count, as `13% of 8`. With none it returns `no
      settled task yet`. The witness drives an empty ledger, and a ledger
      with one task in each of the 17 states not settled, both of which
      return that text. It drives one task in each of the seven settled
      states, which reads `14% of 7`. It drives one `MERGED` and seven
      `EXHAUSTED`, which reads `13% of 8`. It drives five tasks with no
      `MERGED`, which reads `0% of 5`. It drives fifteen `MERGED` and five
      `EXHAUSTED`, which reads `75%`.
    witness: tests/test_accept_rate.py::test_the_rate_is_merged_over_settled_and_names_the_count_below_twenty
    wrong_versions:
      - A percent from `round()` or `int()`, which reads one of eight as `12% of 8`.
      - A percent rounded up, which reads one of seven as `15% of 7`.
      - A settled set that leaves out one of the seven, which reads the seven-state ledger as `17% of 6` or `0% of 6`.
      - A task in a state not settled counted, which gives the 17-state ledger a rate.
      - The count added at twenty too, which reads `75% of 20`.
      - A ledger with no settled task read as `0%`, `0% of 0` or an em-dash.
      - A window with no `MERGED` read as the empty text rather than `0% of 5`.
      - The rate as a fraction, which reads `0.75`.
  - claim: >-
      The window is the twenty settled tasks with the latest `updated_at`,
      and a tie on `updated_at` goes to the higher `task_id`. It spans every
      repo in the ledger. A task in a state not settled is left out before
      the twenty are counted. The witness drives the 23 tasks the notes lay
      out across two repos, and asserts `75%`.
    witness: tests/test_accept_rate.py::test_the_window_is_the_twenty_latest_settled_tasks_by_update_then_task_id
    wrong_versions:
      - A window of the twenty highest `task_id`s, which reads `70%`.
      - A window of the twenty oldest `updated_at`s, which reads `70%`.
      - A window of the twenty lowest `task_id`s, which reads `70%`.
      - A tie on `updated_at` broken by the lower `task_id`, which reads `70%`.
      - Every settled task with no cut at twenty, which reads `68%`.
      - The twenty latest tasks cut first and filtered to settled after, which reads `74% of 19`.
      - A window of one repo's tasks, which reads `67% of 12` or `70% of 10`.
  - claim: >-
      Both callers of `append_queue_line` that hold a ledger put the rate in
      the page's header, under the key `trailing accept rate`, read from that
      ledger. The first is `run_task` for a task that never reached PACKAGE,
      which reads the rate after the cell wrote the task's own state. The
      second is PACKAGE's `_finish`, which reads the rate after it writes the
      task's own state. The witness drives each one, and in each the task's
      own state changes the rate.
    witness: tests/test_task.py::test_both_queue_writers_put_the_trailing_accept_rate_in_the_header
    wrong_versions:
      - Only `_finish` passes the field, so the unpackaged task's page has none.
      - "`run_task` reads the rate before `run_one_cell` returns, which reads `67% of 3` where `50% of 4` is right."
      - Only `run_task` passes the field, so the packaged task's page has none.
      - "`_finish` reads the rate before `set_task_package`, which reads `100% of 3` where `75% of 4` is right."
      - The rate counted from the rows in `queue.json`, which reads the unpackaged page as `0% of 1`.
      - The field under another key, such as `accept rate`.
  - claim: >-
      `write_stack_view(out_dir, ledger, specs)` puts the rate in the page's
      header beside `tasks` and `spend`, under the key `trailing accept
      rate`, read from its ledger over every settled task, not only the
      batch's. The witness drives a ledger whose newest batch has a layer,
      with settled tasks inside and outside that batch, over a page that
      already holds one `EXHAUSTED` row. Its header reads `75% of 4`.
    witness: tests/test_accept_rate.py::test_the_stack_view_page_carries_the_trailing_accept_rate
    wrong_versions:
      - "`write_stack_view` keeps its header to `tasks` and `spend`, so a stack night's page has no rate."
      - The rate read over the newest batch's tasks only, which reads `50% of 2`.
      - The rate counted from the rows in `queue.json`, which reads `0% of 1`.
      - The field under another key, such as `accept rate`.
---

## Context

Backlog item **b-49a2f7**. It cites `DESIGN.md` §6 and §8.

§6 names the trailing accept rate as the batch header's one number that says
whether Saffron works (`DESIGN.md:1279`). Its next paragraphs say the field had
no source, because nothing recorded a merge (`DESIGN.md:1281`). Item 52 made
`reconcile` the writer of `MERGED`. It calls `set_task_state` with the state
GitHub reports (`saffron/reconcile.py:186-188`).

The operator's hand edit at this spec's base adds a paragraph to §6
(`DESIGN.md:1285`). It reads: "**The window holds settled tasks.** The rate is
the share of them that merged." It lists seven settled states. It says a task
the scheduler re-queues on its own `task_id` has not settled, and neither has
one whose outcome still waits on the operator. That paragraph is the rule this spec builds.

**What writes the page today.** `append_queue_line` counts `tasks` and
`spend` itself and merges a caller's `header` after them
(`saffron/report/index.py:257-261`). Three places call it. `saffron/replay.py:143`
passes `{"trailing accept rate": "—"}`. `run_task` calls it for a task that
never reached PACKAGE (`saffron/task.py:611`). PACKAGE's `_finish` calls it
after `set_task_package` (`saffron/phases/package.py:968-977`). Neither of the
last two passes a `header`, so the field is absent from every page a cell
writes. Line numbers in `saffron/report/index.py` and `saffron/cli.py` are at
this spec's base, and `SA-0152` moves them. Find each by the function named
beside it.

**What this spec relies on from its parent.** `SA-0152` adds
`saffron/report/stack.py`, which does not exist at this spec's base. So
these citations are to `SA-0152`'s spec, not to code. Its criterion 3 and
its build step 3 say `write_stack_view(out_dir, ledger, specs)` renders the
newest batch's view, with `tasks` and `spend` counted as
`append_queue_line` counts them. With no layer in the newest batch it writes
nothing. Its Out of scope says it drops replay's header field. Its step 4
calls it after every `--stack` batch, so a stack night's last page write is
`write_stack_view`'s.

**The state sets.** `DONE_STATES` holds eleven states
(`saffron/scheduler.py:69-83`). `DEPENDENCY_WAITING_STATES` holds
`READY_FOR_REVIEW`, `APPROVED` and `MERGE_TRAIN` (`saffron/scheduler.py:98`).
`SCOPE_REVIEW` is in `DONE_STATES` (`saffron/scheduler.py:80`) and not in
`DEPENDENCY_WAITING_STATES`. It waits on the operator to ratify a scope
(`CONTEXT.md:655`).
`REQUEUE_STATES` holds the five states the scheduler resumes on their own
`task_id` (`saffron/scheduler.py:110-118`). `TaskState` lists all 24
(`saffron/ledger.py:37-62`).

**The ledger's clock.** The `tasks` table has `task_id`, `state` and
`updated_at`, and no column for when a task ended (`saffron/ledger.py:121-139`).
Every state write sets `updated_at` to the fact's time
(`saffron/ledger.py:728-735`, `:736-751`). `_ledger_time` writes it as
`%Y-%m-%d %H:%M:%S` in UTC, so it sorts as text (`saffron/ledger.py:314-317`).
`reconcile` writes `MERGED` when it sees the merge, so a merged task's
`updated_at` is the hour its merge was noticed.

**Measured on the real ledger, 2026-10-02, read-only.** The settled states
hold `MERGED` 154, `NOT_IMPLEMENTED` 14, `EXHAUSTED` 13 and `PLAN_REJECTED` 6.
The rest hold `ORPHANED` 14, two each of `REBUTTING`, `RATE_LIMITED` and
`IMPLEMENTING`, and one each of `PREFLIGHT_FAILED` and `GATE_ERROR`. Over the seven settled states, both orders below pick the
same twenty tasks today, 208 down to 186 with gaps. Fifteen of them are
`MERGED`, so the header would read `75%`. Across all tasks, 45 timestamps
are shared, 99 tasks between them. `reconcile` stamps several merges within
one second.

## Problem

- **The header's one number is missing.** §6 calls it the number that says
  whether this works. No page a cell writes carries it.
- **Replay's field is a confident em-dash.** §6 says a field with no
  source renders exactly that (`DESIGN.md:1281`). Replay is v0 and stays
  as it is.
- **Nothing names which tasks count.** `DONE_STATES` mixes four states whose
  outcome still waits on the operator with seven that settled. A rate over `DONE_STATES`
  counts a pull request still in review as a miss.

## Out of scope

- **`saffron/replay.py`.** It is v0, agent-free, and `forbidden`, and v1
  deletes it (`saffron/replay.py:3`). It keeps its em-dash. It also writes
  its task's state into the same ledger, `READY_FOR_REVIEW` or `EXHAUSTED`
  (`saffron/replay.py:107-108`, the one `Ledger` `saffron/cli.py:216` opens).
  So a replay that ends `EXHAUSTED` enters the window as a settled miss. The
  real ledger held no task with a `REPLAY` attempt on 2026-10-02, so this
  spec does not filter one out.
- **A per-repo rate.** The window spans every repo in the ledger, because
  the header scores Saffron rather than one repo. A page per repo waits on
  multi-repo, which is v2.
- **An ended-at column.** `updated_at` is the clock this spec reads, and
  any later write to a task moves it. `push_unpackaged_work` calls
  `record_push` after an unpackaged task's state
  (`saffron/phases/package.py:1179`), which moves it by the seconds a push
  takes. `reconcile` reads only `READY_FOR_REVIEW`, `APPROVED` and
  `CHANGES_REQUESTED` rows (`saffron/reconcile.py:49`, `:167-168`), so it
  never writes to a settled task. This spec adds no column.
- **The glossary.** `CONTEXT.md`'s **Settled task** and **Trailing accept
  rate** entries already say this. They were edited by hand in this spec's
  own pull request.
- **The ontology's sets.** `tests/ontology/test_vocabulary_agrees_with_code.py:197-204`
  checks four scheduler sets against `TaskState`. A fifth line for
  `SETTLED_STATES` belongs there, and `tests/ontology/**` is `forbidden`.
  Criterion 1's own table covers it.

## Notes for the agent

**Every criterion is new code.** The set, the read and the function do not
exist. The three page writes gain a field they never had. No text pins
honestly, so each criterion declares a witness and no mutant. Expect
`witness` to report `skip` for all five.

**Derive the set, with one named exception.** Build `SETTLED_STATES` in
`saffron/scheduler.py` from `DONE_STATES` minus `DEPENDENCY_WAITING_STATES`,
less `SCOPE_REVIEW`. No existing set names `SCOPE_REVIEW` as waiting on the
operator, so it is spelled once, with a one-line comment citing §6. A third
hand-written list of seven drifts from `DONE_STATES` in silence. Criterion 1's
table is what forces a decision when `TaskState` grows.

**Criterion 1's table is the witness's own.** Write it as a dict from each
of the 24 states to `True` or `False`. Assert its keys equal
`set(get_args(TaskState))`, not a subset. Assert the keys it marks `True`
equal a set literal of the seven names, spelled in the test. Import `SETTLED_STATES` inside the
test body.

**Put the read in `Ledger`.** `saffron/report/index.py` imports from
`saffron.ledger` already (`saffron/report/index.py:18`). Add one method that
takes a set of states and a count, and returns the states of the newest
tasks in that set. Order by `updated_at` descending, then `task_id`
descending, and filter before the cut. `trailing_accept_rate` passes it
`SETTLED_STATES` and twenty, and formats the result. Importing
`saffron.scheduler` from `saffron/report/index.py` makes no cycle. Importing
the scheduler loads no `saffron.report` module (measured 2026-10-02 with
`sys.modules`).

**Why `updated_at` and not `task_id`.** A task that fails settles the night it
runs. A task that succeeds settles when the operator merges it, days later.
Ordered by `task_id`, the window's newest end then holds every recent failure
and none of the recent successes still in review. The rate reads low for as
long as review lags. Ordered by `updated_at`, each task enters the window
when it settles. The window is the last twenty outcomes, whatever order the
tasks started in. Criterion 3's first two tasks are that case: task 1 started
first and merged last, and task 2 failed first.

**Criterion 2's percent.** Half rounds up: `math.floor(100 * merged / n + 0.5)`
or an integer form of it. Python's `round` rounds half to even and gives 12
for one in eight.

**Criterion 2's ledgers.** Use a fresh `Ledger` under `tmp_path` per case.
`upsert_repo`, `create_run`, `create_task`, then `set_task_state`, are the
public writers (`saffron/ledger.py:893`, `:1007`, `:1197`, `:1264`). The
17-state case creates one task per state that criterion 1's table marks
not settled. Read that set off the table rather than from `SETTLED_STATES`,
so a wrong set cannot hide in its own test.

**Criterion 3's arrangement.** Set each task's `updated_at` by SQL after its
state write, as other ledger tests do through `ledger._db`. Create the tasks
in this order, so `task_id` follows it. Repo `a` and repo `b` are two
`upsert_repo` origins.

| task | state | `updated_at` | repo |
| --- | --- | --- | --- |
| 1 | `MERGED` | `2026-10-02 12:00:00` | a |
| 2 | `EXHAUSTED` | `2026-10-01 00:00:00` | a |
| 3 to 15 | `MERGED` | `2026-10-01 01:NN:00`, NN the task number | b if odd, else a |
| 16 to 20 | `NOT_IMPLEMENTED` | the same rule | the same rule |
| 21 | `REJECTED` | `2026-10-01 00:30:00` | b |
| 22 | `MERGED` | `2026-10-01 00:30:00` | a |
| 23 | `READY_FOR_REVIEW` | `2026-10-02 13:00:00` | a |

The right window is tasks 1, 3 to 20 and 22: fifteen `MERGED` of twenty,
`75%`. Each wrong version under criterion 3 reads the figure it names. A
script over this table produced each figure on 2026-10-02. It also ran
`ORDER BY updated_at DESC` with no tie-break, against a real `Ledger` built
as above. SQLite returned the tied tasks 21 and 22 in `task_id` order, so
that version took task 21 and read `70%`. A Python sort on `updated_at`
alone is stable over rows fetched in `task_id` order, and read `70%` too.

**Criterion 4's two cases.** Seed the ledger `_drive` opens
(`tests/test_task.py:88`) before calling it. Open a `Ledger` at
`tmp_path / f"{spec_id}.db"`, write two `MERGED` tasks, one
`NOT_IMPLEMENTED` and a fourth task in `IMPLEMENTING`, and close it. Drive
an `EXHAUSTED` cell on that fourth task, with `push_unpackaged_work`
replaced as `_push` does. The `run_one_cell` double in `_drive`
(`tests/test_task.py:58-61`) writes no state today. Have the double set the
fourth task to `EXHAUSTED` through the `ledger` keyword `run_task` hands it
(`saffron/task.py:566-573`, in `run_task`), as the real cell does. Give
`_drive` an optional hook for it, or write the double in the test. The
page's header then holds `trailing accept rate <strong>50% of 4</strong>`.
A rate read before `run_one_cell` returns holds `67% of 3`. For `_finish`, seed a
second ledger with three `MERGED` tasks and one `REVIEWING` task. Call
`package_phase._finish` directly on the `REVIEWING` task, with a result
whose state is `MERGE_FAILED`. Its page's header then holds
`trailing accept rate <strong>75% of 4</strong>`.

**Criterion 5's case.** Build the batch as `run_stack_batch` records one.
Call `create_batch`, then `create_run` with that `batch_id`, then
`record_stack_layer` on one of its tasks (`saffron/batch.py:483-488`, in
`run_stack_batch`). The batch holds a `MERGED` layer and an `EXHAUSTED`
task. A run outside every batch holds two `MERGED` tasks. First append one
`QueueLine` in `EXHAUSTED` with `append_queue_line`. Then call
`write_stack_view(out_dir, ledger, {})`. Its page's header holds
`trailing accept rate <strong>75% of 4</strong>`. Call
`trailing_accept_rate` there rather than a second copy of the read.

**`tests/test_stack_view.py` is in `touches` for one reason.** If `SA-0152`'s
witness asserts the whole header `write_stack_view` writes, add the new
field to that expected header. Change nothing else in the file.
`tests/test_cli.py` stays `forbidden`. If one of its tests breaks, stop and
say so in the pull request body.

**Pass the field as `header=`.** `append_queue_line` already merges a
caller's header after its own counts (`saffron/report/index.py:261`). Keep
its signature, so its nineteen test calls stay as they are.

**A raise from the read is not caught.** `_finish` puts no catch around
`append_queue_line` (`saffron/phases/package.py:964-990`). A raise there
reaches `main`'s catch-all, which prints one line and exits 2
(`saffron/cli.py:245-252`). The read sits beside that call and follows the
same rule.

**Import new names inside each test body.** At module scope, a name this
change adds turns `revert`'s reverted run into a collection error. `revert`
reads that as `skip`.

Commit after each witness passes. Uncommitted work dies with the cell.
