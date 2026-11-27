"""`saffron regate`: judge an open pull request's current head with the
task's own gates, agent-free (backlog item 97, the re-gate half of item 40).

A packaged commit is what `run_task` judged, and a review round can add
commits on top of it. This module re-runs the task's own gate suite over the
branch as GitHub shows it now, against the `base_sha` export its cell was
judged by. It records the result and leaves the task's state alone.
"""

from __future__ import annotations

import json
from pathlib import Path

from saffron import end_review, mutants, parent_versions, preflight
from saffron.cell import runtime, session
from saffron.cell.worktree import DIFF_FLAGS, GATES_MOUNT
from saffron.intake import SpecError, load_spec, parse_spec
from saffron.ledger import Ledger
from saffron.phases import package as package_phase
from saffron.phases import review
from saffron.repos import image as repo_image
from saffron.repos import mirror as git_mirror
from saffron.repos.policy import load_policy

_TASK_ROW = """
    SELECT t.task_id, t.spec_id, t.spec_sha, t.branch, t.pr_url, t.pushed_sha,
           r.run_id, r.base_sha, r.repo_id
    FROM tasks t JOIN runs r ON r.run_id = t.run_id
    WHERE t.task_id = ?
"""

# Open is the only state this judges. A merged or closed pull request has
# nothing left to re-gate against.
_JUDGEABLE_STATE = "OPEN"


