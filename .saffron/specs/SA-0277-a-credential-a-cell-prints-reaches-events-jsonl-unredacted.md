---
id: SA-0277
title: A credential a cell prints reaches events.jsonl unredacted, and PACKAGE's credential shapes live where only PACKAGE reads them
type: feature
priority: 2
depends_on: [SA-0276, SA-0271, SA-0268]
estimated_lines: 431
estimate_measured: true
touches:
  - saffron/credentials.py
  - saffron/events.py
  - saffron/phases/package.py
  - saffron/task.py
  - tests/test_credentials.py
  - tests/test_task.py
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
  - saffron/cli.py
  - saffron/cell/**
  - saffron/gates/**
  - saffron/repos/**
  - saffron/watch.py
  - saffron/scheduler.py
  - saffron/ledger.py
  - tests/test_events.py
  - tests/test_package.py
  - tests/test_scheduler.py
budget_usd: 58
max_attempts: 3
max_turns: 190
acceptance:
  - claim: >-
      Every credential shape PACKAGE refuses is redacted from an `Agent`
      event before `EventLog.append` writes it. The witness drives each
      shape inside an event's text. They are an Anthropic API key, an
      Anthropic OAuth token, a GitHub token under each of its five
      prefixes `ghp_`, `gho_`, `ghu_`, `ghs_` and `ghr_`, an AWS access
      key id, and a private key block with one body line. For each one,
      PACKAGE's prose scan still returns exactly that shape's description,
      and the written file holds neither the credential nor that body
      line. The event read back keeps its other keys, the text on
      both sides of the credential, and a `redacted` field naming that
      shape's description alone. The witness then drives two key blocks
      with no END line. One is a header and four body lines inside a
      `tool_use` input, cut at 200 characters and ending in the marker
      `agent_runner.py`'s clip appends. The other is a raw `line` holding
      the header alone. Each is written with neither the header nor a whole
      body line, and `redacted` names the private key block.
    witness: tests/test_credentials.py::test_every_shape_package_refuses_is_redacted_from_the_log
    wrong_versions:
      - A private key block redacted at its header line alone, so the key's body is written.
      - The GitHub shape narrowed to one prefix when it moves.
      - A marker that names a generic credential rather than the shape's description.
      - A description reworded when the shapes move, so PACKAGE's refusal note changes.
      - An event that carried a credential written with `event` set to `None`, so the evidence is lost.
      - A block pattern that requires an END line, so a clipped block or a lone header is written whole.
      - A block body limited to key characters and anchored at the end of the string, so the clip's marker stops the match.
  - claim: >-
      Redaction reaches every cell-authored place in an `Agent` event. The
      witness puts one AWS access key id in each of seven places. They are
      a top-level string value of `event`, a value in a dict nested in it,
      an element of a list in it, a dict key, a raw `line`, `detail`, and
      the innermost string of a list nested 999 deep inside an event too
      large to keep whole. Each is written without the credential, with
      the text around it, and read back with `redacted` naming the shape.
      An eighth event carries two AWS key ids in one string and a third in
      `detail`, and its `redacted` names the shape once. An event carrying
      no credential reads back equal to the one appended.
    witness: tests/test_credentials.py::test_an_agent_events_credentials_are_redacted_in_every_field
    wrong_versions:
      - Only the top level of `event` walked, so a nested dict or a list keeps its credential.
      - Dict values walked and keys left alone.
      - The raw `line` left unredacted.
      - The `detail` field left unredacted.
      - One `redacted` entry per match, so a shape found three times is named three times.
      - A recursive walk, so the 999-deep event raises `RecursionError` and is never written.
      - A recursive walk that falls back to the unredacted event on `RecursionError`.
      - The marker written as an extra JSON key rather than a dataclass field, so `read_log` drops it.
  - claim: >-
      The cell's own token is redacted when `EventLog` is handed it, under
      PACKAGE's length guard. The witness hands a token of no listed shape
      and places it in a nested `event` value, a raw `line` and `detail`.
      Each is written without it and read back with `redacted` naming the
      cell's own `CLAUDE_CODE_OAUTH_TOKEN`. It then hands `None`, an empty
      token and an eight-character token found in the text. Each event
      reads back equal to the one appended, and PACKAGE's prose scan finds
      nothing in that text either.
    witness: tests/test_credentials.py::test_the_cells_own_token_is_redacted_under_packages_length_guard
    wrong_versions:
      - The token check copied without its length guard, so an empty token rewrites every string.
      - The guard written as at least eight characters, so the eight-character token is redacted.
      - The token redacted in `event` alone, so `line` and `detail` keep it.
  - claim: >-
      For a parsed event, redaction runs before the size bound, so a
      credential the bound's cut would split is never written in part. The
      witness places a GitHub
      token so the cut at `BOUND_CHARS` falls ten characters past its
      prefix, and an Anthropic API key in the event's `model`. The event
      reads back bounded. The file holds neither the token's first
      fourteen characters nor the key, its `usage` holds no key, and
      `redacted` names both shapes.
    witness: tests/test_credentials.py::test_a_credential_cut_by_the_size_bound_is_redacted_whole
    wrong_versions:
      - The bound applied first and its slice redacted after, so a cut token too short for its shape is written.
      - The `usage` copy taken from the event before it was redacted.
  - claim: >-
      `describe` names what was redacted for an `Agent` event read back from
      the log, even when the credential sat past the line's own cut. The
      witness drives each of the four shapes `describe` renders an `Agent`
      in, bounded, raw, a parsed event and `detail`. Each has the credential
      600 characters in. Each line names the shape's description and holds
      no credential. A raw line with nothing redacted renders without any
      mention of redaction.
    witness: tests/test_credentials.py::test_a_redacted_event_read_back_says_what_was_redacted
    wrong_versions:
      - The marker rendered only for a parsed event, so a bounded, raw or `detail` line hides it.
      - The marker never rendered, so the redaction is visible only past the terminal's cut.
  - claim: >-
      The credential shapes are spelled in one module, `saffron/credentials.py`,
      which PACKAGE and `EventLog` both read. The witness takes each of the
      five shapes' regex source text and finds it in that file and in no
      other file under `saffron/`.
    witness: tests/test_credentials.py::test_the_credential_shapes_are_spelled_in_one_module
    wrong_versions:
      - "`package.py` keeps its own copy of a shape beside the shared one."
  - claim: >-
      `run_task` hands its log the token it was given, and never reads the
      environment for it. The witness runs `run_task` with that variable
      unset and a token of no listed shape. Its cell double emits a raw line
      carrying the token. The task's `events.jsonl` holds no token, and the
      event read back names the cell's own token in `redacted`.
    witness: tests/test_task.py::test_run_task_redacts_the_cells_own_token_from_its_log
    mutant:
      file: saffron/task.py
      find: EventLog(out_dir / spec.id, token=token)
      replace: EventLog(out_dir / spec.id)
    wrong_versions:
      - "`run_task`'s default log built without the token, so only shapes are redacted."
      - The log reading `CLAUDE_CODE_OAUTH_TOKEN` from the environment instead of the token `run_task` holds.
  - claim: >-
      PACKAGE still refuses a patch carrying a credential before anything
      is pushed, and its note names the file and never the value.
    witness: tests/test_package.py::test_a_credential_in_the_patch_is_refused_before_anything_is_pushed
    preserves: true
  - claim: >-
      PACKAGE's patch scan still finds the cell's own token and never
      echoes it.
    witness: tests/test_package.py::test_the_cells_own_token_is_found_and_never_echoed
    preserves: true
  - claim: >-
      An event the size bound keeps today is still written, a list nested
      1000 deep included.
    witness: tests/test_events.py::test_carried_counts_are_held_to_their_own_bound
    preserves: true
---

## Context

Backlog item **46**, which cites `DESIGN.md` §5.4 and §9. Every line number
below was read at `bc879e2c`.

**The decision.** The item records that `events.jsonl` is evidence, so it
takes a size cap and must come within reach of a credential scan. The size
half is done. `BOUND_CHARS` is 8192 (`saffron/events.py:61`), and
`EventLog.append` cuts an oversized `Agent` event to a slice of its
serialization (`saffron/events.py:452-462`). The secrets half is open. No
`secrets` gate exists, and the name is only reserved
(`saffron/repos/policy.py:30`). The operator settled the arm. Redact at
`EventLog.append` with PACKAGE's own shapes and token check, moved into one
module both read. Record each redaction in the event, never the value.

**What PACKAGE has today.** `_CREDENTIAL_SHAPES` lists five shapes, each a
description and a compiled pattern (`saffron/phases/package.py:61-70`).
`find_credentials` scans a patch's added lines and `find_credentials_in_text`
scans prose (`saffron/phases/package.py:267-275`). Both reach `_scan`
(`saffron/phases/package.py:278-292`). Per line, `_scan` checks the literal
token first, under a length guard, `token and len(token) > 8 and token in
line` (`saffron/phases/package.py:285`). It reports the cell's own token and
moves on. Otherwise it reports the first shape that matches. Six call sites
refuse on a hit (`saffron/phases/package.py:790`, `:795`, `:914`, `:1127`,
`:1129`, `:1172`). The shape of a private key is its header line alone
(`saffron/phases/package.py:69`). That is enough to refuse a patch, but a
redaction that replaced only the header would write the key.

**What reaches the log.** `Agent` carries a parsed cell event under `event`
and a raw line under `line` (`saffron/events.py:292-323`). Its `detail` is
host text that can quote the cell runtime's stderr. `EventLog.__init__`
takes the task directory alone (`saffron/events.py:434`). `append` bounds an
oversized event and copies its counts and `model` into `usage`
(`saffron/events.py:452-462`). Every read of the cell's dict sits inside one
`try`, so `append` never raises. A test appends a list nested 1000 deep and
expects it written (`tests/test_events.py:1001`, `:1013`). `describe`
renders an `Agent` in four shapes, bounded, raw, parsed and `detail`
(`saffron/events.py:845-855`).

**Who holds the token.** `run_task` takes `token` (`saffron/task.py:444`).
When its caller passes no `emit`, it builds `EventLog(out_dir / spec.id)`
(`saffron/task.py:478`) and prints each line before it appends
(`saffron/task.py:482-489`). Both `saffron cell` and `saffron batch` call it
that way, reading `CLAUDE_CODE_OAUTH_TOKEN` at the edge
(`saffron/cli.py:567`, `:615`), as does the stack runner (`:657`).

## Problem

A cell's stdout reaches `events.jsonl` verbatim, inside `BOUND_CHARS`. A
credential the cell prints is written to the host's disk and scanned by
nothing. Make these changes.

1. **One module for the shapes.** Write `saffron/credentials.py`. Move the
   five shapes there as a module-level tuple named `CREDENTIAL_SHAPES`, of
   `(description, compiled pattern)` pairs, with the descriptions word for
   word. Move the literal-token check there as one function, its length
   guard unchanged. Add one function that redacts a string. It replaces
   the token, when the guard admits it, and every match of every shape. It
   returns the new string and the description of each kind it replaced.
   For the private key shape, replace from the header through the next
   `-----END ... PRIVATE KEY-----` line, or to the end of the string when
   none follows.
2. **PACKAGE reads it.** `_scan` keeps its behaviour exactly, token first
   and then the first matching shape, and reads both from the new module.
   No shape stays in `package.py`.
3. **`EventLog` redacts.** `EventLog.__init__` takes a keyword-only
   `token`, default `None`. Add a field `redacted: tuple[str, ...]`, default empty,
   to `Agent`. In `append`, before the size bound and inside its `try`,
   redact an `Agent` event's `event`, `line` and `detail`. Walk `event` at
   every depth, dict keys included. When anything was replaced, the event
   written carries the redacted fields and `redacted` names each
   description once. An event with nothing to redact is written as it was.
4. **`describe` says so.** For an `Agent` with a non-empty `redacted`,
   each of the four lines ends by naming what was redacted.
5. **`run_task` hands over its token.** Its default `EventLog` takes the
   `token` argument `run_task` already holds.
6. **`Agent`'s docstring stops claiming verbatim.** Its second sentence
   calls `event` verbatim and says `original_chars` names the event's full
   size (`saffron/events.py:294`, `:303-304`). Say instead that
   `event` is verbatim except where a credential was redacted, and that
   `original_chars` counts the serialization after redaction. Two other
   texts say the copied `usage` is `kept verbatim` (`saffron/events.py:312`,
   `:413-414`). It is copied from the redacted dict, so say it is kept as
   redacted.

## Out of scope

- **The `secrets` gate.** §5.4 still reserves it, and no gate is added.
- **The terminal line.** Both default emitters print `describe` of the
  event before `append` redacts a copy (`saffron/task.py:482-489`,
  `saffron/cell/session.py:107-110`). That line stays unredacted.
- **Other event kinds.** A `PhaseStart`, `Teardown`, `Terminal` or
  `Preflight` detail can quote cell text (`saffron/events.py:690-691`), and
  none is redacted here.
- **A private key on raw stdout.** Each stdout line that is not an event
  becomes its own `Agent` with `raw=True` (`saffron/events.py:295-297`). The
  header's line is redacted, but each body line is its own event and
  matches no shape, so it is written.
- **A raw line cut before `append`.** `_quarantined` slices a raw line at
  `BOUND_CHARS` before it ever reaches `append`
  (`saffron/phases/implement.py:224`, `:239`). A credential straddling that cut is
  written in part when what is left matches no shape.
- **A credential the cell clipped.** `agent_runner.py` cuts every string in
  a tool input at 200 characters (`images/agent_runner.py:25`, `:78-79`). A
  credential cut there short of its shape's length is written in part.
- **Two keys that redact alike.** A dict whose two keys redact to one
  placeholder keeps one of the two values.
- **Logs built without the token.** The spec-session log,
  `EventLog(log_dir)` (`saffron/cli.py:944`), redacts the shapes only.
  So do the defaults `EventLog(out_dir / spec.spec_id)`
  (`saffron/cell/session.py:959`) and `EventLog(outcome.task_dir)`
  (`saffron/phases/package.py:646`, `:1093`). A token of the `sk-ant-oat`
  form still matches the Anthropic OAuth shape there. This spec did not
  measure the form of a live token.
- **More shapes.** A shape not in the five passes both readers, as
  `DESIGN.md` §5.7 already says.
- **`DESIGN.md`.** §4.7's paragraph on this redaction is written by hand in
  the pull request that adds this spec.

## Notes for the agent

**Edit or new.** The module, the walk, the field and the `describe` suffix
are new code. So criteria 1 to 6 declare a witness and no mutant.
Criterion 7 edits one existing call, whose spelling step 5 and step 3
determine, so it declares a mutant. The three `preserves` witnesses exist
at your base and pass there.

**Your base.** This spec stacks on `SA-0271`, which edits
`saffron/phases/package.py` in its gate-only cell, and `SA-0268`, which edits
`saffron/task.py`. Neither touches the scan or the default `EventLog`, but
read both files at your base before you edit them.

**Walk with a loop.** A recursive walk raises at 1000 levels, and `append`
then drops an event it writes today. Build new containers rather than
editing the caller's dict.

**Test tokens.** Build each credential at run time from pieces, as
`"sk-ant-" + "api03-" + ...`, so no line of a test is itself a credential.
For the token criteria, use a token that matches none of the five shapes,
so only the literal check can catch it. Each witness reads the written file
as text and reads it back with `read_log`.

**Criterion 4's arithmetic.** Put `text` before `model` in the event. Then
the test can compute the token's position in `json.dumps` from
`BOUND_CHARS` and the prefix before `text`'s value.

**Criterion 5's witness** puts 600 characters before each credential.
`describe` cuts text with `_clean(text, 160)` and a detail at
`_DETAIL_BOUND = 500` (`saffron/events.py:708`, `:699`). So the placeholder
in the content never reaches the line, and only the marker can name the
redaction.

**Imports in the new tests.** Each test in `tests/test_credentials.py`
imports a name the change adds inside its own body, never at module scope.
So does the new test in `tests/test_task.py`. That covers `saffron.credentials` and
anything else this spec adds. A module-scope import of such a name makes
the reverted run a collection error, which `revert` reads as `skip`.

**Criterion 6's witness** reads each pattern's `.pattern` and searches every
`*.py` under `saffron/` for it as text.

**`tests/test_task.py`.** `_drive` passes `token=None` to `run_task`
(`tests/test_task.py:100`). Give it a `token` keyword, default `None`, that
it passes instead. `_FailFirst` and `_FailAfterTwo` subclass `EventLog` with
`__init__(self, task_dir)` (`tests/test_task.py:527`, `:577`). Let each
accept and pass on the new keyword. The `_drive` double returns the outcome
it was built with. It emits only the events it was handed. So the witness
patches `push_unpackaged_work` with `_push` and drives an `EXHAUSTED` state.
It unsets `CLAUDE_CODE_OAUTH_TOKEN` with `monkeypatch.delenv(...,
raising=False)`.

**The `prose` gate.** `saffron/credentials.py` and `tests/test_credentials.py`
start at zero. PACKAGE's three-line `ponytail:` comment moves with the
shapes, so rewrite it in two lines and keep the `ponytail:` mark. `Agent`'s
docstring is already past ten lines. Keep it no longer than today, or its
length hit counts as new. Name the new field in a one-line comment above
it. The gate keys a hit on its sentence's text, so step 6 makes the edited
sentence a new hit unless you rewrite it clean. Split it into sentences of
25 words or fewer, with no em dash and no semicolon.

**The `dead` gate.** `redacted` counts as used only because `describe`
reads it, which is step 4.

**Size.** A prototype at `e30fa26f` measured 1725 changed tokens with
`size_gate`, and `estimated_lines` is that over four. It held all six
steps above, the seven new witnesses and the `test_task.py` edits. Its
step 6 rewrote the docstring's first thirteen lines clean and changed the
two `usage` texts, with no new `prose` hit. Every
wrong version listed above failed its witness there, and each new witness
failed with the source reverted.
