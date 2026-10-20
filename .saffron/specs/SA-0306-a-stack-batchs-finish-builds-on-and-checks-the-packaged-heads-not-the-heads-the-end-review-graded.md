---
id: SA-0306
title: "A stack batch's finish builds on and checks the packaged heads, not the heads the end review graded"
type: feature
priority: 2
depends_on: [SA-0303]
estimated_lines: 375
estimate_measured: true
touches:
  - saffron/finish.py
  - saffron/cli.py
  - saffron/report/stack.py
  - tests/test_finish.py
  - tests/test_cli.py
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
  - harness/**
  - records/**
  - hooks/**
  - images/**
  - saffron/record/**
  - saffron/view/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/agents/**
  - saffron/phases/**
  - saffron/repos/**
  - saffron/ledger.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/end_review.py
  - saffron/qualify.py
  - saffron/follow_up.py
  - saffron/regate.py
  - saffron/report/index.py
  - tests/test_scheduler.py
  - tests/test_end_review.py
  - tests/test_qualify.py
  - tests/test_follow_up.py
  - tests/test_batch.py
  - tests/test_session.py
  - tests/test_queued_specs.py
budget_usd: 58
max_attempts: 3
max_turns: 160
risk: standard
acceptance:
  - claim: >-
      `finish.commit_finish` takes a keyword `heads`, a mapping from task key
      to head, empty by default. When it names the top layer, the finishing
      commit is built on that head. When it names only lower layers, it is
      still built on the top layer's recorded `pushed_sha`. The witness drives
      a top layer whose branch moved past its `pushed_sha`, once named and
      once with only the two layers below it named.
    witness: tests/test_finish.py::test_a_finish_handed_graded_heads_commits_atop_the_top_layers_graded_head
    wrong_versions:
      - "`heads` is ignored, so the commit is still built on the top layer's `pushed_sha`."
      - The commit is built on the bottom layer's entry in `heads`.
      - "`heads` is looked up by spec id, so a mapping keyed by task key is never matched."
      - The commit is built on any entry in `heads`, so a lower layer's head is used.
  - claim: >-
      `finish.write_findings` takes the same `heads`. For a layer named
      there, each `qualifications` entry from an end-review lens or the
      join carries that head as its `head`. The witness drives the `spec`,
      `standards` and `join` lenses, as pooled, `follow_up` and `unanchored`
      entries. Each `qualifications` entry from a lens in `review.LENSES` keeps the layer's
      `pushed_sha`, and the witness drives all four of those lenses. A layer
      `heads` lacks keeps its `pushed_sha` on every entry, its critic
      entries included. A follow-up that added no layer keeps the head it
      names without `heads`. The witness names one generation-0 layer and
      leaves the bottom layer and the generation-1 layer out.
    witness: tests/test_finish.py::test_each_finding_names_the_head_the_end_review_graded_its_layer_at
    mutant:
      file: saffron/finish.py
      find: "                \"head\": head,"
      replace: "                \"head\": layer[\"pushed_sha\"],"
    wrong_versions:
      - "`heads` is ignored, so every entry names its `pushed_sha`."
      - A layer missing from `heads` gets `None` as its head.
      - Every entry of a named layer takes the graded head, in-cell entries included.
      - Only the `spec` and `standards` lenses take the graded head, so a join entry keeps the `pushed_sha`.
      - "`write_findings` never passes `heads` on to `_layer_findings`."
  - claim: >-
      `finish.publish_finish` takes the same `heads`. It hands `verify` the
      top layer's entry as its `base`, or the top layer's `pushed_sha` when
      `heads` lacks it. It reads each layer's remote head against that
      layer's entry, or against its `pushed_sha` when `heads` lacks it. So a
      branch graded where it now sits does not escalate. A branch that moved
      after it was graded escalates, and the line names the head it was
      graded at. The witness drives a three-layer stack four ways. Every
      layer is moved and named at its moved head, and the finish pushes. The
      same, then the middle branch moves again, and it escalates. Only the
      bottom is named at its moved head and the finish pushes, then the
      unnamed top moves and it escalates. Only the top is named at its moved
      head, and the unnamed bottom moves and escalates.
    witness: tests/test_finish.py::test_a_finish_handed_graded_heads_judges_and_checks_each_layer_at_its_graded_head
    mutant:
      file: saffron/finish.py
      find: head = package_phase.remote_sha(url, layer["branch"], cwd=mirror)
      replace: head = package_phase.remote_sha(url, top["branch"], cwd=mirror)
    wrong_versions:
      - "`verify` still gets the top layer's `pushed_sha` as its `base`."
      - "`verify` gets the bottom layer's entry as its `base`."
      - "The moved-branch check ignores `heads`, so every graded branch escalates."
      - The moved-branch check reads `heads` for the top layer alone.
      - A layer missing from `heads` is compared against `None`, so an unmoved branch escalates.
      - A lower layer missing from `heads` is skipped by the check, so its moved branch pushes.
      - The escalation names the layer's `pushed_sha` rather than the head it was graded at.
  - claim: >-
      `cli._stack_finish` takes a required keyword `heads` and reads it each
      time its callable runs. `finish.write_findings`,
      `finish.commit_finish` and `finish.publish_finish` each get it.
      `saffron batch --stack` wraps the end review it hands
      `run_stack_batch` in `cli._keeping_graded_heads(end_review, heads)`,
      a module-level function. The wrapper copies each `StackReview.fields`
      entry's `head` into the mapping it hands `_stack_finish`, and returns
      the review it got. A review whose `fields` is empty leaves the mapping
      empty. The witness drives one review with two graded layers and one
      with none, and checks all three calls each time.
    witness: tests/test_cli.py::test_a_stack_batchs_finish_reads_the_heads_its_end_review_graded
    wrong_versions:
      - "`_batch` hands `run_stack_batch` the unwrapped end review, so the finish gets an empty mapping."
      - "`_stack_finish` copies the mapping when it is built, before the end review fills it."
      - "`_batch` hands `_stack_finish` an empty mapping of its own."
      - "`write_findings` is not handed the mapping."
      - "`commit_finish` is not handed the mapping."
      - "`publish_finish` is not handed the mapping."
      - The wrapper returns the review's `fields` in place of the review.
  - claim: >-
      `report.stack.write_stack_view` takes a keyword `batch_id`. Named, it
      renders that batch's stack view, even while a newer batch has layers.
      An id with no `stack_layers` row writes nothing and leaves the page as
      it was, even while the newest batch has layers. The witness names an
      id no batch carries.
    witness: tests/test_stack_view.py::test_the_queue_page_carries_the_named_batchs_stack_view_over_the_newest
    wrong_versions:
      - "`batch_id` is ignored, so the newest batch is rendered."
      - A named batch with no layer falls back to the newest batch's view.
  - claim: >-
      Without `heads`, the finishing commit is still built on the top
      layer's recorded `pushed_sha`.
    witness: tests/test_finish.py::test_the_finishing_commit_writes_each_layers_and_unrun_texts_and_moves_no_spec
    preserves: true
  - claim: >-
      Without `heads`, `verify` still gets the top layer's `pushed_sha`, and
      a hand-pushed bottom, middle or top branch still escalates.
    witness: tests/test_finish.py::test_each_escalation_leaves_the_stack_unpushed
    preserves: true
  - claim: >-
      Without `heads`, each finding still names its layer's `pushed_sha`.
    witness: tests/test_finish.py::test_findings_json_holds_each_layers_findings_and_each_follow_up_that_added_no_layer
    preserves: true
  - claim: >-
      Without `batch_id`, `write_stack_view` still renders the newest batch,
      and writes nothing when that batch has no layer.
    witness: tests/test_stack_view.py::test_the_queue_page_carries_the_newest_batchs_stack_view_and_only_that
    preserves: true
  - claim: >-
      The end review `saffron batch --stack` hands `run_stack_batch` still
      returns what `end_review.run_end_review` returned, even when that is
      not a `StackReview`.
    witness: tests/test_cli.py::test_a_stack_batch_holds_a_quarter_of_its_budget_and_reads_its_stack_at_the_pinned_base
    preserves: true
---

## Context

Backlog item **b-8a0c9a**, under ADR 7 and `DESIGN.md` §5.7. A stack
batch's end review graded the heads PACKAGE pushed, before the loop's
review commits landed. `SA-0302` grades each layer at its branch head and
records what it graded in `StackReview.fields`. `SA-0303` has qualification
and the follow-up writer read those fields. The finish still reads the
packaged heads. This spec has it read the graded ones. `SA-0305` then
builds `saffron finish <batch id> --repo .` on what this spec adds.

Every line below was read in `saffron/` as it stands at `e8f5529e`.
`SA-0301`, `SA-0302` and `SA-0303` edit `saffron/cli.py` before this
spec runs, so find each function there by name. None of them edits
`saffron/finish.py` or `saffron/report/stack.py`.

**What `SA-0302` and `SA-0303` give this spec.** `StackReview.fields` maps
a task key to the `LayerFields` the end review graded that layer at. It
holds every layer either walk resolved, and it is empty by default.
`LayerFields` gains `diff_base`. A batch's own end review finds each
branch at its pushed head. So inside a batch each graded head equals the
packaged one (`SA-0302`, Problem 5).

**The finishing commit is built on the top layer's `pushed_sha`.**
`commit_finish` reads the batch's layers and raises when the top one has no `pushed_sha`
(`saffron/finish.py:164-169`). It cuts its worktree at that sha (`:183`).
Its docstring says so (`:156`), and so does the module docstring
(`:3-5`).

**The publish judges and checks against `pushed_sha`.** `publish_finish`
hands `verify` the top layer's `pushed_sha` as its `base` (`:374`). It then
reads each layer's remote head and escalates when it is not that layer's
`pushed_sha`, naming both (`:383-389`). Its docstring says so (`:364-366`).
A branch the loop's review commits moved therefore escalates, though the
end review graded it there.

**Each finding names `pushed_sha`.** `_layer_findings` sets `head` to the
layer's `pushed_sha` (`:259`). Every `qualifications` entry carries it
(`:270-282`), and so does a generation-1 layer's critic entry (`:283-284`,
`_left_by_critic` at `:230-250`). `write_findings` calls `_layer_findings`
once per layer (`:306-307`). A follow-up that added no layer names its own
row's `pushed_sha` (`:314-317`). A `qualifications` row holds the
end-review lenses (`END_LENSES`, `saffron/end_review.py:35-38`), the join,
and the in-cell lenses of `review.LENSES` (`saffron/phases/review.py:41-46`).
`SA-0303` qualifies an in-cell concern over the packaged range, citing the
packaged head. So only an end-review or join row was graded at the
graded head.

**No generation-1 layer is graded.** `run_stack_batch` calls `end_review`
before `follow_ups` (`saffron/batch.py:863-867`). So `StackReview.fields`
never holds a follow-up's layer, and a critic entry never meets a graded
head.

**The batch builds both callables from one resolve.** `_batch` builds
`_stack_end_review` and `_stack_finish` in the same `--stack` branch
(`saffron/cli.py:2116-2118`, `:2148-2154`). It hands them to
`run_stack_batch` as `end_review` and `finish` (`:2198`, `:2205`).
`run_stack_batch` calls `end_review` and later `finish` (`SA-0304`'s
context, `saffron/batch.py:852-909`). `_stack_finish` calls
`finish.write_findings`, `finish.commit_finish` and `finish.publish_finish`
inside its callable (`saffron/cli.py:958`, `:966-968`, `:989-999`). The
end review's callable is typed to return `object`
(`saffron/cli.py:823`). One existing test's fake `run_end_review` returns a
bare `object()` and asserts the batch hands it back unchanged
(`tests/test_cli.py:5258`, `:5280`, `:5359`).

**`_batch` already binds a local named `heads`.** It is the shared commit
cache of the cite and the review (`saffron/cli.py:2121`). It maps a pair of
strings to a sha, and it is not this mapping.

**The stack view reads the newest batch.** `write_stack_view` renders
`stack_view` of `ledger.latest_batch_id()` (`saffron/report/stack.py:264-272`).
Its docstring says "the newest batch" (`:265-270`). A finish that runs
after a later batch would render that later batch. `SA-0305` calls it
with the id of the batch it finishes. `_batch` calls it after
`run_stack_batch` returns (`saffron/cli.py:2210`), when its own batch is
the newest.

## Problem

1. **`finish.py` reads the graded heads.** `commit_finish`,
   `publish_finish` and `write_findings` each take a keyword
   `heads: Mapping[str, str]`, keyed by task key, empty by default.
   `write_findings` passes it to `_layer_findings`. A layer found there
   uses that head in place of its `pushed_sha`, and a layer missing from
   it keeps its `pushed_sha`. That changes four reads. The first is the
   commit the finish is built on, and the second is `verify`'s `base`.
   The third is the head each layer's remote branch is checked against.
   The fourth is the head of a layer's end-review and join entries. An entry whose lens is in `review.LENSES` and every
   critic entry keep the layer's `pushed_sha`. The escalation
   line names the head the branch was checked against. So only a branch
   that moved after it was graded escalates.
2. **`_stack_finish` takes the mapping.** It is a required keyword
   `heads`. Its callable reads it on each call and never copies it at
   build time. It hands it to all three `finish` calls.
3. **The batch fills it from its end review.** Add
   `_keeping_graded_heads(end_review, heads)` at module level in
   `saffron/cli.py`. `SA-0305` calls it by that name. It returns a
   callable that calls `end_review`, copies `{key: fields.head}` for each
   `StackReview.fields` entry into `heads`, and returns the result
   unchanged. It copies only from a result `isinstance` finds to be a
   `StackReview`, and nothing from any other. `_batch` builds one
   empty dict, wraps `_stack_end_review`'s callable with it, and hands the
   same dict to `_stack_finish`. `SA-0305` builds `_stack_finish` the same
   way.
4. **`write_stack_view` takes `batch_id`.** A keyword, `None` by default,
   which falls back to `ledger.latest_batch_id()`. `_batch` keeps calling
   it without one.
5. **Four docstrings go false, so edit them.** `finish.py`'s module
   docstring (`:3-5`), `commit_finish`'s (`:156`), `publish_finish`'s
   (`:364-366`) and `write_stack_view`'s (`saffron/report/stack.py:265-270`).

## Out of scope

- **`saffron finish` itself.** `SA-0305` builds it, with its own
  `_stack_finish` and its own call to `write_stack_view`.
- **How the end review grades.** `SA-0302` owns `StackReview.fields`.
- **A follow-up that added no layer.** `write_findings` names its own
  row's `pushed_sha` (`saffron/finish.py:316`). The end review grades no
  follow-up, so `heads` holds no entry for one.
- **The check of each pull request's base branch, and `link_stack`.**
  Both read branches, not heads (`saffron/finish.py:391-424`, `:46-86`).
- **The finishing row.** `record_stack_finish` records the finishing
  commit's own sha (`saffron/finish.py:434`, `:445`), which does not move.
- **ADR 7.** Its paragraph "The finishing layer's parent is the top
  layer's recorded head" and its dated amendment
  (`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:136-145`)
  are the operator's. `docs/adr/**` is `protected`, and the amendment
  lands by hand in this spec's pull request.

## Notes for the agent

**The fixtures are unit arrangements.** Production never grades `TE-20` or
puts a `join` row on `TE-7`. Only generation 0 is graded, and join rows sit
on the top layer. The witnesses exercise each function on
its own.

**Which criteria are edits.** Criteria 2 and 3 each mutate a line the
change keeps. Keep the `head` key of the dict `_layer_findings` builds
per `qualifications` row bound to a per-row local named `head`. Pass
`layer["pushed_sha"]` to `_left_by_critic` explicitly, so that local never
reaches it. Leave the
remote read in `publish_finish` as it is. Criterion 1 replaces the one
line that picks the commit to build on, so no line it keeps pins the
claim. Criteria 4 and 5 are new wiring and a new keyword. Those three declare no mutant, and
`witness` reports `skip` for them. Criteria 6 to 10 name tests that exist
now. The wrong versions under each criterion are what its witness must
kill. Do not run them yourself.

**Where the wrapper goes on.** Wrap the end review only inside the
readiness guard, and only where `_batch` builds the in-batch end review.
Under `--defer-end-review` (`SA-0301`) `finish` is `None`, so nothing is
wrapped.

**Name the new dict apart from `heads`.** `_batch`'s `heads` is the commit
cache, typed by a pair of strings (`saffron/cli.py:2121`). A second binding
of that name fails the `types` gate or shadows the cache.

**Existing tests that change.** Two fakes in `tests/test_cli.py` take a
fixed keyword set and would raise on `heads`. They are
`_recording_write_findings` in
`test_a_stack_batch_writes_its_findings_from_the_pooled_list_its_writer_filled`
and `_fake_publish_finish` in
`test_a_stack_batch_publishes_its_finish_through_the_finishing_suite`.
Let each take `heads`, and keep every assertion.

**Import new names inside each test.** `tests/test_finish.py` imports
`saffron.finish` inside each test body. Keep that, so each new test fails
in its body with the source reverted, rather than at collection.

**Fixtures, as the prototype built them.**

- Criterion 1: the `stack` fixture. Batch B's top layer is `TE-20`, and
  `stack.heads["TE-20-plus"]` is a commit past its `pushed_sha` on its
  branch, already in the mirror. Read each task key from
  `ledger.stack_layers(stack.batch_b)`. Commit once with `TE-20` named at
  that head. Then commit again into a fresh workdir with `TE-10` and
  `TE-7` named at it, and `TE-20` left out.
- Criterion 2: the `stack` fixture, with `_qual` rows on `TE-10`, `TE-7`
  and `TE-20`. Give `TE-7` a pooled row, a `qualified` row no group
  matches, and an `unanchored` row with a reason. Give `TE-20` one
  qualification and one critic finding through `record_findings`, and
  `TE-22` one critic finding. Give `TE-7` one `qualified` row under each
  lens in `review.LENSES` too, importing that inside the test. Call
  `write_findings` without `heads`, then with `TE-7` alone named. Assert
  the second result equals the first, with the head replaced only on
  `TE-7`'s entries whose lens is not in `review.LENSES`. Assert the set of
  `(spec_id, lens, outcome, head)` too, so a missing entry shows. Each
  in-cell entry of `TE-7` keeps `stack.heads["TE-7"]`. The kept
  outcomes `note` and `unverified` take the branch `unanchored` takes
  (`saffron/finish.py:268-269`), and no witness drives them apart.
- Criterion 3: `_stack(root, 3)` per case. Push a new commit past a branch
  in the bare remote, from a clone, as `_hand_push` does. Give each push its
  own file, since the second push to one branch needs a change. Then fetch
  that branch into the mirror, so `_finishing_commit` can build on it.
  Answer each pull request's base branch with `_FakeGh(_bases(s.layers))`,
  and record each `verify` call. Assert each escalation line in full.
- Criterion 4: the batch rigs `_readiness_passes` and
  `_fake_batch_resolution`, with `real_remote` patched, as
  `test_a_stack_batch_commits_its_finish_and_survives_a_raise` uses them.
  Replace `cli._stack_end_review` with a factory whose callable returns a
  `StackReview` you built, with two `fields` entries. Build each
  `LayerFields` with every field, `diff_base` included. The faked
  `run_stack_batch` calls the handed `end_review`, records its return,
  then calls the handed `finish`. Replace the three `finish` functions
  with fakes that each record the `heads` they got and require it. Assert
  the recorded return is the review you built. Run `main` again over a
  `StackReview` with no `fields`.
- Criterion 5: `_build_batches`, whose batch B is newer than batch A and
  both have layers. Render batch A by id, and assert the page holds
  `render_stack(stack_view(ledger, batch_a, specs))` and no `TE-9`. Then
  name an id no batch carries. Read the page through its own path, since
  the call returns `Path | None` and `types` reads each use.

**Measured on a prototype at `45305c7a`.** It stubbed
`StackReview.fields` and `LayerFields.diff_base` as `SA-0302` specifies. It passed all five new witnesses and all five
`preserves` witnesses. The full `tests/test_finish.py`, `tests/test_cli.py`
and `tests/test_stack_view.py` passed, and so did the `lint`, `types`,
`dead` and `structure` gates and the `prose` hook. Each new witness failed
with `saffron/` reverted. Every wrong version above was applied as an edit
and failed its own criterion's witness, and so did each declared mutant.
Its diff measured 1499 changed tokens, 312 of them outside `tests/`.

**Docstrings at the cap.** `_stack_finish`'s and `publish_finish`'s
docstrings are at ten lines now, and the `prose` gate caps one at ten.
Shorten what is there as you add to them. New comments and docstrings take
no em dash, semicolon, contraction, perfect tense or sentence over 25
words.
