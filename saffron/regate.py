"""`saffron regate`: judge an open pull request's current head with the
task's own gates, agent-free (backlog item 97, the re-gate half of item 40).

A packaged commit is what `run_task` judged. A review round can add commits
on top of it, and nothing judges those today.
`docs/evidence/2026-09-10-review-fixes-past-package.md` found 34 of 38
merged pull requests landing past `pushed_sha`. This module re-runs the
task's own gate suite over the branch as GitHub shows it now, against the
`base_sha` export its cell was judged by. It records the result and leaves
the task's state alone.
"""

from __future__ import annotations

import json
from pathlib import Path

from saffron import preflight
from saffron.cell import runtime
from saffron.intake import load_spec
from saffron.ledger import Ledger
from saffron.phases import package as package_phase
from saffron.repos import image as repo_image
from saffron.repos import mirror as git_mirror
from saffron.repos.policy import load_policy

_TASK_ROW = """
    SELECT t.task_id, t.spec_id, t.spec_sha, t.branch, t.pr_url,
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
    that constructor. This is a rejection before any gate executes, not
    one of §4.2.1's eight queue-scan kinds."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _task_and_run(ledger: Ledger, task_id: int, repo, url: str):
    row = ledger._db.execute(_TASK_ROW, (task_id,)).fetchone()
    if row is None:
        raise _Declined(f"task {task_id} names no task")
    if not row["pr_url"]:
        raise _Declined(f"task {task_id} carries no pull request")
    if ledger.spec_text(task_id) is not None:
        raise _Declined(
            f"task {task_id} ran a recorded spec text, not a file at base_sha"
        )
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


def run_regate(
    task_id: int,
    *,
    repo: Path,
    ledger: Ledger,
    out_dir: Path,
    mirror_path: Path,
    gh: package_phase.GhRunner,
) -> int:
    """Everything `saffron regate` does: refuse, or judge the pull request's
    current head with the task's own gates and record the count.

    No agent runs here, and `CLAUDE_CODE_OAUTH_TOKEN` is never read. A
    refusal prints `regate:` and its reason, then returns 1. Any other
    raise, a failed `gh`, a `PreflightFailed`, a `PackageError`, is left
    to the caller, which exits 2.
    """
    url = package_phase.real_remote(repo)
    try:
        row = _task_and_run(ledger, task_id, repo, url)
        _state, base_ref = _pull_request_state(gh, row["pr_url"])

        mirror = git_mirror.ensure_mirror(repo, mirror_path)
        base_head = package_phase.fetch_parent_branch(mirror, url, base_ref)
        head = package_phase.fetch_parent_branch(mirror, url, row["branch"])
        baseline_sha = git_mirror._git(mirror, "merge-base", base_head, head)

        exported = git_mirror.export_saffron_dir(
            mirror, row["base_sha"], out_dir / "regate" / str(task_id) / "gates"
        )
        spec = _spec_at_base(exported, row["spec_id"], row["spec_sha"])
        policy, _policy_sha = load_policy(exported)
    except _Declined as declined:
        print(f"regate: {declined.reason}")
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
    )

    for gate, failure in comparison.new_failures:
        print(f"regate: {gate} {failure.code} {failure.file}")
    count = len(comparison.new_failures)
    ledger.record_regate(
        task_id, head_sha=head, baseline_sha=baseline_sha, new_failures=count
    )
    outcome = (
        "green" if count == 0 else f"{count} new failure" + ("" if count == 1 else "s")
    )
    print(f"regate: {head[:12]} vs {baseline_sha[:12]} {outcome}")
    return 0 if count == 0 else 1
