---
id: SA-0365
title: Every git worktree a cell starts from builds its own cell image, and no batch bounds the build cache
type: bug
priority: 2
estimated_lines: 97
estimate_measured: true
touches:
  - saffron/repos/image.py
  - saffron/cell/runtime.py
  - saffron/cell/runtimes/__init__.py
  - saffron/cell/runtimes/apple.py
  - saffron/cell/runtimes/podman.py
  - saffron/cli.py
  - tests/conftest.py
  - tests/test_image.py
  - tests/test_runtime.py
  - tests/test_sigterm.py
  - tests/test_batch_build_cache.py
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
  - saffron/ledger.py
  - saffron/record/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/preflight.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/regate.py
  - saffron/cell/session.py
  - tests/test_cli.py
  - tests/test_preflight.py
  - tests/test_home_lock.py
  - tests/test_finish.py
  - tests/test_task.py
  - tests/test_regate.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 60
max_attempts: 3
max_turns: 290
risk: standard
acceptance:
  - claim: >-
      `cell_tag` names the image for the repo's `origin`, so every git
      worktree of one repo builds one cell image. The witness builds the
      cell image of a repo and of two git worktrees added to it, named
      `joel+one` and `wt-two`, through `build_cell_image` with `runtime.call`
      recording each `-t` tag. The cell image tags recorded are one tag, named
      for the origin and not for the repo's directory. A second repo
      with another origin then adds a second tag.
    witness: tests/test_image.py::test_two_git_worktrees_of_one_repo_build_one_cell_image
    wrong_versions:
      - "`cell_tag` keeps the directory name, so the repo and its two git worktrees record three tags."
      - "`cell_tag` returns one constant tag, so the second repo records no tag of its own."
      - "`cell_tag` names the image for the directory holding the repo's git common dir, so every worktree shares a tag that is not the origin's name."
  - claim: >-
      The name is the last path segment of `origin`, split at `/` or `:`,
      after a trailing `/` and then a trailing `.git` suffix are stripped. The
      witness gives one name, `thermal-edge`, through nine origin forms, each
      in a repo whose directory has another name. They are https with
      `.git`, https bare, https with a trailing `/`, scp-like with an owner,
      scp-like with none, `ssh://`, a local path with `.git`, a local path
      with `.git/`, and `file://`. The https origin of a repo named `audit`
      names `audit`, so only the whole suffix is stripped. An origin whose
      last segment is empty once stripped keeps the directory name. The
      witness drives that with a local path ending in `repo` then `.git`, and
      with an https origin whose path is an owner then `.git`. An origin
      ending `joel+v0.5.git` names `joel-v0.5`, through the replacement the
      directory name takes today. A git repo with no `origin` keeps its
      directory name. The witness reads no host git config.
    witness: tests/test_image.py::test_the_cell_tag_reads_the_repo_name_from_every_origin_form
    wrong_versions:
      - The URL is split at `/` alone, so `git@host:thermal-edge.git` names `git-host-thermal-edge`.
      - A trailing `/` is kept, so the last segment is empty and the directory name is used.
      - "`.git` is kept on the name."
      - "`.git` is stripped before the trailing `/`, so `/srv/git/thermal-edge.git/` names `thermal-edge.git`."
      - The name is not made legal, so `joel+v0.5` reaches the tag.
      - A repo with no `origin` raises instead of keeping its directory name.
      - The owner is joined to the name, so `o/thermal-edge` names `o-thermal-edge`.
      - "`.git` is removed with `rstrip`, which strips characters, so `audit.git` names `aud`."
      - An empty last segment is kept, so a local path ending `repo/.git` names its whole path rather than the directory.
  - claim: >-
      A directory that is no git repo at all keeps its own name as its tag.
    witness: tests/test_image.py::test_the_cell_image_is_named_for_the_repo
    preserves: true
  - claim: >-
      `runtime.reclaim_build_cache` executes the selected dialect's
      `build_cache_reclaim_argv` through `_call`, bounded at 600 seconds, and
      returns its `Completed`. Under apple/container that argv is
      `container builder delete --force`. podman's member is `None`, and
      the function then executes nothing and returns `None`. The witness
      selects each dialect in turn through one patched `_call`, which
      records apple's argv and bound and nothing for podman.
    witness: tests/test_runtime.py::test_each_runtime_reclaims_its_build_cache_with_its_own_command
    wrong_versions:
      - apple's argv is `container builder stop`, which keeps the cache on disk.
      - apple's argv is `container image prune -a`, which leaves the builder's cache alone.
      - apple's argv drops `--force`, which fails while the builder is running.
      - podman's member names `podman image prune --force`, a spelling no measurement backs.
      - The function returns a made-up success for podman rather than `None`.
      - The function reads apple's dialect whatever is selected.
      - The function takes `_call`'s default bound of 120 seconds.
  - claim: >-
      Each batch form, plain and `--stack`, calls `runtime.reclaim_build_cache`
      once, after the unattended refusal and before `check_readiness`. A
      reclaim that succeeds prints nothing. The witness first drives a failing
      reclaim, whose line it reads through `capsys`, then a succeeding one,
      which prints no line naming the build cache. A night refused because
      podman is selected calls no reclaim, read through the same spy that
      recorded the apple calls.
    witness: tests/test_batch_build_cache.py::test_a_batch_reclaims_the_build_cache_before_readiness_on_both_forms
    wrong_versions:
      - The reclaim is called after readiness, or inside `check_readiness`, so the patched readiness is reached first.
      - The reclaim is called only when `--stack` is absent.
      - The reclaim is called before the unattended refusal, so a podman night reclaims.
      - The reclaim is called twice.
      - A reclaim that succeeds prints a line, which changes the night's pinned log.
  - claim: >-
      A reclaim that does not succeed prints one line, `batch: build cache
      not reclaimed — ` and why, and the batch goes on to readiness. The
      witness drives four outcomes. A nonzero exit with stderr prints the
      stderr, and one with no output prints `exit` and the code. A reclaim
      that timed out names the timeout, though it also carries a nonzero code
      and stderr, since `timed_out` is read first. A `CellRuntimeError` from
      `_call` prints its text.
    witness: tests/test_batch_build_cache.py::test_a_reclaim_that_fails_is_printed_and_the_batch_goes_on
    wrong_versions:
      - A failed reclaim returns 2 before readiness, so the night stops.
      - A `CellRuntimeError` is not caught, so readiness is never reached.
      - A timed-out reclaim prints its exit code 124 without naming the timeout.
      - The stderr is read before `timed_out`, so a timed-out reclaim with stderr prints that stderr and never names the timeout.
      - A nonzero exit is read as success and prints nothing.
      - The line carries stdout alone, so a refusal written to stderr prints empty.
      - A refusal with no output prints an empty reason.
