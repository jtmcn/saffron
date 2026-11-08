"""Reading a criterion's mutant from `refs/saffron/mutants` (DESIGN.md §5.4.1,
backlog item 80).

`SA-0339` adds the writer. This module is the reader `run_task` and
`cli._stack_mint` share, so the ref and the parser each have one path in.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from saffron.intake import Mutant, Spec, SpecError, refuse_disclosed_mutants
from saffron.repos.mirror import MUTANTS_REF, _run, file_at


class MutantsError(SpecError):
    """A mutants file, or a spec it is matched against, that cannot be
    trusted (item 80)."""


def ref_commit(mirror: Path) -> str | None:
    """The commit `MUTANTS_REF` names in `mirror`, or `None` where the ref is
    absent.

    A nonzero exit reads as no ref, which also covers a `mirror` that is not
    a repository at all. Several callers hand this a scratch path that was
    never a repo, and this is why that costs them nothing.
    """
    # ponytail: a mirror whose rev-parse fails for any other reason runs with no
    # mutants and says nothing.
    completed = _run(
        ["git", "-C", str(mirror), "rev-parse", "--verify", "--quiet", MUTANTS_REF]
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def parse_mutants(text: str, where: str) -> dict[str, Mutant]:
    """`where`'s mapping from witness to `Mutant`, read from `text`.

    `where` names the file in every error, so `SA-0339`'s writer and this
    reader share one parser with one voice.
    """
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise MutantsError(f"{where} is not valid YAML: {exc}") from exc
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise MutantsError(f"{where} is not a mapping of witness to mutant")
    found: dict[str, Mutant] = {}
    for witness, entry in raw.items():
        if not isinstance(entry, dict):
            raise MutantsError(f"{where}'s entry for {witness!r} is not a mapping")
        try:
            found[witness] = Mutant.model_validate(entry)
        except ValidationError as exc:
            raise MutantsError(
                f"{where}'s entry for {witness!r} is invalid: {exc}"
            ) from exc
    return found


def read_mutants(mirror: Path, commit: str | None, spec_id: str) -> dict[str, Mutant]:
    """`<spec_id>.yaml` at `commit`, parsed by `parse_mutants`.

    No mutants for a `None` commit or a tree with no such file. Read by
    `file_at`, never at the ref's own head, so a task that pinned an earlier
    commit stays pinned to it.
    """
    if commit is None:
        return {}
    path = f"{spec_id}.yaml"
    text = file_at(mirror, commit, path)
    if text is None:
        return {}
    return parse_mutants(text, path)


def attach_mutants(spec: Spec, found: dict[str, Mutant]) -> Spec:
    """A copy of `spec` with each criterion's mutant set from `found`, keyed
    by witness.

    Raises `MutantsError` for an unmatched witness, a witness two criteria
    share, or a subject with no mutant. Then re-runs the disclosure check
    against the filled-in copy, since `parse_spec`'s own run of it saw no
    mutants yet.
    """
    seen: set[str] = set()
    for criterion in spec.acceptance:
        if criterion.witness in seen:
            raise MutantsError(
                f"witness {criterion.witness!r} is declared by two criteria"
            )
        seen.add(criterion.witness)
    stray = sorted(set(found) - seen)
    if stray:
        raise MutantsError(
            f"the mutants file names a witness no criterion declares: {stray[0]!r}"
        )
    criteria = []
    for criterion in spec.acceptance:
        mutant = found.get(criterion.witness)
        if criterion.subject is not None and mutant is None:
            raise MutantsError(f"{criterion.witness} declares a subject with no mutant")
        criteria.append(criterion.model_copy(update={"mutant": mutant}))
    attached = spec.model_copy(update={"acceptance": criteria})
    refuse_disclosed_mutants(attached)
    return attached
