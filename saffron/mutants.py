"""Reading and writing a criterion's mutant on `refs/saffron/mutants`
(DESIGN.md §5.4.1, backlog item 80).

The reader is `run_task` and `cli._stack_mint`'s shared path in. The writer
is `saffron mutant`'s own work (`SA-0339`). It fetches origin's copy of the
ref and builds a new commit on top of it, then pushes. It never uses
`saffron/repos/mirror.py`'s helpers. Those pass no environment, and the
writer carries `GIT_TERMINAL_PROMPT=0` on every process it starts.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import yaml
from pydantic import ValidationError

from saffron.intake import (
    Mutant,
    Spec,
    SpecError,
    load_spec,
    refuse_disclosed_mutants,
    refuse_inline_mutants,
)
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


class MutantWriteRefused(Exception):
    """A write that stopped before reaching origin: a validation failure
    from step 1, or a lost race, local or at origin, that leaves the
    previous winner in place (item 80). It is never a `SpecError`.
    `cli` catches this and every `SpecError` the same way, as exit 1.
    The two come from different halves of the command. Parsing raises
    its own `SpecError` subtypes directly, and this covers everything
    else `write_mutants` itself refuses."""


class MutantGitError(RuntimeError):
    """A git failure writing the mutants ref that is no refusal: a broken
    origin, a missing remote, a held lock file, or a rollback that itself
    failed (item 80)."""


# Identity flags on every call, as `saffron/record/refs.py:23` does: a
# checkout under test inherits none, so `commit-tree` would otherwise fail.
_IDENT = ("-c", "user.email=saffron@localhost", "-c", "user.name=Saffron")

_RACE_PHRASES = (
    "but expected",
    "reference already exists",
    "unable to resolve reference",
)


def _no_prompt_env() -> dict[str, str]:
    """`os.environ`, plus the one override every process the writer starts
    carries: no terminal credential prompt, ever (item 80)."""
    return {**os.environ, "GIT_TERMINAL_PROMPT": "0"}


def _git_run(
    repo: Path,
    args: list[str],
    env: dict[str, str],
    *,
    input_bytes: bytes | None = None,
) -> subprocess.CompletedProcess[bytes]:
    """The one call every git process the writer starts goes through: an
    explicit argv and `env=` on every call, never `saffron/repos/mirror.py`'s
    helpers. The race and prompt witnesses replace `subprocess.run` with a
    wrapper that acts on the call whose argv holds `update-ref` or `push`."""
    return subprocess.run(
        ["git", "-C", str(repo), *_IDENT, *args],
        input=input_bytes,
        capture_output=True,
        env=env,
    )


def _git(
    repo: Path,
    args: list[str],
    env: dict[str, str],
    *,
    input_bytes: bytes | None = None,
) -> str:
    """`_git_run`, raising `MutantGitError` on a nonzero exit and returning
    stripped stdout text otherwise. For every call whose failure needs no
    finer reading than "this is broken"."""
    completed = _git_run(repo, args, env, input_bytes=input_bytes)
    if completed.returncode != 0:
        raise MutantGitError(
            f"git {' '.join(args)} failed ({completed.returncode}): "
            f"{completed.stderr.decode(errors='replace').strip()}"
        )
    return completed.stdout.decode().strip()


def _resolve(repo: Path, ref: str, env: dict[str, str]) -> str | None:
    """`ref`'s commit in `repo`, or `None` where it is absent. Any other
    `rev-parse` failure also reads as absent, the same forgiving rule
    `saffron/repos/mirror.py`'s `ref_commit` applies to the reader's own
    mirror: harmless here, since every check downstream still runs against
    the git this `repo` has."""
    completed = _git_run(repo, ["rev-parse", "--verify", "-q", ref], env)
    return completed.stdout.decode().strip() if completed.returncode == 0 else None


def _occurrences_at_head(
    repo: Path, path: str, find: bytes, env: dict[str, str]
) -> int:
    """How many times `find` occurs in `path` as committed at `HEAD`. A
    `path` absent at `HEAD` counts as zero. That is the same refusal as a
    `find` that occurs nowhere, since neither names text a mutant could
    run against."""
    completed = _git_run(repo, ["show", f"HEAD:{path}"], env)
    if completed.returncode != 0:
        return 0
    return completed.stdout.count(find)


def _tree_entries(
    repo: Path, commit: str | None, env: dict[str, str]
) -> dict[str, str]:
    """`commit`'s root tree as a name -> blob sha mapping, or empty for no
    commit. Non-recursive: the ref's tree holds one `<spec id>.yaml` per
    spec, at its root, and nothing else (`DESIGN.md` §5.4.1)."""
    if commit is None:
        return {}
    out = _git(repo, ["ls-tree", commit], env)
    entries: dict[str, str] = {}
    for line in out.splitlines():
        if not line:
            continue
        meta, name = line.split("\t", 1)
        entries[name] = meta.split()[2]
    return entries


def _mktree(repo: Path, entries: dict[str, str], env: dict[str, str]) -> str:
    stdin = "".join(
        f"100644 blob {sha}\t{name}\n" for name, sha in sorted(entries.items())
    )
    return _git(repo, ["mktree"], env, input_bytes=stdin.encode())


def _hash_object(repo: Path, raw: bytes, env: dict[str, str]) -> str:
    return _git(repo, ["hash-object", "-w", "--stdin"], env, input_bytes=raw)


def _is_race_phrase(stderr: str) -> bool:
    return any(phrase in stderr for phrase in _RACE_PHRASES)


def _update_ref(
    repo: Path, ref: str, new: str, old: str, env: dict[str, str]
) -> subprocess.CompletedProcess[bytes]:
    return _git_run(repo, ["update-ref", ref, new, old], env)


def _delete_ref(
    repo: Path, ref: str, old: str, env: dict[str, str]
) -> subprocess.CompletedProcess[bytes]:
    return _git_run(repo, ["update-ref", "-d", ref, old], env)


def _rollback(
    repo: Path, old_commit: str | None, new_commit: str, env: dict[str, str]
) -> None:
    """Put the local ref back to what it held before a failed push.

    Never read as a race: the push's own cause, rejected or broken, is
    already decided by its caller before this runs. A rollback that
    itself fails exits 2 either way, and names both commits, since
    neither witness drives this and no reinterpretation would help.
    """
    if old_commit:
        completed = _update_ref(repo, MUTANTS_REF, old_commit, new_commit, env)
    else:
        completed = _delete_ref(repo, MUTANTS_REF, new_commit, env)
    if completed.returncode != 0:
        raise MutantGitError(
            f"push failed and rolling {MUTANTS_REF} back from {new_commit} "
            f"to {old_commit or '(none)'} also failed "
            f"({completed.returncode}): "
            f"{completed.stderr.decode(errors='replace').strip()}"
        )


def write_mutants(repo: Path, spec_id: str, from_path: Path) -> str:
    """`saffron mutant <spec id> --from <file> [--repo <path>]`'s own work
    (item 80, `DESIGN.md` §5.4.1). Validates everything `run_task` would
    refuse, fetches origin's copy of `MUTANTS_REF`, and builds a new
    commit that adds or replaces `<spec id>.yaml`. Moves the local ref
    with a compare-and-swap, pushes with no `--force`, and returns the
    new commit's sha.

    Raises `MutantWriteRefused` for a refusal or a lost race, and
    `MutantGitError` for any other git failure.
    """
    env = _no_prompt_env()

    specs_dir = repo / ".saffron" / "specs"
    matches = sorted(specs_dir.glob(f"{spec_id}-*.md")) if specs_dir.is_dir() else []
    if len(matches) != 1:
        raise MutantWriteRefused(
            f"expected exactly one spec file {specs_dir}/{spec_id}-*.md "
            f"outside done/, found {len(matches)}"
        )
    spec, _ = load_spec(matches[0])
    if spec.id != spec_id:
        raise MutantWriteRefused(
            f"{matches[0]} declares id {spec.id!r}, not {spec_id!r}"
        )

    try:
        raw = from_path.read_bytes()
    except OSError as exc:
        raise MutantWriteRefused(
            f"--from file {from_path} could not be read: {exc}"
        ) from exc
    found = parse_mutants(raw.decode(), str(from_path))
    for witness, mutant in found.items():
        count = _occurrences_at_head(repo, mutant.file, mutant.find.encode(), env)
        if count != 1:
            raise MutantWriteRefused(
                f"{witness}'s mutant find text occurs {count} time(s) in "
                f"{mutant.file} at HEAD, expected exactly once"
            )
    attach_mutants(spec, found)
    refuse_inline_mutants(spec)

    _git(
        repo,
        ["fetch", "--prune", "origin", f"+{MUTANTS_REF}*:{MUTANTS_REF}*"],
        env,
    )
    old_commit = _resolve(repo, MUTANTS_REF, env)
    entries = _tree_entries(repo, old_commit, env)
    entries[f"{spec_id}.yaml"] = _hash_object(repo, raw, env)
    tree = _mktree(repo, entries, env)
    commit_args = ["commit-tree", tree, "-m", f"mutant {spec_id}"]
    if old_commit:
        commit_args += ["-p", old_commit]
    new_commit = _git(repo, commit_args, env)

    completed = _update_ref(repo, MUTANTS_REF, new_commit, old_commit or "", env)
    if completed.returncode != 0:
        stderr = completed.stderr.decode(errors="replace")
        if _is_race_phrase(stderr):
            current = _resolve(repo, MUTANTS_REF, env)
            if current != old_commit:
                raise MutantWriteRefused(
                    f"lost the race for {MUTANTS_REF}: expected "
                    f"{old_commit!r}, found {current!r}"
                )
        raise MutantGitError(
            f"git update-ref {MUTANTS_REF} failed ({completed.returncode}): "
            f"{stderr.strip()}"
        )

    completed = _git_run(repo, ["push", "origin", f"{MUTANTS_REF}:{MUTANTS_REF}"], env)
    if completed.returncode != 0:
        stderr = completed.stderr.decode(errors="replace")
        _rollback(repo, old_commit, new_commit, env)
        if "[rejected]" in stderr:
            raise MutantWriteRefused(
                f"origin rejected the push of {MUTANTS_REF}: {stderr.strip()}"
            )
        raise MutantGitError(
            f"git push failed ({completed.returncode}): {stderr.strip()}"
        )

    return new_commit
