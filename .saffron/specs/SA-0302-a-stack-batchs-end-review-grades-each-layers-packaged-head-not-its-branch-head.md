---
id: SA-0302
title: "A stack batch's end review grades each layer's packaged head, not the head its branch carries now"
type: feature
priority: 2
depends_on: [SA-0301]
estimated_lines: 406
estimate_measured: true
touches:
  - saffron/end_review.py
  - saffron/cli.py
  - tests/test_end_review.py
  - tests/test_cli.py
  - tests/test_session.py
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
  - saffron/qualify.py
  - saffron/follow_up.py
  - saffron/finish.py
  - saffron/regate.py
  - tests/test_scheduler.py
  - tests/test_qualify.py
  - tests/test_follow_up.py
  - tests/test_batch.py
budget_usd: 32
max_attempts: 3
max_turns: 160
risk: standard
acceptance:
  - claim: >-
      Given the resolver `end_review.branch_heads` builds, `run_end_review`
      opens each layer's cell, and the join's, at the head the layer's
      branch carries when the end review runs. Each lens's diff and stated
      range start at the base the rule picks, for each of its three arms.
      A layer with no predecessor starts at its pushed head's parent. A
      restacked layer starts at its predecessor's current head, which
      outranks the recorded one. A layer that was not restacked starts at
      its predecessor's recorded head. The join reads from the bottom
      layer's base to the top layer's current head. Each branch is fetched
      once per end review. `StackReview.fields` holds each layer's fields
      as its lenses graded them. An unmoved stack still reads `head^..head`
      per layer. The witness drives all three arms over moved branches, and
      an unmoved stack.
    witness: tests/test_end_review.py::test_an_end_review_grades_each_layer_at_its_branch_head_after_package
    mutant:
      file: saffron/end_review.py
      find: "with open_cell(top_fields) as container:"
      replace: "with open_cell(bottom_fields) as container:"
    wrong_versions:
      - The resolver fetches each branch but keeps the pushed head as the head it grades.
      - A restacked layer starts at its predecessor's recorded head, so the predecessor's review commits join its diff.
      - A layer with no predecessor starts at its run's `base_sha` rather than its pushed head's parent.
      - The layer diff stays `head^..head` of the current head, so a layer with a review commit loses its own commit.
      - The join's range still starts at the bottom layer's pushed head's parent.
      - The join's stated base is not the base its diff starts from.
      - The stated range in a layer's prompt keeps the recorded base while the diff starts at the chosen one.
      - Each lens fetches its branch again, so the join and the layers can grade two heads.
      - "`StackReview.fields` stays empty."
  - claim: >-
      A layer the resolver cannot place gets `error` on both its lenses at
      cost 0, and the walk goes on to the layer below. The set of outcomes
      is three. Its own branch is gone at origin. Its predecessor's branch is
      gone at origin. Its current head contains none of its candidate bases.
      Each error names the branch it could not read or place. The third
      also names the current head and every candidate. The join is filed `error`
      at cost 0 when any layer fails, a middle layer included. The witness
      drives each outcome, on a layer with a predecessor and on one without.
    witness: tests/test_end_review.py::test_a_layer_whose_branch_head_cannot_be_resolved_errors_at_no_cost
    mutant:
      file: saffron/end_review.py
      find: top_task_id, lens="join", status="error", cost_usd=0.0, error=error
      replace: top_task_id, lens="join", status="reviewed", cost_usd=0.0, error=error
    wrong_versions:
      - A gone layer branch falls back to the layer's pushed head and is reviewed.
      - A gone predecessor branch falls back to the predecessor's recorded head and the layer is reviewed.
      - A head that contains none of its bases is graded from the recorded base anyway.
      - A resolution failure stops the walk, so the layers below it get no review.
      - The join resolves only its top and bottom layers, so a middle layer's failure leaves it `reviewed`.
      - The error names the branch but not the current head or the candidates.
  - claim: >-
      Read through `layer_fields`, whose diff base is the pushed head's
      parent, each layer's lenses still get that layer's own commit,
      `head^..head`, as at base.
    witness: tests/test_end_review.py::test_each_layer_is_read_from_its_own_commit_in_its_own_cell
    preserves: true
    wrong_versions:
      - "`layer_fields` sets the diff base to its recorded `base`, so the bottom layer's diff takes in the run's `base_sha` commits."
      - "`layer_fields` sets the diff base to the pushed head itself, so every diff is empty."
  - claim: >-
      `saffron batch --stack` hands `run_end_review` the resolver
      `branch_heads` builds on the pinned mirror and the pinned url. Asked
      for a layer, it fetches that layer's branch there and grades the
      fetched head.
    witness: tests/test_cli.py::test_a_stack_batchs_end_review_reads_each_layer_at_its_fetched_branch_head
    wrong_versions:
      - "`_stack_end_review` passes `layer_fields` as the resolver."
      - The resolver is built on the operator's repo rather than the pinned mirror.
      - The resolver is built on a url other than the pinned url.
