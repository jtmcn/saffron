---
id: SA-0353
title: A writer's draft reaches the finish unparsed, because nothing reads it inside its own session
type: bug
priority: 2
depends_on: [SA-0339]
estimated_lines: 157
estimate_measured: true
touches:
  - saffron/spec_review.py
  - saffron/cli.py
  - tests/test_spec_review.py
  - tests/test_cli.py
  - tests/test_follow_up.py
  - tests/test_batch.py
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
  - saffron/intake.py
  - saffron/finish.py
  - saffron/follow_up.py
  - saffron/draft.py
  - saffron/batch.py
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/cell/**
  - saffron/repos/**
  - tests/test_draft.py
  - tests/test_finish.py
budget_usd: 46
max_attempts: 3
max_turns: 240
risk: standard
acceptance:
  - claim: >-
      `run_spec_writer` takes a required `faults` callable, returning a
      `DraftFaults`, and a required `emit`. Once a turn's `spec` field
      validates, it calls `faults` on that text. A text with no fault lines
      ends the session as today. A text with fault lines goes back to the
      same session as one more turn. That turn resumes the session's latest
      id, and its prompt is `SPEC_WRITER_SEND_BACK_PROMPT` then every line,
      one per line. It runs under `SPEC_WRITER_FORMAT` with
      `SPEC_WRITER_SEND_BACK_BUDGET_USD` as its budget. Its `last_cost_usd`
      is the last turn's cost capped at that budget. Its validated text is
      the session's text, and its cost joins the session's. At most
      `SPEC_WRITER_SEND_BACKS` such turns run, read at call time, and the
      default is 1. `SPEC_WRITER_SESSION_USD` counts every send-back turn's
      budget. The witness drives a text the first extraction returns and
      one the re-ask returns, a text with no faults, a text whose faults
      persist under the default, two send backs with the bound patched to
      2, and a last cost both under and over the budget.
    witness: tests/test_spec_review.py::test_a_draft_with_faults_goes_back_to_the_same_session_naming_each_line
    wrong_versions:
      - The send-back turn starts a fresh session, with no `resume`.
      - The send-back prompt names only the first line `faults` returned.
      - The send-back turn runs under the extraction's budget.
      - The send-back turn drops `output_format` from its options.
      - The session returns the text `faults` found faults in rather than the send-back turn's text.
      - One more send-back turn runs than the bound allows.
      - One send-back turn runs whatever `SPEC_WRITER_SEND_BACKS` says.
      - The send-back turn's cost is left out of the session's.
      - A text the re-ask returns ends the session without reaching `faults`.
      - "`faults` reads the last send-back turn's text too, though no send back remains."
      - The send-back's `last_cost_usd` is always the send-back budget.
      - The send-back's `last_cost_usd` is the last turn's cost with no cap.
      - "`SPEC_WRITER_SESSION_USD` stays the first turn plus one extraction turn."
  - claim: >-
      A send-back turn that fails keeps the last text that parsed. The
      failures are an answer that is not the schema, a rate-limited turn,
      and a turn that raised. When the first draft parsed, the session
      returns it with no error and no reset. It emits one line naming the
      failure, then each fault line. When no text parsed, the session ends
      as a failed extraction turn does today. That is the schema error, the
      reset, or the raised error, each with no text. The witness drives all
      three failures both ways.
    witness: tests/test_spec_review.py::test_a_failed_send_back_keeps_the_last_draft_that_parsed_and_says_why
    wrong_versions:
      - A failed send-back discards the draft that parsed and ends with its error.
      - A failed send-back keeps the draft and also sets the error.
      - A rate-limited send-back keeps the draft and its reset.
      - A failed send-back emits nothing.
      - A failed send-back emits its failure but not the faults.
      - A failed send-back emits the faults but not its failure.
      - A failed send-back returns a first draft that did not parse.
  - claim: >-
      `spec_review.draft_faults` reads a draft with `intake.parse_spec`, then
      SA-0338's `intake.refuse_inline_mutants`. A draft either refuses comes
      back with `parsed` false and one line carrying intake's own error, and
      nothing is judged. The witness drives four refusals. One is a
      `wrong_versions` entry written as an object, the shape SA-0338's first
      draft took. One is a text with no frontmatter. One declares both
      `acceptance:` and a `## Acceptance criteria` section, which only
      `parse_spec` refuses. One declares a `mutant:` inline.
    witness: tests/test_spec_review.py::test_a_draft_intake_refuses_is_named_by_intakes_own_error_and_reaches_no_gate
    wrong_versions:
      - The draft is parsed by a copy that loads the YAML and validates `Spec` alone.
      - An inline mutant passes `draft_faults`.
      - Only a pydantic `ValidationError` is caught, so a draft with no frontmatter raises.
      - The judgement still runs on a draft that does not parse.
      - A refused draft comes back with `parsed` true.
  - claim: >-
      A draft that parses goes to the injected `judge` at the given path, or
      at `.saffron/specs/<id>.md` when the path is `None`. It comes back
      with `parsed` true and every line `judge` returns, in order, or none
      when it returns none. With no `judge`, a draft that parses has no
      fault lines. The witness drives both path forms, a judge with two
      lines, a judge with none, and no judge.
    witness: tests/test_spec_review.py::test_a_draft_the_form_gates_fail_is_named_line_by_line_at_its_path
    wrong_versions:
      - Only the first line `judge` returned comes back.
      - A `None` path reaches `judge` as a fixed name rather than the draft's own id.
  - claim: >-
      A `judge` that raises is the gate's failure and never the draft's.
      `draft_faults` then returns the draft as parsed with no fault line, so
      nothing goes back to the writer. It emits one line naming the raised
      error.
    witness: tests/test_spec_review.py::test_a_form_judgement_that_raises_sends_nothing_back_and_says_so
    wrong_versions:
      - The raise escapes `draft_faults`.
      - The raise returns no line and emits nothing.
      - The raised error goes back to the writer as a fault.
  - claim: >-
      `cli._draft_faults` judges a draft with `finish.judge_draft`, atop the
      head it is given, through `_finish_verify`. The policy is narrowed to
      the gates the repo declares `form: true`, read from the policy, and
      the core gates still run. Its lines are `judge_draft`'s own rendering
      of each new failure. A policy that declares no form gate passes no
      `judge`, so a draft that parses has no fault line and one that does
      not still gets intake's line. The witness drives a policy declaring
      two form gates beside one that is not, and one declaring no form gate,
      with a draft that parses and one that does not.
    witness: tests/test_cli.py::test_a_writers_draft_is_judged_atop_its_head_by_the_repos_form_gates
    wrong_versions:
      - The judgement runs every declared gate.
      - The narrowing names one gate by a literal, such as `prose`.
      - The draft is committed atop `pinned.base_sha` rather than the head it was given.
      - A policy with no form gate still judges the draft.
      - A policy with form gates passes no `judge`.
      - "`_draft_faults` returns `lambda text: []`, a callable that finds no fault."
  - claim: >-
      Each of the three writer adapters hands its session `_draft_faults`
      for the tree its cell opened at, and `emit=print`. `_stack_revise`
      passes its layer's fetched head and the queued file's path.
      `_draft_adapters`'s `write` passes `pinned.base_sha` and no path.
      `_stack_follow_ups`'s `write` passes the top layer's graded head and no
      path. Each passes its own pinned base and the policy it read. The
      witness drives all three adapters, the revision with a layer, and reads
      all four arguments from each.
    witness: tests/test_cli.py::test_every_writer_adapter_hands_its_session_the_faults_of_its_own_head
    wrong_versions:
      - The revision passes no path, so its draft is judged beside the queued file.
      - The revision judges at `pinned.base_sha` rather than its layer's head.
      - An adapter passes an empty `Policy` rather than the one it read.
      - The follow-up writer judges at `pinned.base_sha` rather than the top layer's head.
      - The follow-up writer hands its session a callable that finds no fault.
---

## Context

Backlog item **b-ffb930**. It cites `DESIGN.md` §3, whose §3.4 draft
chain is one of the three paths this spec reaches. Every line below was
read at `5539eeb5`, whose `saffron/` matches `9201e3be`.

**The incident.** Finish 67 drafted `SA-0338` as a follow-up. The first
draft failed to parse, because each of its four `wrong_versions` entries was
an object. The second draft failed the finishing suite's `prose` gate on six
hits, and the group was pooled. Both faults were found only after the writer
session ended.

**The writer session today.** `run_spec_writer` runs one tool-using turn,
then an extraction turn under `SPEC_WRITER_FORMAT`
(`saffron/spec_review.py:628-711`). A validated `spec` field returns at once
(`saffron/spec_review.py:760-770`). An answer that is not the schema gets one
re-ask, whose validated text also returns at once
(`saffron/spec_review.py:772-791`). Nothing reads the text before it leaves
the session.

**The schema cannot carry the type.** `_SpecWriterReply` has one field,
`spec: str` (`saffron/spec_review.py:531-539`). `SPEC_WRITER_FORMAT` is its
schema (`saffron/spec_review.py:544-547`).
`test_the_spec_writer_format_is_the_schema_of_one_string_field` pins that
shape (`tests/test_spec_review.py:1464-1491`). The frontmatter travels
inside that string, so `wrong_versions` is not a field of the schema at all.
Only `intake.Criterion` types it, as `list[str]` (`saffron/intake.py:146`).
Measured at the base: `SPEC_WRITER_FORMAT`'s schema names one property,
`spec`, of type `string`. Intake's loader then refuses an object entry with
`Input should be a valid string`. The SDK pin is 0.2.142
(`images/cell-base.python.Dockerfile:33`). Its CLI rejects a value its schema
refuses, measured in `docs/evidence/2026-09-23-structured-output-spike.md`
(Q3). That holds only for the schema it is given, and this one accepts any
string.

**Where each draft is read later.** The follow-up loop parses a draft with
`intake.parse_spec`, then judges it with the finishing suite
(`saffron/follow_up.py:413-451`). A failure there opens a fresh `write`
call, a new session, once (`saffron/follow_up.py:291-318`). The judge is
`finish.judge_draft`, which commits the text atop a head in a worktree
(`saffron/finish.py:257-293`). It runs the verify `_finish_verify` builds
(`saffron/cli.py:1049-1076`). That verify loads the policy from the pinned
base's export, builds `finish.finish_suite` over it and runs
`package_phase.reverify`. `reverify` runs both suites in gate-only cells,
never host-side, and keeps only new failures
(`saffron/phases/package.py:524-565`). The suite runs the core gates beside
the declared ones (`saffron/gates/suite.py:203-210`).

**Why the gates cannot run in the writer's own cell.** The writer's cell is
a critic cell (`saffron/end_review.py:783-803`). `DESIGN.md` §5.5 forbids a
gate there, since a gate executes model-authored code as root where the
session then re-execs its runner (`DESIGN.md:1247`). This repo's `prose`
gate does execute tree code. It loads `ontology/spans.py` from the tree
under judgement (`.saffron/gates/prose.py:432-438`). So the judgement goes
to gate-only cells through `judge_draft`, as the follow-up's own judge does.

**Which gates.** Core names no repo-defined gate (`DESIGN.md` §2.1). A repo
marks a gate `form: true` (`saffron/repos/policy.py:63`), and REBUT's
`form_only` already reads that flag rather than a name
(`saffron/phases/rebut.py:200-218`, its rule at `:208-209`). A policy cannot
declare a core gate's name (`saffron/repos/policy.py:220-226`). This repo
declares `format`, `lint` and `prose` as form gates (`.saffron/policy.yaml`).

**What a failed writer session costs a revision.** A revision whose writer
returns an error sets its task `GATE_ERROR`, misses its spec and raises
(`saffron/batch.py:883-892`). So a send-back that discards a draft that
parsed would turn a revision that once proceeded into an abort.

**Inline mutants.** SA-0338 keeps its inline-mutant refusal out of
`parse_spec`. It adds `refuse_inline_mutants(spec)`, which raises
`InlineMutantError`, a `SpecError` (SA-0338's spec, line 127). SA-0338 is
this spec's ancestor, so the function exists at this cell's base.

**The session's ceiling.** `SPEC_WRITER_SESSION_USD` is the first turn plus
one extraction turn (`saffron/spec_review.py:573-575`). The follow-up
sub-cap reads it (`saffron/follow_up.py:301`, `:330`), and so does a
revision's budget test (`saffron/batch.py:836-840`).

**The three callers.** Every `run_spec_writer` call sits in `saffron/cli.py`.
`_stack_revise` calls it at `saffron/cli.py:1442`. Its head comes from
`_stack_head` (`saffron/cli.py:1394`), and its policy from
`_spec_review_policy` (`saffron/cli.py:1400`). `_draft_adapters`'s `write`
calls it at `saffron/cli.py:1551`, seeded at `pinned.base_sha`.
`_stack_follow_ups`'s `write` calls it at `saffron/cli.py:1732`, in a cell at
`top.head` (`saffron/cli.py:1724-1731`), with the policy read at
`saffron/cli.py:1681`.

## Problem

1. **`DraftFaults`.** A frozen dataclass in `saffron/spec_review.py` with
   `parsed: bool` and `lines: tuple[str, ...]`.
2. **The send-back turn.** `run_spec_writer` gains two required keywords,
   `faults: Callable[[str], DraftFaults]` and
   `emit: Callable[[str], None]`. Wherever a validated `spec` field would
   end the session, call `faults` on the text first. Fault lines mean the
   draft goes back. Run one more turn on the same session, resumed at its
   latest id, under the extraction's options with `max_budget_usd` set to
   `SPEC_WRITER_SEND_BACK_BUDGET_USD`. Pass
   `last_cost_usd=min(<the last turn's cost_usd_est>, SPEC_WRITER_SEND_BACK_BUDGET_USD)`,
   as the extraction turns cap theirs. Its prompt is
   `SPEC_WRITER_SEND_BACK_PROMPT`, then every line, one per line. Read its
   answer the way the extraction's is read. A valid answer becomes the
   text, and `faults` reads it again while send backs remain.
3. **A failed send-back.** Keep the last text whose `DraftFaults` said
   `parsed`. When the send-back turn fails and such a text exists, return it
   with no error and no reset. Emit one line naming the failure, then each
   fault line. With no such text, end the session as the extraction turn's
   own failure handling does today.
4. **The constants.** Add `SPEC_WRITER_SEND_BACKS = 1`, the operator's
   bound, read at call time so a patched value holds. Add
   `SPEC_WRITER_SEND_BACK_BUDGET_USD = 3.0`, marked reasoned and unmeasured,
   twice the extraction turn's. Add `SPEC_WRITER_SEND_BACK_PROMPT`, one or
   two sentences that say the host found faults in the spec. They ask the
   writer to fix every line below and send the whole spec again. Keep it
   free of any repo path or tool name. Make `SPEC_WRITER_SESSION_USD` the
   first turn, one extraction turn and `SPEC_WRITER_SEND_BACKS` times the
   send-back budget, which is $21.50 today.
5. **`spec_review.draft_faults(text, *, path, judge, emit)`.** Call
   `intake.parse_spec`, then `intake.refuse_inline_mutants` on its spec. A
   `SpecError` from either returns `parsed` false and one line carrying its
   message, and nothing is judged. Otherwise, with `judge` `None`, return
   `parsed` true and no line. With a `judge`, call it with `path`, or
   `.saffron/specs/<id>.md` beside a `None` path, and the text. Return its
   lines in order. A raise from `judge` returns no line and calls `emit` once
   with the raised error.
6. **`cli._draft_faults(*, pinned, repo, policy, head, workdir, path)`.**
   Read the form gates as the names in `policy.gates` whose declaration
   says `form`. Return `draft_faults` bound to `path`, `emit=print` and a
   `judge`, which is `None` when there is no form gate. The `judge` calls
   `finish.judge_draft(pinned.mirror, head, ...)` with
   `workdir=workdir / "tree"`. Its verify comes from `_finish_verify` with
   `gates_dir=workdir / "gates"` and `only=` the form gates.
   `_finish_verify` gains a keyword `only: Collection[str] | None = None`.
   Given names, it narrows the loaded policy's `gates` to those names before
   `finish.finish_suite`. Core gates still run in that suite.
7. **The adapters.** Pass `faults=_draft_faults(...)` and `emit=print` at
   each of the three calls above. Use the head and policy each adapter
   already holds, and a workdir under its own `out_dir` that no other judge
   uses. A revision passes `.saffron/specs/<the queued file's name>`. A draft
   and a follow-up pass no path.
8. **Two sentences that become false.** The comment at
   `saffron/spec_review.py:573-574` says a session is its first turn plus
   one extraction turn. The `SpecWriterSession` docstring at
   `saffron/spec_review.py:590-591` says `text` is the extraction turn's
   field. Make each say what the code now does.

## Out of scope

- The re-ask stays outside `SPEC_WRITER_SESSION_USD`, as today.
- The follow-up loop keeps its own parse, judge and one resend
  (`saffron/follow_up.py:413-451`). A follow-up still passes the whole
  finishing suite before it is minted (ADR 7).
- Restructuring the writer's reply so the schema types each frontmatter
  field. The reply stays one string.
- b-4a9207's citation check and its one-line finishing-layer edit.
  b-cc87b1's `specs:` update.

## Notes for the agent

**`SA-0339`, the parent, and `SA-0338`.** Both edit `saffron/cli.py`, and
`SA-0338` edits `tests/test_cli.py` and `tests/test_follow_up.py`. The
numbers above were read before them. Find each line by its text. Find
`refuse_inline_mutants` in `saffron/intake.py` by the name SA-0338's spec
gives it. `saffron/intake.py` is forbidden here.

**Edit or new.** The send-back turn, `DraftFaults`, `draft_faults`,
`_draft_faults` and the `only` keyword are new code. So no criterion
declares a mutant, and `witness` reports an honest `skip` on each.

**Prose limits.** A docstring stays within ten lines and a comment within
two. New comments take no hedge, so write "a send-back turn reads files" as
a fact. The `prose` gate reads `saffron/` docstrings and comments.

**The witnesses.** Use plain `def`s and never a parametrised test. Import
every name this spec adds inside the test function, never at module scope,
so the reverted run fails rather than erroring at collection.

- In `tests/test_spec_review.py`, script turns with `_Agent`, `_draft` and
  `_write_extract`. Give the send-back turn its own session id and cost, so
  the latest id and the summed cost show. Give the extraction a cost above
  the send-back budget in one case and below it in another, so the cap on
  `last_cost_usd` shows. `_write_extract_options()` with the send-back
  budget is the send-back turn's expected options. A `faults` double that
  records what it reads in a closure list type-checks. On the prototype, an
  attribute set on the function failed `types`.
- Criterion 2's three failures are `_write_extract` with a non-schema
  value, `_write_extract(status="rejected", resets_at=...)`, and `_KILLED`.
  Drive each with a `faults` that says `parsed` true, then with one that
  says `parsed` false.
- The parse-only refusal in criterion 3 is `parse_spec`'s own check at
  `saffron/intake.py:350-356`. A copy that validates `Spec` alone accepts
  it.
- In `tests/test_cli.py`, criterion 6 builds a small git mirror whose
  `.saffron/policy.yaml` declares two `form: true` gates and one without,
  with an executable for each. Give one form gate a name no repo here
  declares, so a literal cannot pass. Use `_git`, `_rev_parse` and
  `_exec_file`. Monkeypatch `package_phase.reverify` to record its keyword
  arguments and return one `NewFailure`. Read the parent of `packaged_sha`
  and the draft's blob at it from the mirror, before the ref goes. `_git`
  strips its output.
- Criterion 7 monkeypatches `cli._draft_faults` with a recorder and
  `spec_review.run_spec_writer` with a fake taking `faults` and `emit`.
  Drive `_stack_revise` and `_draft_adapters` over `_spec_session_rig`. Give
  the revision the rig's `SY-7` candidate as its layer, whose fetch the rig
  fakes to `"d" * 40`, so its head differs from `pinned.base_sha`. Drive
  `_stack_follow_ups` over `_follow_ups_mirror`, as
  `test_a_stack_batchs_follow_up_writer_is_seeded_at_the_top_head_the_end_review_graded`
  does, with a `write_follow_ups` fake that calls `write` once. Both
  fixtures write into `tmp_path` directly, so give each its own new
  subdirectory, made before the call. Assert the layer's record key is not
  `None`, as that test does. On the prototype, `types` failed the test file
  without it.

**Existing tests this changes.** A prototype of this change failed eleven
tests across `tests/test_spec_review.py`, `tests/test_cli.py`,
`tests/test_follow_up.py` and `tests/test_batch.py`. No other test file
failed.

- `_run_writer` in `tests/test_spec_review.py` passes a `faults` that finds
  nothing and an `emit`. That fixes the three writer tests that call it.
  The pin `SPEC_WRITER_SESSION_USD == 18.5` at `tests/test_spec_review.py:1616`
  becomes 21.5.
- The four `_fake_run_spec_writer` fakes in `tests/test_cli.py` take
  `faults` and `emit`.
- `test_a_spec_revision_fills_cores_writer_prompt_from_its_base_policy_in_a_cell_at_its_predecessors_head`
  and `test_a_review_reads_a_recorded_text_and_a_revision_starts_from_the_queued_file`
  run the real writer over texts that do not parse. Patch
  `spec_review.draft_faults` to return a parsed `DraftFaults` with no line in
  each.
- `test_a_sub_cap_of_18_dollars_writes_none_and_37_writes_two` in
  `tests/test_follow_up.py` pins the shares 0.18 and 0.37, below one and
  two $18.50 sessions. The prototype passed with 0.21 and 0.43, renamed to
  `test_a_sub_cap_of_21_dollars_writes_none_and_43_writes_two`.
- `test_a_revision_waits_on_a_rate_limit_and_stops_on_an_error_a_raise_or_the_budget`
  and `test_each_revision_is_an_attempt_and_a_spec_text_on_its_specs_task`
  in `tests/test_batch.py` pin `budget_usd=100.0` (`tests/test_batch.py:4740`,
  `:4812`). Both thresholds sit one session cost above the spend. The
  prototype passed both at 103.0, and failed both at 101.0, 102.0 and 104.0.

**Every new test fails with the source reverted.** On the prototype, all
seven witnesses failed with `saffron/spec_review.py` and `saffron/cli.py`
reverted. The prototype stood in a stub for SA-0338's
`refuse_inline_mutants`. The `prose`, `structure`, `types`, `dead`, `lint`
and `format` gates showed no new failure in `saffron/`.

**Size.** The prototype measured 626 changed tokens by `size_gate`, against
the `bug` ceiling of 1300, and 1312 more under the test paths. The stub is
left out of that count. `estimated_lines` is the first figure over four,
rounded up.
