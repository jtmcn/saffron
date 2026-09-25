"""The worktree a task edits, on a volume mounted at /work (DESIGN.md §5.1).

Cloned from the bare mirror, which is the cell's only remote — the cell
physically cannot reach the real one. Work happens on the volume, not a bind
mount: macOS bind-mount I/O is slow for the many-small-files pattern of test
collection, and the difference compounds across a four-attempt repair loop.
"""

from __future__ import annotations

import base64
import contextlib
import shlex
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path, PurePosixPath

from saffron.cell import runtime
from saffron.intake import Mutant

WORKTREE_MOUNT = "/work"
STATE_MOUNT = "/agent-state"
GATES_MOUNT = "/gates"
_MIRROR_MOUNT = "/mirror"


def mounts(volume: str, state_volume: str, gates_dir: Path) -> list[runtime.Mount]:
    """The mounts every cell gets, and why they are separate.

    Session state and any credential file must not live in the tree the agent
    can write, that the scope gate walks, and that gets patch-exported. The
    gates are read-only and come from a sha the cell never wrote: the
    executables that judge a task are not the ones the task can edit (§5.4).
    """
    return [
        runtime.Mount("volume", volume, WORKTREE_MOUNT),
        runtime.Mount("volume", state_volume, STATE_MOUNT),
        runtime.Mount("bind", str(gates_dir), GATES_MOUNT, readonly=True),
    ]


def prepare_worktree(
    *,
    mirror: Path,
    volume: str,
    base_sha: str,
    branch: str,
    image: str,
    container: str,
    network: str,
    env: Mapping[str, str],
    gates_dir: Path,
    state_volume: str | None = None,
    created: set[str] | None = None,
) -> None:
    """Clone the mirror into the volume at the base it is given, on `branch`,
    cell running.

    `network`, `env` and `gates_dir` are required, not defaulted: a cell started
    without them joins the runtime's default network with full egress, or falls
    back to the gates in `/work` that the agent can rewrite, and every
    containment control the caller ran applies to some other container (§5.1).

    `created` is the caller's leak ledger: each name is added immediately before
    the call that creates it, so a failure part-way reports what may survive and
    nothing that was never attempted.

    The mirror is bind-mounted read-only for the clone and is not among the
    mounts the cell keeps — a cell that could write the mirror could rewrite
    the history the host is about to read.

    `git clone` refuses a non-empty destination, and a freshly formatted
    volume already has a `lost+found` — init/fetch/checkout in place instead.

    `base_sha` is the base the **tree** is built on, which the caller has
    already resolved: `CellSpec.tree_base` is the run's pin unstacked and the
    parent's head otherwise. This function does not re-derive that — a second
    copy of the rule is two things sharing one word again, one layer down, and
    the two copies can disagree with nothing to notice.
    """
    state = state_volume or f"{volume}-state"
    if created is not None:
        created.add(state)
    runtime.create_volume(state)

    seed = runtime.run_ephemeral(
        image,
        [
            "sh",
            "-euc",
            f"cd {WORKTREE_MOUNT} && "
            "git init -q && "
            f"git remote add origin {_MIRROR_MOUNT} && "
            "git fetch -q origin && "
            f"git checkout -q -b {branch} {base_sha} && "
            "git remote remove origin && "
            "git config user.email saffron@localhost && "
            "git config user.name Saffron",
        ],
        mounts=[
            runtime.Mount("bind", str(mirror), _MIRROR_MOUNT, readonly=True),
            runtime.Mount("volume", volume, WORKTREE_MOUNT),
        ],
        timeout_s=600,
    )
    if seed.returncode != 0:
        raise runtime.CellRuntimeError(
            f"seeding the worktree failed: {seed.stderr.strip()}"
        )

    # Here and not at the call site: the seed above is an *ephemeral* container
    # that can fail on a base the mirror does not have or an unreadable mirror, and recording the
    # cell's name before that reports a container nothing ever created.
    if created is not None:
        created.add(container)
    runtime.run_detached(
        container,
        image,
        command=["sleep", "infinity"],
        network=network,
        env=env,
        mounts=mounts(volume, state, gates_dir),
        cpus=1,
        memory="4g",
    )