---

## Context

Backlog item b-2bc0d5. On 2026-10-11 the dev laptop fell to 16 GB free.
`container system df` showed 34 images at 43.52 GB and one container at
84.45 GB, the runtime's `buildkit` builder. A hand cleanup freed about 128 GB.

**One image per directory.** `cell_tag` (`saffron/repos/image.py:24-30`) tags
`saffron/cell:` plus `repo.name`, the invoking checkout's directory name. Its
docstring at `saffron/repos/image.py:25` spells the image
`saffron/cell:<repo>`, and §5.1 shows
`saffron/cell:thermal-edge`.
`build_cell_image` (`saffron/repos/image.py:69-81`) rebuilds the base and then that tag on every
call. A cell started from a `git worktree add` directory builds under that
directory's name. The host held 27 such tags over 8 digests on 2026-10-11.
Four callers derive the tag again from the same `repo`
(`saffron/cell/session.py:1142` and `:1474`, `saffron/cli.py:1163`,
`saffron/task.py:972`). Three build it (`saffron/cell/session.py:1143`,
`saffron/task.py:1460`, `saffron/regate.py:164`).

**The ledger knows a repo by its origin.** `upsert_repo` keys its row on
`origin` (`saffron/ledger.py:1139-1159`, `ON CONFLICT(origin)`). Its `name`
column is not an identity: `run_one_cell` writes `repo.name` there
(`saffron/cell/session.py:2237`), the same directory name, and each conflict
overwrites it. `real_remote` reads the origin with `git remote get-url origin`
(`saffron/phases/package.py:105-112`). A git worktree shares its repo's
config, so every worktree reads the same origin.

**Nothing bounds the build cache.** No module in `saffron/` stops, deletes or
prunes the builder. `_batch` refuses an unproven runtime at
`saffron/cli.py:2393-2396` and calls `check_readiness` at `:2416`. Readiness
checks disk headroom (`saffron/preflight.py:585`) and reclaims nothing.

