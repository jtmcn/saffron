---
id: SA-0303
title: "A stack batch's follow-ups are qualified and written at the packaged heads, not the heads the end review graded"
type: feature
priority: 2
depends_on: [SA-0302]
estimated_lines: 443
estimate_measured: true
touches:
  - saffron/qualify.py
  - saffron/follow_up.py
  - saffron/cli.py
  - tests/test_qualify.py
  - tests/test_follow_up.py
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
  - saffron/view/**
  - saffron/report/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/agents/**
  - saffron/phases/**
  - saffron/ledger.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/end_review.py
  - saffron/finish.py
  - saffron/regate.py
  - tests/test_scheduler.py
  - tests/test_end_review.py
  - tests/test_batch.py
  - tests/test_session.py
budget_usd: 34
max_attempts: 3
max_turns: 180
risk: standard
acceptance:
  - claim: >-
      `qualify.qualify` takes the end review's graded fields as a required
      keyword, and reads every range from them. The join's findings are
      anchored and probed from the bottom layer's diff base to the top
      layer's graded head. Each layer's end-review findings are read from
      its own diff base to its graded head. The probe runs at that range's
      base, over that range's patch. A layer's in-cell REVIEW concerns cite
      its packaged head, so they are still read over the range
      `end_review.layer_fields` gives, its packaged head's parent to its
      packaged head. A layer missing from the fields reads that packaged
      range for its end-review findings too. That holds for a missing top
      layer and a missing bottom layer alike, in the join's range and in
      its own. The witness drives both ranges over moved heads, a moved
      layer with both kinds of finding, then each missing layer.
    witness: tests/test_qualify.py::test_findings_are_anchored_and_probed_over_the_range_the_end_review_graded
    mutant:
      file: saffron/qualify.py
      find: "head=top.head,"
      replace: "head=bottom.head,"
    wrong_versions:
      - The join's range starts at the bottom layer's graded head's parent.
      - The join's range still ends at the top layer's packaged head.
      - The join's range starts at the bottom layer's recorded `base`.
      - A layer's range starts at its graded head's parent.
      - A layer's range starts at its recorded `base`.
      - A layer missing from the fields raises `KeyError`.
      - The fields are ignored, so every range stays the packaged one.
      - A layer missing from the fields is skipped, and its findings are never recorded.
      - A layer's in-cell concerns are anchored over its graded range.
      - A layer's end-review findings stay on its packaged range while its in-cell concerns move.
  - claim: >-
      `write_follow_ups` reads every head and range from `stack.fields`,
      with the same fallback for a missing layer. The stack's test paths
      come from the bottom layer's diff base to the top layer's graded
      head. The probe check reads the top layer's graded head. Each writer
      prompt carries its origin layer's diff, from its diff base to its
      graded head. The prompt names that range, the origin's graded head
      and the top's graded head. Each in-cell concern's line in the prompt
      names the origin's packaged head, the head its lines cite. An
      end-review finding's line names none. A missing top layer and a
      missing bottom layer each read their packaged head. The witness
      drives a prompt for each layer of a moved stack, a group holding both
      kinds of finding, then each missing layer.
    witness: tests/test_follow_up.py::test_a_follow_up_is_written_from_the_heads_and_ranges_the_end_review_graded
    mutant:
      file: saffron/follow_up.py
      find: "top_head=top.head,"
      replace: "top_head=bottom.head,"
    wrong_versions:
      - The stack's test paths start at the bottom layer's graded head's parent.
      - The stack's test paths start at the bottom layer's packaged diff base.
      - The stack's test paths end at the top layer's packaged head.
      - The probe check reads the top layer's packaged head.
      - The origin diff starts at the origin's graded head's parent.
      - The origin is read through `layer_fields`, so its diff and head are the packaged ones.
      - The prompt still labels the origin diff as its head's parent to its head, while the diff starts at the diff base.
      - The prompt's top head is the origin's head.
      - A missing top layer raises `KeyError`.
      - A missing bottom layer raises `KeyError`.
      - An in-cell concern's line names no head.
      - An in-cell concern's line names the origin's graded head.
      - Every finding's line names the packaged head, an end-review finding's included.
  - claim: >-
      `_stack_follow_ups` hands `qualify` the stack's own `fields`. It
      seeds every writer cell at the top layer's graded fields, or at the
      fields `layer_fields` gives when the end review graded none for the
      top layer. The witness drives both.
    witness: tests/test_cli.py::test_a_stack_batchs_follow_up_writer_is_seeded_at_the_top_head_the_end_review_graded
    wrong_versions:
      - The writer cell is still seeded at `layer_fields` of the top layer.
      - "`qualify` is handed an empty mapping."
      - A top layer missing from the fields raises `KeyError`, so no writer cell opens.
  - claim: >-
      With every layer's fields equal to what `layer_fields` gives, as an
      unmoved stack's end review grades them, the join's probe runs at the
      bottom layer's packaged head's parent. Each layer's probe runs at its
      own packaged head's parent, as at base.
    witness: tests/test_qualify.py::test_the_joins_probes_run_on_the_stack_counted_from_the_bottom_run
    preserves: true
    wrong_versions:
      - The join's range starts at the bottom layer's recorded `base`.
      - A layer's range starts at its head, so its diff is empty.
  - claim: >-
      With every layer's fields equal to what `layer_fields` gives, each
      writer prompt carries its origin layer's own commit and names the top
      layer's packaged head, as at base.
    witness: tests/test_follow_up.py::test_an_accepted_follow_up_is_a_minted_task_with_its_text_and_its_writers_cost
    preserves: true
    wrong_versions:
      - The prompt's top head is the origin's head.
      - The origin diff starts at the origin's head, so it is empty.
---

## Context

Backlog item **b-8a0c9a**, under `DESIGN.md` §5.7 and ADR 7. It is the
third of six specs that item splits into. `SA-0302` has the end review
grade each layer at its branch head and record what it graded in
`StackReview.fields`. This spec has qualification and the follow-up writer
read those fields. `SA-0305` then runs both outside a batch. Every line
below was read at `cb2b0602`. Its `saffron/` is `e8f5529e`'s.
`SA-0302` edits `saffron/cli.py` first, and `SA-0300` moves lines in
`saffron/follow_up.py`. So find each function in those two files by name.

**What `SA-0302` gives this spec.** `LayerFields` gains `diff_base`, the
commit a layer's diff starts from. `end_review.layer_fields` sets it to
the pushed head's parent. `StackReview.fields` maps a task key to the
fields the end review graded that layer at. It holds every layer either
walk resolved. The join resolves every layer before the layer walk, so a
layer the reserve did not reach is still there whenever the join ran. A
layer neither walk reached, or whose resolution failed, is absent. So a
layer's presence says nothing about whether it was reviewed.
`run_end_review` returns it (`SA-0302`, Problem 4). `_end_review_error_reviews` builds a
`StackReview` with no `fields` (`saffron/cli.py:839`).

**Qualification reads the packaged heads.** `qualify` reads the top and
bottom layers through `end_review.layer_fields`
(`saffron/qualify.py:223-224`). It walks the join from the bottom layer's
head's parent to the top layer's head (`:231-232`). It reads each layer
the same way, over `head^..head` (`:255`, `:260-261`). That range holds
the layer's end-review findings and its in-cell REVIEW concerns together
(`:251-252`). `_in_cell_concerns` rebuilds those concerns from the
`findings` table, at the line numbers the task's own REVIEW cited at its
packaged head (`:81-96`). `_qualify_range`
anchors over `base..head`, reads each cited file at `head`, and probes at
`base` over that range's patch (`:124-152`).

**The follow-up writer reads them too.** `write_follow_ups` reads the top
and bottom layers through `layer_fields` (`saffron/follow_up.py:246-247`).
The stack's test paths come from the bottom head's parent to the top head
(`:248-252`). The probe check reads the top head (`:289`). The origin's
fields come from `layer_fields` too (`:309`). The prompt's origin diff is
its head's parent to its head, and so is the range the prompt names
(`:326-328`, `:169`). The prompt names the origin head and the top head
(`:148-150`).

**The writer cell is seeded at the packaged top head.** `_stack_follow_ups`
reads the top layer through `layer_fields` before anything else runs
(`saffron/cli.py:1563`). Each writer cell opens at it (`:1598-1599`).
`qualify.qualify` is called with no fields (`:1572-1584`). The origin's
spec id comes from `layer_fields` too (`:1592`), inside each `write`
call.

**Inside a batch the two agree.** Each branch still sits at its pushed head
when a batch's own end review runs (`SA-0302`, Problem 5). So each graded
range is the packaged one, and a batch's follow-ups do not change.

## Problem

1. **One fallback reads a layer's graded fields.** A public helper in
   `saffron/qualify.py` takes the ledger, the fields mapping and a task
   key. It returns the mapping's entry, or `end_review.layer_fields` for a
   key the mapping lacks. `follow_up.py` imports it from `qualify.py`, as it
   imports the rest of that module now (`saffron/follow_up.py:26`). `cli.py`
   reaches it through the `qualify` module.
2. **`qualify` takes the fields.** `qualify.qualify` gains a required
   keyword-only `fields`. The join's top and bottom layers and each layer
   are read through the helper. The join's base is the bottom layer's
   `diff_base`. A layer's base is its own `diff_base`. Each head is the
   graded `head`. A layer's in-cell concerns get a range of their own,
   read through `layer_fields`, after its end-review findings. Rows keep
   today's order.
3. **`write_follow_ups` reads `stack.fields`.** The top, bottom and origin
   layers are read through the helper. The stack's test paths start at
   the bottom layer's `diff_base`. The origin diff starts at the origin's
   `diff_base`. The range the prompt names is the one the diff was read
   over. A finding whose lens is one of `review.LENSES` is an in-cell
   concern, and its line names the origin's packaged head. The packaged
   head is read through `layer_fields` only for a group that holds one.
4. **`_stack_follow_ups` passes them on.** Its `qualify` call passes
   `stack.fields`. Its top layer is read through the helper, so each writer
   cell opens at the graded top head. Each `write` call reads its origin
   layer through the helper too. Graded fields keep the layer's spec id,
   so the writer's agent is named as before. A layer the ledger has not
   recorded still raises there, as `layer_fields` does.

## Out of scope

- How the end review resolves a layer. `SA-0302` owns `branch_heads` and
  `StackReview.fields`.
- Ending a batch without its end review, resuming a closed batch's tail,
  and `saffron finish`. `SA-0301`, `SA-0304` and `SA-0305` build those.
- The finishing layer's parent. ADR 7 keeps it at the top layer's recorded
  `pushed_sha`, and `saffron/finish.py` reads it. `SA-0306` moves it to the
  graded head. This spec does not touch it.
- A follow-up's cell is seeded from its predecessor's branch, fetched
  fresh (`saffron/cli.py:771-776`), so it stacks on the head the branch
  carries. Only its `stack_layers` row's `predecessor_head` keeps the
  recorded `pushed_sha`.
- `finish.write_findings` names each finding's `head` as the layer's
  `pushed_sha` (`saffron/finish.py:259`). A finding anchored at a graded
  head is still reported against the packaged one. `SA-0306` changes
  that file.
- A stack whose top layer alone is missing from the fields mixes heads.
  Its writer cell opens at the packaged top head, while a lower origin is
  graded. Only a failed resolution of the top layer reaches that.

## Notes for the agent

**Which criteria are edits.** Criteria 1 and 2 each mutate a line the
change keeps. Leave the join's head argument in `qualify.qualify` as it is.
Leave the prompt's top head argument in `write_follow_ups` as it is too. Criterion 3
judges the new wiring in `_stack_follow_ups`. It declares no mutant, and
`witness` reports `skip`. Criteria 4 and 5 name tests that exist now.
The wrong versions under each criterion are what its witness must kill. Do
not run them yourself.

**Existing tests that change.**

- `tests/test_qualify.py`: `_Built.run` passes `fields`, built by calling
  `layer_fields` for each of its layers. Its docstring's count of the
  keywords it forwards goes from eight to nine (`:328`). Every existing
  test keeps its assertions. Criterion 4's witness is one of them.
- `tests/test_follow_up.py`: `_stack` builds its `StackReview` with the
  same `fields`. Criterion 5's witness is one of them.
- `tests/test_cli.py`'s
  `test_a_stack_batchs_follow_ups_are_qualified_and_written_from_the_pinned_base_at_the_stacks_top`
  replaces `cli.end_review.layer_fields` with a fake. Its ledger records
  no layers, so every read must come from the stack's `fields`. Pass that
  fake's two results as the stack's `fields`, and drop the replacement.
  The top layer, the `qualify` call and each `write` call's origin then
  read only those. Its `k-gone` case still stops before `qualify`, because
  the fallback reads a layer the ledger does not have.

**Import new names inside each test.** Both test modules' docstrings say
why. A module-scope import of a name the change adds turns the reverted
run into a collection error.

**Fixtures, as the prototype built them.**

- `DIFF_FLAGS` diffs with three lines of context, and `anchor` counts a
  context line as inside a hunk. So put each review commit's line more than
  three lines from the packaged change it sits beside. A review line at 5
  beside a change at 2 anchors over the packaged range too.
- Criterion 1: one mirror. `A`, then `M` changes a file the layers never
  touch. `H1` and `H2` are the packaged heads. Branch from `H1`: `R1` adds a
  review line, `H2b` restacks `H2`'s change on it, `R2` adds TE-2's review
  line. Record the two layers at `H1` and `H2`. Build each graded entry with
  `dataclasses.replace` over `layer_fields`. Give each a recorded `base`
  apart from its `diff_base`, and a `diff_base` apart from its head's
  parent. Cite one finding per changed line and one on `M`'s line, in the
  join and each layer, and give one in each range a probe. Replace
  `session.probe_findings` with a double recording each call's base and
  patch. Record two in-cell concerns on TE-2, under a lens in
  `review.LENSES`. One cites its packaged change and one its review line.
  Then run the same stack again, once without the top layer's entry and
  once without the bottom's.
- Criterion 2: extend `_build`'s mirror. From `base`, `D` adds a test
  file, and `H1r` rebases `H1`'s change onto it. `R1` and `R2` are review
  commits that each add a test file. `H2r` restacks `H2`'s change on
  `R1`. Grade the bottom layer from `D` to `R1`, and the top from `R1` to
  `R2`. Give the top group a probe whose find text only `R2` carries, and
  an in-cell concern. Pass one group per layer, and a `write` double that
  records each prompt.
- Criterion 3: `_follow_ups_mirror` for the pinned base, a ledger with two
  recorded layers, and doubles for `qualify.qualify`,
  `end_review.layer_cell`, `follow_up.write_follow_ups` and
  `spec_review.run_spec_writer`, all reached through `cli`.

**Measured on a prototype at `e8f5529e` with `SA-0302`'s revised
prototype applied.** It passed all five witnesses and the whole of
`tests/test_cli.py`, `tests/test_qualify.py` and `tests/test_follow_up.py`.
It passed the `lint`, `types`, `dead` and `structure` gates too. Each new
witness failed with `saffron/` reverted. Every wrong version above was
applied as an edit and failed its own criterion's witness, and so did each
declared mutant. A `write` that read its origin through `layer_fields`
failed the existing follow-ups test named above. Its diff measured 1770
changed tokens, 220 of them outside `tests/`.
