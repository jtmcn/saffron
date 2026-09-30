"""Turning a stack batch's qualified end-review findings into follow-up spec
candidates (ADR 7, backlog item b-792ab2, step 7).

`write_follow_ups` is the first caller of `qualify.qualify`. It walks one
stack's layers, asks the injected `qualify` for `FollowUpGroup`s, and turns
each affordable, validated group into a `Candidate` a caller can `mint`.
A reset writer, an exhausted sub-cap, a stale probe, or a spec the host
cannot trust joins the caller-owned `pooled` list instead. This module
opens no cell and calls no model. `write` and `mint` are the caller's own
adapters.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from saffron import end_review, intake, spec_review
from saffron.cell.worktree import DIFF_FLAGS, git_argv
from saffron.gates.core.scope import matches
from saffron.ledger import Ledger
from saffron.phases import review
from saffron.qualify import FollowUpGroup, Qualification, Qualified
from saffron.repos.mirror import GitError, changed_files, file_at
from saffron.scheduler import RETIRED_DIRNAME, Candidate

# The share of `--budget` a stack batch holds back for its writer (§3).
# `SA-0173` passes `--budget * WRITER_SHARE` in as `cap_usd`.
WRITER_SHARE = 0.25

_SPEC_ID = re.compile(r"^([A-Za-z0-9]+)-([0-9]+)$")
_SLUG_WORD = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class Pooled:
    """One qualified group, or the slice of one, that became no follow-up.

    `group` holds only the findings the reason names. The probe check
    narrows a group before it pools one.
    """

    group: FollowUpGroup
    reason: str


def next_spec_id(origin_id: str, specs_dir: Path, ledger: Ledger, repo_id: int) -> str:
    """One more than the highest number sharing `origin_id`'s prefix.

    Reads three places: the live spec files, their `done/` retirees, and
    this repo's own tasks. Each carries a spec id whether or not the file
    that named it still parses, or still exists. The result is
    zero-padded to `origin_id`'s own digit width. A width already
    exceeded stays as is.
    """
    match = _SPEC_ID.match(origin_id)
    if match is None:
        raise ValueError(f"{origin_id!r} is not a spec id")
    prefix, digits = match.group(1), match.group(2)
    file_id = re.compile(rf"^{re.escape(prefix)}-([0-9]+)")

    highest = 0
    for directory in (specs_dir, specs_dir / RETIRED_DIRNAME):
        if not directory.is_dir():
            continue
        for path in directory.glob("*.md"):
            found = file_id.match(path.name)
            if found is not None:
                highest = max(highest, int(found.group(1)))
    for row in ledger.tasks_by_repo(repo_id):
        found = file_id.match(row["spec_id"])
        if found is not None:
            highest = max(highest, int(found.group(1)))

    return f"{prefix}-{str(highest + 1).zfill(len(digits))}"


def _slug(title: str) -> str:
    words = _SLUG_WORD.findall(title.lower())
    return "-".join(words) if words else "follow-up"


def _read_head(mirror: Path, head: str, path: str) -> str | None:
    try:
        return file_at(mirror, head, path)
    except GitError:
        return None


def _diff(mirror: Path, base: str, head: str) -> str:
    """One range's patch, read from `mirror` under the same pins a cell's
    own diff carries, `DIFF_FLAGS` and `worktree.git_argv`. Reads no
    operator `.git/config` either.
    """
    completed = subprocess.run(
        git_argv("diff", *DIFF_FLAGS, f"{base}..{head}"),
        cwd=mirror,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


def _origin_task_id(ledger: Ledger, repo_id: int, task_key: str) -> int:
    for row in ledger.tasks_by_repo(repo_id):
        if ledger.record_key(row["task_id"]) == task_key:
            return int(row["task_id"])
    raise KeyError(task_key)


def _origin_file_text(specs_dir: Path, spec_id: str) -> str:
    """The spec file in `specs_dir` whose parsed id is `spec_id`.

    Never one matched by its name. A file can carry a different name
    than its frontmatter id.
    """
    discovered, _failures = intake.discover_specs(specs_dir)
    for entry in discovered:
        if entry.spec.id == spec_id:
            return entry.path.read_text()
    raise ValueError(f"no spec file in {specs_dir} parses as {spec_id!r}")


def _probe_survives(mirror: Path, head: str, qualified: Qualified) -> bool:
    probe = qualified.finding.probe
    if probe is None:
        return True
    text = _read_head(mirror, head, probe.file)
    return text is not None and text.count(probe.find) == 1


def _prompt(
    *,
    candidate_id: str,
    allowed: Sequence[str],
    budget: float,
    findings: Sequence[Qualified],
    origin_spec_id: str,
    origin_text: str,
    origin_diff: str,
    origin_head: str,
    top_head: str,
) -> str:
    lines = [
        f"context: this session drafts a follow-up spec growing out of "
        f"{origin_spec_id}, the origin spec quoted in full below.",
        "Reply with the whole spec text; this session files no record of its own.",
        f"The findings below cite lines at the origin head {origin_head}. "
        f"The checkout in front of you is the top of the stack, head "
        f"{top_head}.",
        f"id: {candidate_id}",
        f"budget_usd must not exceed {budget}.",
        "allowed paths:",
        *(f"- {path}" for path in allowed),
        "findings:",
    ]
    for qualified in findings:
        finding = qualified.finding
        line = f"- {finding.file}:{finding.line}: {finding.claim}"
        if finding.probe is not None:
            line += (
                f" (probe {finding.probe.file} find={finding.probe.find!r} "
                f"replace={finding.probe.replace!r} "
                f"verdict={qualified.finding.probe_verdict})"
            )
        lines.append(line)
    lines.append(f"origin spec text ({origin_spec_id}):")
    lines.append(origin_text)
    lines.append(f"origin layer diff ({origin_head}^..{origin_head}):")
    lines.append(origin_diff)
    return "\n".join(lines)


def _validate(
    candidate: intake.Spec,
    *,
    candidate_id: str,
    origin: intake.Spec,
    group: FollowUpGroup,
    allowed: set[str],
) -> str | None:
    """`None` when `candidate` can become a follow-up. Otherwise the
    reason it cannot.
    """
    if candidate.id != candidate_id:
        return f"declared id {candidate.id!r}, not the assigned {candidate_id!r}"
    if candidate.type not in ("bug", "feature"):
        return f"declared type {candidate.type!r}, neither bug nor feature"
    if candidate.depends_on:
        return "declares a depends_on entry"
    if candidate.budget_usd > origin.budget_usd:
        return (
            f"budget_usd {candidate.budget_usd} exceeds the origin's "
            f"{origin.budget_usd}"
        )
    if not candidate.touches:
        return "declares no touches"
    for path in candidate.touches:
        if path not in allowed:
            return f"touches {path!r}, outside the allowed paths"
    written_edits = {
        (qualified.finding.probe.file, qualified.finding.probe.find)
        for qualified in group.findings
        if qualified.finding.probe is not None
    }
    for criterion in candidate.acceptance:
        if criterion.mutant is None:
            continue
        edit = (criterion.mutant.file, criterion.mutant.find)
        if edit in written_edits:
            return "declares a mutant naming a probe its own findings wrote"
    return None


def write_follow_ups(
    ledger: Ledger,
    stack: end_review.StackReview,
    *,
    batch_key: str,
    qualify: Callable[
        [Sequence[end_review.LayerReview], review.LensReview | None], Qualification
    ],
    write: Callable[[FollowUpGroup, str], spec_review.SpecWriterSession],
    mint: Callable[[Candidate], int],
    mirror: Path,
    specs_dir: Path,
    repo_id: int,
    test_paths: Sequence[str],
    cap_usd: float,
    emit: Callable[[str], None],
    pooled: list[Pooled],
) -> list[Candidate]:
    """One stack's qualified findings, turned into follow-up candidates.

    Walks `stack.layers` top down through `qualify`'s own grouping. Every
    group that survives the reset, sub-cap, probe and allowed-path checks
    gets one `write` call. What it returns is validated before it is
    minted. This function opens no cell. `write` and `mint` are the
    caller's own.
    """
    top = end_review.layer_fields(ledger, stack.layers[0].task_key)
    bottom = end_review.layer_fields(ledger, stack.layers[-1].task_key)
    stack_paths = [
        path
        for path in changed_files(mirror, f"{bottom.head}^", top.head)
        if any(matches(path, glob) for glob in test_paths)
    ]

    qualification = qualify(stack.layers, stack.join)
    emit(f"{len(qualification.pool)} qualified findings joined no group")

    def _pool(group: FollowUpGroup, reason: str) -> None:
        pooled.append(Pooled(group=group, reason=reason))
        emit(f"pooled {group.task_key} {group.file}: {reason}")

    def _charge(task_id: int, session: spec_review.SpecWriterSession) -> None:
        attempt_id = ledger.open_attempt(task_id, phase=spec_review.WRITING_PHASE)
        ledger.close_attempt(
            attempt_id,
            session_id=session.session_id,
            subtype="error" if session.error is not None else "success",
            terminal_reason=None,
            num_turns=session.num_turns,
            cost_usd_est=session.cost_usd,
        )

    spent = 0.0
    reset_reason: str | None = None
    candidates: list[Candidate] = []

    for group in qualification.groups:
        if reset_reason is not None:
            _pool(group, reset_reason)
            continue

        remainder = cap_usd - spent
        if remainder < spec_review.SPEC_WRITER_SESSION_USD:
            _pool(group, "the writer's sub-cap cannot cover another session")
            continue

        kept: list[Qualified] = []
        dropped: list[Qualified] = []
        for q in group.findings:
            (kept if _probe_survives(mirror, top.head, q) else dropped).append(q)
        if dropped:
            _pool(
                FollowUpGroup(
                    task_key=group.task_key, file=group.file, findings=tuple(dropped)
                ),
                "a named probe no longer matches exactly once at the top head",
            )
        if not kept:
            continue
        group = FollowUpGroup(
            task_key=group.task_key, file=group.file, findings=tuple(kept)
        )

        if not stack_paths:
            _pool(group, "no test path in test_paths changed across the stack")
            continue
        allowed = {group.file, *stack_paths}

        origin_task_id = _origin_task_id(ledger, repo_id, group.task_key)
        origin_fields = end_review.layer_fields(ledger, group.task_key)
        origin_row = ledger.spec_text(origin_task_id)
        origin_text = (
            origin_row["text"]
            if origin_row is not None
            else _origin_file_text(specs_dir, origin_fields.spec_id)
        )
        origin = intake.parse_spec(origin_text)

        candidate_id = next_spec_id(origin_fields.spec_id, specs_dir, ledger, repo_id)
        prompt = _prompt(
            candidate_id=candidate_id,
            allowed=sorted(allowed),
            budget=origin.budget_usd,
            findings=group.findings,
            origin_spec_id=origin_fields.spec_id,
            origin_text=origin_text,
            origin_diff=_diff(mirror, f"{origin_fields.head}^", origin_fields.head),
            origin_head=origin_fields.head,
            top_head=top.head,
        )

        try:
            session = write(group, prompt)
        except Exception as exc:
            _pool(group, f"write raised {type(exc).__name__}: {exc}")
            continue

        spent += session.cost_usd

        if session.resets_at is not None:
            reset_reason = "a writer session met the account's rate limit"
            _charge(origin_task_id, session)
            _pool(group, reset_reason)
            continue
        if session.error is not None:
            _charge(origin_task_id, session)
            _pool(group, f"writer session errored: {session.error}")
            continue

        try:
            candidate_spec = intake.parse_spec(session.text)
        except intake.SpecError as exc:
            _charge(origin_task_id, session)
            _pool(group, f"follow-up text did not parse: {exc}")
            continue

        reason = _validate(
            candidate_spec,
            candidate_id=candidate_id,
            origin=origin,
            group=group,
            allowed=allowed,
        )
        if reason is not None:
            _charge(origin_task_id, session)
            _pool(group, reason)
            continue

        path = f".saffron/specs/{candidate_id}-{_slug(candidate_spec.title)}.md"
        assert session.spec_sha is not None  # non-empty text always hashes
        candidate = Candidate(
            path=Path(path),
            spec=candidate_spec,
            spec_sha=session.spec_sha,
            task_id=None,
        )
        task_id = mint(candidate)
        _charge(task_id, session)
        ledger.attach_run_to_batch(ledger.task_run(task_id), int(batch_key))
        ledger.record_spec_text(
            task_id,
            origin="follow_up",
            spec_id=candidate_spec.id,
            path=path,
            text=session.text,
        )
        candidates.append(
            Candidate(
                path=Path(path),
                spec=candidate_spec,
                spec_sha=session.spec_sha,
                task_id=task_id,
            )
        )

    return candidates