---

## Context

Backlog item **b-8a0c9a**, under `DESIGN.md` §5.7 and ADR 7. It is the
second of five specs that item splits into. `SA-0301` lets a stack batch
end without its end review, so the review can run after the loop's review
commits land. This spec makes the end review read those commits.
`SA-0303` then has `qualify` and the follow-up writer read the fields this
spec records. Every line below was read at `e8f5529e`. `SA-0301` edits
`saffron/cli.py` first, so find each function by name.

**The end review reads the head PACKAGE pushed.** `layer_fields` takes a
layer's `head` from its task's `pushed_sha` (`saffron/end_review.py:101-133`,
`:131`). Its `base` is the predecessor's head as the layer's row recorded
it, or the run's `base_sha` for a layer with none (`:116-124`).
`record_stack_layer` reads the predecessor's `pushed_sha` once, when the
layer is recorded (`saffron/ledger.py:1726-1754`). `_review_one_layer`
reads those fields, and its diff is `head^..head`
(`saffron/end_review.py:249-283`). `review_joins` reads every layer the
same way. It diffs from the bottom layer's pushed head's parent to the top
layer's pushed head (`:411-460`). `layer_cell`
seeds each critic cell at `fields.head` (`:601`, `:620`).

**Review commits land after PACKAGE.** The item records five runs where
most end-review findings were already fixed on the branches. `DESIGN.md`
§5.7 already says a parent's head is fetched, never remembered.

**A branch is fetched fresh in one place.** `fetch_parent_branch` fetches
a branch into the mirror and returns its head
(`saffron/phases/package.py:167-198`). It raises `ParentGone` when the
fetch fails, or when the head is out of the mirror's reach (`:183-198`).
Its message calls the branch a parent (`:187`, `:191`).
`saffron/regate.py:76-83` wraps it to name the branch's role instead.
`_stack_head` already uses it for a spec session's seed
(`saffron/cli.py:683-695`).

**Both catches already exist.** `_review_one_layer` turns any raise into
an `error` for each lens at cost 0, and the next layer is still tried
(`saffron/end_review.py:280-305`). `review_joins` files any raise as an
`error` join at cost 0 (`:448-483`).

**One caller.** `_stack_end_review` calls `run_end_review`
(`saffron/cli.py:821-869`, `:855`). `StackReview` holds the join and the
layers, and nothing else (`saffron/end_review.py:496-502`).

## Problem

1. **`LayerFields` gains the diff base.** A new field holds the commit a
   layer's diff starts from. `layer_fields` sets it to the pushed head's
   parent, which is today's range. The three spec-session constructions
   in `saffron/cli.py` (`:1092`, `:1205`, `:1331`) set it to their own
   head. So do the test constructions in `tests/test_end_review.py`,
   `tests/test_cli.py` and `tests/test_session.py:8943`.
2. **A resolver reads each layer at its branch head.**
   `end_review.branch_heads(mirror, url)` returns a callable with
   `layer_fields`' own signature. It reads the layer's recorded fields.
   It fetches the layer's branch through
   `package_phase.fetch_parent_branch`, reached through its module. A layer
   with a predecessor also fetches the predecessor's branch, read from
   that task's row. The base is the first candidate the current head
   contains, by `git merge-base --is-ancestor` in the mirror.
   - With a predecessor: its current head, then its recorded head.
   - With none: the pushed head's parent.

   It returns the recorded fields with `head` set to the current head, and
   both `base` and the diff base set to the chosen base. The prompt's
   stated range is then the diff's own range. It caches each fetched
   head by branch, so one resolver fetches a branch once. A gone branch
   raises naming the branch and its role, layer or predecessor. No
   candidate contained raises `ValueError` naming the layer's branch, its
   current head and every candidate.