class _Declined(Exception):
    """Internal to this module: a task `run_regate` will not judge.

    Named differently from `Refusal` on purpose, since
    `tests/test_refusal_count.py` scans every file but `scheduler.py` for
    that constructor. It declines a task before any gate executes, and is
    not one of §4.2.1's eight queue-scan kinds."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _task_and_run(ledger: Ledger, task_id: int, repo, url: str):
    row = ledger._db.execute(_TASK_ROW, (task_id,)).fetchone()
    if row is None:
        raise _Declined(f"task {task_id} names no task")
    if not row["pr_url"]:
        raise _Declined(f"task {task_id} carries no pull request")
    wanted = ledger.resolve_repo_id(url)
    if wanted is None or wanted != row["repo_id"]:
        raise _Declined(f"task {task_id} belongs to another repo than {repo}")
    return row


def _pull_request_state(gh: package_phase.GhRunner, pr_url: str) -> tuple[str, str]:
    done = gh(["gh", "pr", "view", pr_url, "--json", "state,baseRefName"])
    if done.returncode != 0:
        raise RuntimeError(f"gh pr view {pr_url} failed: {done.stderr.strip()[:300]}")
    info = json.loads(done.stdout)
    state, base_ref = info["state"], info["baseRefName"]
    if state != _JUDGEABLE_STATE:
        raise _Declined(f"{pr_url} is {state}, not {_JUDGEABLE_STATE}")
    return state, base_ref


def _fetch(mirror: Path, url: str, role: str, branch: str) -> str:
    # `fetch_parent_branch`'s own message would call either branch a parent.
    try:
        return package_phase.fetch_parent_branch(mirror, url, branch)
    except package_phase.ParentGone as gone:
        raise package_phase.PackageError(
            f"{role} branch {branch} could not be fetched"
        ) from gone


def _spec_at_base(exported: Path, spec_id: str, spec_sha: str):
    specs_dir = exported / ".saffron" / "specs"
    candidates = sorted(specs_dir.glob(f"{spec_id}-*.md")) if specs_dir.is_dir() else []
    if not candidates:
        raise _Declined(f"no spec file for {spec_id} under {specs_dir}")
    spec, file_sha = load_spec(candidates[0])
    if file_sha != spec_sha:
        raise _Declined(
            f"{candidates[0].name} does not hash to task's recorded spec_sha"
        )
    return spec


def _probe(task_id: int, image_tag: str) -> None:
    """N1's host-unreachability probe. It claims and releases one network for
    this call alone, the same shape `run_one_cell` and `package_ready_task`
    each run before any cell they admit."""
    network = f"saffron-regate-probe-{task_id}"
    runtime.remove_network(network)
    try:
        subnet = runtime.allocate_network(network)
        gateway = runtime.gateway(subnet)
        ports, tolerated, sockets = preflight.host_probe_ports()
        addresses = dict.fromkeys([gateway, *preflight.probe_addresses(gateway)])
        print(
            f"probing {len(ports)} host ports at "
            + ", ".join(addresses)
            + "; tolerating "
            + (", ".join(tolerated) or "nothing")
        )
        preflight.assert_host_is_unreachable(
            image_tag, network, gateway=gateway, ports=ports, sockets=sockets
        )
    finally:
        runtime.remove_network(network)


def review_commit_diff(
    mirror: Path, pushed_sha: str | None, baseline_sha: str, head: str
) -> str:
    """The diff a task's own review commits make on `head` (`b-d9a027`).

    The range starts at `pushed_sha` when it is still an ancestor of
    `head`, or at its rebased copy after a restack. Empty when `pushed_sha`
    names no packaged commit the mirror holds and `head` carries, or when
    the found start equals `head` itself. Otherwise the result keeps only
    the paths both that range and `baseline_sha..head` change, so a merge
    of the base branch alone contributes nothing. `SA-0404` runs this
    beside `own_version_pairs`.
    """
    if not pushed_sha or not git_mirror.has_commit(mirror, pushed_sha):
        return ""
    if end_review._is_ancestor(mirror, pushed_sha, head):
        start = pushed_sha
    else:
        from saffron.commit_review import _rebased_copy

        copy = _rebased_copy(mirror, head, pushed_sha)
        if copy is None:
            return ""
        start = copy
    if start == head:
        return ""
    review_paths = set(git_mirror.changed_files(mirror, start, head))
    baseline_paths = set(git_mirror.changed_files(mirror, baseline_sha, head))
    shared = sorted(review_paths & baseline_paths)
    if not shared:
        return ""
    return git_mirror._git(
        mirror,
        # Matches `git_mirror.changed_files`'s own call: unset, a non-ASCII
        # path's header comes back octal-escaped, not the real path.
        "-c",
        "core.quotePath=false",
        "--literal-pathspecs",
        "diff",
        *DIFF_FLAGS,
        start,
        head,
        "--",
        *shared,
        strip=False,
    )


def run_regate(
    task_id: int,
    *,
    repo: Path,
    ledger: Ledger,
    out_dir: Path,
    mirror_path: Path,
    gh: package_phase.GhRunner,
) -> int:
    """Everything `saffron regate` does: decline, or judge the pull request's
    current head with the task's own gates and record the count.

    No agent runs here, and `CLAUDE_CODE_OAUTH_TOKEN` is never read. A
    decline prints `regate:` and its reason, then returns 1, including a
    `revert-exempt.json` this cannot read, or a pinned mutants commit it
    cannot read (`b-c5da95`). Any other raise, a failed `gh`, a
    `PreflightFailed`, any other `PackageError`, an `OSError` reading that
    file, is left to the caller, which exits 2.
    """
    url = package_phase.real_remote(repo)
    try:
        row = _task_and_run(ledger, task_id, repo, url)
        _state, base_ref = _pull_request_state(gh, row["pr_url"])

        mirror = git_mirror.ensure_mirror(repo, mirror_path)
        base_head = _fetch(mirror, url, "base", base_ref)
        head = _fetch(mirror, url, "task", row["branch"])
        baseline_sha = git_mirror._git(mirror, "merge-base", base_head, head)

        exported = git_mirror.export_saffron_dir(
            mirror, row["base_sha"], out_dir / "regate" / str(task_id) / "gates"
        )
        text_row = ledger.spec_text(task_id)
        if text_row is None:
            spec = _spec_at_base(exported, row["spec_id"], row["spec_sha"])
        else:
            try:
                spec = parse_spec(text_row["text"])
            except SpecError as exc:
                raise _Declined(
                    f"task {task_id}'s text {text_row['n']} does not parse: "
                    + " ".join(str(exc).split())
                ) from exc
        try:
            spec = mutants.attach_mutants_at(
                mirror, ledger.task_mutants_commit(task_id), spec
            )
        except SpecError as exc:
            raise _Declined(" ".join(str(exc).split())) from exc
        policy, _policy_sha = load_policy(exported)
        exempt = package_phase.read_revert_exempt(out_dir / row["spec_id"])
    except _Declined as declined:
        print(f"regate: {declined.reason}")
        return 1
    except package_phase.RevertExemptUnreadable as unreadable:
        print(f"regate: {unreadable}")
        return 1

    cell_image = repo_image.build_cell_image(repo)
    _probe(task_id, repo_image.BASE_TAG)

    comparison = package_phase.reverify(
        mirror=mirror,
        packaged_sha=head,
        new_base_sha=baseline_sha,
        policy=policy,
        gates_dir=exported,
        image=cell_image,
        spec=spec,
        exempt=exempt,
    )

    for gate, failure in comparison.new_failures:
        print(f"regate: {gate} {failure.code} {failure.file}")
    count = len(comparison.new_failures)

    # A review commit on `head` can revive an already-killed or -raised wrong
    # version. A survivor of that ask counts as one more new failure (`SA-0404`).
    diff = review_commit_diff(mirror, row["pushed_sha"], baseline_sha, head)
    own_pairs, own_unreadable = parent_versions.own_version_pairs(
        spec=spec, out_dir=out_dir, diff=diff
    )
    if own_unreadable:
        print(f"regate: no wrong-version record read for {row['spec_id']}")
    parent_pairs, parent_unread = parent_versions.parent_version_pairs(
        depends_on=spec.depends_on,
        specs_dir=exported / ".saffron" / "specs",
        out_dir=out_dir,
        diff=diff,
    )
    for name in parent_unread:
        print(f"regate: no wrong-version record read for {name}")

    pairs = own_pairs + parent_pairs
    if pairs:
        patch = git_mirror._git(
            mirror,
            "-c",
            "core.quotePath=false",
            "diff",
            *DIFF_FLAGS,
            "--binary",
            "--full-index",
            baseline_sha,
            head,
            strip=False,
        )
        probe_spec = session.CellSpec(
            spec_id=row["spec_id"],
            spec_sha=row["spec_sha"],
            branch=row["branch"],
            base_sha=baseline_sha,
            touches=spec.touches,
            spec_type=spec.spec_type,
            body=spec.body,
        )
        session._apply_criterion_probes(
            spec=probe_spec,
            repo=repo,
            mirror=mirror,
            gates_dir=exported,
            thread_env=policy.thread_env,
            test_paths=policy.integrity.test_paths,
            gates=policy.gate_executables(Path(GATES_MOUNT)),
            patch=patch,
            pairs=pairs,
            diff=diff,
            gate_comparison=comparison,
            reviews=[review.LensReview(lens="adequacy")],
            created=set(),
            note=lambda _step, _ok, detail: print(f"regate: {detail}"),
            inert_patterns=policy.probes.inert,
            assertion=policy.witness.assertion,
        )
        for _criterion, entry in pairs:
            outcome = entry["outcome"]
            if outcome == "killed":
                continue
            print(
                f"regate: {entry['parent']} wrong version {outcome}: "
                f"{entry['version']} ({entry['summary']})"
            )
            if outcome == "survived":
                count += 1

    ledger.record_regate(
        task_id, head_sha=head, baseline_sha=baseline_sha, new_failures=count
    )
    outcome = (
        "green" if count == 0 else f"{count} new failure" + ("" if count == 1 else "s")
    )
    print(f"regate: {head[:12]} vs {baseline_sha[:12]} {outcome}")
    return 0 if count == 0 else 1