# The shape of every diff the host reads, pinned on the command line. Worktree
# config is the agent's to write (§2), and a `-c` override or an explicit flag
# beats `.git/config` — including config it pulls in via `include.path`,
# measured on git 2.50. `export_patch` reads no `.git/config`, but the agent's
# global config still reaches it.
DIFF_FLAGS = (
    # diff.srcPrefix/dstPrefix/noprefix/mnemonicPrefix all move the a/ b/ the
    # host matches paths against; these flags win over every one of them.
    "--src-prefix=a/",
    "--dst-prefix=b/",
    # diff.external replaces the diff with whatever program the agent names.
    "--no-ext-diff",
    # A textconv driver renders both sides through a program, so a real edit
    # can come back as no diff at all.
    "--no-textconv",
    # A rename is git's guess at intent; the host needs both paths, or a test
    # renamed into `touches` leaves scope nothing to object to.
    "--no-renames",
    # core.abbrev moves the `index` line's bytes `pinned_diff` compares; 7 is
    # what `auto` emitted across every shipped fixture, not `auto` itself.
    "--abbrev=7",
    # diff.context widens a hunk, and every line a hunk covers is somewhere a
    # critic finding may anchor (`parse_diff`).
    "--unified=3",
    # diff.algorithm picks a different diff for the same two trees.
    "--diff-algorithm=myers",
    # diff.ignoreSubmodules=all drops a submodule path a commit added from
    # both the name-only listing and the patch — a hole in `scope` itself,
    # not merely a cosmetic one (backlog item 89).
    "--ignore-submodules=none",
    # color.ui=always or color.diff=always paints the patch with escape
    # codes, `diff --git` headers included. The flag, not `-c color.ui=never`
    # — probed on git 2.39.5, 2.47 and 2.54, the override does not undo
    # `color.diff=always`.
    "--no-color",
    # diff.interHunkContext widens how close two hunks must be before they
    # merge into one, which widens where a critic finding may anchor exactly
    # as diff.context would.
    "--inter-hunk-context=0",
)


def git_argv(*args: str) -> list[str]:
    """`git *args` under every pin below, for a call `_git` cannot make."""
    # quotePath=false: a path outside ASCII comes back verbatim rather than
    # octal-escaped, which is what `touches` globs are written against.
    # suppressBlankEmpty=false: it strips the leading space from a blank context
    # line, and a diff the host cannot parse is an `error` the agent can set with
    # one uncommitted `git config` (§5.4).
    # useReplaceRefs=false: here, not in `DIFF_FLAGS` — measured on git 2.54,
    # `git replace` moves every read of the object graph, not only diffs
    # (backlog item 102).
    # bigFileThreshold, attributesFile: either can print an edit as `Binary files
    # differ`, so no lens reads its hunks (backlog item 103).
    # attr.tree: names a tree whose .gitattributes stands in for the worktree's
    # own, so it can hide hunks too. Empty disarms it, measured on git 2.47.3 and
    # 2.54 (backlog item b-a9ee32).
    # GIT_GRAFT_FILE, GIT_SHALLOW_FILE: a planted grafts or shallow file re-parents
    # the history `commits_ahead` counts (backlog item 110). No flag pins
    # either, and `exec_` takes no env; measured on git 2.39.5, 2.47 and 2.54.
    # advice.graftFileDeprecated=false: setting `GIT_GRAFT_FILE` alone makes
    # git print its eight-line "grafts is deprecated" hint on stderr on every
    # call, present or not — measured the same way as the two vars above.
    return [
        "env",
        "GIT_GRAFT_FILE=/dev/null",
        "GIT_SHALLOW_FILE=/dev/null",
        "git",
        "-c",
        "core.quotePath=false",
        "-c",
        "diff.suppressBlankEmpty=false",
        "-c",
        "core.useReplaceRefs=false",
        "-c",
        "advice.graftFileDeprecated=false",
        "-c",
        "core.bigFileThreshold=2g",
        "-c",
        "core.attributesFile=/dev/null",
        "-c",
        "attr.tree=",
        *args,
    ]


def _git(container: str, *args: str) -> runtime.Completed:
    return runtime.exec_(container, git_argv(*args), workdir=WORKTREE_MOUNT)


