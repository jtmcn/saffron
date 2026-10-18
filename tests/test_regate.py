"""`saffron regate <task id> --repo .` (backlog item 97).

Every witness drives a real git fixture: a bare origin and a checkout. The
checkout commits a base, forks a parent branch and a packaged commit, then
adds a review commit. That commit merges a moved default branch into the
task's branch, the way GitHub's "update branch" does. `reverify`, the probe
and `gh` are faked. The mirror, the fetches and the merge base stay real git.
"""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path

from saffron import cli, preflight
from saffron.cell import runtime
from saffron.gates.baseline import NewFailure
from saffron.gates.contract import Failure
from saffron.gates.suite import SuiteComparison, SuiteRun
from saffron.ledger import Ledger
from saffron.phases import package as package_phase
from saffron.repos import image as repo_image

SPEC_ID = "SA-0005"
SPEC_FILENAME = f"{SPEC_ID}-regate-test.md"


def _git(repo, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _spec_text(title: str) -> str:
    return (
        "---\nid: SA-0005\n"
        f"title: {title}\ntype: feature\nrisk: standard\ntouches: ['src/**']\n---\n\n"
        "## Acceptance criteria\n- [ ] it works\n"
    )


def _write_policy(work, marker: str) -> None:
    gates_dir = work / ".saffron" / "gates"
    gates_dir.mkdir(parents=True, exist_ok=True)
    tests_gate = gates_dir / "tests"
    if not tests_gate.exists():
        tests_gate.write_text('#!/bin/sh\necho "{}"\n')
        tests_gate.chmod(0o755)
    (work / ".saffron" / "policy.yaml").write_text(
        f"gates:\n  tests: {{blocking: true}}\nprotected:\n  - {marker}.marker\n"
    )


def _write_spec(work, title: str) -> None:
    specs_dir = work / ".saffron" / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / SPEC_FILENAME).write_text(_spec_text(title))


@dataclass
class Fixture:
    """Every sha a witness needs, named for what the spec's own notes call
    it: the task's own base, the fork point both branches share, the
    packaged commit, the review merge, and each branch after it moved."""

    work: Path
    no_spec_sha: str
    base_sha: str
    spec_sha: str
    fork_sha: str
    packaged_sha: str
    review_sha: str
    main_moved_sha: str
    parent_moved_sha: str
    origin_url: str


def _build_fixture(tmp_path) -> Fixture:
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True)
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "config", "user.name", "T")
    _git(work, "symbolic-ref", "HEAD", "refs/heads/main")

    # A policy with no spec.
    _write_policy(work, "policy-0")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "policy, no spec")
    no_spec_sha = _git(work, "rev-parse", "HEAD")

    # Then the spec.
    _write_spec(work, "v1")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "add spec")

    # Then the task's own base, policy A.
    _write_policy(work, "policy-A")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "policy A, base_sha")
    base_sha = _git(work, "rev-parse", "HEAD")
    spec_sha = hashlib.sha256(
        (work / ".saffron" / "specs" / SPEC_FILENAME).read_bytes()
    ).hexdigest()

    # Policy B, with an edited spec text. The fork point for both branches.
    _write_policy(work, "policy-B")
    _write_spec(work, "v2 edited")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "policy B, edited spec")
    fork_sha = _git(work, "rev-parse", "HEAD")

    _git(work, "branch", "parent")
    _git(work, "checkout", "-q", "-b", "saffron/SA-0005")
    (work / "work.txt").write_text("packaged change\n")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "packaged commit")
    packaged_sha = _git(work, "rev-parse", "HEAD")

    _git(work, "checkout", "-q", "main")
    _write_policy(work, "policy-mainmoved")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "main moved")
    main_moved_sha = _git(work, "rev-parse", "HEAD")

    _git(work, "checkout", "-q", "parent")
    _write_policy(work, "policy-parentmoved")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "parent moved")
    parent_moved_sha = _git(work, "rev-parse", "HEAD")

    _git(work, "checkout", "-q", "saffron/SA-0005")
    _git(work, "merge", "-q", "--no-ff", "-m", "Merge main (update branch)", "main")
    review_sha = _git(work, "rev-parse", "HEAD")

    _git(work, "push", "-q", "origin", "main")
    _git(work, "push", "-q", "origin", "parent")
    _git(work, "push", "-q", "origin", "saffron/SA-0005")

    origin_url = _git(work, "remote", "get-url", "origin")

    return Fixture(
        work=work,
        no_spec_sha=no_spec_sha,
        base_sha=base_sha,
        spec_sha=spec_sha,
        fork_sha=fork_sha,
        packaged_sha=packaged_sha,
        review_sha=review_sha,
        main_moved_sha=main_moved_sha,
        parent_moved_sha=parent_moved_sha,
        origin_url=origin_url,
    )


