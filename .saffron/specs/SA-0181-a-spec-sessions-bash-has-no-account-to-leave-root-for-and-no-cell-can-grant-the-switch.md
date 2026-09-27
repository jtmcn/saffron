---
id: SA-0181
title: A spec session's Bash has no account to leave root for, and no cell can grant the switch or check it
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
  - tests/test_implement.py
  - tests/test_worktree.py
  - tests/test_session.py
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
  - saffron/phases/package.py
  - saffron/end_review.py
  - saffron/spec_review.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/record/**
  - tests/test_end_review.py
  - tests/test_agent_runner.py
  - tests/test_image.py
  - tests/test_runtime.py
  - tests/test_review.py
  - tests/test_rebut.py
budget_usd: 22
max_attempts: 3
max_turns: 200
estimated_lines: 406
pending_symbols:
  - saffron/phases/implement.py::UNPRIVILEGED_BASH_CAPS
  - saffron/cell/session.py::assert_bash_is_unprivileged
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
      `session.assert_bash_is_unprivileged(container)` calls
      `runtime.exec_` once, with the container and an argv of
      `implement.UNPRIVILEGED_BASH` and one probe script. It raises
      `runtime.CellRuntimeError` naming "did not leave root" unless three
      things hold. The exit status is 0, and the first output line is a
      uid other than 0. Every later line is `refused <path>` or `skipped
      <path>`, and at least six are `refused`. So a `wrote` line or a
      `missing` line fails it, and a `skipped` line counts as no refusal.
      The witness drives a passing report, one with a `skipped` line added,
      a uid of 0, a write the account made to a path on `PATH`, one to
      the runner's directory, a missing fixed path, five refusals, five
      refusals and a `skipped` line, exit status 127, empty output, a uid with no
      other lines, and a first line that is not a number.
    witness: tests/test_session.py::test_the_bash_wrapper_self_check_refuses_a_cell_where_it_stayed_root
  - claim: >-
      The probe script `assert_bash_is_unprivileged` passes prints `wrote
      <dir>` for a directory on `PATH` the running user can write. It
      prints `skipped <entry>` for a `PATH` entry that does not exist, and
      no `missing` line for it. The witness takes the script from the argv
      criterion 4's `exec_` double recorded. It runs it under the host's
      `bash`, with a writable directory in `tmp_path` and an entry that
      does not exist on `PATH`.
    witness: tests/test_session.py::test_the_bash_self_checks_probe_reports_a_writable_path_directory_as_written
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
capabilities this needs, and that the account never sees
`CLAUDE_CODE_OAUTH_TOKEN`.

**This is one of two specs.** They were one, `SA-0169`, until its cell
ended `PLAN_REJECTED` on 2026-09-26. Its plan priced 8400 changed tokens
against the `feature` ceiling of 3000, with `size` blocking at `elevated`.
The plan had read the spec's token count as a line count. This spec
builds the account, the wrapper, the shell prefix, the capabilities and
the self-check. `SA-0169` then gives `end_review.layer_cell` the keyword
that grants a spec session's cell the capabilities and runs the
self-check. It also carries the cell test that probes all of it.

**What the tree base holds.** This spec's tree base is `SA-0168`'s head,
`f492629e`. Every line number below was read there.

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
301699670, runs that string as `bash -c -l`. So root's login shell reads
`/etc/profile` and root's own profile, then starts the prefix. Everything
`v` holds runs inside the prefix, as the account. That is the shell
snapshot's `source`, the session environment script, two shell-option
lines, the command's `eval`, and the `pwd -P` into `/tmp/claude-<id>-cwd`.
The CLI opens the command's output file itself, as root, and reads and
removes the working-directory file.

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

Build five things.

1. **The account and the wrapper.** Edit
   `images/cell-base.python.Dockerfile` after the step that runs the
   runner, before `WORKDIR /work` (`images/cell-base.python.Dockerfile:68-72`).
   Add a system account named `unprivileged`, with its own group and
   home. Write its global git config there with two `safe.directory`
   entries, `/work` and `/work/.git`. Copy a new `images/unprivileged.sh`,
   a bash script, to `/opt/saffron/unprivileged`, owned by root, mode
   `0755`. It takes the command as its one argument. In one `{ }` block,
   so bash reads it whole before any descriptor closes, it does four
   things.
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
   `PYTHON` (`saffron/phases/implement.py:34-37`), add `UNPRIVILEGED_BASH`
   and `UNPRIVILEGED_BASH_CAPS`. Make `agent_options`
   (`saffron/phases/implement.py:101-144`) add the prefix as criterion 1
   states. A session that holds `Write` or `Edit` is the implementer,
   whose Bash commits to `/work` and keeps root in its own cell.
4. **The capabilities.** Add `cap_add` to `runtime._run_argv`
   (`saffron/cell/runtime.py:210-221`), `runtime.run_detached` (`:366-393`),
   `worktree.prepare_worktree` (`saffron/cell/worktree.py:41-124`) and
   `session.cell_up` (`saffron/cell/session.py:873-979`), as criteria 2
   and 3 state. Each defaults to `()`. `_drive_cell` and `critic_cell`
   pass nothing, so a task's cells keep `--cap-drop ALL` alone. Reword
   the comment above `--cap-drop ALL` (`saffron/cell/runtime.py:225-226`).
   It says "No capabilities", and a caller can now name some.
5. **The self-check.** Add `assert_bash_is_unprivileged` to
   `saffron/cell/session.py`, as criteria 4 and 5 state. Its probe prints
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
   `missing` and the probe goes on to `PATH`. Core names no repository
   path, so a repo's own tree is reached through `PATH`. In this repo that
   covers `/opt/venv/bin` and `/opt/venv`. A `PATH` entry the account
   cannot reach, such as one under a root-only home, is skipped. The
   account cannot write through it either, and failing on it would refuse
   every spec session in that repo's image.

   The self-check is forgeable only by code the image controls, since it
   runs before any session. It guards against a misbuilt image or a
   missing grant, not an adversary. It never goes through the CLI, so it
   never exercises the prefix.

**The seams `SA-0169` builds on.** `SA-0169` calls three names this spec
adds, and its witness pins their shape.

- `implement.UNPRIVILEGED_BASH_CAPS` is the tuple `("CAP_SETUID",
  "CAP_SETGID")`, in that order.
- `session.cell_up(*, repo, mirror, tree_base, branch, network, volume,
  state, container, gates_dir, thread_env, created, note, cap_add=())`
  returns `None`. `cap_add` is a keyword, any `Sequence[str]`, and the
  other twelve parameters are unchanged. `SA-0169` passes it only for a
  spec session, since a test double of `cell_up` names the twelve alone
  (`tests/test_cli.py:3118-3132`).
- `session.assert_bash_is_unprivileged(container: str) -> None` takes the
  container name `cell_up` was given. It returns `None` on a pass and
  raises `runtime.CellRuntimeError` on a failure, never another type. It
  is a module attribute of `saffron.cell.session`, called through the
  module, so a test that replaces it there reaches every caller.

**Why the stream is then out of reach.** The runner and the CLI stay root.
Only the Bash commands run as `unprivileged`, with empty effective,
permitted and inheritable sets and `NoNewPrivs`. That account cannot open
a root process's descriptors, and so cannot write the runner's stream or
the CLI's. It inherits no descriptor but its own stdout and stderr. It
cannot write the runner, the CLI, the SDK, the wrapper, `/etc`, the
worktree, the repo's toolchain or the state volume. The session's
transcript lives in the state volume, and a resumed extraction turn reads
it. So neither the turn under way nor any later turn in the cell runs
anything the account wrote.

**What a session's Bash can do.** Measured in this repo's cell image, the
account reads `/work` and cannot write it, and it writes `/tmp`. Through
the CLI's composite command, with no snapshot, its `PATH` is
`/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`. Root's
login shell resets it there, so `pytest` does not resolve. `git clone -q
/work /tmp/w` worked, and this repo's test runner, called by its full
path, ran a test in the clone. `SA-0156`'s review prompt and `SA-0176`'s
writer prompt tell the session so. This spec writes no prompt text.

## Out of scope

- **`end_review.layer_cell`.** `SA-0169` gives it the `spec_session`
  keyword that passes `UNPRIVILEGED_BASH_CAPS` to `cell_up` and runs the
  self-check. No production code calls either name before then, which is
  why both are `pending_symbols`. The `dead` gate defers each while this
  spec is open (`.saffron/gates/dead.py:4-6`, `:113-127`).
- **The cell test.** `SA-0169` carries it, since it enters `layer_cell`
  with that keyword.
- **`DESIGN.md`.** It is protected. The operator records two departures by
  hand, in `SA-0169`'s pull request, each narrowed to a spec session's
  cell.
  - §5.5 (`DESIGN.md:1065`) keeps model-authored code out of the critic
    cell. A spec session's cell now runs it, as `unprivileged` only.
  - §5.1 says "No capability is granted to anything" (`DESIGN.md:587`). A
    spec session's cell now grants its root `CAP_SETUID` and `CAP_SETGID`.
    The Bash that runs model-authored code holds neither.
- **The implementer's cell.** Its Bash stays root.
- **REVIEW's lens cells.** `session.critic_cell` passes no `cap_add`, and
  a lens holds no `Bash`. They do not share the change.
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

**Every criterion is new code.** Each adds a parameter, a branch, a
constant or a function that no code at the tree base has. So each
criterion declares a witness and no mutant, and `witness` reports `skip`
for each. Import `UNPRIVILEGED_BASH_CAPS` inside the test bodies that use
it.

**Criterion 1's witness** builds `env` through `agent_options` with
`system_prompt="s"`, `max_turns=5` and `budget_usd=1.0`. It calls with
`["Bash"]` first. It pops the prefix from that `env` and asserts it is the
literal `/opt/saffron/unprivileged`, and that the rest equals the `env` for
an empty list. It asserts the prefix for `["Read", "Glob", "Grep",
"Bash"]`. It asserts no prefix for `IMPLEMENT_TOOLS`, `["Bash", "Write"]`,
`["Bash", "Edit"]`, `review.REVIEW_TOOLS`, `[]` and a call with no `tools`.
These fail it:

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
`CAP_SETGID`. It holds two `--cap-add` in all. The second holds none.
These fail it:

- `cap_add` dropped by `prepare_worktree`, by `run_detached`, or by
  `_run_argv`
- the flags placed before `--cap-drop ALL`
- one `--cap-add` with the names joined by a comma
- `prepare_worktree` defaulting to the capabilities
- a third capability granted, `CAP_SETPCAP` added to the constant

**Criterion 3's witness** uses `_stub_the_runtime` and `_drive`
(`tests/test_session.py:909`, `:1229`), with the policy
`test_the_lens_gate_cell_holds_no_credential_and_is_gone_before_any_lens_runs`
uses (`tests/test_session.py:5542-5559`), so a gate-only cell comes up. It
asserts `READY_FOR_REVIEW`. It maps each recorded `prepare_worktree`
call's container to its `cap_add`, or `()` where the call passed none.
The map holds `_IMPLEMENTER_CONTAINER`, `_CRITIC_CONTAINER` and
`_GATE_CONTAINER`, and every value is `()`. It then calls
`session.cell_up` directly with the container `c-2` and `cap_add`
`("CAP_X", "CAP_Y")`. The last recorded call is `c-2`'s, carrying those
two. These fail it:

- `_drive_cell` asking for the capabilities
- `critic_cell` asking for them
- `cell_up` dropping `cap_add`, or passing `()` in its place

**What criterion 3 leaves undriven.** `critic_cell` has five callers
(`saffron/cell/session.py:1282`, `:1398`, `:1564`, `:2563`, `:2769`), and
all share its one `prepare_worktree` call (`:1211`). The witness reaches
it through two of them. Two more cells come up outside `critic_cell`.
PACKAGE's re-verification cell calls `prepare_worktree` directly
(`saffron/phases/package.py:525`), and the proxy calls
`runtime.run_detached` directly (`saffron/cell/proxy.py:60`). Neither
passes `cap_add`. Neither file is in `touches`, so neither can gain one.

**Criterion 4's witness** replaces `runtime.exec_` with a double that
records its container and argv and returns the case's output and exit
status. The passing report is `999`, then seven `refused` lines:
`/opt/saffron`, the runner, the wrapper, `/cli`, `/sdk`, `/site` and
`/opt/venv/bin`. Two cases pass: that report, and that report with
`skipped /root/.local/bin` added. In each, the one call's argv is
`/opt/saffron/unprivileged` and one script. Every other case raises
`CellRuntimeError` matching "did not leave root". Those include the
report with `/cli` turned into `missing /cli`, and the report cut to its
first five `refused` lines. They include the same five with
`skipped /root/.local/bin` added. These fail it:

- a uid of 0 accepted
- a `wrote` line accepted
- the exit status ignored
- an empty report accepted
- the uid read alone
- the probe run through `sh` rather than the wrapper
- a `missing` line counted as a refusal
- two refusals enough to pass
- a `skipped` line read as a failure
- a `skipped` line counted as a refusal

**Criterion 5's witness** calls `assert_bash_is_unprivileged` with
criterion 4's double and its passing report, and takes the script from
the recorded argv. It makes a directory `w` in `tmp_path`, and runs
`bash -c` on the script with `subprocess.run`. Its `PATH` is `w`, then
`tmp_path / "absent"`, then `/usr/bin` and `/bin`. It asserts the output
holds the line `wrote <w>` and the line `skipped <tmp_path>/absent`, and
no line `missing <tmp_path>/absent`. It asserts nothing of the fixed
paths, since the host has no `/opt/saffron`, and nothing of the exit
status. It holds whether the suite runs as root or not, since `w` is
the running user's own directory. These fail it:

- a probe printing `refused` for every path that exists
- a probe that reads no `PATH`
- a probe printing `missing` for a `PATH` entry that does not exist,
  or nothing for it
- a probe run under `set -e`, which stops at the host's absent
  `/opt/saffron/python` before it reaches `PATH`

A probe testing `[ -r ]` in place of `[ -w ]` passes it, since `w` is
readable too. `SA-0169`'s cell test catches it, since it asserts
`refused` for paths the account can read.

**How the lists were measured.** A prototype of this spec and `SA-0169`
ran on 2026-09-27 at `f492629e`. Its five witnesses here passed. The
whole suite and `ty` stayed green at this spec's head and at `SA-0169`'s. Each wrong version above was applied
as a text edit and failed its own witness. Two also failed another
witness. The prefix with an argument failed criterion 4, and
`CAP_SETPCAP` in the constant failed `SA-0169`'s. The `[ -r ]` probe
passed criterion 5, as stated. With this spec's source reverted, all five
witnesses failed on an assertion or a missing attribute, and none failed
collection.

**What each wrapper line buys, measured.** Each version below ran against
`SA-0169`'s cell test on 2026-09-25, at `f2a08a9f`. It went through a
stand-in `layer_cell` and this repo's image. The probe then printed `missing` for
a `PATH` entry too. Its `skipped` spelling came later and is unmeasured
in a cell.

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

The last two pass the cell test. Root's inheritable set is already empty
under `--cap-drop ALL`, so `--inh-caps=-all` changes nothing measured
here. A third capability goes to root and never reaches the account.
Criterion 2 here and `SA-0169`'s criterion catch it.

Earlier versions ran in a raw container, against the same probes:
`--keep-groups` failed the group probe, and no `HOME` the `HOME` probe.
Mode `0777` failed the write to the wrapper. With no capability at all,
the "command runs" probe failed, which is why that probe exists. Without
it, every refusal passes in a cell where nothing runs.

**No witness here builds the image.** The `tests` gate never builds one,
and a cell cannot run the runtime. The Dockerfile's own `RUN` step is the
image's check, and `SA-0169`'s cell test is the operator's.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines. Keep each
Dockerfile comment to two lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** `saffron/cell/**` is in `elevate_on`, so `size` blocks at the
`feature` ceiling of 3000 changed tokens (`saffron/gates/core/size.py:26`).
The prototype, formatted with `ruff format`, measured 1159 changed tokens
with `size_gate`'s own count. The Dockerfile took 142, the wrapper 69,
`implement.py` 77, `runtime.py` 33, `worktree.py` 5 and `session.py` 260.
The tests took 573. Sibling cells landed at 1.4 times their authors'
estimates, so about 1623 tokens, 54% of the ceiling. The plan's
`estimated_lines` counts lines, and the checkpoint prices each line at 4
tokens (`saffron/gates/core/size.py:39`). So plan this at about 406
changed lines, not at a token count.