def commits_ahead(container: str, base_sha: str) -> int:
    """Doneness, measured (DESIGN.md §4.3). Zero means the attempt failed."""
    done = _git(container, "rev-list", "--count", f"{base_sha}..HEAD")
    if done.returncode != 0:
        raise runtime.CellRuntimeError(f"rev-list failed: {done.stderr.strip()}")
    return int(done.stdout.strip().splitlines()[-1])


def head_sha(container: str) -> str:
    done = _git(container, "rev-parse", "HEAD")
    if done.returncode != 0:
        raise runtime.CellRuntimeError(f"rev-parse failed: {done.stderr.strip()}")
    return done.stdout.strip().splitlines()[-1]


def commit_subjects(container: str, base_sha: str) -> list[str]:
    """The agent's own commit subjects, newest first — the only surviving trace
    of them once the squash lands (§5.7)."""
    done = _git(container, "log", "--format=%s", f"{base_sha}..HEAD")
    if done.returncode != 0:
        raise runtime.CellRuntimeError(f"log failed: {done.stderr.strip()}")
    return [line for line in done.stdout.splitlines() if line.strip()]


# Each `{prefix}`/`{diff_flags}` token below comes from `git_argv`/`DIFF_FLAGS`.
_EXPORT_PATCH_SCRIPT = """\
worktree_prefix="{prefix}"
git_dir=$($worktree_prefix rev-parse --absolute-git-dir)
head=$($worktree_prefix rev-parse HEAD)
fmt=$($worktree_prefix rev-parse --show-object-format)
dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT
git init -q --bare --template= --object-format="$fmt" "$dir"
printf '%s\\n' "$git_dir/objects" > "$dir/objects/info/alternates"
$worktree_prefix --git-dir="$dir" diff {diff_flags} "$1..$head"
"""


def export_patch(container: str, base_sha: str) -> str:
    """The patch every lens, `integrity` and `size` read, and PACKAGE applies.

    Read from a fresh bare git dir that borrows the worktree's objects
    through `objects/info/alternates`. That dir has no `info` of its own. So
    neither `* -diff` in `.git/info/attributes` nor an excluded, untracked
    `.gitattributes` reaches it (item 103). The fresh dir has no refs, so
    `HEAD` is resolved to a sha first, and `base_sha` arrives as one. It has no template and no object-format default,
    so `git init` pins both against whatever global config is readable.
    """
    prefix = shlex.join(git_argv())
    script = _EXPORT_PATCH_SCRIPT.format(
        prefix=prefix, diff_flags=shlex.join(DIFF_FLAGS)
    )
    done = runtime.exec_(
        container, ["sh", "-euc", script, "sh", base_sha], workdir=WORKTREE_MOUNT
    )
    if done.returncode != 0:
        raise runtime.CellRuntimeError(f"diff failed: {done.stderr.strip()}")
    return done.stdout


def read_at_head(container: str, path: str) -> str | None:
    """A file's content at HEAD, or None if there is no such file — what
    anchoring a finding outside a hunk needs (§5.5). Read from git rather than
    the worktree: the agent may have left the tree dirty after its last commit.
    """
    done = _git(container, "show", f"HEAD:{path}")
    return done.stdout if done.returncode == 0 else None


def commit_dirty(container: str, message: str) -> bool:
    """A host-side checkpoint: stages and commits whatever is dirty, or
    no-ops on a clean tree. `False` means there was nothing to commit — not
    a failure.

    Used when a turn ends abnormally (§4.3): the agent's own "commit as you
    go" instruction is a prompt, and a prompt is not the boundary. Real edits
    left uncommitted when a turn is cut do not survive teardown otherwise.
    """
    add = _git(container, "add", "-A")
    if add.returncode != 0:
        raise runtime.CellRuntimeError(f"add failed: {add.stderr.strip()}")
    commit = _git(container, "commit", "-q", "-m", message)
    if commit.returncode == 0:
        return True
    if "nothing to commit" in commit.stdout + commit.stderr:
        return False
    raise runtime.CellRuntimeError(f"commit failed: {commit.stderr.strip()}")


