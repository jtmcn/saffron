---
id: SA-0161
title: A stack batch's qualified findings reach no writer, so no follow-up spec exists
type: feature
priority: 1
depends_on: [SA-0164]
touches:
  - saffron/follow_up.py
  - tests/test_follow_up.py
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
  - saffron/cli.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/ledger.py
  - saffron/qualify.py
  - saffron/spec_review.py
  - saffron/end_review.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/events.py
  - saffron/probe.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - tests/test_cli.py
  - tests/test_batch.py
  - tests/test_task.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
  - tests/test_qualify.py
  - tests/test_spec_review.py
  - tests/test_end_review.py
  - tests/test_session.py
budget_usd: 24
max_attempts: 3
max_turns: 130
pending_symbols:
  - saffron/follow_up.py::write_follow_ups
  - saffron/follow_up.py::WRITER_SHARE
acceptance:
  - claim: >-
      `follow_up.write_follow_ups(ledger, stack, *, batch_key, qualify,
      write, mint, mirror, specs_dir, repo_id, test_paths, cap_usd, emit,
      pooled)` calls `qualify` once, with the stack's layers and its join.
      It emits one line counting the `Qualification`'s own pool. It takes
      the groups in the order returned. Each pooled entry is appended to the
      caller's `pooled` as it arises, and `emit` gets one line for it. A
      finding whose named probe does not match exactly once in its file at
      the top layer's head is pooled, in a group narrowed to such findings.
      The group's other findings go on. A whole group is pooled in each of
      these cases. A writer session before it met a reset time. The sub-cap
      left is under `spec_review.SPEC_WRITER_SESSION_USD`. Its allowed paths
      hold no path `test_paths` match. `write` raises. The session carries
      an error or a reset time. Its text does not parse. The parsed spec
      has another id than the one assigned, a type other than `bug` or
      `feature`, or a `depends_on` entry. Its `touches` is empty or names a
      path outside the allowed paths. Its `budget_usd` exceeds the origin
      spec's. A mutant has both the file and the `find` of a probe the
      group's written findings name. The allowed paths are the group's file
      and each path `test_paths` match that the stack's range changes. The
      origin task is the task whose record key is the group's. The origin
      spec is that task's latest spec text, and its file in `specs_dir`
      when it has none. The sub-cap left is `cap_usd` less the sessions'
      own costs, and no other spend. A pooled session's cost is one
      `spec_review.WRITING_PHASE` attempt on the origin task. A group
      pooled after its probe check holds only the findings not already
      pooled. A raise part-way through leaves `pooled` holding every entry
      before it. The witness drives each case, a group with a failing and
      a matching probe, a revised origin spec, other tasks of the origin's
      spec id with their own texts, a glob in `touches`, and a test path
      the stack's range leaves unchanged. It drives a budget equal to the
      origin's, a layer task with spend of its own, and a sub-cap remainder
      equal to the ceiling.
    witness: tests/test_follow_up.py::test_a_group_the_host_refuses_or_the_sub_cap_cannot_cover_goes_to_the_pool
  - claim: >-
      Every other group becomes one `Candidate`, in the groups' order, and
      the call returns the list. Its id is `next_spec_id` of the origin
      spec's id, read before its session. Its path is
      `.saffron/specs/<id>-<slug>.md`. The slug is the lowercased title's
      runs of `[a-z0-9]` joined by `-`, or `follow-up` when there are
      none. Its `spec_sha` is the SHA-256 of the session's text. `mint`
      gets it with no `task_id`. The minted task then gets one
      `WRITING_PHASE` attempt with the session's cost, `session_id` and
      turns. Its run joins the batch `batch_key` names. Last, it gets a
      `follow_up` spec text of that id, path and text. A follow-up is
      written once that record returns. The candidate returns with that
      task. The prompt names the id, the allowed paths, the origin's
      budget, each finding written with its probe and verdict, the origin
      spec's text, the origin layer's diff, and the origin and top heads.
      It names no pooled finding. The witness drives three accepted groups
      on two layers, one of them with an empty slug.
    witness: tests/test_follow_up.py::test_an_accepted_follow_up_is_a_minted_task_with_its_text_and_its_writers_cost
  - claim: >-
      A sub-cap of $100 times `follow_up.WRITER_SHARE` writes one
      follow-up whose session costs
      `spec_review.SPEC_WRITER_SESSION_USD`. It pools the second and third
      groups as over the sub-cap.
    witness: tests/test_follow_up.py::test_a_hundred_dollar_night_writes_one_follow_up_at_the_writer_ceiling
  - claim: >-
      `follow_up.next_spec_id(origin_id, specs_dir, ledger, repo_id)`
      returns one more than the highest number carrying the origin id's
      prefix. It reads the `.md` file names in `specs_dir` and in its
      `done/`, and the spec ids of the repo's tasks. The number is
      zero-padded to the origin id's width. The witness makes each source
      the highest in turn. It holds a file of another prefix, a task of
      another repo, and an origin id of another width.
    witness: tests/test_follow_up.py::test_the_next_spec_id_reads_both_spec_directories_and_the_repos_tasks
