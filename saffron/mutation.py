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
"""

from __future__ import annotations

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

    `ok=False` is not a weaker `ok=True` — a mutant that does not apply must
    read as "this mutant did not apply", not as "the witness survived", and a
    reason that names the file and the text is what makes that reading
    possible for whoever is looking at the result.
    """

    ok: bool
    displaced: bytes | None = None
    offset: int | None = None
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
            reason=f"mutant path {mutant.file!r} escapes the tree it is applied to",
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
    return MutationResult(ok=True, displaced=find, offset=offset)


def restore_mutant(tree: Path, mutant: Mutant, result: MutationResult) -> None:
    """Undo a prior successful `apply_mutant`, putting `result.displaced`
    back at `result.offset`.

    Restoring by recorded position, not by searching the file for
    `mutant.replace`: `replace` is schema-legal as `""`, which every non-empty
    file "matches" at every position and therefore names none, and even a
    non-empty `replace` could coincidentally already appear elsewhere in the
    file, which would make a search-based restore ambiguous in exactly the
    cases `apply_mutant` itself refuses to be. The byte range `apply_mutant`
    actually wrote is checked against `mutant.replace` before anything is
    written back, so a mismatch here — the tree having moved since `apply_
    mutant` ran — is a refusal, not a corrupted restore.
    """
    if not result.ok or result.displaced is None or result.offset is None:
        raise MutationError("cannot restore a mutant that was not applied")

    target = _resolve_target(tree, mutant.file)
    if target is None:
        raise MutationError(
            f"mutant path {mutant.file!r} escapes the tree it is applied to"
        )

    content = target.read_bytes()
    replace = mutant.replace.encode()
    start, end = result.offset, result.offset + len(replace)
    if content[start:end] != replace:
        raise MutationError(
            f"{mutant.file}: cannot restore — the tree has moved since apply_mutant ran"
        )

    target.write_bytes(content[:start] + result.displaced + content[end:])
