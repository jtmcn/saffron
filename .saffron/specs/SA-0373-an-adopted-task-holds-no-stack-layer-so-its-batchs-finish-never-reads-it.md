---
id: SA-0373
title: An adopted task holds no stack layer, so its batch's finish refuses or grades the next layer against the wrong predecessor
type: bug
priority: 2
estimated_lines: 71
estimate_measured: true
touches:
  - saffron/cli.py
  - saffron/ledger.py
  - tests/test_adopt_stack_layer.py
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
  - images/**
  - records/**
  - hooks/**
  - saffron/batch.py
  - saffron/finish.py
  - saffron/end_review.py
  - saffron/regate.py
  - saffron/scheduler.py
  - saffron/follow_up.py
  - saffron/events.py
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/record/**
  - saffron/report/**
  - tests/test_cli.py
  - tests/test_batch.py
  - tests/test_finish.py
  - tests/test_regate.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 32
max_attempts: 3
max_turns: 150
acceptance:
  - claim: >-
      When `saffron adopt`'s re-gate moves a task of a stack batch to
      `READY_FOR_REVIEW`, and the task ran after every layer the batch
      holds, adopt records it as that batch's top layer. Its position is one
      more than the top layer's, or 1 when the batch holds no layer. Its
      predecessor is the top layer's task, or none. Its generation is 0 for
      a task of the stack order. Adopt writes it through
      `Ledger.record_stack_layer`, so a fold of the record rebuilds it, and
      prints a line holding `layer <position> of batch <batch id>`. The
      witness drives a batch holding no layer and a batch whose two layers
      both ran before the task. It checks the predecessor's key and head.
      It sees `saffron finish` refuse the empty batch with `holds no layer`
      before the adopt, and pass that check after it.
    witness: tests/test_adopt_stack_layer.py::test_an_adopted_task_that_ran_after_every_layer_becomes_its_batchs_top_layer
    wrong_versions:
      - The first layer taken as the predecessor, so the new layer sits on `SY-ONE`.
      - The position set to the count of layers, so the third layer reads position 2.
      - The `stack_layers` row written with SQL and no fact, so a fold loses it.
      - A batch with no layer skipped, so `saffron finish` still refuses it.
      - The layer filed under the newest batch, not the task's own run's batch.
  - claim: >-
      A follow-up the batch minted is placed at generation 1, the pass it
      ran in. A follow-up is a task `Ledger.batch_follow_ups` names. The
      witness drives a follow-up that ran after the order's one layer, which
      sits at generation 0.
    witness: tests/test_adopt_stack_layer.py::test_an_adopted_follow_up_becomes_a_layer_at_generation_one
    wrong_versions:
      - Generation always 0.
      - Generation copied from the highest layer's, so the follow-up reads 0.
  - claim: >-
      When any layer of the batch ran after the task, adopt records no layer
      and leaves the batch's layers as they were. It still moves the task to
      `READY_FOR_REVIEW`, and prints one line holding `no end review` and
      `batch <batch id>`. Tasks ran in the order `Ledger.batch_tasks` returns.
      The witness drives a batch whose only layer ran after the task. It
      drives a batch with one layer before the task and one after it, as
      `SA-0353`'s batch 73 held.
    witness: tests/test_adopt_stack_layer.py::test_an_adopted_task_a_layer_ran_after_gets_no_layer_and_a_no_end_review_line
    wrong_versions:
      - A task placed when it ran after any one layer, so the mixed batch gains a layer.
      - Only the bottom layer compared, so the mixed batch gains a layer.
      - A refusal that prints no line.
      - A refusal that also keeps the task in its old state.
  - claim: >-
      Adopt records no layer and prints neither line for a task outside a
      stack batch, or for a task that already holds a layer. A stack batch
      is the batch the task's run names, when the task holds a
      `spec_reviews` row. The witness drives a task on a plain batch with no
      review, a task whose run names no batch, and a task already a layer.
      Each still reaches `READY_FOR_REVIEW`. The same witness then adopts a
      stack batch's own task and sees it placed, with its line.
    witness: tests/test_adopt_stack_layer.py::test_adopt_outside_a_stack_batch_or_of_a_layer_records_nothing_and_prints_no_line
    wrong_versions:
      - Any batch read as a stack batch, so the plain batch's task becomes a layer.
      - The no-end-review line printed outside a stack batch.
      - No check for a task already a layer, so it gains a second row or the adopt raises.
  - claim: >-
      Adopt records a layer only on the path where its re-gate moves the
      task to `READY_FOR_REVIEW`. A red re-gate, a declined one and a task
      already `READY_FOR_REVIEW` record no layer and print neither line.
      The witness drives all three in one stack batch. It then adopts the
      red task again on a green re-gate and sees it placed, with its line.
    witness: tests/test_adopt_stack_layer.py::test_adopt_records_a_layer_only_when_its_regate_moves_the_task_to_ready_for_review
    wrong_versions:
      - The layer recorded right after the head and url, before the re-gate, so the red task becomes a layer.
      - The layer recorded on the already-`READY_FOR_REVIEW` path too.
---

## Context

Backlog item **b-323c97**, filed 2026-10-29 from the spec loop's run 50. It
cites `DESIGN.md` §5.7. Every line number below was read at `d2c80a3d`.

**The incident, four times.** Each time a task of a
`--stack --defer-end-review` batch ended `EXHAUSTED`, and `saffron adopt`
moved it to `READY_FOR_REVIEW`. `saffron finish 59`, `finish 66` and
`finish 79` then refused with "holds no layer". Batches 66 and 79 left
$47.50 and $30 of reserve unspent. In batch 73 the end review read the
adopted `SA-0353`'s whole diff as `SA-0354`'s. It raised eight false
out-of-`touches` blockers. b-619b7d's Record lines carry the same batches.

**What the home ledger holds.** It was read on 2026-11-11. None of
batches 59, 66 and 79 holds a layer. Each adopted task holds one
`spec_reviews` row. In batch 73, `SA-0353` ran after four layers
and before `SA-0354`'s layer 5. So the rule below places the first three
and prints the no-end-review line for the fourth.

**A layer is recorded only by the batch.** `record_layer` records one
`stack_layer` fact per task that reaches `READY_FOR_REVIEW`
(`saffron/batch.py:622-635`). `_is_layer` reads an `EXHAUSTED` outcome as a
miss (`saffron/batch.py:439-449`). `Ledger.record_stack_layer` looks up the
predecessor's record key and pushed sha once and bakes both into the fact
(`saffron/ledger.py:1802-1842`). `_build_fact` files the fact under the
batch the task's run names (`saffron/ledger.py:654-673`).
`Ledger.stack_layers` returns a batch's layers, lowest position first
(`saffron/ledger.py:1844-1863`).

**`saffron finish` reads only layers.** It refuses with "holds no layer"
when `stack_layers` is empty (`saffron/cli.py:2779-2782`). Otherwise the top
layer seeds its resume, and its spec comes from `deferred.json`
(`saffron/cli.py:2817-2833`). That file holds every spec of the order, the
missed ones included (`saffron/batch.py:1001-1015`).

**What adopt does now.** `_adopt` (`saffron/cli.py:3157`) takes
`EXHAUSTED`, `MERGE_FAILED`, `NOT_IMPLEMENTED` and `READY_FOR_REVIEW`
(`saffron/cli.py:3124-3126`). A `READY_FOR_REVIEW` task gets its url and,
when unresolved, its head, with no re-gate (`saffron/cli.py:3213-3220`). Any
other task is re-gated. A green re-gate on the adopted head moves it to
`READY_FOR_REVIEW` and prints one line (`saffron/cli.py:3236-3247`).

**Which batch a task ran in.** A task row names a run, and the run names
its batch (`saffron/ledger.py:135-137`, `saffron/ledger.py:124-127`). A stack
batch mints each spec's run and task as the spec comes up, and attaches the
run to the batch at once (`saffron/batch.py:693-705`). Its cell then runs on
that task and run (`saffron/cell/session.py:2359-2366`). No reader returns
a task's batch yet.

**Which batch was a stack batch.** No column says so. Only
`run_stack_batch` records a spec review against a task of a batch
(`saffron/batch.py:768`, `saffron/batch.py:803`). It reviews every spec
before its cell, and both `saffron batch --stack` and `saffron finish` pass
it a `review` (`saffron/cli.py:2682`, `saffron/cli.py:2907`). `saffron
draft` records spec reviews on a run that names no batch
(`saffron/cli.py:1777`). A plain batch records none.

**ADR 7's miss rule governs the night.** "A task that misses
`READY_FOR_REVIEW` adds no layer" (`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:64`).
The batch still adds none. The layer here comes later, from the operator's
own adopt.

**The order tasks ran in, and generation.** `Ledger.batch_tasks` returns
a batch's tasks by run id, then task id. Its docstring says that is the order the night ran
(`saffron/ledger.py:1465-1479`). A fold rebuilds tasks in the order they
were created (`saffron/record/fold.py:95-118`). The order's pass runs at
generation 0, and the follow-ups at generation 1
(`saffron/batch.py:603-605`, `saffron/batch.py:1016-1028`). Follow-ups are
minted and attached to the batch before their pass starts (`saffron/follow_up.py:474-476`).
`Ledger.batch_follow_ups` names each task of a batch whose earliest spec
text is a `follow_up` one (`saffron/ledger.py:1946-1963`). `finish` reads a
generation-1 layer's critic findings as well (`saffron/finish.py:377`).

## Problem

A task adopt moves to `READY_FOR_REVIEW` holds no layer of the stack batch
it came from. So that batch's finish refuses, or grades a later layer
against the wrong predecessor. Make the adopted task the batch's top layer
where that is safe, and say so where it is not.

**The reader.** Add one `Ledger` method in `saffron/ledger.py` that returns
the batch a task's run names, only when the task holds a `spec_reviews`
row. It returns `None` otherwise. One query over `tasks`, `runs` and
`spec_reviews` is enough. The prototype named it `stack_batch_of(task_id)`.

**The placement.** In `saffron/cli.py`, call one helper on `_adopt`'s green
path, after `set_task_state` and its line. The helper returns the line to
print, or `None`.

1. No stack batch: return `None`.
2. The task already holds a layer of that batch: return `None`.
3. A layer's task comes after the task in `ledger.batch_tasks(batch_id)`:
   record nothing, and return the no-end-review line.
4. Otherwise call `ledger.record_stack_layer` with the position, the
   predecessor and the generation the criteria name. Return the placed
   line.

Print the helper's line prefixed `adopt: task <id> (<spec id>)`. The
already-`READY_FOR_REVIEW` path, the red path and the declined path do not
call the helper. Write the five tests the criteria name, in
`tests/test_adopt_stack_layer.py`.

## Out of scope

- **`saffron finish` itself.** It reads the new layer as it reads any
  other, and stays as it is.
- **A batch whose end review already ran.** Adopt places the task there
  too. `finish` refuses such a batch as it does now. Adopt does not check
  for an end review, a `deferred.json` or a finishing layer.
- **The adopted pull request's base.** Adopt does not check that the pull
  request targets the predecessor's branch.
- **Past batches.** Batches 59, 66, 73 and 79 gain no layer. Nothing
  backfills them.
- **A `MERGE_FAILED` task whose re-gate declines.** b-619b7d owns that
  route. Such a task never reaches the green path.
- **Two documents amended by hand.** This spec's pull request amends
  `CONTEXT.md`'s **Layer** and **Adopt** entries, and one sentence of
  `DESIGN.md` §5.7. The cell must not edit either.

## Notes for the agent

**Every criterion is new code.** None declares a mutant, so `witness` will
report `skip` for each. The wrong versions under each criterion say what its
witness must still catch.

**Seed the task already a layer as `EXHAUSTED`.** A batch writes a layer
only for a task in `READY_FOR_REVIEW`. Adopt sends that state down its
early return. So production never brings a layer to the green path.
Criterion 4's arm is defensive. Seed that task as the batch's top layer in
`EXHAUSTED`, so the green path reaches the check.

**Seed criterion 5's `READY_FOR_REVIEW` task with no layer.** Put it in a
stack batch where no layer ran after it. A task seeded as a layer would
send a wrong early-return call into the already-a-layer check, which
records nothing.

**At base each witness fails in its body.** Adopt there records no layer.
So each witness fails on its first placed case.
Import nothing the change adds at module scope.

**Why a spec review marks a stack batch.** A missed task is the case here.
Its batch can hold no layer at all, as batches 59, 66 and 79 show. So a
layer cannot be the mark. Every task a stack
batch runs was reviewed first, and nothing else reviews a task on a batch.

**Why the order tasks ran in decides.** A task is cut from the last layer
that existed when it ran. If it ran after every layer, that is the top layer now, so the
end review grades its own diff. If a layer ran after it, that layer was cut
from an older head. Placing the task above it, or between, grades the wrong
diff, as batch 73 did.

**The fixtures.** `tests/test_cli.py` holds `_checkout_with_origin`,
`_seed_repo`, `_fake_gh_names_a_pull_request` and `_FakeRegate`. Import
them, and do not edit that file. `test_an_adopted_head_and_state_move_are_facts_the_fold_keeps`
shows a `MemoryRecord` shared by every `Ledger` and folded afterwards. Seed
each task on its own run, attached to its batch with
`attach_run_to_batch`, in the order the night would run them. Record a spec
review with `record_spec_review` and a follow-up's text with
`record_spec_text` and the origin `follow_up`. For the `finish` check,
write `deferred.json` naming the batch and the repo under
`<home>/batches/v0/finish/<batch id>/`, close the batch, and unset
`CLAUDE_CODE_OAUTH_TOKEN`. `finish` then refuses at the token, past the
layer check (`saffron/cli.py:2797-2800`).

**The `prose` gate** counts each new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words.

**Size.** A prototype measured 284 changed tokens with `size_gate`, against
the `bug` ceiling of 1300, with 1214 more under the test paths. It held the
reader, the helper, the one call and the five witnesses. `saffron/ledger.py`
is in `elevate_on`, so `size` blocks at this spec's tier. Every adopt test
in `tests/test_cli.py` and every test in `tests/test_regate.py` passed on
it.