def dirty_paths(container: str) -> list[str]:
    """Paths with uncommitted changes, verbatim, untracked files included."""
    done = _git(container, "status", "--porcelain", "-z", "--untracked-files=all")
    if done.returncode != 0:
        raise runtime.CellRuntimeError(f"status failed: {done.stderr.strip()}")
    chunks = [chunk for chunk in done.stdout.split("\0") if chunk]
    paths: list[str] = []
    index = 0
    while index < len(chunks):
        entry = chunks[index]
        index += 1
        # A rename or copy emits a second NUL-terminated field — the source
        # path — which is not itself an entry.
        if "R" in entry[:2] or "C" in entry[:2]:
            index += 1
        paths.append(entry[3:])
    return sorted(paths)


def _exists_at(container: str, ref: str, path: str) -> bool:
    """Whether `path` is present in the tree `ref` names — read from git, not
    the worktree, the same reason `read_at_head` is (§5.4)."""
    return _git(container, "cat-file", "-e", f"{ref}:{path}").returncode == 0


def _revert_source(container: str, tree_base: str, paths: list[str]) -> None:
    """Check `paths` back to their content at `tree_base` — or, for a path
    added by this diff and so absent there, remove it. Reverting an added
    file to nothing rather than leaving it in place is what makes stashing
    the source of a spec that lands a module *and* its tests together break
    the import, instead of trivially satisfying the gate (`DESIGN.md` §5.4).
    """
    existing = [p for p in paths if _exists_at(container, tree_base, p)]
    added = [p for p in paths if p not in existing]
    if existing:
        done = _git(container, "checkout", tree_base, "--", *existing)
        if done.returncode != 0:
            raise runtime.CellRuntimeError(
                f"revert checkout failed: {done.stderr.strip()}"
            )
    if added:
        done = _git(container, "rm", "-f", "-q", "--", *added)
        if done.returncode != 0:
            raise runtime.CellRuntimeError(f"revert rm failed: {done.stderr.strip()}")


def _restore_source(container: str, paths: list[str]) -> None:
    """Undo `_revert_source`, partitioned the same way it is.

    Measured: `git checkout HEAD -- <paths>` requires *every* pathspec to exist
    in `HEAD` and aborts the whole checkout on the first that does not — it
    restores nothing, not just that one path. A source file the diff *deleted*
    is absent from `HEAD` and present at `tree_base`, so `_revert_source`
    recreated it; handing it back here took the entire restore down with it and
    left the tree fully reverted for `committed` and the host's salvage
    checkpoints to act on. `changed_files` is computed `--no-renames`, so every
    rename contributes one such delete.
    """
    at_head = [p for p in paths if _exists_at(container, "HEAD", p)]
    absent = [p for p in paths if p not in at_head]
    if at_head:
        done = _git(container, "checkout", "HEAD", "--", *at_head)
        if done.returncode != 0:
            raise runtime.CellRuntimeError(
                f"restore checkout failed: {done.stderr.strip()}"
            )
    if absent:
        # `--ignore-unmatch`: the path may already be gone, and a restore that
        # fails because the tree is already right is not a failure.
        done = _git(container, "rm", "-f", "-q", "--ignore-unmatch", "--", *absent)
        if done.returncode != 0:
            raise runtime.CellRuntimeError(f"restore rm failed: {done.stderr.strip()}")

    # An exit code is not the guarantee this function makes. The two arms above
    # partition `paths`, so one that succeeds while the other silently does
    # nothing exits 0 with the source still reverted — and `committed` runs
    # next and blames that on the agent (§5.4). Scoped to `paths` because work
    # elsewhere in the tree is the agent's and none of this function's business;
    # the gate has already refused to run if any of *these* paths was dirty.
    done = _git(
        container, "status", "--porcelain", "--untracked-files=all", "--", *paths
    )
    if done.returncode != 0:
        raise runtime.CellRuntimeError(f"restore status failed: {done.stderr.strip()}")
    if done.stdout.strip():
        raise runtime.CellRuntimeError(
            f"restore left the tree dirty: {done.stdout.strip()}"
        )


