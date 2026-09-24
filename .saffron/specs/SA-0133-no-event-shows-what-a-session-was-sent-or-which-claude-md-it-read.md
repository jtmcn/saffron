---
id: SA-0133
title: No event shows what an agent session was sent or which `CLAUDE.md` its task read, so the standing instructions reaching a live cell cannot be checked
type: feature
priority: 3
depends_on: [SA-0139]
touches:
  - saffron/phases/implement.py
  - saffron/cell/session.py
  - saffron/events.py
  - tests/test_implement.py
  - tests/test_session.py
  - tests/test_events.py
  - tests/fixtures/watch-golden.txt
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
  - saffron/agents/**
  - saffron/phases/review.py
  - saffron/phases/rebut.py
  - saffron/phases/package.py
  - saffron/gates/**
  - saffron/record/**
  - saffron/report/**
  - saffron/repos/**
  - saffron/cell/runtime.py
  - saffron/cell/worktree.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/batch.py
  - saffron/cli.py
  - saffron/task.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_fold.py
  - tests/test_package.py
  - tests/test_rebut.py
  - tests/test_review.py
  - tests/test_spec_loop_driver.py
budget_usd: 25
max_attempts: 3
max_turns: 160
estimated_lines: 330
risk: elevated
acceptance:
  - claim: >-
      `run_agent` emits one host-authored `AgentEvent` whose `detail` holds
      the SHA-256 hex of the request it writes to the runner's stdin. It is
      the turn's first event, emitted before the runner starts. The witness
      drives three turns through `run_agent` with an `exec_stream` double
      that keeps the exact string it was handed. Its options carry no string
      system prompt. One is a fresh session, one
      resumes a session with the same prompt and options, and one has a
      runner that exits 1 with no result event, so `run_agent` raises. On
      each, exactly one event carries a 64-character hex digest, it is the
      first event emitted, and it equals the SHA-256 of the string the double
      received. The fresh and the resumed digests differ. Today `run_agent`
      emits nothing before the runner starts.
    witness: tests/test_implement.py::test_each_request_is_recorded_by_the_sha256_of_the_bytes_the_runner_reads
    mutant:
      file: saffron/phases/implement.py
      find: stdin_data=request,
      replace: 'stdin_data=request + "\n",'
  - claim: >-
      Every agent session a task starts leaves the SHA-256 of its request in
      the task's events. The witness drives four cells through the real
      `run_agent`, with only `exec_stream` faked. Between them they start
      the plan session, IMPLEMENT, a repair turn, a salvage turn, each of
      the three lenses, one criterion probe, the rebuttal turn, the
      rebuttal's extraction turn and one verdict session. In each cell the
      digests its `AgentEvent`s carry equal, in order and in number, the
      SHA-256 of each request the double received. The witness finds each
      of those session kinds among the requests by the turn prompt it
      carries. The notes name the sessions it does not drive. Today no event carries a digest of any request.
    witness: tests/test_session.py::test_every_session_a_task_starts_records_the_sha256_of_its_request
    mutant:
      file: saffron/phases/implement.py
      find: stdin_data=request,
      replace: 'stdin_data=request + "\n",'
  - claim: >-
      Each task emits one `PreflightEvent` with step `claude_md`, which holds
      the SHA-256 hex of the `CLAUDE.md` text read at `base_sha`, or says none
      was found there. The witness drives three cells. In the first the base
      commit's `CLAUDE.md` differs from the working copy's, and the event
      holds the digest of the base text and not the working copy's. In the
      second neither has one, and the event names `CLAUDE.md` and holds no
      64-character hex digest. In the third the base file is empty, and the
      event holds the SHA-256 of the empty string. Today the task emits no
      event about `CLAUDE.md`.
    witness: tests/test_session.py::test_a_task_records_the_sha256_of_claude_md_at_base_or_that_it_found_none
    mutant:
      file: saffron/cell/session.py
      find: spec.base_sha, "CLAUDE.md")
      replace: spec.base_sha, "README.md")
  - claim: >-
      Changing only `CLAUDE.md` at the base commit changes both digests in
      the task's `events.jsonl`. The witness drives three cells with the
      default emit, so each writes its own event log, and reads each log
      back. The cells differ only in the base `CLAUDE.md`. The first two
      carry the same text and the third a different one. The witness pins
      the system prompt file's path to one fixed value across all three
      cells. The first two logs
      hold the same `CLAUDE.md` digest and the same list of request digests.
      The third holds a different `CLAUDE.md` digest, and its request digests
      differ from the first log's at every position. Each list has one entry
      per session, five in all, and matches the requests its double received.
    witness: tests/test_session.py::test_changing_only_claude_md_at_base_changes_both_digests
    mutant:
      file: saffron/cell/session.py
      find: standing_instructions=context.standing_instructions(claude_md),
      replace: standing_instructions="",
  - claim: >-
      For options that carry no string system prompt, the request
      `run_agent` sends still carries the prompt, the options and the resume
      id, and nothing else.
    witness: tests/test_implement.py::test_the_request_carries_the_prompt_the_options_and_the_resume
    preserves: true
  - claim: >-
      IMPLEMENT's system prompt still carries the base commit's `CLAUDE.md`
      and not the working copy's.
    witness: tests/test_session.py::test_the_implement_prompt_carries_claude_md_at_the_base_commit
    preserves: true
---

## Context

Backlog item **b-864a4d**. `DESIGN.md` §5.3 says the host injects the
repo's `CLAUDE.md` into every agent session, read from the mirror at
`base_sha`. §8 makes that file the flywheel's second bucket. Unit tests
assert the injection, and no live run can show it.

This spec's parent is `SA-0139`, and its cell is cut from that spec's
branch. `SA-0139` edits `saffron/phases/implement.py`,
`tests/test_implement.py` and `tests/test_session.py`. It rewrites
`repair_prompt`'s preamble, and it replaces two `test_session.py` checks
that matched on the old preamble text. The line numbers below were read at
`bd888bed`, the head of `SA-0139`'s branch. That head also carries `SA-0140`
and `SA-0129`. Both `SA-0139` and `SA-0140` moved lines in
`saffron/phases/implement.py`, and `SA-0140` moved them in
`saffron/phases/rebut.py`. Find each by its name if your base differs.

What the code does now:

- `run_agent` (`saffron/phases/implement.py:191`) is the one function that
  starts the in-cell runner. It builds the request as a JSON string of the
  prompt, the options and the resume id at `:229-232`. When the options
  carry a string `system_prompt`, it also adds `system_prompt_path`, a
  fresh `/tmp/saffron-system-prompt-<uuid4 hex>` path the runner writes that
  prompt to (`:223-231`). So two requests with a string system prompt never
  match byte for byte. It hands that string to `exec_stream` as the runner's
  stdin at `:275-282`. Every `AgentEvent` it
  emits comes from the runner's stream or from what happens after it ends
  (`:253`, `:258`, `:273`, `:290-301`, `:344-351`). None comes before it.
- Every session reaches `run_agent` through one callable. `_drive_cell`
  binds `implement.run_agent` inside `record_attempts` and
  `stop_on_rejected` at `saffron/cell/session.py:1829-1839`. The plan,
  IMPLEMENT, salvage, repair and notes turns call it at
  `saffron/cell/session.py:499`, `:2012`, `:2094`, `:2280` and `:2350`.
  The lenses get it through `review.run_review`, called at
  `saffron/cell/session.py:2516`. The criterion probe gets it through
  `review.run_criterion_probes`, called at `saffron/cell/session.py:2545`.
  The rebuttal, its extraction turn and the verdicts get it through
  `rebut.run_rebut`, called at `saffron/cell/session.py:2713`.
- The task reads `CLAUDE.md` once, at `saffron/cell/session.py:1655`, with
  `mirror_ops.file_at` at `base_sha`. `file_at`
  (`saffron/repos/mirror.py:231-259`) returns the file's text, follows a
  symlink one hop, and returns `None` when the tree has no such path.
- `_preflight` (`saffron/cell/session.py:1614-1619`) emits each preflight
  step as a `PreflightEvent`. Nothing emits one about `CLAUDE.md`.
- The task row's `prompt_sha` is `context.prompt_sha()`
  (`saffron/cell/session.py:1706`). That digests the prompt templates
  as authored (`saffron/agents/context.py:201-217`), and its docstring
  excludes the assembled prompt. Every task at one Saffron commit gets the
  same value, whatever its `CLAUDE.md` said.
- `context.standing_instructions` (`saffron/agents/context.py:134-152`)
  returns an empty string for a missing or blank `CLAUDE.md`. For any
  other it embeds the text with trailing whitespace stripped. IMPLEMENT
  passes it at `saffron/cell/session.py:1811`, the lenses at
  `saffron/phases/review.py:187`, the criterion probe at `:382`, and the
  verdict at `saffron/phases/rebut.py:262`.

## Problem

Nothing in `events.jsonl` says what prompt a session was given. The item
searched the event logs of `SA-0121` to `SA-0124` for the
standing-instructions heading and found it zero times. So no live cell
shows the `CLAUDE.md` injection. The one prompt digest the ledger holds
cannot tell two tasks' prompts apart.

The change:

1. **`run_agent` records a digest of each request.** It emits one
   `AgentEvent` after it builds the request and before it calls
   `exec_stream`. That event has `raw=False`, no `event` and no `line`.
   Its `detail` names the SHA-256 hex of the request string, all 64
   characters, encoded as UTF-8.
   Hash that string, the exact bytes the runner reads. Never hash a
   re-serialisation or the prompt alone.
2. **Each task records a digest of `CLAUDE.md`.** Beside the read at
   `saffron/cell/session.py:1655`, emit one `PreflightEvent` through
   `_preflight` with step `claude_md`. Its `detail` names the SHA-256 hex of
   the text `file_at` returned, encoded as UTF-8. When `file_at` returned
   `None`, the detail names `CLAUDE.md` and says none was found at base,
   with no digest in it. An empty file is found, and its digest is the
   empty string's.

A reader then pairs the two. The task's `CLAUDE.md` digest names the text
that was read, and each session's request digest names what that session
was sent.

## Out of scope

**The ledger and the record.** No column, no fact kind and no change to
`context.prompt_sha()`. `tasks.prompt_sha` stays the template digest it is.
`saffron/ledger.py`, `saffron/record/**` and `saffron/agents/**` are
`forbidden`.

**A new field on any event kind.** Both digests ride in `detail`, which
`AgentEvent` and `PreflightEvent` already carry. `CONTEXT.md`'s event kind
entry lists kinds, not fields, so no glossary entry changes.

**The prompt text itself.** The digest is what the log keeps. Storing each
request whole would put the spec body, `CONTEXT.md` sections and the diff
into `events.jsonl` on every turn.

**`review.py` and `rebut.py`.** Both hand their sessions the callable
`_drive_cell` built, so the change in `run_agent` reaches them with no
edit.

## Notes for the agent

**Which criteria are new code.** Criteria 1 and 3 add an emission. Each
names a mutant of a line that exists at base, and its witness must catch
that mutant. Criterion 1's mutant changes the string sent to the runner, so a
digest of anything but those bytes fails. Criterion 3's mutant reads a
different file, so a digest not taken from the read fails. Criterion 4's
mutant drops `CLAUDE.md` from IMPLEMENT's system prompt. Criterion 2 relies
on criterion 1's emission, so it declares the same mutant. With a newline
appended, the bytes each double receives no longer hash to the digest
`run_agent` emits, and the equality fails in every cell.

**Commit as each witness passes.** A long cell can reach its turn limit
before its first commit.

**Criterion 1's witness.** Build it on the `_stream` double
(`tests/test_implement.py:144`), which parses stdin into `self.request`.
Keep the raw string as well, or write a double of your own in the test.
Find the digest with a 64-character lowercase hex pattern over each
`Agent` event's `detail`. Assert it is `watched[0]`. The failing turn is a
double returning exit code 1 with no lines, which makes `run_agent` raise
`AgentFailed` (`saffron/phases/implement.py:319-337`). Wrap that call in
`pytest.raises`, and check the events after it. Pass options with no
string `system_prompt`, as `{"max_turns": 3}` is. With one, each request
carries its own random `system_prompt_path`, and the fresh and resumed
digests differ through that path alone, whatever `resume` does.

**A harness option for criteria 2 and 4.** `_drive`
(`tests/test_session.py:1214-1335`) replaces `implement.run_agent` with a
stub that returns each scripted turn (`:1268-1302`). That stub never reaches
the real `run_agent`, so it can observe no request digest. Add a keyword to
`_drive`, a list that is `None` by default. Given a list, the stub calls
the real `run_agent` for each scripted turn. It passes an `exec_stream`
double that appends the stdin string it receives to that list. The double
then feeds two lines back: a `text` event with the turn's text, and a
`result` event built from the turn's `session_id`, `subtype`,
`terminal_reason`, `num_turns` and `is_error`. The turn's `cost_usd_est`
goes under the key `total_cost_usd`, which `run_agent` reads. Pass a
`reap_cell` double too. A scripted `AgentFailed` that carries an
`attempt` goes through the same route, so a turn-ceiling cut raises from
the real `run_agent` as it would live. Any other scripted exception is
raised as today. Leave every other test on the default path.

Bind the real `run_agent` to a module-scope name once. `_drive`
monkeypatches `implement.run_agent`, and a test that calls
`_drive` twice would otherwise capture the first call's stub. The name
exists at base, so the module still collects when `revert` reverts the
source.

**Criterion 2's four cells.** Each goes in its own subdirectory of
`tmp_path`, with its own `_stub_the_runtime` (`tests/test_session.py:900`).
A prototype measured each shape at `f307e83b`, before `SA-0125`, `SA-0126`
and `SA-0128` merged. It was not re-run at this base, so treat each count
as a lead and confirm it against your own double.

- A criterion probe: `_probe_turns` (`tests/test_session.py:6471`) with
  one answer from `_probe_answer` (`tests/test_session.py:6458`) whose
  edit is `None`, and a spec with one `Criterion`. Six
  requests: plan, IMPLEMENT, three lenses, the probe.
- A repair: `suites=([], _results(failing), [])` and three scripted turns.
  Six requests, the third a repair turn.
- A salvage: `commits=[0, 1]`, with the plan turn,
  `implement.AgentFailed("max turns", _cut_off_turn(cost=0.4))` and one
  clean turn, as `tests/test_session.py:1584-1624` does. Six requests.
  `SA-0126` changed how a cut the salvage cannot rescue ends. This
  salvage commits, so the cell still goes on to REVIEW.
- A rebuttal: `_rebuttable` (`tests/test_session.py:3187`) with
  `rebut_commits=1`, over `_ANCHORING_DIFF`. Script `_through_rebut`
  (`tests/test_session.py:3205`) with a rebuttal turn, an extraction block
  and a verdict block, as `tests/test_session.py:5278-5320` does. Eight
  requests.

Collect events with `capture=`. Identify each session kind by the parsed
request's `prompt`. The plan turn carries `implement.PLAN_PROMPT`. IMPLEMENT
carries `implement.IMPLEMENT_PROMPT`, and the salvage turn
`implement.SALVAGE_PROMPT`. Find the repair request as the one whose
prompt starts with `implement.repair_prompt([])`. Match no preamble
wording, which `SA-0139` rewrites. Three lens requests carry `review.REVIEW_PROMPT`, and the probe
`review.CRITERION_PROBE_PROMPT`. The rebuttal turn starts from
`rebut.REBUT_PROMPT`, its extraction carries `rebut.EXTRACT_PROMPT`, and
the verdict `rebut.VERDICT_TURN_PROMPT`. Check the constants' spelling at
your base. Suppose a change emitted a digest only for IMPLEMENT's own
calls in the session module. The lens, probe and rebuttal requests would
then have none, and the in-order equality fails on it.

No cell drives the plan re-prompts (`saffron/cell/session.py:530`, `:563`),
a lens re-prompt (`saffron/phases/review.py:268`) or the notes turn
(`saffron/cell/session.py:2350`). Each calls the same `agent` callable, so
criterion 1 covers them by construction.

**Criterion 3's witness** drives `_drive` three times with `capture=`. Each
cell gets its own subdirectory of `tmp_path` and its own `_stub_the_runtime`.
The witness selects `Preflight` events whose `step` is `claude_md`. Assert exactly one
in each cell. The first cell passes `claude_md` and `base_claude_md`
with different text, as `tests/test_session.py:1521-1537` does. The first
cell's base text must end in `"\n"`, as that test's does. A digest of the
stripped text then differs from the digest of what `file_at` returned. The second
passes neither, so the stub's `file_at` returns `None`. The third passes
`base_claude_md=""`. A check of the form `if not claude_md` reads the empty
file as absent and fails the third cell. Hashing the stripped text fails the
first, through its trailing newline.

**Criterion 4's witness** passes `use_default_emit=True`, so
`run_one_cell` writes `tmp_path/<cell>/out/SY-1/events.jsonl`, and reads it
with `events.read_log`. Script the plan block and one clean turn, so each
cell has five sessions: plan, IMPLEMENT and the three lenses. Use two texts
that differ in more than trailing whitespace, because
`standing_instructions` strips it.

Pin the system prompt file's path before the first cell, and keep it for
all three. Every session in a cell sends a string system prompt, so every
request carries a fresh `uuid4` in `system_prompt_path`. Monkeypatch
`implement.uuid` with a stand-in whose `uuid4` returns one fixed `UUID`.
Nothing else under `saffron/` uses `uuid`. Leave the hashed bytes as they
are. The rule stays to hash the exact string the runner reads.

The pin is what lets the mutant die. Unpinned, the first two logs differ at
every position, and the witness cannot pass at head. Worse, the third log
differs from the first at every position under the mutant too, so the
`standing_instructions=""` mutant survives that half. Pinned, the plan and
IMPLEMENT requests share one options dict (`saffron/cell/session.py:499`
and `:1813`). They carry `CLAUDE.md` in all three cells. The mutant drops it
from both, so their positions match between the first and third logs, and
the witness fails on them.

The prototype measured the first two logs equal and every position of the
third different. That was at `f307e83b`, before `SA-0140` added the random
path, and it was not re-run at this base.

**Criterion 5 and `system_prompt_path`.** Its witness
(`tests/test_implement.py:523`) sends `{"max_turns": 3}`, so the key is
never added. Keep `system_prompt_path` for a string system prompt, since
the runner reads its prompt from that file. Criterion 2 needs no pin,
because each cell compares a digest with the bytes its own double received.

**Existing tests this changes.**

- `tests/test_implement.py:218` asserts `len(watched) == 4` for a turn of
  four stream lines. The digest makes it five. Update the number and the
  comment above it. Keep the test's name.
- `test_watch_output_matches_the_golden_fixture`
  (`tests/test_events.py:1777-1805`) drives two cells whose repo has no
  `CLAUDE.md`, so each now opens with the new preflight line. Regenerate
  `tests/fixtures/watch-golden.txt` from the run and read the diff. It
  adds those two lines and nothing else. The comment at
  `tests/test_events.py:1747` counts the `preflight:` steps the fixture
  captured, so correct it.
- `test_the_join_covers_every_captured_line_a_kind_renders`
  (`tests/test_events.py:2012-2050`) fails on a captured line that no
  `_JOINED` row (`:1824`) reproduces. Join the new `preflight:` line inline
  in that test, beside `per_gate`, as its docstring prescribes. Render
  `describe` of a `Preflight` with step `claude_md` and the detail your code
  writes, and exclude that line from `unchecked`. Add no `_JOINED` row. A row
  is a new parametrised test id, so `revert` runs it with the source
  reverted. It passes there, because `describe`'s catch-all `Preflight`
  branch (`saffron/events.py:729`) exists at base, and `revert` blocks.
- `FAMILIES` in `saffron/events.py` gains two rows, one per new line shape.
  The `agent:` digest line cites `_IA`, and the `preflight:` line cites
  `_S`. Each prefix must differ from every other row's.
  `test_the_table_did_not_quietly_lose_a_row`
  (`tests/test_events.py:1206`) pins the count. This spec adds two to the
  65 it reads at base. Its
  docstring is at the ten-line limit `prose` enforces, so rewrite it within
  ten lines, naming this spec beside the others.

A prototype of the change ran the full suite at `f307e83b`. Only the first
two tests above failed, apart from the prototype's own lint. That run predates
`SA-0125`, `SA-0126` and `SA-0128` and was not repeated.

**Callers that need nothing.** Four other tests call `run_agent`, and none
counts the events it emits. They are at `tests/test_agent_runner.py:321`
and `tests/test_events.py:2315`, `:2462` and `:2508`. The first starts a
real cell and reads no event at all. The prototype ran the other three
green at `f307e83b`. `saffron/projection.py:181-183` reads only `Ceilings`, `PhaseStart` and
`Teardown` from the log.

**Import nothing at module scope that this change adds.** `revert` runs the
new tests with the source reverted. An import of a new name is then a
collection error, which it reads as `skip`. `hashlib` and `re` are standard
library and are fine.

**Size.** The prototype measured 186 changed lines before `ruff format` and
docstrings: 16 in source, 139 in `tests/test_session.py` and 31 in
`tests/test_implement.py`. Formatted, with the fixture, the inline join,
the two `FAMILIES` rows and docstrings, expect about 330 lines. The `size`
gate counts tokens, with `feature` at 3000 (`saffron/gates/core/size.py:26`).
Where it counts a line it uses `_TOKENS_PER_LINE = 4` (`size.py:39`), so this
is about 1,300 to 1,450. `size` blocks at `elevated`, which
`saffron/cell/session.py` makes this task.

**Prose.** Each touched file's `prose` count must not rise. New comments and
docstrings take no em-dash, semicolon, contraction, perfect tense or hedge.
Keep a docstring within ten lines and a comment within two. Check each file
with `python3 hooks/prose_limit.py --file <path>`.
