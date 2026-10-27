---
id: SA-0326
title: A review commit is read by no lens until the deferred finish, and no command reads one on its own
type: feature
priority: 2
estimated_lines: 320
touches:
  - saffron/commit_review.py
  - saffron/cli.py
  - tests/test_commit_review.py
  - CLAUDE.md
  - README.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
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
  - saffron/end_review.py
  - saffron/regate.py
  - saffron/finish.py
  - saffron/ledger.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/scheduler.py
  - saffron/preflight.py
  - saffron/intake.py
  - saffron/record/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/report/**
  - saffron/view/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/repos/**
  - tests/test_cli.py
  - tests/test_end_review.py
  - tests/test_regate.py
  - tests/test_ledger.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 48
max_attempts: 3
max_turns: 240
risk: standard
acceptance:
  - claim: >-
      `saffron review <task id> --repo <path>` reads an open pull request's
      review commits with the end review's per-layer review. It asks
      `gh pr view` about the task's `pr_url` and fetches the task's branch
      into the mirror at `_mirror_path`'s path. The range runs from the task
      row's `pushed_sha` to that fetched head. The policy and the spec file
      come from `.saffron/` exported at the run's `base_sha`. `CLAUDE.md` is
      read at that `base_sha` too. One cell opens through
      `end_review.layer_cell` at the fetched head, with that export and the
      policy's `thread_env`. The Spec lens runs, then the Standards lens,
      each bounded by `LENS_MAX_TURNS` and `LENS_BUDGET_USD`. Each system
      prompt holds the review commit's added line and not the packaged
      commit's. Each names the range start and the head, and lists the
      task's own in-cell finding. Each agent turn opens and closes one
      attempt labelled `COMMIT_REVIEW`, carrying that turn's session id,
      turn count and cost. Both lens reviews go to one JSON
      file named for the head, in a `commit-reviews` directory under the
      task's own directory in the batch tree. The cell's `findings.json` there keeps its bytes. The
      task's state, `pushed_sha`, `pr_url`, findings and end-review rows stay
      as they were. The command prints each finding and exits 0, since
      neither lens filed a blocker. The witness's Spec lens files a concern
      and its Standards lens a note.
    witness: tests/test_commit_review.py::test_review_reads_the_review_commits_with_both_end_review_lenses_and_charges_the_task
    wrong_versions:
      - The diff taken from the packaged head's parent, the whole layer, as `layer_fields` takes it.
      - The diff taken from the run's `base_sha`.
      - The head taken from the task row's `pushed_sha` rather than the fetched branch.
      - The policy, the spec or `CLAUDE.md` read from the checkout's working tree.
      - The export taken at the default branch's head rather than the run's `base_sha`.
      - A mirror at a path other than `_mirror_path`'s.
      - Only the Spec lens run, or each lens in its own cell.
      - The in-cell lens ceilings passed rather than the end review's.
      - An empty `known` block.
      - Attempts opened through `session.record_attempts`, so each is labelled with the task's state.
      - One attempt for both lenses, or a turn's cost left off its attempt.
      - The reviews written over the cell's `findings.json`.
      - The findings recorded with `record_findings`, or one `record_end_review` row per lens.
      - The task moved out of `READY_FOR_REVIEW`.
      - An exit of 1 on a concern or a note.
  - claim: >-
      When the packaged commit is not an ancestor of the fetched head, the
      range starts at its rebased copy. That copy is the commit on the
      head's first-parent chain whose full message equals the packaged
      commit's. The witness restacks the task's branch onto its moved
      predecessor, then adds two review commits. The newer one repeats the
      packaged commit's subject with another body, and each adds its own
      line. Each system prompt holds both review commits' added lines. It
      holds neither the predecessor's moved line nor the packaged commit's
      added line.
    witness: tests/test_commit_review.py::test_review_starts_a_restacked_branchs_range_at_the_packaged_commits_rebased_copy
    wrong_versions:
      - The range always started at `pushed_sha`, so the predecessor's move reads as review work.
      - The range started at the predecessor's fetched head, so the packaged change reads as review work.
      - A decline whenever `pushed_sha` is not an ancestor of the head.
      - The copy matched on the subject alone, by `--format=%s` or by `git log --grep`, so the newer review commit starts the range.
  - claim: >-
      A task holding recorded spec texts is read against its newest one,
      never the spec file at `base_sha`. The witness records two texts for a
      task whose file at `base_sha` hashes to its `spec_sha`. Each system
      prompt holds the second text's body marker, and neither the first
      text's nor the file's.
    witness: tests/test_commit_review.py::test_review_reads_a_task_against_its_newest_recorded_spec_text
    wrong_versions:
      - The file at `base_sha` used whenever it hashes to `spec_sha`.
      - The oldest recorded text used.
      - A task holding a recorded text declined, as `saffron regate` declines one.
  - claim: >-
      When either lens files a blocker, the command prints it, writes both
      reviews and exits 1. A lens that broke beside it leaves that exit at 1.
      The witness drives three runs. The Standards lens alone files a
      blocker in one, and the Spec lens alone in another. In the third the
      Standards lens files one while the Spec lens's turn raises
      `AgentFailed`.
    witness: tests/test_commit_review.py::test_review_exits_one_when_either_lens_files_a_blocker
    wrong_versions:
      - An exit of 0 whatever the lenses filed.
      - Only the first lens's findings counted toward the exit.
      - An exit of 2 whenever any lens broke, a blocker beside it included.
  - claim: >-
      With no blocker from either lens, each of four breaks exits 2. In the
      first the Spec lens's turn raises `AgentFailed`, and the review file
      records that lens's error. That failed turn's cost is still charged
      through one `COMMIT_REVIEW` attempt. The second is the same break in
      the Standards lens's turn alone. In the third `end_review.layer_cell`
      raises. The review file then records an error for both lenses, and no
      attempt opens. In the fourth `gh pr view` exits non-zero, and no cell
      opens. The witness drives all four.
    witness: tests/test_commit_review.py::test_review_exits_two_when_a_lens_or_its_cell_breaks_and_charges_the_failed_turn
    wrong_versions:
      - A broken lens read as one that found nothing, so the exit is 0.
      - Only the first lens's error read, so a Standards break alone exits 0.
      - A failed turn left with no attempt, or one carrying a cost of 0.
      - A failed `gh pr view` read as a decline that prints and returns.
  - claim: >-
      The command declines each of these thirteen tasks before any cell.
      Each prints `review:` and a reason holding the fragment named here,
      then exits 2. An id with no task row gives "names no task". A task
      with a pushed head and no pull request gives "carries no pull
      request". A task whose adopted pull request has no packaged head gives
      "has no packaged head". A task of another repo than `--repo`'s gives
      "belongs to another repo". A pull request GitHub reports `MERGED`
      gives "is MERGED", and one it reports `CLOSED` gives "is CLOSED". A
      fetched head equal to `pushed_sha` gives "is the packaged head". A
      restacked head that is the packaged commit's rebased copy itself gives
      "is the packaged commit's rebased copy". A head holding neither the
      packaged commit nor a commit carrying its message gives "holds no
      packaged commit". A newest recorded text that `parse_spec` refuses
      gives "recorded text does not parse". With no recorded text, a missing
      `.saffron/specs/<spec id>-*.md` at `base_sha` gives "no spec file". A
      spec file there whose sha is not `spec_sha` gives "does not hash to".
      A task the command would read, with `CLAUDE_CODE_OAUTH_TOKEN` unset,
      gives "CLAUDE_CODE_OAUTH_TOKEN is unset". None opens a cell, runs an
      agent, opens an attempt or writes a review file. The witness drives all
      thirteen in one test and asserts each case's own fragment.
    witness: tests/test_commit_review.py::test_review_declines_each_task_it_cannot_read_before_any_cell_and_exits_two
    wrong_versions:
      - Any one of the thirteen declines dropped, so its case falls through to a later decline with another reason.
      - A recorded text that does not parse left to raise, so `main` exits 2 with no `review:` line.
      - A state check that declines `CLOSED` and lets `MERGED` through.
      - An empty range checked only as head equal to `pushed_sha`, so a restacked copy with nothing on it reaches a cell.
      - The token read only after the cell opens.
      - A decline that exits 1, so a caller reads it as a blocker.
  - claim: >-
      The spec body both lenses read opens with one framing paragraph that
      `commit_review.py` holds. It says the diff holds only the review
      commits made after the cell's packaged head, and that a criterion met
      below the range is not unmet. It names the range start and the head by
      sha. In each system prompt it sits under the spec heading, ahead of
      the spec's own body. The spec file and the recorded texts stay
      unchanged.
    witness: tests/test_commit_review.py::test_review_frames_the_spec_body_as_review_commits_over_a_packaged_head
    wrong_versions:
      - No framing paragraph, so the Spec lens reads the review commits as the whole layer.
      - The paragraph in the Spec lens's prompt alone.
      - The paragraph after the spec's body rather than ahead of it.
      - A paragraph naming the run's `base_sha` or the packaged head's parent as the range start.
  - claim: >-
      A SIGTERM while a lens runs exits 143 through `_guarding_sigterm`. The
      cell `end_review.layer_cell` opened is torn down first. The witness
      installs its own SIGTERM handler first, which must not be the one
      that runs.
    witness: tests/test_commit_review.py::test_review_stopped_by_sigterm_tears_its_cell_down_and_exits_143
    wrong_versions:
      - The dispatch calling the command with no `_guarding_sigterm` around it.
      - The attempt wrapper catching `BaseException`, so the interrupt never unwinds the cell.
---

## Context

Backlog item **b-549012**, found in the spec loop's run 49. It cites
`DESIGN.md` §5.7, and this spec also leans on §4.1 and ADR 7. Every line
number below was read at `5a9ee6d7`.

**A review commit reached the stack unread.** PACKAGE pushes one commit per
task, `saffron <spec id>: <title>` (`saffron/phases/package.py:315`). The
operator's review commits land on top of it. In run 49, `2742f631`,
`review(SA-0322)`, sits on the packaged `f4afbd49`
(`git log 5a9ee6d7`). The item records that this commit dropped a kill.
Two review seats read the cell's diff before it, and `make check` passed.
Only the deferred finish's end review raised it, as a blocker.

**The end review's per-layer review is the reader to reuse.**
`end_review._review_one_layer` (`saffron/end_review.py:427-476`) takes a
`resolve` callable, a spec map, a mirror and an `open_cell` factory. It
diffs `fields.diff_base..fields.head` in the mirror
(`saffron/end_review.py:419-424`). It opens one cell and runs `review_layer`,
the Spec lens then the Standards lens (`saffron/end_review.py:358-407`). A
raise reading the fields, the diff or the cell becomes an error review for
both lenses at cost 0 (`saffron/end_review.py:472-476`).
`LayerFields` holds `spec_id`, `branch`, `pr_url`, `base`, `head`, `known`
and `diff_base` (`saffron/end_review.py:63-80`). `_known_block` formats the
task's in-cell findings (`saffron/end_review.py:92-94`). `layer_fields` sets
`diff_base` to `pushed_sha^`, the whole layer
(`saffron/end_review.py:147`). `layer_cell` brings a critic cell up at
`fields.head` and always tears it down in a `finally`
(`saffron/end_review.py:752-832`).

**How the deferred finish wires it.** `_stack_end_review` exports `.saffron/`
at the pinned `base_sha` and loads the policy from it
(`saffron/cli.py:895-898`). It reads `CLAUDE.md` at that sha and
`CONTEXT.md` from the engine's own root (`saffron/cli.py:899-900`). Its
agent is `stop_on_rejected` over `implement.run_agent` with
`TURN_TIMEOUT_S` (`saffron/cli.py:901-907`). Its `open_cell` is
`end_review.layer_cell` with the export and `policy.thread_env`
(`saffron/cli.py:908-914`). It passes `LENS_MAX_TURNS` and
`LENS_BUDGET_USD` (`saffron/cli.py:928-929`, `saffron/end_review.py:50-51`).

**`saffron regate` is the nearest command in shape.** It reads the task row
and its run, asks `gh pr view <pr url> --json state,baseRefName`, and
declines any state but `OPEN` (`saffron/regate.py:49-73`). It fetches the
task's branch into the mirror (`saffron/regate.py:145-147`). It exports
`.saffron/` at the run's `base_sha` and loads the spec whose sha is the
task's `spec_sha` (`saffron/regate.py:150-154`, `saffron/regate.py:86-96`).
A decline prints `regate:` and returns 1 (`saffron/regate.py:155-157`). It
declines a task holding a recorded spec text (`saffron/regate.py:55-58`).
`_regate` hands it the resolved `--repo`, the ledger, `out_dir`,
`_mirror_path` and `run_gh` (`saffron/cli.py:2791-2804`). The dispatch runs
it inside `_guarding_sigterm` (`saffron/cli.py:366-367`).

**Where a session is charged.** An attempt row is the unit of spend (§4.1).
`Ledger.open_attempt(task_id, phase)` takes a phase the task's state is
not, for a host-invoked session (`saffron/ledger.py:1536-1562`).
`close_attempt` records the session id, model, subtype, turns and cost
(`saffron/ledger.py:1564-1592`). `task_spend` sums every attempt
(`saffron/ledger.py:1594-1604`). `session.record_attempts` opens each
attempt under the task's own state (`saffron/cell/session.py:291-315`). The
stack batch charges a spec review under `SPEC_REVIEW` instead
(`saffron/batch.py:758-766`). `run_lens` catches `AgentFailed` and keeps
the failed turn's cost (`saffron/phases/review.py:320-326`).

**What a later reader holds.** `saffron finish` refuses a batch that already
holds an end-review row (`saffron/cli.py:2494-2501`). `record_end_review`
refuses a second row for one lens of one layer (`saffron/ledger.py:2041`). A
`findings` row names no head (`DESIGN.md` §4.1's schema, `DESIGN.md:393`).
`saffron package` reads the cell's `findings.json` under
`<out dir>/<spec id>/` (`saffron/task.py:1219-1225`).

**The token.** `_finish` refuses with `CLAUDE_CODE_OAUTH_TOKEN` unset, before
any cell (`saffron/cli.py:2508-2511`). `CLAUDE.md` lists the commands that
need it (`CLAUDE.md:87`). `CLAUDE.md` is not in `.saffron/policy.yaml`'s
`protected` list, so this cell edits it.

## Problem

Add `saffron review <task id> --repo <path>`, `--repo` defaulting to the
working directory. It reads one task's review commits with `end_review`'s
per-layer review, charges the session to the task, and writes the findings
into the batch tree. It changes no task state.

**`saffron/commit_review.py` takes every step.** `saffron/cli.py` adds the
parser and dispatches inside `_guarding_sigterm`, as `regate` does. It
passes the resolved `--repo`, the ledger, the shared `out_dir`,
`_mirror_path`'s path and `run_gh`. The steps run in this order.

1. Read the task row and its run. Decline an unknown id, a task with no
   `pr_url`, and a task with no `pushed_sha` or `branch`. Decline a task
   whose run's `repo_id` is not the one `resolve_repo_id` gives for
   `real_remote(repo)`.
2. Ask `gh pr view <pr url>` for its state. A non-zero exit raises. Decline
   any state but `OPEN`.
3. `ensure_mirror` at `_mirror_path`'s path, and fetch the task's branch with
   `fetch_parent_branch`. That is the head.
4. Find the range start. It is `pushed_sha` when that is an ancestor of the
   head. Otherwise it is the newest commit on the head's first-parent chain
   whose full message equals `pushed_sha`'s. Decline when none matches.
   Decline when the range start is the head itself.
5. Export `.saffron/` at the run's `base_sha` and load the policy from it.
   Take the spec from the task's newest recorded text when it holds one,
   declining a text `parse_spec` refuses. Otherwise take the file under the export's `.saffron/specs/` whose sha
   is the task's `spec_sha`, declining when there is none.
6. Decline a `CLAUDE_CODE_OAUTH_TOKEN` that is unset or empty.
7. Prepend the framing paragraph below to the spec's body. Build one
   `LayerFields`: `base` and `diff_base` the range start, `head`
   the fetched head, `known` the task's `_known_block`. Call
   `end_review._review_one_layer` with a `resolve` that returns it. Pass
   the same `open_cell`, `context_md`, `claude_md`, prompts, ceilings and
   agent shape `_stack_end_review` builds, with the run's `base_sha` as
   its pin.
8. Write the reviews, print each finding, then print one summary line, and
   return the exit code.

A decline prints `review:` and its reason, and returns 2. Any other raise
propagates to `main`, which exits 2.

**The framing paragraph.** Both end-review prompts were written for a whole
layer, and the Spec lens files an unmet criterion as a blocker
(`saffron/agents/prompts/end-review-spec.md:12-14`, `saffron/agents/prompts/end-review-spec.md:38-39`). So the body
handed to the lenses opens with one paragraph, built in `commit_review.py`.
It says the diff holds only the review commits made after the cell's
packaged head, and it names both shas. It says a criterion met below the
range is not unmet. The lens reads the worktree at the head, so it can find one. The
prompt files stay as they are.

**Each decline's reason** carries the fragment criterion 6 names, so a
caller can tell one decline from another.

**Exit codes.** 1 when any finding of either lens is a `blocker`. Otherwise
2 when either lens carries an error. Otherwise 0. A blocker is counted
whether or not it anchored, because the defect run 49 missed sat outside
the review commit's own hunks.

**Charging (§4.1).** Wrap the agent so each turn opens
`ledger.open_attempt(task_id, phase="COMMIT_REVIEW")` and closes it with the
turn's own `AttemptResult` fields. On `AgentFailed`, close it from the
exception's `attempt`, then re-raise for `run_lens` to catch. Put the wrapper
inside `stop_on_rejected`, as `record_attempts` documents its own
placement. A `BaseException` that is not an `Exception` passes through
untouched.

**The review file.** Write `<out dir>/<spec id>/commit-reviews/<head
sha>.json`, the full 40-character head. It holds `task_id`, the range start,
the head, and `reviews`, each lens's `LensReview.as_dict()`. Write it once
the lenses return, whatever they found. A second read of one head replaces
that head's file. Record nothing through `record_findings` or
`record_end_review`. A `findings` row names no head, so a reader could not
tell these from the cell's own. An end-review row makes `saffron finish`
refuse the batch.

**Output.** One line per finding, naming its severity, lens, file, line and
claim. Then one line naming the head, the range start and the blocker count,
and one naming the review file's path.

**The documentation, as cell work.**

- `CLAUDE.md`'s command list gains one line after `regate`'s
  (`CLAUDE.md:63`). The token sentence at `CLAUDE.md:87` gains
  `saffron review`.
- `README.md` gains a short paragraph and block after `regate`'s
  (`README.md:143-150`). It names the token and the three exit codes.
- `saffron/cli.py`'s module docstring lists every subcommand
  (`saffron/cli.py:1-3`). Add `review`.

## Out of scope

- **The loop's own text.** The spec loop skill calling the command after each
  review commit is a separate edit.
- **`DESIGN.md` and `CONTEXT.md`.** Both are protected. The paragraph in
  §6.1 and the vocabulary entries are backlog item b-bc8343, by hand.
- **The lens prompts.** The files stay as they are. The framing paragraph
  rides in the spec body. Exit 1 is still unmeasured as a signal. No live
  review commit was read this way. How often the Spec lens files a blocker
  for a criterion met below the range is unknown.
- **The stack page.** `saffron/report/stack.py:136-155` lists six attempt
  labels, so its attempt table omits `COMMIT_REVIEW` rows while
  `task_spend` counts them. Backlog item b-bc8343 carries it.
- **The join lens.** One task's range has no seam to read.
- **A merge into the branch.** A review range holding GitHub's "update
  branch" merge reads the merged commits as review work.
- **Readiness.** The command runs no `check_readiness`. A rejected token
  surfaces as a lens error, exit 2. `cell_up` still runs N1's probe.
- **A packaged head missing from the mirror.** PACKAGE committed it there,
  so the read of its message finds it. A pruned one raises, exit 2.

## Notes for the agent

**Every criterion is new code.** Neither the module nor the subcommand exists
at base. So each criterion declares a witness and no mutant, and `witness`
reports `skip` for each. With the source reverted, `review` is no
subcommand, so `main` raises `SystemExit` from argparse and every witness
fails. Import nothing at the witness module's top that this change adds.

**The seams.** Call each host step through its module, so a monkeypatch
reaches it. They are `saffron.cli.run_gh` as the dispatch reads it,
`end_review.layer_cell` and `implement.run_agent`. Read each when the
command runs, never at import. The witnesses replace `layer_cell` with a
context manager that records its `fields` and keywords and whether its exit
ran. They replace `run_agent` with a fake that records each system prompt
and its options and returns an `AttemptResult`. Its `text` holds an
`<output>` block. The witnesses also replace `saffron.task.run_one_cell`
with a function that raises.

**A scan reads every file under `saffron/`.**
`tests/test_refusal_count.py` fails any file but `scheduler.py` whose text
holds the refusal constructor's call. So name the decline otherwise, as
`regate` does with `_Declined`. Annotate the runner with
`package_phase.GhRunner`.

**What each fake returns by default, and what that default hides.**

- The agent fake tells the lenses apart by the prompt's opening line. It
  returns a distinct session id, turn count and cost per lens. Equal values
  would pass a build that charges one turn twice.
- The `layer_cell` fake yields a container name. Criterion 1 asserts its
  `fields.head`, its `mirror`, its `gates_dir` and its `thread_env`, and that
  it opened once.
- `gh` answers `OPEN` unless a case sets another state. It records its argv,
  and criterion 1 asserts the argv names the task's `pr_url`.

**The origin is real git.** Build a checkout with a bare origin as `origin`,
as `tests/test_regate.py` does. On `main`, commit a policy whose
`thread_env` carries a marker, a spec whose body carries a marker, and a
`CLAUDE.md` carrying a marker. That commit is `base_sha`. Commit new markers
in all three on `main` after it. Fork the task's branch from `base_sha` with
a packaged commit, whose message has a subject and a body. Add a review
commit on it. Each of the two adds its own unique line. Push both branches.
Then rewrite the working copy's three files with a third set of markers. Seed
the repo row with the origin's path, a run at `base_sha`, and the task with
the spec's sha. Record one in-cell finding under a lens in `review.LENSES`.
Call `set_task_package` with the packaged commit and a pull request URL.
Write a `findings.json` into the task's directory first.

**Criterion 2's two review commits.** Add the first review commit with its
own subject. Add the second with the packaged commit's subject, another body
and its own line. A subject match then starts the range at the second.

**Criterion 2's restack.** Fork a predecessor branch from `base_sha` with a
commit, and fork the task's branch from it. Move the predecessor with a
commit adding its own line. Rebase the task's branch onto the moved
predecessor with `git rebase --onto`, then add the review commit. Keep a
branch in the checkout naming the original packaged commit, so the mirror
holds it as PACKAGE's own mirror does.

**Criterion 3's texts.** Record both with `record_spec_text`, origin
`revision` and a path under `.saffron/specs/`. Each text parses, carries the
task's spec id, and holds its own body marker.

**Criterion 5's failed turn.** Raise `AgentFailed(message, attempt)` with an
`attempt` whose cost is not zero.

**Criterion 6's cases.** Unset the token for the last case alone. Build the
no-pull-request case with `ledger.record_push`, so the task has a
`pushed_sha` and no `pr_url`. Record one text that does not parse for the
unparseable case. Assert each case's own fragment, never `review:` alone. Seed a run
at a commit with no spec for the missing file. Seed a `spec_sha` of zeros for
the mismatched one. Seed a task under a second repo row for another repo.
Use `adopt_pull_request` on a task with no package for the missing head. A
branch reset to a fresh commit carrying another message covers the head
holding neither.

**Criterion 7** sets its own SIGTERM handler before `main`, and restores the
earlier one in a `finally`. Its agent fake sends the process SIGTERM. With
the guard, `main` returns 143, the `layer_cell` fake's exit ran, and the
test's handler never ran.

**Residuals, one line each.**

- `layer_cell` names its cell for the spec id and removes any container of
  that name first (`saffron/end_review.py:774-781`). A `saffron review` run
  during a finish of the same spec removes the finish's lens cell. The
  operator does not run the two at once.
- `_review_one_layer` turns any raise into an error for both lenses at cost
  0 (`saffron/end_review.py:472-476`). A rate-limited Standards turn raises
  `RateLimited`, a `RuntimeError` (`saffron/cell/session.py:248`). So a
  Spec blocker before it is lost, the exit is 2, and the file shows cost 0
  while the attempts hold the spend. `end_review.py` stays forbidden.
- The session's attempts join the batch's spend through its run. A deferred
  batch's `saffron finish` then has that much less left for follow-ups.
- `saffron package` declines a task that carries a pull request, so it never
  counts these attempts as its cell's own.

**Wrong versions.** Each criterion lists the ones its witness must kill. Do
not run them yourself.

**The `prose` gate** counts every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words.

**Size.** No path in `touches` is in `elevate_on`, so the task is `standard`
and `size` is advisory. `estimated_lines` counts the source, the dispatch and
the two documents, about 1200 tokens. The witnesses sit under the declared
test paths, which `size` does not count.
