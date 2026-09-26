---
id: SA-0152
title: The queue page lists a stack batch's tasks one by one and cannot show them as a stack
type: feature
priority: 2
depends_on: [SA-0170]
touches:
  - saffron/ledger.py
  - saffron/report/stack.py
  - saffron/report/index.py
  - saffron/cli.py
  - tests/test_stack_view.py
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
  - images/**
  - harness/**
  - records/**
  - saffron/task.py
  - saffron/batch.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/events.py
  - saffron/replay.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/report/pr_body.py
  - tests/test_report.py
  - tests/test_batch.py
  - tests/test_task.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
budget_usd: 27
max_attempts: 3
max_turns: 200
acceptance:
  - claim: >-
      `stack_view(ledger, batch_id, specs)` returns `None` for a batch with
      no `stack_layers` row. For any other it returns a `StackView`. Its
      layers are that batch's rows and no other batch's, in `position`
      order, whatever order they were written in. Each carries its spec id,
      the title and `max_turns` from `specs` or `None` when `specs` lacks
      the spec, the task's state as the ledger holds it now, its spend
      summed from its attempts, its task's `budget_usd`, its highest turn
      count in one attempt, its pull request, the summary of its last
      `size` gate result or `None`, its generation, and the spec id and
      head of the layer below as the row recorded them. Its end-review
      status is `reviewed` when its `spec` and `standards` rows are both
      `reviewed`, and `error` when either is `error`. Otherwise it is
      `not_reached`, a layer with no row included. A `join` row plays no
      part. The view's order is
      every task of the batch's runs in run order, each with its state and
      its layer position or `None`. It carries the batch's spend as
      `batch_spend` reads it, the batch's budget, and a count of those
      tasks by state. The witness
      drives a layer whose predecessor was pushed again after the layer was
      recorded, a layer whose state moved to `REJECTED` afterwards, a
      generation 1 layer, a spec absent from `specs`, and a task with no
      `size` result. It drives a peak in a later attempt, and a last
      attempt with no gate result. It drives a spec with two tasks in the
      batch, and a layer's spec with a later task outside it. It drives a
      layer whose two lenses are `reviewed` beside an errored `join` row, a
      Spec `error` beside a `reviewed` Standards, the reverse, both
      `not_reached`, and a layer of a second batch with no row.
    witness: tests/test_stack_view.py::test_the_stack_view_reads_each_layer_of_one_batch_in_position_order
  - claim: >-
      `render_stack(view)` renders one `<section>` for the batch, then one
      for each layer in the order the view lists them. The batch section
      holds the batch id, its spend against its budget, each order entry
      with its state and its layer or no layer, and each state with its
      count. Each order entry reads as its spec id, its state in `<code>`,
      and `layer <n>` or `no layer`. Each layer section holds every field
      of its layer, its end-review status included, as `end review` and
      the status in `<code>`. The title and the size summary are escaped, and a
      missing value renders as the placeholder `_row` uses for an unknown
      cost, never as `None`. The witness drives one layer with every value
      set and one with every optional value `None`, and a title and a size
      summary that each hold a `<`, and the statuses `error` and
      `not_reached`.
    witness: tests/test_stack_view.py::test_the_stack_view_renders_a_section_for_the_batch_and_each_layer
  - claim: >-
      `write_stack_view(out_dir, ledger, specs)` renders the newest batch's
      view into `index.html`, between the header and the table, over the
      rows `queue.json` holds, and leaves `queue.json` as it was. When the
      newest batch has no `stack_layers` row, it writes nothing, so a page
      `append_queue_line` wrote stays byte for byte as it was, and an empty
      directory stays empty. A page `append_queue_line` writes still has its
      table on the line after its header. In the witness's second case, an
      older batch has layers, so a view of the newest batch with layers
      fails it.
    witness: tests/test_stack_view.py::test_the_queue_page_carries_the_newest_batchs_stack_view_and_only_that
  - claim: >-
      `saffron batch --stack` writes the stack view of the batch it ran into
      the queue page, with titles from the specs of its order, after
      `run_stack_batch` returns any of the five stop reasons. `saffron
      batch` without `--stack` writes no stack view. The witness drives all
      five stop reasons, and a plain batch whose loop records a layer. When
      `write_stack_view` raises after a `DRAINED` batch, the raise reaches
      `main`'s catch-all, which prints its line and exits 2.
    witness: tests/test_cli.py::test_a_stack_batch_writes_its_stack_view_into_the_queue_page
---

## Context

Backlog item **b-792ab2**, step 9 of its Done. It cites `DESIGN.md` §6.
ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides a stack batch. Section 4 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md`, under **The
summary**, is the design. The morning queue page gains a stack view, with a
section per layer and one for the batch.

**The chain this spec sits on.** `SA-0142` to `SA-0145` build the stack
batch. `SA-0143` adds `run_stack_batch` to `saffron/batch.py`. `SA-0144`
makes `saffron batch --stack` call it from `cli._batch`. `SA-0145` adds the
`stack_layers` table and `Ledger.record_stack_layer`. That table holds one
row per layer: `task_key`, `batch_key` (the batch id as text), `position`,
`spec_id`, `predecessor_key`, `predecessor_head` and `generation`.
`SA-0153` adds the `end_reviews` table and
`Ledger.record_end_review(task_id, *, lens, status, cost_usd, error)`. It
writes one row per lens of each layer, keyed on `(task_key, lens)`, with a
`status` of `reviewed`, `error` or `not_reached`. `SA-0154` writes a `join`
row under the top layer's task. `SA-0153` also widens `batch_spend` to add
each layer's end-review cost. This spec reads those names, and
`SA-0151`'s `Ledger.stack_layers`, and no other name the chain adds. Every
line number below was read at `e3020b3b`, where none of them is merged.
Read `cli.py` and `ledger.py` by symbol at the tree base.

**How the page is written today.** `append_queue_line` upserts one
`QueueLine` into `queue.json`, then re-renders `index.html` from every row
the store holds (`saffron/report/index.py:196-239`). It counts two header
fields itself, `tasks` and `spend` (`:227-230`). It renders under a lock
file (`:215`, `:242-253`) and writes each file through `_atomic_write`
(`:300-310`). `render_index` puts the header, then the table
(`:112-140`). PACKAGE calls it once per task (`saffron/phases/package.py:968`),
and so does `run_task` for a task that never packaged
(`saffron/task.py:408`). `saffron batch` writes to
`<home>/batches/v0` (`saffron/cli.py:182`).

**What the ledger already reads.** `batch_spend` sums a batch's attempts
through `runs.batch_id` (`saffron/ledger.py:897-911`). `task_spend` sums one
task's attempts (`:1053-1063`). `attempts` lists them in order
(`:1065-1071`), each with `num_turns`. `task_results` lists a task's gate
results in attempt order (`:1254-1259`). `tasks.spent_usd_est` is rolled up
only by `set_task_state` (`:585-592`), and `set_task_package` leaves it
alone (`:593-608`). `batches.budget_usd` holds a batch's budget (`:51-59`),
and no read method returns it. `max_turns` bounds each attempt, not a task
(`saffron/cell/session.py:1829`). A spec's title and `max_turns` are in no
table.

**§6 and the ledger.** §6 says the queue reads `queue.json`, not the
ledger, and calls that undecided. The stack view reads the ledger, because
`stack_layers` has no other home. The rows of the page still come from
`queue.json`.

## Problem

Build four things.

1. **The reads.** Add four read methods to `Ledger`. The layers come
   from `SA-0151`'s `Ledger.stack_layers(batch_id)`, which returns the
   batch's rows by position, each with its task's id, state, `budget_usd`
   and `pr_url`. Add no second method for them.
   - `batch_tasks(batch_id)`: every task whose run has that `batch_id`,
     ordered by `run_id`, then `task_id`, with its spec id, state and
     record key.
   - `batch_budget(batch_id)`: `batches.budget_usd`, or `None` when no
     row exists.
   - `latest_batch_id()`: the highest `batch_id`, or `None`.
   - `end_reviews(batch_id)`: every `end_reviews` row whose `task_key`
     has a `stack_layers` row with that batch's `batch_key`, as
     `task_key`, `lens` and `status`.
2. **The view.** A new module, `saffron/report/stack.py`, holds two frozen
   dataclasses and three functions. It imports from
   `saffron/report/index.py`, and `index.py` imports nothing from it, so
   the two never import each other.
   - `StackLayer`: `position`, `spec_id`, `title`, `state`, `spent_usd`,
     `budget_usd`, `peak_turns`, `max_turns`, `pr_url`, `size`,
     `generation`, `predecessor`, `predecessor_head` and `end_review`.
     `end_review` is one of `reviewed`, `error` and `not_reached`, as
     criterion 1 states, and never `None`. Match a row to its layer by
     `task_key`, never by spec id.
   - `StackView`: `batch_id`, `order`, `spent_usd`, `budget_usd`,
     `outcomes` and `layers`. `order` is a list of `(spec_id, state,
     position)` tuples, with `None` for a task that added no layer.
     `outcomes` maps each state to its count over `order`.
   - `stack_view(ledger, batch_id, specs)` builds one, as criterion 1
     says. `specs` maps a spec id to its `Spec`. A layer's `predecessor`
     is the spec id of the batch's layer whose `task_key` is this row's
     `predecessor_key`. Its `predecessor_head` is the row's own
     `predecessor_head`.
   - `render_stack(view)` renders it, as criterion 2 says. Write each
     money value as `$` and two decimals, and spend as
     `$<spent> of $<budget>`. Write turns as `<peak> of <max_turns> turns`,
     the generation as `generation <n>`, and the predecessor as
     `on <spec id> at <head>`. A missing value, a missing pull request
     included, takes criterion 2's placeholder `<P>`. So a layer with no
     budget and no turns reads `of <P>` and `<P> of <P> turns`. One with no
     predecessor reads `on <P>`. Write the end-review status as
     `end review <code><status></code>`, so an unreviewed layer never reads
     as a clean one (principles 34 and 36). Write an order entry as its spec id, its
     state in `<code>`, and `layer <n>` or `no layer`. Write an outcome as
     its state in `<code>`, a space and its count. Render the pull request
     through `_link` (`saffron/report/index.py:184-193`).
3. **The page.** `render_index` takes a keyword `stack: str = ""` and puts
   it between the header and the table. With `stack` empty, its output is
   what it is today. Add `write_stack_view(out_dir, ledger, specs)` to
   `saffron/report/stack.py`. It reads `latest_batch_id()` and builds that
   batch's view. With no view it returns `None` and writes nothing. With
   one, it creates `out_dir` as `append_queue_line` does, then takes the
   lock `_locked` holds (`saffron/report/index.py:242-253`). It reads the
   rows through `_existing_queue_rows`, counts `tasks` and `spend` as
   `append_queue_line` does, and writes `index.html` through
   `_atomic_write`. It writes nothing to `queue.json`.
4. **The call.** On `cli._batch`'s `--stack` path, once `run_stack_batch`
   returns a stop reason, call `write_stack_view(out_dir, ledger, specs)`.
   `specs` maps each candidate of the order to its `spec`. Import it by
   name, so a test can replace `cli.write_stack_view`. Put no catch
   around it. A raise reaches `main`'s catch-all
   (`saffron/cli.py:222-229`) and exits 2, as a raise from `_finish`'s
   `append_queue_line` does in `saffron cell`
   (`saffron/phases/package.py:955-984`). Otherwise map the stop reason to
   an exit code as `_batch` does now. The path without `--stack` gains no
   call.

## Out of scope

- **Spec review's detail.** A spec its review withheld shows in the order
  by its state, such as `SPEC_WITHHELD`. The view shows no revision count
  and no blocker list, though `spec_reviews` (`SA-0155`) and `spec_texts`
  (`SA-0150`) hold both.
- **Findings and their outcomes.** The view shows each layer's end-review
  status alone. The findings, their `qualifications` rows (`SA-0147`) and
  the follow-up each fed are not on the page. `SA-0174` writes them to
  the delegate's findings file.
- **The join lens's status.** Its `end_reviews` row sits under the top
  layer's task with the lens `join`. No layer's status reads it, so an
  errored join shows nowhere on the page.
- **The finish's escalations.** The finish prints each as a line
  (`SA-0167`, `SA-0170`), and no spec records one as a fact.
- **Follow-up titles.** A follow-up's spec is not in the order `_batch`
  resolved, so its layer shows no title and no `max_turns`. Its text is a
  recorded spec text (`SA-0150`), which a later spec can parse for both.
- **Keeping the view across a later write.** `append_queue_line`
  re-renders `index.html` from `queue.json` alone
  (`saffron/report/index.py:213-238`). So a `saffron cell` after the
  batch writes a page with no stack view, and nothing re-renders it. The ledger still holds every layer.
- **A spec refused by the stack loop.** It has no task, so it is in no
  order entry.
- **`DESIGN.md` §6.** It says the queue reads `queue.json` alone. It is
  protected, so the stack view's reading of the ledger is left to a hand
  edit.
- **The vocabulary.** `CONTEXT.md` has no entry for a layer. Backlog item
  b-466005 files it by hand.

## Notes for the agent

**Every criterion is new code.** No text at the tree base builds a stack
view. So each declares a witness and no mutant, and `witness` reports
`skip` for them. Import `stack_view`, `render_stack`, `StackView`,
`StackLayer` and `write_stack_view` inside each test body, so the reverted
run fails rather than failing to collect.

**`depends_on` is for the stack's order only.** It reads
`run_stack_batch`, `record_stack_layer` and the table, which `SA-0143` to
`SA-0145` add, and `SA-0151`'s `Ledger.stack_layers`. It reads `SA-0153`'s
`end_reviews` table, `record_end_review` and its wider `batch_spend`.

**Criteria 1 and 3 share one arrangement.** Write it as a helper in
`tests/test_stack_view.py`. On a `Ledger` in `tmp_path`, upsert one repo.
Create each run with `create_run(..., batch_id=...)`, so each layer's fact
carries its batch. For each task, open and close its attempts in the order
given, recording each listed gate result against its attempt. Package a
`READY_FOR_REVIEW` task with `set_task_package` and the sha and pull
request given, and give every other task `set_task_state`.

Batch A, budget 50: `TE-2`, `READY_FOR_REVIEW`, one attempt of 5 turns
costing 2.00, sha `2`×40, then its layer at position 1.

Batch B, budget 100, tasks in this run order:

| run | spec | task budget | attempts (turns, cost, gate results) | end | sha, PR |
|---|---|---|---|---|---|
| 1 | `TE-6` | 9 | (8, 0.40) | `RATE_LIMITED` | none |
| 2 | `TE-3` | 11 | (12, 1.25) | `GATE_ERROR` | none |
| 3 | `TE-7` | 18 | (44, 5.50, `size` "900 ..."), then (3, 0.00) | `READY_FOR_REVIEW` | `7`×40, `/pull/207` |
| 4 | `TE-5` | 13 | (20, 4.00) | `EXHAUSTED` | none |
| 5 | `TE-9` | 20 | (50, 3.00, `size` "2410 ..."), then (30, 2.00, `size` "1180 ... <a>", then `tests` "412 passed") | `READY_FOR_REVIEW` | `9`×40, `/pull/209` |
| 6 | `TE-6` | 16 | (20, 1.00), then (61, 5.10) | `READY_FOR_REVIEW` | `6`×40, `/pull/206` |
| 7 | `TE-4` | 12 | (10, 0.75, `size` "300 ...") | `READY_FOR_REVIEW` | `4`×40, `/pull/204` |

`TE-7`'s last attempt records no gate result, as a lens or rebuttal turn
records none (`saffron/cell/session.py:184-199`). `TE-6` ran twice in B,
and its peak is in its second attempt.

Each `size` summary is the gate's own shape, such as `1180 changed tokens
within the feature ceiling of 3000`. The `tests` result carries a `tool`.
Each pull request is `https://github.com/o/r/pull/<n>`. Then record B's
layers in this order, never in position order: `TE-6` at 3 on `TE-9`,
`TE-4` at 4 on `TE-7` at generation 1, `TE-7` at 1 on nothing, `TE-9` at 2
on `TE-7`. `TE-4`'s predecessor is not the layer at position 3, so a
predecessor read from the position below fails. Then `record_push`
`TE-7`'s task with `e`×40, and `set_task_state` `TE-9`'s task to
`REJECTED`. Then create run 8 in B, with a second `TE-4` task of one
attempt (4, 0.20), ended `RATE_LIMITED`. Last, create a run with no batch
and a second `TE-7` task on it, packaged `READY_FOR_REVIEW` at `8`×40, as
a later `saffron cell` would.

Then record end reviews with `record_end_review`. Each costs 0.0 and holds
no error unless its line says otherwise.

- `TE-4`'s layer: `spec` and `standards` `reviewed`, then `join` `error`
  with the error "join broke".
- `TE-6`'s layer: `spec` `error` at 0.25 with the error "spec broke", then
  `standards` `reviewed`.
- `TE-9`'s layer: `spec` and `standards` `not_reached`.
- `TE-7`'s layer in B: `spec` `reviewed`, then `standards` `error` with
  the error "standards broke".

`TE-2`'s layer in A and the second `TE-7` task get no row. Record them in
one loop over tuples, to keep the helper short.

`specs` holds `TE-7` (title `Seven`, `budget_usd` 25, `max_turns` 90),
`TE-9` (`Nine`, 24, 140, `depends_on: [TE-3]`), `TE-6` (`Six`, 22, 70),
`TE-3` and `TE-5`. It lacks `TE-4`.

**Criterion 1's witness** calls `stack_view(ledger, B, specs)` and asserts
the whole view. Write each expected layer as one tuple and compare it
with `dataclasses.astuple`. Compare money with `pytest.approx`, and every
other field with `==`.

- order: `TE-6` `RATE_LIMITED` `None`, `TE-3` `GATE_ERROR` `None`, `TE-7`
  `READY_FOR_REVIEW` 1, `TE-5` `EXHAUSTED` `None`, `TE-9` `REJECTED` 2,
  `TE-6` `READY_FOR_REVIEW` 3, `TE-4` `READY_FOR_REVIEW` 4, `TE-4`
  `RATE_LIMITED` `None`
- spend 23.45, budget 100.0, outcomes `RATE_LIMITED` 2, `GATE_ERROR` 1,
  `READY_FOR_REVIEW` 3, `EXHAUSTED` 1, `REJECTED` 1

| position | spec | title | state | spent | budget | peak | max | size | gen | predecessor | head | end review |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `TE-7` | Seven | `READY_FOR_REVIEW` | 5.50 | 18 | 44 | 90 | the 900 summary | 0 | `None` | `None` | `error` |
| 2 | `TE-9` | Nine | `REJECTED` | 5.00 | 20 | 50 | 140 | the 1180 summary | 0 | `TE-7` | `7`×40 | `not_reached` |
| 3 | `TE-6` | Six | `READY_FOR_REVIEW` | 6.10 | 16 | 61 | 70 | `None` | 0 | `TE-9` | `9`×40 | `error` |
| 4 | `TE-4` | `None` | `READY_FOR_REVIEW` | 0.75 | 12 | 10 | `None` | the 300 summary | 1 | `TE-7` | `7`×40 | `reviewed` |

Each layer's `pr_url` is its own. It asserts that `stack_view(ledger, A,
specs)` holds one layer, `TE-2`, whose end-review status is `not_reached`. It
then creates a third batch holding
one `EXHAUSTED` task and no layer, and asserts `stack_view` returns `None`
for it. These fail it:

- a read with no `ORDER BY position`, which returns the rows as written
- layers ordered by spec id
- a read with no batch filter, which brings in `TE-2`
- the order sorted by spec id, or taken from every task in the ledger
- turns summed over attempts, or taken from the first or last attempt
- the first `size` summary, or the last gate result of any gate
- a `size` summary read from the last attempt's results alone, which
  `TE-7` leaves empty
- a layer's task joined by spec id, alone, as that spec's newest task, or
  as its newest task within the batch.
  It brings in the second `TE-7` or the `RATE_LIMITED` `TE-6`.
- an order entry's position looked up by spec id, which gives the
  `RATE_LIMITED` `TE-6` position 3
- spend read off `tasks.spent_usd_est`, which is 0 on three layers
- a layer's budget read from `specs`
- a predecessor from `depends_on[0]`, which names `TE-3`
- a predecessor taken as the task run before, which names `TE-5`
- a predecessor taken as the layer at position - 1, which names `TE-6`
  below `TE-4`
- a head read from the predecessor's live `pushed_sha`, which is `e`×40
- the layer's own `pushed_sha` as the head
- a state fixed at `READY_FOR_REVIEW`, since every layer reached it
- a title or `max_turns` defaulted for a spec `specs` lacks
- a generation written as a literal 0
- the order taken from the layers alone
- the batch spend summed over layers, or over every attempt
- the batch budget summed from the task budgets
- outcomes counted over layers alone
- a view with no layers where `None` belongs, or `None` only for a batch
  with no task
- a layer with no `end_reviews` row read as `reviewed`, or given `None`,
  which `TE-2` fails, reasoned
- `reviewed` for a layer with one `reviewed` lens, which misreads `TE-6`
  and `TE-7`, reasoned
- `error` only for a Spec row, or only for a Standards row, which misses
  `TE-7` or `TE-6`, reasoned
- the `join` row counted, which reads `TE-4` as `error`, reasoned
- rows matched to a spec id's newest task, which finds none for `TE-7`,
  reasoned
- the batch spend summed from attempts alone, which gives 23.20, reasoned

Measured at `4797e80e`. A scratch `conftest.py` added `SA-0145`'s table
and a `record_stack_layer` written to its spec. It loaded a prototype of
the reads and `stack.py`, and ran prototypes of criteria 1 to 3's
witnesses. The right build passed all three. Each wrong build above was
applied as a text edit to the prototype, and each failed criterion 1's
witness. Without an `ORDER BY`, SQLite returned the rows in the order
written. The end-review status came after that run. So each wrong build
marked reasoned is unmeasured, and so are the spend of 23.45 and the
status column.

**Criterion 2's witness** builds a `StackView` by hand, with no ledger. Its
order is `TE-3` with no layer, then `TE-9` at 1, then `TE-5` with no layer,
then `TE-4` at 2. Layer 1 is `TE-9` with every value set. Its title is
`<b>Nine</b>` and its size summary ends in `<a>`, with spend 7.25 of 20.00
and 44 of 140 turns. It is generation 1, on `TE-7` at `7`×40. Layer 2 is `TE-4` with `title`,
`budget_usd`, `peak_turns`, `max_turns`, `pr_url`, `size`, `predecessor`
and `predecessor_head` all `None`. `TE-9`'s end-review status is `error`
and `TE-4`'s is `not_reached`. It splits the output on `<section`, and
asserts three sections: the batch, then `TE-9`, then `TE-4`. It asserts
each value in its own section, in the formats of Problem step 2. It
asserts each order entry whole, in order, such as
`TE-9 <code>READY_FOR_REVIEW</code> layer 1` and
`TE-5 <code>EXHAUSTED</code> no layer`. It asserts the escaped title and
size summary, and no raw `<b>` or `<a>`. It asserts no `None` anywhere. With `<P>` read from `_row`'s placeholder
(`saffron/report/index.py:144`), it asserts `TE-4`'s section holds
`of <P>`, `<P> of <P> turns` and `on <P>`. It asserts `<P>` appears there
at least seven times, one each for the title, budget, peak turns,
`max_turns`, pull request, size and predecessor. It asserts
`end review <code>error</code>` in `TE-9`'s section and
`end review <code>not_reached</code>` in `TE-4`'s. These fail it:

- layers sorted by spec id
- an order entry with its state left out
- a layer number taken from the entry's index, which gives `TE-4` 4
- an unescaped title, or an unescaped size summary
- a `None` printed, or an empty string where the placeholder belongs
- the end-review status left out of a layer's section, reasoned

Measured by the same run: each of these failed criterion 2's witness, but
the one marked reasoned, which is unmeasured.

**Criterion 3's witness** uses the arrangement above and an `out_dir` in
`tmp_path`. It appends two `QueueLine`s with `append_queue_line`, for
`TE-7` costing 5.50 and `TE-9` costing 5.00, and keeps the bytes of `queue.json`. It asserts the page
they wrote holds `</header>` then a newline then `<table>`, as the
template does today (`saffron/report/index.py:136-137`). It calls
`write_stack_view(out_dir, ledger, specs)`. It asserts `index.html` holds
`render_stack(stack_view(ledger, B, specs))` after `</header>` and before
`<table>`, holds no `TE-2`, and says `tasks` 2 and `spend` $10.50. It
asserts `queue.json` is unchanged. Then it creates batch C, the newest,
with one `EXHAUSTED` task and no layer. It appends one more line, keeps the
bytes of `index.html`, and asserts the same header and table join there.
It calls `write_stack_view` again and asserts the bytes are unchanged.
Last it calls `write_stack_view` on an empty directory and asserts the
directory is still empty. These fail it:

- the newest batch that has layers, which renders B over C
- a page written with no view
- a header left out
- a rewrite of `queue.json`
- a `render_index` that, given an empty `stack`, adds a line or a wrapper
- a lock file taken before the view is known, which leaves a file behind

Measured by the same run: each of the six failed criterion 3's witness.
The five without a lock file were modelled as text edits. The lock file
was modelled as a touch of `.queue.lock` before the view is read.

**Criterion 4's witness** follows `SA-0144`'s witness for `saffron batch
--stack`. It uses `_readiness_passes` (`tests/test_cli.py:2603`) and fakes
`_resolve_queue` to return the order `SY-2` (title `Second layer`,
`max_turns` 77), then `SY-1`. It fakes `cli._stack_runner` to return a
sentinel. It fakes `cli.run_stack_batch` to write, while `main`'s ledger is
open, on the ledger it is handed: a batch, a run in that batch, a task for
`SY-2` packaged `READY_FOR_REVIEW`, and its layer at position 1 with
`record_stack_layer`. The fake returns a stop reason. The witness runs
`main([..., "batch", "--stack"])` once for each of `DRAINED`, `BUDGET`,
`UNTIL`, `INFRASTRUCTURE` and `INCOMPLETE`, each with its own `--home`. It
asserts the exit code `_batch` maps each to. It reopens that home's
ledger, and asserts `<home>/batches/v0/index.html` holds
`render_stack(stack_view(ledger, <that batch>, specs))`, with `specs`
mapping `SY-2` and `SY-1` to the specs the fake returned. Then it runs
`saffron batch` without `--stack`, with a fake `run_batch` that writes the
same rows. That run takes a fresh `--home` of its own, since a stack
run's home already holds an `index.html`. It asserts no `index.html` there.
Last, it runs `--stack` once more on a fresh home, with the `DRAINED` fake
and `cli.write_stack_view` replaced by one that raises `OSError("disk
full")`. It asserts exit 2 and `main`'s line, `saffron: OSError: disk
full`. These fail it:

- a view written only on exit 0
- a view written on the plain path too
- `specs` left empty, which renders no title
- a view written before `run_stack_batch`, which finds no layer
- a broad catch around the call that keeps exit 0

This half is unmeasured. `--stack` does not exist at `4797e80e`.

**The call's place.** `SA-0151`'s `finish` runs inside
`run_stack_batch`, after the follow-ups and before the batch row closes.
`SA-0167` and `SA-0170` work inside it. So a view written once
`run_stack_batch` returns reads what the finish recorded. Criterion 4's
fake `run_stack_batch` takes every keyword the chain adds through
`**kwargs`.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**The turn ceiling.** `max_turns` is 200. The nearest history row,
`SA-0133`, peaked at 161 turns, cut off at its own ceiling of 160. So 161
is a floor, and 200 leaves 39 turns above it, as `SA-0146` does.

**Size.** `saffron/ledger.py` is in `elevate_on`, so `size` blocks at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). A
prototype of the whole change, formatted with `ruff`, was measured with
`size_gate` at `4797e80e`. It came to 1937 tokens, before the `stack_layers`
read moved to `SA-0151`, which takes about 54 off.

| part | lines | tokens |
|---|---|---|
| the three reads in `ledger.py`, estimated | 25 | 115 |
| `stack.py` | 168 | 516 |
| `render_index` and the call in `cli.py` | 8 | 42 |
| `tests/test_stack_view.py` | 363 | 954 |
| criterion 4's witness in `tests/test_cli.py` | 78 | 256 |

The prototype carries a docstring on each function and few comments.
About 290 more tokens cover test docstrings and comments, so the estimate
was about 2175 tokens. The end-review status adds about 250, unmeasured.
The fourth read takes about 50, and the status rule and its render line
50. Nine arrangement rows in one loop take 95, and the column and the new
asserts 55. The total is about 2425, 81% of the ceiling. Keep one fixture helper that
every witness in `tests/test_stack_view.py` shares, and one tuple for
each expected layer.