def _seed_task(
    ledger: Ledger,
    *,
    origin_url: str,
    mirror_path,
    base_sha: str,
    spec_sha: str,
    branch: str,
    pr_url: str | None,
    pushed_sha: str | None = None,
    repo_id: int | None = None,
) -> int:
    if repo_id is None:
        repo_id = ledger.upsert_repo("work", origin_url, str(mirror_path), None)
    run_id = ledger.create_run(repo_id, base_sha)
    task_id = ledger.create_task(run_id, SPEC_ID, spec_sha, branch=branch)
    if pr_url is not None:
        ledger.set_task_package(
            task_id, "READY_FOR_REVIEW", branch, pushed_sha or ("0" * 40), pr_url
        )
    return task_id


def _gh_pr_view(expected_pr_url: str, state: str, base_ref: str, calls: list):
    def _gh(argv: list[str]):
        calls.append(argv)
        payload = json.dumps({"state": state, "baseRefName": base_ref})
        return subprocess.CompletedProcess(argv, 0, payload, "")

    return _gh


def _fake_reverify(calls: list, new_failures=()):
    def _reverify(**kwargs):
        calls.append(kwargs)
        run = SuiteRun(
            results=[], effective_risk="standard", advisory_gates=frozenset()
        )
        return SuiteComparison(run=run, new_failures=tuple(new_failures))

    return _reverify


def _install_probe_fakes(monkeypatch, order: list, *, assert_raises=None):
    def _allocate(name):
        order.append(("allocate", name))
        return "10.200.5.0/24"

    def _remove(name):
        order.append(("remove", name))

    def _ports():
        order.append(("ports",))
        return [2222], ["rapportd"], [("rapportd", 2222)]

    def _addresses(gateway):
        order.append(("addresses", gateway))
        return [gateway, "192.168.1.50"]

    def _assert_unreachable(image_tag, network, *, gateway, ports, sockets):
        order.append(("assert", image_tag, network, gateway))
        if assert_raises is not None:
            raise assert_raises

    monkeypatch.setattr(runtime, "allocate_network", _allocate)
    monkeypatch.setattr(runtime, "remove_network", _remove)
    monkeypatch.setattr(preflight, "host_probe_ports", _ports)
    monkeypatch.setattr(preflight, "probe_addresses", _addresses)
    monkeypatch.setattr(preflight, "assert_host_is_unreachable", _assert_unreachable)


