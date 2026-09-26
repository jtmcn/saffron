---
id: SA-0169
title: A spec session's Bash would run as root beside the runner its findings come from
type: feature
priority: 1
depends_on: [SA-0168]
touches:
  - images/cell-base.python.Dockerfile
  - images/unprivileged.sh
  - saffron/phases/implement.py
  - saffron/cell/runtime.py
  - saffron/cell/worktree.py
  - saffron/cell/session.py
  - saffron/end_review.py
  - tests/test_implement.py
  - tests/test_worktree.py
  - tests/test_session.py
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
  - images/agent_runner.py
  - images/proxy.Dockerfile
  - saffron/cell/proxy.py
  - saffron/cell/runtimes/**
  - saffron/phases/review.py
  - saffron/phases/rebut.py
  - saffron/spec_review.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/record/**
  - tests/test_agent_runner.py
  - tests/test_image.py
  - tests/test_runtime.py
  - tests/test_review.py
  - tests/test_rebut.py
budget_usd: 22
max_attempts: 3
max_turns: 200
acceptance:
  - claim: >-
      `implement.agent_options` adds the key `CLAUDE_CODE_SHELL_PREFIX` to
      its `env` exactly when `tools` holds `Bash` and neither `Write` nor
      `Edit`. The value is `implement.UNPRIVILEGED_BASH`, the wrapper's
      path in the base image. Every other `env` key is unchanged, and
      each call builds its own `env`. The witness drives `["Bash"]`,
      `["Read", "Glob", "Grep", "Bash"]`, `IMPLEMENT_TOOLS`, `["Bash",
      "Write"]`, `["Bash", "Edit"]`, `review.REVIEW_TOOLS`, an empty list
      and no `tools` at all.
    witness: tests/test_implement.py::test_a_session_that_cannot_write_the_tree_runs_its_bash_unprivileged
  - claim: >-
      `worktree.prepare_worktree` takes `cap_add`, which defaults to `()`,
      and passes it through `runtime.run_detached` to `runtime._run_argv`.
      The argv `_run_argv` builds then holds `--cap-add` and one name, for
      each name in order, directly after `--cap-drop ALL`. With no
      `cap_add` the argv holds no `--cap-add`.
      `implement.UNPRIVILEGED_BASH_CAPS` is `("CAP_SETUID",
      "CAP_SETGID")`. The witness drives that constant and no `cap_add`.
    witness: tests/test_worktree.py::test_a_worktree_cell_carries_exactly_the_capabilities_it_is_given
  - claim: >-
      `session.cell_up` takes `cap_add`, which defaults to `()`, and passes
      it to `prepare_worktree` unchanged. `_drive_cell`'s `cell_up` call
      and `critic_cell` pass none. A `_drive_cell` run to
      `READY_FOR_REVIEW` brings up the task's own cell, its gate-only cell
      and its critic cell. Each reaches `prepare_worktree` with no
      `cap_add` or an empty one. The witness drives that run and one
      direct `cell_up` call naming two capabilities.
    witness: tests/test_session.py::test_no_cell_a_task_brings_up_is_granted_a_capability
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
  - claim: >-
      `session.assert_bash_is_unprivileged(container)` calls
      `runtime.exec_` once, with the container and an argv of
      `implement.UNPRIVILEGED_BASH` and one probe script. It raises
      `runtime.CellRuntimeError` naming "did not leave root" unless three
      things hold. The exit status is 0, and the first output line is a
      uid other than 0. Every later line is `refused <path>` or `skipped
      <path>`, and at least six are `refused`. So a `wrote` line or a
      `missing` line fails it, and a `skipped` line counts as no refusal.
      The witness drives a passing report, one with a `skipped` line added,
      a uid of 0, a write the account made to a path on `PATH`, one to the
      runner, a missing fixed path, five refusals, five refusals and a
      `skipped` line, exit status 127, empty output, a uid with no other
      lines, and a first line that is not a number.
    witness: tests/test_session.py::test_the_bash_wrapper_self_check_refuses_a_cell_where_it_stayed_root
  - claim: >-
      The probe script `assert_bash_is_unprivileged` passes prints `wrote
      <dir>` for a directory on `PATH` the running user can write. It
      prints `skipped <entry>` for a `PATH` entry that does not exist, and
      no `missing` line for it. The witness takes the script from the argv
      criterion 5's `exec_` double recorded. It runs it under the host's
      `bash`, with a writable directory in `tmp_path` and an entry that
      does not exist on `PATH`.
    witness: tests/test_session.py::test_the_bash_self_checks_probe_reports_a_writable_path_directory_as_written
---

## Context

Backlog item **b-792ab2**, step 6 of its Done. It cites `DESIGN.md` §5.5.
`SA-0175` gives the stack batch's spec review session `Bash`, through
`spec_review.SPEC_SESSION_TOOLS`, which is `Read`, `Glob`, `Grep` and
`Bash`. `SA-0156` runs that session in a critic cell, and `SA-0160`'s
spec writer takes the same list. The
operator decided that this Bash runs as an unprivileged account. That
account cannot write the runner, its files, or anything the host reads the
session's findings from. The operator also decided that only a cell that
runs a spec session gets the capabilities this needs, and that the account
never sees `CLAUDE_CODE_OAUTH_TOKEN`. This spec builds that, and
`SA-0175` and `SA-0156` build on it.

**What the tree base holds.** This spec's tree base is `SA-0168`'s head.
Every line number below was read at `71140772`, where no chain code
exists. This spec consumes one chain name. `SA-0154` adds
`end_review.layer_cell(fields, *, repo, mirror, gates_dir, thread_env)`, a
context manager. It removes a leftover container, calls `session.cell_up`
with `tree_base` set to `fields.head`, yields the container, and always
calls `session.cell_down`. A spec session and each end-review lens run in
one. Only a spec session holds `Bash`. `SA-0154`'s witness file is
`tests/test_end_review.py`.

**What §5.5 forbids, and why.** A gate-only cell exists so that no gate
executes in the critic cell (`DESIGN.md:1065`). There, "a gate would run
model-authored code as root in the container the lenses then re-exec
their runner from". A spec session's cell is seeded at the predecessor
layer's head, which the previous layer's implementer wrote. A spec review
that runs a test there runs that code.

**Who runs as what today.** No image sets a `USER`, so every cell process
runs as root (`DESIGN.md:604`). `implement.run_agent` execs
`/opt/saffron/python /opt/saffron/agent_runner.py` with no user
(`saffron/phases/implement.py:290-297`). The runner starts the bundled
Claude Code CLI through the SDK, and the CLI runs the Bash tool's commands.
So the model's Bash, the CLI and the runner are all root. The runner writes
Saffron's events on stdout, and the host reads the session's text from that
stream (`saffron/phases/implement.py:261-288`). Every cell starts with
`--cap-drop ALL` (`saffron/cell/runtime.py:227`), so root there cannot
change its uid.

**What was measured, on apple/container 1.3.0.** Each probe ran in a
container from the base image, on 2026-09-24 and 2026-09-25. The guest
kernel was 6.18.35.

- Under `--cap-drop ALL` alone, root cannot call `setuid`. Python's
  `os.setuid` raised `EPERM`.
- A root process held a pipe on its fd 1, as the runner holds the host's
  stream. Another root process wrote a line through `/proc/<pid>/fd/1`, and
  it arrived. A process of another uid got `Permission denied`.
- With the runner started as uid 10001 through the runtime's own `--user`,
  a second uid 10001 process forged a line into its stream. So the Bash
  needs a uid of its own, apart from the runner and the CLI.
- With `CAP_SETUID` and `CAP_SETGID` alone, `setpriv --inh-caps=-all`
  ran and the command's inheritable set read 0. `--bounding-set=-all`
  needs `CAP_SETPCAP` and exited 127 without it, so the wrapper does not
  pass it. `--no-new-privs` already stops the account regaining a
  capability through exec or file capabilities. A `setuid` from root with
  no keep-caps clears the permitted and effective sets. So an emptied
  bounding set would only add depth.
- Root in such a cell holds no `CAP_DAC_OVERRIDE`, so it cannot write the
  account's home. The account's files are made in the image build.
- `fs.protected_symlinks` and `fs.protected_regular` both read 0.
- A local `git clone` from `/work` clears git's config variables in the
  child it starts. So a `safe.directory` set through `GIT_CONFIG_COUNT`
  did not reach it, and the clone refused "dubious ownership". The same
  entries in the account's global config let it clone.

**What the CLI does with a shell prefix.** The bundled CLI is 2.1.237,
under SDK 0.2.142. It is a compiled binary at
`/usr/local/lib/python3.12/site-packages/claude_agent_sdk/_bundled/claude`
in the base image, so its source has byte offsets, not lines. Near byte
301699542 it builds each Bash command:

```
v.push(`eval ${_}`),v.push(`pwd -P >| ${_y([m])}`);let C=v.join(" && "),R=G.CLAUDE_CODE_SHELL_PREFIX;if(R)C=b8o(R,C)
```

`b8o` is at byte 297994426, and `_y`, the quoting it calls, at 297994257:

```
function _y(e){return e.map((t)=>{let r=String(t);if(r==="")return"''";if(/^[A-Za-z0-9_./:=@+,-]+$/.test(r))return r;return"'"+r.replaceAll("'",`'"'"'`)+"'"}).join(" ")}
function b8o(e,t){let r=e.lastIndexOf(" -");if(r>0){let n=e.substring(0,r),o=e.substring(r+1);return`${_y([n])} ${o} ${_y([t])}`}else return`${_y([e])} ${_y([t])}`}
```

So `b8o` escapes a single quote inside the command, as `'"'"'`, and returns
`'<prefix>' '<command>'` for a prefix with no ` -` in it. The two
functions were transcribed into Python and run in a two-capability cell.
Each command below went through the composite shape, `eval` and the
`pwd -P` included, as `bash -c -l` from root. Every uid printed was the
account's, 999, and none was 0.

| command | output |
|---|---|
| `echo 'a'"'"'; id -u; echo '` | `a'; id -u; echo`, no uid |
| `echo x' ; id -u ; '` | `x ; id -u ;`, no uid |
| `printf '%s\n' "'" ; id -u` | `'`, then 999 |
| ``id -u; echo "$(id -u)" `id -u` `` | 999, three times |
| `id -u`, a newline, `id -u` | 999, twice |

The inner `eval` there is quoted with `_y`, a stand-in for the CLI's own
quoting of the command, which was not transcribed. `getSpawnArgs`, at byte
301699670, runs that string as
`bash -c -l`. So root's login shell reads `/etc/profile` and root's own
profile, then starts the prefix. Everything `v` holds runs inside the
prefix, as the account. That is the shell snapshot's `source`, the session
environment script, two shell-option lines, the command's `eval`, and the
`pwd -P` into `/tmp/claude-<id>-cwd`. The CLI opens the command's output
file itself, as root, and reads and removes the working-directory file.

**Where the snapshot and the session environment live.** The CLI's config
directory is `CLAUDE_CONFIG_DIR`, which is `/agent-state` in a cell.
Near byte 301694273 it writes the snapshot to
`/agent-state/shell-snapshots/snapshot-<shell>-<ms>-<random>.sh`, from a
root shell. It checks the file exists before each command, and the
`source` is guarded: `source <path> 2>/dev/null || true`. The session
environment lives in `/agent-state/session-env/<session id>/`. The CLI
reads it as root and puts its text in the command, so the account never
opens it. In the measured cell, `/agent-state` is root's, mode `0755`. A
stand-in snapshot written there by root under the default umask came out
`0644`, in a `0755` directory, and the account sourced it. The CLI's own
modes for these files are unmeasured.

## Problem

Build six things.

1. **The account and the wrapper.** Edit
   `images/cell-base.python.Dockerfile` after the step that runs the runner,
   before `WORKDIR /work` (`images/cell-base.python.Dockerfile:68-72`). Add a system account named
   `unprivileged`, with its own group and home. Write its global git
   config there with two `safe.directory` entries, `/work` and
   `/work/.git`. Copy a new `images/unprivileged.sh`, a bash script, to
   `/opt/saffron/unprivileged`, owned by root, mode `0755`. It takes the
   command as its one argument. In one `{ }` block, so bash reads it whole
   before any descriptor closes, it does four things.
   - Given any argument count but 1, it exits 64 and runs nothing.
   - It closes every descriptor above 2 that `/proc/$$/fd` lists.
   - It execs, with stdin from `/dev/null`, `/usr/bin/setpriv
     --reuid=unprivileged --regid=unprivileged --clear-groups
     --no-new-privs --inh-caps=-all`.
   - That runs `/usr/bin/env -u CLAUDE_CODE_OAUTH_TOKEN
     HOME=/home/unprivileged /bin/bash -c` on the command.

   It sets no `GIT_CONFIG_*` variable, so a repo's `thread_env` keeps any
   it declares. It never falls back to running the command as root.
2. **Run it in the build.** In the same Dockerfile, add a `RUN` step that
   invokes `/opt/saffron/unprivileged`. It asserts that `id -u` under the
   wrapper equals `id -u unprivileged` and is not 0, and that the account
   cannot write `/opt/saffron/agent_runner.py`. It also fails the build
   when `grep -aqF CLAUDE_CODE_SHELL_PREFIX /opt/saffron/claude-code`
   finds nothing. That tripwire catches a CLI that drops the variable's
   name. It cannot catch one that keeps the name and changes what it does.
3. **The prefix.** In `saffron/phases/implement.py`, beside `RUNNER` and
   `PYTHON`, add `UNPRIVILEGED_BASH` and `UNPRIVILEGED_BASH_CAPS`. Make
   `agent_options` add the prefix as criterion 1 states. A session that
   holds `Write` or `Edit` is the implementer, whose Bash commits to
   `/work` and keeps root in its own cell.
4. **The capabilities.** Add `cap_add` to `runtime._run_argv`,
   `runtime.run_detached`, `worktree.prepare_worktree` and
   `session.cell_up`, as criteria 2 and 3 state. Each defaults to `()`.
   `_drive_cell` and `critic_cell` pass nothing, so a task's cells keep
   `--cap-drop ALL` alone. Reword the comment above `--cap-drop ALL`
   (`saffron/cell/runtime.py:225-226`). It says "No capabilities", and a
   caller can now name some.
5. **The self-check.** Add `assert_bash_is_unprivileged` to
   `saffron/cell/session.py`, as criteria 5 and 6 state. Its probe prints
   `id -u`, then exactly one line per path.
   - Six fixed paths come first. They are `/opt/saffron`, the runner, the
     wrapper, and the CLI binary as `readlink -f /opt/saffron/claude-code`
     resolves it. Then the SDK's package directory, which the probe finds
     with `/opt/saffron/python`, and the `site-packages` above it. Each
     prints `missing <path>` where `[ -e ]` fails, and otherwise
     `wrote <path>` or `refused <path>` by `[ -w ]`.
   - Then each directory on the cell's `PATH`, and its parent, `/` for a
     top-level one. Each prints `skipped <path>` where `[ -e ]` fails, and
     otherwise `wrote <path>` or `refused <path>` by `[ -w ]`.

   A path that fails `[ -e ]` prints only its `missing` or `skipped` line.
   The probe sets no `-e`, so a fixed path it cannot resolve prints
   `missing` and the probe goes on to `PATH`.
   Core names no repository path, so a repo's own tree is reached through
   `PATH`. In this repo that covers `/opt/venv/bin` and `/opt/venv`. A
   `PATH` entry the account cannot reach, such as one under a root-only
   home, is skipped. The account cannot write through it either, and
   failing on it would refuse every spec session in that repo's image.

   The self-check is forgeable only by code the image controls, since it
   runs before any session. It guards against a misbuilt image or a
   missing grant, not an adversary. It never goes through the CLI, so it
   never exercises the prefix. The operator's probe is the only check that
   the CLI applies the prefix.
6. **The layer's cell.** In `saffron/end_review.py`, give `layer_cell`
   the keyword `spec_session: bool = False`, as criterion 4 states. The
   default grants nothing and checks nothing, so a forgotten keyword
   leaves a cell as it is today. No caller at the tree base passes it.

**Why the stream is then out of reach.** The runner and the CLI stay root.
Only the Bash commands run as `unprivileged`, with empty effective,
permitted and inheritable sets and `NoNewPrivs`. That account cannot open a root process's
descriptors, and so cannot write the runner's stream or the CLI's. It
inherits no descriptor but its own stdout and stderr. It cannot write the
runner, the CLI, the SDK, the wrapper, `/etc`, the worktree, the repo's
toolchain or the state volume. The session's transcript lives in the state
volume, and a resumed extraction turn reads it. So neither the turn under
way nor any later turn in the cell runs anything the account wrote.

**What `SA-0175`, `SA-0156`, `SA-0160` and `SA-0165` pass.** `SA-0175`'s
`run_spec_review` passes `agent_options` of `SPEC_SESSION_TOOLS`, which
hold `Bash` and neither `Write` nor `Edit`. So the prefix reaches that
session with no argument. Each of `SA-0156`'s, `SA-0160`'s and
`SA-0165`'s callables opens its cell with
`layer_cell(..., spec_session=True)`, and that grants the capabilities and
runs the self-check. A cell whose wrapper stays root raises
`CellRuntimeError` before any session starts.

**What a session's Bash can do.** Measured in this repo's cell image, the
account reads `/work` and cannot write it, and it writes `/tmp`. Through
the CLI's composite command, with no snapshot, its `PATH` is
`/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`. Root's
login shell resets it there, so `pytest` does not resolve. `git clone -q
/work /tmp/w` worked, and this repo's test runner, called by its full
path, ran a test in the clone. The session's prompt tells it so. Those
prompts are core's, and name no repo file, tool or URL (ADR 7,
principle 41). `SA-0156`'s review prompt carries three lines for this,
quoted verbatim there, and they name no tool path. `SA-0176` puts
the same lines in core's writer prompt. This spec writes no prompt text.

## Out of scope

- **`DESIGN.md`.** It is protected. The operator records two departures by
  hand, in the pull request, each narrowed to a spec session's cell.
  - §5.5 (`DESIGN.md:1065`) keeps model-authored code out of the critic cell. A
    spec session's cell now runs it, as `unprivileged` only.
  - §5.1 says "No capability is granted to anything" (`DESIGN.md:587`). A spec
    session's cell now grants its root `CAP_SETUID` and `CAP_SETGID`.
    The Bash that runs model-authored code holds neither.
- **The implementer's cell.** Its Bash stays root.
- **REVIEW's lens cells.** `session.critic_cell` passes no `cap_add`, and
  a lens holds no `Bash`. They do not share the change.
- **End-review lens cells.** They come up through `layer_cell` with no
  keyword, so they get no capability and no check.
- **A leftover process of the account.** A command the account left
  running, in the background or detached, shares the account's uid. It can
  open a later command's output descriptor through `/proc` and write lines
  the model then reads as that command's output. It cannot reach the
  runner's stream. Nothing kills it, since a kill would also end a
  background command the session asked for.
- **The CLI's working directory.** The account writes the file that
  names the CLI's working directory. So the CLI then works from any
  directory the account names. Its file tools read from there, as root.
  The CLI's own `git`, run as root in a clone the account owns, refuses
  it as "dubious ownership". Measured, a clone whose `core.fsmonitor` ran
  a command made root's `git status` exit 128, and the command never ran.
- **The account's bounding set.** It still holds `CAP_SETUID` and
  `CAP_SETGID`, 0xc0. `--no-new-privs` stops an exec from raising them.
  The account can make a user namespace of its own, and inside it holds
  every capability over that namespace alone. Measured, `unshare -Ur`
  gave a full effective set there. From inside it, a write to the runner
  and one to a root process's `/proc/<pid>/fd/1` were both refused. An
  empty bounding set would not change that, since a new user namespace
  starts with a full set.
- **`fs.protected_symlinks` and `fs.protected_regular` are off.** Both read
  0 on the measuring host, and a cell cannot change them. So root follows a
  link the account plants in `/tmp`. Per the CLI's source, root there
  creates `/tmp/claude-0` before any Bash command runs, and refuses one
  that is a link or another uid's. It reads the working-directory file the
  account writes. A link there makes root read another file as a path. It
  writes nothing through it.
- **`/tmp`.** It stays writable to the account. A command there can steer
  a later command's working directory, or fail a later turn. A failed
  turn becomes the session's `error`, which `SA-0149` routes `error`.
  None of it writes the stream.
- **What the session reads.** A file in the tree can argue with the model,
  through `Read` as through `Bash`. That exposure exists today, for every
  lens.
- **The SDK's `user` option and the runtime's `exec --user`.** Each runs the
  CLI and its Bash as one uid, which the third measurement shows is
  forgeable. So neither is used, and `images/agent_runner.py` is unchanged.
- **podman.** It is not on the measuring host. Its spelling of
  `--cap-add`, and `setpriv` under its `no-new-privileges`, are unmeasured.
  A night does not run on podman yet.

## Notes for the agent

**Every criterion is new code.** Each adds a parameter, a branch or a
function that no code at the tree base has. So each criterion declares a
witness and no mutant, and `witness` reports `skip` for each. Import
`UNPRIVILEGED_BASH_CAPS` inside the test bodies that use it.

**Criterion 1's witness** builds `env` through `agent_options` with
`system_prompt="s"`, `max_turns=5` and `budget_usd=1.0`. It calls with
`["Bash"]` first. It pops the prefix from that `env` and asserts it is the
literal `/opt/saffron/unprivileged`, and that the rest equals the `env` for
an empty list. It asserts the prefix for `["Read", "Glob", "Grep",
"Bash"]`. It asserts no prefix for `IMPLEMENT_TOOLS`, `["Bash", "Write"]`,
`["Bash", "Edit"]`, `review.REVIEW_TOOLS`, `[]` and a call with no `tools`.
These fail it, each measured:

- the prefix on any list holding `Bash`
- a rule that reads `Write` alone, or `Edit` alone
- the prefix on any list but `IMPLEMENT_TOOLS`
- `env` replaced by a dict holding only the prefix
- one `env` dict shared across calls
- a prefix carrying an argument. The CLI splits a prefix at its last ` -`.

**Criterion 2's witness** replaces `runtime._admit`, `runtime.create_volume`
and `runtime.run_ephemeral`, and records each argv `runtime._must` gets. It
calls the real `prepare_worktree` twice, with `cap_add` set to the constant
and with none. The first argv's six items from `--cap-drop` on read
`--cap-drop`, `ALL`, `--cap-add`, `CAP_SETUID`, `--cap-add`,
`CAP_SETGID`. It holds two `--cap-add` in all. The second holds none. These fail it, each measured:

- `cap_add` dropped by `prepare_worktree`, by `run_detached`, or by
  `_run_argv`
- the flags placed before `--cap-drop ALL`
- one `--cap-add` with the names joined by a comma
- `prepare_worktree` defaulting to the capabilities
- a third capability granted, `CAP_SETPCAP` added to the constant

**Criterion 3's witness** uses `_stub_the_runtime` and `_drive`, with the
policy `test_the_lens_gate_cell_holds_no_credential_and_is_gone_before_any_lens_runs`
uses, so a gate-only cell comes up. It asserts `READY_FOR_REVIEW`. It maps
each recorded `prepare_worktree` call's container to its `cap_add`, or `()`
where the call passed none. The map holds `_IMPLEMENTER_CONTAINER`,
`_CRITIC_CONTAINER` and `_GATE_CONTAINER`, and every value is `()`. It then
calls `session.cell_up` directly with the container `c-2` and `cap_add`
`("CAP_X", "CAP_Y")`. The last recorded call is `c-2`'s, carrying those
two. These fail it, each measured:

- `_drive_cell` asking for the capabilities
- `critic_cell` asking for them
- `cell_up` dropping `cap_add`, or passing `()` in its place

**What criterion 3 leaves undriven.** `critic_cell` has five callers, and
all share its one `prepare_worktree` call (`saffron/cell/session.py:1204`).
The witness reaches it through two of them. Two more cells come up
outside `critic_cell`. PACKAGE's re-verification cell calls
`prepare_worktree` directly (`saffron/phases/package.py:525`), and the
proxy calls `runtime.run_detached` directly (`saffron/cell/proxy.py:60`).
Neither passes `cap_add`. Neither file is in `touches`, so neither can
gain one.

**Criterion 4's witness** replaces `runtime.remove_container`,
`session.cell_up`, `session.cell_down` and
`session.assert_bash_is_unprivileged` with recorders that append to one
log, `remove_container` included. It enters `layer_cell` with no keyword
and with `spec_session=False`. Each time the log reads remove, up, body,
down, and the up call's `kwargs.get("cap_add", ())` is `()`. It enters
once more with `spec_session=True`. The log reads remove, up, check,
body, down. The up call's `cap_add`, as a tuple, is the literal pair. The
check got the container the up call named, which is also the one
yielded. Last, it replaces the check with one that logs and raises
`CellRuntimeError`. The error leaves `layer_cell`, and the log reads
remove, up, check, down. These fail it, each
measured against a stand-in `layer_cell`:

- the capabilities granted to every `layer_cell`
- none granted to a spec session
- the keyword defaulting to `True`
- `("SETUID", "SETGID")`, or `CAP_SETUID` alone
- no self-check
- the self-check on every `layer_cell`
- the self-check before `cell_up`
- `layer_cell` swallows the self-check's error

**Criterion 5's witness** replaces `runtime.exec_` with a double that
records its container and argv and returns the case's output and exit
status. The passing report is `999`, then seven `refused` lines:
`/opt/saffron`, the runner, the wrapper, `/cli`, `/sdk`, `/site` and
`/opt/venv/bin`. Two cases pass: that report, and that report with
`skipped /root/.local/bin` added. In each, the one call's argv is
`/opt/saffron/unprivileged` and one script. Every other case raises
`CellRuntimeError` matching "did not leave root". Those include the
report with `/cli` turned into `missing /cli`, and the report cut to its
first five `refused` lines. They include the same five with
`skipped /root/.local/bin` added. These fail it. The last two are
reasoned, and the prototype measured the rest.

- a uid of 0 accepted
- a `wrote` line accepted
- the exit status ignored
- an empty report accepted
- the uid read alone
- the probe run through `sh` rather than the wrapper
- a `missing` line counted as a refusal
- two refusals enough to pass
- a `skipped` line read as a failure, reasoned
- a `skipped` line counted as a refusal, reasoned

Two probe wrong builds, measured against the cell test below, not this
witness: the probe without the existence test, and the probe without the
three new paths.

**Criterion 6's witness** calls `assert_bash_is_unprivileged` with
criterion 5's double and its passing report, and takes the script from
the recorded argv. It makes a directory `w` in `tmp_path`, and runs
`bash -c` on the script with `subprocess.run`. Its `PATH` is `w`, then
`tmp_path / "absent"`, then `/usr/bin` and `/bin`. It asserts the output
holds the line `wrote <w>` and the line `skipped <tmp_path>/absent`, and
no line `missing <tmp_path>/absent`. It asserts nothing of the fixed
paths, since the host has no `/opt/saffron`, and nothing of the exit
status. It holds whether the suite runs as root or not, since `w` is
the running user's own directory. These fail it, reasoned, since no
prototype ran it:

- a probe printing `refused` for every path that exists
- a probe that reads no `PATH`
- a probe printing `missing` for a `PATH` entry that does not exist,
  or nothing for it
- a probe run under `set -e`, which stops at the host's absent
  `/opt/saffron/python` before it reaches `PATH`

A probe testing `[ -r ]` or `[ -x ]` in place of `[ -w ]` passes it,
since `w` is readable and searchable too. The cell test catches it,
since it asserts `refused` for paths the account can read.

**How the lists were measured.** A prototype ran on 2026-09-25 at
`f2a08a9f`, with a stand-in `layer_cell` as `SA-0154` states it. The right
build passed all five witnesses, and `test_implement.py`, `test_runtime.py`,
`test_worktree.py`, `test_session.py`, `test_review.py`, `test_rebut.py`,
`test_events.py` and `test_end_review.py` stayed green. Each wrong version
above was applied as a text edit, and each failed its own witness. Two
also failed another: the prefix with an argument failed criterion 5, and
a third capability granted failed criterion 4. With the source
reverted, all five failed. Criterion 6 and the `skipped` line came
later, so criterion 5's two `skipped` cases and all of criterion 6 are
reasoned. With the source reverted, criterion 6's witness fails, since
`assert_bash_is_unprivileged` does not exist.

**The cell test, which no criterion declares.** Add
`test_a_spec_sessions_bash_cannot_write_what_root_runs` to
`tests/test_end_review.py`, marked `cell`. `pyproject.toml` deselects that
marker, so the `tests` gate never collects it, and `criteria` would report
a declared one `witness-not-collected`. You cannot run it in your cell.
The operator runs it by hand before merging, as `SA-0041` asked. A host
with a tolerated listener sets `SAFFRON_ALLOW_HOST_PROCESS` in its own
environment, and the test never sets it. It sets a
stand-in `CLAUDE_CODE_OAUTH_TOKEN`, seeds a one-commit mirror in
`tmp_path`, and enters `end_review.layer_cell(..., spec_session=True)` with
this repository as `repo`. So `cell_up` brings up the proxy and
`saffron-cells`, and builds this repo's image, as production does. Existing
cell tests already start a proxy (`tests/test_worktree.py:280`). Inside
the cell it runs one Python program as root through `runtime.exec_` and
`implement.PYTHON`. The program runs each probe as `bash -c -l "'<prefix>'
'<command>'"`, the CLI's own call, and prints one JSON object. It asserts:

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
assert. On 2026-09-25 it passed against the prototype. The measuring host
had two more non-loopback listeners, so the host set
`SAFFRON_ALLOW_HOST_PROCESS=rapportd,limactl,RAATServe` for that run.

**What each wrapper line buys, measured.** Each version below ran against
that cell test, through the real `layer_cell` and this repo's image:

| version | what failed |
|---|---|
| the right one | nothing |
| no argument guard | the argument-count probe |
| no descriptor close | the fd 3 pipe got the command's line |
| stdin kept | the fd 0 pipe got the command's line |
| the token kept | the token was set for the account |
| no `--no-new-privs` | `NoNewPrivs` was not 1 |
| a root fallback after `setpriv` | the image build |
| `CAP_SETGID` not granted | the self-check raised in `layer_cell` |
| the probe without the existence test | no `missing /nonexistent`, the line the probe then printed |
| the probe without the new paths | no `refused /opt/saffron` |
| no `--inh-caps=-all` | nothing |
| a third capability granted | nothing |

The probe then printed `missing` for a `PATH` entry too. Its `skipped`
spelling, the `/root/x` entry and criterion 6's witness came after this
run, so they are unmeasured.

The last two pass the cell test. Root's inheritable set is already empty
under `--cap-drop ALL`, so `--inh-caps=-all` changes nothing measured
here. A third capability goes to root and never reaches the account.
Criteria 2 and 4 catch it.

Earlier versions ran in a raw container, against the same probes:
`--keep-groups` failed the group probe, and no `HOME` the `HOME` probe.
Mode `0777` failed the write to the wrapper. With no capability at all,
the "command runs" probe failed, which is why that probe exists. Without
it, every refusal passes in a cell where nothing runs.

**What stays unmeasured.** No live session ran, since that needs the token
and a model turn. So these rest on the CLI's source above:

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
sentence over 25 words. Keep each docstring within ten lines. Keep each
Dockerfile comment to two lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** `saffron/cell/**` is in `elevate_on`, so `size` blocks at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). The
prototype measured 1883 changed tokens with `size_gate`'s own count. The
Dockerfile took 163, the wrapper 70, `implement.py` 83, `runtime.py` 33,
`worktree.py` 5, `session.py` 204 and `end_review.py` 11. The tests took
1314, with the cell test 688 of `test_end_review.py`'s 871. That is 63% of
the ceiling. The `skipped` branch, criterion 5's three new cases and
criterion 6's witness add about 200, so about 2080, 69%.
