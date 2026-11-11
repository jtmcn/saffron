---
id: SA-0369
title: A cell the runtime cannot exec in loses its green patch, though its worktree volume still holds it
type: bug
priority: 2
estimated_lines: 140
estimate_measured: true
touches:
  - saffron/cell/session.py
  - saffron/cell/worktree.py
  - tests/test_session.py
  - tests/test_worktree.py
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
  - images/**
  - records/**
  - hooks/**
  - saffron/cell/runtime.py
  - saffron/cell/runtimes/**
  - saffron/cell/proxy.py
  - saffron/events.py
  - saffron/ledger.py
  - saffron/record/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/repos/**
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/view/**
  - tests/conftest.py
  - tests/test_events.py
  - tests/test_runtime.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
  - tests/fixtures/**
budget_usd: 60
max_attempts: 4
max_turns: 245
risk: standard
acceptance:
  - claim: >-
      When `session.export_patch`'s patch read from the cell fails, it
      first removes the cell with `runtime.remove_container`. Once that
      removal succeeds, it drops the cell's name from the `created` set it is
      handed. Then it reads all four again from the worktree volume: the commit subjects,
      the patch, the head sha and the changed files. Each read goes through
      `runtime.run_ephemeral`, in a fresh container of the image the export
      is handed. That container gets no `env` and exactly one mount, the
      volume handed, read-only at `worktree.WORKTREE_MOUNT`. Its network is
      `saffron-export-<spec id lowercased>`, which this export creates
      through `runtime.create_network`. That name is neither
      `saffron-cells-<id>` nor `saffron-critic-net-<id>`. A
      network of that name is removed before the create and again after
      the last read. `patch.diff` and `patch.json` then hold the same bytes
      a live cell's export writes, and the returned head sha and subjects
      are equal. The one `exported` teardown line keeps the base text
      `exported N bytes to <path>`, then names the volume and the cell's
      patch read error. The cell's own "commit subjects are unreadable" line
      is not emitted on this path. A cell whose patch read succeeds is not
      removed and keeps its name in `created`. It starts no such container
      and creates no network, and its `exported` line is the base text
      exactly. When only its subject read failed, it emits the base's
      `commit_subjects` line, returns no subjects and writes its patch as at
      base. The witness drives a live cell, the same volume behind a dead
      cell whose subject and patch reads both fail, and a live cell whose
      subject read alone fails. Each reads a rename under a global git
      config that sets `diff.noprefix`.
    witness: tests/test_session.py::test_a_cell_the_runtime_cannot_exec_in_exports_its_patch_from_the_volume
    wrong_versions:
      - The reader passes no network, so it joins the runtime's default network with full egress.
      - The reader joins the cell's own network, where the task's proxy is reachable.
      - The export's network reuses the name `saffron-cells-<id>`.
      - A failed subject read alone sends the export to the volume.
      - The cell's "commit subjects are unreadable" line is still emitted when the volume answers the subjects.
      - The volume is mounted read-write.
      - The reader is handed the OAuth token, or any `env` at all.
      - The reader also mounts the state volume.
      - Only the patch is read again, so `patch.json` carries no head sha and no files.
      - The subjects are not read again, so the dead cell's empty list is returned.
      - The reader runs its own `git diff` without the export's pins, so the volume's patch differs from the cell's.
      - The reader never changes to the worktree mount, so its git reads the wrong directory.
      - The network is never removed, or is removed before the last read.
      - No network of that name is removed before the create.
      - The `exported` line does not name the volume.
      - A live cell's `exported` line names the volume as well.
      - The volume is read even when the cell's reads succeed.
      - The cell is not removed before the volume reads, so the volume cannot attach.
      - The removal happens after the first volume read.
      - The cell's name stays in `created`.
      - A live cell is removed too.
  - claim: >-
      When the volume cannot be read either, `export_patch` returns
      `None` and the subjects the volume gave, and does not raise. It writes neither file and emits
      exactly one `export_failed` teardown line. That line begins
      `patch export FAILED — ` and names the cell's error, the volume and
      the volume's own error. The export's network is removed in this case
      too. The witness drives two such volumes. In one the reader's git
      fails, and a `commit_subjects` line names the volume. In the other the
      network create hangs with `runtime.NetworkCreateHung`, and no
      container starts. When the cell's removal exits non-zero, no container
      starts either. The one failure line then names the cell's error and
      the removal's stderr, and the cell's name stays in `created`. A volume
      whose subject read succeeds and whose patch read fails returns
      `(None, subjects)` with those subjects and emits the one failure line.
      A volume holding no commits past the base emits the
      base's `no_commits` line, writes neither file and returns
      `(None, [])`.
    witness: tests/test_session.py::test_a_volume_that_cannot_be_read_either_ends_the_export_once
    wrong_versions:
      - A failed volume read raises out of `export_patch`, which runs from a `finally`.
      - The failure line names the volume's error and drops the cell's.
      - The failure line names the cell's error and drops the volume's.
      - A failed volume subject read names no volume, so it reads as the cell's line.
      - The network is removed only when the volume read succeeds.
      - A volume with no commits writes an empty `patch.diff`.
      - The network is claimed outside the `try`, so a hung create raises out of `export_patch`.
      - A failed removal is ignored, and the volume is read anyway.
      - The cell's name leaves `created` before its removal succeeds.
      - A volume whose patch read fails drops the subjects it read.
  - claim: >-
      `_drive_cell`'s teardown hands `export_patch` the task's own worktree
      volume, `saffron-wt-<spec id>`, as `volume`. It hands
      `image.cell_tag(repo)`, the image the worktree was seeded with, as
      `image`. Both are handed before `cell_down` removes that volume.
    witness: tests/test_session.py::test_teardown_hands_the_export_the_tasks_own_volume_and_cell_image
    wrong_versions:
      - The state volume is handed as `volume`.
      - The base image is handed as `image`.
  - claim: >-
      When teardown's export removed a dead cell, `cell_down`'s second
      removal of that container emits no `survived` line for it. The witness
      drives `_drive_cell` with a cell whose reads fail at teardown. Its
      `remove_container` answers a container already removed with a non-zero
      exit, as a missing one does. Three removals of the cell's name reach
      it: `_drive_cell`'s own pre-clean, the export's, then `cell_down`'s.
    witness: tests/test_session.py::test_a_cell_the_export_removed_is_not_reported_surviving_teardown
    wrong_versions:
      - The export removes the cell and leaves its name in `created`, so `cell_down` reports it surviving.
      - The export never removes the cell.
---

## Context

Backlog item b-f582ee, found in the spec loop's run 23 and left `partial`
by `SA-0232`. Its record holds two later losses of the same kind. On
2026-11-10, in the spec loop's run 59, `SA-0362` went green and finished
REBUT. The cell runtime then failed to start any process in the cell
container ("no PID data from sync pipe"). In the spec loop's run 60 `SA-0365`'s agent died
with exit -6, and the cell runtime failed the same way. Neither task wrote a
`patch.diff`, and each ended `ORPHANED`, at $31.46 and $49.80. Both were
rebuilt by hand (#1127, #1137).

**The export execs in the cell.** `_drive_cell`'s `finally` calls
`export_patch` when the container was created
(`saffron/cell/session.py:3911-3914`), then `cell_down`
(`:3915-3924`). `export_patch` reads the subjects in their own `try`
(`:955-963`), then the patch, the head sha and the changed files
(`:964-992`). Each of those four reads execs in the container:
`worktree._git` calls `runtime.exec_` (`saffron/cell/worktree.py:275-276`),
and `worktree.export_patch` calls it too (`:331-333`). A failure there lands
in one `except` that emits `patch export FAILED` (`saffron/cell/session.py:993-994`). No
other read is tried.

**A volume one container holds cannot attach to a second.** Measured on
`apple/container` 1.6.1 with `saffron/cell:saffron`, each container on an
internal network. While a container mounting a volume exists, a second
`container run` mounting it fails, read-only or read-write:
`Error: failed to bootstrap container ... VZErrorDomain Code=2 "The storage
device attachment is invalid."` The cell container still exists when the
export runs, since `cell_down` removes it afterwards
(`saffron/cell/session.py:1227`). So the fallback removes the cell first.

**Removing the cell first loses no commit.** Measured the same way: after
`container rm -f` on a container, and after `container stop`, a
`run --rm -v vol:/work:ro` reads the commits made before the removal. `git log`
shows the last commit and `git fsck` exits 0. Three commits made immediately before
`rm -f` all survived.

**The read-only flag `Mount(readonly=True)` sends is enforced.** Measured
on `apple/container` 1.6.1, after the holder was removed with `rm -f`:
`container run --rm --cap-drop ALL --mount
type=volume,source=<vol>,target=/work,readonly saffron/cell:saffron` printed
the commit with `git log`. Its `touch /work/x` then failed with "Read-only
file system", exit 1. That is the spelling `runtime.Mount.to_flag` builds
(`saffron/cell/runtime.py:209-211`).

**Each network of the cell is named for its spec.** `_drive_cell` names them
`saffron-cells-<id>` and `saffron-critic-net-<id>`
(`saffron/cell/session.py:2163-2164`). It pre-cleans the container with its
own `runtime.remove_container` call (`saffron/cell/session.py:2176`).

**`cell_down` reports a failed removal of anything in `created`.** It
removes the container first (`saffron/cell/session.py:1227`). A non-zero
exit for a name in `created` becomes a `survived` note
(`saffron/cell/session.py:1244-1252`). A second removal of a container the
export already removed would then read as a leak. Measured on
apple/container 1.6.1: `container rm -f` of a missing name exits 1 with
"container with ID ... not found". Dropping the name from
`created` once the export's removal succeeds keeps that line true. A failed
removal keeps the name, so `cell_down` tries again and reports it.

**The volume still holds the commits at that point.** The worktree lives on
a named volume mounted at `/work` (`saffron/cell/worktree.py:42-52`).
`cell_down` removes the volume after the export returns
(`saffron/cell/session.py:1242`). DESIGN.md §4.3 says what a failed task keeps is its
exported patch, not its volume. The patch is then the only thing that
survives teardown (§5.7).

**The seed already reads the volume from a fresh container.**
`worktree._run_seed` starts one through `runtime.run_ephemeral`, with the
volume at `/work` (`saffron/cell/worktree.py:87-98`). It runs the image
`prepare_worktree` is handed. `cell_up` hands it `image.build_cell_image(repo)`
(`saffron/cell/session.py:1143`, `saffron/cell/session.py:1184`), which returns `image.cell_tag(repo)`
(`saffron/repos/image.py:105-117`). `CellSpec` carries no image
(`saffron/cell/session.py:341-406`). The Gate-only cell names the same tag with
`image.cell_tag(repo)` (`saffron/cell/session.py:1474`).

**A container with no route out takes a network of its own.**
`run_ephemeral` builds its argv with `_run_argv`
(`saffron/cell/runtime.py:488-513`). That adds `--network` only for a
network it is handed (`saffron/cell/runtime.py:243-244`). With none, the container
joins the runtime's default network with full egress. That was v0.5's
founding defect (Appendix I, quoted at `saffron/phases/package.py:581-582`).
`create_network` always creates an `--internal` network (`saffron/cell/runtime.py:341-351`).
Such a network has no route out at all (§5.1). PACKAGE's re-verify cell
claims one through `runtime.allocate_network` and removes it in a `finally`
(`saffron/phases/package.py:579-612`). Neither `apple/container` 1.6.1's `run --help` nor
the `Dialect` names a "no network" option.

**One reader looks for the `exported` step by name.** `saffron/projection.py:201`
reads a `Teardown` whose step is `exported` and whose `ok` is true.

## Problem

- **A green patch dies with a cell the runtime can no longer exec in.** The
  four reads fail together, and the export writes nothing. `cell_down` then
  removes the one place the commits lived. Two tasks lost $81 of work this
  way in two days.
- **The fallback reads a tree the agent wrote, so it must be contained.** Its
  git runs over agent-written content. So it needs the cell's own bounds at
  least: no credential, no egress, and no write to the volume.

## Out of scope

**`saffron adopt` taking an `ORPHANED` task.** The operator holds that
question. The task still ends `ORPHANED` here, with its patch on disk.

**REBUT's agent dying.** A task whose REBUT agent died reads `EXHAUSTED`
(the spec loop's run 61). That is a different defect.

**Retrying the in-cell exec.** The fallback reads the volume. It never
retries the cell.

**Volume failures criterion 2 does not drive.** It drives a reader whose
git fails and a network create that hangs. A `run_ephemeral` that raises,
and a subnet pool that refuses every create, are left. Both reach the same
handler in the prototype.

**A cell whose patch read succeeds and a later read fails.** That cell is
not read from its volume. Its head sha or changed-files failure emits the
base's `export_failed` line, and no criterion claims more.

**Teardown time and launchd.** The fallback lengthens a dead cell's
teardown by up to the removal's, the network's and the four reads' bounds.
Launchd's stop timeout is not changed here.

**The line's length.** The `exported` and `export_failed` lines render
clipped at `_DETAIL_BOUND` (`saffron/events.py:807`), while `events.jsonl`
keeps each whole.

**`events.py`.** The new lines render under the existing `teardown:` rows:
`exported N bytes`, `patch export FAILED` and `commit subjects unreadable`.
`FAMILIES` does not change.

## Notes for the agent

**This change is new behaviour.** No criterion has a mutant on the ref.
Each witness reads a keyword, a container or a line the base never
produces. Expect `witness` to report `skip` for all four.

**Read the volume through the same four reads.** The patch must be the
same bytes a live cell's export writes. So reuse `worktree.commit_subjects`,
`worktree.export_patch`, `worktree.head_sha` and `worktree.changed_files`
with every pin they carry. Do not write a second copy of any of them. One
shape that does this: let those four take either a container name or a
small frozen dataclass naming the image, the volume and the network. Route
their one exec through a helper that calls `runtime.exec_` for a name and
`runtime.run_ephemeral` for the dataclass. Annotate the union, since the
`types` gate reads both files.

**`runtime.py` is forbidden, so `run_ephemeral` keeps its signature.** It
takes no working directory. The command changes to `/work` itself, for
example `["sh", "-c", 'cd /work && exec "$@"', "sh", *argv]`. Leave
`timeout_s` at its default or set the seed's 600. Pass no `env`, no
`cpus` and no `memory`.

**The trigger.** Read the subjects from the cell first and hold any
failure. Then read the patch. Only a failed patch read starts the fallback,
which drops the held failure and reads the subjects from the volume. A
successful patch read emits the held failure as the base line and goes on
as at base.

**The network.** Name it `saffron-export-<spec id lowercased>`: apple/container
refuses an uppercase network name (measured 2026-09-16,
`tests/test_session.py:1212-1215`). Remove that name first, so a
SIGKILLed export cannot fail this one's create. Claim it with
`runtime.allocate_network`. Remove it in a `finally` that ignores the
return code, as `saffron/phases/package.py:612` does. Allocate it only on
the fallback path.

**`export_patch` gains three required keyword arguments, `volume`,
`image` and `created`.** `_drive_cell` passes `volume`,
`image.cell_tag(repo)` and its own `created` set. Import
`image` from `saffron.repos` inside the `finally`, as the Gate-only cell
imports it inside its own function. Its docstring says a dead cell makes
the exec fail (`saffron/cell/session.py:937-940`). Correct it to name the
volume read, and keep it within ten lines. The comment above the call says
the export execs inside the cell (`saffron/cell/session.py:3907-3910`).
Correct it too. The export must still precede the volume's removal.

**The removal.** Only on the fallback path, before the network and the
reads. Call `runtime.remove_container(container)` and read its return code,
since it does not raise on a non-zero exit. On success, discard the
container's name from `created`. On failure, emit the one `export_failed`
line and return without reading the volume, since measurement 1 says the
attach would fail.

**The lines.** On the volume path the `exported` step and `ok=True` stay, so
`saffron/projection.py:201` still counts it. Append the volume's name and the
cell's error to the base detail. Keep the base detail byte for byte on a
live cell. The cell's error in the line is its patch read's. On a failed volume read, emit one `export_failed` line whose
detail starts `patch export FAILED — ` and then the cell's error, so
`tests/test_session.py:3808`'s substring still holds. A failed volume
subject read keeps the `commit_subjects` step and names the volume.

**Existing tests that change.**

- `test_a_stacked_specs_patch_is_exported_against_its_parent_not_the_pin`
  calls `session.export_patch` with four arguments
  (`tests/test_session.py:326-328`). Add the three keywords. Rename no test,
  since `census` compares test names.
- `test_a_dead_cell_reports_the_failed_export_rather_than_raising` and
  `test_the_agents_subjects_survive_an_export_that_dies`
  (`tests/test_session.py:3788-3846`) kill the cell at teardown. Both
  pass unchanged on the prototype. `_stub_the_runtime` stubs the four reads by name and
  answers any first argument (`:1320-1350`). It stubs `create_network`,
  `remove_network` and `remove_container`, the last answering 0
  (`tests/test_session.py:1167-1231`).
- `_stub_the_runtime` does not stub `runtime.run_ephemeral`. A real one in
  a test hits `tests/conftest.py`'s tripwire, `HostToolExecInTest`. That is
  a `BaseException`, so `except Exception` does not catch it
  (`tests/conftest.py:19-22`). If your fallback reaches `run_ephemeral`
  under that stub, stub it there.

**The witnesses.**

- Criteria 1 and 2: a real repo in `tmp_path` stands for the volume. It
  holds a base commit, a `git mv` and one added file, made with
  `tests/test_worktree.py`'s `_commit`. Point `GIT_CONFIG_GLOBAL` at a file
  setting `diff.noprefix` to true, and set `GIT_CONFIG_NOSYSTEM`. Stub
  `runtime.exec_` to run the command in the repo for a live cell, and to
  return exit 1 with `no PID data from sync pipe` for a dead one. Stub
  `runtime.run_ephemeral` to record its arguments. It runs the command from
  `tmp_path`, with `/work` in each argument replaced by the repo's path.
  Run it from `tmp_path` so a read that never changes to `/work` fails.
  Decode both stubs' output with `runtime._decode`, as `_host_git` does
  (`tests/test_worktree.py:1124-1137`). Stub `create_network`,
  `remove_network`, `networks_on_subnet` and `remove_container` on one
  ordered list. Hand each call its own `created` set holding the cell's
  name, and read it back after. Call
  `session.export_patch` live first and dead second, into two task
  directories, and compare the two files' bytes. Compare each recorded
  mount with `runtime.Mount("volume", <volume>, "/work", readonly=True)` as
  a whole list.
- Criterion 1's third case: make the stubbed `exec_` fail only a command
  holding `log`, on a live cell.
- Criterion 2's partial volume: make the stubbed `run_ephemeral` fail only
  the patch read, the command holding `-euc`.
- Criterion 2's empty volume: a second repo whose head is its base.
- Criterion 3: `_drive` with `_stub_the_runtime`. Wrap `session.export_patch`
  in a spy that records its keywords, appends to `cell.order`, and calls
  through. Compare the spy's entry with the last
  `removed:volume:saffron-wt-SY-1`, since `cell_up` pre-cleans that name
  first.
- Criterion 4: `_drive` with `_stub_the_runtime`, the four reads raising
  once a `teardown` line is watched, as
  `test_a_dead_cell_reports_the_failed_export_rather_than_raising` does.
  Override `runtime.remove_container` to answer 0 once and non-zero with
  `not found` for a name already removed during teardown. Stub
  `runtime.run_ephemeral` to fail, in case your fallback reaches it. Assert
  no watched line holds both `survived` and the cell's name.

Import every name the change adds inside a test body. A module-scope import
of one makes the reverted test a collection error, which `revert` reads as
`skip`.

**Measured on a prototype.** A diff built to this spec at base measured 557
changed tokens on `size_gate` outside `tests/**`, and 2102 with the tests.
The `bug` ceiling is 1300. Its four witnesses failed with the source
reverted. Each wrong version listed under the four criteria ran against its
witness, and each failed it. Deleting the removal call fails criteria 1 and
4. The four reads also ran with host git 2.54 on a repository made
read-only with `chmod -R a-w`, and all four succeeded. No read writes to
`/work`.

**`error` is not `fail`.** The task's state does not change here. A task
whose cell died still ends `ORPHANED`, now with its patch on disk.

Commit after each coherent step. Uncommitted work dies with the cell.