def _assert_green_case(monkeypatch, case_root, capsys, base_ref):
    fixture = _build_fixture(case_root)
    home = case_root / "home"
    work = fixture.work.resolve()
    mirror_path = cli._mirror_path(work, home)
    pr_url = "https://github.com/o/r/pull/9"

    ledger = Ledger(home / "ledger.db")
    task_id = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="saffron/SA-0005",
        pr_url=pr_url,
        pushed_sha=fixture.packaged_sha,
    )
    ledger.close()

    gh_calls: list = []
    monkeypatch.setattr(cli, "run_gh", _gh_pr_view(pr_url, "OPEN", base_ref, gh_calls))

    build_calls: list = []
    monkeypatch.setattr(
        repo_image,
        "build_cell_image",
        lambda repo: build_calls.append(repo) or "fake-image:tag",
    )

    order: list = []
    _install_probe_fakes(monkeypatch, order)

    reverify_calls: list = []
    monkeypatch.setattr(package_phase, "reverify", _fake_reverify(reverify_calls))

    monkeypatch.chdir(work)
    result = cli.main(["--home", str(home), "regate", str(task_id), "--repo", "."])

    assert result == 0
    out = capsys.readouterr().out
    assert (
        "probing 1 host ports at 10.200.5.1, 192.168.1.50; tolerating rapportd" in out
    )

    assert gh_calls == [["gh", "pr", "view", pr_url, "--json", "state,baseRefName"]]
    assert build_calls == [work]

    network = f"saffron-regate-probe-{task_id}"
    assert order[0] == ("remove", network)
    assert order[1] == ("allocate", network)
    assert order[-2][:3] == ("assert", "saffron/cell-base:python", network)
    # Removed again, after the probe and before `reverify` ran.
    assert order[-1] == ("remove", network)
    assert order.count(("remove", network)) == 2

    assert len(reverify_calls) == 1
    call = reverify_calls[0]
    assert call["mirror"] == mirror_path
    assert call["image"] == "fake-image:tag"
    assert call["spec"].id == SPEC_ID
    assert (
        call["gates_dir"] == home / "batches" / "v0" / "regate" / str(task_id) / "gates"
    )
    assert call["policy"].protected == ["policy-A.marker"]
    assert call["packaged_sha"] == fixture.review_sha

    expected_baseline = (
        fixture.main_moved_sha if base_ref == "main" else fixture.fork_sha
    )
    assert call["new_base_sha"] == expected_baseline
    assert f"{fixture.review_sha[:12]} vs {expected_baseline[:12]} green" in out

    ledger = Ledger(home / "ledger.db")
    row = ledger.regate(task_id)
    assert row is not None
    assert row["head_sha"] == fixture.review_sha
    assert row["baseline_sha"] == expected_baseline
    assert row["new_failures"] == 0
    ledger.close()


def test_regate_runs_the_tasks_gates_over_the_pull_requests_head_and_records_green(
    monkeypatch, tmp_path, capsys
):
    # A base of the default branch, then a parent's, each moved after the
    # task's branch forked from it, in its own subdirectory.
    for base_ref in ("main", "parent"):
        case_root = tmp_path / base_ref
        case_root.mkdir()
        _assert_green_case(monkeypatch, case_root, capsys, base_ref)


def test_regate_prints_each_new_failure_records_the_count_and_exits_one(
    monkeypatch, tmp_path, capsys
):
    fixture = _build_fixture(tmp_path)
    home = tmp_path / "home"
    work = fixture.work.resolve()
    mirror_path = cli._mirror_path(work, home)
    pr_url = "https://github.com/o/r/pull/9"

    ledger = Ledger(home / "ledger.db")
    task_id = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="saffron/SA-0005",
        pr_url=pr_url,
        pushed_sha=fixture.packaged_sha,
    )
    ledger.close()

    monkeypatch.setattr(cli, "run_gh", _gh_pr_view(pr_url, "OPEN", "main", []))
    monkeypatch.setattr(repo_image, "build_cell_image", lambda repo: "fake-image:tag")
    _install_probe_fakes(monkeypatch, [])

    failures = (
        NewFailure("tests", Failure(file="a.py", code="E1", message="m1")),
        NewFailure("lint", Failure(file="b.py", code="E2", message="m2")),
    )
    monkeypatch.setattr(
        package_phase, "reverify", _fake_reverify([], new_failures=failures)
    )

    monkeypatch.chdir(work)
    result = cli.main(["--home", str(home), "regate", str(task_id), "--repo", "."])

    assert result == 1
    out = capsys.readouterr().out
    assert "regate: tests E1 a.py" in out
    assert "regate: lint E2 b.py" in out
    assert "2 new failures" in out

    ledger = Ledger(home / "ledger.db")
    row = ledger.regate(task_id)
    assert row is not None
    assert row["new_failures"] == 2
    ledger.close()


def test_regate_prints_the_singular_for_exactly_one_new_failure(
    monkeypatch, tmp_path, capsys
):
    fixture = _build_fixture(tmp_path)
    home = tmp_path / "home"
    work = fixture.work.resolve()
    mirror_path = cli._mirror_path(work, home)
    pr_url = "https://github.com/o/r/pull/9"

    ledger = Ledger(home / "ledger.db")
    task_id = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="saffron/SA-0005",
        pr_url=pr_url,
        pushed_sha=fixture.packaged_sha,
    )
    ledger.close()

    monkeypatch.setattr(cli, "run_gh", _gh_pr_view(pr_url, "OPEN", "main", []))
    monkeypatch.setattr(repo_image, "build_cell_image", lambda repo: "fake-image:tag")
    _install_probe_fakes(monkeypatch, [])

    failures = (NewFailure("tests", Failure(file="a.py", code="E1", message="m1")),)
    monkeypatch.setattr(
        package_phase, "reverify", _fake_reverify([], new_failures=failures)
    )

    monkeypatch.chdir(work)
    result = cli.main(["--home", str(home), "regate", str(task_id), "--repo", "."])

    assert result == 1
    out = capsys.readouterr().out
    assert "1 new failure" in out
    assert "1 new failures" not in out