---

## Context

Backlog item **b-792ab2**, step 7 of its Done. It cites `DESIGN.md` §1.4,
§4.2.1 and §5.5. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides that qualified end-review findings become follow-up specs, one
generation deep. Section 3 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md`, "Follow-ups take
the same chain" and "The host enforces a follow-up's fields", is the design.
Its **Money** paragraph gives the writer a sub-cap of its own.

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**. Once the last queued task
settles, one **end review** reads the stack. `SA-0147` qualifies its
findings and groups the qualified ones by layer and file.

**This spec is the first of three for follow-up writing.** It builds the
host logic: qualification's first caller, the writer per group, the host's
refusals, the next free id and the writer sub-cap. `SA-0173` adds the
`follow_ups` and `writer_usd` keywords to `run_stack_batch`. `SA-0165`
builds the command-line callable that binds `qualify`, the writer's critic
cell and the mint, and passes it from `saffron batch --stack`. `SA-0162`
then runs the follow-ups as generation 1.

**What the tree base holds.** This spec's tree base is `SA-0164`'s head.
Only `depends_on[0]` stacks (`saffron/task.py:144-148`). The chain
`SA-0142` to `SA-0164` puts these names there, so they are cited by symbol.
Every line number below was read at `f2a08a9f`, where none of them exist.

- `SA-0145` and `SA-0146`: `record_stack_layer`, and
  `end_review.layer_fields(ledger, task_key)`, whose `head` is the layer's
  `pushed_sha` and whose `spec_id` is its task's.
- `SA-0154`: `end_review.StackReview`, a frozen dataclass of `join` and
  `layers`. `layers` holds one `LayerReview` per layer, top down, each with
  its `task_key`.
- `SA-0147`: `qualify.qualify(ledger, layers, join, *, mirror, repo,
  gates_dir, thread_env, test_paths, gates, created, note)`. It returns a
  `Qualification` of `groups` and `pool`. Each `FollowUpGroup` holds a
  `task_key`, a `file` and a tuple of `findings`. A survived probe makes its
  finding a `blocker` and sets its `probe_verdict`.
- `SA-0150`: `Ledger.record_spec_text(task_id, *, origin, spec_id, path,
  text)`, and `Ledger.spec_text(task_id)`, the latest row or `None`. A row's
  `spec_sha` is the SHA-256 of its text, as `load_spec` hashes a file
  (`saffron/intake.py:308-319`). Its fact's `batch_key` is the task's run's
  batch when it is written (`saffron/ledger.py:372-391`).
- `SA-0156` and `SA-0168`: `cli._stack_mint`, whose mint creates a run and
  a task with no batch and returns the task's id, and
  `Ledger.task_run(task_id)`.
- `SA-0160`: `spec_review.SpecWriterSession`, a frozen dataclass of
  `text`, `cost_usd`, `error`, `resets_at`, `session_id`, `num_turns` and
  `spec_sha`. `SPEC_WRITER_SESSION_USD` is 18.5, the budget of one
  session's writer and extraction turns. Its one re-ask can add 1.5
  more. `run_spec_writer` returns the spec text from its
  extraction turn.
- `SA-0164`: `spec_review.WRITING_PHASE`, `SPEC_WRITING`, the phase of
  every writer session's attempt. It charges each revision session as an
  attempt on its spec's task.

**What the base holds.** `batch_spend` sums the attempts of the tasks on
the batch's runs (`saffron/ledger.py:897-912`). `attach_run_to_batch` sets
a run's batch (`:848-863`). `open_attempt` takes a phase (`:1000-1023`).
`tasks_by_repo` lists a repo's tasks with their spec ids (`:712-727`), and
`record_key` gives a task's key (`:366-370`). `parse_spec` refuses a mutant
whose `find` the body or a claim spells (`saffron/intake.py:260-303`). It
does not refuse one a finding named. The `scope` gate's glob match is
`matches` (`saffron/gates/core/scope.py:31-36`), and `touches` is judged
by it. `mirror.changed_files`
and `mirror.file_at` read a range's paths and a file at a sha
(`saffron/repos/mirror.py:136-158`, `saffron/repos/mirror.py:241-270`). `worktree.git_argv` and
`DIFF_FLAGS` pin a diff's shape (`saffron/cell/worktree.py:132-205`). A
spec file's name starts with its id and a hyphen
(`saffron/cell/session.py:459-466`), and ids are numbered from the highest
existing one (`docs/agents/issue-tracker.md:10-11`). `RETIRED_DIRNAME` is
`done` (`saffron/scheduler.py:504`).

**What a writer costs.** No writer session is in the ledger yet. So the cost
was measured on the operator's `spec-writer` and `spec-reviewer` sessions,
from their transcripts' token counts. They were priced at the cell's own
rates, which 294 result events in `~/.saffron/batches/` fit exactly. Those
are $3, $15, $0.30 and $6 per million input, output, cache-read and
cache-write tokens.

| sessions | n | mean | median | p90 | max |
|---|---|---|---|---|---|
| `spec-writer` | 74 | $6.24 | $4.21 | $16.92 | $23.43 |
| `spec-reviewer` | 256 | $1.38 | $1.35 | $2.21 | $3.71 |

The batch's writer holds Bash, as the hand writer does, so these figures
apply to it.

## Problem

Build two things in `saffron/follow_up.py`.

1. **The names.**
   - `WRITER_SHARE`, 0.25, the share of `--budget` a stack batch holds back
     for its writer.
   - A frozen dataclass `Pooled`, of `group` and `reason`.
   - `next_spec_id`, as criterion 4 states. A file name counts by its
     leading id, since an unparseable file still holds its number. A task
     counts too, because its branch and its queue rows carry its spec id.
   - `write_follow_ups`, as criteria 1 and 2 state. It returns the list of
     candidates. `qualify` takes a layer list and a join. `write` takes a
     group and a prompt, and returns a `SpecWriterSession`. `mint` takes a
     `Candidate` and returns a task id. `pooled` is a list the caller owns.
     No `pooled` copy rides on the return, so a raise loses nothing.
2. **The walk.** Before the groups, read each layer's head with
   `layer_fields`. The top head is the first layer's, and the bottom the
   last's. The stack's test paths are `mirror.changed_files` over
   `<bottom head>^..<top head>` that `test_paths` match. Then, per group:
   - A reset time met earlier pools the group with the same reason.
   - The sub-cap check. The remainder is `cap_usd` less every session's
     cost so far. Read `spec_review.SPEC_WRITER_SESSION_USD` at call time.
   - The probe check at the top head, finding by finding. `mirror.file_at`
     gives the text, and a missing file counts as no match. A group left
     with no finding ends here.
   - The allowed paths: the group's file, then the stack's test paths. With
     none matching `test_paths`, the group is pooled.
   - The origin task, found by record key among `tasks_by_repo`. Its head
     is `layer_fields` of the group's key. Its text, and its parse. With no
     spec text, the file is the one in `specs_dir` whose name starts with
     the layer's spec id and a hyphen. The id, from `next_spec_id`.
   - The prompt, then `write` with the group narrowed to its written
     findings. A pooled session is charged to the origin task.
   - An accepted group: `mint`, then the attempt, then
     `attach_run_to_batch` of `task_run` and `int(batch_key)`, then
     `record_spec_text` with origin `follow_up`. So the attempt's facts
     carry no batch, and the spec text's fact carries this one.

   The prompt opens with a `context:` line naming the origin spec. It says
   the reply is the spec text, and that the writer files no record. It says
   the findings cite lines at the origin head, and that the writer's tree is
   the top head. The diff is `git diff` with `DIFF_FLAGS` over
   `<head>^..<head>` in `mirror`, through `worktree.git_argv`.

**Why a probe is checked at the top.** A follow-up runs on top of the
stack. A later layer can move a probe's `find` text, and a `find` that
matches other than once is `unproven` (`saffron/cell/worktree.py:640-648`,
`saffron/probe.py:206-210`). So a finding whose probe no longer matches
once at the top is pooled. Principle 28 asks that the group's other
findings still reach a follow-up.

**Why the host checks the mutant.** ADR 3 forbids a follow-up that declares
a named probe as its own mutant. `parse_spec` catches that only when the
body or a claim spells the `find`. A writer can leave it out of both.

**The sub-cap.** `SA-0165` passes `--budget` times `WRITER_SHARE` as
`cap_usd`, and `SA-0173` holds the same amount back from generation 0. A
writer starts only while the sub-cap covers one session at
`SPEC_WRITER_SESSION_USD`, 18.5. A $100 night holds $25, which covers one
session at that ceiling, since $6.50 is left after it. At the measured
mean of $6.24 it writes two, since $18.76 is left after the first.
Criterion 3 fails if the ceiling falls to $12.50 or below with the share
unchanged, since two sessions then fit. With `SA-0157`'s quarter for the end review, generation 0 runs
within half of `--budget`.

## Out of scope

- **The keywords on `run_stack_batch`.** `SA-0173` adds `follow_ups` and
  `writer_usd`.
- **The command-line callable.** `SA-0165` binds `qualify` with the probe
  cell's keywords, and `write` with `run_spec_writer` in a critic cell. It
  seeds that cell at the top layer's head, the tree the prompt names. It
  calls `run_spec_writer(container, *, system_prompt, prompt, agent)` as
  `SA-0160` defines it. The system prompt is core's
  `saffron/agents/prompts/spec-writer.md`, which `SA-0176`'s
  `spec_writer_system_prompt` fills from the policy at the pinned
  `base_sha`. It binds the mint, owns `pooled`, passes
  `follow_ups` from `saffron batch --stack`, and catches every raise.
- **Running the follow-ups.** `SA-0162` appends them on top, records each
  layer at generation 1, and moves the batch row's close after them.
- **The anchors of principle 27.** ADR 7's entry holds once a follow-up's
  anchors and named probe are keyed to the tree it runs on. The probe is
  checked at the top here. The anchors stay at the origin head, and the
  prompt names both heads. That is the residual.
- **A revision of a follow-up.** `SA-0150`'s gate 0 refuses one whose
  `touches` widens past its first spec text's.
- **Ids that reach the default branch after the pinned base.**
  `next_spec_id` reads the specs at the base and this ledger. A spec merged
  since, with no task here, can take the same id.
- **Ids that live in the ledger alone.** A follow-up that missed, or that
  its review refused, is never committed. Its id is then in no spec file,
  so hand numbering from the highest file id
  (`docs/agents/issue-tracker.md:10-11`) can take it again. The delegate
  files a backlog item.
- **A durable record of a pooled entry.** It gets an `emit` line and no
  fact. `SA-0151` lists every qualified finding beside the batch's
  follow-ups.
- **A raise from `qualify`, `mint` or a ledger write.** Each propagates.
  `SA-0165`'s callable catches it.
- **The fields a follow-up claims beyond these.** Its `risk`, `max_turns`
  and `max_attempts` are the writer's claims. The budget bounds its money.
- **Vocabulary.** `CONTEXT.md` has no entry for a follow-up spec, the
  writer sub-cap or the pool. Backlog item b-466005 files them by hand.

## Notes for the agent

**Every criterion is new code.** No text at the tree base writes a
follow-up. So each declares a witness and no mutant, and `witness` reports
`skip` for each. Import every new name inside the test body, so the
reverted source fails each test rather than its collection.

**Criteria 1 and 2 share one arrangement.** A helper builds it, runs
`write_follow_ups` once, and returns what each test reads. Build a git repo
in `tmp_path` as the mirror, with `-c user.name` and `-c user.email` on
each commit.

| commit | change |
|---|---|
| base | `src/a.py` `alpha`, `src/b.py` `beta` then `beta_l2`, `src/c.py` `gamma`, `tests/test_a.py`, `tests/test_c.py` |
| `H1` | `src/a.py` becomes `alpha_new`, and `tests/test_a.py` changes |
| `H2` | `src/b.py` line 2 becomes `beta_rate`, `src/c.py` becomes `gamma gamma`, and `tests/test_b.py` is added |

`specs_dir` holds `SA-0101-one.md` and `SA-0102-two.md` at a budget of 12,
`SB-0400-other.md`, and `done/SA-0105-old.md`. Open a `Ledger` in
`tmp_path` with a `MemoryRecord`, and open a batch. Create these tasks,
each on its own run, in order:

- `SA-0102`, no batch, a `revision` spec text at budget 9 saying "before"
- `SA-0101` on the batch, packaged `READY_FOR_REVIEW` at `H1`, with one
  closed `IMPLEMENTING` attempt at 0.5
- `SA-0102` on the batch, packaged at `H2`, with a `revision` spec text at
  budget 10 saying "revised body"
- `SA-0102`, no batch, a `revision` spec text at budget 8 saying "after"
- `SA-0107`, no batch and no file

Record the two packaged tasks as layers 1 and 2, as `SA-0145` does. The
`StackReview` has a join `LensReview` and the two layers, top down.

Replace `spec_review.SPEC_WRITER_SESSION_USD` with 1.0 through
`monkeypatch`. `qualify` records its arguments, and returns these groups
and a pool of two. `write` records each group and prompt, and plays the
turns in order. A string turn is a session of that text at 0.25, with a
`session_id` and three turns. `mint` creates a run with no batch and a
task. `cap_usd` is 4.25, and `test_paths` is `["tests/**"]`. `rate` is a
survived probe on `beta_rate` in `src/b.py`, and `gone` one on `beta_l2`.

| # | layer, file | findings | turn | outcome |
|---|---|---|---|---|
| 1 | `SA-0102`, `src/b.py` | `rate`, a probe-less concern, `gone` | `SA-0108`, budget 10, `touches` `src/b.py` and `tests/test_b.py`, a mutant on `src/b.py` with another `find` | `gone` pooled, the rest accepted |
| 2 | `SA-0101`, `src/a.py` | the concern | `touches` `src/a.py` and `tests/test_b.py` | accepted |
| 3 | `SA-0102`, `src/b.py` | the concern | id `SA-0999` | id |
| 4 | the same | the concern | type `refactor` | type |
| 5 | the same | the concern | a `depends_on` entry | depends_on |
| 6 | the same | the concern | budget 11 | budget |
| 7 | the same | the concern | `touches` `src/**` | touches |
| 8 | the same | the concern | empty `touches` | touches |
| 9 | the same | `rate`, `gone` | a mutant on `src/b.py` with the `find` `beta_rate` | `gone` pooled, then mutant |
| 10 | the same | the concern | `touches` `src/b.py` and `src/c.py` | touches |
| 11 | the same | the concern | `touches` `src/b.py` and `tests/test_c.py` | touches |
| 12 | the same | the concern | a text with no frontmatter | parse |
| 13 | the same | the concern | a session with error `idle bound` | error |
| 14 | the same | the concern | `write` raises `RuntimeError("cell gone")` | raise |
| 15 | `SA-0101`, `src/b.py` | `gone` | none | probe, no match at `H2` |
| 16 | `SA-0102`, `src/c.py` | a probe on `gamma` | none | probe, two matches |
| 17 | `SA-0102`, `src/b.py` | `rate` | title "(-)", a mutant on `src/c.py` with the `find` `beta_rate` | accepted |
| 18 | the same | the concern | none | sub-cap |

Group 1's turn carries `SA-0108` and group 2's `SA-0109`. Every later turn
carries `SA-0110`, except group 3's. Group 1's title is "A layer's rate,
re-read".

**Criterion 1's witness** asserts `qualify` got the layers and the join.
The first `emit` line holds `2`, and one more line comes per pooled entry.
It asserts the seventeen pooled entries in order, each with a reason
naming its case. The first holds `gone` alone. Group 9's two entries hold
`gone`, then `rate`. Group 15's names `SA-0101`'s key. It asserts fifteen
`write` calls. `SA-0101`'s layer task holds its `IMPLEMENTING` attempt
alone, and the two other `SA-0102` tasks hold none. The layer task of
`SA-0102` holds eleven `WRITING_PHASE` attempts, and the batch's spend is
4.0. Then it runs
three calls on the same arrangement.

- Three groups of the concern, `cap_usd` 50, and one turn with a reset
  time. One `write` call, and three entries pooled for the rate limit.
- One group, and `test_paths` `["spec/**"]`. No `write` call, and one
  entry pooled for no test path.
- Two groups, turns `SA-0999` and a valid `SA-0111`, and a `mint` that
  raises. The raise propagates, and the caller's list holds the id
  refusal.

These fail it, each measured:

- a gate of spent under `cap_usd`, or a strict one against the ceiling
- the gate at `SPEC_WRITER_BUDGET_USD`, or fixed at 18.5
- no session's cost counted
- the test paths from the origin layer's diff
- `touches` matched as globs, or an empty `touches` accepted
- any path a `test_paths` glob matches accepted in `touches`
- every test file at the top head allowed
- the remainder read as `cap_usd` less `batch_spend`, which pools group 17
- a refused group pooled with a finding already pooled
- a budget equal to the origin's, refused
- the origin budget read from the file, past a revision
- the origin task found by spec id, the first or the last
- no check of the id, the type, `depends_on` or the mutant
- the probe read at the origin head, or not checked
- the whole group pooled for one failing probe, or pooled unnarrowed
- no check for a test path
- a reset time that pools only its own group
- a raise from `write` that propagates
- an errored session parsed as text
- a pooled session charged nowhere
- no `emit` line per entry, or no count of the qualification's pool
- the join dropped from the `qualify` call
- the pool kept in a local list and handed over at the end

**Criterion 2's witness** asserts three candidates, `SA-0108`, `SA-0109`
and `SA-0110`. Their paths end `SA-0108-a-layer-s-rate-re-read.md` and
`SA-0110-follow-up.md`. `mint` got each with no `task_id`. Each task is
new, not the layer's or another `SA-0102` task. Each holds one
`WRITING_PHASE` attempt at 0.25 with `s` and three turns. Its spec text
row is `follow_up` with that id and path, and `spec_sha` hashes the row's
text. Group 1's `spec_sha` hashes turn 1's text. Each task's facts are
`task_created`, `attempt_opened`, `attempt_closed` and `spec_text`. The
attempt's fact carries no batch key, and the spec text's carries the
batch's. Group 1's prompt holds `SA-0108` and the allowed paths `src/b.py`,
`tests/test_a.py` and `tests/test_b.py`. It holds the budget 10.0, both
written claims, `src/b.py:1`, the probe's `find`, `replace` and
`survived`, "revised body", `+beta_rate` and `H2`. It holds neither
`gone`'s claim, "before", "after" nor `alpha_new`. Group 2's prompt holds
its allowed paths, `+alpha_new`, `H1`, `H2` and `SA-0101`'s file text, and
not `+beta_rate`. These fail it, each measured:

- the test paths from the top layer's diff alone, or from the origin's
- the id read once for the whole walk, or from `specs_dir` alone
- the origin task found by spec id, the first or the last
- the whole group pooled for one failing probe
- a mutant refused by its file alone, or by its `find` alone
- the accepted session charged to the origin task
- the minted run left off the batch
- the spec text recorded before the attach, or the attach before the
  attempt
- the candidate returned without its task
- the `spec_sha` of anything but the session's text
- a slug that drops an apostrophe, or an empty slug kept
- no diff in the prompt, or the top layer's diff for every group
- a pooled finding sent to the writer

**Criterion 3's witness** runs the same arrangement with the real
constants. Three groups on `SA-0102`, each written at exactly
`SPEC_WRITER_SESSION_USD` with a valid text. It asserts `SA-0108` alone,
and two entries pooled over the sub-cap. A share of 0.18 writes none, and
one of 0.37 writes two. Both fail it, reasoned, since the figure changed
after the prototype ran.

**Criterion 4's witness** has `SA-0003-x.md` and `SB-0900-x.md` in
`specs_dir`, and expects `SA-0004`. It adds `done/SA-0012-y.md` and
expects `SA-0013`. It adds a task for `SA-0090` in another repo and one
for `SA-0020` in this one, and expects `SA-0021`. An origin of `SB-01`
gives `SB-901`. These fail it, each measured:

- `done/` not read, or the tasks not read
- the tasks of every repo read
- a pattern not anchored on the prefix
- a width fixed at four
- the first free number in place of one past the highest

**The writer's attempt.** Its subtype is `error` when the session carries
an error, and `success` otherwise, as `SA-0164` records a revision's. Its
`terminal_reason` is `None`.

**The ceiling's tail.** The measured writer sessions have a p90 of $16.92
and a max of $23.43. `SPEC_WRITER_BUDGET_USD` of 17.0 sits above the p90
(`SA-0160`). So fewer than one in ten sessions shaped like them would
reach it, stop there, and see its group pooled.

**How the lists were measured.** A throwaway prototype ran on 2026-09-24,
on the host's git. It stood in for `StackReview`, `LayerReview`,
`layer_fields`, `FollowUpGroup`, `Qualification`, `SpecWriterSession`,
`WRITING_PHASE`, `SPEC_WRITER_SESSION_USD`, `record_spec_text`,
`spec_text` and `task_run`, as the chain states them. Its
`record_spec_text` appended a `spec_text` fact built by `_build_fact`. It
ran the real `parse_spec`, `matches`, `changed_files`, `file_at`,
`git_argv`, `Ledger` and `MemoryRecord`. The right build passed every
witness above. Each wrong version listed was applied as a text edit, and
each failed its own witness.

**What the witnesses leave undriven.**

- A group whose key names no task of the repo. The lookup raises
  `KeyError`.
- An origin spec with no spec text and no file. The lookup raises.
- A stack with no layers. `qualify` then returns no group.

**The `prose` gate** reads every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense, a hedge or a
sentence over 25 words. Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** No path here is in `elevate_on`, so `size` is advisory at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). The
prototype, formatted by `ruff format`, measured 2342 changed tokens with
`size_gate` itself. `saffron/follow_up.py` took 1007 and
`tests/test_follow_up.py` 1335. That is 78% of the ceiling, with few
docstrings. Keep the arrangement in one helper and the turns in one table.
