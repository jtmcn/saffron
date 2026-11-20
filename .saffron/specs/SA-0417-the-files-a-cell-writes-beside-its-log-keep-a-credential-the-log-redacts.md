---
id: SA-0417
title: "The files a cell writes beside events.jsonl keep a credential the log redacts, and three default logs never hold the cell's token"
type: bug
priority: 2
estimated_lines: 138
estimate_measured: true
removes:
  - saffron/events.py:_redact_nested
touches:
  - saffron/credentials.py
  - saffron/events.py
  - saffron/cell/session.py
  - saffron/task.py
  - saffron/phases/package.py
  - tests/test_session.py
  - tests/test_task.py
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
  - hooks/**
  - saffron/intake.py
  - saffron/cli.py
  - saffron/projection.py
  - saffron/finish.py
  - saffron/gates/**
  - saffron/agents/**
  - tests/test_credentials.py
  - tests/test_events.py
  - tests/test_intake.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 56
max_attempts: 3
max_turns: 300
acceptance:
  - claim: >-
      `plan.json` holds the accepted plan block passed through
      `credentials.redact` as text, and the PLAN line's sha256 is the hash
      of the bytes written. The witness's block is indented JSON, so a
      parse and a fresh dump would change its bytes. It carries three
      credentials in three of its string fields. The cell's own token, of no
      listed shape, sits in the first field. A GitHub token sits in a middle
      field, and a private key block with its END line in a later one. Two
      fields after the key, a list and the integer `estimated_lines`, are
      written unchanged. The file equals the block with each credential
      replaced by its kind's placeholder, spacing included. The PLAN line
      names the hash of the file's own bytes, and never the hash of the
      block as the cell wrote it. The witness drives the cell twice, handed
      the token and then handed `None`. Handed `None`, the two shapes are
      still redacted and the token is written.
    witness: tests/test_session.py::test_the_recorded_plan_is_redacted_and_its_announced_hash_names_the_file
    wrong_versions:
      - "`plan.json` written as the block came, with only the PLAN line's hash changed."
      - The PLAN line hashes the block as the cell wrote it, while the file holds the redacted text.
      - The plan redacted with no token, so the cell's own token is written.
      - "`run_one_cell` takes the token but never hands it to `_drive_cell`, so every write there redacts the shapes only."
      - The plan is redacted only when a token was handed, so a cell handed `None` writes every shape.
      - "`plan.json` is parsed, walked with `redact_nested` and dumped again, so its bytes are not the block's."
  - claim: >-
      `notes.json`'s `raw` is the notes passed through `credentials.redact`
      with the cell's own token. Its `sha256` and the outcome's
      `notes_sha256` are both the hash of that redacted text. The witness's
      notes hold three lines. A GitHub token sits on the first, the cell's
      own token on the middle one, and an AWS access key id ends the last.
      `raw` reads back as all three lines with each credential's placeholder
      in its place. The outcome's `notes` stay the text the turn extracted,
      credentials included, so PACKAGE's own body scan still sees them. The
      witness drives the cell twice, handed the token and then handed
      `None`. Handed `None`, the two shapes are still redacted and the token
      is written.
    witness: tests/test_session.py::test_the_recorded_notes_are_redacted_and_hashed_as_written
    wrong_versions:
      - "`notes.json`'s `raw` written as the turn extracted it."
      - The envelope's `sha256` hashes the notes as extracted, so it names a text no file holds.
      - The notes redacted in memory too, so the outcome's `notes` lose the credential PACKAGE refuses.
      - The notes redacted with no token, so the cell's own token is written.
      - The notes are redacted only when a token was handed, so a cell handed `None` writes every shape.
  - claim: >-
      The task's own `findings.json` holds every lens's record with each
      string passed through `credentials.redact` with the cell's own token,
      one string at a time. That covers a claim, a probe's text and a lens's
      `error`. The witness drives all four lenses in `LENSES` order. The
      first lens files two findings, an AWS access key id inside the first
      one's claim and a clean second. The second lens files five. They are
      one carrying the cell's own token, a clean one, one whose claim ends
      in a private key header and one body line with no END line, a clean
      one, and one ending in a GitHub token. The third, adequacy, files one
      clean finding whose probe's `find` carries an AWS access key id. The
      last lens fails, and its `error` quotes a GitHub token. The file loads
      as JSON. Each claim, the probe's `find` and the error read back
      unchanged or with its placeholder. The claim with the key keeps the
      text before it. Every finding validates as a `Finding`, the way
      `ready_task` reads them back. The outcome's reviews keep each claim
      and the error as the lenses gave them. The witness drives the cell
      twice, handed the token and then handed `None`. Handed `None`, every
      shape is still redacted and the token is written.
    witness: tests/test_session.py::test_the_recorded_findings_are_redacted_in_every_lens_and_finding
    wrong_versions:
      - The serialized JSON redacted as one string, so the key with no END line takes every finding after it and the file no longer loads.
      - Only the first lens's findings redacted.
      - Only the last lens's findings redacted.
      - Only the first finding of each lens redacted.
      - The findings redacted with no token, so the second lens's claim keeps the cell's own token.
      - Each finding's claim redacted in place, so the outcome's reviews and the ledger's rows lose what the lens filed.
      - Only each finding's `claim` redacted, so a probe's `find` and a lens's `error` keep their credentials.
      - Each lens's findings walked and its `error` left alone.
      - The findings are redacted only when a token was handed, so a cell handed `None` writes every shape.
  - claim: >-
      `run_one_cell` takes a keyword `token`, default `None`, and the log it
      builds when handed no `emit` is handed that token. The witness drives
      a cell through its plan turn, its implement turn and all four lenses,
      and each of the six turns emits one `Agent` event carrying the token.
      Handed it, `events.jsonl` holds the token nowhere, and each of the six
      events reads back with `redacted` naming the cell's own token. Handed
      `None`, with the same token set in `CLAUDE_CODE_OAUTH_TOKEN`, the same
      cell writes the token, and no event names a redaction. The log never
      reads the environment (item 46, `saffron/events.py:505-506`).
    witness: tests/test_session.py::test_a_cells_default_log_redacts_the_token_it_was_handed
    wrong_versions:
      - "`run_one_cell`'s default log built with no token, as at base."
      - "`run_one_cell`'s default log falls back to `CLAUDE_CODE_OAUTH_TOKEN` when handed `None`."
  - claim: >-
      `run_task` hands `run_one_cell` the token it was given, and never the
      environment's. The witness sets `CLAUDE_CODE_OAUTH_TOKEN` to one value
      and hands `run_task` another. The cell is handed the second.
    witness: tests/test_task.py::test_run_task_hands_its_cell_the_token_it_was_given
    wrong_versions:
      - "`run_task` calls `run_one_cell` with no token."
      - "`run_task` hands the cell the environment's token."
  - claim: >-
      `package()` and `push_unpackaged_work()` each build their default log
      with the token they were given. The witness calls `package()` with one
      token, then `push_unpackaged_work()` with another, then
      `push_unpackaged_work()` with `None`, each with no `emit`. It appends
      one raw `Agent` event carrying each call's token to the log that call
      built. The first two tokens are written nowhere, and each of their
      events names the cell's own token in `redacted`. The third is written
      whole, and its event names nothing.
    witness: tests/test_package.py::test_packages_own_logs_redact_the_token_they_were_handed
    wrong_versions:
      - "`package()`'s default log built with no token."
      - "`push_unpackaged_work()`'s default log built with no token."
  - claim: >-
      An `Agent` event is still redacted in every field after the nested
      walk moves to `saffron/credentials.py`, a list nested 999 deep
      included.
    witness: tests/test_credentials.py::test_an_agent_events_credentials_are_redacted_in_every_field
    preserves: true
  - claim: >-
      An event the size bound keeps today is still written, a list nested
      1000 deep included.
    witness: tests/test_events.py::test_carried_counts_are_held_to_their_own_bound
    preserves: true
  - claim: >-
      Notes with no credential are recorded, hashed and returned as before.
    witness: tests/test_session.py::test_the_notes_artifact_is_hashed_when_it_is_produced
    preserves: true
---

## Context

Backlog item **b-3a3081**, filed from review of #906 (`SA-0277`), with
items 46 and 11. It cites `DESIGN.md` §5.4 and §5.7. Every line below was read
at `a58105b4`.

**What is redacted today.** `SA-0277` redacts an `Agent` event before
`EventLog.append` writes it (`saffron/events.py:526-546`). It walks the
event with `_redact_nested` (`saffron/events.py:450`), which calls
`credentials.redact` on every string leaf. That function replaces the
cell's own token, when it is handed one, and each listed credential shape
(`saffron/credentials.py:37-51`). The shapes are the module's five-entry
tuple (`saffron/credentials.py:15-21`). Each match becomes
`[redacted: <description>]`. A private key with no END line is swept to the
end of the string (`saffron/credentials.py:25-28`).

**What is not.** The files a cell's output lands in are written as they
came.

- `plan.json` is the accepted block, written at
  `saffron/cell/session.py:2773`. The PLAN line hashes that same text at
  `:2777`.
- `notes.json` is an envelope of the extracted notes and their hash
  (`saffron/cell/session.py:3252-3255`). The hash also reaches the
  outcome's `notes_sha256` (`:4100`).
- The task's own `findings.json` is every lens's `as_dict()`, dumped whole
  (`saffron/cell/session.py:3656-3658`).

**Who holds the token.** `run_task` builds its own log with the token it
was given (`saffron/task.py:799`). It calls `run_one_cell` with no token
(`saffron/task.py:963-971`), and neither `run_one_cell` nor `_drive_cell`
takes one (`saffron/cell/session.py:1134`, `:2325`). `run_one_cell`'s own
default log, built when it is handed no `emit`, gets no token
(`saffron/cell/session.py:1161-1163`). PACKAGE holds `token` in both
`package()` and `push_unpackaged_work()` (`saffron/phases/package.py:659`,
`:1133`). Each builds its default log without it (`:691`, `:1171`). PACKAGE
emits no `Agent` event today, so nothing it writes is unredacted yet.

**Who reads the hash.** `projection` takes the 12-character hash from the
PLAN line (`saffron/projection.py:61`, `:198-200`). It compares it with the
sha256 of `plan.json`'s bytes (`saffron/projection.py:273-274`, `:412`).
The comment at `saffron/cell/session.py:2687-2689` says the same thing:
`sha256sum plan.json` re-derives the PLAN line's hash.

**Who reads the files back.** `ready_task`, which `saffron package` uses,
rebuilds the reviews from `findings.json` with `Finding.model_validate`. It
reads the notes from `notes.json`'s `raw` (`saffron/task.py:1411-1435`).

**The settled scope.** The operator settled these. Redact the three files
with `saffron/credentials.py` before each is written. Hand PACKAGE's log
the token it holds. Leave `patch.diff` as it is, since PACKAGE applies and
pushes that text. This spec's pull request amends `DESIGN.md` §5.7 by hand
to say so.

## Problem

A credential the cell writes into its plan, its notes or a lens finding
reaches the host's disk unredacted, beside a log that redacts it. Make
these changes.

1. **One walk, in the one module.** Move `_redact_nested` from
   `saffron/events.py` into `saffron/credentials.py` as the public
   `redact_nested`, with `token` keyword-only. Its body is unchanged: an
   explicit stack, new containers, and each description named once.
   `EventLog.append` calls it from there.
2. **The cell is handed the token.** `run_one_cell` and `_drive_cell` each
   take a keyword `token: str | None = None`. `run_one_cell` hands it to
   `_drive_cell`, and to the log it builds when handed no `emit`.
   `run_task` hands `run_one_cell` its own `token`.
3. **`plan.json` is redacted, then hashed.** Pass the accepted block
   through `redact` with the token. Write that text, and hash that same
   text for the PLAN line. Leave the line's wording alone, since
   `projection`'s pattern matches it whole.
4. **`notes.json` is redacted, then hashed.** Pass the extracted notes
   through `redact` with the token. The envelope's `raw` is that text, and
   its `sha256` and the outcome's `notes_sha256` are that text's hash. The
   outcome's `notes` stay the text as extracted.
5. **The task's own `findings.json` is redacted leaf by leaf.** Pass the list of
   `as_dict()` values through `redact_nested` with the token, and dump what
   it returns. The `reviews` list itself is untouched.
6. **PACKAGE's two default logs take the token.** Both `EventLog` calls in
   `saffron/phases/package.py` are handed the `token` that function holds.
7. **The module says where it reaches.** `saffron/credentials.py`'s
   docstring names `EventLog` alone, and its `ponytail:` comment says an
   unlisted shape reaches "the remote and the log". Name `plan.json`,
   `notes.json` and the task's own `findings.json` in the docstring, and
   say the host's files in the comment.
8. **Two texts stop calling the plan verbatim.** The comment at
   `saffron/cell/session.py:2687-2689` and the docstring of
   `test_the_recorded_proposal_carries_the_hash_of_its_own_raw_block`
   (`tests/test_session.py:16989`) call `plan.json` the raw block verbatim.
   Say instead that `sha256sum plan.json` re-derives the PLAN line's hash,
   or that the block is redacted.

**Redact before the hash.** The control-artifact rule is that an artifact
is hashed the moment it is produced (`CLAUDE.md`). The hash is the record's
name, so it must name the bytes on disk. A hash of the unredacted text
names bytes no file holds. `projection` would then find the plan mismatched
and leave it unlinked from the diff. `redact` is a pure function of the
extracted text, and nothing is re-read from `/work`. Redacting first keeps
both halves of the rule.

## Out of scope

- **`patch.diff`.** It is written as the cell left it
  (`saffron/cell/session.py:1025`, `:1118`). PACKAGE applies that file and
  pushes it, so redacting it would change the pushed code. PACKAGE's own
  scan refuses a patch carrying a known shape (`saffron/phases/package.py:835`).
  §5.7 names it as accepted risk.
- **Every other file in the task directory.** `scope_proposal.json`
  (`saffron/cell/session.py:2681`) and `rebuttal.json`
  (`saffron/cell/session.py:4007`) carry cell text and stay as they are.
  So do each review commit's `commit-reviews/<head>.json`
  (`saffron/commit_review.py:189`) and the probe and wrong-version records.
  So does `pr_body.md`, which PACKAGE writes before it scans the body
  (`saffron/phases/package.py:962`, `:965`).
- **The end review's `findings.json`.** `saffron/finish.py:43` names a
  batch-level file of the same name. This spec means the task's own, under
  the task directory.
- **The ledger and the record.** `ledger.record_findings` still stores each
  claim as filed (`saffron/cell/session.py:3667`).
- **The terminal line.** Each default emitter prints `describe(event)`
  before `log.append` redacts it (`saffron/cell/session.py:135-138`,
  `saffron/task.py:803-806`). So stdout carries the token and every known
  shape. Under `launchd` that line lands in `~/.saffron/batch.out.log`
  (`docs/host/dev.saffron.batch.plist:59`). §5.7 names both as residual.
- **The spec-session log.** `_spec_session_emit` builds `EventLog(log_dir)`
  with no token (`saffron/cli.py:1375`), and `cli.py` is forbidden here.
- **A plan with an unterminated key.** `plan.json` is the raw block. A
  private key header with no END line takes the rest of the file, as it
  does for a raw `line` in the log. Nothing parses `plan.json`.
- **`saffron package` after a redaction.** `ready_task` reads the redacted
  files back. On that path a placeholder reaches the pull request body, and
  the body scan no longer refuses it.
- **Hand edits in this spec's pull request.** `DESIGN.md` §5.7 now says
  `events.jsonl`, `plan.json`, `notes.json` and the task's own
  `findings.json` are redacted before each is written. It says `patch.diff`
  is accepted risk, and names the terminal line and the batch log file as
  residual. That text
  replaces the sentence that began "Until it exists" and named the remote
  alone. Item 11 now names `saffron/credentials.py`'s tuple in place
  of `_CREDENTIAL_SHAPES` (`docs/backlog/011-what-package-left-and-the-one-design-question-it-raised.md:83`).

## Notes for the agent

**Edit or new.** Each criterion edits existing code, and no mutant on the
ref pins one. A mutant's `find` must occur once at your base. Every spelling
these criteria need is new there, criterion 4's keyword included. Criteria 1
to 3 add new local names. Criterion 5's keyword can sit anywhere in the call.
Criterion 6's two calls are spelled alike. So every witness stands alone,
and `witness` reports `skip` for each. The three `preserves` witnesses exist at
your base and pass there.

**Test credentials.** Build each one inside the test from pieces, such as
`"gh" + "p_" + ...`. A private key header too: join `"PRIVATE " + "KEY"`
before you format the BEGIN and END lines. PACKAGE scans the diff for a
whole header and refuses the push, and no gate in the cell runs that scan.
For the cell's own token, use one that matches none of the five shapes, so
only the literal check catches it.

**`tests/test_session.py`.** Give `_drive` a `token` keyword, default
`None`, and hand it to both of its `run_one_cell` calls. Criteria 1 to 4
each drive `_drive` twice, under `tmp_path / name`, handed the token and
then `None`. Criterion 1 scripts its block as `json.dumps(plan, indent=2)`
inside an `<output>` block, then one implement turn. Criterion 2 follows
`test_the_notes_artifact_is_hashed_when_it_is_produced`: a `forbidden` list
asks the notes turn. Criterion 3 files `"note"` findings, so no REBUT turn
runs. Only adequacy's schema takes a `probe` (`saffron/phases/review.py:102-105`),
so its probe sits on an adequacy finding. The last lens's turn is an
`implement.AgentFailed`, whose message becomes that lens's `error`.
Criterion 4 drives `use_default_emit=True` with `agent_says`, which emits
one `Agent` per turn, and reads
`tmp_path / name / "out" / "SY-1" / "events.jsonl"`. Its None half sets
`CLAUDE_CODE_OAUTH_TOKEN` with `monkeypatch.setenv`. Its plan, implement
turn and four lenses make six. The PLAN line `cell.watched` holds reads
`PLAN: accepted, sha256 <12 hex>`.

**`tests/test_task.py`.** `_drive` takes `on_cell`, which sees the keywords
`run_task` hands the double. Pass `state="NOT_IMPLEMENTED"`, so no PACKAGE
path runs.

**`tests/test_package.py`.** Replace `package_phase.EventLog` with a
subclass that records each instance, so the test can append to the log a
call built. Pass each keyword to `package()` and `push_unpackaged_work()`
by name from `packageable.kwargs` and `packageable.unpackaged_kwargs`,
leaving `emit` out. Spreading a filtered dict widens every value to a
union, and the `types` gate reports 13 diagnostics over the three calls.

**Imports in the new tests.** Import `redact_nested` and any other name the
change adds inside the test's own body, never at module scope. A
module-scope import makes the reverted test a collection error, which
`revert` reads as `skip`.

**The `prose` gate.** The comment above the plan write is two lines today.
Adding a third line is a new comment-block hit, so fold the new reason into
two lines. Step 8's comment is three lines today, so its rewrite fits in
two. Each new docstring sentence stays within 25 words.

**Size.** A prototype at `a58105b4` measured 552 changed tokens with
`size_gate` outside the test paths, and `estimated_lines` is that over
four. It held all eight steps and the six new witnesses. Each new witness
failed with the source reverted. Every wrong version listed above failed
its witness there.
