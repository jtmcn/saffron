"""Applying and undoing a criterion's `mutant` (DESIGN.md §5.4.1).

This module builds no gate — `saffron/gates/**` is `forbidden` to this spec,
and `SA-0057` is where the applier below is wired to the repo's `tests` gate.
What lives here is the mechanism a gate needs: turn a `Mutant` (`saffron.intake`)
into a byte edit against a real tree, and turn it back, with no opinion on
what an unapplied mutant *means* — that is `ok=False` and a `reason`, never an
exception and never a status. Whether that becomes a `skip`, a `fail` or a
refusal is `SA-0057`'s code, not this one's.

Everything here reads and writes raw bytes, never text. A file opened in text
mode has its line endings translated on the way in and, depending on how it is
reopened, on the way out — and the gate this feeds executes inside the
worktree a task is being packaged from, so anything it does must be undone
exactly: byte-identical, including a trailing newline or a CRLF line ending
that text mode would otherwise normalize away.

`host_mutator` (`SA-0060`) is the host-tree implementation of
`witness.Mutated` — a callable from a `Mutant` to a context manager that
applies on entry and undoes on exit, the shape `saffron/gates/core/witness.py`
now asks for instead of a bare `tree: Path` it would have to do its own file
I/O against. It is built entirely on `apply_mutant`/`restore_mutant` below,
unchanged: this module still knows nothing about gates, `skip`, or `error` —
it only turns "could not apply" into a yielded reason instead of a status, and
"could not restore" into a raised exception, and leaves both readings to the
gate that injects it.
"""

from __future__ import annotations

import contextlib
import hashlib
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path

from saffron.intake import Mutant


class MutationError(ValueError):
    """Restoring a mutant failed. Applying never raises this — it reports
    `MutationResult(ok=False, ...)` instead, because a mutant that does not
    apply is the ordinary case when an implementation is written differently
    from what the spec anticipated (§5.4.1). Restoring is different: by the
    time it is called, the caller believes the tree is in the mutated state
    `apply_mutant` left it in, and a caller that cannot trust that has no safe
    way to proceed silently."""


@dataclass(frozen=True)
class MutationResult:
    """The applier's answer: whether the mutant applied, everything
    `restore_mutant` needs to undo it, and why not when it did not apply.

    `offset` is the byte position `find` occupied before the edit, which is
    also where `replace` now sits — recorded rather than rediscovered, because
    `replace` is schema-legal as `""` (an ordinary deletion mutant: a guard or
    a clamp removed entirely) and searching a file for an empty string, or for
    a `replace` that happens to recur elsewhere in it, does not name one
    position. `displaced` and `offset` together are what `apply_mutant`
    promises the caller in exchange for the obligation to restore.

    `applied_digest` is a digest of the whole file as `apply_mutant` left it,
    and it is what `restore_mutant` checks before writing. A span check cannot
    do this job: for a deletion mutant the written span is empty, so comparing
    it to `replace` compares `b""` to `b""` and cannot fail — the refusal was
    dead in exactly the configuration the schema defaults to. Whole-file also
    refuses a second restore, which a span check accepts and which
    double-inserts the displaced bytes.

    `ok=False` is not a weaker `ok=True` — a mutant that does not apply must
    read as "this mutant did not apply", not as "the witness survived", and a
    reason that names the file and the text is what makes that reading
    possible for whoever is looking at the result.
    """

    ok: bool
    displaced: bytes | None = None
    offset: int | None = None
    applied_digest: str | None = None
    reason: str = ""


def _resolve_target(tree: Path, file: str) -> Path | None:
    """The path `file` names inside `tree`, or `None` if it would resolve
    outside it.

    A spec is data the host reads and the operator writes, but `..` in a
    declared path is the shape that turns a check into an arbitrary write, and
    this is the one place both `apply_mutant` and `restore_mutant` refuse it —
    checked before either ever reads or writes a byte, so an escaping mutant
    cannot even be used to probe what exists outside the tree.
    """
    candidate = Path(file)
    if candidate.is_absolute():
        # Refused whether or not it lands inside the tree. `file` is
        # repo-relative by contract, and the `relative_to` check below already
        # catches an absolute path pointing *outside* — so this branch exists
        # for the absolute path that points inside, which is a spec-authoring
        # error rather than an escape and would otherwise be applied silently.
        return None
    tree_resolved = tree.resolve()
    target = (tree_resolved / candidate).resolve()
    try:
        target.relative_to(tree_resolved)
    except ValueError:
        return None
    return target


def apply_mutant(tree: Path, mutant: Mutant) -> MutationResult:
    """Replace `mutant.find` with `mutant.replace` in `tree / mutant.file`.

    Applies only when `find` matches the file's current bytes exactly once.
    Zero matches is the ordinary case when the implementation reads
    differently from what the spec anticipated; more than one match means the
    mutant does not name one property, and picking one of them silently is
    how a check comes to measure something other than what it claims — both
    are refused the same way, as `ok=False` with a reason naming the file and
    the text, never as a silent edit of the first occurrence.

    Returns the exact bytes it displaced, and the offset it displaced them
    at, so the caller can put them back with `restore_mutant` — including for
    a deletion mutant (`replace=""`), where nothing distinguishes the edited
    span from its surroundings except that recorded position. Restoring is
    the caller's obligation; this is the applier's half of that promise.
    """
    target = _resolve_target(tree, mutant.file)
    if target is None:
        return MutationResult(
            ok=False,
            reason=f"mutant path {mutant.file!r} is not a relative path inside the tree",
        )

    try:
        content = target.read_bytes()
    except OSError as exc:
        return MutationResult(
            ok=False, reason=f"{mutant.file}: could not be read: {exc}"
        )

    find = mutant.find.encode()
    count = content.count(find)
    if count == 0:
        return MutationResult(
            ok=False,
            reason=f"{mutant.file}: find text not found: {mutant.find!r}",
        )
    if count > 1:
        return MutationResult(
            ok=False,
            reason=(
                f"{mutant.file}: find text matches {count} times, expected "
                f"exactly once: {mutant.find!r}"
            ),
        )

    offset = content.index(find)
    replace = mutant.replace.encode()
    new_content = content[:offset] + replace + content[offset + len(find) :]
    target.write_bytes(new_content)
    return MutationResult(
        ok=True,
        displaced=find,
        offset=offset,
        applied_digest=hashlib.sha256(new_content).hexdigest(),
    )


