---
id: SA-0327
title: "The finishing layer queues a follow-up whose cell ran, and a follow-up draft its own gates fail, so its suite escalates"
type: bug
priority: 2
estimated_lines: 136
depends_on: [SA-0325]
touches:
  - saffron/finish.py
  - saffron/follow_up.py
  - saffron/cli.py
  - tests/test_finish.py
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
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/qualify.py
  - saffron/intake.py
  - saffron/spec_review.py
  - saffron/end_review.py
  - saffron/batch.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/agents/**
  - saffron/phases/**
  - saffron/record/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/repos/**
  - tests/test_qualify.py
  - tests/test_package.py
  - tests/test_batch.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 30
max_attempts: 3
max_turns: 170
risk: standard
acceptance:
  - claim: >-
      `finish.commit_finish` takes a keyword `ran_dir`. It leaves out of
      its commit the latest spec text of each follow-up layer, a layer
      whose earliest `spec_texts` row carries the origin `follow_up`. It
      writes each such text to `ran_dir`, under its own file name, and
      emits one line naming the layer's spec id and the written path. It
      still commits every other layer's latest text and every unrun
      task's, and the commit touches no path under `done/`. The witness
      drives a follow-up layer whose latest text is a revision, and one
      whose only text is the writer's own. It also drives an original
      layer with a revision, an original layer with no text, an unrun
      follow-up and an unrun task with no text.
    witness: tests/test_finish.py::test_the_finishing_commit_leaves_out_each_follow_up_layer_that_ran_and_writes_its_text_to_the_ran_directory
    wrong_versions:
      - A layer is left out when its latest text carries the origin `follow_up`, so a follow-up layer whose latest text is a revision is still committed.
      - A follow-up layer's text is left out of the commit and written nowhere.
      - The left-out text is written into `done/` inside the finishing commit.
      - An unrun follow-up's text is left out as well.
      - A follow-up layer's first text is written to `ran_dir` instead of its latest.
      - No line is emitted for a left-out text.
  - claim: >-
      `cli._stack_finish` hands `commit_finish` a `ran_dir` named `ran`,
      in the batch tree's own finish directory for that batch. It sits
      beside the `tree` workdir the finish already passes.
    witness: tests/test_cli.py::test_a_stack_finish_hands_commit_finish_a_ran_directory_beside_its_tree
    wrong_versions:
      - The `ran_dir` is the workdir itself, which the finish removes.
      - The `ran_dir` is the batch's finish directory itself, so the texts sit beside `findings.json`.
  - claim: >-
      `finish.judge_draft(mirror, head, path, text, *, workdir, verify)`
      commits `text` at `path` atop `head`, in a worktree at `workdir`. The
      commit's parent is `head`, and its diff from `head` adds `path` alone.
      A ref under `refs/heads/` names the commit while `verify(sha, head)`
      runs. The ref and the worktree are gone once it returns or raises,
      and a raise from `verify` reaches the caller. It returns one line per
      new failure `verify` gives back, in order. A line reads `[gate]
      file:line code: message`, with `?` for a missing line. A failure with
      no file drops the `file:line ` part. It raises `ValueError` before
      `verify` runs for a symlinked `.saffron`, a symlinked
      `.saffron/specs` or a symlink at `path`. It raises `ValueError`
      before any worktree for a path outside the spec directory. The
      witness drives `.saffron/specs/done/x.md` and `CLAUDE.md`.
    witness: tests/test_finish.py::test_a_draft_is_judged_on_its_own_commit_atop_the_head_under_a_ref_the_judge_removes
    wrong_versions:
      - The draft is committed atop the mirror's own `HEAD`, not `head`.
      - '`verify` is called with the base and the commit swapped.'
      - The ref is left in the mirror after `verify` returns.
      - The ref is deleted only on the success path, so a raise from `verify` leaves it.
      - The worktree is left behind when `verify` raises.
      - "A failure with no file renders as `[gate] :? code: message`."
      - A failure with no line renders `None` in place of `?`.
      - The draft is written through a symlinked `.saffron/specs`.
  - claim: >-
      `write_follow_ups` takes a keyword `judge`, a callable given a
      draft's spec path and text that returns the lines naming its new
      failures. A draft that parses and passes `_validate` is judged once
      before it is minted. A draft that does not parse, or that `_validate`
      refuses, is never judged. A first draft the judge fails is sent back
      once through the `send_back(reason)` closure `SA-0325` adds. Its
      reason is `the finishing suite failed it: ` and the lines joined by
      `; `. The second prompt begins with the first prompt in full, then
      the reason, then the refused draft. `emit` gets a line naming the
      group's task key, its file and that reason. A second draft the judge
      passes is minted under the next id. The first session is charged to
      the origin task as one `WRITING` attempt. The witness drives a green
      first draft, a red first draft with a green second, a first draft
      that does not parse with a green second, and a first draft
      `_validate` refuses.
    witness: tests/test_follow_up.py::test_a_draft_the_finishing_suite_fails_is_sent_back_once_with_its_failures_and_then_minted
    wrong_versions:
      - The judge runs before `_validate`, so a draft `_validate` refuses is judged.
      - A draft that does not parse is handed to the judge.
      - A red first draft is pooled at once, with no send-back.
      - The send-back's reason names the failure count but not the failure lines.
      - The second draft is minted without being judged.
      - The gate branch builds its own second prompt and `write` call rather than calling `send_back`, so no line is emitted.
      - A green draft is judged twice.
      - The first session of a red draft is not charged.
  - claim: >-
      A group is sent back at most once, whichever refusal sent it. A
      second draft the judge fails pools with `the finishing suite failed
      it: ` and the second judgement's lines, and no third call is made.
      That holds whether the first draft failed the judge or failed to
      parse. A second draft that does not parse after a judge send-back
      pools with its parse reason. One `_validate` refuses pools with that
      reason. A judge send-back whose second `write` raises pools the group
      with `write raised`, and the raise goes no further. A judge send-back
      whose second session has a reset time pools its group and every later
      group. A judge that raises pools its group with `judge raised `, the
      exception's type, `: ` and its text. Every later group pools with that
      reason too, and makes no `write` call. The session the judge raised on
      is charged to the origin task. A red first draft the sub-cap cannot
      cover pools with its own judge reason, after one call. Every session of
      a pooled group is charged to the origin task.
    witness: tests/test_follow_up.py::test_a_draft_the_finishing_suite_fails_twice_pools_with_its_second_failures_and_never_a_third_call
    wrong_versions:
      - A second judge failure is sent back again, so a group makes three calls.
      - A draft sent back for a parse error and then failed by the judge is sent back a second time.
      - A second judge failure pools with the first judgement's lines.
      - A raise from the judge escapes `write_follow_ups`.
      - A raise from the judge pools only its own group, so later groups are still written.
      - The judge send-back sits outside the `try`, so a raise from its second `write` escapes `write_follow_ups`.
      - A judge send-back's second session runs its own copy of the reset handling, which pools its own group but leaves later groups to be written.
      - A session whose draft the judge raised on is not charged.
      - A red first draft the sub-cap cannot cover pools with the sub-cap reason, not its judge reason.
  - claim: >-
      `cli._stack_follow_ups` hands `write_follow_ups` a `judge` that calls
      `finish.judge_draft` with the pinned mirror, the top layer's graded
      head, the draft's path and text, and a workdir named `tree`. That
      workdir sits in a judge directory named for the batch key, beside
      the follow-ups export. The `verify` it passes runs
      `package_phase.reverify` on the given commit against the given head.
      That call uses the spec and policy `finish.finish_suite` builds from
      the policy exported at the pinned base. The export lands in `gates`,
      in the same judge directory. The `verify` returns
      the comparison's `new_failures` unchanged. The judge returns what
      `judge_draft` returns. `publish_finish`'s own `verify` still counts
      the same suite's new failures.
    witness: tests/test_cli.py::test_a_stack_batchs_follow_up_judge_runs_the_finishing_suite_on_each_draft_atop_the_top_head
    wrong_versions:
      - The judge runs the repo's policy as declared, with `protected` kept, rather than the finishing suite's.
      - The judge's base is the pinned base, not the top layer's graded head.
      - The judge's gates directory is the follow-ups export itself, which the export empties first.
      - The `verify` returns the count of new failures, not the failures.
---

## Context

Backlog item **b-e0044f**, under ADR 7 and `DESIGN.md` §5.7 and §2.1.
Every line below was read at `965c541f`.

**The run that found it.** The spec loop's run 49 ran `saffron finish 58`
(`docs/evidence/2026-10-27-spec-loop-skill-feedback-run-49.md`). The finish
drafted `SA-0323` and `SA-0324`. `SA-0323`'s cell ran and reached
`READY_FOR_REVIEW` as #982. `SA-0324` was refused for two citations, so it
was unrun. The finishing layer `341fee6e` added both to `.saffron/specs/`.
Its suite counted 40 new failures and escalated, so nothing was pushed. 39
were `prose` hits in the two drafts. One was `tests/test_queued_specs.py`
failing `SA-0323`, a queued spec whose fix was already in the tree.

**What the finishing commit writes.** `commit_finish` reads each layer's
latest spec text, then each unrun task's (`saffron/finish.py:174-184`). It
writes every one into the worktree (`:190-192`). Its docstring says it
retires no spec (`saffron/finish.py:161-162`). ADR 7 says the finishing layer
commits the batch's revised and follow-up specs
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:133-134`).
The host cannot close a backlog item, so retirement stays a hand step
(b-fdbedc). The operator decided on 2026-10-27 that a follow-up whose cell
ran leaves the commit, and its text goes to the batch tree for that step.

**Which layer is a follow-up.** `Ledger.spec_text` returns a task's latest
`spec_texts` row (`saffron/ledger.py:2002-2013`). A spec review's revision
of a follow-up records a row with the origin `revision`
(`saffron/batch.py:719-725`, `:888-894`). So a follow-up's latest row can
carry `revision`. `Ledger.batch_follow_ups` names a follow-up by its
earliest row's origin instead (`saffron/ledger.py:1872-1888`). A stack
batch records its follow-ups' layers at generation 1 and its order's at 0
(`saffron/batch.py:579`, `:987`). `Ledger.stack_layers` returns
`generation` beside `task_key` (`saffron/ledger.py:1770-1787`).

**The batch tree.** `cli._stack_finish` writes `findings.json` into
`finish/<batch id>/` and cuts its worktree at `finish/<batch id>/tree`
(`saffron/cli.py:1093-1113`). It calls `commit_finish` with no `emit`, so
the default `print` reaches the log (`:1106-1113`).

**How the finishing suite judges.** `finish_suite` builds the `FINISH-0`
chore spec and the repo's policy with `protected` emptied and its
suppression scan off (`saffron/finish.py:90-111`). `cli._finish_verify`
exports `.saffron/` at the pinned base, builds that suite and runs
`package_phase.reverify` (`saffron/cli.py:1014-1038`). It returns the
count of new failures (`:1038`). `reverify` runs the suite in two fresh
gate-only cells, a baseline and a head (`saffron/phases/package.py:475-586`).
It raises `PackageError` on an errored gate or drift. `publish_finish`
names the commit with a temporary ref while `verify` runs, since a
gate-only cell's seed can only fetch a branch (`saffron/finish.py:382-398`).

**Where a draft is accepted.** `write_follow_ups` parses each draft
(`saffron/follow_up.py:410-417` at `SA-0325`'s head), then `_validate`
reads it (`:419-429`).
A draft that passes is given its path, minted and charged to its minted
task (`:431-449`). Nothing between `_validate` and the mint reads the
repo's gates. The follow-ups adapter exports `.saffron/` at the pinned
base into `follow-ups/<batch key>` (`saffron/cli.py:1638-1640`). It reads
the top layer's graded fields there (`:1648`).

**The parent.** `SA-0325` adds `send_back(reason: str) ->
SpecWriterSession | None`, a closure inside `write_follow_ups` beside
`_pool` and `_charge`. It owns the whole send-back step, in this order.
It charges the loop's refused session to the origin task. Some groups it
pools with `reason`, and then it returns `None`. Those are a group already
sent back, and one whose `cap_usd` less what is spent cannot cover
`SPEC_WRITER_SESSION_USD`. Otherwise it marks the group sent back and
emits a line naming its task key, its file and `reason`. Then it calls
`write` once with the first prompt, then `reason`, then the refused draft.
A returned session re-enters the loop's handling from `spent` onward.
`SA-0325`'s notes name this spec's call site: after `_validate` passes,
before `mint` runs (`saffron/follow_up.py:419-431` at its head).

## Problem

Every finish that drafts a follow-up escalates, so none reaches its push.

1. **The queue.** `commit_finish` gains a keyword `ran_dir`. A follow-up
   layer is one whose earliest `spec_texts` row carries the origin
   `follow_up`. Its latest text leaves the commit. It is written to
   `ran_dir / Path(path).name`, with `ran_dir` made first. One line is
   emitted per such text, naming its spec id and the written path. Emit
   these after every text is read, so a missing-text line for an unrun
   task comes first (`tests/test_finish.py:492-493`). Every
   other layer's text and every unrun task's text is committed as today.
   Read and check every text with `_checked` before any write, as today.
2. **The wiring for the queue.** `cli._stack_finish` passes
   `ran_dir=out_dir / "finish" / str(batch_id) / "ran"`.
3. **The judge.** Add `finish.judge_draft(mirror, head, path, text, *,
   workdir, verify)`. Refuse a `path` that `_REVISION_PATH` does not fully
   match, before any worktree. Cut a worktree at `head`, call
   `_refuse_symlink` on `path`, write `text`, and commit it as
   `commit_finish` does. Name the commit with a ref under
   `refs/heads/saffron-judge/`, call `verify(sha, head)`, and delete the
   ref in a `finally`. Remove the worktree in a `finally` too. Render each
   `NewFailure` as `[gate] file:line code: message`, with `?` for a
   missing line. Drop the `file:line ` part when the failure has no file.
4. **The send-back.** `write_follow_ups` gains a required keyword `judge`.
   After a draft parses and passes `_validate`, and before the mint, call
   `judge(path, text)` with the path the mint would use. An empty list
   mints the draft as today. A non-empty list calls `send_back` with the
   reason `the finishing suite failed it: ` and the lines joined by `; `.
   `SA-0325` calls it inside its `except SpecError` clause
   (`saffron/follow_up.py:410-417`). So use one `send_back` site shared by
   the parse and judge refusals, or a `try` of the same shape. A raise from
   it pools the group with `write raised`, as that branch's does. Bind the
   return to a new name, end the group on `None`, and only then rebind
   `session`, as that branch does. The session then re-enters the one
   handling from `spent` onward, the reset time and the error included.
   Write no second copy of it. So the second draft meets the same parse,
   `_validate` and judge. On a second draft, or on a group already sent
   back for its parse, `send_back` pools the group with that reason.
5. **A raise from the judge.** It charges its session to the origin task
   through `_charge`, never through `send_back`. It pools the group with
   `judge raised <type>: <text>`. Every later group pools with the same
   reason before any `write` call, the way a reset time's reason does
   (`saffron/follow_up.py:322-324`). A raise is infrastructure, and it
   would repeat for each group.
6. **The wiring for the judge.** In `cli._stack_follow_ups`, pass a `judge`
   that calls `finish.judge_draft` with `pinned.mirror`, `top.head`, the
   path, the text and `out_dir / "follow-ups" / f"{batch_key}-judge" /
   "tree"`. Its `verify` is the finishing suite over `gates_dir`
   `out_dir / "follow-ups" / f"{batch_key}-judge" / "gates"`, returning
   `comparison.new_failures`. Reshape `_finish_verify` so the judge and
   `publish_finish` share it. `publish_finish`'s `verify` keeps returning a
   count.
7. **Docstrings.** `commit_finish`'s docstring, the module docstrings of
   `finish.py` and `follow_up.py`, and `write_follow_ups`'s say what
   changed. `_stack_follow_ups`'s docstring says every input is read once
   (`saffron/cli.py:1615-1617`). The judge's `verify` exports and loads the
   policy for each draft (`:1026-1027`), so rewrite that sentence. A function's docstring stays within ten lines. The `prose`
   gate exempts a module docstring (`.saffron/gates/prose.py:66`).

## Out of scope

- Moving a spec into `done/`, or closing a backlog item. Both stay the
  delegate's hand step (b-fdbedc).
- A follow-up whose cell ran and added no layer. `commit_finish` never
  wrote it (`saffron/finish.py:174-184`), and `write_findings` already
  carries its text (`:327-349`).
- Any gate's policy, and any gate core names. The judge runs the repo's own
  declared gates through the finishing suite (§2.1).
- `send_back` itself, the writer's prompt and its system prompt. They are
  `SA-0325`'s. Call `send_back` as it lands, and change none of its
  steps.
- A baseline shared across drafts. `reverify` runs its own baseline on each
  call.

## Notes for the agent

The ran directory, the judge and the send-back are new code. So every
criterion declares a witness and no mutant, and `witness` will report
`skip` for each.

**Why the earliest origin.** A follow-up's spec review can record a
`revision` row after the writer's own (`saffron/batch.py:719-725`). Reading
the latest row's origin would commit that follow-up again. In every batch
`run_stack_batch` records, generation 1 names the same layers. The witness
does not separate the two readings. Reasoned, not measured: the earliest
origin also covers a follow-up task that a later batch resumes as a
generation-0 layer.

**Unmeasured wrong versions.** No wrong version under criteria 1 and 3 to
6 was run. Those under criteria 4 and 5 can be run only once `SA-0325`'s
code lands.

**The judge's tree is not the finishing tree.** The judge commits atop the
end review's top head. The finishing commit sits atop the later top, which
includes the follow-up layers (`saffron/batch.py:987-1004`). So a draft
judged green can meet a different tree there.

**The path moves up.** The judge needs the path the mint uses, so the
`path =` line moves above the judge call (`saffron/follow_up.py:431`).

**Records amended by hand.** `DESIGN.md:472` and ADR 7's second amendment
line are amended in this spec's pull request, not by the cell.

**What the judge costs.** No model spend. Each judged draft costs one
`reverify`: two gate-only cells, each running the whole suite. This repo's
suite took about 193 seconds at `SA-0323`'s baseline, 179 of them in
`tests` (`~/.saffron/batches/v0/SA-0323/baseline.json`). So a judged draft
costs about six and a half minutes of wall time, and a group at most two
judgements. The finishing suite's own judgement is the narrowest form that
keeps the finish green. A form-gate subset misses a `tests` failure such
as `test_queued_specs.py`'s.

**Existing tests that move.**
- `test_the_finishing_commit_writes_each_layers_and_unrun_texts_and_moves_no_spec`
  expects `TE-20-follow.md` in the commit (`tests/test_finish.py:517`,
  `:525-527`). `TE-20` is a follow-up layer in the `stack` fixture, so drop
  both checks. Its `assert len(emitted) == 1` becomes 2, since `TE-20`'s
  new line follows `TE-24`'s. `emitted[0]` still names `TE-24`
  (`tests/test_finish.py:492-493`).
- Every `commit_finish` call in `tests/test_finish.py` needs a `ran_dir`
  (`:482`, `:535`, `:588`, `:648`, `:663`, `:713`, `:1382`, `:1393`).
- `_fake_commit_finish` names its keywords
  (`tests/test_cli.py:11481`) and needs `ran_dir`.
- `_fake_write_follow_ups` and `_make_partial_double` name theirs
  (`tests/test_cli.py:10583-10597`, `:10838-10853`) and need `judge`.
- Every `write_follow_ups` call in `tests/test_follow_up.py` needs a
  `judge`. One returning an empty list keeps each as it is.
- `test_a_stack_batch_publishes_its_finish_through_the_finishing_suite`
  checks `publish_finish`'s count (`tests/test_cli.py:11365`). It must stay
  green through the reshape of `_finish_verify`.

**The witnesses.**
- Criterion 1 builds on the `stack` fixture. Add a `TE-25` layer to
  `batch_b` at position 4, packaged at `stack.heads["TE-20"]`, generation
  1, whose only text has the origin `follow_up`. Pass `TE-24` and `TE-21`
  as unrun. Assert the commit's name-status lines exactly, and the files
  and texts in `ran_dir` exactly.
- Criterion 2 follows `test_a_stack_batch_commits_its_finish_and_survives_a_raise`
  (`tests/test_cli.py:11063`) and records `commit_finish`'s keywords.
- Criterion 3 drives `judge_draft` on the `stack` fixture's mirror at
  `stack.heads["TE-20"]`. Its `verify` double reads the refs and the
  commit while it runs. Call it twice with one `workdir`, once returning
  failures and once raising. Compare the mirror's refs before and after
  each call. Plant each symlink with the `add_worktree` wrapper
  `test_the_finish_refuses_a_symlink_on_any_path_it_writes` uses.
- Criteria 4 and 5 build on `SA-0325`'s helpers in
  `tests/test_follow_up.py`. Give each group its own finding claim, and
  compare groups with `==`. The judge double maps a draft's text to its
  lines, so each judgement is told apart. Assert the exact groups `write`
  saw, the exact `judge` calls, and each pooled reason in full.
  Criterion 5's sub-cap run sets `SPEC_WRITER_SESSION_USD` with
  `monkeypatch`, as `SA-0325`'s own witness does.
- Criterion 6 follows
  `test_a_stack_batch_publishes_its_finish_through_the_finishing_suite`
  for the export and `reverify` doubles. Its `write_follow_ups` double
  calls the `judge` it is handed. Record `finish.judge_draft`'s arguments,
  and call the `verify` it was handed.

**What the witnesses leave.** After a judge send-back, criterion 5 drives
a second `write` that raises and a second session with a reset time. A
second session that carries an error meets the same shared handling.
`SA-0325`'s witnesses drive it after a parse send-back, and these do not.
A `.saffron/specs` path that `_REVISION_PATH` refuses has more shapes than
the two driven. Each meets the same `re.fullmatch`.
