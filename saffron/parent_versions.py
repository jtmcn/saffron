"""Which recorded wrong versions a child's diff puts back in play (b-9efbe2).

A parent's REVIEW already ran each declared wrong version once, against its
own criterion's witness. When a child edits that witness, the wrong versions
it once caught are worth asking again. This module chooses the pairs and
states the one line their asking earns. `SA-0402` runs them.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from pydantic import ValidationError

from saffron.gates.core.integrity import _DiffError, _parse_block, _split_blocks
from saffron.intake import RETIRED_DIRNAME, Criterion, Mutant, Spec, discover_specs

# Besides letters and digits, what continues a longer path right after `path`.
_PATH_CONTINUATION = frozenset("_.-/")


def names_file(witness: str, path: str) -> bool:
    """Whether `witness` is a node id of, or under, `path`.

    True when `witness` begins with `path`. The character right after it,
    if any, must not continue a longer path or name sharing that prefix.
    """
    if not witness.startswith(path):
        return False
    rest = witness[len(path) :]
    return not rest or not (rest[0].isalnum() or rest[0] in _PATH_CONTINUATION)


def _changed_paths(diff: str) -> list[str]:
    """Every path a diff's `diff --git` blocks name, one per block (§2.1).
    Empty for a diff `integrity` refuses, since that attempt ends before REVIEW."""
    try:
        return [_parse_block(block).path for block in _split_blocks(diff)]
    except _DiffError:
        return []


def _chosen_criteria(spec: Spec, changed_paths: list[str]) -> list[Criterion]:
    """`spec`'s criteria declaring wrong versions whose witness names a
    changed path, in the spec's own declared order."""
    return [
        criterion
        for criterion in spec.acceptance
        if criterion.wrong_versions
        and any(names_file(criterion.witness, path) for path in changed_paths)
    ]


def _resolve_parents(depends_on: list[str], specs_dir: Path) -> dict[str, Spec]:
    """Every named parent, read once from `specs_dir` and its retired
    directory, the retired copy winning where a name is in both."""
    queued, _ = discover_specs(specs_dir)
    by_id = {discovered.spec.id: discovered.spec for discovered in queued}
    retired_dir = specs_dir / RETIRED_DIRNAME
    if retired_dir.is_dir():
        retired, _ = discover_specs(retired_dir, retired=True)
        by_id.update({discovered.spec.id: discovered.spec for discovered in retired})
    return {name: by_id[name] for name in depends_on if name in by_id}


class _Unreadable(Exception):
    """Raised within one parent's record to abandon it, never past it."""


def _load_record(out_dir: Path, parent_id: str) -> list[object]:
    try:
        text = (out_dir / parent_id / "wrong-versions.json").read_text()
    except OSError as exc:
        raise _Unreadable from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise _Unreadable from exc
    if not isinstance(data, list):
        raise _Unreadable
    return data


def _parent_pairs(
    parent_id: str, criteria: list[Criterion], record: list[object]
) -> list[tuple[Criterion, dict]]:
    """One parent's pairs, or `_Unreadable` once any matching entry is bad."""
    pairs: list[tuple[Criterion, dict]] = []
    for criterion in criteria:
        for entry in record:
            if not isinstance(entry, dict) or entry.get("witness") != criterion.witness:
                continue
            if "versions" not in entry:
                raise _Unreadable
            versions = entry["versions"]
            if not isinstance(versions, list):
                raise _Unreadable
            for version in versions:
                if not isinstance(version, dict):
                    raise _Unreadable
                if version.get("outcome") != "killed":
                    continue
                try:
                    edit = Mutant.model_validate(version.get("edit"))
                except ValidationError as exc:
                    raise _Unreadable from exc
                pairs.append(
                    (
                        criterion,
                        {
                            "parent": parent_id,
                            "witness": criterion.witness,
                            "version": version.get("version"),
                            "edit": edit.model_dump(),
                            "reason": "",
                        },
                    )
                )
    return pairs


def parent_version_pairs(
    *, depends_on: list[str], specs_dir: Path, out_dir: Path, diff: str
) -> tuple[list[tuple[Criterion, dict]], list[str]]:
    """Which recorded wrong versions of which parent criteria a child's diff
    puts back in play, and which parent's record could not answer.

    A parent is named by `depends_on`, read from `specs_dir`'s retired
    directory first and from `specs_dir` itself otherwise. A name
    neither declares is left out of both returned lists. A named parent with
    no criterion the diff's changed files put in play is left out too. The
    rest is read from `out_dir / <parent id> / wrong-versions.json`: an
    unreadable one is named in the second list and contributes no pair.
    """
    if not depends_on:
        return [], []
    changed_paths = _changed_paths(diff)
    parents = _resolve_parents(depends_on, specs_dir)
    pairs: list[tuple[Criterion, dict]] = []
    unreadable: list[str] = []
    for name in depends_on:
        parent = parents.get(name)
        if parent is None:
            continue
        criteria = _chosen_criteria(parent, changed_paths)
        if not criteria:
            continue
        try:
            record = _load_record(out_dir, name)
            pairs.extend(_parent_pairs(name, criteria, record))
        except _Unreadable:
            unreadable.append(name)
    return pairs, unreadable


def describe_parent_versions(
    entries: Sequence[Mapping[str, object]], unread: Sequence[str]
) -> str:
    """REVIEW's own line for the asked parent pairs (`SA-0402`). Every entry
    counts as chosen. It then counts at most one more thing: `survived`, a
    `refusal` key read as refused, or an `unproven` outcome with neither. A
    killed or errored entry counts only as chosen. The tail names, in
    `unread`'s own order, each parent whose record could not answer."""
    chosen = len(entries)
    survived = sum(1 for e in entries if e.get("outcome") == "survived")
    refused = sum(1 for e in entries if e.get("refusal") is not None)
    unproven = sum(
        1
        for e in entries
        if e.get("outcome") == "unproven" and e.get("refusal") is None
    )
    line = (
        f"parent wrong versions: {chosen} chosen, {survived} survived, "
        f"{refused} refused, {unproven} unproven"
    )
    if unread:
        line += "; no record read for " + ", ".join(unread)
    return line
