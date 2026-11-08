---
id: SA-0353
title: A writer's draft reaches the finish unparsed, because nothing reads it inside its own session
type: bug
priority: 2
depends_on: [SA-0339]
estimated_lines: 173
estimate_measured: true
touches:
  - saffron/spec_review.py
  - saffron/cli.py
  - saffron/agents/prompts/turns/spec-writer-send-back.md
  - tests/test_spec_review.py
  - tests/test_cli.py
  - tests/test_context.py
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
  - saffron/agents/*.py
  - saffron/agents/prompts/*.md
  - saffron/cell/**
  - saffron/repos/**
  - tests/test_draft.py
  - tests/test_finish.py
budget_usd: 60
max_attempts: 3
max_turns: 270
risk: standard
acceptance:
  - claim: >-
      `run_spec_writer` takes a required `faults` callable, returning a
      `DraftFaults`, and a required `emit`. Once a turn's `spec` field
      validates, it calls `faults` on that text. A text with no fault lines
      ends the session as today. A text with fault lines goes back to the
      same session as a send-back of two turns. The first is a work turn.
      It resumes the session's latest id with tools and no `output_format`,
      and its budget is `SPEC_WRITER_SEND_BACK_BUDGET_USD`. Its prompt is
      `SPEC_WRITER_SEND_BACK_PROMPT` then every fault line, one per line.
      The second is the existing extraction turn, with
      `SPEC_WRITER_EXTRACT_PROMPT` and its options unchanged, resumed at the
      work turn's id. Each turn's `last_cost_usd` is the turn before it
      capped at its own budget. Every turn's cost and turns join the
      session's. `faults` also reads the text a send-back returns. The
      session's text is then the newest text that parsed, or the newest
      text of all when none parsed. At most `SPEC_WRITER_SEND_BACKS`
      send-backs run, read at call time, and the default is 1.
      `SPEC_WRITER_SESSION_USD` is the first turn and one extraction turn,
      plus each send-back's work and extraction budgets, $23.00 today. The
      witness drives a text the first extraction returns and one the re-ask
      returns, a text with no faults, faults that persist, a returned text
      that does not parse with and without an earlier one that did, two
      send-backs with the bound patched to 2, and last costs both under and
      over each cap.
    witness: tests/test_spec_review.py::test_a_draft_with_faults_goes_back_to_the_same_session_naming_each_line
    wrong_versions:
      - The work turn starts a fresh session, with no `resume`.
      - The work prompt names only the first fault line.
      - A send-back is one turn under `output_format`, so it does work and answers at once.
      - The work turn runs under the extraction's budget.
      - The send-back's extraction turn sends a prompt other than `SPEC_WRITER_EXTRACT_PROMPT`.
      - The send-back's extraction turn resumes the id before the work turn.
      - A `last_cost_usd` is always its turn's budget.
      - A `last_cost_usd` is the turn before it with no cap.
      - The session returns the text `faults` found faults in rather than the send-back's text.
      - One more send-back runs than the bound allows.
      - One send-back runs whatever `SPEC_WRITER_SEND_BACKS` says.
      - The work turn's cost is left out of the session's.
      - A text the re-ask returns ends the session without reaching `faults`.
      - The text the last send-back returns is never read by `faults`.
      - A returned text that does not parse replaces one that did.
      - "`SPEC_WRITER_SESSION_USD` leaves out the send-back's extraction budget."
  - claim: >-
      A send-back that fails ends the send-backs and still ends the session
      with a text, no error and no reset. A failure is the work turn
      rate-limited or raised, or its extraction not the schema,
      rate-limited or raised. The session's text follows criterion 1's
      rule, the newest text that parsed or else the newest text. It emits
      one line naming the failure, then each fault line. Each failing turn's
      cost and turns join the session's. The witness drives all five
      failures, after a first draft that parsed and after one that did not.
      With the bound patched to 2 it drives a first draft that parses, a
      first send-back whose text parses with faults, and a second send-back
      that fails. The first send-back's text survives.
    witness: tests/test_spec_review.py::test_a_failed_send_back_keeps_the_last_draft_that_parsed_and_says_why
    wrong_versions:
      - A failed send-back ends the session with its error and no text.
      - A failed send-back emits nothing.
      - A failed send-back emits its failure but not the faults.
      - A failed send-back emits the faults but not its failure.
      - A failed send-back keeps the first draft rather than the newest that parsed.
      - A failed send-back's cost and turns are left out of the session's.
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
read at `1742e79f`, whose `saffron/` matches `9201e3be`.

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

**Principle 18.** Structured output is a separate, tool-less turn
(`DESIGN.md:1865`). The host resumes the session with a prompt that forbids
further action (`DESIGN.md:850`, §5.3). ADR 7 says a spec writer keeps
principle 18 (`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:113-116`).
So a send-back cannot be one turn under `output_format`. It is a work turn
with tools, then the existing extraction turn.

**The schema cannot carry the type.** `_SpecWriterReply` has one field,
`spec: str` (`saffron/spec_review.py:531-539`). `SPEC_WRITER_FORMAT` is its
schema (`saffron/spec_review.py:544-547`).
`test_the_spec_writer_format_is_the_schema_of_one_string_field` pins that
shape (`tests/test_spec_review.py:1464-1491`). The frontmatter travels
inside that string, so `wrong_versions` is not a field of the schema at all.
Only `intake.Criterion` types it, as `list[str]` (`saffron/intake.py:156`).
Measured at the base: `SPEC_WRITER_FORMAT`'s schema names one property,
`spec`, of type `string`. Intake's loader then refuses an object entry with
`Input should be a valid string`. The SDK pin is 0.2.142
(`images/cell-base.python.Dockerfile:33`). Its CLI rejects a value its schema
refuses, measured in `docs/evidence/2026-09-23-structured-output-spike.md`
(Q3). That holds only for the schema it is given, and this one accepts any
string.

**Where each draft is read later.** The follow-up loop parses a draft with
`intake.parse_spec`, then judges it with the finishing suite
(`saffron/follow_up.py:406-443`). A failure there opens a fresh `write`
call, a new session, once (`saffron/follow_up.py:284-311`). The judge is
`finish.judge_draft`, which commits the text atop a head in a worktree
(`saffron/finish.py:257-293`). It runs the verify `_finish_verify` builds
(`saffron/cli.py:1073-1100`). That verify loads the policy from the pinned
base's export, builds `finish.finish_suite` over it and runs
`package_phase.reverify`. `reverify` runs both suites in gate-only cells,
never host-side, and keeps only new failures
(`saffron/phases/package.py:524-565`). The suite runs the core gates beside
the declared ones (`saffron/gates/suite.py:203-210`).

**Why the gates cannot run in the writer's own cell.** The writer's cell is
a critic cell (`saffron/end_review.py:783-803`). `DESIGN.md` §5.5 forbids a
gate there, since a gate executes model-authored code as root where the
session then re-execs its runner (`DESIGN.md:1254`). This repo's `prose`
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
(`saffron/batch.py:883-892`). So a send-back must never turn a session that
produced a text into one that ends with an error.

**Inline mutants.** At `1742e79f`, `saffron/intake.py` holds no
`refuse_inline_mutants`. SA-0338 adds it. Its spec keeps that refusal out of
`parse_spec` and has the function raise `InlineMutantError`, a `SpecError`
(SA-0338's spec, line 127). This spec declares `depends_on: [SA-0339]`, and
SA-0339 depends on SA-0338. So the cell's base includes SA-0338's code, and
the function exists there.

**Turn prompts.** A turn prompt lives in `saffron/agents/prompts/turns/` and
loads through `context.turn_prompt` (`saffron/agents/context.py:283-298`).
`prompt_sha` digests every file under the prompts tree
(`saffron/agents/context.py:333-348`), so a prompt there is recorded with
each task. `test_every_turn_prompt_file_is_loaded_by_something` holds the
directory's files equal to the keys of `TURN_PROMPTS`
(`tests/test_context.py:688-708`).

**The session's ceiling.** `SPEC_WRITER_SESSION_USD` is the first turn plus
one extraction turn (`saffron/spec_review.py:573-575`). The follow-up
sub-cap reads it (`saffron/follow_up.py:294`, `:323`), and so does a
revision's budget test (`saffron/batch.py:836-840`). Both read the module
attribute at call time.

**The three callers.** Every `run_spec_writer` call sits in `saffron/cli.py`.
`_stack_revise` calls it at `saffron/cli.py:1466`. Its head comes from
`_stack_head` (`saffron/cli.py:1418`), and its policy from
`_spec_review_policy` (`saffron/cli.py:1424`). `_draft_adapters`'s `write`
calls it at `saffron/cli.py:1579`, seeded at `pinned.base_sha`.
`_stack_follow_ups`'s `write` calls it at `saffron/cli.py:1760`, in a cell at
`top.head` (`saffron/cli.py:1752-1759`), with the policy read at
`saffron/cli.py:1709`.

## Problem

1. **`DraftFaults`.** A frozen dataclass in `saffron/spec_review.py` with
   `parsed: bool` and `lines: tuple[str, ...]`.
2. **The send-back.** `run_spec_writer` gains two required keywords,
   `faults: Callable[[str], DraftFaults]` and
   `emit: Callable[[str], None]`. Wherever a validated `spec` field would
   end the session, call `faults` on the text first. Fault lines mean the
   draft goes back, as two turns on the same session.
   - The work turn resumes the session's latest id under the first turn's
     options, with `max_budget_usd` set to
     `SPEC_WRITER_SEND_BACK_BUDGET_USD` and no `output_format`. Its prompt
     is `SPEC_WRITER_SEND_BACK_PROMPT`, then every fault line, one per line.
     Pass
     `last_cost_usd=min(<the last turn's cost_usd_est>, SPEC_WRITER_SEND_BACK_BUDGET_USD)`.
   - The extraction turn sends `SPEC_WRITER_EXTRACT_PROMPT` under the
     extraction's options, unchanged. It resumes at the work turn's id, with
     `last_cost_usd=min(<the work turn's cost_usd_est>, SPEC_WRITER_EXTRACT_BUDGET_USD)`.
     Read its answer the way the first extraction's is read. It gets no
     re-ask.
   - Call `faults` on each text a send-back returns. Keep the newest text
     whose `DraftFaults` said `parsed`. Run the next send-back while fault
     lines remain and the bound allows.
3. **The session's text.** It is the newest text that parsed. With no text
   that parsed, it is the newest text of all. The session sets no error and
   no reset.
4. **A failed send-back.** A failure is either turn rate-limited or raised,
   or the extraction answer not the schema. It ends the send-backs. Emit one
   line naming the failure, then each fault line of the newest text read.
   The session's text follows item 3. Each failing turn's cost and turns
   still join the session's.
5. **The constants and the prompt.**
   - `SPEC_WRITER_SEND_BACKS = 1`, the operator's bound, read at call time so
     a patched value holds.
   - `SPEC_WRITER_SEND_BACK_BUDGET_USD = 3.0`, marked reasoned and
     unmeasured, twice the extraction turn's. It is the work turn's budget.
   - `SPEC_WRITER_SESSION_USD` becomes `SPEC_WRITER_BUDGET_USD` plus
     `SPEC_WRITER_EXTRACT_BUDGET_USD`, plus `SPEC_WRITER_SEND_BACKS` times
     the send-back budget plus the extraction budget. That is $23.00 today.
   - `SPEC_WRITER_SEND_BACK_PROMPT` loads once at import through
     `context.turn_prompt("spec-writer-send-back")`, from the new file
     `saffron/agents/prompts/turns/spec-writer-send-back.md`. The file holds
     one or two sentences. They say the host found the faults below, and
     ask the writer to fix every one in the spec. Keep it free of any repo path
     or tool name. Add it to `TURN_PROMPTS` in `tests/test_context.py`.
6. **`spec_review.draft_faults(text, *, path, judge, emit)`.** Call
   `intake.parse_spec`, then `intake.refuse_inline_mutants` on its spec. A
   `SpecError` from either returns `parsed` false and one line carrying its
   message, and nothing is judged. Otherwise, with `judge` `None`, return
   `parsed` true and no line. With a `judge`, call it with `path`, or
   `.saffron/specs/<id>.md` beside a `None` path, and the text. Return its
   lines in order. A raise from `judge` returns no line and calls `emit` once
   with the raised error.
7. **`cli._draft_faults(*, pinned, repo, policy, head, workdir, path)`.**
   Read the form gates as the names in `policy.gates` whose declaration
   says `form`. Return `draft_faults` bound to `path`, `emit=print` and a
   `judge`, which is `None` when there is no form gate. The `judge` calls
   `finish.judge_draft(pinned.mirror, head, ...)` with
   `workdir=workdir / "tree"`. Its verify comes from `_finish_verify` with
   `gates_dir=workdir / "gates"` and `only=` the form gates.
   `_finish_verify` gains a keyword `only: Collection[str] | None = None`.
   Given names, it narrows the loaded policy's `gates` to those names before
   `finish.finish_suite`. Core gates still run in that suite.
8. **The adapters.** Pass `faults=_draft_faults(...)` and `emit=print` at
   each of the three calls above. Use the head and policy each adapter
   already holds, and a workdir under its own `out_dir` that no other judge
   uses. A revision passes `.saffron/specs/<the queued file's name>`. A draft
   and a follow-up pass no path.
9. **Two sentences that become false.** The comment at
   `saffron/spec_review.py:573-574` says a session is its first turn plus
   one extraction turn. The `SpecWriterSession` docstring at
   `saffron/spec_review.py:590-591` says `text` is the extraction turn's
   field. Make each say what the code now does.

## Out of scope

- The first extraction's re-ask stays outside `SPEC_WRITER_SESSION_USD`, as
  today. It can add `SPEC_WRITER_EXTRACT_BUDGET_USD`, $1.50, to a session.
- The follow-up loop keeps its own parse, judge and one resend
  (`saffron/follow_up.py:406-443`). A follow-up still passes the whole
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

**Edit or new.** The send-back, `DraftFaults`, `draft_faults`,
`_draft_faults`, the `only` keyword and the turn prompt are new code. So no
criterion declares a mutant, and `witness` reports an honest `skip` on each.

**An import-time figure.** `SPEC_WRITER_SESSION_USD` is computed once, at
import, from `SPEC_WRITER_SEND_BACKS`. A test that patches the bound and
needs the admission figure to follow patches `SPEC_WRITER_SESSION_USD` too.

**Prose limits.** A docstring stays within ten lines and a comment within
two. New comments take no hedge, so write "a send-back turn reads files" as
a fact. The `prose` gate reads the new turn prompt, and `saffron/`
docstrings and comments.

**The witnesses.** Use plain `def`s and never a parametrised test. Import
every name this spec adds inside the test function, never at module scope,
so the reverted run fails rather than erroring at collection.

- In `tests/test_spec_review.py`, script turns with `_Agent`, `_draft`,
  `_attempt` and `_write_extract`. A send-back is two scripted calls, a work
  turn then an extraction. Give each turn its own session id, cost and turn
  count, so the latest id and the summed cost and turns show. Give the turn
  before each send-back turn a cost above that turn's cap in one case and
  below it in another. `_write_options()` with the send-back budget is the
  work turn's expected options, and `_write_extract_options()` the
  extraction's. A `faults` double that records what it reads in a closure
  list type-checks. On the prototype, an attribute set on the function
  failed `types`. Compare summed float costs with `pytest.approx` where three
  or more costs add.
- Criterion 2 drives five failures. Two are a rate-limited work turn,
  `_attempt(status="rejected", resets_at=...)`, and a raised one,
  `implement.AgentFailed` carrying an attempt. Three follow a work turn: an
  extraction that is not the schema, one rate-limited and one raised. Drive each after
  a first draft whose `DraftFaults` says `parsed` true, then after one that
  says false.
- The parse-only refusal in criterion 3 is `parse_spec`'s own check at
  `saffron/intake.py:358-364`. A copy that validates `Spec` alone accepts
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
`tests/test_follow_up.py` and `tests/test_batch.py`. It also needed the new
prompt's entry in `tests/test_context.py`. No other test file failed.

- `_run_writer` in `tests/test_spec_review.py` passes a `faults` that finds
  nothing and an `emit`. That fixes the three writer tests that call it.
  The pin `SPEC_WRITER_SESSION_USD == 18.5` at `tests/test_spec_review.py:1616`
  becomes 23.0.
- The four `_fake_run_spec_writer` fakes in `tests/test_cli.py` take
  `faults` and `emit`.
- `test_a_spec_revision_fills_cores_writer_prompt_from_its_base_policy_in_a_cell_at_its_predecessors_head`
  and `test_a_review_reads_a_recorded_text_and_a_revision_starts_from_the_queued_file`
  run the real writer over texts that do not parse. Patch
  `spec_review.draft_faults` to return a parsed `DraftFaults` with no line in
  each.
- `test_a_sub_cap_of_18_dollars_writes_none_and_37_writes_two` in
  `tests/test_follow_up.py` pins the shares 0.18 and 0.37 of a $100 cap,
  under one and two $18.50 sessions. Derive the cap from
  `SPEC_WRITER_SESSION_USD` instead. The prototype passed with 0.99 and 2.0
  sessions, renamed
  `test_a_sub_cap_under_one_session_writes_none_and_two_sessions_write_two`.
  It failed with 1.0 and 1.99 sessions.
- `test_a_revision_waits_on_a_rate_limit_and_stops_on_an_error_a_raise_or_the_budget`
  and `test_each_revision_is_an_attempt_and_a_spec_text_on_its_specs_task`
  in `tests/test_batch.py` pin `budget_usd=100.0` (`tests/test_batch.py:4740`,
  `:4812`). Write each as `81.5 + SPEC_WRITER_SESSION_USD`, which is 100.0
  at the old $18.50 and 104.5 at $23.00. On the prototype at $23.00, both
  passed at 104.5 and 105.0, and both failed at 103.5, 104.0 and 105.5.

**Every new test fails with the source reverted.** On the prototype, all
seven witnesses failed with `saffron/spec_review.py` and `saffron/cli.py`
reverted and the new prompt removed. The prototype stood in a stub for
SA-0338's `refuse_inline_mutants`. The `prose`, `structure`, `types`,
`dead`, `lint` and `format` gates showed no new failure in `saffron/`.

**Size.** The prototype measured 689 changed tokens by `size_gate`, against
the `bug` ceiling of 1300, and 1546 more under the test paths. The stub is
left out of that count, and the new prompt is in it. `estimated_lines` is
the first figure over four, rounded up.