**The dialect holds what the runtimes spell differently.** `Dialect`
(`saffron/cell/runtimes/__init__.py:29-91`) grows by measurement, and the
module docstring above it admits only measured differences. apple's
`unattended` is true (`saffron/cell/runtimes/apple.py:59-60`) and podman's is
false (`saffron/cell/runtimes/podman.py:88-91`). So `_batch` refuses every
podman night before the line a reclaim would take.

## Problem

- Twenty git worktrees of one repo hold twenty cell images. Each stays
  tagged after its directory is removed.
- The builder keeps every layer it ever built. On 2026-11-10 it held 68.1 GB
  on this host, running since 2026-10-24.
- §4.5 names preflight that "would detect it and abort" as "detection without
  reclamation". That is what headroom does here.

## Out of scope

**Tags already on a host.** The per-directory tags built before this change
stay until removed by hand. A batch never deletes a `saffron/cell:` tag, since
another target repo on the same host owns its own.

**Untagged images.** A rebuild that changes a layer leaves the old digest
untagged. `container image prune` without `-a` removes those, and this
change leaves it out. On 2026-11-10 `system df` counted 12 images where
`image ls` listed 10.

**`saffron cell`, `regate`, `draft` and `finish`.** Only a batch reclaims.
`saffron/regate.py` and `saffron/preflight.py` are forbidden.

**The ledger's `name` column.** `saffron/ledger.py` and `saffron/cell/session.py`
are forbidden.

**One image across git worktrees whose Dockerfiles differ.** The origin tag
is shared, and each worktree reads its own branch's `.saffron/Dockerfile`. PACKAGE
derives the tag without rebuilding (`saffron/task.py:971-972`), and so does
the re-verification (`saffron/cli.py:1163`). `saffron regate` takes no home
lock (`saffron/cli.py:423`) and rebuilds the tag (`saffron/regate.py:164`).
A regate from another worktree between a build and PACKAGE leaves PACKAGE on
that worktree's image. This change does not close it.

**A build in flight when a batch starts.** The delete can end a build in a
process the home lock does not cover: `saffron regate`, `pytest -m cell`, or
a batch under another `--home`. That outcome is unmeasured, and this change
does not guard it. Deleting the builder also drops any CPUs or memory given
to it, and nothing in `saffron/` configures the builder today.

## Notes for the agent

**This change is new behaviour.** Criteria 1, 2, 4, 5 and 6 declare no
mutant. Expect `witness` to report `skip` for them. Criterion 3 is
`preserves`, and its test exists at base.

**Why the origin and not the ledger's name.** The ledger's `name` is the
directory name again (`saffron/cell/session.py:2237`). The origin is the key
the ledger itself treats as the repo. The last segment of it keeps this
repo's tag `saffron/cell:saffron`, in the `saffron/cell:<repo>` shape
`saffron/repos/image.py:25` spells. Read it in `image.py` with `git -C <repo> remote get-url origin`
through `subprocess`, as `real_remote` does. Do not import
`saffron.phases.package` into `saffron/repos/image.py`. A nonzero exit, empty
output, an `OSError` or an empty last segment falls back to `repo.name`.
Strip `.git` as a whole suffix, never as a set of characters.
`cell_tag(repo)` keeps its
signature, so the seven callers above need no edit.

**The dialect member.** Add `build_cache_reclaim_argv`, a `list[str] | None`
property, to `Dialect` and to both runtimes. apple spells its argv from
`self.binary`, and its comment says it was measured, with the version.
podman returns `None`, and its comment says no measurement names a command.
The member is then of the kind the module docstring calls "the exception in
kind": what was measured of one runtime and not the other. Reword that
docstring sentence so it still counts its members truly. Add
`reclaim_build_cache(timeout_s=...)` to `saffron/cell/runtime.py` beside
`inspect_image`, with a module-level bound of 600 seconds and a one-line
reason. It returns `Completed | None`. Also extend
`tests/test_runtime.py::test_every_declared_runtime_satisfies_the_dialect`
with the new member.

**The batch helper.** One function in `saffron/cli.py`, called by `_batch`
between the unattended refusal and the readiness `with` block. It catches
`runtime.CellRuntimeError` and never stops the night. A `None` result prints
nothing. `Completed.timed_out` marks a reclaim cut at its bound, with
`returncode` 124 and whatever stderr was read (`saffron/cell/runtime.py:296-302`).
So read `timed_out` before the exit code and the stderr.