@contextlib.contextmanager
def source_reverted(
    container: str, tree_base: str, paths: Sequence[str]
) -> Iterator[None]:
    """The `revert` gate's one piece of worktree mutation (`DESIGN.md` §5.4).

    Reverts `paths` to `tree_base` for the block, then restores them to HEAD
    from a `finally` — failing and erroring paths alike, so the tree
    `committed` measures next is the one the agent's commits produced. Raises
    `runtime.CellRuntimeError` on a failed checkout or restore; the gate
    turns that into `error`, not `fail` — it did not run.
    """
    paths = list(paths)
    if not paths:
        # Unreachable from the gate, which skips before it gets here — kept
        # because `_restore_source` ends in a pathspec-scoped `git status`, and
        # an empty pathspec is not "no paths" to git, it is *every* path: the
        # restore would read the agent's unrelated work as its own failure.
        yield
        return
    # The revert is inside the `try`, not before it: it is two git operations,
    # and a second that fails after the first succeeded leaves half the source
    # reverted with no restore attempted. Entering first costs one restore of an
    # untouched tree in the worst case, which is a no-op.
    try:
        _revert_source(container, tree_base, paths)
        yield
    finally:
        _restore_source(container, paths)


def _confined(file: str) -> bool:
    """Whether `file` names a path inside the worktree.

    `tests.mutation._resolve_target` is the host half of this refusal and
    the reason is the same: a spec is data the operator writes, but `..` in a
    declared path is the shape that turns a check into an arbitrary write, and
    a cell mounts more than the worktree (`/agent-state` among them). Refused
    before anything is read or written, so an escaping mutant cannot be used
    to probe what exists outside the tree either.

    ponytail: lexical, where the host half calls `Path.resolve()`. A symlink
    is not the hole that would otherwise leave, because `source_mutated`
    refuses anything that is not a regular file tracked at `HEAD` — and git
    tracks no path *through* a symlink, only the link itself. What is left is
    a resolution git cannot represent either.
    """
    candidate = PurePosixPath(file)
    if candidate.is_absolute():
        return False
    depth = 0
    for part in candidate.parts:
        if part == "..":
            depth -= 1
        elif part != ".":
            depth += 1
        if depth < 0:
            return False
    return depth > 0


def _read_file(container: str, path: str) -> bytes:
    """`path`'s bytes in the cell's working tree, right now — not `HEAD`, so a
    mutation edits exactly what the tests about to run will see.

    Bytes, and through `base64` rather than `cat`, because `runtime.exec_`
    decodes with `errors="replace"`: read as text and written back, every byte
    that was not valid UTF-8 returns as U+FFFD and a CRLF may not return at
    all. The tests would then run against a file differing from `HEAD` in ways
    the mutant never declared — the thing `tests.mutation` handles raw bytes
    to prevent, restated here because the failure mode is the same one.

    A non-zero exit here becomes `error` in `witness_gate`, not a yielded
    reason: `witness.Mutated`'s own docs call this out by name — `mutate`
    "enters through a container exec, which can fail routinely" — where the
    host mutator, reading straight off disk, gets to tell "the file does not
    exist" apart from a live failure and this one does not need to.
    """
    script = f"base64 < {shlex.quote(path)}"
    done = runtime.exec_(container, ["sh", "-euc", script], workdir=WORKTREE_MOUNT)
    if done.returncode != 0:
        raise runtime.CellRuntimeError(
            f"reading {path} for its mutant failed: {done.stderr.strip()}"
        )
    return base64.b64decode(done.stdout)


# Linux caps a single argv string at `MAX_ARG_STRLEN` whatever `ARG_MAX` is.
# Measured against `saffron/cell-base:python`: 131,000 bytes of argv run,
# 131,071 and above fail.
_MAX_ARG_BYTES = 131_000

# Half the cap, not near it: the measurement names no cell runtime, and an
# oversize exec has wedged an apple/container cell before.
_CHUNK_BYTES = 65_536


def _fail_write(container: str, path: str, scratch: str | None, stderr: str) -> None:
    """Best-effort scratch cleanup, then the same restore-and-raise every
    failure of `_write_file` needs, whichever step failed: a step before the
    last never touched `path` at all, so the checkout is a no-op there, but
    calling it unconditionally is what keeps this one path the only place
    that decides what "failed" leaves behind (`item 78`).
    """
    if scratch is not None:
        runtime.exec_(
            container,
            ["sh", "-euc", f"rm -f {shlex.quote(scratch)}"],
            workdir=WORKTREE_MOUNT,
        )
    undo = _git(container, "checkout", "HEAD", "--", path)
    restored = "restored from HEAD" if undo.returncode == 0 else "AND NOT RESTORED"
    raise runtime.CellRuntimeError(
        f"writing {path}'s mutant failed ({restored}): {stderr.strip()}"
    )