def test_regate_refuses_each_task_it_cannot_judge_before_any_cell_and_exits_one(
    monkeypatch, tmp_path, capsys
):
    fixture = _build_fixture(tmp_path)
    home = tmp_path / "home"
    work = fixture.work.resolve()
    mirror_path = cli._mirror_path(work, home)

    order: list = []
    build_calls: list = []
    reverify_calls: list = []
    record_calls: list = []
    monkeypatch.setattr(
        repo_image, "build_cell_image", lambda repo: build_calls.append(repo)
    )
    _install_probe_fakes(monkeypatch, order)
    monkeypatch.setattr(package_phase, "reverify", _fake_reverify(reverify_calls))
    monkeypatch.setattr(
        Ledger,
        "record_regate",
        lambda self, *a, **k: record_calls.append((a, k)),
    )

    ledger = Ledger(home / "ledger.db")

    task_no_pr = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="saffron/SA-0005",
        pr_url=None,
    )

    other_repo_id = ledger.upsert_repo(
        "other", "https://example.invalid/other.git", "/nowhere.git", None
    )
    task_foreign_repo = _seed_task(
        ledger,
        origin_url="unused",
        mirror_path="/unused",
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="saffron/SA-0005",
        pr_url="https://github.com/o/r/pull/1",
        repo_id=other_repo_id,
    )

    pr_merged = "https://github.com/o/r/pull/2"
    task_merged = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="saffron/SA-0005",
        pr_url=pr_merged,
        pushed_sha=fixture.packaged_sha,
    )

    pr_closed = "https://github.com/o/r/pull/3"
    task_closed = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="saffron/SA-0005",
        pr_url=pr_closed,
        pushed_sha=fixture.packaged_sha,
    )

    pr_missing_spec = "https://github.com/o/r/pull/4"
    task_missing_spec = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.no_spec_sha,
        spec_sha="z" * 64,
        branch="saffron/SA-0005",
        pr_url=pr_missing_spec,
        pushed_sha=fixture.packaged_sha,
    )

    pr_bad_sha = "https://github.com/o/r/pull/5"
    task_bad_sha = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha="0" * 64,
        branch="saffron/SA-0005",
        pr_url=pr_bad_sha,
        pushed_sha=fixture.packaged_sha,
    )

    pr_recorded_text = "https://github.com/o/r/pull/6"
    task_recorded_text = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="saffron/SA-0005",
        pr_url=pr_recorded_text,
        pushed_sha=fixture.packaged_sha,
    )
    ledger.record_spec_text(
        task_recorded_text,
        origin="revision",
        spec_id=SPEC_ID,
        path=f".saffron/specs/{SPEC_ID}.md",
        text="a revised spec",
    )
    ledger.close()

    unknown_task_id = 999_999

    gh_states = {
        pr_merged: "MERGED",
        pr_closed: "CLOSED",
        pr_missing_spec: "OPEN",
        pr_bad_sha: "OPEN",
    }
    gh_calls: list = []

    def _gh(argv: list[str]):
        gh_calls.append(argv)
        pr_url = argv[3]
        payload = json.dumps(
            {"state": gh_states.get(pr_url, "OPEN"), "baseRefName": "main"}
        )
        return subprocess.CompletedProcess(argv, 0, payload, "")

    monkeypatch.setattr(cli, "run_gh", _gh)
    monkeypatch.chdir(work)

    cases = [
        unknown_task_id,
        task_no_pr,
        task_recorded_text,
        task_foreign_repo,
        task_merged,
        task_closed,
        task_missing_spec,
        task_bad_sha,
    ]
    for task_id in cases:
        result = cli.main(["--home", str(home), "regate", str(task_id), "--repo", "."])
        assert result == 1, task_id
    out = capsys.readouterr().out
    for line in out.splitlines():
        assert line.startswith("regate: "), line

    assert build_calls == []
    assert order == []
    assert reverify_calls == []
    assert record_calls == []