**A batch in a test reaches the host's builder.** `no_host_tool_exec`
raises `HostToolExecInTest`, a `BaseException`, on any unmarked exec of
`container` (`tests/conftest.py:16-22`
and `:68-97`). Tests in `tests/test_cli.py`, `tests/test_home_lock.py` and
`tests/test_finish.py` reach `_batch`. A prototype that stubbed the first two
files alone failed
`tests/test_finish.py::test_a_stack_finish_lets_a_commit_raise_outside_its_two_types_reach_main`.
So add one autouse fixture to `tests/conftest.py`. For an unmarked test it replaces `runtime.reclaim_build_cache`
with a stub returning `Completed(0, "", "")`, through `monkeypatch.setattr`
with `raising=False`. It reads the real function first with
`getattr(runtime, "reclaim_build_cache", None)` and returns it. Criterion 4's
witness requests that fixture by name to reach the real function. The
`raising=False` and the `getattr` keep the suite collecting with the source
reverted, which `revert` needs. A success prints nothing, so no pinned batch
log in `tests/test_cli.py` changes. That file is forbidden: `SA-0363`, merged
since, edits it, and this spec needs none of it.

**The subprocess batch has no conftest.** `tests/test_sigterm.py`'s
`_BATCH_WITNESS_SCRIPT` (`:275-341`) starts a real `saffron batch` in a child
process. Without a stub there, `make check` on a host deletes that host's
builder. Replace `runtime.reclaim_build_cache` in the script beside
`preflight.check_readiness = _fake_readiness` (`:334`). The stub writes a
file next to the script's marker. Have
`test_a_batch_sent_sigterm_exits_143_with_its_log_flushed` assert that file
after `proc.returncode == 143` (`:393`), so the stub is seen taking the call.

**Criteria 5 and 6 drive `cli.main` with `--home tmp_path / "h"`, then
`batch --repo tmp_path`.** The `--home` keeps the home lock and the ledger out
of the operator's `~/.saffron`. Patch
`runtime.reclaim_build_cache` with a spy and `cli.preflight.check_readiness`
with one that records its call and returns `Readiness(False, "auth", ...)`.
The batch then exits 2 at readiness. Select a dialect with
`monkeypatch.setattr(runtime, "_selected", ...)`, as
`test_a_batch_on_a_runtime_never_proven_end_to_end_is_refused` does. Put both
witnesses in the new `tests/test_batch_build_cache.py`.

**Criterion 1's store.** Patch `runtime.call` to collect each argv's `-t`
value into a set, as `_record_builds` in `tests/test_image.py` does. Commit
each repo before `git worktree add`, with `-c user.email=... -c user.name=...`.
In criteria 1 and 2, set `GIT_CONFIG_GLOBAL=/dev/null` and
`GIT_CONFIG_NOSYSTEM=1` with `monkeypatch.setenv`, as `SA-0255`'s witnesses do,
so no host `url.<base>.insteadOf` rewrites an origin.

**Measured on this host, 2026-11-10, apple/container CLI 1.6.1, builder shim
0.13.2.** All read-only. `container builder --help` lists `start`, `status`,
`stop` and `delete`, and no prune. `container builder delete --help` reads
"Delete the builder container" with `-f, --force` "even if it is running".
`container build --help` offers `--cpus` and `--memory` "to allocate to the
builder container", so a build starts the builder it needs. The builder now
running was created at 2026-10-23T17:01:55Z, and `saffron/cell:saffron` was
built at 17:02:54Z that day. `container system df` showed one container at
68.1 GB, and `du` put the builder's directory at 63 GB. The delegate then
ran `container builder delete --force`, which exited 0, and `container
builder status` printed "builder is not running". The next `container build`
of the base image exited 0 in 42 s and started a fresh `buildkit` builder at
a new address.

**Measured on a prototype.** A diff built to this spec at base measured 387
changed tokens on `size_gate`, against the `bug` ceiling of 1300. Another 790
under `tests/**` were not counted. Its five new witnesses failed with the
source reverted, and criterion 3's passed. Every wrong version listed under
criteria 1, 2, 4, 5 and 6 failed its witness. `tests/test_cli.py`,
`tests/test_home_lock.py`, `tests/test_sigterm.py`, `tests/test_preflight.py`,
`tests/test_finish.py`, `tests/test_image.py`, `tests/test_runtime.py` and
`tests/test_batch_build_cache.py` passed on it.

**`error` is not `fail`.** A reclaim that could not execute is a printed line,
never a readiness failure and never a gate status.

Commit after each coherent step. Uncommitted work dies with the cell.