def _write_file(container: str, path: str, content: bytes) -> None:
    """Write `content` to `path` inside the cell.

    `runtime.exec_` carries no stdin — only `exec_stream`, the agent's own
    turn, does — so an argument is the only channel across, and a mutant's
    `find`/`replace` can hold anything a shell would otherwise misread: a
    quote, a backslash, a newline. Base64 has no such character left, which
    is what makes each `printf` of a piece safe for an edit this function
    never has to inspect the content of.

    ponytail: one exec per `_CHUNK_BYTES` of base64, appended to a `/tmp`
    scratch file and decoded once; a file's size now costs round trips.
    """
    encoded = base64.b64encode(content).decode()
    pieces = [
        encoded[i : i + _CHUNK_BYTES] for i in range(0, len(encoded), _CHUNK_BYTES)
    ] or [""]

    done = runtime.exec_(container, ["sh", "-euc", "mktemp"], workdir=WORKTREE_MOUNT)
    if done.returncode != 0 or not done.stdout.strip():
        _fail_write(
            container, path, None, done.stderr or "mktemp printed no scratch path"
        )
    scratch = done.stdout.strip()

    for piece in pieces:
        script = f"printf '%s' {shlex.quote(piece)} >> {shlex.quote(scratch)}"
        done = runtime.exec_(container, ["sh", "-euc", script], workdir=WORKTREE_MOUNT)
        if done.returncode != 0:
            # A piece reaches only the scratch file, so `path` is untouched.
            _fail_write(container, path, scratch, done.stderr)

    script = f"base64 -d < {shlex.quote(scratch)} > {shlex.quote(path)}"
    done = runtime.exec_(container, ["sh", "-euc", script], workdir=WORKTREE_MOUNT)
    if done.returncode != 0:
        # `>` truncated before `base64 -d` wrote a byte, so the file is empty
        # or half-written *now*. `witness_gate` reports a raise from
        # `__enter__` as "could not apply" — its `applied` flag is not set yet
        # — so leaving the tree like this understates it exactly as that
        # gate's own contract comment says it must not (`item 78`).
        _fail_write(container, path, scratch, done.stderr)

    runtime.exec_(
        container,
        ["sh", "-euc", f"rm -f {shlex.quote(scratch)}"],
        workdir=WORKTREE_MOUNT,
    )


