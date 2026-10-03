---
id: SA-0202
title: A malformed wrong-version answer leaves every version unproven, and REVIEW still passes
type: feature
priority: 1
depends_on: [SA-0201]
estimated_lines: 342
estimate_measured: true
touches:
  - saffron/phases/review.py
  - saffron/cell/session.py
  - saffron/phases/package.py
  - saffron/report/pr_body.py
  - tests/test_review.py
  - tests/test_session.py
  - tests/test_package.py
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
  - saffron/agents/**
  - saffron/gates/**
  - saffron/record/**
  - saffron/intake.py
  - saffron/ledger.py
  - saffron/task.py
  - saffron/replay.py
  - saffron/phases/rebut.py
  - tests/test_report.py
budget_usd: 31
max_attempts: 3
max_turns: 180
acceptance:
  - claim: >-
      A wrong-version session whose first answer is not the schema is resumed
      once, in that same session, with a prompt carrying that answer's own
      error. The re-prompt keeps the first turn's system prompt and tools,
      its budget is what the first turn left of the ceiling, and it passes the
      first turn's cost as `last_cost_usd`. Its answer is the
      record, and the entry's cost is both turns'. That holds for four first
      answers: one with no `<output>` block, one whose JSON does not parse, one
      the schema refuses, and one with the wrong number of answers.
    witness: tests/test_review.py::test_a_wrong_version_answer_that_is_not_the_schema_is_reprompted_once_in_its_own_session
    wrong_versions:
      - The re-prompt starts a fresh session instead of resuming the failed one.
      - The re-prompt sends the extraction prompt alone, without the error.
      - Only a parse failure is re-prompted, so a wrong answer count is filed as before.
      - Only an answer `json.loads` refuses is re-prompted, so a missing block or a schema refusal is filed as before.
      - The entry's cost is the re-prompt's alone.
      - The re-prompt is given the whole ceiling, not what the first turn left.
      - The re-prompt's answer is read from the first turn's text.
      - The re-prompt passes no `last_cost_usd`.
  - claim: >-
      The re-prompt fires once, and only where `run_lens` would fire its own.
      A second bad answer ends the criterion with an error that opens
      `not the schema, even after a re-prompt: ` and carries its own cause.
      That holds for a second answer with no block, one with the wrong
      number of answers, and one whose JSON does not parse. A re-prompt that
      fails ends it too, charged both turns. A first turn that left exactly
      what it spent is re-prompted. No re-prompt follows a first turn that
      left less of the ceiling than it spent, one that carries no session id,
      one that failed, or one whose answer is the schema.
    witness: tests/test_review.py::test_a_wrong_version_reprompt_fires_once_and_only_where_a_lens_would
    wrong_versions:
      - A second bad answer is re-prompted again.
      - The re-prompt fires whenever any of the ceiling is left.
      - A first turn with no session id is re-prompted anyway.
      - A first turn that failed is re-prompted too.
      - A re-prompt that fails is charged the first turn alone.
      - The error after a second bad answer reads as a first-answer error, with no word of the re-prompt.
      - The retry's count check is copied from the first answer's, so a second wrong count files `not the schema` with no word of the re-prompt.
      - A second answer whose JSON does not parse is filed as a first-answer error.
      - The re-prompt is refused when the ceiling left equals what the first turn spent.
  - claim: >-
      A criterion whose wrong-version entry still carries an error is an
      `error`, never a silent pass. `wrong-versions.json` records each of its
      versions with outcome `error` and the entry's error as its summary. The
      REVIEW line counting wrong versions names its witness, and names no
      answered criterion's. The task still reaches `READY_FOR_REVIEW`, and
      its cell outcome carries the entries. The witness drives three such
      criteria, one whose session failed, one that twice answered with no
      block, and one that twice answered the wrong count, whose error opens
      `not the schema, even after a re-prompt: `. Beside them is one that
      answered with no edit.
    witness: tests/test_session.py::test_a_criterion_whose_wrong_versions_no_session_answered_is_an_error_the_review_line_names
    mutant:
      file: saffron/cell/session.py
      find: version["outcome"] = "error"
      replace: version["outcome"] = "unproven"
    wrong_versions:
      - An errored criterion's versions stay `unproven`.
      - Every version without an edit reads `error`, an answered criterion's included.
      - The REVIEW line counts the errored criteria and names none.
      - The REVIEW line names every criterion that declared wrong versions.
      - Only a criterion whose error starts with "not the schema" is named, so a failed session is not.
      - An errored criterion stops the task at `REVIEWING`, as an errored lens does.
      - The cell outcome carries no wrong-version entries.
      - The retry's count check is copied from the first answer's, so a second wrong count files `not the schema` with no word of the re-prompt.
  - claim: >-
      The pull request body's `Not covered` section names the witness of each
      criterion whose wrong-version entry carries an error. It names no
      answered criterion, and quotes no entry's error. `package()` hands the
      renderer the entries the cell outcome carries. The witness drives an
      answered entry and two errored ones, from a failed session and from an
      answer that was not the schema.
    witness: tests/test_package.py::test_the_packaged_body_names_each_criterion_whose_wrong_versions_no_edit_reached
    wrong_versions:
      - "`package()` never hands the entries to the renderer."
      - The body names every criterion that declared wrong versions.
      - The body quotes each entry's error beside its witness.
      - Only an entry whose error starts with "not the schema" is named.
      - The line is built and never added to the section.
  - claim: >-
      A session whose first answer is the schema is asked once, and the REVIEW
      line of a review with no errored criterion reads as it does today.
    witness: tests/test_review.py::test_each_criterion_with_wrong_versions_gets_one_session_that_turns_each_into_an_edit
    preserves: true
---

## Context

Backlog item **b-7251b5**, found in the spec loop's run 26 on `SA-0183`'s
cell. It cites `DESIGN.md` §4.3 and §5.5. Every line number below was read at
`0fecec0c`. Your base will also carry `SA-0198`, `SA-0199` and `SA-0201`.
`SA-0199` and `SA-0201` both edit `saffron/cell/session.py` and
`tests/test_session.py`, so those line numbers will not match. Follow the
function and test names given beside each one, not the numbers.

**What the cell did.** `~/.saffron/batches/v0/SA-0183/wrong-versions.json`
holds one entry. Its `error` is
`not the schema: Expecting ',' delimiter: line 31 column 35 (char 2228)`,
its cost is $0.31, and all five versions read `unproven` with no edit. The
session's last text event in `events.jsonl` carries session id
`b666c240-8df4-4045-bdf0-24b9fef50bf7`. Fed through `parse_output_block` and
`json.loads` on 2026-10-03, that text raised the same error. Line 31 is a
`find` string holding a Python `"""` the session never escaped. The REVIEW
lines were `wrong versions: 5 declared, 0 expressed`, then
`no blockers, 1 concern(s)`. The item records that #648's Spec seat ran all
five versions by hand, and the witness killed each.

**How a lens answer is re-prompted.** `run_lens`
(`saffron/phases/review.py:234`) parses its answer and catches `ValueError`
and `ValidationError` (`:270`). It refuses a retry when the ceiling left is
less than the failed turn spent, or the turn carries no session id (`:274`).
Otherwise it resumes the failed turn's session (`:298`). The prompt is the
error, then `EXTRACTION_PROMPT` (`:296`), on the budget left. It also passes
`last_cost_usd` (`:300`). A failed retry is `re-prompted once, then …`
(`:307`). Its cost is both turns' (`:309`). A second bad answer is
`not the schema, even after a re-prompt: …` (`:316`).

**How a wrong-version answer is read today.** `run_wrong_versions`
(`saffron/phases/review.py:559`) asks one session per declaring criterion. A
failed turn files `_unresolved_wrong_versions` with the failure (`:599-602`).
An answer that does not parse or validate files it with
`not the schema: …` (`:603-613`). So does an answer of the wrong length
(`:614-623`). None is re-prompted. `_unresolved_wrong_versions` keeps every
version with a null edit (`:544-556`). `describe_wrong_versions` counts
versions and edits only (`:647-655`).

**What the cell does with an errored entry.** `_drive_cell` calls
`run_wrong_versions` (`saffron/cell/session.py:2771`) on `probe_budget`
(`:2705`). For an entry with an error it sets each version's outcome to
`unproven` and its summary to the error (`:2836-2840`). Then it writes the
record and emits `describe_wrong_versions`
(`saffron/cell/session.py:2884`). It adds each entry's `cost_usd` to the
spend (`saffron/cell/session.py:2893`). `review_state` then reads the lenses
alone (`saffron/cell/session.py:2910`). The final `CellOutcome` is built at
`saffron/cell/session.py:3050` and carries no wrong-version entry. Its class
is at `saffron/cell/session.py:313`.

**How the pull request body is built.** `package()` calls
`pr_body.render_pr_body` (`saffron/phases/package.py:868`) with fields of
the cell outcome, `notes` last (`:890`). `_not_covered`
(`saffron/report/pr_body.py:492`) lists what the body does not stand
behind. It never quotes a rebuttal's error string (`:561-562`). It writes
`Nothing: …` only when it lists nothing (`:575`).

**An errored version blocks nothing today.** The witness at
`tests/test_session.py:7964` records one version whose gate errored, and its
task still ends ready for review. `DESIGN.md` §5.4 now says a criterion with
no usable answer is an `error` that blocks nothing. §5.7 now says the body's
**Not covered** names it. Both were edited by hand beside this spec.

## Problem

One malformed wrong-version answer turns a measured check into no check,
and nothing above one log line says so. Give the session the re-prompt a
lens gets, and name what is still unanswered.

1. **The re-prompt.** In `run_wrong_versions`, an answer that is not the
   schema gets one re-prompt, built as `run_lens` builds its own. That
   covers a missing block, JSON that does not parse, JSON the model refuses
   and a wrong answer count. The retry resumes the failed turn's session,
   with the error then `EXTRACTION_PROMPT` as its prompt. It keeps the
   criterion's system prompt and `REVIEW_TOOLS`, takes the ceiling the first
   turn left, and passes `last_cost_usd`. Refuse it on the lens rule at
   `saffron/phases/review.py:274`. Never re-prompt a turn that raised
   `AgentFailed`.
2. **The record after it.** A good second answer is filed as a good first
   answer is. A second bad answer is filed with
   `not the schema, even after a re-prompt: ` and its error. A retry that
   raises is filed with `re-prompted once, then ` and the failure. The
   entry's `cost_usd` is both turns'. A first turn that raised is filed
   as today.
3. **The outcome.** In `_drive_cell`, an entry with an error records each
   version's outcome as `error`, not `unproven`. Its summary stays the
   entry's error.
4. **The REVIEW line.** `describe_wrong_versions` appends the witness of
   each entry whose `error` is set, in entry order. With none, the line is
   byte-identical to today's.
5. **The pull request.** `CellOutcome` gains a list field `wrong_versions`,
   empty by default. The final outcome at `saffron/cell/session.py:3050`
   carries the entries.
   `render_pr_body` gains a keyword `wrong_versions`, default empty, and
   hands it to `_not_covered`. `package()` passes `outcome.wrong_versions`.
   `_not_covered` adds one line naming, through `_cell`, the witness of each
   entry whose `error` is set. It never quotes the error.
6. **The state.** `review_state` is unchanged, so the task's state is what
   the lenses and the probes decide.

## Out of scope

- **A version a good answer names no edit for.** That is a real answer and
  stays `unproven`. Backlog item b-12e717 owns telling "no edit exists" from
  "the session stopped".
- **Criterion probes.** `run_criterion_probe` stays without a re-prompt
  (`saffron/phases/review.py:412`).
- **A line announcing the re-prompt.** The lens path announces its own,
  a line opening `{lens}: not the schema` (`saffron/phases/review.py:284`).
  This spec adds none, so each REVIEW line the witnesses count stays one
  line.
- **The ledger and the queue line.** Neither reads `wrong-versions.json`.
- **`DESIGN.md`.** Edited by hand beside this spec, in §5.4 and §5.7.

## Notes for the agent

**New or edit.** Criterion 3 edits one line that exists, and declares a
mutant on it. Criteria 1, 2 and 4 build new code, so each declares a witness
and no mutant, and `witness` reports `skip` for them. Criterion 5 is
`preserves` and names a test that passes now. Each wrong version listed
under a criterion is one its witness must fail. REVIEW turns each into an
edit and runs the witness. Do not run them yourself.

**Commit as each witness passes.** Run the witness, then commit, before the
next one.

**Keep every existing test's name.** The `census` gate reads a renamed test
as a removed one. Add the four new tests beside the existing ones.

**Two existing tests assert the old behaviour.** Change their bodies, not
their names.

- `test_a_wrong_version_session_that_answers_nothing_usable_keeps_every_version`
  (`tests/test_review.py:1299`) scripts one bad reply and two wrong counts,
  none re-prompted. Script each bad turn twice, so seven calls are recorded.
  Each of those three entries then costs 0.2, and its error opens
  `not the schema, even after a re-prompt: `. Update the docstring's
  sentence that says none of the four re-prompts.
- `test_every_wrong_version_is_recorded_with_its_outcome_beside_the_criterion_probes`
  (`tests/test_session.py:7964`) asserts the old record. Its one bad turn
  for the fourth criterion is at `tests/test_session.py:8022`. Add a second bad turn
  after it. That entry then costs 0.2, its error is the after-a-re-prompt
  one, and both its versions read `error`. It pins the line
  `REVIEW: wrong versions: 6 declared, 3 expressed`
  (`tests/test_session.py:8114`), which gains `t.py::d` in your wording.

**Two fakes the packager reads.** The outcome `_cell_outcome` builds
(`tests/test_package.py:773`) and `pkg_outcome` inside
`test_a_protected_path_alone_asks_for_notes` (`tests/test_session.py:8429`)
are each a namespace. Give each `wrong_versions=[]`, or `package()` raises
`AttributeError` on them.

**Criterion 1's witness** calls `run_wrong_versions` over four criteria,
`a` to `d`, each declaring two versions, on a 2.0 ceiling. Script the agent
inside the test so it records every keyword, `resume` included. Each
criterion gets two `implement.AttemptResult` turns with its own session id,
`s-a` to `s-d`. The first costs 0.3 and the second 0.2. The first answers are
these, in order.

1. Plain text with no block.
2. A block whose JSON leaves a quote unescaped inside a string, the shape
   `SA-0183` produced.
3. A block holding two answers with no `reason`.
4. A block holding one answer.

Each second answer is a block of two answers, the first naming an edit. The
witness asserts eight calls. Each first call has no `resume`. Each second
resumes its own criterion's session id. Its prompt contains a fragment of
that criterion's error, in order: `no <output> block in the response`,
`Expecting ',' delimiter`, `reason`, `1 answers for 2 wrong versions`. Its
system prompt equals the first call's, its tools are `REVIEW_TOOLS`, its
`max_budget_usd` is 1.7, and its `last_cost_usd` keyword is 0.3. Each entry equals a literal dict with `error`
`None`, `cost_usd` 0.5, and the second answer's versions.

**Criterion 2's witness** uses the same scripted agent over eight criteria
with one version each, on a 2.0 ceiling. A bad turn is plain text with no
block, and a good answer is a block of one answer. Each turn's session id is
its criterion's, `s-a` to `s-h`, except where the list says otherwise.

1. `a`: a bad turn at 1.0, then a bad turn at 0.2. The 1.0 left equals the
   spend, so the re-prompt fires.
2. `b`: a bad turn at 1.5.
3. `c`: a bad turn at 0.3 whose session id is `None`.
4. `d`: `implement.AgentFailed` carrying a turn at 0.4 with session id
   `s-d`, so only the failure can refuse the re-prompt.
5. `e`: a good answer at 0.1.
6. `f`: a bad turn at 0.3, then `AgentFailed` carrying a turn at 0.25.
7. `g`: two turns at 0.3 and 0.2, each a block of two answers.
8. `h`: two turns at 0.3 and 0.2, each a block whose JSON leaves a quote
   unescaped.

It asserts twelve calls, with `resume` set on the second, eighth, tenth and
twelfth alone. Its errors are, in order, these.

- `not the schema, even after a re-prompt: no <output> block in the response`
- `not the schema: no <output> block in the response`, twice
- the first failure's own text, then `None`
- `re-prompted once, then ` with the second failure's text
- `not the schema, even after a re-prompt: 2 answers for 1 wrong versions`
- one opening `not the schema, even after a re-prompt: Expecting ',' delimiter`

Its costs are 1.2, 1.5, 0.3, 0.4, 0.1, 0.55, 0.5 and 0.5.

**Criterion 3's witness** follows `tests/test_session.py:7964`. It drives
`_drive` with `_stub_the_runtime(monkeypatch)` and four criteria, `a` to `d`,
witnesses `t.py::a` to `t.py::d`, each declaring two versions. After
`_probe_turns` with four probe answers naming no edit come six turns.

1. `a`: an answer of two versions with no edit.
2. `b`: `implement.AgentFailed` carrying a turn.
3. `c`: two turns of plain text with no block.
4. `d`: two turns each holding one answer.

It asserts these.

- The outcome's state is `READY_FOR_REVIEW`.
- In `wrong-versions.json`, `a`'s outcomes are `unproven` twice, and `b`'s,
  `c`'s and `d`'s are `error` twice. Each errored version's summary is its
  entry's error.
- `d`'s error equals
  `not the schema, even after a re-prompt: 1 answers for 2 wrong versions`.
- Exactly one REVIEW line starts `REVIEW: wrong versions:`. It contains
  `t.py::b`, `t.py::c` and `t.py::d`, and not `t.py::a`.
- `outcome.wrong_versions` equals the file's entries.

**Criterion 4's witness** follows
`test_the_packaged_body_carries_the_implementers_notes`
(`tests/test_package.py:1853`). Set `packageable.outcome.wrong_versions` to
three entries. `t.py::answered` has error `None`. `t.py::cut` has an error
ending `MARKER-ONE`, and `t.py::garbled` one opening `not the schema` and
ending `MARKER-TWO`. Run `package()`, then read `pr_body.md`. The text
between `## Not covered` and the next `## ` heading contains `t.py::cut` and
`t.py::garbled`, and no `- Nothing:` line. The whole body contains neither
`t.py::answered` nor `MARKER`.

**Measured.** On 2026-10-03 a prototype of this change passed all four new
witnesses and the two updated tests. The whole suite passed but the queue
smoke test, which this spec's own commit re-measures. With its source
reverted to `0fecec0c`, all four new witnesses failed. Each wrong version
above was applied to the prototype, and its own criterion's witness failed
on every one. After the review, the revised witnesses ran again over the
prototype and every wrong version was applied again. Each one failed again.

**What criterion 3's witness leaves out.** It drives no re-prompt refused on
the lens rule and no re-prompt that failed. Both entries carry an error the
same way, and criterion 2 drives each of them.

**Four docstrings go stale.** `run_wrong_versions`'s says nothing of the
re-prompt. `describe_wrong_versions`'s says the line counts versions and
edits alone. `_not_covered`'s says every line derives from a section above,
and the new one derives from the wrong-version record.
`test_every_wrong_version_is_recorded_with_its_outcome_beside_the_criterion_probes`
(`tests/test_session.py:7964`) has one too. It says, at
`tests/test_session.py:7970`, that its third declaring criterion's session
fails outright and its versions are unproven. That session answers with no
block, and its versions now read `error`. Make each say what the code now
does.

**The `prose` gate** reads every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words.

**Size.** `saffron/cell/**` is in `elevate_on`, so `size` blocks here. The
prototype, counted by `size_gate`, came to 1369 tokens against the
`feature` ceiling of 3000. `estimated_lines` is that over four, with no
overrun added. About a fifth of it is `saffron/`, and the rest is tests.
