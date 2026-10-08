---
id: SA-0227
title: No task drafts a spec, so the spec chain's sessions and review rounds stay outside the record
type: feature
priority: 2
depends_on: [SA-0226, SA-0224]
estimated_lines: 460
estimate_measured: true
touches:
  - saffron/draft.py
  - saffron/ledger.py
  - tests/test_draft.py
  - tests/test_ledger_fold_task.py
pending_symbols:
  - saffron/draft.py::draft_spec
  - saffron/draft.py::seed_spec_id
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
  - saffron/agents/**
  - saffron/record/**
  - saffron/view/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/batch.py
  - saffron/cli.py
  - saffron/follow_up.py
  - saffron/spec_review.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/task.py
  - saffron/finish.py
  - tests/test_batch.py
  - tests/test_cli.py
  - tests/test_follow_up.py
  - tests/test_spec_review.py
  - tests/test_ledger.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 30
max_attempts: 3
max_turns: 130
risk: elevated
acceptance:
  - claim: >-
      `draft_spec` calls `write` once, with a prompt whose first line begins
      `context:`, which holds the line `id: <spec_id>`, and which holds a
      line `<item>`, then the item's text unchanged, then a line reading
      </item> alone.
      It records the reply as the task's spec text 1, origin `draft`, at
      `.saffron/specs/<spec_id>-<slug>.md`. The slug is `follow_up._slug` of
      the reply's parsed title, or `draft` when the reply does not parse as
      a spec. The first review reads that path and that text. The witness
      drives a reply that parses and one that does not, each under an item
      that ends in a newline and one that does not.
    witness: tests/test_draft.py::test_the_draft_prompt_quotes_the_item_and_names_the_draft_for_its_title
    wrong_versions:
      - The item is stripped before it is quoted.
      - The prompt names the id as `spec id SA-0042` rather than on an `id:` line.
      - The prompt opens with a `spec:` line rather than a `context:` line.
      - A reply that does not parse is named by `follow_up._slug("")`, so its file ends `-follow-up.md`.
      - A reply that does not parse raises `SpecError` out of `draft_spec`.
      - The reply is recorded with the origin `follow_up`.
      - The first review is handed the item rather than the recorded text.
  - claim: >-
      `draft_spec` ends the task, and returns a `Drafted` whose `state`,
      `path` and `text` are that state and the last recorded spec text's
      path and text, or `None` for both when none was recorded. A writer
      reply carrying `resets_at` ends `RATE_LIMITED`, and one carrying an
      `error` ends `GATE_ERROR`, before any text is recorded. Each review
      round is routed by `spec_review_route`. `run` ends `SPEC_DRAFTED`,
      `escalate` ends `SPEC_WITHHELD`, `wait` ends `RATE_LIMITED` and
      `error` ends `GATE_ERROR`. A `revise` in round 1 calls `revise` once,
      with the path, the text that round reviewed and the review session's
      whole text. A revision carrying `resets_at` ends `RATE_LIMITED` and
      one carrying an `error` ends `GATE_ERROR`, and neither records a
      text. Any other revision is recorded as spec text 2, origin
      `revision`, at the same path, and round 2 reviews it. A `revise` in
      round 2 is recorded as `escalate`, ends `SPEC_WITHHELD`, and calls
      `revise` no more. A raise from `write`, `review` or `revise` sets
      `GATE_ERROR` and propagates. The witness drives each of the four
      routes in round 1, and in round 2 after a revision, with `revise`
      in round 2 as a fifth. Round 1's `error` is driven twice, by a
      session with no fenced block and by one carrying an error over a
      block holding a finding. It also drives a writer error and reset, a
      revision error and reset, and a raise from `write`, from `review` in
      each round and from `revise`.
    witness: tests/test_draft.py::test_each_route_and_each_writer_stop_ends_the_draft_in_its_own_state
    wrong_versions:
      - A `revise` in round 2 is recorded as `revise`, though the task still ends `SPEC_WITHHELD`.
      - The review rounds are capped at three, so a second `revise` starts a second revision.
      - A `wait` route ends `GATE_ERROR`.
      - An `error` route ends `SPEC_WITHHELD`.
      - A writer reply carrying `resets_at` ends `GATE_ERROR`.
      - A revision carrying an `error` still records its text before the task ends.
      - A raise from an adapter propagates and leaves the task's state unset.
      - A raise from an adapter is caught and returned as a `GATE_ERROR` result.
      - The revision is handed the review's fenced block rather than its whole text.
      - The returned `text` stays the first draft after a revision.
      - Round 2 reviews the first draft rather than the revision.
  - claim: >-
      Each session an adapter returns is one attempt on the task, opened
      and closed in call order. A writer or revision session is a
      `SPEC_WRITING` attempt and a review session a `SPEC_REVIEW` one, each
      numbered from 1 within its phase. Each carries the session's
      `session_id`, `model`, `num_turns` and `cost_usd`, and the subtype
      `error` when the session's `error` is set, else `success`. An adapter
      call that raised opens none. Each review round calls
      `record_spec_review` with that round's route and `read.findings`, so
      its `spec_findings` rows carry the round's `n` and each finding's
      `position`, `severity`, `fixes` and `claim` in block order. A `wait`
      or `error` round writes none. The witness runs every arrangement
      criterion 2's witness runs, and compares the attempts and the rows of
      each with the sessions that arrangement handed out.
    witness: tests/test_draft.py::test_each_session_is_one_attempt_and_each_round_records_its_own_findings
    wrong_versions:
      - A writer session carrying `resets_at` is not charged.
      - A review session is charged as `SPEC_WRITING`.
      - Every round passes `findings=[]`.
      - Round 2 passes round 1's findings again.
      - A review session whose read carries an error and no reset is not charged.
      - A revision session is charged as `SPEC_REVIEW`.
      - Every attempt closes with the subtype `success`.
      - Every attempt closes with `num_turns=0`.
  - claim: >-
      `seed_spec_id(specs_dir)` returns the spec id of the highest-numbered
      `*.md` file directly in `specs_dir` or in its `done/`, read from the
      file's name as `<prefix>-<digits>` and compared as a number, with its
      digits as written. A name that is not of that shape is passed over.
      It raises `ValueError` when those files carry no prefix, or more
      than one. The witness drives ids in `specs_dir` alone, in `done/`
      alone and in both with the highest in `done/`, and two digit widths.
      It passes over a `notes.md` in `specs_dir`, a `README.md` in `done/`
      and a `.txt` file of another prefix.
      It drives the raise on no file, on `README.md` alone, on two prefixes
      across the two directories and within one, and on a missing
      `specs_dir`.
    witness: tests/test_draft.py::test_the_seed_id_is_the_highest_file_id_of_the_one_prefix
    wrong_versions:
      - "`done/` is not read."
      - The first prefix found is returned when two are present.
      - The highest id is chosen by comparing the digit strings, so `SA-9` beats `SA-10`.
      - Every file in the directory is read, not only `*.md`.
      - An empty directory returns `SA-0001` rather than raising.
  - claim: >-
      `Ledger.record_spec_text` takes the origin `draft`, at a path named
      for the task's own spec id under `_FOLLOW_UP_PATH`'s rule. It refuses
      a `draft` text at another id's path, at an id with one more digit, at
      a name holding no id, at the bare id with no slug, and under `done/`,
      writing no row. The witness drives the accepted path and those five.
    witness: tests/test_draft.py::test_a_draft_spec_text_records_only_under_its_own_ids_path
    wrong_versions:
      - A `draft` path is checked against `_REVISION_PATH`.
---

## Context

Backlog item **b-98a3be**, under `DESIGN.md` §3.4. §3.4 makes the spec chain
a task: "`saffron draft <item> --repo <repo>` runs the spec chain as a
task." Its writer works "in the writer prompt's `context:` form". §3.4 adds
"A review that routes `revise` starts one revision. A second review that
is still unclean escalates. The bound is two review rounds." It also says
"Each session is a `SPEC_WRITING` or `SPEC_REVIEW` attempt with turns, cost
and times (§4.1)."

This spec is the core of that command. `SA-0229` is its other half. It adds
`saffron draft` to `saffron/cli.py`, mints the task, builds the three
adapters over cells, and writes the file. Nothing here opens a cell.

Line numbers below were read at `3d594729`, the head that adds `SA-0226`'s
spec file.

**The states and the fact kind exist.** `SPEC_DRAFTED` is a task state
(`saffron/ledger.py:57`) and in `DONE_STATES` (`saffron/scheduler.py:82`).
`SETTLED_STATES` leaves it out (`saffron/scheduler.py:123-126`).
`SPEC_WITHHELD`, `GATE_ERROR` and `RATE_LIMITED` predate it.

**What the stack batch does today, and what this reuses.** The stack batch
reads each spec review session with `read_spec_review`
(`saffron/spec_review.py:205`). It routes the read with `spec_review_route`
(`saffron/spec_review.py:266-286`). That route returns `wait` before
`error`, and `revise` only for blockers each tagged `build` or `witness`, or
a `concern` tagged `witness`. The batch charges each review session as a
`SPEC_REVIEW` attempt (`saffron/batch.py:588-597`). A revision gets the
review session's whole text (`saffron/batch.py:657`). The batch charges the
revision as a `WRITING_PHASE` attempt (`saffron/batch.py:695-705`).
`WRITING_PHASE` is `"SPEC_WRITING"` (`saffron/spec_review.py:38`). The
batch caps revisions at `MAX_REVISE_ROUNDS = 3` (`saffron/batch.py:71`).
`follow_up.write_follow_ups` charges a writer session the same way, in a
local `_charge` (`saffron/follow_up.py:254-263`).

**Where the findings go.** `SA-0226` gives `Ledger.record_spec_review` a
keyword `findings` with no default. Each finding becomes one `spec_finding`
fact and one `spec_findings` row, numbered from 1 in the order given, under
the round's `n`. At `3d594729` the method takes no such keyword
(`saffron/ledger.py:1624-1631`).

**Where the spec text goes.** `SPEC_TEXT_ORIGINS` is `("revision",
"follow_up")` (`saffron/ledger.py:72`). Any other origin is a `ValueError`
in `record_spec_text` (`saffron/ledger.py:1673-1676`). So is a spec id the
task does not carry (`saffron/ledger.py:1682-1683`). A `follow_up` path
must match `_FOLLOW_UP_PATH` for the spec's own id, and any other origin
`_REVISION_PATH` (`saffron/ledger.py:76-77`, `:1684-1690`).
`tests/test_ledger_fold_task.py:942` pins the tuple.

**What names a new spec.** `follow_up.next_spec_id(origin_id, specs_dir,
ledger, repo_id)` takes its prefix and digit width from `origin_id`
(`saffron/follow_up.py:50-78`). It reads the live files, their `done/`
retirees and the repo's tasks. A draft has no origin spec, so its caller
needs an id to start from. `follow_up._slug` lowercases a title and joins
its runs of letters and digits with `-`, or returns `follow-up` for none
(`saffron/follow_up.py:81-83`). A follow-up's file is
`.saffron/specs/<id>-<slug>.md` (`saffron/follow_up.py:364`).
`RETIRED_DIRNAME` names `done/` (`saffron/scheduler.py:525`). This repo's
`done/` holds a `README.md`.

**The sessions.** `SpecWriterSession` carries `text`, `cost_usd`, `error`,
`resets_at`, `session_id`, `num_turns`, `spec_sha` and `model`
(`saffron/spec_review.py:587-602`). `SpecReviewSession` carries `text`,
`cost_usd`, `error`, `resets_at`, `session_id`, `num_turns` and `model`
(`saffron/spec_review.py:121-138`).

## Problem

1. **`saffron/draft.py`, new.** `draft_spec(ledger, task_id, *, spec_id,
   item, write, review, revise)` drives the chain on a task its caller
   minted with `spec_id`, as the criteria say. The adapters are called as
   `write(prompt)`, `review(path, text)` and `revise(path, text,
   review_text)`. The first and third return a `SpecWriterSession`, the
   second a `SpecReviewSession`. It returns a frozen `Drafted` with
   `state`, `path` and `text`.
2. **The seed id.** `seed_spec_id(specs_dir)` in the same module, pure
   over the two directories. `SA-0229` passes its result to
   `next_spec_id`.
3. **`saffron/ledger.py`.** `SPEC_TEXT_ORIGINS` gains `"draft"` as its
   third member. A `draft` path is checked by `_FOLLOW_UP_PATH` for the
   spec's own id, as a `follow_up` path is. Update the comments above both
   constants. Also update the docstring sentence naming two origins
   (`saffron/ledger.py:1666-1667`).
4. **`tests/test_ledger_fold_task.py:942`** pins the three-member tuple.

## Out of scope

- The command, the mint, the cell adapters and writing the file into the
  repo's working tree. `SA-0229` adds them in `saffron/cli.py`.
- The stack batch's loop, its `MAX_REVISE_ROUNDS` cap and its own adapters.
  `draft_spec` is a new module, not an extraction from `saffron/batch.py`.
- A review adapter that raised records no `spec_review` row here. The stack
  batch records one with the route `error` (`saffron/batch.py:563-570`).
  `draft_spec` only sets `GATE_ERROR` and re-raises.
- Checking the draft's declared id, type or `touches`. The spec review reads
  the text. `_validate` stays the follow-up's alone
  (`saffron/follow_up.py:170-208`).
- The core writer prompt's sentence that a `context:` line gives findings
  (`saffron/agents/prompts/spec-writer.md:11-12`). The draft prompt says
  what it gives.
- Any reader that sums attempts per spec. `SA-0228` adds attempt totals to
  the task page.

## Notes for the agent

**This change is new code.** No text at base fixes the spelling of what it
adds. So each criterion declares a witness and no mutant. The `witness` gate
reports `skip` for all five. The wrong versions under each criterion are
what its witness must kill. Do not run them yourself.

**Import `saffron.draft` inside each test body**, never at module scope. A
module-scope import makes the reverted run a collection error, which
`revert` reads as `skip`. The criterion 5 witness imports nothing new.

**One arrangement drives criteria 2 and 3.** Build one table of named
arrangements. Each holds a list of writer replies and a list of review
sessions. Run `draft_spec` once per arrangement on a fresh `Ledger` and
task. Give every session its own `session_id`, `model`, `num_turns` and
`cost_usd`, so a swapped or dropped attempt shows. A raise is an exception
in the list, popped and raised by the double. Give each finding its own
claim, so order shows. A review that routes `revise` holds a `concern`, a
`blocker` tagged `build` and a `note`, in that order. One that escalates
holds a `blocker` tagged `scope`. A clean one holds a `note`, so `run`
rounds write a row. A `wait` session has empty text and `resets_at` set.
Use eighteen arrangements: the five round-1 routes, the five round-2
routes after a revision, the two writer stops, the two revision stops and
the four raises.

**Criterion 2's witness asserts these per arrangement.** It checks the
returned triple, the task's `state` column and the routes in `spec_reviews`
order. It checks each spec text's origin, path and text. It checks the
arguments each `review` and `revise` call got, and how many `revise` calls
ran.

**Criterion 3's witness reads the sessions back from the double.** It reads
them in the order the double handed them out. It derives the expected
attempts and rows from them.

**Criterion 4's witness builds each tree under `tmp_path`.** Each file holds
any text, since only names are read.

**What the witnesses leave undriven.** A title whose slug has no letter or
digit gets `follow-up` from `_slug`. A writer reply carrying both
`resets_at` and `error` is another. The writer's rate-limited reply, from
`_rejected`, sets no error (`saffron/spec_review.py:664-673`). Round 2's `error` is
driven by a session with no fenced block alone.

**The parent is `SA-0226`.** Both edit `saffron/ledger.py`. Its
`record_spec_review(..., findings=...)` is what criterion 3 reads through.
`SA-0224` is the top of the chain below it.

**Measured on a prototype.** A prototype at `3d594729`, with `SA-0226`'s
source applied first, passed all five witnesses. With its source reverted,
each failed. Its diff measured 1840 changed tokens. Each of the 32 wrong
versions above was applied to it as an edit with a fresh bytecode cache.
Each failed its own criterion's witness. The rest of the suite passed on
it.