3. **The walk takes the resolver.** `run_end_review`, `review_stack` and
   `review_joins` each take a required keyword `resolve`, and
   `_review_one_layer` too. Each reads a layer's fields through it, never
   through `layer_fields` directly. A layer's diff and the join's range
   start at the diff base. The join's stated base is the bottom layer's
   diff base. A failed resolution raises into the two existing catches.
4. **`StackReview` carries the fields it graded.** A `fields` mapping, by
   task key, defaults empty. `run_end_review` wraps `resolve` so that
   every resolution it makes lands there. `SA-0303` reads it.
5. **The batch passes the resolver.** `_stack_end_review` passes
   `branch_heads(pinned.mirror, pinned.url)`, built inside its `run`, so
   each end review starts with an empty cache. Inside a batch each branch
   still sits at its pushed head, so the diffs a batch reads do not change.

## Out of scope

- `qualify`, `write_follow_ups` and `_stack_follow_ups` still call
  `layer_fields`. `SA-0303` moves them to `StackReview.fields`. Inside a
  batch the two agree, since each branch still sits at its pushed head.
- Ending a batch without its end review, and running it later. `SA-0301`
  and `SA-0305` build those.
- A bottom layer rebased onto a newer default branch. Its head still
  contains the commit PACKAGE built it on, so it resolves. Its range then
  takes in the default branch's newer commits too.
- A layer rebased onto a head its predecessor's branch no longer carries.
  It contains neither candidate and ends `error`.
- The finishing layer's parent. ADR 7 keeps it at the top layer's
  recorded head.
- `CONTEXT.md`'s **End-review lens** entry says each lens runs at the
  layer's pushed head. The operator edits it by hand.

## Notes for the agent

**Which criteria are edits.** Criterion 1 mutates the join's cell, a line
the change keeps. Criterion 2 mutates the status the join's catch files.
Leave both lines as they are. Criterion 3 names a test that exists now.
Only the shared kwargs helper changes under it. Criterion 4 judges only
the new wiring, so it declares no mutant, and `witness` reports `skip`.
The wrong versions under each criterion are what its witness must kill.
Do not run them yourself.

**Import new names inside each test.** `tests/test_end_review.py`'s own
docstring says why (`:1-6`). A module-scope import of `branch_heads`
turns the reverted run into a collection error.

**Existing tests that change.** `_end_review_kwargs` passes
`end_review.layer_fields` as `resolve`. So every existing `review_stack`
and `review_joins` test keeps its assertions. The `run_end_review` test
compares every keyword with the ones it passed
(`tests/test_end_review.py:1314-1375`). The wrapped `resolve` breaks that
equality. Compare the other keywords, and check the wrapped one delegates.

**Fixtures, as the prototype built them.**

- Criteria 1 and 2: a real origin repository, with one branch per layer.
  Clone it with `git clone --mirror` once every layer is pushed. That
  clone is PACKAGE's mirror. Then move branches in the origin. Pass the
  origin's path as the url, so `fetch_parent_branch` runs for real.
  Record each layer with `set_task_package` and `record_stack_layer`, as
  `_stack_ledger` does (`tests/test_end_review.py:574-634`).
- Criterion 1: cut the bottom layers from a commit after the run's
  `base_sha`, so a bottom base read from the run shows in the diff. Give
  each review commit its own file, so the layer's own commit stays in its
  diff. Count fetches with a spy that wraps the real
  `fetch_parent_branch`. Assert each lens's diff equals the mirror's
  `DIFF_FLAGS` diff of its expected range.
- Criterion 2: point a branch at an orphan commit for "contains none".
  Delete a bottom layer's branch for the predecessor case above it. Put
  the unplaceable layer in the middle of a three-layer stack once.
- Criterion 4: a plain repository as the mirror, with
  `.saffron/policy.yaml` and `CLAUDE.md` at base. Replace
  `package.fetch_parent_branch` and `cli.end_review.run_end_review`. Call
  the captured `resolve` on a one-layer ledger.

**Measured on a prototype at `e8f5529e`.** It passed all four witnesses,
and the `lint`, `types` and `dead` gates. Each new witness failed with
`saffron/end_review.py` and `saffron/cli.py` reverted. Every wrong version
above was applied as an edit and failed its own criterion's witness, and
so did each declared mutant. Its diff measured 1622 changed tokens, 354
of them outside `tests/`.
