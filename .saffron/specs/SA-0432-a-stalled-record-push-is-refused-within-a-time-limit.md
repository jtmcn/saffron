---
id: SA-0432
title: "A stalled record push holds a batch for hours, with no time limit and no ssh keepalive"
type: bug
priority: 2
estimated_lines: 56
estimate_measured: true
touches:
  - saffron/record/refs.py
  - tests/test_record_refs.py
  - tests/test_record_routed.py
  - tests/test_record_migrate.py
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
  - saffron/record/contract.py
  - saffron/record/routed.py
  - saffron/record/migrate.py
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/task.py
  - saffron/scheduler.py
  - saffron/regate.py
  - saffron/parent_versions.py
  - saffron/phases/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/report/**
  - tests/test_cli.py
  - tests/test_scheduler.py
  - tests/test_refusal_count.py
  - tests/test_adopt_stack_layer.py
  - tests/test_ledger_fold_task.py
  - tests/test_queued_specs.py
budget_usd: 62
max_attempts: 3
max_turns: 220
risk: standard
acceptance:
  - claim: >-
      A record push that never returns is refused inside `PUSH_TIMEOUT_S`,
      a module constant in `saffron/record/refs.py`. The refusal is a plain
      `RecordError`, never a `StaleWriter` and never a
      `subprocess.TimeoutExpired`, and its text carries the limit's value
      followed by `s` or `seconds`. The witness patches the constant to 2
      and stalls each push in a stand-in `ssh`. It drives `RefsRecord.push`
      twice on the same ref, then `RefsRecord.append` with a `remote`. Each
      refusal comes no sooner than the limit and less than five seconds
      after it. The appended fact stays on the local ref.
    witness: tests/test_record_refs.py::test_a_push_that_never_returns_is_refused_within_the_limit
    wrong_versions:
      - "The push passes a timeout and lets `subprocess.TimeoutExpired` reach the caller."
      - "The timeout's message says only that the push timed out, without the limit."
      - "A timed-out push raises `StaleWriter`."
      - "Only `push` gets the time limit, so `append` with a `remote` still waits on git."
    covers:
      - set: the calls that start a record push
        members:
          - member: "`RefsRecord.push`"
            driven_by: tests/test_record_refs.py::test_a_push_that_never_returns_is_refused_within_the_limit
          - member: "`RefsRecord.append` on a record built with `remote`"
            driven_by: "Only `push` gets the time limit, so `append` with a `remote` still waits on git."
      - set: the pushes of one ref
        members:
          - member: the first push
            driven_by: tests/test_record_refs.py::test_a_push_that_never_returns_is_refused_within_the_limit
          - member: a second push of the same ref after a timed-out one
            driven_by: tests/test_record_refs.py::test_a_push_that_never_returns_is_refused_within_the_limit
    positive_case: >-
      Before each refusal the witness reads the stand-in's beat file grow,
      and it reads the refusal no sooner than the limit. So a refusal it
      reads came from a push that reached the stalled `ssh`, not from
      conftest's `GIT_ALLOW_PROTOCOL=file` refusing the origin at once.
  - claim: >-
      A timed-out push leaves no process behind. git and every process it
      started, the `ssh` included, are gone when the refusal reaches the
      caller. The witness's stand-in `ssh` appends a beat every 0.1 seconds.
      The witness reads at least five new beats at the refusal, then reads
      the count unchanged one second later. It drives `RefsRecord.push` and
      `RefsRecord.append` with a `remote`, each refused less than five
      seconds after the limit.
    witness: tests/test_record_refs.py::test_a_timed_out_push_leaves_no_process_behind
    wrong_versions:
      - "On the timeout the push kills git alone, the way `subprocess.run`'s own timeout does, and leaves the `ssh` git started."
      - "The push starts git in the caller's own process group and kills git's pid alone."
    covers:
      - set: the calls that start a record push
        members:
          - member: "`RefsRecord.push`"
            driven_by: tests/test_record_refs.py::test_a_timed_out_push_leaves_no_process_behind
          - member: "`RefsRecord.append` on a record built with `remote`"
            driven_by: tests/test_record_refs.py::test_a_timed_out_push_leaves_no_process_behind
    positive_case: >-
      The same beat file grows by at least five beats while each push
      waits, so the instrument that reads it flat afterwards sees a live
      stand-in when there is one.
  - claim: >-
      A `KeyboardInterrupt` raised while a record push waits reaches the
      caller unchanged, and leaves no process behind. Ctrl-C raises it, and
      so does SIGTERM under `_guarding_sigterm`. The witness raises it from
      a `SIGALRM` handler 2.5 seconds into a push against the same
      stand-in. It drives `RefsRecord.push`, then `RefsRecord.append` with a
      `remote`. For each it reads at least five new beats at the interrupt,
      then the count unchanged one second later.
    witness: tests/test_record_refs.py::test_an_interrupted_push_leaves_no_process_behind
    wrong_versions:
      - "The process group is killed on the timeout alone, so an interrupt leaves git's `ssh` alive."
      - "The interrupt is caught and raised again as a `RecordError`."
      - "The process group is killed on an interrupt in `push` alone, so an interrupt in `append` with a `remote` leaves git's `ssh` alive."
    covers:
      - set: the calls that start a record push
        members:
          - member: "`RefsRecord.push`"
            driven_by: tests/test_record_refs.py::test_an_interrupted_push_leaves_no_process_behind
          - member: "`RefsRecord.append` on a record built with `remote`"
            driven_by: "The process group is killed on an interrupt in `push` alone, so an interrupt in `append` with a `remote` leaves git's `ssh` alive."
    positive_case: >-
      The beat file gains at least five beats before each interrupt lands,
      so the flat count after it reads a stand-in that was alive.
  - claim: >-
      Where the host sets neither `GIT_SSH_COMMAND` nor `core.sshCommand`,
      each record push hands `ssh` `-o ServerAliveInterval=15 -o
      ServerAliveCountMax=4`, and `PUSH_TIMEOUT_S` exceeds 15 times 4.
      Where it sets either, or both, the push adds neither option. The
      witness reads the arguments a stand-in `ssh` receives. It drives
      neither set, through `RefsRecord.push` twice and then through
      `RefsRecord.append` with a `remote`, and `GIT_SSH_COMMAND` alone. It drives
      `core.sshCommand` alone in the mirror's own config, the global file
      under `HOME`, the file under `XDG_CONFIG_HOME`, a system file named by
      `GIT_CONFIG_SYSTEM`, and the environment's `GIT_CONFIG_COUNT`
      entries. It drives both set.
    witness: tests/test_record_refs.py::test_a_push_asks_ssh_for_keepalive_only_where_the_host_names_no_ssh_command
    wrong_versions:
      - "The keepalive options are added even where `GIT_SSH_COMMAND` is set."
      - "No keepalive option is ever added."
      - "`core.sshCommand` is read from the global config alone."
      - "`core.sshCommand` is read from the mirror's own config alone."
      - "Only the first push in a process gets the keepalive options."
      - "`PUSH_TIMEOUT_S` is 60, no longer than keepalive takes to give up."
      - "`ServerAliveInterval` is 30."
      - "The keepalive options are built in `push` alone, so `append` with a `remote` keeps `_no_prompt`'s environment."
    covers:
      - set: the calls that start a record push
        members:
          - member: "`RefsRecord.push`"
            driven_by: "No keepalive option is ever added."
          - member: "`RefsRecord.append` on a record built with `remote`"
            driven_by: "The keepalive options are built in `push` alone, so `append` with a `remote` keeps `_no_prompt`'s environment."
      - set: where the host names an ssh command
        members:
          - member: neither `GIT_SSH_COMMAND` nor `core.sshCommand`
            driven_by: "No keepalive option is ever added."
          - member: "`GIT_SSH_COMMAND` alone"
            driven_by: "The keepalive options are added even where `GIT_SSH_COMMAND` is set."
          - member: "`core.sshCommand` in the mirror's own config"
            driven_by: "`core.sshCommand` is read from the global config alone."
          - member: "`core.sshCommand` in the global file under `HOME`"
            driven_by: "`core.sshCommand` is read from the mirror's own config alone."
          - member: "`core.sshCommand` in the file under `XDG_CONFIG_HOME`"
            driven_by: tests/test_record_refs.py::test_a_push_asks_ssh_for_keepalive_only_where_the_host_names_no_ssh_command
          - member: "`core.sshCommand` in a system file named by `GIT_CONFIG_SYSTEM`"
            driven_by: tests/test_record_refs.py::test_a_push_asks_ssh_for_keepalive_only_where_the_host_names_no_ssh_command
          - member: "`core.sshCommand` in `GIT_CONFIG_COUNT` entries"
            driven_by: tests/test_record_refs.py::test_a_push_asks_ssh_for_keepalive_only_where_the_host_names_no_ssh_command
          - member: both set
            driven_by: tests/test_record_refs.py::test_a_push_asks_ssh_for_keepalive_only_where_the_host_names_no_ssh_command
      - set: the pushes of one ref
        members:
          - member: the first push
            driven_by: "No keepalive option is ever added."
          - member: a second push of the same ref
            driven_by: "Only the first push in a process gets the keepalive options."
    positive_case: >-
      The stand-in on `PATH` that logs no keepalive option for each
      `core.sshCommand` place is the one that logged both options for the
      two pushes with neither set. It logs them again on a push after that
      loop has unset every place.
---

## Context

Backlog item **b-65eb8f**, filed from batch 102 of the spec loop. After
PACKAGE pushed `saffron/SA-0419`, teardown pushed the task's record ref to
GitHub over ssh. That push stalled for 2 hours 11 minutes and never failed.
Killing it by hand let the batch go on, and teardown printed "record push
refused". `~/.saffron/batches/v0/SA-0419/events.jsonl` holds that
`Teardown` event, with git's exit `-15` and "send-pack: unexpected
disconnect while reading sideband packet".

**Every record push waits on git with no limit.** `_push` calls
`self._git("push", remote, f"{ref}:{ref}")` (`saffron/record/refs.py:157-161`).
`_git_bytes` calls `subprocess.run` with no `timeout`
(`saffron/record/refs.py:59-64`). Two calls reach `_push`: `append` on a
record built with `remote` (`saffron/record/refs.py:101-103`), and `push`
(`saffron/record/refs.py:144-149`).

**A refused push is a `RecordError` today.** `_git_bytes` raises one on a
non-zero exit, carrying git's stderr (`saffron/record/refs.py:65-73`).
`_push` turns it into `StaleWriter` only when stderr carries `[rejected]`
(`saffron/record/refs.py:162-171`). Callers catch the plain one:

- `run_task`'s `finally` calls `ledger.push_record` and catches
  `RecordError` and `OSError` into the "record push refused" `Teardown`
  event (`saffron/task.py:1144-1155`). A `subprocess.TimeoutExpired`
  escaping there would end teardown with a traceback.
- `RoutedRecord.push_unpushed` catches any exception and returns it beside
  its key (`saffron/record/routed.py:59-71`). `saffron/cli.py:467-474`
  prints each one.
- `migrate_and_push` yields `push_failed` for a `StaleWriter` or a
  `[remote rejected]` stderr and raises anything else
  (`saffron/record/migrate.py:766-773`). A timed-out push raises there, as
  a dead remote does today.

**The local ref lands first.** `append` moves the local ref with
`update-ref` before it pushes, and its `ponytail:` says so
(`saffron/record/refs.py:98-100`). That stays true.

**Ctrl-C and SIGTERM reach a push as `KeyboardInterrupt`.** The terminal
signals its foreground process group, and git sits in the caller's group
today. `_guarding_sigterm` turns SIGTERM into `KeyboardInterrupt`
(`saffron/cli.py:651-664`), and `main` wraps `saffron batch` in it.

**`_no_prompt` always sets `GIT_SSH_COMMAND`.** It appends `-o
BatchMode=yes` to the host's `GIT_SSH_COMMAND`, or to `ssh` where there is
none (`saffron/record/refs.py:25-31`). Its `ponytail:` says this overrides
a host's `core.sshCommand` and `GIT_SSH`. Measured on git 2.54.0 with an
isolated `HOME` and `XDG_CONFIG_HOME`: with both set, git starts
`GIT_SSH_COMMAND`, whether `core.sshCommand` came from `-c` or the global
file. `git config --get core.sshCommand` exits 1 where nothing sets it.
Criterion 4's prototype witness measured what it reads. That is the
mirror's own config, the global file and the file under `XDG_CONFIG_HOME`.
It is also a `GIT_CONFIG_SYSTEM` file and `GIT_CONFIG_COUNT` entries.

**How long a record push takes.** Five `git push --dry-run` calls each
pushed one record ref from the home mirror to GitHub over ssh. Each took
1.29 to 1.41 seconds on 2026-11-24, with `-o BatchMode=yes`. A dry-run push
sends no pack. A record ref's pack is one commit, two trees and one blob a
fact. No log records a successful record push's duration, because
`run_task` emits no event for one.

**The tests reach git through `subprocess.run`.** conftest sets
`GIT_ALLOW_PROTOCOL=file` for every test, so an `ssh://` origin is refused
at once (`tests/conftest.py:116-127`).
`test_every_network_git_call_asks_for_no_credential` sets `file:ssh` and a
stand-in `ssh` (`tests/test_record_refs.py:410-444`). Three spies patch
`subprocess.run` to read git's argv: `tests/test_record_routed.py:224-231`
and `tests/test_record_routed.py:429-436`, and `_spy_on_pushes`
(`tests/test_record_migrate.py:139-152`).

## Problem

1. **Bound every record push.** Add `PUSH_TIMEOUT_S`, a module constant in
   `saffron/record/refs.py` holding seconds, set to 120. Bound `_push`'s git
   call by it. A timed-out push raises the plain `RecordError` with text
   naming the limit, so every caller above treats it as the refusal it
   already handles. `_push`'s `[rejected]` reading stays as it is. The
   witness patches the constant, so each push reads it from the module.
2. **Leave nothing behind.** `subprocess.run`'s timeout kills git and
   waits for it, but the `ssh` git started stays alive. Start the push's
   git in a process group of its own, and kill that whole group on the
   timeout. `_call` in `saffron/cell/runtime.py` already does this for the
   cell runtime (`saffron/cell/runtime.py:279-317`). Its `_kill_group`
   (`saffron/cell/runtime.py:320-323`) also suppresses `PermissionError`, since macOS answers EPERM for a group
   left holding only zombies. It bounds the wait after the kill, since a
   child outside the group can keep a pipe open. Follow that shape in
   `refs.py`, and leave `saffron/cell/` as it is. A new group also takes git off the terminal's Ctrl-C. So kill
   the group on any exception that leaves the wait too, then let the
   exception go on.
3. **Ask ssh for keepalive.** Where `GIT_SSH_COMMAND` is unset and
   `git -C <mirror> config --get core.sshCommand` exits 1, append `-o
   ServerAliveInterval=15 -o ServerAliveCountMax=4` to the push's own
   `GIT_SSH_COMMAND`. Any other exit from that read raises `RecordError`,
   as `_resolve` does for its own. Only the push's environment changes, so
   `_no_prompt` and every other git call keep theirs. Edit no file under
   `~/.ssh` and no global git config.
4. **Keep the spies reading the push.** A push that leaves
   `subprocess.run` is invisible to the three spies above. Two of them
   assert that pushes happened (`tests/test_record_routed.py:448`,
   `tests/test_record_migrate.py:1742`). The third asserts that no git call
   names the origin, and it would go blind to pushes
   (`tests/test_record_routed.py:254-260`). Move each spy to whatever the
   push now starts git through, so each still reads every git argv.

## Out of scope

- **The two fetches.** `_fetch_one` and `fetch` stay unbounded
  (`saffron/record/refs.py:129-131`, `saffron/record/refs.py:151-155`).
  Batch 102 stalled on a push.
- **The `core.sshCommand` sources criterion 4 leaves undriven.**
  `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_PARAMETERS`, an `include.path` or
  `includeIf` file, and an empty `core.sshCommand=` all reach `git config
  --get`. No witness drives them.
- **A SIGKILL of saffron.** It leaves the push's group alive, as it leaves
  a gate's or the cell runtime's group today.
- **An empty `GIT_SSH_COMMAND`.** `_no_prompt` reads one as unset
  (`saffron/record/refs.py:29`). No witness drives it, so read it the same
  way or not, as you choose.
- **`GIT_SSH`.** The claim names `GIT_SSH_COMMAND` and `core.sshCommand`.
  A host that sets only `GIT_SSH` gets the keepalive options, and
  `_no_prompt` already overrides it.
- **A host `core.sshCommand`.** Such a host gets `ssh -o BatchMode=yes`
  with no keepalive, as `_no_prompt` gives it today. Honouring the host's
  command is `_no_prompt`'s `ponytail:` to lift.
- **Sending the ref again.** `RoutedRecord.push` drops its key from the
  kept set before it pushes (`saffron/record/routed.py:48-57`). A refused
  key is pushed again only when a later fact lands on it.
- **An `ssh` that leaves the group.** The group kill reaches only the
  processes that stay in git's own group. Problem 2's bounded wait keeps
  such a child from holding the push open, and no witness drives one.

## Notes for the agent

**No criterion declares a mutant.** The time limit, the group kill and the
keepalive are new code, and their spelling is yours. So `witness` will
report `skip`. The witnesses name `PUSH_TIMEOUT_S` because they patch it.

**Why 120 seconds.** The 1.3 second dry-run push is measured. The margin is
reasoned: 120 seconds is about ninety times it, and a stalled push then
costs a batch two minutes. Keepalive gives up on a dead link after 60
seconds. The limit sits above that, so on such a link ssh's own error
reaches the caller first.

**The stand-in.** Name it `ssh`. git probes any other basename with `-G`
first, so it would start twice. That was measured on the host's git
2.54.0 on macOS. Set `GIT_ALLOW_PROTOCOL` to
`file:ssh`, as `test_every_network_git_call_asks_for_no_credential` does.
Let it give up on its own after about 20 seconds, so a wrong version fails
the witness rather than hanging it. A stand-in that appends to a beat file
is the instrument for a process left behind. `os.kill(pid, 0)` reads a
zombie as alive. Import `saffron.record.refs` inside the test, and patch
the constant with `raising=False`, so the witness fails at base rather
than erroring at collection.

**Waiting after the kill.** Kill the group before you collect git's
output. Otherwise a pipe the `ssh` still holds keeps the wait open until
the stand-in gives up, and the witnesses' five-second bound fails.

**Isolate criterion 4's witness.** It writes `core.sshCommand` into config
files, so point `HOME` and `XDG_CONFIG_HOME` at temporary directories and
set `GIT_CONFIG_NOSYSTEM`. Drop that last one only for the
`GIT_CONFIG_SYSTEM` member. Remove `GIT_SSH_COMMAND` and `GIT_SSH` from the
environment first. With neither set, `_no_prompt` starts plain `ssh`, so
put a logging stand-in named `ssh` first on `PATH`. Set it apart from the
stand-in that `GIT_SSH_COMMAND` names, so each member reads its own log.

**Measured in the repo's cell image.** On 2026-11-24 the prototype's four
witnesses and the three spy files passed in `saffron/cell:saffron`, 55
tests. That image and `saffron/cell-base:python` both carry git 2.47.3,
not the 2.39.5 older notes name. There an `ssh`-named stand-in started
once a push, so no `-G` probe ran. `GIT_CONFIG_SYSTEM` and
`GIT_CONFIG_COUNT` were both honoured. The two witnesses were invoked
three times. Criterion 3's stand-in beat 26 times before each 2.5 second
alarm. Criterion 2's beat 19 or 20 times before the 2 second limit. Both
need five.

**Two things only the image showed.** The checkout was mounted as a git
worktree, whose `.git` named a host path. So `git config --file` run from
the checkout exited 128. So give each config write `cwd=tmp_path`. A
spy's return annotation of `subprocess.Popen[Any]` raised `TypeError` on
the image's Python 3.12. conftest has already swapped `subprocess.Popen`
for a function there, and a file without postponed annotations evaluates
it. Annotate such a spy `Any`.
