---
id: SA-0265
title: "A stack batch has no way to seed, record, exempt or finish a stack on an earlier batch's open pull request"
type: feature
priority: 2
depends_on: [SA-0261, SA-0264]
estimated_lines: 401
estimate_measured: true
touches:
  - saffron/scheduler.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/finish.py
  - tests/test_cli.py
  - tests/test_batch.py
  - tests/test_finish.py
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
  - saffron/ledger.py
  - saffron/task.py
  - saffron/end_review.py
  - saffron/follow_up.py
  - saffron/reconcile.py
  - saffron/phases/**
  - tests/test_scheduler.py
budget_usd: 48
max_attempts: 3
max_turns: 200
risk: standard
acceptance:
  - claim: >-
      Given no predecessor, `_stack_runner`, `_stack_review` and
      `_stack_revise` each fetch the branch of the candidate's stack base and
      seed there. The runner's `Handoff` names that branch and its fetched
      head. Each spec session's cell starts at that head. A predecessor still
      outranks the stack base, and a spec with neither seeds at `base_sha` as
      before. The witness drives all three callables in all three cases.
    witness: tests/test_cli.py::test_a_stack_batchs_spec_with_no_predecessor_is_seeded_on_the_pull_request_its_order_stacks_on
    wrong_versions:
      - The runner ignores the stack base and hands an empty `Handoff`.
      - The spec review seeds at `base_sha` despite the stack base.
      - The spec writer seeds at `base_sha` despite the stack base.
      - The stack base outranks a predecessor, so a later layer is cut from it.
  - claim: >-
      `run_stack_batch` records the stack base's task as the first layer's
      predecessor, at that task's pushed sha. Every later layer's predecessor
      stays the layer below it. `end_review.layer_fields` then starts the
      first layer's range at the stack base's pushed sha, not at the run's
      `base_sha`.
    witness: tests/test_batch.py::test_a_stacks_first_layer_records_the_earlier_pull_request_it_stacks_on
    mutant:
      file: saffron/ledger.py
      find: predecessor_head = pred_row["pushed_sha"]
      replace: predecessor_head = None
    wrong_versions:
      - The first layer records no predecessor, so its range starts at `base_sha`.
      - Every layer records the stack base as its predecessor.
  - claim: >-
      Gate 0's open pull request check, as `run_stack_batch` runs it, exempts
      the stack base's branch for a revised spec of the order and for a
      follow-up. Another open pull request still refuses each. The witness
      drives a revised spec and a follow-up that overlap each pull request.
    witness: tests/test_batch.py::test_a_follow_up_and_a_revised_spec_on_an_earlier_pull_request_are_not_refused_on_it
    mutant:
      file: saffron/scheduler.py
      find: "if branch == own_branch or branch in exempt_branches:"
      replace: "if branch == own_branch:"
    wrong_versions:
      - The stack base's branch is exempt for neither.
      - A revised spec of the order is refused on the stack base's pull request.
      - A follow-up is refused on the stack base's pull request.
  - claim: >-
      Each time a spec of the order is offered with no predecessor,
      `run_stack_batch` asks `stack_base_alive` about its stack base before
      the mint. When the branch is gone, every remaining spec on that stack
      base is refused. Each reason names the stack base and its branch, and
      the remedy, to run the next batch, which reconciles it first. Nothing
      more is minted, reviewed or run, no abort is counted, and the night
      drains. Once a layer exists, nothing asks. An order with no stack base
      never asks. The witness drives four arrangements. The branch is gone
      before the first spec, or gone after a first spec ends `EXHAUSTED`. It
      stays alive through every layer. The fourth order has no stack base.
    witness: tests/test_batch.py::test_a_stack_whose_base_branch_is_gone_refuses_its_order_without_an_abort
    mutant:
      file: saffron/batch.py
      find: "if isinstance(outcome, Refused):"
      replace: "if False:"
    wrong_versions:
      - The stack base is never asked about.
      - Only the spec at hand is refused, and the next one asks again.
      - The stack base is asked before every spec, a predecessor or not.
      - The stack base is asked once per batch, before `_drive`.
      - The stack base is asked only before the order's first spec.
      - An order with no stack base still calls `stack_base_alive`.
      - A gone stack base raises instead of returning a refusal.
      - The reason names no stack base.
      - The reason names no remedy.
  - claim: >-
      `saffron batch --stack` hands `run_stack_batch` the `stack_base_alive`
      that `cli._stack_base_alive` builds on the pinned base. That callable
      reads the stack base's branch on the remote with `remote_sha`. A
      present branch is true and a missing ref is false. An unreachable
      remote raises `PackageError`, which `_drive` counts as an abort. The
      witness drives the wiring, and a present branch, a missing ref and an
      unreachable remote on real git remotes.
    witness: tests/test_cli.py::test_a_stack_batch_reads_its_stack_base_as_gone_only_when_its_ref_is_missing
    wrong_versions:
      - "`_batch` passes no `stack_base_alive`."
      - A missing ref reads as alive.
      - An unreachable remote reads as gone.
  - claim: >-
      When a stack's first layer stacks on a stack base, `publish_finish`
      expects that layer's pull request to target the stack base's branch.
      It pushes when the pull request does, and escalates naming that branch
      when it targets the default branch. `link_stack` then runs no `gh` and
      returns one line saying nothing is linked. The witness drives both
      targets and the link.
    witness: tests/test_finish.py::test_a_stack_on_an_earlier_pull_request_is_finished_against_its_branch_and_never_linked
    mutant:
      file: saffron/finish.py
      find: base = view.stdout.strip() if view.returncode == 0 else None
      replace: base = None
    wrong_versions:
      - The first layer's pull request is still expected to target the default branch.
      - "`link_stack` links the stack anyway, with the default branch as `--base`."
---

## Context

Backlog item **b-e0e1cf**, under `DESIGN.md` §4.2 and §4.2.1, and ADR 7.
This spec builds everything that reads a stack base. `SA-0267` then makes
`build_queue` choose one. Until it lands, nothing in `saffron/` sets a
stack base, so this spec changes no live batch. Every line below was read at
`0a5e3e5c`. `SA-0245`, `SA-0258`, `SA-0253`, `SA-0254` and `SA-0264` edit
`saffron/cli.py` before this spec runs. `SA-0261` edits
`saffron/batch.py`. Line numbers in both can move, so find each function
by name.

**A candidate carries nothing about its stack.** A `Candidate` holds a
path, a spec, a `spec_sha` and a `task_id` (`saffron/scheduler.py:131-148`).
`saffron/task.py:78` imports from `saffron/scheduler.py`.

**A stack's first layer starts at the default branch.** Its predecessor is
`None` until a layer exists (`saffron/batch.py:462`). `run_stack_batch`
hands that to the runner, the review and the revise (`:568`, `:696`,
`:738`). Given `None`, `_stack_runner` hands `run_task` an empty `Handoff`
(`saffron/cli.py:610-611`). `_stack_review` and `_stack_revise` each seed
their cell at the pinned `base_sha` (`saffron/cli.py:925-926`,
`:1011-1012`).

**The first layer records no predecessor.** `record_layer` passes
`predecessor_task_id`, which starts `None` (`saffron/batch.py:463`,
`:497-503`). `record_stack_layer` bakes in the predecessor's record key
and `pushed_sha` (`saffron/ledger.py:1607-1615`). `layer_fields` gives a
layer with no predecessor its run's `base_sha` as `base`, and any other
layer its `predecessor_head` (`saffron/end_review.py:116-124`). Each
end-review prompt states the range as `{base}..{head}`
(`saffron/agents/prompts/end-review-spec.md:69`,
`saffron/agents/prompts/end-review-standards.md:65`,
`saffron/agents/prompts/end-review-join.md:48`).

**Gate 0 inside the batch exempts only this batch's layers.**
`layer_branches` starts empty (`saffron/batch.py:482`). A follow-up meets
`open_pr_refusal` against it (`saffron/batch.py:550-556`), and so does a
revised spec of the order (`saffron/batch.py:650-655`).

**A raise is an abort, and a refusal is not.** A raise from the review is
recorded `GATE_ERROR`, marked a miss and raised again
(`saffron/batch.py:569-581`). `_drive` counts every raise toward the
breaker (`saffron/batch.py:268-286`). A returned `Refused` leaves the count
where it was (`saffron/batch.py:291-294`). `fetch_parent_branch` raises
`ParentGone` for a branch the origin no longer has
(`saffron/phases/package.py:81`, `:173`).

**`remote_sha` tells a missing ref from an unreachable remote.** It runs
`git ls-remote <url> refs/heads/<branch>`. It returns `""` when the remote
has no such ref, and raises `PackageError` when the call fails
(`saffron/phases/package.py:367-376`). Measured on the host, git 2.54.0
(Apple Git-157), 2026-10-10. A missing ref exits 0 with no output, or 2
under `--exit-code`. An unreachable remote, a path that does not exist,
exits 128 either way. The check runs host-side, so the cell's git does
not enter. A batch's scan reconciles before it reads the queue
(`saffron/cli.py:1510-1512`).

**The finish expects the first layer on the default branch.**
`publish_finish` reads each layer's pull request base back. It wants the
predecessor's branch when the predecessor is a layer of this batch, and
the default branch otherwise (`saffron/finish.py:383-397`). A
`stack_layers` row carries the predecessor's key and head, not its branch
(`saffron/ledger.py:1637-1644`). `link_stack` passes every layer's URL to
`gh stack link --base <default>` (`saffron/finish.py:64-67`). Run 4
read that a list without the pull request below would retarget the bottom
one onto `main`, and linked by hand instead
(`docs/evidence/2026-09-16-spec-loop-skill-feedback-run-4.md:57-61`).
`gh stack link --help` says `--base` names the bottom's base branch, and
defaults it to the default branch (gh-stack, read on the host 2026-10-10).

## Problem

The operator chose to stack on the earlier pull request. A stack batch
takes a parent that is an earlier batch's open pull request. The stack's
first layer is seeded from that branch, and its pull requests are based on
it. This spec builds the half that reads the stack base.

1. **The type.** A frozen `StackBase` in `saffron/scheduler.py` holds the
   parent's spec id, its task and its branch. `Candidate` gains a
   `stack_base` field, `None` by default. Nothing here sets it.
2. **Seeding.** With no predecessor, the runner, the spec review and the
   spec writer fetch the stack base's branch fresh and seed there.
3. **The layers.** The first layer's predecessor is the stack base's task.
   Its branch joins the exempt set the batch's own gate 0 checks use.
4. **A gone stack base.** `run_stack_batch` takes a `stack_base_alive`
   callable. Each time a spec is offered with no predecessor, it asks
   before the mint. A gone stack base refuses every remaining spec on it.
   `_batch` passes one that reads the branch with `remote_sha`.
5. **The finish.** The first layer's pull request must target the stack
   base's branch. `link_stack` links nothing for such a stack and says so.

**Decision: the end review and the finish leave the earlier pull
request's commits alone.** They are not graded and not finished.

- The end review reads each layer's own commit, `head^..head`
  (`saffron/end_review.py:249-254`). The join reads from the bottom
  layer's parent, `bottom^..top` (`saffron/end_review.py:450-459`).
  Neither range reaches below this batch's first layer. Criterion 2 makes
  the first layer's stated `base` the earlier head too. Those commits
  already passed their own in-cell lenses, and their own end review when
  a stack batch made them.
- The finishing commit writes this batch's layers' and unrun follow-ups'
  spec texts alone (`saffron/finish.py:139-175`). An earlier stack
  batch's finish wrote its own. `publish_finish` checks this batch's
  layers' heads and pull request bases. The first layer's pull request
  base becomes the earlier branch.
- `link_stack` links nothing. A list without the earlier pull request
  would retarget the first layer onto the default branch, as run 4 read.
  Linking onto the earlier branch with `--base` was never tried. Each
  pull request already targets the branch below it, so the stack stays
  reviewable, and the operator links it by hand.

## Out of scope

- Choosing the stack base and refusing what cannot stack. `SA-0267`
  builds both.
- Lower layers of the earlier stack. Only the stack base's own branch
  joins the exempt set. A follow-up or a revised spec overlapping a layer
  below it is still refused, though the stack base's branch holds that
  code.
- A stack base deleted between `stack_base_alive` and the seeding fetch.
  That fetch raises `ParentGone` as it does today, and the spec is missed.
- A stack base merged or closed with its branch kept.
  `stack_base_alive` finds the branch, so the batch stacks on it. The
  next night's reconcile records the merge or the close, and the scan
  reads it there.
- Checking the stack base branch's remote head at the finish. A hand push to
  the earlier pull request mid-batch leaves this stack on a stale head.
  ADR 7's principle 21 residual says the same of a layer.
- The stack view. Its first layer's predecessor still shows the
  placeholder (`saffron/report/stack.py:115-118`, `:258-261`).
- A plain batch, and `saffron queue --stack`'s output.
- `DESIGN.md`, `CONTEXT.md` and ADR 7. The operator edits them by hand.

## Notes for the agent

**Each mutant sits on a line the change keeps.** Every criterion edits
existing code. Criterion 2 mutates the head the ledger bakes in.
Criterion 3 mutates `open_pr_refusal`'s exemption. Criterion 4 mutates
the line that keeps a refusal off the breaker. Criterion 6 mutates the
pull request base `publish_finish` reads back. Leave those lines unedited. Criteria 1
and 5 judge only code this change writes, so they declare no mutant, and
`witness` will report `skip` for them. The wrong versions under each
criterion are what its witness must kill. Do not run them yourself.

**Import new names inside each test.** A module-scope import of
`StackBase` turns the reverted run into a collection error.

**`SA-0253` edits the same two functions.** Each of `_stack_review` and
`_stack_revise` builds a `partial(implement.run_agent, ...)`. `SA-0253`
binds an `emit` into it, so each session logs to `<spec id>.spec-review`
or `<spec id>.spec-write`. Criterion 1 edits only the block that picks
the seed, where `layer is None` chooses `base_sha`. The two edits share
no line, and the export, the prompt and the cell are unchanged by both.

**Shape, as the prototype measured it.**

- `saffron/cli.py`: one helper returns the branch a spec is seeded on.
  It is the predecessor's branch, else the stack base's, else `None`.
  All three callables use it. `_stack_base_alive(pinned)` compares
  `remote_sha` with `""` and lets its `PackageError` through. `_batch`
  builds it beside `_stack_finish`, only once readiness pins `base_sha`, and
  passes it as `stack_base_alive`.
- `saffron/batch.py`: read the stack base from the order once, before
  the loop. It seeds `predecessor_task_id` and `layer_branches`. The
  `stack_base_alive` check opens `wrapped`, before the mint. Name its
  local something other than `base`, which the outer function already
  binds.
- `saffron/finish.py`: for a layer whose predecessor is not a layer of
  this batch, read that task's branch by its record key. `end_review.py`
  reads `ledger._db` the same way (`saffron/end_review.py:117`).
  `saffron/ledger.py` is forbidden, since `.saffron/policy.yaml` elevates
  any diff that touches it.

**Fixtures.**

- Criterion 1: `_spec_session_rig` in `tests/test_cli.py`. Its fake
  fetch returns `d` times 40 for any branch but `saffron/SY-8`. Replace
  `spec_review.run_spec_review`, `spec_review.run_spec_writer` and
  `cli.run_task`. Build the stack base's candidate with
  `dataclasses.replace`.
- Criteria 2 to 4: `ScriptedRunner` and `StackDoubles` in
  `tests/test_batch.py`. Record the stack base's task with
  `set_task_package` at `READY_FOR_REVIEW`. For criterion 4, assert no
  line holds ` raised `, which `_drive` prints for every raise it counts.
  Its `EXHAUSTED` arrangement answers true, then false, and expects two
  asks. Its order with no stack base passes a callable that fails if
  called.
- Criterion 5: replace `cli._resolve_queue` with `_fake_batch_resolution`
  and call `_readiness_passes`, as
  `test_a_stack_batch_wires_its_spec_review_and_mint_once_readiness_passes`
  does. Replace `cli._stack_base_alive` to capture the wiring. Then drive
  the real one on `_local_origin`, `_push_parent_branch` and `_mirror_of`.
  That test replaces `real_remote`, so pass the bare origin's own path as
  the url, and a path that does not exist for the unreachable remote.
- Criterion 6: `_stack(root, 2)` in `tests/test_finish.py`. Open a
  second batch whose one layer reuses the top branch, with the bottom
  task as its predecessor. Run it once with its pull request on the
  bottom branch and once on `trunk`.

**Three things a reader can trip on.**

- Criterion 2's mutant pins the head the ledger already bakes in, which
  existing tests also kill. It proves the witness reads that head, not
  that `batch.py` seeds the predecessor.
- A hand push to the stack base after its last recorded push leaves
  `predecessor_head` older than the fetched seed. The stated range then
  spans the operator's commits, while the diff stays `head^..head`.
- Linking nothing is a choice. Run 4 linked by hand a list that included
  the pull request below, and that link worked.

**Size `--budget` for this spec.** A stack batch holds back a quarter of
`--budget` for the end review and a quarter for the writer. This spec's
`budget_usd` of 48 is half of 96. So it needs `--budget` of $96 or
more as a stack's first layer. Every earlier layer's budget and spec
review adds to that (`SA-0254`'s admission arithmetic).

**Measured on a prototype at `0a5e3e5c`, before the `cli.py` and
`batch.py` specs above.** It passed all six witnesses and `make check`.
Each witness failed with the four source files reverted. Its diff
measured 1602 changed tokens. Every wrong version above was applied as
an edit, and so was each declared mutant. Each failed its own
criterion's witness.