def restore_mutant(tree: Path, mutant: Mutant, result: MutationResult) -> None:
    """Undo a prior successful `apply_mutant`, putting `result.displaced`
    back at `result.offset`.

    Restoring by recorded position, not by searching the file for
    `mutant.replace`: `replace` is schema-legal as `""`, which every non-empty
    file "matches" at every position and therefore names none, and even a
    non-empty `replace` could coincidentally already appear elsewhere in the
    file, which would make a search-based restore ambiguous in exactly the
    cases `apply_mutant` itself refuses to be.

    The whole file is checked against the digest `apply_mutant` recorded,
    before anything is written back, so a tree that moved since then is a
    refusal rather than a corrupted restore. Not the written span against
    `mutant.replace`: for a deletion mutant that span is empty and the
    comparison is `b"" != b""`, which cannot fire — measured, and it spliced
    the displaced bytes into unrelated content instead of refusing. The
    digest also refuses a second restore, where the span check accepted one
    and inserted `displaced` twice.
    """
    if (
        not result.ok
        or result.displaced is None
        or result.offset is None
        or result.applied_digest is None
    ):
        raise MutationError("cannot restore a mutant that was not applied")

    target = _resolve_target(tree, mutant.file)
    if target is None:
        raise MutationError(
            f"mutant path {mutant.file!r} is not a relative path inside the tree"
        )

    content = target.read_bytes()
    if hashlib.sha256(content).hexdigest() != result.applied_digest:
        raise MutationError(
            f"{mutant.file}: cannot restore — the tree has moved since apply_mutant ran"
        )

    start = result.offset
    end = start + len(mutant.replace.encode())
    target.write_bytes(content[:start] + result.displaced + content[end:])


def host_mutator(tree: Path) -> Callable[[Mutant], AbstractContextManager[str | None]]:
    """The host-tree implementation of `witness.Mutated`: a host `tree`,
    turned into a callable from a `Mutant` to a context manager that applies
    on entry and undoes on exit — `apply_mutant`/`restore_mutant` above,
    wrapped rather than reimplemented, so nothing about their behaviour
    changes.

    Reached only from tests, and it stays that way for the whole sequence:
    `SA-0061`'s stub lives in `session.py` and `SA-0062`'s `source_mutated` in
    `worktree.py`, and this module is `forbidden` to both. A cell run gets its
    own mutator rather than this one.

    Entering yields `None` when the mutant applied — it is now live in `tree`
    and will be undone on exit — or a `str` reason when it did not, exactly
    `apply_mutant`'s own `reason`: the ordinary case an implementation written
    differently from what the spec anticipated produces, never an exception
    and never a status, because that reading belongs to the gate that injects
    this, not to this module (§5.4.1).
    """

    def mutate(mutant: Mutant) -> AbstractContextManager[str | None]:
        return _mutated(tree, mutant)

    return mutate


@contextlib.contextmanager
def _mutated(tree: Path, mutant: Mutant) -> Iterator[str | None]:
    """Apply `mutant` to `tree` for the block, and undo it on exit however
    the block ends — a witness that died, one that survived, an inner
    `error`, or an exception in flight.

    The restore lives in this `finally`, not in a `finally` the gate writes,
    because a context manager's exit is the one place a `BaseException`
    cannot route around. And the `finally` below does not itself raise on a
    failed restore — it *records* the failure and only raises it once the
    `finally` has run to completion. That ordering is what a review round and
    a swallowed interrupt bought here once already: an exception raised
    *inside* a `finally` replaces whatever exception was already propagating
    through it, so a `KeyboardInterrupt` in flight while `restore_mutant`
    fails on a tree the caller corrupted would come out as `MutationError` or
    `OSError` instead, with the interrupt demoted to `__context__`, where
    nothing looks. Catching the restore failure *inside* the `finally`, then
    checking it only in the code that runs after — which Python never reaches
    while an exception is still propagating — is what keeps the `finally`
    from raising at all in that case, so the interrupt continues on its own.
    On an ordinary, exception-free exit, that same check does run, and a
    failed restore is what raises here — the caller reads that as `error`,
    the worse fact, and the tree is left mutated because nothing here can put
    back what it could not read or write.
    """
    applied = apply_mutant(tree, mutant)
    if not applied.ok:
        yield applied.reason
        return

    failed_to_restore: MutationError | OSError | None = None
    try:
        yield None
    finally:
        try:
            restore_mutant(tree, mutant, applied)
        except (MutationError, OSError) as exc:
            # `OSError` too: `restore_mutant` guards neither its read nor its
            # write, so a caller that deletes the file raises
            # `FileNotFoundError` from inside this `finally`.
            failed_to_restore = exc

    if failed_to_restore is not None:
        raise failed_to_restore