@contextlib.contextmanager
def source_mutated(container: str, mutant: Mutant) -> Iterator[str | None]:
    """`witness.Mutated`'s cell implementation (`DESIGN.md` §5.4.1) —
    `source_reverted`'s sibling, in the same file: it runs git inside the
    container and restores from a `finally`.

    Applies `mutant.find` -> `mutant.replace` to the working tree for the
    block. The undo is plain `git checkout HEAD -- <file>`, not a replay of
    displaced bytes the way `tests.mutation.host_mutator` restores — so it
    is only correct over a file that *is* at `HEAD`, and this refuses to run
    otherwise. `SA-0062` claimed `committed` guaranteed that; it does not.
    `committed_gate` runs after `run_suite`, which is where this is called
    from, so the tree here may still be dirty (backlog item 78).

    Six things apply nothing and say so by yielding the reason instead of
    `None`, leaving the tree exactly as it was: a path outside the worktree,
    a path not tracked at `HEAD`, a path tracked as something other than a
    regular file, a file carrying uncommitted work, a `find` that is absent,
    and a `find` that matches more than once. The last two are `apply_mutant`'s
    own rule for the identical case, matched here rather than re-derived; the
    uncommitted-work one is `revert`'s, for the identical reason; the two
    `ls-tree` ones are this function's own, and the comment below says why a
    symlink is worse than an untracked path. (This sentence said "four" and
    omitted the `ls-tree` pair, which the code has refused since the paragraph
    below it was written.) Any other failure to apply, or a
    failure to undo, raises `runtime.CellRuntimeError`: `witness_gate` turns
    that into `error`, never a verdict on the claim the mutant was meant to
    test.
    """
    if not _confined(mutant.file):
        yield f"mutant path {mutant.file!r} is not a relative path inside the tree"
        return
    # What the undo needs is not a *clean* path but a regular file tracked at
    # `HEAD`, and one `ls-tree` is the only thing that answers both. A
    # gitignored or untracked file is clean to `git status` and has nothing at
    # `HEAD` to come back from. A symlink is worse than either: the read and
    # the write follow it, `git checkout` restores the link — which never
    # changed — and exits 0, so the mutation survives inside a success.
    # `tests.mutation` never meets that because it writes bytes back to the
    # path it read them from; here the two halves resolve differently.
    listed = _git(container, "ls-tree", "HEAD", "--", mutant.file)
    if listed.returncode != 0:
        raise runtime.CellRuntimeError(
            f"ls-tree for {mutant.file}'s mutant failed: {listed.stderr.strip()}"
        )
    entry = listed.stdout.strip()
    if not entry:
        yield f"{mutant.file}: not tracked at HEAD, so the undo has nothing to restore"
        return
    if not entry.startswith(("100644", "100755")):
        yield (
            f"{mutant.file}: not a regular file at HEAD (mode "
            f"{entry.split()[0]}) — `git checkout` would not undo a write "
            "through it"
        )
        return
    dirty = _git(
        container,
        "status",
        "--porcelain",
        "-z",
        "--untracked-files=all",
        "--",
        mutant.file,
    )
    if dirty.returncode != 0:
        raise runtime.CellRuntimeError(
            f"status for {mutant.file}'s mutant failed: {dirty.stderr.strip()}"
        )
    if dirty.stdout.strip():
        # `revert` refuses the same way and says why: no evidence about
        # theater is worth destroying the agent's uncommitted work and
        # blinding the gate that would have caught it.
        yield (
            f"{mutant.file}: uncommitted changes — restoring to HEAD would "
            "destroy them and hide them from `committed`"
        )
        return
    content = _read_file(container, mutant.file)
    find = mutant.find.encode()
    count = content.count(find)
    if count == 0:
        yield f"{mutant.file}: find text not found"
        return
    if count > 1:
        yield (f"{mutant.file}: find text matches {count} times, expected exactly once")
        return
    _write_file(
        container, mutant.file, content.replace(find, mutant.replace.encode(), 1)
    )

    # Recorded and raised *after* the `finally`, never inside it: an exception
    # raised there replaces whatever was already propagating through, so a
    # `KeyboardInterrupt` in flight would come out as `CellRuntimeError` with
    # the interrupt demoted to `__context__`, where nothing looks.
    # `tests.mutation._mutated` carries the same shape for the same reason.
    failed_to_undo: runtime.CellRuntimeError | None = None
    try:
        yield None
    finally:
        done = _git(container, "checkout", "HEAD", "--", mutant.file)
        if done.returncode != 0:
            failed_to_undo = runtime.CellRuntimeError(
                f"mutant undo for {mutant.file} failed: {done.stderr.strip()}"
            )
        else:
            # `_restore_source` above makes the same argument: an exit code is
            # not the guarantee this function makes. The bytes are already in
            # hand, so the check is a comparison rather than a digest.
            try:
                back = _read_file(container, mutant.file)
            except runtime.CellRuntimeError as exc:
                failed_to_undo = exc
            else:
                if back != content:
                    failed_to_undo = runtime.CellRuntimeError(
                        f"mutant undo for {mutant.file} exited 0 and did not "
                        "restore the file"
                    )

    if failed_to_undo is not None:
        raise failed_to_undo


def changed_files(container: str, base_sha: str) -> list[str]:
    """Changed paths, verbatim — they are matched against `touches`.

    `-z` for the same reason `repos.mirror` uses it: a path holding a newline
    would otherwise arrive as two paths.
    """
    done = _git(
        container, "diff", *DIFF_FLAGS, "--name-only", "-z", f"{base_sha}..HEAD"
    )
    if done.returncode != 0:
        raise runtime.CellRuntimeError(f"diff --name-only failed: {done.stderr}")
    return [path for path in done.stdout.split("\0") if path.strip()]
