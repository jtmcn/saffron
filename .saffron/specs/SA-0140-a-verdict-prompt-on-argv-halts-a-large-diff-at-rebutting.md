---
id: SA-0140
title: A session's system prompt reaches the agent CLI on its argument list, so a large verdict prompt cannot start and the task halts at `REBUTTING`
type: bug
priority: 1
depends_on: []
touches:
  - images/agent_runner.py
  - saffron/phases/rebut.py
  - tests/test_agent_runner.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - .saffron/**
  - ontology/**
  - docs/**
  - harness/**
  - records/**
  - images/cell-base.python.Dockerfile
  - images/proxy.Dockerfile
  - saffron/phases/implement.py
  - saffron/phases/review.py
  - saffron/phases/package.py
  - saffron/cell/**
  - saffron/events.py
  - saffron/gates/**
  - saffron/task.py
  - saffron/batch.py
  - saffron/cli.py
  - tests/test_rebut.py
  - tests/test_implement.py
  - tests/test_session.py
  - tests/test_events.py
budget_usd: 18
max_attempts: 3
max_turns: 120
acceptance:
  - claim: >-
      `agent_runner.py` hands the SDK a string system prompt as exactly
      `{"type": "file", "path": p}`, never as a string, so the SDK puts only
      a path on the agent CLI's argument list. `p` is an absolute `str`
      outside the session's `cwd`, with the runner started in that `cwd` as
      production starts it. The witness drives two requests. One carries a
      verdict prompt built by `rebut.verdict_prompt` from a diff of at least
      200 KB holding a non-ASCII character. The other carries a
      one-character prompt and a `resume`. For each, the file's bytes, read
      while the SDK runs, decode as UTF-8 to the prompt exactly. The file is
      gone once the runner returns, and every other option reaches the SDK
      unchanged. A third request carries no system prompt. Its session still
      reaches the SDK, and the SDK receives no `system_prompt` option.
    witness: tests/test_agent_runner.py::test_the_runner_hands_the_sdk_a_system_prompt_file_never_a_string
  - claim: >-
      A verdict session that never started ends REBUT `GATE_ERROR`. Never
      started means the runner's `error` event records that `query` yielded
      no message. The `why` names that lens and carries the runner's error,
      and names no other lens. The witness drives it after a lens that
      returned a valid verdict set, in the same test process, and before a
      lens whose session yielded a message that prints nothing, then raised.
      It also drives the reverse order, that started lens first and the
      never-started lens after it. Any other verdict session with no verdict still leaves REBUT at
      `REBUTTING`. The witness drives two of those: that silent message then
      the never-started lens's exception, and a bound kill with no output.
    witness: tests/test_agent_runner.py::test_a_verdict_session_that_never_started_ends_rebut_gate_error
  - claim: >-
      A verdict session that ran and returned output that is not the schema
      still leaves REBUT at `REBUTTING`.
    witness: tests/test_rebut.py::test_a_verdict_that_is_not_the_schema_is_not_a_clean_verdict
    preserves: true
  - claim: >-
      A verdict session that ran and left a blocker unverdicted still leaves
      REBUT at `REBUTTING`.
    witness: tests/test_rebut.py::test_a_lens_that_leaves_a_blocker_unverdicted_has_not_withdrawn_it
    preserves: true
---

## Context

Backlog item **b-8487de**, found in the spec loop's run 15 on `SA-0128`
(#483). The adequacy lens raised a blocker, and REBUT fixed it. The lens's
verdict session then failed with `CLIConnectionError: Failed to start Claude
Code: [Errno 7] Argument list too long`. The task was left `REBUTTING` with
$19.75 of $24 spent. The operator judged the rebuttal by hand.

**How a system prompt reaches the agent CLI today.** The host writes one JSON
request to the runner's stdin, `json.dumps({"prompt": prompt, "options": options, "resume": resume})`
(`saffron/phases/implement.py:219`). Its options carry the system prompt as a
string, `"system_prompt": system_prompt` (`saffron/phases/implement.py:109`).
The runner passes those options to the SDK unchanged
(`images/agent_runner.py:162`, `:167-169`). The runner starts in `/work`, by
`workdir=WORKTREE_MOUNT` (`saffron/phases/implement.py:267`). The cell pins
`claude-agent-sdk==0.2.142` (`images/cell-base.python.Dockerfile:33`).

**Read in that wheel on 2026-09-23.** The file is
`claude_agent_sdk-0.2.142-py3-none-macosx_11_0_arm64.whl`, sha256
`194a5936c3b0f7d92846b28c017887aa5c1ec290392ab1c5af1f956d1e227675`. Paths are
inside the `claude_agent_sdk` package. The Python sources are what the cell's
Linux wheel installs too, but only the macOS wheel was read.

- `_internal/transport/subprocess_cli.py`, lines 568 to 579, in
  `_build_command`:

  ```
  if self._options.system_prompt is None:
      cmd.extend(["--system-prompt", ""])
  elif isinstance(self._options.system_prompt, str):
      cmd.extend(["--system-prompt", self._options.system_prompt])
  else:
      sp = self._options.system_prompt
      if sp.get("type") == "file":
          cmd.extend(["--system-prompt-file", cast(SystemPromptFile, sp)["path"]])
  ```

- `types.py`, lines 60 to 64, declares `SystemPromptFile` with the keys
  `type: Literal["file"]` and `path: str`. Line 1967 reads
  `system_prompt: str | SystemPromptPreset | SystemPromptFile | None = None`.
- `_internal/client.py`, lines 172 to 180, writes a string `prompt` to the
  CLI's stdin as `{"role": "user", "content": prompt}`. The turn prompt never
  travels on argv.
- `_internal/transport/subprocess_cli.py`, line 893:
  `error = CLIConnectionError(f"Failed to start Claude Code: {e}")`, inside
  the `except Exception` around the spawn. That is the incident's text.
- `_internal/message_parser.py`, line 226, parses a `system` line into a
  `SystemMessage` with `subtype` and `data` (`types.py`, line 1134). The runner
  prints one as `{"type": "system", "subtype": ...}`
  (`images/agent_runner.py:148-155`).
- `_cli_version.py` reads `__cli_version__ = "2.1.237"`. The bundled binary's
  strings include `--system-prompt-file <file>` and `Error: Cannot use both
  --system-prompt and --system-prompt-file`.

Linux's `MAX_ARG_STRLEN` caps one argument string at 32 pages, 128 KiB on
4 KiB pages. That is the kernel's constant, not measured in a cell. The verdict
prompt carries two diffs, the spec and the vocabulary
(`saffron/phases/rebut.py:214-259`), so it crosses that first.

**What happens when a verdict session cannot start.** `run_verdict` catches
`implement.AgentFailed` and returns a `LensVerdicts` with `error` set
(`saffron/phases/rebut.py:286-288`). `rebut_state` returns `REBUTTING` for any
lens with an error (`saffron/phases/rebut.py:331-332`). `run_rebut` already
ends `GATE_ERROR` for one critic-cell fault charged to nobody
(`saffron/phases/rebut.py:546-550`). REBUT's state becomes the task's, by
`outcome, why = result.state, result.why` (`saffron/cell/session.py:2776`)
and `ledger.set_task_state(task_id, outcome)` (`:2789`). `saffron cell` exits `2`
for `GATE_ERROR` (`saffron/cli.py:62`).

**Telling "never started" from "ran" today.** `AgentFailed` carries a message
and an attempt (`saffron/phases/implement.py:54-71`). A session killed by a
bound before any result reaches `run_verdict` in the same shape, through
`if not result:` (`saffron/phases/implement.py:302`). So
`run_verdict` cannot tell them apart from what it catches. Every line the
runner prints does reach `run_verdict`'s `emit`, as an `events.Agent` whose
`event` is the parsed dict (`saffron/phases/implement.py:260`). The line
order cannot say whether a message arrived either. An assistant message
whose content is empty gives `evts = [_block_event(block) for block in blocks]`
an empty list and prints nothing (`images/agent_runner.py:128-140`). Only the
runner sees `query` yield.

## Problem

Every session goes through `agent_runner.py`, REVIEW's lenses included. So
any system prompt past the argument limit fails to start, and the verdict
prompt is the first to reach it. When a verdict session cannot start, REBUT
reports an unjudged rebuttal. That reads as the task's own halt. It is an
infrastructure failure charged to nobody, which `GATE_ERROR` exists to name
(§3.3). `GATE_ERROR` is in the batch breaker's `ABORT_STATES`
(`saffron/batch.py:49`). So a verdict session that never started now counts
toward the two consecutive aborts that stop a night.

## Out of scope

**`DESIGN.md` §3.3.** Its `GATE_ERROR` line now names a verdict session
that never started. `DESIGN.md` is `protected`, so that edit landed by hand
with this spec.

**REVIEW's lens sessions and REBUT's rebuttal turn.** Part one fixes their
argument list too. What state each ends in when its session never starts is
unchanged here.

**A runner that never reports.** A session killed before the runner prints
anything still leaves REBUT at `REBUTTING`. Criterion 2 drives that ending to
keep it there. Treating it as never started would call a bound kill
infrastructure.

**Other neighbours of a never-started lens.** Criterion 2 drives one beside
a valid verdict set and beside a session that raised after a message. One
beside output that is not the schema, a short verdict set or a bound kill is
not driven. The branch sits ahead of every errored-lens reading, so each
still ends `GATE_ERROR`.

**An empty system prompt.** No witness drives `""`. `agent_options` is always
given a non-empty one.

**What the CLI does with the file.** The witnesses show the SDK receives the
file form. Nothing here shows that the agent CLI 2.1.237 reads the file and
uses its contents. The operator's first live run measures that, in the
cell-marked test below and in a cell. The operator runs
`uv run pytest -m cell tests/test_agent_runner.py` on the cell's branch
before merging. That test's `init` assertion is unmeasured until then.

## Notes for the agent

**New code, so witnesses and no mutants.** Neither the file reference nor
the never-started branch exists at base. No text exists for a mutant to name.
Criteria 3 and 4 are `preserves` and name tests that exist.

**Why a session that ran stays at `REBUTTING` (§5.6).** A lens confirms or
withdraws each blocker in a fresh session. One that ran and returned no
usable verdict is the critic's output, not infrastructure. It is not the
task's failure either, so `EXHAUSTED` is wrong. §5.6 already halts a rebuttal
that recorded nothing at `REBUTTING`, because §3.3 has no state for it. A
session that ran and produced nothing usable is the same shape. A session
that never started produced no output of any kind, so no model is to blame.

**Part one.** In `agent_runner.py`, write a string system prompt to a file
from `tempfile`, whose default directory is absolute and outside `/work`.
Write the UTF-8 bytes. Pass the SDK `{"type": "file", "path": <str>}` in its
place. Unlink the file in a `finally` once `query` is exhausted. REVIEW's
lenses share one critic cell, and REBUT's verdict lenses share another. A
file left in `/tmp` is one a later lens can read with `Glob` and `Read`
(`saffron/phases/review.py:35`). Leave a request with no system prompt as it
is. The host keeps sending a string, so `implement.agent_options` and every
caller stay unchanged.

**Part two, in the runner.** Record whether `query` yielded any message.
Reset it at the start of each run. Put that flag on the `error` event `main`
prints, spelled as you like. One runner process is one session in
production. The witnesses call `main` many times in one process, so a flag
never reset carries the last session's answer.

**Part two, in `rebut.py`.** Wrap the `emit` `run_verdict` passes to `agent`,
forward every event, and read the flag off the runner's `error` event. An
`events.Agent` carries a runner event under `event`. The wrapper must pass
over an `events.Agent` whose `event` is `None`, such as a reap line, a
quarantined raw line or a stub's event. Run B's reap produces one. A session whose stream
holds no `error` event carrying the flag did not report never starting, so
it stays `REBUTTING`. Record the fact on `LensVerdicts`, as a field with a
default. `tests/test_package.py`, `tests/test_report.py` and
`tests/test_task.py` build one by keyword. Give `rebut_state` a branch ahead
of `if errored := [v.lens for v in verdicts if v.error]:`
(`saffron/phases/rebut.py:331`). `saffron/phases/implement.py` stays
unedited, because `SA-0133` rewrites `run_agent` and lists that file in its
`touches`.

**The stub SDK.** Neither witness imports the real SDK, which the host does
not install. Put a stub module under the name `claude_agent_sdk` with
`monkeypatch.setitem(sys.modules, ...)`. It needs `ClaudeAgentOptions`, which
records its keyword arguments, and a `query` async generator. Drive the runner
in-process through its `main`, with `sys.stdin` patched to the request and
stdout captured. The module-scope `runner` in `tests/test_agent_runner.py`
serves. `.saffron/rules/agent-sdk-import-is-runner-only.yml` matches import
statements and `import_module` calls, not a `sys.modules` key.

**Witness 1.** Build each request with `run_agent`'s own
`json.dumps({"prompt": prompt, "options": options, "resume": resume})`
(`saffron/phases/implement.py:219`), with options from
`implement.agent_options` and `cwd` set to a directory under `tmp_path`.
`monkeypatch.chdir` into that `cwd` before calling `main`. The stub's `query`
reads the file's bytes before it yields a result message, since the agent CLI
reads it at spawn. Assert the value equals `{"type": "file", "path": path}`,
that `path` is a `str` and absolute, and that it does not resolve under
`cwd`. After `main` returns, assert the file no longer exists. For the
request with no system prompt, assert `system_prompt` is absent from the
keyword arguments the stub recorded.

**Witness 2.** Drive `rebut.run_rebut` with one anchored blocker per lens. Its
`agent` double answers a call carrying `resume` with scripted rebuttal turns.
It routes each verdict call through `implement.run_agent`, forwarding the
`emit` it is given. Pass `exec_stream` a double that runs the runner in-process
on `stdin_data` and feeds each line to `on_line`. Pass `reap_cell` a double
too. Script the stub's sessions in lens order:

1. Run A. `correctness` returns a valid verdict set. `contract` raises
   `CLIConnectionError("Failed to start Claude Code: [Errno 7] Argument list
   too long")` before it yields anything. `adequacy` yields an assistant
   message with empty content, then raises the same exception. Assert
   `GATE_ERROR`, and a `why` holding `contract` and `Argument list too long`
   but neither other lens.
2. Run B, with `correctness` and `contract` blockers only. `correctness` is
   run A's `adequacy` session. For `contract`, the `exec_stream` double
   prints nothing and returns a `wall` bound kill. Assert `REBUTTING`.
3. Run C, with `correctness` and `contract` blockers only. `correctness` is
   run A's `adequacy` session, and `contract` is run A's `contract` session.
   Assert `GATE_ERROR`, and a `why` naming `contract` but neither other lens.

Define the stub's `CLIConnectionError` yourself. The runner only renders its
class name and message (`images/agent_runner.py:181`).

**Measured against a prototype on 2026-09-23.** The operator's delegate built
the change and both witnesses in a scratch copy, outside this repo. With the
two source files reverted, both witnesses failed. Each wrong version below
then failed its witness and passed the other.

**Wrong versions the witnesses must kill:**

- A runner that writes a file only for a prompt above some size.
- A runner that passes the prompt as a `preset` with `append`.
- A prompt file at a relative path, or anywhere under the session's `cwd`.
- A value with another key, or a `pathlib.Path` for `path`.
- A prompt file removed before the SDK's `query` runs, or never removed.
- A runner that drops or rewrites another option on the way.
- A prompt file written in an encoding other than UTF-8.
- A started flag that is never reset between runs.
- A runner that turns a missing system prompt into a file holding `""`.
- `GATE_ERROR` for any `AgentFailed` from a verdict session.
- "Never started" read from the exception's class or text.
- "Never started" read from a missing result event, zero turns or no text.
- "Never started" read from an empty stream, which a bound kill also leaves.
- "Never started" read from the first runner line being an `error` event.
- `GATE_ERROR` that needs every lens to fail, or every failed lens to have
  never started.
- A `rebut_state` in which the first errored lens decides the state.
- A `why` that names every lens with an error, or omits the runner's error.

**A cell-marked test for the real argument list.** No host test can spawn
the agent CLI. Add one `@pytest.mark.cell` test beside
`test_without_a_credential_the_agent_fails_rather_than_reporting_success`
(`tests/test_agent_runner.py:299`). Reuse its network and container setup.
Call `implement.run_agent` with options holding only `max_turns` and a 1 MiB
system prompt, and capture what it emits. Assert `AgentFailed`, and that its
message holds neither `Argument list too long` nor `Failed to start`. Assert
too that one emitted `events.Agent` carries a runner event of type `system`
and subtype `init`. That shows the CLI parsed its arguments and began a
session.
Whether the CLI emits `init` before it fails for want of a credential is
unmeasured. The operator's first run of this test settles it. The `tests`
gate never collects it, because `addopts = "-m 'not cell'"`
(`pyproject.toml:53`). The operator runs
`uv run pytest -m cell tests/test_agent_runner.py` on the cell's branch
before merging.
1 MiB exceeds the cap on 4 KiB and 16 KiB pages alike.

**Import nothing new at module scope** in `tests/test_agent_runner.py`. A name
the change adds, imported there, turns the reverted run into a collection
error, which `revert` reads as `skip`.

**The `size` gate counts tokens.** The prototype's diff measured 790 changed
tokens against the `bug` ceiling of 1300, before the cell-marked test. The
gate is advisory at `standard` risk. Keep docstrings to one or two lines.
