---
id: SA-0169
title: A spec session's Bash would run as root beside the runner its findings come from
type: feature
priority: 1
depends_on: [SA-0181]
touches:
  - saffron/end_review.py
  - tests/test_end_review.py
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
  - images/**
  - saffron/cell/**
  - saffron/phases/**
  - saffron/spec_review.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/record/**
  - tests/test_agent_runner.py
  - tests/test_cli.py
  - tests/test_image.py
  - tests/test_implement.py
  - tests/test_runtime.py
  - tests/test_worktree.py
  - tests/test_session.py
  - tests/test_review.py
  - tests/test_rebut.py
budget_usd: 22
max_attempts: 3
max_turns: 200
estimated_lines: 328
acceptance:
  - claim: >-
      `end_review.layer_cell` takes a keyword `spec_session`, which
      defaults to `False`. Given `True`, it calls `session.cell_up` with
      `cap_add` equal to `implement.UNPRIVILEGED_BASH_CAPS`. It then calls
      `session.assert_bash_is_unprivileged` once, on the container
      `cell_up` was given, before it yields. Given `False`, or no keyword,
      the `cell_up` call's `kwargs.get("cap_add", ())` is `()`, and no
      check runs. A check that raises propagates out of `layer_cell`. The
      body never runs, and `cell_down` still does. The witness drives no
      keyword, `False`, `True`, and `True` with a check that raises.
    witness: tests/test_end_review.py::test_only_a_spec_sessions_layer_cell_is_granted_capabilities_and_checked
---

## Context

Backlog item **b-792ab2**, step 6 of its Done. It cites `DESIGN.md` §5.5.
`SA-0175` gives the stack batch's spec review session `Bash`, through
`spec_review.SPEC_SESSION_TOOLS`, which is `Read`, `Glob`, `Grep` and
`Bash`. `SA-0156` runs that session in a critic cell, and `SA-0160`'s
spec writer takes the same list. The operator decided that this Bash runs
as an unprivileged account. That account cannot write the runner, its
files, or anything the host reads the session's findings from. The
operator also decided that only a cell that runs a spec session gets the
capabilities this needs. `SA-0175` and `SA-0156` build on this spec.

**This is the second of two specs.** They were one, this spec, until its
cell ended `PLAN_REJECTED` on 2026-09-26. Its plan priced 8400 changed
tokens against the `feature` ceiling of 3000, with `size` blocking at
`elevated`. The plan had read the spec's token count as a line count.
`SA-0181` now builds the account, the wrapper `/opt/saffron/unprivileged`,
the shell prefix, the capabilities and the self-check. Its `## Context`
holds the measurements behind each, and the CLI's source that applies the
prefix. This spec opens a spec session's cell with them, and carries the
cell test that probes all of it.

**What the tree base holds.** This spec's tree base is `SA-0181`'s head.
Every line number below was read at `f492629e`, `SA-0168`'s head, where
no `SA-0181` code exists. `SA-0181` edits no file this spec touches.

`SA-0154` added `end_review.layer_cell(fields, *, repo, mirror,
gates_dir, thread_env)`, a context manager
(`saffron/end_review.py:564-616`). It removes a leftover container, calls
`session.cell_up` with `tree_base` set to `fields.head`, yields the
container, and always calls `session.cell_down` from a `finally`
(`:591-616`). A spec session and each end-review lens run in one. Only a
spec session holds `Bash`. Its one caller at the tree base,
`saffron/cli.py:637-643`, binds it with `partial` and no `spec_session`.

This spec consumes three names `SA-0181` adds, as its `## Problem` names
them.

- `implement.UNPRIVILEGED_BASH_CAPS`, the tuple `("CAP_SETUID",
  "CAP_SETGID")`.
- `session.cell_up(..., cap_add=())`, whose keyword `cap_add` takes any
  `Sequence[str]` and reaches the cell's run argv after `--cap-drop ALL`.
- `session.assert_bash_is_unprivileged(container) -> None`. It runs the
  wrapper once in the container and raises `runtime.CellRuntimeError`
  naming "did not leave root" on a failure.

**What §5.5 forbids, and why.** A gate-only cell exists so that no gate
executes in the critic cell (`DESIGN.md:1065`). There, "a gate would run
model-authored code as root in the container the lenses then re-exec
their runner from". A spec session's cell is seeded at the predecessor
layer's head, which the previous layer's implementer wrote. A spec review
that runs a test there runs that code. `SA-0181`'s wrapper runs it as
`unprivileged`, and only a cell granted `CAP_SETUID` and `CAP_SETGID` can
switch to it.

## Problem

**The layer's cell.** In `saffron/end_review.py`, give `layer_cell` the
keyword `spec_session: bool = False`, as the criterion states. Given
`True`, it passes `cap_add=implement.UNPRIVILEGED_BASH_CAPS` to its
`session.cell_up` call (`saffron/end_review.py:593-606`). Given `False`,
that call passes no `cap_add` keyword at all. A test double of `cell_up`
names its twelve keywords one by one, with no `**kwargs`
(`tests/test_cli.py:3118-3132`). An empty `cap_add` there raises
`TypeError`, and `tests/test_cli.py` is not this spec's to edit.

After `cell_up` returns and before the `yield` (`:607`), a spec session's
`layer_cell` calls `session.assert_bash_is_unprivileged(container)`. Both
calls stay inside the `try`, so a raise still reaches the `finally`'s
`cell_down`. Reach both names through their module, as `layer_cell`
already reaches `cell_up`, so a caller that replaces them there reaches
this call too. The docstring is ten lines already
(`saffron/end_review.py:573-582`), the `prose` gate's limit. So say what
the keyword does in a comment, not in the docstring.

The default grants nothing and checks nothing, so a forgotten keyword
leaves a cell as it is today. No caller at the tree base passes it.

**What `SA-0175`, `SA-0156`, `SA-0160` and `SA-0165` pass.** `SA-0175`'s
`run_spec_review` passes `agent_options` of `SPEC_SESSION_TOOLS`, which
hold `Bash` and neither `Write` nor `Edit`. So `SA-0181`'s prefix reaches
that session with no argument. Each of `SA-0156`'s, `SA-0160`'s and
`SA-0165`'s callables opens its cell with
`layer_cell(..., spec_session=True)`, and that grants the capabilities and
runs the self-check. A cell whose wrapper stays root raises
`CellRuntimeError` before any session starts.

## Out of scope

- **`DESIGN.md`.** It is protected. The operator records two departures by
  hand, in the pull request, each narrowed to a spec session's cell.
  - §5.5 (`DESIGN.md:1065`) keeps model-authored code out of the critic
    cell. A spec session's cell now runs it, as `unprivileged` only.
  - §5.1 says "No capability is granted to anything" (`DESIGN.md:587`). A
    spec session's cell now grants its root `CAP_SETUID` and `CAP_SETGID`.
    The Bash that runs model-authored code holds neither.
- **End-review lens cells.** They come up through `layer_cell` with no
  keyword (`saffron/cli.py:637-643`), so they get no capability and no
  check.
- **Everything `SA-0181` builds**, and everything its `## Out of scope`
  lists. That covers the implementer's cell, REVIEW's lens cells and a
  leftover process of the account. It covers the CLI's working directory,
  the account's bounding set, `fs.protected_symlinks` and `/tmp`. It also
  covers what the session reads, the SDK's `user` option and podman.

## Notes for the agent

**The criterion is new code.** The keyword, its branch and its call do
not exist at the tree base. So it declares a witness and no mutant, and
`witness` reports `skip` for it. `tests/test_end_review.py` imports
`saffron.end_review` inside every test body, never at module scope
(`tests/test_end_review.py:1-6`). Do the same.

**The witness** replaces `runtime.remove_container`, `session.cell_up`,
`session.cell_down` and `session.assert_bash_is_unprivileged` with
recorders that append to one log, `remove_container` included. It builds
`LayerFields` with every field, `known` among them. It enters
`layer_cell` with no keyword and with `spec_session=False`. Each time the
log reads remove, up, body, down, and the up call's
`kwargs.get("cap_add", ())` is `()`. It enters once more with
`spec_session=True`. The log reads remove, up, check, body, down. The up
call's `cap_add`, as a tuple, is the literal pair
`("CAP_SETUID", "CAP_SETGID")`. The check got the container the up call
named, which is also the one yielded. Last, it replaces the check with one
that logs and raises `CellRuntimeError`. The error leaves `layer_cell`,
and the log reads remove, up, check, down. These fail it:

- the capabilities granted to every `layer_cell`
- none granted to a spec session
- the keyword defaulting to `True`
- `("SETUID", "SETGID")`, or `CAP_SETUID` alone
- no self-check
- the self-check on every `layer_cell`
- the self-check before `cell_up`
- `layer_cell` swallows the self-check's error

`CAP_SETPCAP` added to `SA-0181`'s constant fails it too, since it
compares with the literal pair. One more wrong version passes it:
`cap_add=()` passed to a lens cell's `cell_up`. `kwargs.get` reads that as
`()`. The suite's existing
`tests/test_cli.py::test_a_stack_batch_holds_a_quarter_of_its_budget_and_reads_its_stack_at_the_pinned_base`
fails it instead, on its double's `TypeError`.

**How the list was measured.** A prototype of `SA-0181` and this spec ran
on 2026-09-27 at `f492629e`. The witness passed, and the rest of
`test_end_review.py` stayed green. Each wrong version above was applied
to `layer_cell` as a text edit, and each failed the witness. The
`cap_add=()` version failed only the `test_cli.py` test named above. The
whole suite and `ty` stayed green at the prototype's head. With
`end_review.py` reverted to `SA-0181`'s head, the witness failed on an
assertion, not at collection.

**The cell test, which no criterion declares.** Add
`test_a_spec_sessions_bash_cannot_write_what_root_runs` to
`tests/test_end_review.py`, marked `cell`. `pyproject.toml` deselects that
marker (`pyproject.toml:52-53`), so the `tests` gate never collects it,
and `criteria` would report a declared one `witness-not-collected`. You
cannot run it in your cell. The operator runs it by hand before merging,
as `SA-0041` asked. A host with a tolerated listener sets
`SAFFRON_ALLOW_HOST_PROCESS` in its own environment, and the test never
sets it.

It sets a stand-in `CLAUDE_CODE_OAUTH_TOKEN`, seeds a one-commit mirror
in `tmp_path`, and enters `end_review.layer_cell(..., spec_session=True)`
with this repository as `repo`. So `cell_up` brings up the proxy and
`saffron-cells`, and builds the base image and this repo's image, as
production does (`saffron/repos/image.py:69-80`). Existing cell tests
already start a proxy (`tests/test_worktree.py:280`). Inside the cell it
runs one Python program as root through `runtime.exec_` and
`implement.PYTHON`. The program runs each probe as
`bash -c -l "'<prefix>' '<command>'"`, the CLI's own call, and prints one
JSON object. It takes the prefix from `implement.agent_options` with
`["Read", "Glob", "Grep", "Bash"]`.

`SA-0181` exposes no name for the self-check's probe script. So the test
wraps `runtime.exec_` in a recorder that still calls the real one. While
`layer_cell` runs, the recorder keeps each argv it sees. The probe is the
second item of the first recorded argv whose first item is
`implement.UNPRIVILEGED_BASH`, the call `SA-0181`'s criterion 4 pins. The
test then runs that probe through the wrapper again, once as it is and
once under the altered `PATH` below. `runtime.exec_` takes no `env`, so
the `PATH` goes in the argv: `["env", "PATH=...", <wrapper>, <probe>]`.
No run collected this recorder route yet, since the prototype of
2026-09-27 read a private name for the probe instead. The test asserts:

- the uid equals `id -u unprivileged` and is not 0, with no group 0 and a
  writable `HOME`
- `CapEff` and `CapPrm` are 0 and `NoNewPrivs` is 1
- a set-uid-root copy of `id` in `/tmp` reports the account's uid
- the token is unset for the account and set for root
- `git -C /work log -1` prints the seeded commit, `/work` reads, `/tmp`
  writes, and a clone into `/tmp/w` runs `/opt/venv/bin/pytest --version`
- `Permission denied` on a write to each of eleven paths. They are the
  runner, `/opt/saffron/claude-code`, the wrapper and the SDK's
  `__init__.py`. Then `/opt/venv/pyvenv.cfg`, a new file in the venv's
  `site-packages` and in `/opt/venv/bin`. Then a new file in
  `/agent-state`, one in `/work`, `/work/.git/config`, and one in `/etc`.
- a root parent passes a pipe as the command's fd 3, then as its fd 0.
  Each pipe carries root's own line and never the command's.
- a root process holding a pipe on fd 1 receives no line the account
  writes through `/proc/<pid>/fd/1`, and does receive root's own line
- the self-check's own probe, run again, reports `refused` for
  `/opt/venv/bin` and then `/opt/venv`, and for `/opt/saffron`, the
  wrapper and the resolved CLI binary
- the same probe with `PATH=/nonexistent:/root/x:/usr/bin` reports
  `skipped /nonexistent` and `skipped /root/x`, and no `missing` line for
  either
- the wrapper with no argument, or with two, exits non-zero and prints
  nothing
- the transcribed `_y` and `b8o` build the composite command around
  `echo 'a'"'"'; id -u; echo '; id -u`. It prints the literal, then the
  account's uid.

It also prints the account's `PATH`, `command -v pytest`, and
`fs.protected_symlinks` and `fs.protected_regular`, which it does not
assert. `SA-0181`'s `## Context` quotes `_y` and `b8o` from the CLI's
source. Write no suppression comment in it. The `integrity` gate refuses
one, so bind a helper with `def` rather than a lambda.

**What the cell test showed.** On 2026-09-25 it passed against an
earlier prototype at `f2a08a9f`. The measuring host had two more
non-loopback listeners, so the host set
`SAFFRON_ALLOW_HOST_PROCESS=rapportd,limactl,RAATServe` for that run. The
probe then printed `missing` for a `PATH` entry too. Its `skipped`
spelling and the `/root/x` entry came after that run, so they are
unmeasured in a cell. On 2026-09-27 the test was ported to `f492629e`
and collected, and not run.

**What stays unmeasured.** No live session ran, since that needs the token
and a model turn. So these rest on the CLI's source that `SA-0181` quotes:

- the CLI reading `CLAUDE_CODE_SHELL_PREFIX` from the options' `env`
- a command started with `run_in_background` going through the prefix
- the shell snapshot's effect on `PATH` once it is sourced as the account

The operator's probe settles all three before `SA-0156`'s first night. Run
one session with `SPEC_SESSION_TOOLS` in a `layer_cell(...,
spec_session=True)` cell, with the token. Ask it to run three commands and
report each one's output:

- `id -u; echo $PATH`, in the foreground
- the same, with `run_in_background`
- `echo 'a'"'"'; id -u; echo '; id -u`, in the foreground

It passes when output appears for all three and every uid printed is the
account's. Output that never appears means the snapshot or the wrapper
failed, since the `source` hides its own error.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Commit as the witness passes**, before the full suite runs.

**Size.** Neither file this spec touches is in `elevate_on`, so `size`
is advisory at the `feature` ceiling of 3000 changed tokens
(`saffron/gates/core/size.py:26`). The prototype, formatted with
`ruff format`, measured 935 changed tokens with `size_gate`'s own count:
30 in `end_review.py` and 905 in `test_end_review.py`, the cell test most
of it. Sibling cells landed at 1.4 times their authors' estimates, so
about 1309 tokens, 44% of the ceiling. The plan's `estimated_lines`
counts lines, and the checkpoint prices each line at 4 tokens
(`saffron/gates/core/size.py:39`). So plan this at about 328 changed
lines, not at a token count.
