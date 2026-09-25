---
id: SA-0165
title: saffron batch --stack hands its end review to no follow-up writer, and holds no share of its budget for one
type: feature
priority: 1
depends_on: [SA-0173]
touches:
  - saffron/cli.py
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
  - saffron/batch.py
  - saffron/follow_up.py
  - saffron/qualify.py
  - saffron/spec_review.py
  - saffron/end_review.py
  - saffron/task.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/ledger.py
  - saffron/events.py
  - saffron/probe.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - tests/test_batch.py
  - tests/test_follow_up.py
  - tests/test_qualify.py
  - tests/test_spec_review.py
  - tests/test_end_review.py
  - tests/test_task.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_session.py
budget_usd: 22
max_attempts: 3
max_turns: 130
acceptance:
  - claim: >-
      `cli._stack_follow_ups(*, pinned, repo, ledger, out_dir, cap_usd,
      pooled)` returns a callable that takes a batch key and a
      `StackReview`. Given a stack with no layers, it returns `[]`, and
      reads, prints and calls nothing. Otherwise it exports `.saffron/` at
      the pinned `base_sha` into `out_dir / "follow-ups" / <batch key>`, and
      loads that export's policy. The system prompt is the file the policy's
      `spec_writer_prompt` names, read at the pinned `base_sha`, after its
      frontmatter. It then calls `follow_up.write_follow_ups` once, with the
      ledger, the stack and the batch key. Its `mirror` is the pinned mirror,
      `specs_dir` the export's `.saffron/specs`, and `repo_id` the pinned
      url's. Its `test_paths` is the policy's, `cap_usd` is as given,
      `pooled` is the `pooled` list itself, and `emit` prints. Its `qualify` calls `qualify.qualify` with the ledger
      and the layers and join it gets. It passes the pinned mirror, `repo`,
      the export, the policy's `thread_env` and `test_paths`, and the
      policy's gates under `worktree.GATES_MOUNT`. It passes one `created`
      set, and a `note(step, ok, detail)` that prints its detail. It keeps
      the `Qualification` it returns. Its `mint` calls `_stack_mint` of the
      pinned base, `repo` and the ledger, and keeps each task id it returns
      beside the group last written. Its `write` brings up
      `end_review.layer_cell` at `layer_fields` of the stack's first layer,
      over `repo`, the pinned mirror, the export and its `thread_env`. In
      that cell it returns `spec_review.run_spec_writer` of the system
      prompt and the prompt it got. The agent is `implement.run_agent`
      bound to `spec_review.SPEC_WRITER_TIMEOUT_S` and to `follow-up-` plus
      the spec id of the group's own layer. Each `write` call gets its own
      cell. The callable returns the list of candidates `write_follow_ups`
      returns, and adds nothing to `pooled`. A raise from the export, the policy load, the prompt read, the repo lookup,
      `layer_fields` or `write_follow_ups` is caught. The callable then
      prints one line, `follow-ups: stopped, <type>: <message>`, and returns
      `[]`. Given a kept `Qualification`, it takes each of its groups in
      order and skips an accepted one. A group is accepted when a task id
      kept beside a written group of its `task_key` and `file` has a spec
      text, by `ledger.spec_text`. For any other group it keeps the findings
      that no `Pooled` in `pooled` holds, compared by equality. If any
      remain, it appends a `Pooled` of the group narrowed to them, with the
      reason `"<type>: <message>"`. Given no `Qualification`, it leaves
      `pooled` as it was. A raise before `qualify` runs brings up no cell.
      The witness drives each raise, an unset key, a prompt with no
      frontmatter, and groups on two layers. It drives a success that leaves
      a minted group without a text. It drives a raise after a mint with no
      text, and one before a group's session. Each holds a whole pooled
      group, a narrowed pooled group, and an accepted group written
      narrowed.
    witness: tests/test_cli.py::test_a_stack_batchs_follow_ups_are_qualified_and_written_from_the_pinned_base_at_the_stacks_top
  - claim: >-
      `saffron batch --stack --budget N` passes `run_stack_batch` a
      `writer_usd` of `N` times `follow_up.WRITER_SHARE`, read when the
      command runs, and a `follow_ups` callable. It builds that callable
      once with `_stack_follow_ups`, from the `PinnedBase` readiness
      returned, the resolved `--repo`, the ledger `main` opened and `main`'s
      `out_dir`. Its `cap_usd` equals `writer_usd`, and its `pooled` is an
      empty list. The budget still passes whole. The plan header prints
      `writer $<writer_usd>` after the reserve. When readiness fails, it
      builds no callable and passes `follow_ups=None`.
    witness: tests/test_cli.py::test_a_stack_batch_holds_the_writer_share_and_passes_its_follow_up_writer
  - claim: >-
      A night without `--stack` prints its plan header as before, with no
      reserve and no writer share.
    witness: tests/test_cli.py::test_the_printed_night_is_unchanged_by_sharing_the_base
    preserves: true
  - claim: >-
      `saffron batch` without `--stack` still hands `run_batch` its budget
      and its defaults.
    witness: tests/test_cli.py::test_saffron_batch_runs_a_night_with_the_defaults_4_2_1_fixes
    preserves: true
