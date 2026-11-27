---
id: SA-0445
title: "A spec review whose extraction turn hits its cap ends with no re-ask, and its review text is kept only in a bounded event log"
type: bug
priority: 2
estimated_lines: 93
estimate_measured: true
touches:
  - saffron/spec_review.py
  - saffron/cli.py
  - tests/test_spec_review.py
  - tests/test_cli.py
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
  - tests/conftest.py
  - saffron/batch.py
  - saffron/draft.py
  - saffron/events.py
  - saffron/credentials.py
  - saffron/ledger.py
  - saffron/task.py
  - saffron/scheduler.py
  - saffron/follow_up.py
  - saffron/end_review.py
  - saffron/regate.py
  - saffron/qualify.py
  - saffron/intake.py
  - saffron/parent_versions.py
  - saffron/phases/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/record/**
  - saffron/report/**
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
  - tests/test_events.py
  - tests/test_draft.py
  - tests/test_follow_up.py
  - tests/test_adopt_stack_layer.py
  - tests/test_ledger_fold_task.py
  - tests/test_witness_gate.py
  - tests/test_suite.py
  - tests/test_session.py
  - tests/test_parent_versions.py
  - tests/test_regate.py
  - tests/test_report.py
  - tests/test_record_refs.py
  - tests/test_record_routed.py
  - tests/test_record_migrate.py
  - tests/test_spec_id_lock_callers.py
  - tests/test_stack_view.py
  - tests/test_package.py
  - tests/test_package_cell.py
  - tests/test_intake.py
  - tests/test_image.py
  - tests/test_corpus.py
budget_usd: 72
max_attempts: 3
max_turns: 210
risk: standard
acceptance:
  - claim: >-
      A spec review's extraction turn is capped at $1.50, up from $1.00.
      `SPEC_REVIEW_EXTRACT_BUDGET_USD` is 1.5, and `SPEC_REVIEW_SESSION_USD`
      is still the review budget plus twice that cap, so 9.0. Each
      extraction turn a spec review sends carries `max_budget_usd` 1.5, and
      the review turn keeps 6.0. The witness compares with the literals 1.5
      and 9.0, rather than the constants. It drives the first extraction turn, the
      re-ask after a refused value and the re-ask after a raised turn.
    witness: tests/test_spec_review.py::test_a_spec_review_extraction_turn_is_capped_at_a_dollar_fifty
    wrong_versions:
      - "`SPEC_REVIEW_EXTRACT_BUDGET_USD` stays 1.0."
      - "`SPEC_REVIEW_SESSION_USD` becomes the literal 8.0 rather than the sum."
    covers:
      - set: the extraction turns of one spec review
        members:
          - member: the first extraction turn
            driven_by: "`SPEC_REVIEW_EXTRACT_BUDGET_USD` stays 1.0."
          - member: the re-ask after a refused value
            driven_by: tests/test_spec_review.py::test_a_spec_review_extraction_turn_is_capped_at_a_dollar_fifty
          - member: the re-ask after a raised extraction turn
            driven_by: tests/test_spec_review.py::test_a_spec_review_extraction_turn_is_capped_at_a_dollar_fifty
  - claim: >-
      A first extraction turn that raises `AgentFailed` with no rate limit
      gets the one re-ask a refused value already gets. The re-ask resumes
      the latest session id, carries the raise's message, a blank line and
      the extraction prompt, and is given the floor the first extraction
      turn was given. A clean re-ask returns its findings, with cost and
      turns summed over all three turns and the raised turn's model named.
      A re-ask that raises or is refused returns an error. A rejected
      window on the re-ask, raised or returned, returns its reset. No
      failure earns a third extraction turn. A
      rate-limited raise, or a rejected window, on the first extraction
      turn still returns the reset with no re-ask. The witness drives three
      raises: one carrying an attempt, shaped as a budget cut, one carrying
      none, and a turn killed with no result event. Each meets all five
      re-ask outcomes, each scripted with exactly three outcomes. A review turn of $4.00 then shows the re-ask's floor
      capped at 1.5.
    witness: tests/test_spec_review.py::test_a_spec_review_re_asks_once_when_its_extraction_turn_raises
    wrong_versions:
      - "A raised first extraction turn returns its error with no re-ask, as it does today."
      - "The re-ask after a raise resumes the review turn's own session id."
      - "The re-ask after a raise sends the extraction prompt alone, without the raise's message."
      - "A rate-limited raise on the first extraction turn is re-asked rather than returned as a reset."
      - "The session's cost leaves out the turns before the re-ask when the re-ask comes back clean."
      - "A re-ask that raises earns one more extraction turn."
      - "A re-ask after a raise whose value is refused earns the refused-value re-ask."
      - "The re-ask after a raise is given the raised turn's own cost as its floor."
      - "The re-ask after a raise is given the review turn's whole cost as its floor, uncapped."
    covers:
      - set: the raises a first extraction turn can end in
        members:
          - member: an `AgentFailed` carrying an attempt, shaped as a budget cut
            driven_by: "The re-ask after a raise resumes the review turn's own session id."
          - member: an `AgentFailed` carrying no attempt
            driven_by: tests/test_spec_review.py::test_a_spec_review_re_asks_once_when_its_extraction_turn_raises
          - member: a turn killed with no result event
            driven_by: tests/test_spec_review.py::test_a_spec_review_re_asks_once_when_its_extraction_turn_raises
      - set: what the re-ask after a raise returns
        members:
          - member: a clean value
            driven_by: "The session's cost leaves out the turns before the re-ask when the re-ask comes back clean."
          - member: a raise
            driven_by: "A re-ask that raises earns one more extraction turn."
          - member: a refused value
            driven_by: "A re-ask after a raise whose value is refused earns the refused-value re-ask."
          - member: a rejected window, returned
            driven_by: tests/test_spec_review.py::test_a_spec_review_re_asks_once_when_its_extraction_turn_raises
          - member: a rejected window, raised
            driven_by: tests/test_spec_review.py::test_a_spec_review_re_asks_once_when_its_extraction_turn_raises
      - set: the rate limits a first extraction turn can meet
        members:
          - member: a raise whose attempt reports a rejected window
            driven_by: "A rate-limited raise on the first extraction turn is re-asked rather than returned as a reset."
          - member: a returned attempt that reports a rejected window
            driven_by: tests/test_spec_review.py::test_a_spec_review_re_asks_once_when_its_extraction_turn_raises
    positive_case: >-
      The same recording double that counts two calls for each rate-limited
      first extraction turn counts three for each raise with no rate limit.
      Each script holds exactly three outcomes. So a fourth call fails the
      witness, and a missing re-ask leaves the count at two.
  - claim: >-
      When `run_spec_review` is given a directory to keep text in, every
      error return after its review turn returned keeps that turn's text.
      The text passes through `credentials.redact` with no token, and lands
      as `review-<sha256 hex of the written text>.md` in that directory,
      which is made when missing. The error is the old one followed by `;
      review text kept at `, the directory's own name, a slash and the
      file's name. That path is relative to the batch tree, and never
      absolute, since the error reaches origin in the record. Where the write raises `OSError`, the
      error is the old one followed by `; review text not kept: ` and the
      exception, and nothing raises. A clean extraction keeps nothing, and
      so does a rejected window on either extraction turn. The witness drives five error returns: no session
      id to resume, raised then raised, raised then refused, refused then
      raised, and refused then refused. It drives six returns that keep
      nothing. It drives two failed sessions for one spec, and a directory
      path that is a file.
    witness: tests/test_spec_review.py::test_a_spec_review_whose_extraction_fails_keeps_its_review_text
    wrong_versions:
      - "Nothing is written, as today."
      - "The text is written without `credentials.redact`."
      - "Only refused then refused keeps the text, since that is the one return the old code built at the end."
      - "The return with no session id to resume keeps nothing."
      - "Every session writes the same file name, so a second failure for the spec overwrites the first."
      - "An `OSError` from the write reaches the caller."
      - "A re-ask after a refused value that comes back clean still writes the text."
      - "A rate-limited extraction turn writes the text."
      - "A rate-limited re-ask keeps the text."
      - "A re-ask after a raise that comes back clean still writes the text."
      - "The file is written, but the error does not name it."
      - "The error names the file by its absolute path."
    covers:
      - set: the error returns after a review turn returned
        members:
          - member: no session id to resume
            driven_by: "The return with no session id to resume keeps nothing."
          - member: raised, then raised
            driven_by: "Only refused then refused keeps the text, since that is the one return the old code built at the end."
          - member: raised, then refused
            driven_by: tests/test_spec_review.py::test_a_spec_review_whose_extraction_fails_keeps_its_review_text
          - member: refused, then raised
            driven_by: tests/test_spec_review.py::test_a_spec_review_whose_extraction_fails_keeps_its_review_text
          - member: refused, then refused
            driven_by: "Nothing is written, as today."
      - set: the returns that keep nothing
        members:
          - member: a clean first extraction turn
            driven_by: tests/test_spec_review.py::test_a_spec_review_whose_extraction_fails_keeps_its_review_text
          - member: a clean re-ask after a refused value
            driven_by: "A re-ask after a refused value that comes back clean still writes the text."
          - member: a clean re-ask after a raise
            driven_by: "A re-ask after a raise that comes back clean still writes the text."
          - member: a rejected window returned by the first extraction turn
            driven_by: "A rate-limited extraction turn writes the text."
          - member: a rejected window returned by the re-ask after a refused value
            driven_by: "A rate-limited re-ask keeps the text."
          - member: a rejected window returned by the re-ask after a raise
            driven_by: tests/test_spec_review.py::test_a_spec_review_whose_extraction_fails_keeps_its_review_text
      - set: the failed sessions for one spec
        members:
          - member: the first
            driven_by: tests/test_spec_review.py::test_a_spec_review_whose_extraction_fails_keeps_its_review_text
          - member: a second, with other text, in the same directory
            driven_by: "Every session writes the same file name, so a second failure for the spec overwrites the first."
      - set: the error returns whose text names the kept file
        members:
          - member: every one of the five error returns above
            driven_by: "The error names the file by its absolute path."
    positive_case: >-
      Each of the six returns that keep nothing runs over the same review
      text, through the same helper, into a directory of the same shape as
      the five error returns. Those five each read exactly one file there.
      So a directory the witness reads as absent is one the write would
      have made.
  - claim: >-
      A batch's spec review and a draft's spec review both keep a failed
      extraction's text in the directory the spec's event log is written
      to. That directory sits in `out_dir` and is named for the spec id
      followed by `.spec-review`. `_stack_review` passes
      that directory to `run_spec_review`, and the draft's `review` adapter
      reaches it through `_stack_review`. The error `read_spec_review` reads
      from that session names the kept file relative to `out_dir`. The witness drives the real
      `run_spec_review` through `cli._stack_review` and through
      `cli._draft_adapters`' `review`, over a scripted `implement.run_agent`
      whose two extraction turns each lack a structured output.
    witness: tests/test_cli.py::test_a_batch_or_draft_spec_review_keeps_its_text_beside_its_event_log
    wrong_versions:
      - "`_stack_review` passes no directory, so nothing is kept."
      - "`_stack_review` passes the spec's export directory under `out_dir` rather than its event log directory."
    covers:
      - set: the adapters that start a spec review
        members:
          - member: "`cli._stack_review`, which `_batch` and `_finish` build"
            driven_by: "`_stack_review` passes no directory, so nothing is kept."
          - member: "`cli._draft_adapters`' `review`"
            driven_by: tests/test_cli.py::test_a_batch_or_draft_spec_review_keeps_its_text_beside_its_event_log
---

## Context

Backlog item **b-298b1c**, filed from the spec loop on 2026-10-29. Batch 59's
spec review of `SA-0326` returned from its review turn after 105 turns, at
$3.81. Its first extraction turn then ended `error_max_budget_usd` after 3
turns, at $1.0876 against the $1.00 cap. It was cold, with 158,840
cache-creation tokens. `~/.saffron/batches/v0/SA-0326.spec-review/events.jsonl`
holds both result events. The batch printed "spec review for SA-0326 could
not be read", raised, and ran no cell for the layer.

**The cap.** `SPEC_REVIEW_EXTRACT_BUDGET_USD` is 1.0, and its comment says
it was reasoned, not measured (`saffron/spec_review.py:51-53`).
`SPEC_REVIEW_SESSION_USD` is the review budget plus twice it
(`saffron/spec_review.py:55-57`). The extraction options set
`max_budget_usd` from it (`saffron/spec_review.py:391-394`). Two callers
read `SPEC_REVIEW_SESSION_USD` when called: the revision budget check
(`saffron/batch.py:879-883`) and the admission block (`saffron/cli.py:2327`).
So the per-candidate review reserve rises from $8.00 to $9.00. Across the
home batch tree, 187 extraction turns of a spec review returned clean. Their
median cost $0.67, and the dearest cost $0.974, on `SA-0330`.
`SPEC_WRITER_EXTRACT_BUDGET_USD` is already 1.5 (`saffron/spec_review.py:576`).

**The re-ask covers only a refused value.** `_extraction_turn` catches a
raised turn and returns a rate-limited one as a reset. It returns any other
as an error session (`saffron/spec_review.py:409-423`). `run_spec_review`
returns that session at once (`saffron/spec_review.py:435-436`). A
value `rebut._validate` refuses gets one re-ask, which resumes `sid` with the
refusal, a blank line and `SPEC_REVIEW_EXTRACT_PROMPT`
(`saffron/spec_review.py:449-478`). `run_agent` raises for a turn cut at its
budget cap, with an attempt that carries that turn's session id
(`saffron/phases/implement.py:443-459`). So `SA-0326`'s budget cut got no
re-ask.

**Where the review text goes today.** The review turn's text is
`first.text`, and no return carries it. Every error return sets `text=""`
(`saffron/spec_review.py:381-389`, `saffron/spec_review.py:469-477`).
`_stack_review` gives each review's agent an `emit` over the
`<out_dir>/<spec id>.spec-review` directory (`saffron/cli.py:1445-1450`).
`_spec_session_emit` appends there through an `EventLog`
(`saffron/cli.py:1373-1378`). That log bounds
each agent event at `BOUND_CHARS`, 8192 characters of JSON, and keeps only
the first 8192 of a longer one (`saffron/events.py:63`,
`saffron/events.py:524-534`). `SA-0326`'s findings text is 5,735 characters
there, kept whole. Three spec review text events in the home batch tree were
cut, on `SA-0273`, `SA-0282` and `SA-0283`. No line the batch prints names
the log. The `unreviewed` line prints `read.error`
(`saffron/batch.py:841`), and the `spec_reviews` row stores it
(`saffron/batch.py:810-817`). `read_spec_review` passes a session's own
error through (`saffron/spec_review.py:218-219`).

**Who calls `run_spec_review`.** `_stack_review`'s `run` is the one caller
(`saffron/cli.py:1459-1461`). Three functions build `_stack_review`. They are `_draft_adapters`
(`saffron/cli.py:1675-1750`), `_batch` (`saffron/cli.py:2414-2782`) and
`_finish` (`saffron/cli.py:2783-2970`). The draft's `review` calls it with
no layer (`saffron/cli.py:1735-1739`). `saffron/draft.py` reads only the session
that `review` returns. A spec review that errors sets its task
`GATE_ERROR` and raises, which the breaker counts as an abort (§4.2.1).

## Problem

1. **Raise the cap.** Set `SPEC_REVIEW_EXTRACT_BUDGET_USD` to 1.5. Its new
   comment says three things. $1.0876 is where a $1.00 cap cut `SA-0326`'s
   extraction turn, so it is a floor. $0.974 is the largest clean use. 1.5
   matches `SPEC_WRITER_EXTRACT_BUDGET_USD`. Leave
   `SPEC_REVIEW_SESSION_USD`'s formula as it is. A spec review still makes at
   most two extraction turns, so the sum stays its ceiling.
2. **Re-ask after a raise.** In `run_spec_review`, give a first extraction
   turn that comes back as an error session the one re-ask a refused value
   gets. The prompt is the error text, a blank line, then
   `SPEC_REVIEW_EXTRACT_PROMPT`. It resumes `sid`. `_measure` moves `sid` to the raised attempt's own
   session id when that attempt carries one. Its
   `last_cost_usd` is the floor the first extraction turn was given,
   `min(first.cost_usd_est, SPEC_REVIEW_EXTRACT_BUDGET_USD)`. A reset session
   from that turn still returns at once. Whatever the re-ask returns ends
   the session.
3. **Keep the review text.** Add a keyword-only `keep_dir: Path | None`
   parameter to `run_spec_review`, defaulting to `None`. Every return that
   carries an error after the review turn returned keeps `first.text` there,
   as criterion 3 says, with `credentials.redact(text, token=None)`. That is
   the redaction `_stack_review`'s own event log applies, since it is built
   with no token. Name the file by the hash of the redacted text, never by a
   session id. A session id comes from the cell's own result event. Keep
   `SpecReviewSession.text` empty on these returns. `read_spec_review` reads
   the last fenced block from it, and a revision reads it as review text.
   With `keep_dir` `None`, write nothing and leave every error as it is.
4. **Pass the directory.** In `_stack_review`'s `run`, bind
   `out_dir / f"{candidate.spec.id}.spec-review"` once. Hand it to
   `_spec_session_emit` and to `run_spec_review` as `keep_dir`.
5. **Fix the tests the change turns red.** These pass at base and fail
   with the change. Edit only what each needs.
   - `tests/test_cli.py` defines a fake of `run_spec_review` four times,
     each named `_fake_run_spec_review`, and none takes an extra keyword.
     `git grep -n _fake_run_spec_review tests/test_cli.py` lists them. Give
     each a `**kwargs`.
   - `test_a_spec_review_session_returns_a_rejected_window_as_a_reset_time`
     pins the old cap and reserve (`tests/test_spec_review.py:502-503`).
   - In `test_a_spec_review_returns_its_tags_from_a_separate_extraction_turn`,
     four rows script a raised extraction turn and nothing after it
     (`tests/test_spec_review.py:768-830`). The recording double fails on a
     call it has no outcome for. The last row's carry and cost assume the old
     cap.
   - Case 5 of `test_a_spec_review_session_names_each_model_its_turns_named`
     is the same shape (`tests/test_spec_review.py:902-911`).
   - The cost 3.0 row of
     `test_a_spec_review_re_asks_once_when_its_extraction_is_not_the_schema`
     assumes the old cap (`tests/test_spec_review.py:1308-1322`).
   - Six tests in `tests/test_cli.py` and two in `tests/test_batch.py` fix
     their budgets against an $8.00 reserve without naming the constant.
     They are `test_queue_stack_prints_each_layers_admission_threshold_and_the_total`
     (`tests/test_cli.py:7745`),
     `test_each_stack_layers_threshold_agrees_with_what_run_stack_batch_admits`
     (`tests/test_cli.py:7962`),
     `test_a_sibling_threshold_is_the_least_budget_every_larger_one_admits`
     (`tests/test_cli.py:8042`),
     `test_a_stack_batch_prints_the_admission_block_saffron_queue_prints`
     (`tests/test_cli.py:8244`),
     `test_a_stack_batch_below_its_total_is_refused_before_any_batch_row`
     (`tests/test_cli.py:8332`),
     `test_partial_runs_a_stack_order_below_its_total`
     (`tests/test_cli.py:8408`),
     `test_a_revision_waits_on_a_rate_limit_and_stops_on_an_error_a_raise_or_the_budget`
     (`tests/test_batch.py:5108`) and
     `test_each_revision_is_an_attempt_and_a_spec_text_on_its_specs_task`
     (`tests/test_batch.py:5185`). Pin `SPEC_REVIEW_SESSION_USD` to 8.0 in
     each with `monkeypatch.setattr`, as `tests/test_batch.py:6889` already
     does.

## Out of scope

- **The spec writer's own extraction.** `run_spec_writer` has the same
  shape, and its re-ask too covers only a refused value
  (`saffron/spec_review.py:938-949`). It stays as it is.
- **A review turn that raises.** Its attempt can carry text too. A review
  cut at its turn or budget ceiling is a different failure, and this spec
  keeps nothing for it.
- **The event log's bound.** `BOUND_CHARS` stays as it is. The kept file
  is whole, and the log stays bounded.
- **The batch's lines and rows.** `saffron/batch.py` changes nowhere. The
  `unreviewed` line and the `spec_reviews` row already carry the error, so
  each names the kept file once the error does.
- **The other credential shapes.** The witness drives one shape, a GitHub
  token, to show the text passes through `redact`. Each shape `redact`
  names is its own tests' subject.

## Notes for the agent

**Mutants.** Criterion 1 edits an existing value. After this spec merges,
the delegate pushes its mutant to `refs/saffron/mutants`, keyed by
criterion 1's witness. It puts the old value back. Criteria 2 to 4 are new code whose
spelling is yours, so `witness` reports `skip` for them.

**Import inside each witness.** Each new witness imports `saffron.spec_review`
inside its body, as the module's own helpers do. Criterion 3 calls
`run_spec_review` with `keep_dir`, so at base it fails with a `TypeError`
rather than erroring at collection.

**The recording double.** `tests/test_spec_review.py`'s `_Agent` plays one
scripted outcome per call and fails on a call past its script. Its
`_KILLED` outcome raises with a cost equal to that call's `last_cost_usd`.
Criterion 2's floor wrong version shows up there: a budget-cut attempt
carrying a cost of 1.0 against a first turn of 0.5.

**Criterion 4's rig.** `_spec_session_rig` (`tests/test_cli.py:11878`)
fakes the cell and the fetch. Patch `implement.run_agent`, never
`spec_review.run_spec_review`, so the witness reads what the real function
does with the directory. `_stack_review` builds its `partial` over
`implement.run_agent` inside `run`, so the patch reaches it.

**Measured on the prototype.** At base `a13d8890` the four witnesses fail.
With the change they pass, and every wrong version above fails its own
criterion's witness. `tests/test_spec_review.py`, `tests/test_cli.py`,
`tests/test_batch.py`, `tests/test_draft.py` and
`tests/test_spec_reviewer.py` pass. So do the fourteen other test files
that name `spec_review` or `run_stack_batch`.