def test_regate_exits_two_on_infrastructure_and_records_nothing(monkeypatch, tmp_path):
    fixture = _build_fixture(tmp_path)
    home = tmp_path / "home"
    work = fixture.work.resolve()
    mirror_path = cli._mirror_path(work, home)
    pr_url = "https://github.com/o/r/pull/9"

    def _seed():
        ledger = Ledger(home / "ledger.db")
        task_id = _seed_task(
            ledger,
            origin_url=fixture.origin_url,
            mirror_path=mirror_path,
            base_sha=fixture.base_sha,
            spec_sha=fixture.spec_sha,
            branch="saffron/SA-0005",
            pr_url=pr_url,
            pushed_sha=fixture.packaged_sha,
        )
        ledger.close()
        return task_id

    record_calls: list = []
    monkeypatch.setattr(
        Ledger,
        "record_regate",
        lambda self, *a, **k: record_calls.append((a, k)),
    )
    monkeypatch.setattr(repo_image, "build_cell_image", lambda repo: "fake-image:tag")
    monkeypatch.chdir(work)

    # A `gh pr view` that exits non-zero.
    monkeypatch.setattr(
        cli,
        "run_gh",
        lambda argv: subprocess.CompletedProcess(argv, 1, "", "gh is unauthenticated"),
    )
    task_id = _seed()
    assert cli.main(["--home", str(home), "regate", str(task_id), "--repo", "."]) == 2

    # A `PreflightFailed` from the probe. The probe's network is removed,
    # and `reverify` is never reached.
    monkeypatch.setattr(cli, "run_gh", _gh_pr_view(pr_url, "OPEN", "main", []))
    order: list = []
    _install_probe_fakes(
        monkeypatch, order, assert_raises=preflight.PreflightFailed("unreachable")
    )
    reverify_calls: list = []
    monkeypatch.setattr(package_phase, "reverify", _fake_reverify(reverify_calls))
    task_id = _seed()
    assert cli.main(["--home", str(home), "regate", str(task_id), "--repo", "."]) == 2
    network = f"saffron-regate-probe-{task_id}"
    assert order[-1] == ("remove", network)
    assert reverify_calls == []

    # A `PackageError` from `reverify`.
    _install_probe_fakes(monkeypatch, [])

    def _raising_reverify(**kwargs):
        raise package_phase.PackageError("the suite drifted")

    monkeypatch.setattr(package_phase, "reverify", _raising_reverify)
    task_id = _seed()
    assert cli.main(["--home", str(home), "regate", str(task_id), "--repo", "."]) == 2

    assert record_calls == []


def test_regate_stopped_by_sigterm_exits_143(monkeypatch, tmp_path):
    fixture = _build_fixture(tmp_path)
    home = tmp_path / "home"
    work = fixture.work.resolve()
    mirror_path = cli._mirror_path(work, home)
    pr_url = "https://github.com/o/r/pull/9"

    ledger = Ledger(home / "ledger.db")
    task_id = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="saffron/SA-0005",
        pr_url=pr_url,
        pushed_sha=fixture.packaged_sha,
    )
    ledger.close()

    monkeypatch.setattr(cli, "run_gh", _gh_pr_view(pr_url, "OPEN", "main", []))
    monkeypatch.setattr(repo_image, "build_cell_image", lambda repo: "fake-image:tag")
    _install_probe_fakes(monkeypatch, [])

    def _sigterm_reverify(**kwargs):
        os.kill(os.getpid(), signal.SIGTERM)
        raise AssertionError("SIGTERM did not interrupt reverify")

    monkeypatch.setattr(package_phase, "reverify", _sigterm_reverify)

    heard: list[int] = []

    def _record(signum: int, _frame: object) -> None:
        heard.append(signum)

    outer_previous = signal.signal(signal.SIGTERM, _record)
    try:
        monkeypatch.chdir(work)
        try:
            result = cli.main(
                ["--home", str(home), "regate", str(task_id), "--repo", "."]
            )
        except BaseException as exc:  # a leak fails this one call, not the test
            result = exc
        restored = signal.getsignal(signal.SIGTERM)
    finally:
        signal.signal(signal.SIGTERM, outer_previous)

    assert result == 143
    assert heard == []
    assert restored == _record