---

## Context

Backlog item **b-792ab2**, step 7 of its Done. It cites `DESIGN.md` §2.1,
§4.2.1 and §5.5. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides that qualified end-review findings become follow-up specs, one
generation deep. Section 3 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md` is the design.
Spec writing runs as a host-invoked session in a critic cell. Its
**Money** paragraph gives the writer a sub-cap of its own.

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**. Once the last queued task
settles, one **end review** reads the stack.

**Follow-up writing takes three specs, and this is the third.**
`SA-0161` builds the host logic in `saffron/follow_up.py`. `SA-0173` adds
the `follow_ups` and `writer_usd` keywords on `run_stack_batch`. This spec
builds the command-line callable that binds its cells, and passes it from
`saffron batch --stack`. `SA-0162` then runs the follow-ups as generation
1.

**What the tree base holds.** This spec's tree base is `SA-0173`'s head.
Only `depends_on[0]` stacks (`saffron/task.py:133-136`). The chain from
`SA-0142` puts these names there, so they are cited by symbol. Every line
number below was read at `68892367`, where none of them exist.

- From `SA-0143` and `SA-0144`: `run_stack_batch` in `saffron/batch.py`,
  and `saffron batch --stack`. Its `_batch` calls `run_stack_batch` where
  readiness passed and `pinned` is bound.
- From `SA-0146`: `end_review.layer_fields(ledger, task_key)`, which
  returns `LayerFields`. Its `spec_id` and `branch` are the layer's task's,
  and its `head` is that task's `pushed_sha`.
- From `SA-0153` and `SA-0154`: `end_review.StackReview`, of `join` and
  `layers`, with one `LayerReview` per layer, top down, each with its
  `task_key`. `end_review.layer_cell(fields, *, repo, mirror, gates_dir,
  thread_env)` is a context manager. It seeds a critic cell at
  `fields.head`, yields its container, and always tears it down.
- From `SA-0147`: `qualify.qualify(ledger, layers, join, *, mirror, repo,
  gates_dir, thread_env, test_paths, gates, created, note)`. It probes in
  Gate-only cells, and passes the last six keywords through to them.
- From `SA-0156`: `cli._stack_mint(*, pinned, repo, ledger)`, whose
  callable mints a run and a task for a candidate and returns the task id.
  `_stack_mint` upserts the repo at the pinned url.
- From `SA-0157`: `_stack_end_review`, and the `--stack` path's
  `reserve_usd` of `--budget` times `end_review.RESERVE_SHARE`.
  `_print_batch_plan` takes `reserve_usd`, and prints `budget $<budget>,
  reserve $<reserve>, until <deadline>` when it is given.
- From `SA-0160`: `Policy.spec_writer_prompt`, and the start refusal when
  the policy at the pinned base leaves it unset. `spec_review` holds
  `SpecWriterSession`, `run_spec_writer(container, *, system_prompt,
  prompt, agent)` and `SPEC_WRITER_TIMEOUT_S`, the writer turn's wall
  clock of 3600 s. `cli._stack_revise` reads the writer prompt the way
  this spec does.
- From `SA-0164`: the `revise` route, and `_stack_revise` wired into the
  `--stack` path.
- From `SA-0161`: `follow_up.write_follow_ups(ledger, stack, *,
  batch_key, qualify, write, mint, mirror, specs_dir, repo_id, test_paths,
  cap_usd, emit, pooled)`, which returns the list of follow-up
  `Candidate`s. It appends each `Pooled` to the caller's `pooled` list as
  it arises. A group whose findings partly fail the probe check is pooled
  narrowed to those findings, and its other findings go on to a writer.
  `write` then gets the group narrowed to the findings it writes. `qualify` takes a layer list and a
  join. `write` takes a group and a prompt, and returns a
  `SpecWriterSession`. `mint` takes a `Candidate` and returns a task id.
  For an accepted group it mints, then opens the attempt, then attaches
  the run, and records the spec text last. `follow_up.Pooled` holds a
  group and a reason. `follow_up.WRITER_SHARE` is 0.25. A raise from
  `qualify`, `mint` or a ledger write propagates out of
  `write_follow_ups`, and `SA-0161` leaves it to this spec to catch.
- From `SA-0173`: `run_stack_batch` takes `writer_usd` and `follow_ups`.
  It calls `follow_ups` once after its end review, with the batch's key and
  the `StackReview`.

**What the base holds.** `_drive_cell` hands REVIEW's probe call the
policy's `thread_env` and `test_paths`, its gates, its `created` set and a
teardown `note` (`saffron/cell/session.py:2577-2589`). Its gates are the
cell-side paths under `worktree.GATES_MOUNT`
(`saffron/cell/session.py:1668-1670`, `saffron/cell/worktree.py:22`).
`gate_executables` joins `.saffron/gates/<name>` to the directory it gets
(`saffron/repos/policy.py:87-90`). `critic_cell` removes each name it
added to `created` in its own `finally`, and reports a survivor through
`note` (`saffron/cell/session.py:1219-1234`). `export_saffron_dir` removes
its destination first (`saffron/repos/mirror.py:173-218`). It raises
`GitError` for a sha the mirror lacks (`:207-209`). `load_policy` raises
`PolicyError` (`saffron/repos/policy.py:114-138`). A pydantic refusal
carries its message over several lines, measured. `file_at` returns
`None` for a missing path, and raises `GitError` for a directory
(`saffron/repos/mirror.py:231-259`). `_FRONTMATTER`'s second group is the
text after the first closing fence (`saffron/intake.py:28`).
`resolve_repo_id` returns `None` for a url with no row
(`saffron/ledger.py:673-681`). `run_agent` takes `spec_id` and
`timeout_s` as keywords, and `timeout_s` defaults to 3600
(`saffron/phases/implement.py:190-199`). `critic_cell` and the probe call
take `note` as `(step, ok, detail)` (`saffron/cell/session.py:1130`,
`:1230-1234`, `:1460`).
`TURN_TIMEOUT_S` is 900 s, per turn (`saffron/cell/session.py:58-63`).
`_print_batch_plan` prints the night's header
(`saffron/cli.py:715-735`).

## Problem

Build two things in `saffron/cli.py`.

1. **The callable.** Add `_stack_follow_ups(*, pinned, repo, ledger,
   out_dir, cap_usd, pooled)` beside `_stack_end_review`, as criterion 1
   states. Its callable does its work in this order.
   - Return `[]` at once for a stack with no layers.
   - Inside one `try`, read every input at the pinned base. Export
     `.saffron/`, load the policy, and read the prompt file with
     `git_mirror.file_at`. An unset key raises `ValueError` naming
     `spec_writer_prompt`. A missing file, or one `_FRONTMATTER` does not
     match, raises `ValueError` naming the path. Then look up the repo id,
     and raise `ValueError` naming the url when it is `None`. Then read
     the top layer's `layer_fields`.
   - Still inside the `try`, build `qualify`, `mint` and `write` over
     those inputs, and call `write_follow_ups` with `pooled` itself.
     `qualify` keeps the `Qualification` it returns. `write` notes the
     group it is writing. `mint` keeps each task id beside that group.
   - On `except Exception`, print `follow-ups: stopped, <type>:
     <message>`, with the message's whitespace runs joined by one space.
     Given a kept `Qualification`, pool each group that is not accepted,
     narrowed to its findings no `Pooled` holds, as criterion 1 states.
     Build the narrowed group with `dataclasses.replace`. Return `[]`.
   - Otherwise return the list `write_follow_ups` returned.

   Reach `git_mirror.export_saffron_dir`, `git_mirror.file_at`,
   `cli.load_policy`, `end_review.layer_fields`, `end_review.layer_cell`,
   `qualify.qualify`, `spec_review.run_spec_writer`, `implement.run_agent`,
   `follow_up.write_follow_ups` and `_stack_mint` through their modules at
   call time, since the witness replaces them there.
2. **The wiring.** In `_batch`'s `--stack` path, where readiness passed,
   create `pooled: list[follow_up.Pooled] = []`. Compute `writer_usd` as
   `args.budget * follow_up.WRITER_SHARE`. Build the callable once, and
   pass `run_stack_batch` `writer_usd` and `follow_ups`. Pass
   `follow_ups=None` when readiness fails. Add `writer_usd`, `None` by
   default, to `_print_batch_plan`. Given one, the header reads `budget
   $<budget>, reserve $<reserve>, writer $<writer>, until <deadline>`.
   The `--stack` path passes it.

**Why every input is read first.** `write_follow_ups` catches a raise from
`write` and pools that group (`SA-0161`). A prompt read inside `write`
would pool every group, one line each, after `qualify` had spent its
probe cells. Read first, a missing prompt is one line and no cell.

**Why each `write` gets its own cell.** A writer session runs with Bash in
its critic cell (`SA-0160`). One cell for every group would hand the next
writer a tree the last one changed.

**Why the top layer's head.** A follow-up is cut from the top of the stack
(`SA-0162`). `SA-0161`'s prompt names that head as the writer's tree, and
its probe check reads there.

**Why the agent's id names the origin layer.** `run_agent` files each
event line under its `spec_id`. The follow-up's own id is assigned inside
`write_follow_ups`, and `write` never sees it. `follow-up-SA-0102` says
which layer the session writes from, as `SA-0157`'s `end-review-<key>`
does for a lens. Two groups on one layer share that id. Every write also
reuses the top layer's cell names. Both are safe, since each cell is torn
down before the next comes up.

**Why a raise still pools.** `SA-0174`'s `findings.json` lists the
qualified findings a pooled group names. A group the walk never reached
would drop out of it. So each finding of a group not accepted, and not
already pooled, is pooled here with the raise as its reason. A finding
pooled before the raise keeps its own reason. The check reads findings,
not groups, since `SA-0161` pools part of a group when only some of its
probes moved. A check by layer and file alone would drop the rest.

**Why accepted means a spec text.** `SA-0161` records the spec text after
the mint, the attempt and the attach. A raise between the mint and the
text leaves a minted task with no text, which no later step reads. So a
mint alone does not accept a group. `write` gets a narrowed group, so
the accepted check compares its `task_key` and `file`, never the whole
group.

**Why no second teardown.** `created` goes to `qualify` alone, and each
probe cell removes its own names in its `finally`
(`saffron/cell/session.py:1219-1234`). `layer_cell` holds a set of its
own. A second removal of the same names would only repeat those calls and
print their misses.

**The share.** `SA-0161` sizes `WRITER_SHARE` so a $100 night writes at
least two follow-ups. It passes the same number as `writer_usd` and as
`cap_usd`, so the loop holds back exactly the writer's sub-cap. With
`SA-0157`'s reserve, generation 0 runs within half of `--budget`.

**`SA-0174` reuses the list.** `SA-0174` sits above this spec in the
chain (`SA-0165`, `SA-0162`, `SA-0151`, then `SA-0174`). It gives `_stack_finish` a `pooled`
keyword, and passes it the list the `--stack` path already holds. So this
spec creates the list, and `SA-0174` must pass that same object to
`_stack_finish`. That keyword is not at this spec's tree base, so
`SA-0174`'s own witness asserts the identity.

## Out of scope

- **The host logic.** Qualification's call, the prompt, the refusals, the
  next id and the sub-cap are `SA-0161`'s.
- **Running the follow-ups.** `SA-0162` appends them on top as generation
  1 layers.
- **The findings file.** `SA-0174` writes `findings.json` from `pooled`.
- **Tasks minted before a raise.** A follow-up with a recorded text
  keeps its task, text and attempt, and its run stays on the batch. The
  callable returns `[]`, so it never runs. A task minted with no text
  keeps its task and any attempt, and its group is pooled. Both are
  residuals.
- **A raise inside `qualify`.** `qualify` records a `qualification` row
  for each finding as it decides it. A raise part-way leaves those rows
  and no `Qualification`, so no group reaches `pooled`. This is a
  residual.
- **A raise before `qualify` runs.** The export, the policy load, the
  prompt read, the repo lookup and `layer_fields` come first. A raise
  there leaves no `Qualification` and no `qualification` rows, so no
  finding reaches `pooled`. This is a residual.
- **The wall clock past `--until`.** Each writer session runs up to two
  turns at `SPEC_WRITER_TIMEOUT_S`, after the loop stops. The sub-cap
  bounds how many sessions start. `README.md:123-124` and the overshoot
  bound at `DESIGN.md:202` gain this too. Both files are forbidden here,
  and backlog item b-1adb50 files them by hand.
- **This repository's policy key.** `.saffron/policy.yaml` gains
  `spec_writer_prompt` by hand, as `SA-0160` says.
- **Concurrent writers.** They wait for per-cell network names
  (b-6a692d).

## Notes for the agent

**Criteria 1 and 2 are new code.** No text at the tree base writes a
follow-up from the command line or holds a writer share. So each declares
a witness and no mutant, and `witness` reports `skip` for each. Criteria 3
and 4 name tests that pass now.

**Every witness fails with the source reverted.** Criterion 1 calls
`cli._stack_follow_ups`, which the reverted source lacks. With the source
reverted, `_batch` passes `run_stack_batch` no `writer_usd`, so criterion
2's fake reads a key that is not there. Import each chain name inside the
test body.

**Other fakes of `run_stack_batch`.** The chain's earlier specs fake it
in `tests/test_cli.py`. Each fake must accept `writer_usd` and
`follow_ups`, through `**kwargs` or by name. Edit each fake that
refuses them, and change nothing else in it.

**The `--stack` header changes.** `SA-0157`'s witness,
`test_a_stack_batch_holds_a_quarter_of_its_budget_and_reads_its_stack_at_the_pinned_base`,
asserts the output holds `budget $42.00, reserve $10.50, until none`. That
text no longer appears. Change its expected line to `budget $42.00,
reserve $10.50, writer $10.50, until none`, and nothing else in it. Do the
same for any other witness in `tests/test_cli.py` that asserts the
`--stack` header.

**Criterion 1's witness** builds a git repository in `tmp_path` as the
mirror, with `_git` and `_rev_parse` (`tests/test_cli.py:36-52`). Each
commit makes `.saffron/gates/tests` an executable file. `P(x)` is a policy
with the gate `tests`, `test_paths` `tests/**`, `thread_env` `X: x` and
`spec_writer_prompt: prompts/writer.md`.

| commit | holds |
|---|---|
| `bare` | `P(bare)`, and `.claude/agents/spec-writer.md` with a frontmatter. No `prompts/writer.md`. |
| `unset` | `P(unset)` without the key, and `prompts/writer.md` with a frontmatter |
| `dir` | the key set to `prompts`, a directory |
| `plain` | the key set to `prompts/plain.md`, which reads `plain` with no frontmatter |
| `broken` | `P(broken)` plus the line `nope: 1`, which the policy forbids |
| `base` | `P(base)`. `prompts/writer.md` is `---\nname: w\n---\nat base\n---\nsecond half\n`, and `.saffron/specs/SY-1-x.md` reads `at base`. |
| head | the gate `lint`, `X: head`, `spec/**` and the key `prompts/head.md`. `prompts/writer.md` reads `head`, and the spec file `at head`. |

The `repo` passed holds its own `prompts/writer.md`, reading `in the
operator's repository`. Open a `Ledger` in `tmp_path`. Upsert
`https://github.com/o/other.git` first, then the pinned url, so its repo
id is 2. Replace these through `monkeypatch`.

- `end_review.layer_fields` asserts it got that ledger. It returns `SY-2`
  on `saffron/SY-2` at `"2" * 40` for `k-top`, and `SY-1` on `saffron/SY-1`
  at `"1" * 40` for `k-bot`. It raises `KeyError` for any other key.
- `session.cell_up` records its keywords and adds its container to
  `created`. `session.cell_down` records its keywords.
  `runtime.remove_container` returns `None`.
- `implement.run_agent` declares `spec_id` and `timeout_s` as keywords
  with no default, and records each call. `SPEC_WRITER_TIMEOUT_S` equals
  `run_agent`'s own default of 3600. The double has none, so it still
  catches a binding that leaves `timeout_s` out.
- `spec_review.run_spec_writer` records its container, system prompt and
  prompt. It calls its agent once with that container and prompt, and
  returns a new `SpecWriterSession`.
- `qualify.qualify` records its arguments and returns a `Qualification`
  it keeps, whose groups are `k-bot` then `k-top`, both on `src/a.py`.
  Every group in this witness holds two `Finding`s of its own, with
  distinct claims.
- `cli._stack_mint` records its keywords. It returns a callable that
  creates a run and a task in the ledger, records its candidate and the
  task id, and returns the id.
- `follow_up.write_follow_ups` records its arguments. It calls `qualify`
  with the stack's layers and join, and appends `P1`, the `k-bot` group
  with the reason `p1`, to the `pooled` it got. It calls `write` for the
  `k-bot` group with `prompt k-bot`, then the `k-top` group with `prompt
  k-top`. It calls `mint` with its candidate, and records no spec text.
  It calls `emit("pooled line")`, and returns a list of that candidate.

`P0` pools a group on `k-old` and `src/z.py`. The stack is a join sentinel
and the layers `k-top` then `k-bot`. The witness pins `base`, builds the
callable with `cap_usd` 6.5 and `pooled` holding `P0`, and calls it with
`"7"`. It asserts:

- the one candidate returns. `write_follow_ups` got the `pooled` list
  itself, which is `P0` then `P1`. The `k-top` group, minted with no
  text, is not pooled on success. The output holds `pooled line`.
- `write_follow_ups` got the ledger, the stack and `"7"`. Its `mint`
  returned the id `_stack_mint`'s callable made for the candidate. It got
  the pinned mirror, repo id 2, `["tests/**"]` and 6.5. Its `specs_dir`
  lies under `out_dir` and holds `SY-1-x.md` reading `at base`.
- `_stack_mint` was built once, with the pinned base, `repo` and the
  ledger.
- `qualify` returned the kept `Qualification` to the double. Its
  positional arguments are the ledger, the layers and the join. Its
  keywords hold the pinned mirror, `repo`, `thread_env` `{"X": "base"}`,
  `["tests/**"]` and `{"tests": Path("/gates/.saffron/gates/tests")}`.
  Its `gates_dir` is `out_dir / "follow-ups" / "7"`, whose policy reads
  `X: base`. Its `created` is a set. Its `note`, called as
  `note("survived", False, "volume v survived")`, prints that detail.
- the calls ran up, writer, agent, down, twice over. Each `cell_up` got
  `"2" * 40`, `saffron/SY-2`, `repo`, the pinned mirror, `{"X": "base"}`
  and a `gates_dir` whose policy reads `X: base`.
- each writer call ran in its own `cell_up`'s container, with the system
  prompt exactly `at base\n---\nsecond half\n`, and the prompts in order.
  The agent's ids are `follow-up-SY-1` then `follow-up-SY-2`, each with
  `timeout_s` of `spec_review.SPEC_WRITER_TIMEOUT_S`. `write` returned
  each session the writer double made.

It then builds a fresh callable per case, with `pooled` holding `P0`
alone, and calls it:

| pinned sha, url or stack | the line holds |
|---|---|
| `bare` | `prompts/writer.md` |
| `unset` | `spec_writer_prompt` |
| `dir` | `not a regular file` |
| `plain` | `prompts/plain.md` |
| `broken` | `nope` |
| `"f" * 40` | `ffffffffffff` |
| `base`, url `https://github.com/o/none.git` | `o/none` |
| `base`, with `write_follow_ups` raising `RuntimeError("mint broke")` | `mint broke` |
| `base`, a stack whose one layer is `k-gone` | `k-gone` |

Each returns `[]`, leaves `pooled` as `P0`, and prints exactly one line.
That line starts `follow-ups: stopped, ` and holds the text above. No case
calls `cell_up`, `qualify` or the writer.

Next it drives a raise part-way, twice. `qualify` now returns five
groups, `A` to `E`, on distinct pairs of layer and file. `X[n]` is `X`
narrowed to its finding `n`, through `dataclasses.replace`. The
`write_follow_ups` double calls `qualify`. It appends `A` whole with the
reason `own a`, then `B[0]` with `moved`. It writes `B[1]`, mints the
candidate, and records a `follow_up` spec text on that task. It appends
`C[0]` with `own c`. In the first round it then writes `D` whole and
mints it, with no text. In the second it goes no further. Each round
then raises `RuntimeError("record broke")`. Each returns `[]`. `pooled`
is `P0`, `A` with `own a`, `B[0]` with `moved` and `C[0]` with `own c`.
Then come `C[1]`, `D` and `E`, each with `RuntimeError: record broke`.
The output holds the line `follow-ups: stopped, RuntimeError: record
broke`.

The first round alone fails every build listed below. The second alone
passes a group counted accepted at its mint, measured. It is there for
the raise before a group's session.

Last, it removes `out_dir` and calls a fresh callable with an empty
stack. That returns `[]`, calls and prints nothing, and leaves `out_dir`
absent.

These fail it, each measured:

- the prompt read from `repo`, or at the mirror's `HEAD`
- `.saffron/` exported at the mirror's `HEAD`
- the frontmatter kept, or the body split on every `---`
- a hard-coded `.claude/agents/spec-writer.md` in place of the key, or for
  an unset key
- the gates as host paths under the export
- `qualify` given no `test_paths`, no join, or a return it drops
- the writer's cell with an empty `thread_env`
- the cell seeded at the group's own layer's head, the last layer's, or
  the pinned `base_sha`
- one cell for every `write`
- no `timeout_s`, or `session.TURN_TIMEOUT_S`
- the agent's id as the bare origin id, the top layer's, or the batch key
- `write_follow_ups` given a fresh list in place of `pooled`
- the candidates dropped
- the guard narrowed to `ValueError` and `GitError`
- a message printed over several lines, or the type alone
- the repo id looked up by `repo`'s path
- `specs_dir` without `.saffron/`, or from `repo`
- `cap_usd` replaced by the writer ceiling
- `emit` or `note` silent
- the writer's session dropped
- no early return on an empty stack
- the mint built over another `repo`
- the prompt read inside `write`
- the export done at build time
- the export under `out_dir / "end-review"`
- a one-argument `note`
- nothing pooled on a raise
- already pooled judged by layer and file, which drops `C[1]`
- a finding already in `pooled` pooled again
- a group's remaining findings pooled as the whole group
- a group accepted at its mint, with or without a text
- accepted matched by the whole group, which the narrowed `B[1]` misses
- every group after the last accepted one
- the groups past the count of mints
- every group from the last one written
- unaccepted groups pooled on success too
- the `Qualification`'s `pool` read in place of its `groups`
- a pooled reason without the raise's type
- the line still reading `none written`

**Criterion 2's witness** follows `SA-0157`'s wiring witness, with
`_readiness_passes` and `_fake_batch_resolution`
(`tests/test_cli.py:2603-2640`). It sets `follow_up.WRITER_SHARE` to 0.125
through `monkeypatch`. `SA-0156` and `SA-0160` refuse the night at start when the policy at
the pinned base leaves `spec_review_prompt` or `spec_writer_prompt` unset.
So replace `git_mirror.export_saffron_dir` with a double that writes
`.saffron/policy.yaml` under its destination with both keys set, and
returns the destination, as their refusal witnesses do. It replaces
`cli._stack_follow_ups` with a recorder
that returns a sentinel. It replaces `cli.run_stack_batch` with a fake
that records its ledger, budget and keywords and returns `DRAINED`. It
runs `main` with `batch --stack --budget 42`, and asserts exit 0. The
output holds `budget $42.00, reserve $10.50, writer $5.25, until none`.
The fake got the budget 42.0, `reserve_usd` 10.5, `writer_usd` 5.25 and
the sentinel as `follow_ups`. The recorder was called once. It got the
pinned base `_readiness_passes` returns, the resolved `--repo`, the fake's
ledger, `main`'s `out_dir`, `cap_usd` 5.25 and an empty list as `pooled`.
No other callable at this tree base takes that list, so the witness can
assert no identity beyond it. `SA-0174`'s witness asserts that
`_stack_finish` gets the same object.
It then fails readiness as `SA-0144`'s witness does, and runs `main`
again. The recorder is not called, and the fake gets `follow_ups=None`.

0.125 keeps the writer's figure apart from the reserve's. A share bound
at import, or `RESERVE_SHARE` in its place, gives 10.5. The budget less
the reserve, times the share, gives 3.94.

These fail it, unmeasured, since `SA-0144`'s `--stack` path is not at
`68892367`:

- `WRITER_SHARE` imported by name, or `RESERVE_SHARE` in its place
- the budget less the writer share passed as the budget
- a `cap_usd` of the whole budget
- the callable built before readiness, on a base not yet pinned
- a callable built over another ledger

These fail it, measured on `_print_batch_plan` alone:

- no writer figure in the header
- the reserve printed as the writer figure

**How the lists were measured.** A throwaway prototype ran on 2026-09-24
at `68892367`, on the host's git. It stood in for the chain's names as
this spec states them. Those were `StackReview`, `LayerReview`,
`LayerFields`, `layer_fields` and `layer_cell`. They were
`FollowUpGroup`, `Qualification` and `qualify`. They were
`SpecWriterSession`, `run_spec_writer` and `SPEC_WRITER_TIMEOUT_S` at
3600. They were `Pooled`, `write_follow_ups` and
`WRITER_SHARE`. Last were `_stack_mint` and `Policy.spec_writer_prompt`. Its `layer_cell`
called the real `cell_up` and `cell_down` names. It ran the real
`export_saffron_dir`, `load_policy`, `file_at`, `_FRONTMATTER` and
`resolve_repo_id`. It built `_stack_follow_ups`, the header and criterion
1's witness. It ran again after the first spec review, with the
`note` shape, the pooling on a raise and the timeout of 3600. It ran a
third time after the second, with `pooled` passed through and accepted
read from the spec text. It ran a fourth time with pooling judged by
findings. That run stood in for `record_spec_text` and
`spec_text` too. The right build passed. Each wrong version listed as measured
was applied as a text edit, and each failed the witness. The first right
build printed a `PolicyError` over four lines, so the line joins the
message's whitespace.

**What the witnesses leave undriven.**

- A raise from `layer_cell`, or from `run_spec_writer`, inside `write`.
  `write_follow_ups` pools that group (`SA-0161`).
- A `created` name that survives its probe cell. `qualify`'s cells report
  it through `note`, which prints it.
- `emit` beyond one line.

**The `prose` gate** reads every new comment and docstring
(`.saffron/gates/prose.py`). Write no em dash, semicolon, contraction,
perfect tense, hedge or sentence over 25 words. Keep each docstring within
ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** No path here is in `elevate_on`, so `size` is advisory at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). The
prototype, formatted by `ruff format`, measured 1602 changed tokens with
`size_gate` itself after the second review's alignment. `saffron/cli.py`
took 422, and criterion 1's witness 1180, of which about 45 are imports
`tests/test_cli.py` already has or a stand-in needs. A sketch of
criterion 2's witness measured 157. Its export double adds about 40, and
the `_batch` wiring and the edits to other fakes about 70, estimated.
That is about 1825 tokens, 61% of the ceiling. Keep the raise cases in one table.
