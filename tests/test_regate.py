"""`saffron regate <task id> --repo .` (backlog item 97).

Every witness drives a real git fixture: a bare origin and a checkout. The
checkout commits a base, forks a parent branch and a packaged commit, then
adds a review commit. That commit merges a moved default branch into the
task's branch, the way GitHub's "update branch" does. `reverify`, the probe
and `gh` are faked. The mirror, the fetches and the merge base stay real git.
`review_commit_diff`'s own witnesses build only a checkout, with no bare
origin, ledger or `gh` fake, since the function reads a plain mirror
directly.
"""

from __future__ import annotations

import contextlib
import errno
import hashlib
import json
import os
import re
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from saffron import cli, preflight
from saffron.cell import runtime
from saffron.cell.worktree import DIFF_FLAGS, GATES_MOUNT
from saffron.gates.baseline import NewFailure
from saffron.gates.contract import Failure, GateResult, GateStatus
from saffron.gates.core.revert import revert_gate
from saffron.gates.suite import SuiteComparison, SuiteRun
from saffron.ledger import Ledger
from saffron.phases import package as package_phase
from saffron.record.routed import RoutedRecord
from saffron.repos import image as repo_image
from saffron.repos import mirror as git_mirror

SPEC_ID = "SA-0005"
SPEC_FILENAME = f"{SPEC_ID}-regate-test.md"


@pytest.fixture(autouse=True)
def _no_token_and_no_agent(monkeypatch):
    """Every witness runs with no token and with each agent path raising, so
    a `regate` that reads one fails whatever the operator's shell holds."""
    from saffron import task
    from saffron.phases import implement

    def _reached(*_args, **_kwargs):
        raise AssertionError("regate reached an agent path")

    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.setattr(task, "run_one_cell", _reached)
    monkeypatch.setattr(implement, "run_agent", _reached)


def _git(repo, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _spec_text(
    title: str, witness: str | None = None, mutant: dict | None = None
) -> str:
    """With no `witness`, the plain free-text criterion every other witness
    reads. With one, a single `acceptance:` criterion declaring it, plus
    an inline `mutant` where given (`b-c5da95`)."""
    if witness is None:
        return (
            "---\nid: SA-0005\n"
            f"title: {title}\ntype: feature\nrisk: standard\ntouches: ['src/**']\n---\n\n"
            "## Acceptance criteria\n- [ ] it works\n"
        )
    lines = [
        "---",
        "id: SA-0005",
        f"title: {title}",
        "type: feature",
        "risk: standard",
        "touches: ['src/**']",
        "acceptance:",
        "  - claim: it works",
        f"    witness: {witness}",
    ]
    if mutant is not None:
        lines += [
            "    mutant:",
            f"      file: {mutant['file']}",
            f"      find: {mutant['find']}",
            f"      replace: {mutant.get('replace', 'replaced')}",
        ]
    lines += ["---", ""]
    return "\n".join(lines)


def _write_policy(work, marker: str) -> None:
    gates_dir = work / ".saffron" / "gates"
    gates_dir.mkdir(parents=True, exist_ok=True)
    tests_gate = gates_dir / "tests"
    if not tests_gate.exists():
        tests_gate.write_text('#!/bin/sh\necho "{}"\n')
        tests_gate.chmod(0o755)
    (work / ".saffron" / "policy.yaml").write_text(
        f"gates:\n  tests: {{blocking: true}}\nprotected:\n  - {marker}.marker\n"
        "integrity:\n  test_paths: ['tests/**']\n"
    )


def _write_spec(
    work, title: str, witness: str | None = None, mutant: dict | None = None
) -> None:
    specs_dir = work / ".saffron" / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / SPEC_FILENAME).write_text(_spec_text(title, witness, mutant))


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


def _build_fixture(
    tmp_path, witness: str | None = None, mutant: dict | None = None
) -> Fixture:
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
    _write_spec(work, "v1", witness, mutant)
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
    _write_spec(work, "v2 edited", witness, mutant)
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
    mutants_commit: str | None = None,
) -> int:
    if repo_id is None:
        repo_id = ledger.upsert_repo("work", origin_url, str(mirror_path), None)
    run_id = ledger.create_run(repo_id, base_sha)
    task_id = ledger.create_task(
        run_id, SPEC_ID, spec_sha, branch=branch, mutants_commit=mutants_commit
    )
    if pr_url is not None:
        ledger.set_task_package(
            task_id, "READY_FOR_REVIEW", branch, pushed_sha or ("0" * 40), pr_url
        )
    return task_id


def _hash_object(work: Path, text: str) -> str:
    return subprocess.run(
        ["git", "-C", str(work), "hash-object", "-w", "--stdin"],
        input=text,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _ls_tree(work: Path, commit: str) -> dict[str, str]:
    out = subprocess.run(
        ["git", "-C", str(work), "ls-tree", commit],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    entries: dict[str, str] = {}
    for line in out.splitlines():
        if not line:
            continue
        meta, name = line.split("\t", 1)
        entries[name] = meta.split()[2]
    return entries


def _mktree(work: Path, entries: dict[str, str]) -> str:
    stdin = "".join(
        f"100644 blob {sha}\t{name}\n" for name, sha in sorted(entries.items())
    )
    return subprocess.run(
        ["git", "-C", str(work), "mktree"],
        input=stdin,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _mutants_commit(
    work: Path, *, parent: str | None = None, spec_id: str, yaml_text: str
) -> str:
    """One commit on top of `parent` (or a root commit with none), replacing
    `<spec_id>.yaml` with `yaml_text`. Never through `write_mutants`: that
    writer touches a real remote this fixture has no reason to grow."""
    entries = _ls_tree(work, parent) if parent else {}
    entries[f"{spec_id}.yaml"] = _hash_object(work, yaml_text)
    tree = _mktree(work, entries)
    args = ["git", "-C", str(work), "commit-tree", tree, "-m", f"mutant {spec_id}"]
    if parent:
        args += ["-p", parent]
    return subprocess.run(
        args, capture_output=True, text=True, check=True
    ).stdout.strip()


def _mutants_yaml(
    witness: str, *, file: str, find: str, replace: str = "replaced"
) -> str:
    return f"{witness}:\n  file: {file}\n  find: {find}\n  replace: {replace}\n"


def _set_mutants_ref(work: Path, commit: str) -> None:
    """Moves `refs/saffron/mutants` to `commit` and pushes it. A fresh
    mirror then clones every ancestor on `commit`'s own chain, never a
    dangling root the ref does not reach (measured)."""
    _git(work, "update-ref", "refs/saffron/mutants", commit)
    _git(work, "push", "-q", "origin", "refs/saffron/mutants:refs/saffron/mutants")


def _seeding_ledger(path: Path, origin_url: str) -> Ledger:
    """A `Ledger` that routes its own writes straight onto the fixture's
    bare origin, standing in for the mirror `regate` has not cloned yet
    (item 170): the production `RoutedRecord` the command builds over its
    own fresh mirror then finds the task's ref already there to recover."""
    return Ledger(
        path, record=RoutedRecord(lambda _key: (Path(origin_url), origin_url))
    )


def _gh_pr_view(expected_pr_url: str, state: str, base_ref: str, calls: list):
    def _gh(argv: list[str]):
        calls.append(argv)
        payload = json.dumps({"state": state, "baseRefName": base_ref})
        return subprocess.CompletedProcess(argv, 0, payload, "")

    return _gh


def _fake_reverify(
    calls: list, new_failures=(), tests_collected: list[str] | None = None
):
    """A `reverify` stand-in. With `tests_collected` given, the comparison's
    own suite carries one green `tests` `GateResult` enumerating exactly
    those node ids, for `_apply_criterion_probes`'s own `collected` check
    (`b-d9a027`). Left `None`, the suite carries no results at all, exactly
    as every witness predating that wiring expects."""

    def _reverify(**kwargs):
        calls.append(kwargs)
        results = (
            []
            if tests_collected is None
            else [
                GateResult(
                    gate="tests",
                    status="pass",
                    tool="pytest 1",
                    collected=tests_collected,
                )
            ]
        )
        run = SuiteRun(
            results=results, effective_risk="standard", advisory_gates=frozenset()
        )
        return SuiteComparison(run=run, new_failures=tuple(new_failures))

    return _reverify


def _fake_reverify_through_revert_gate(calls: list):
    """A `reverify` stand-in. It runs the real `revert_gate` over
    `kwargs["spec"].acceptance`, against `work.txt` as the diff's only
    source change. A criterion whose mutant names `work.txt` stays judged,
    and one naming `src/elsewhere.py` is set aside (b-c5da95)."""

    def _reverify(**kwargs):
        calls.append(kwargs)
        acceptance = kwargs["spec"].acceptance
        witnesses = [c.witness for c in acceptance]
        prior = [GateResult(gate="tests", status="pass", tool="pytest 1", collected=[])]
        results = [
            GateResult(
                gate="tests", status="pass", tool="pytest 1", collected=witnesses
            )
        ]

        def _run_tests(subset: list[str]) -> GateResult:
            return GateResult(
                gate="tests",
                status="pass",
                tool="pytest 1",
                collected=subset,
                failures=[],
            )

        result = revert_gate(
            prior=prior,
            results=results,
            acceptance=acceptance,
            changed_files=["work.txt"],
            test_paths=["tests/**"],
            dirty=lambda: [],
            reverted=lambda _source: contextlib.nullcontext(),
            run_tests=_run_tests,
            exempt=(),
            diff="",
        )
        new_failures = tuple(NewFailure("revert", f) for f in result.failures)
        run = SuiteRun(
            results=[result], effective_risk="standard", advisory_gates=frozenset()
        )
        return SuiteComparison(run=run, new_failures=new_failures)

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

    ledger = _seeding_ledger(home / "ledger.db", fixture.origin_url)
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
    fake_reverify = _fake_reverify(reverify_calls)

    def _ordered_reverify(**kwargs):
        order.append(("reverify",))
        return fake_reverify(**kwargs)

    monkeypatch.setattr(package_phase, "reverify", _ordered_reverify)

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
    assert order[-3][:3] == ("assert", "saffron/cell-base:python", network)
    # Removed again, after the probe and before `reverify` ran.
    assert order[-2] == ("remove", network)
    assert order[-1] == ("reverify",)
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

    ledger = _seeding_ledger(home / "ledger.db", fixture.origin_url)
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

    ledger = _seeding_ledger(home / "ledger.db", fixture.origin_url)
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


def _seed_green_regate(tmp_path):
    """A fixture and a seeded, judgeable task."""
    fixture = _build_fixture(tmp_path)
    home = tmp_path / "home"
    work = fixture.work.resolve()
    mirror_path = cli._mirror_path(work, home)
    pr_url = "https://github.com/o/r/pull/9"

    ledger = _seeding_ledger(home / "ledger.db", fixture.origin_url)
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
    return fixture, home, work, task_id


def test_regate_passes_reverify_the_exemption_its_task_directory_holds(
    monkeypatch, tmp_path
):
    """`run_regate` hands `reverify` an `exempt` built from
    `package_phase.read_revert_exempt(out_dir / row["spec_id"])`: `[]` with
    no task directory, a current file's own list even with no
    `baseline.json` there, and `[]` again for a file older than it.
    Replacing the reader has its own answer reach the call, over that same
    directory."""
    _fixture, home, work, task_id = _seed_green_regate(tmp_path)
    task_dir = home / "batches" / "v0" / SPEC_ID

    def _regate() -> dict:
        monkeypatch.setattr(
            cli, "run_gh", _gh_pr_view("https://x/pull/9", "OPEN", "main", [])
        )
        monkeypatch.setattr(
            repo_image, "build_cell_image", lambda repo: "fake-image:tag"
        )
        _install_probe_fakes(monkeypatch, [])
        reverify_calls: list = []
        monkeypatch.setattr(package_phase, "reverify", _fake_reverify(reverify_calls))
        monkeypatch.chdir(work)
        result = cli.main(["--home", str(home), "regate", str(task_id), "--repo", "."])
        assert result == 0
        return reverify_calls[-1]

    # No task directory at all.
    assert not task_dir.exists()
    assert _regate()["exempt"] == []

    # A current file with no `baseline.json` at all: current regardless.
    # `exist_ok=True`: the `RecordAppend` sink wrote this directory already.
    task_dir.mkdir(parents=True, exist_ok=True)
    assert _regate()["exempt"] == []
    exempt_path = task_dir / "revert-exempt.json"
    exempt_path.write_text(json.dumps(["t/test_a.py::test_one"]))
    assert _regate()["exempt"] == ["t/test_a.py::test_one"]

    # A current file once `baseline.json` exists too.
    baseline_path = task_dir / "baseline.json"
    baseline_path.write_text("{}")
    os.utime(baseline_path, (2_000_000.0, 2_000_000.0))
    os.utime(exempt_path, (2_000_000.0 + 1.0, 2_000_000.0 + 1.0))
    assert _regate()["exempt"] == ["t/test_a.py::test_one"]

    # Older than `baseline.json`: another cell's, read as no exemption.
    os.utime(exempt_path, (2_000_000.0 - 1.0, 2_000_000.0 - 1.0))
    assert _regate()["exempt"] == []

    # Replacing the reader has its own answer reach the call, over the
    # task directory under `out_dir`, not `out_dir` itself.
    calls: list[Path] = []

    def _fake_reader(given: Path) -> list[str]:
        calls.append(given)
        return ["replaced::node"]

    monkeypatch.setattr(package_phase, "read_revert_exempt", _fake_reader)
    assert _regate()["exempt"] == ["replaced::node"]
    assert calls == [task_dir]


def test_regate_declines_an_exemption_it_cannot_read(monkeypatch, tmp_path, capsys):
    """`run_regate` prints one `regate:` line naming the file and returns 1
    when the reader raises `RevertExemptUnreadable`. That covers invalid
    JSON, the wrong JSON shape, and a directory at the path, each before
    any image build, `reverify` call or recorded re-gate. A host failure
    reading the file is no decline: `cli.main` exits 2 on it, with no
    `regate:` line, and nothing else runs either."""
    _fixture, home, work, task_id = _seed_green_regate(tmp_path)
    task_dir = home / "batches" / "v0" / SPEC_ID
    task_dir.mkdir(parents=True)
    exempt_path = task_dir / "revert-exempt.json"

    def _prepare() -> tuple[list, list]:
        monkeypatch.setattr(
            cli, "run_gh", _gh_pr_view("https://x/pull/9", "OPEN", "main", [])
        )
        build_calls: list = []
        monkeypatch.setattr(
            repo_image,
            "build_cell_image",
            lambda repo: build_calls.append(repo) or "fake-image:tag",
        )
        _install_probe_fakes(monkeypatch, [])
        reverify_calls: list = []
        monkeypatch.setattr(package_phase, "reverify", _fake_reverify(reverify_calls))
        monkeypatch.chdir(work)
        return build_calls, reverify_calls

    for payload, as_dir in (
        ("not json", False),
        ("{}", False),
        (json.dumps(["t.py::a", 3]), False),
        (None, True),
    ):
        if as_dir:
            exempt_path.mkdir()
        else:
            exempt_path.write_text(payload)
        with pytest.raises(package_phase.RevertExemptUnreadable) as info:
            package_phase.read_revert_exempt(task_dir)
        expected_line = f"regate: {info.value}"
        build_calls, reverify_calls = _prepare()
        result = cli.main(["--home", str(home), "regate", str(task_id), "--repo", "."])
        out = capsys.readouterr().out
        assert result == 1
        assert out.count("regate:") == 1
        # The whole exception text, not a path substring: a fixed sentence
        # naming only the file would pass a looser check but fails this one.
        assert expected_line in out
        assert build_calls == []
        assert reverify_calls == []
        ledger = Ledger(home / "ledger.db")
        assert ledger.regate(task_id) is None
        ledger.close()
        if as_dir:
            exempt_path.rmdir()
        else:
            exempt_path.unlink()

    # A replaced reader's own text reaches the line, unrebuilt.
    def _own_text(_task_dir: Path) -> list[str]:
        raise package_phase.RevertExemptUnreadable("the reader's own text")

    monkeypatch.setattr(package_phase, "read_revert_exempt", _own_text)
    build_calls, reverify_calls = _prepare()
    result = cli.main(["--home", str(home), "regate", str(task_id), "--repo", "."])
    out = capsys.readouterr().out
    assert result == 1
    assert "regate: the reader's own text" in out
    assert build_calls == []
    assert reverify_calls == []

    # A host failure is no decline: `cli.main`'s own catch-all exits 2, and
    # prints no `regate:` line.
    exempt_path.write_text("[]")
    for fault in (PermissionError("denied"), OSError(errno.EIO, "io error")):

        def _raising(_task_dir: Path, fault=fault) -> list[str]:
            raise fault

        monkeypatch.setattr(package_phase, "read_revert_exempt", _raising)
        build_calls, reverify_calls = _prepare()
        result = cli.main(["--home", str(home), "regate", str(task_id), "--repo", "."])
        out = capsys.readouterr().out
        assert result == 2
        assert "regate:" not in out
        assert f"saffron: {type(fault).__name__}: {fault}" in out
        assert build_calls == []
        assert reverify_calls == []
        ledger = Ledger(home / "ledger.db")
        assert ledger.regate(task_id) is None
        ledger.close()


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
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == len(cases), lines
    for line in lines:
        assert line.startswith("regate: "), line
    reasons = [
        f"task {unknown_task_id} names no task",
        f"task {task_no_pr} carries no pull request",
        f"task {task_recorded_text}'s text 1 does not parse",
        f"task {task_foreign_repo} belongs to another repo",
        f"{pr_merged} is MERGED, not OPEN",
        f"{pr_closed} is CLOSED, not OPEN",
        f"no spec file for {SPEC_ID}",
        "does not hash to task's recorded spec_sha",
    ]
    for line, reason in zip(lines, reasons, strict=True):
        assert reason in line, (reason, line)

    assert build_calls == []
    assert order == []
    assert reverify_calls == []
    assert record_calls == []


def test_regate_exits_two_on_infrastructure_and_records_nothing(
    monkeypatch, tmp_path, capsys
):
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

    # A task branch the origin no longer carries names itself, not a parent.
    ledger = Ledger(home / "ledger.db")
    task_id = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="saffron/SA-0005-deleted",
        pr_url=pr_url,
        pushed_sha=fixture.packaged_sha,
    )
    ledger.close()
    capsys.readouterr()
    assert cli.main(["--home", str(home), "regate", str(task_id), "--repo", "."]) == 2
    printed = capsys.readouterr().out
    assert "task branch saffron/SA-0005-deleted could not be fetched" in printed
    assert "parent" not in printed

    assert record_calls == []


def test_regate_judges_a_witness_its_cells_revert_set_aside_and_finds_no_new_failure(
    monkeypatch, tmp_path, capsys
):
    """`saffron regate` attaches the mutants the task's own row pins
    (`b-c5da95`). A row pinning a commit whose mutant names a file outside
    the diff regates green, through `revert` setting that witness aside.
    This holds even once the ref moves to a commit whose mutant names the
    diff's own file. A row pinning no commit attaches none, so the same
    witness stays judged and `revert` reports it as theater. A spec at base
    declaring the witness's mutant inline keeps it, and regates green,
    though its row pins the commit naming `work.txt`."""
    witness = "tests/test_elsewhere.py::test_guard"
    fixture = _build_fixture(tmp_path, witness=witness)
    home = tmp_path / "home"
    work = fixture.work.resolve()
    mirror_path = cli._mirror_path(work, home)

    outside_sha = _mutants_commit(
        work,
        parent=None,
        spec_id=SPEC_ID,
        yaml_text=_mutants_yaml(
            witness, file="src/elsewhere.py", find="outside-diff-marker"
        ),
    )
    inside_sha = _mutants_commit(
        work,
        parent=outside_sha,
        spec_id=SPEC_ID,
        yaml_text=_mutants_yaml(witness, file="work.txt", find="work-diff-marker"),
    )
    _set_mutants_ref(work, inside_sha)

    def _prepare(pr_url: str) -> list:
        monkeypatch.setattr(cli, "run_gh", _gh_pr_view(pr_url, "OPEN", "main", []))
        monkeypatch.setattr(
            repo_image, "build_cell_image", lambda repo: "fake-image:tag"
        )
        _install_probe_fakes(monkeypatch, [])
        reverify_calls: list = []
        monkeypatch.setattr(
            package_phase,
            "reverify",
            _fake_reverify_through_revert_gate(reverify_calls),
        )
        return reverify_calls

    # Pinned to the commit whose mutant lies outside the diff: green, though
    # the ref itself has since moved to `inside_sha`.
    pr_url = "https://github.com/o/r/pull/9"
    ledger = _seeding_ledger(home / "ledger.db", fixture.origin_url)
    task_outside = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="saffron/SA-0005",
        pr_url=pr_url,
        pushed_sha=fixture.packaged_sha,
        mutants_commit=outside_sha,
    )
    ledger.close()

    monkeypatch.chdir(work)
    reverify_calls = _prepare(pr_url)
    result = cli.main(["--home", str(home), "regate", str(task_outside), "--repo", "."])
    out = capsys.readouterr().out
    assert result == 0
    assert "new failure" not in out
    assert len(reverify_calls) == 1
    assert reverify_calls[0]["spec"].acceptance[0].mutant.file == "src/elsewhere.py"

    ledger = Ledger(home / "ledger.db")
    row = ledger.regate(task_outside)
    assert row is not None
    assert row["new_failures"] == 0
    ledger.close()

    # No commit pinned at all: nothing is attached, so the witness stays
    # judged and `revert` reports it as theater.
    pr_url_none = "https://github.com/o/r/pull/10"
    ledger = _seeding_ledger(home / "ledger.db", fixture.origin_url)
    task_none = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="saffron/SA-0005",
        pr_url=pr_url_none,
        pushed_sha=fixture.packaged_sha,
    )
    ledger.close()

    reverify_calls = _prepare(pr_url_none)
    result = cli.main(["--home", str(home), "regate", str(task_none), "--repo", "."])
    out = capsys.readouterr().out
    assert result == 1
    assert f"regate: revert passed-without-source {witness}" in out
    assert "1 new failure" in out
    assert reverify_calls[0]["spec"].acceptance[0].mutant is None

    ledger = Ledger(home / "ledger.db")
    row = ledger.regate(task_none)
    assert row is not None
    assert row["new_failures"] == 1
    ledger.close()

    # An inline mutant outside the diff, kept over a row pinning
    # `work.txt`'s commit. Its own subdirectory, so files never collide.
    inline_root = tmp_path / "inline"
    inline_root.mkdir()
    inline_fixture = _build_fixture(
        inline_root,
        witness=witness,
        mutant={"file": "src/elsewhere.py", "find": "inline-marker"},
    )
    inline_home = inline_root / "home"
    inline_work = inline_fixture.work.resolve()
    inline_mirror_path = cli._mirror_path(inline_work, inline_home)

    pinned_sha = _mutants_commit(
        inline_work,
        parent=None,
        spec_id=SPEC_ID,
        yaml_text=_mutants_yaml(witness, file="work.txt", find="work-diff-marker"),
    )
    _set_mutants_ref(inline_work, pinned_sha)

    pr_url_inline = "https://github.com/o/r/pull/11"
    ledger = _seeding_ledger(inline_home / "ledger.db", inline_fixture.origin_url)
    task_inline = _seed_task(
        ledger,
        origin_url=inline_fixture.origin_url,
        mirror_path=inline_mirror_path,
        base_sha=inline_fixture.base_sha,
        spec_sha=inline_fixture.spec_sha,
        branch="saffron/SA-0005",
        pr_url=pr_url_inline,
        pushed_sha=inline_fixture.packaged_sha,
        mutants_commit=pinned_sha,
    )
    ledger.close()

    monkeypatch.setattr(cli, "run_gh", _gh_pr_view(pr_url_inline, "OPEN", "main", []))
    monkeypatch.setattr(repo_image, "build_cell_image", lambda repo: "fake-image:tag")
    _install_probe_fakes(monkeypatch, [])
    reverify_calls = []
    monkeypatch.setattr(
        package_phase, "reverify", _fake_reverify_through_revert_gate(reverify_calls)
    )

    monkeypatch.chdir(inline_work)
    result = cli.main(
        ["--home", str(inline_home), "regate", str(task_inline), "--repo", "."]
    )
    out = capsys.readouterr().out
    assert result == 0
    assert "new failure" not in out
    assert reverify_calls[0]["spec"].acceptance[0].mutant.file == "src/elsewhere.py"

    ledger = Ledger(inline_home / "ledger.db")
    row = ledger.regate(task_inline)
    assert row is not None
    assert row["new_failures"] == 0
    ledger.close()


def test_regate_declines_a_mutants_commit_it_cannot_read_before_any_cell(
    monkeypatch, tmp_path, capsys
):
    """`saffron regate` declines a task whose pinned mutants commit it
    cannot read, for a spec declaring no mutant inline, before the image or
    any cell: a commit the mirror lacks, and one whose `<spec id>.yaml`
    does not parse. A readable pinned commit regated first in the same
    witness builds the image and reaches `reverify` (`b-c5da95`)."""
    witness = "tests/test_elsewhere.py::test_guard"
    fixture = _build_fixture(tmp_path, witness=witness)
    home = tmp_path / "home"
    work = fixture.work.resolve()
    mirror_path = cli._mirror_path(work, home)

    readable_sha = _mutants_commit(
        work,
        parent=None,
        spec_id=SPEC_ID,
        yaml_text=_mutants_yaml(
            witness, file="src/elsewhere.py", find="outside-diff-marker"
        ),
    )
    unparseable_sha = _mutants_commit(
        work, parent=readable_sha, spec_id=SPEC_ID, yaml_text="not a mapping at all\n"
    )
    syntax_sha = _mutants_commit(
        work, parent=unparseable_sha, spec_id=SPEC_ID, yaml_text="key: [\n"
    )
    _set_mutants_ref(work, syntax_sha)

    def _prepare(pr_url: str) -> tuple[list, list]:
        monkeypatch.setattr(cli, "run_gh", _gh_pr_view(pr_url, "OPEN", "main", []))
        build_calls: list = []
        monkeypatch.setattr(
            repo_image,
            "build_cell_image",
            lambda repo: build_calls.append(repo) or "fake-image:tag",
        )
        _install_probe_fakes(monkeypatch, [])
        reverify_calls: list = []
        monkeypatch.setattr(
            package_phase,
            "reverify",
            _fake_reverify_through_revert_gate(reverify_calls),
        )
        return build_calls, reverify_calls

    monkeypatch.chdir(work)

    # The readable commit, regated first: builds the image and reaches
    # `reverify`.
    pr_readable = "https://github.com/o/r/pull/9"
    ledger = _seeding_ledger(home / "ledger.db", fixture.origin_url)
    task_readable = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="saffron/SA-0005",
        pr_url=pr_readable,
        pushed_sha=fixture.packaged_sha,
        mutants_commit=readable_sha,
    )
    ledger.close()

    build_calls, reverify_calls = _prepare(pr_readable)
    result = cli.main(
        ["--home", str(home), "regate", str(task_readable), "--repo", "."]
    )
    capsys.readouterr()
    assert result == 0
    assert build_calls == [work]
    assert len(reverify_calls) == 1

    # A commit the mirror lacks.
    missing_sha = "f" * 40
    pr_missing = "https://github.com/o/r/pull/10"
    ledger = _seeding_ledger(home / "ledger.db", fixture.origin_url)
    task_missing = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="saffron/SA-0005",
        pr_url=pr_missing,
        pushed_sha=fixture.packaged_sha,
        mutants_commit=missing_sha,
    )
    ledger.close()

    build_calls, reverify_calls = _prepare(pr_missing)
    result = cli.main(["--home", str(home), "regate", str(task_missing), "--repo", "."])
    out = capsys.readouterr().out
    assert result == 1
    assert out.count("regate:") == 1
    assert f"regate: mutants commit {missing_sha[:12]} is not in the mirror" in out
    assert build_calls == []
    assert reverify_calls == []
    ledger = Ledger(home / "ledger.db")
    assert ledger.regate(task_missing) is None
    ledger.close()

    # A commit whose `<spec id>.yaml` does not parse.
    pr_unparseable = "https://github.com/o/r/pull/11"
    ledger = _seeding_ledger(home / "ledger.db", fixture.origin_url)
    task_unparseable = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="saffron/SA-0005",
        pr_url=pr_unparseable,
        pushed_sha=fixture.packaged_sha,
        mutants_commit=unparseable_sha,
    )
    ledger.close()

    build_calls, reverify_calls = _prepare(pr_unparseable)
    result = cli.main(
        ["--home", str(home), "regate", str(task_unparseable), "--repo", "."]
    )
    out = capsys.readouterr().out
    assert result == 1
    assert out.count("regate:") == 1
    assert out.startswith(f"regate: {SPEC_ID}.yaml")
    assert build_calls == []
    assert reverify_calls == []
    ledger = Ledger(home / "ledger.db")
    assert ledger.regate(task_unparseable) is None
    ledger.close()

    # A YAML syntax error, whose parser message spans several lines.
    pr_syntax = "https://github.com/o/r/pull/12"
    ledger = _seeding_ledger(home / "ledger.db", fixture.origin_url)
    task_syntax = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="saffron/SA-0005",
        pr_url=pr_syntax,
        pushed_sha=fixture.packaged_sha,
        mutants_commit=syntax_sha,
    )
    ledger.close()

    build_calls, reverify_calls = _prepare(pr_syntax)
    result = cli.main(["--home", str(home), "regate", str(task_syntax), "--repo", "."])
    out = capsys.readouterr().out
    assert result == 1
    assert out.startswith(f"regate: {SPEC_ID}.yaml is not valid YAML")
    assert out.count("\n") == 1
    assert build_calls == []
    assert reverify_calls == []


def test_adopt_moves_a_task_whose_witness_its_cell_set_aside_to_ready_for_review(
    monkeypatch, tmp_path, capsys
):
    """`saffron adopt` moves an `EXHAUSTED` task to `READY_FOR_REVIEW` when
    its row pins a mutants commit whose mutant sets the witness aside. Its
    own regate, through `regate.run_regate` with no fake, records no new
    failure on the adopted head (`b-c5da95`)."""
    witness = "tests/test_elsewhere.py::test_guard"
    fixture = _build_fixture(tmp_path, witness=witness)
    home = tmp_path / "home"
    work = fixture.work.resolve()
    mirror_path = cli._mirror_path(work, home)

    mutants_sha = _mutants_commit(
        work,
        parent=None,
        spec_id=SPEC_ID,
        yaml_text=_mutants_yaml(
            witness, file="src/elsewhere.py", find="outside-diff-marker"
        ),
    )
    _set_mutants_ref(work, mutants_sha)

    ledger = _seeding_ledger(home / "ledger.db", fixture.origin_url)
    task_id = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="saffron/SA-0005",
        pr_url=None,
        mutants_commit=mutants_sha,
    )
    ledger.set_task_package(
        task_id, "EXHAUSTED", branch="saffron/SA-0005", pushed_sha="", pr_url=""
    )
    repo_id = ledger.resolve_repo_id(fixture.origin_url)
    assert repo_id is not None
    ledger.close()

    # Adopt writes its own facts before the regate clones the mirror: create
    # it first, or the prototype's own `RecordError` recurs (item 170).
    git_mirror.ensure_mirror(work, mirror_path)

    pr_url = "https://github.com/o/r/pull/9"

    def _gh(argv: list[str]):
        if argv[2] == "view" and len(argv) > 4 and argv[4] == "--repo":
            payload = json.dumps(
                {
                    "url": pr_url,
                    "headRefOid": fixture.review_sha,
                    "headRefName": "saffron/SA-0005",
                }
            )
            return subprocess.CompletedProcess(argv, 0, payload, "")
        payload = json.dumps({"state": "OPEN", "baseRefName": "main"})
        return subprocess.CompletedProcess(argv, 0, payload, "")

    monkeypatch.setattr(cli, "run_gh", _gh)
    monkeypatch.setattr(package_phase, "github_slug", lambda _url: "o/r")
    monkeypatch.setattr(repo_image, "build_cell_image", lambda repo: "fake-image:tag")
    _install_probe_fakes(monkeypatch, [])
    monkeypatch.setattr(
        package_phase, "reverify", _fake_reverify_through_revert_gate([])
    )

    monkeypatch.chdir(work)
    result = cli.main(["--home", str(home), "adopt", SPEC_ID, "9", "--repo", "."])
    assert result == 0, capsys.readouterr().out

    ledger = Ledger(home / "ledger.db")
    row = next(r for r in ledger.tasks_by_repo(repo_id) if r["task_id"] == task_id)
    assert row["state"] == "READY_FOR_REVIEW"
    ledger.close()


def test_regate_judges_a_task_that_ran_a_recorded_spec_text_against_its_latest_row(
    monkeypatch, tmp_path, capsys
):
    """`saffron regate` reads `ledger.spec_text(task_id)` before falling back
    to `_spec_at_base`, and judges the task against its latest row. A
    `follow_up` task's rows share one origin. A `draft` task's rows mix
    `draft` then `revision`, the shape `saffron draft` writes, so reading by
    origin alone would miss one of the two. A task with no row is still
    judged against its file at `base_sha`."""
    witness = "tests/test_regate_text.py::test_guard"
    fixture = _build_fixture(tmp_path)
    home = tmp_path / "home"
    work = fixture.work.resolve()
    mirror_path = cli._mirror_path(work, home)

    mutants_sha = _mutants_commit(
        work,
        parent=None,
        spec_id=SPEC_ID,
        yaml_text=_mutants_yaml(witness, file="src/witness-target.py", find="marker"),
    )
    _set_mutants_ref(work, mutants_sha)

    revision_path = f".saffron/specs/{SPEC_FILENAME}"
    minted_path = f".saffron/specs/{SPEC_ID}-minted.md"
    first_text = _spec_text("first revision", witness=witness)
    second_text = _spec_text("second revision", witness=witness)
    first_sha = hashlib.sha256(first_text.encode()).hexdigest()

    ledger = _seeding_ledger(home / "ledger.db", fixture.origin_url)

    task_revision = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="saffron/SA-0005",
        pr_url="https://github.com/o/r/pull/101",
        pushed_sha=fixture.packaged_sha,
        mutants_commit=mutants_sha,
    )
    ledger.record_spec_text(
        task_revision,
        origin="revision",
        spec_id=SPEC_ID,
        path=revision_path,
        text=first_text,
    )
    ledger.record_spec_text(
        task_revision,
        origin="revision",
        spec_id=SPEC_ID,
        path=revision_path,
        text=second_text,
    )

    task_follow_up = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=first_sha,
        branch="saffron/SA-0005",
        pr_url="https://github.com/o/r/pull/102",
        pushed_sha=fixture.packaged_sha,
        mutants_commit=mutants_sha,
    )
    ledger.record_spec_text(
        task_follow_up,
        origin="follow_up",
        spec_id=SPEC_ID,
        path=minted_path,
        text=first_text,
    )
    ledger.record_spec_text(
        task_follow_up,
        origin="follow_up",
        spec_id=SPEC_ID,
        path=minted_path,
        text=second_text,
    )

    task_draft = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=first_sha,
        branch="saffron/SA-0005",
        pr_url="https://github.com/o/r/pull/103",
        pushed_sha=fixture.packaged_sha,
        mutants_commit=mutants_sha,
    )
    ledger.record_spec_text(
        task_draft,
        origin="draft",
        spec_id=SPEC_ID,
        path=minted_path,
        text=first_text,
    )
    ledger.record_spec_text(
        task_draft,
        origin="revision",
        spec_id=SPEC_ID,
        path=minted_path,
        text=second_text,
    )

    task_no_row = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="saffron/SA-0005",
        pr_url="https://github.com/o/r/pull/104",
        pushed_sha=fixture.packaged_sha,
    )
    ledger.close()

    def _gh(argv: list[str]):
        payload = json.dumps({"state": "OPEN", "baseRefName": "main"})
        return subprocess.CompletedProcess(argv, 0, payload, "")

    monkeypatch.setattr(cli, "run_gh", _gh)
    monkeypatch.setattr(repo_image, "build_cell_image", lambda repo: "fake-image:tag")
    monkeypatch.chdir(work)

    cases = [
        (task_revision, "second revision"),
        (task_follow_up, "second revision"),
        (task_draft, "second revision"),
        (task_no_row, "v1"),
    ]
    for task_id, expected_title in cases:
        _install_probe_fakes(monkeypatch, [])
        reverify_calls: list = []
        monkeypatch.setattr(package_phase, "reverify", _fake_reverify(reverify_calls))
        result = cli.main(["--home", str(home), "regate", str(task_id), "--repo", "."])
        capsys.readouterr()
        assert result == 0, task_id

        assert len(reverify_calls) == 1
        call = reverify_calls[0]
        assert call["spec"].title == expected_title
        if task_id == task_no_row:
            assert call["spec"].acceptance == []
        else:
            assert call["spec"].acceptance[0].mutant.file == "src/witness-target.py"

        ledger = Ledger(home / "ledger.db")
        row = ledger.regate(task_id)
        assert row is not None
        assert row["head_sha"] == fixture.review_sha
        assert row["baseline_sha"] == fixture.main_moved_sha
        assert row["new_failures"] == 0
        ledger.close()


def test_regate_declines_a_latest_recorded_text_that_does_not_parse_and_names_its_row(
    monkeypatch, tmp_path, capsys
):
    """A latest row that does not parse declines with exit 1 and a line
    naming the row's own number. No image build, probe or `reverify` runs,
    and nothing is recorded, though the task's file at `base_sha` hashes to
    its `spec_sha`. Recording a parseable row 2 over the bad one then
    re-gates green through the same spies."""
    fixture = _build_fixture(tmp_path)
    home = tmp_path / "home"
    work = fixture.work.resolve()
    mirror_path = cli._mirror_path(work, home)
    revision_path = f".saffron/specs/{SPEC_FILENAME}"

    bad_text = "not a spec at all\n"
    good_text = _spec_text("first revision")

    ledger = _seeding_ledger(home / "ledger.db", fixture.origin_url)
    task_only_bad = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="saffron/SA-0005",
        pr_url="https://github.com/o/r/pull/201",
        pushed_sha=fixture.packaged_sha,
    )
    ledger.record_spec_text(
        task_only_bad,
        origin="revision",
        spec_id=SPEC_ID,
        path=revision_path,
        text=bad_text,
    )

    task_second_bad = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="saffron/SA-0005",
        pr_url="https://github.com/o/r/pull/202",
        pushed_sha=fixture.packaged_sha,
    )
    ledger.record_spec_text(
        task_second_bad,
        origin="revision",
        spec_id=SPEC_ID,
        path=revision_path,
        text=good_text,
    )
    ledger.record_spec_text(
        task_second_bad,
        origin="revision",
        spec_id=SPEC_ID,
        path=revision_path,
        text=bad_text,
    )
    ledger.close()

    monkeypatch.setattr(cli, "run_gh", _gh_pr_view("unused", "OPEN", "main", []))
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

    for task_id, n in ((task_only_bad, 1), (task_second_bad, 2)):
        result = cli.main(["--home", str(home), "regate", str(task_id), "--repo", "."])
        out = capsys.readouterr().out
        assert result == 1
        assert out.count("regate:") == 1
        assert f"task {task_id}'s text {n} does not parse" in out
        ledger = Ledger(home / "ledger.db")
        assert ledger.regate(task_id) is None
        ledger.close()

    assert build_calls == []
    assert order == []
    assert reverify_calls == []

    ledger = _seeding_ledger(home / "ledger.db", fixture.origin_url)
    ledger.record_spec_text(
        task_only_bad,
        origin="revision",
        spec_id=SPEC_ID,
        path=revision_path,
        text=good_text,
    )
    ledger.close()

    result = cli.main(
        ["--home", str(home), "regate", str(task_only_bad), "--repo", "."]
    )
    out = capsys.readouterr().out
    assert result == 0, out
    assert build_calls == [work]
    assert len(reverify_calls) == 1

    ledger = Ledger(home / "ledger.db")
    row = ledger.regate(task_only_bad)
    assert row is not None
    assert row["new_failures"] == 0
    ledger.close()


def _adopt_recorded_text_case(
    case_root, monkeypatch, capsys, *, state: str, has_text: bool
) -> str:
    """One `saffron adopt` run on its own fixture, seeded with a task in
    `state`, holding a recorded text when `has_text`. Returns the task's
    state after adopt runs."""
    witness = "tests/test_elsewhere.py::test_guard"
    fixture = _build_fixture(case_root)
    home = case_root / "home"
    work = fixture.work.resolve()
    mirror_path = cli._mirror_path(work, home)

    outside_sha = _mutants_commit(
        work,
        parent=None,
        spec_id=SPEC_ID,
        yaml_text=_mutants_yaml(
            witness, file="src/elsewhere.py", find="outside-diff-marker"
        ),
    )
    _set_mutants_ref(work, outside_sha)

    ledger = _seeding_ledger(home / "ledger.db", fixture.origin_url)
    task_id = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="saffron/SA-0005",
        pr_url=None,
        mutants_commit=outside_sha,
    )
    if has_text:
        ledger.record_spec_text(
            task_id,
            origin="revision",
            spec_id=SPEC_ID,
            path=f".saffron/specs/{SPEC_FILENAME}",
            text=_spec_text("revised spec", witness=witness),
        )
    ledger.set_task_package(
        task_id, state, branch="saffron/SA-0005", pushed_sha="", pr_url=""
    )
    repo_id = ledger.resolve_repo_id(fixture.origin_url)
    assert repo_id is not None
    ledger.close()

    # Create the mirror before adopt writes its facts (item 170).
    git_mirror.ensure_mirror(work, mirror_path)

    pr_url = "https://github.com/o/r/pull/9"

    def _gh(argv: list[str]):
        if argv[2] == "view" and len(argv) > 4 and argv[4] == "--repo":
            payload = json.dumps(
                {
                    "url": pr_url,
                    "headRefOid": fixture.review_sha,
                    "headRefName": "saffron/SA-0005",
                }
            )
            return subprocess.CompletedProcess(argv, 0, payload, "")
        payload = json.dumps({"state": "OPEN", "baseRefName": "main"})
        return subprocess.CompletedProcess(argv, 0, payload, "")

    monkeypatch.setattr(cli, "run_gh", _gh)
    monkeypatch.setattr(package_phase, "github_slug", lambda _url: "o/r")
    monkeypatch.setattr(repo_image, "build_cell_image", lambda repo: "fake-image:tag")
    _install_probe_fakes(monkeypatch, [])
    monkeypatch.setattr(
        package_phase, "reverify", _fake_reverify_through_revert_gate([])
    )

    monkeypatch.chdir(work)
    result = cli.main(["--home", str(home), "adopt", SPEC_ID, "9", "--repo", "."])
    assert result == 0, capsys.readouterr().out

    ledger = Ledger(home / "ledger.db")
    row = next(r for r in ledger.tasks_by_repo(repo_id) if r["task_id"] == task_id)
    final_state = row["state"]
    ledger.close()
    return final_state


def test_adopt_moves_a_task_that_ran_a_recorded_spec_text_to_ready_for_review(
    monkeypatch, tmp_path, capsys
):
    """`saffron adopt` moves an `EXHAUSTED` task and a `MERGE_FAILED` task
    that each hold a recorded spec text to `READY_FOR_REVIEW`, through
    `regate.run_regate` with no fake. The text declares a witness whose
    pinned mutant lies outside the diff. The file at `base_sha` declares no
    witness at all, so a sibling task on the same fixture shape with no
    recorded text stays `EXHAUSTED`."""
    for n, state in enumerate(("EXHAUSTED", "MERGE_FAILED")):
        case_root = tmp_path / f"case-{n}"
        case_root.mkdir()
        final_state = _adopt_recorded_text_case(
            case_root, monkeypatch, capsys, state=state, has_text=True
        )
        assert final_state == "READY_FOR_REVIEW", state

    case_root = tmp_path / "case-no-text"
    case_root.mkdir()
    final_state = _adopt_recorded_text_case(
        case_root, monkeypatch, capsys, state="EXHAUSTED", has_text=False
    )
    assert final_state == "EXHAUSTED"


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


@dataclass
class CommitDiffFixture:
    """Every sha `review_commit_diff`'s own witnesses need, from one shared
    checkout with no bare origin, ledger or `gh` fake: the function reads
    the checkout itself as its mirror."""

    work: Path
    baseline_sha: str
    pushed_sha: str
    ordinary_head: str
    merge_only_head: str
    restacked_copy: str
    restacked_head: str
    stray_sha: str


# Shared by both packaged commits, so `_rebased_copy` matches the restacked
# copy by message alone, whichever sha a case passes as `pushed_sha`.
_PACKAGED_MESSAGE = "packaged commit"


def _build_commit_diff_fixture(tmp_path: Path) -> CommitDiffFixture:
    """A base commit, a moved `main`, two packaged commits sharing one
    message, and three heads. One carries a review commit merged with `main`. One merges
    `main` with no review commit at all. One restacks a second, separate
    packaged commit onto the moved `main`, then adds its own review
    commit. That review commit reverts one file, so a wrong range start
    or an unfiltered path set changes the restacked head's own result.
    A fourth, unrelated branch stands for a stray commit naming neither."""
    work = tmp_path / "work"
    subprocess.run(["git", "init", "-q", str(work)], check=True)
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "config", "user.name", "T")
    _git(work, "symbolic-ref", "HEAD", "refs/heads/main")

    (work / "tests").mkdir(parents=True)
    (work / "tests" / "test_old.py").write_text(
        "\n".join(f"# old test file content, line {n}" for n in range(1, 21)) + "\n"
    )
    (work / "src").mkdir()
    (work / "src" / "q.py").write_text("base q\n")
    (work / "src" / "r.py").write_text("r line1\nr line2\nr line3\n")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "base")
    base_sha = _git(work, "rev-parse", "HEAD")

    (work / "main.txt").write_text("main moved\n")
    (work / "src" / "r.py").write_text("r line1\nr line2\nr line3 main\n")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "main moved")
    baseline_sha = _git(work, "rev-parse", "HEAD")

    _git(work, "checkout", "-q", "-b", "saffron/SA-0005", base_sha)
    (work / "src" / "p.py").write_text("packaged p\n")
    (work / "src" / "q.py").write_text("packaged q\n")
    (work / "tests" / "test_w.py").write_text("packaged w\n")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", _PACKAGED_MESSAGE)
    pushed_sha = _git(work, "rev-parse", "HEAD")
    # Kept reachable after the restack below, as `tests/test_commit_review.py`
    # keeps the original packaged commit reachable after its own rebase.
    _git(work, "branch", "keeps-the-original", pushed_sha)

    _git(work, "checkout", "-q", "-b", "ordinary", pushed_sha)
    (work / "tests" / "test_w.py").write_text("packaged w\nreview edit\n")
    (work / "src" / "q.py").write_text("base q\n")
    _git(work, "mv", "tests/test_old.py", "tests/test_new.py")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "review commit (ordinary)")
    _git(work, "merge", "-q", "--no-ff", "-m", "Merge main (update branch)", "main")
    ordinary_head = _git(work, "rev-parse", "HEAD")

    _git(work, "checkout", "-q", "-b", "merge-only", pushed_sha)
    _git(work, "merge", "-q", "--no-ff", "-m", "Merge main (update branch)", "main")
    merge_only_head = _git(work, "rev-parse", "HEAD")

    # A sibling of `pushed_sha`, so a wrong range start changes the
    # restacked head's own answer rather than coincide with the right one.
    _git(work, "checkout", "-q", "-b", "restack-packaged", base_sha)
    (work / "src" / "p.py").write_text("packaged p\n")
    (work / "src" / "q.py").write_text("packaged q\n")
    (work / "tests" / "test_w.py").write_text("packaged w\n")
    (work / "src" / "r.py").write_text("r line1 restack\nr line2\nr line3\n")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", _PACKAGED_MESSAGE)
    restack_pushed_sha = _git(work, "rev-parse", "HEAD")
    _git(work, "branch", "keeps-the-restack-original", restack_pushed_sha)

    _git(work, "checkout", "-q", "-b", "restacked", restack_pushed_sha)
    _git(work, "rebase", "-q", "--onto", baseline_sha, base_sha, "restacked")
    restacked_copy = _git(work, "rev-parse", "HEAD")
    (work / "tests" / "test_w.py").write_text("packaged w\nrestack review edit\n")
    # Reverted to its base text, which `main` never changed, as the
    # ordinary case's review commit reverts it above.
    (work / "src" / "q.py").write_text("base q\n")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "review commit (restack)")
    restacked_head = _git(work, "rev-parse", "HEAD")

    _git(work, "checkout", "-q", "-b", "stray", base_sha)
    (work / "stray.txt").write_text("stray\n")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "stray commit, unrelated")
    stray_sha = _git(work, "rev-parse", "HEAD")

    return CommitDiffFixture(
        work=work,
        baseline_sha=baseline_sha,
        pushed_sha=pushed_sha,
        ordinary_head=ordinary_head,
        merge_only_head=merge_only_head,
        restacked_copy=restacked_copy,
        restacked_head=restacked_head,
        stray_sha=stray_sha,
    )


def _changed_paths_in(diff: str) -> list[str]:
    return sorted(re.findall(r"^diff --git a/(\S+) b/\S+$", diff, re.MULTILINE))


def _raw_diff(work: Path, start: str, head: str, paths: list[str]) -> str:
    return subprocess.run(
        [
            "git",
            "-C",
            str(work),
            "-c",
            "core.quotePath=false",
            "--literal-pathspecs",
            "diff",
            *DIFF_FLAGS,
            start,
            head,
            "--",
            *paths,
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_review_commit_diff_keeps_the_review_commits_paths_the_task_also_changed(
    tmp_path,
):
    from saffron.regate import review_commit_diff

    fixture = _build_commit_diff_fixture(tmp_path)

    diff = review_commit_diff(
        fixture.work, fixture.pushed_sha, fixture.baseline_sha, fixture.ordinary_head
    )
    paths = _changed_paths_in(diff)
    assert paths == ["tests/test_new.py", "tests/test_old.py", "tests/test_w.py"]
    assert diff == _raw_diff(
        fixture.work, fixture.pushed_sha, fixture.ordinary_head, paths
    )

    empty = review_commit_diff(
        fixture.work, fixture.pushed_sha, fixture.baseline_sha, fixture.merge_only_head
    )
    assert empty == ""


def test_review_commit_diff_starts_a_restacked_branch_at_the_packaged_commits_copy(
    tmp_path,
):
    from saffron.regate import review_commit_diff

    fixture = _build_commit_diff_fixture(tmp_path)

    diff = review_commit_diff(
        fixture.work, fixture.pushed_sha, fixture.baseline_sha, fixture.restacked_head
    )
    paths = _changed_paths_in(diff)
    assert paths == ["tests/test_w.py"]
    assert diff == _raw_diff(
        fixture.work, fixture.restacked_copy, fixture.restacked_head, paths
    )


def test_review_commit_diff_is_empty_for_a_head_that_is_the_packaged_commit(tmp_path):
    from saffron.regate import review_commit_diff

    fixture = _build_commit_diff_fixture(tmp_path)

    non_empty = review_commit_diff(
        fixture.work, fixture.pushed_sha, fixture.baseline_sha, fixture.ordinary_head
    )
    assert _changed_paths_in(non_empty) == [
        "tests/test_new.py",
        "tests/test_old.py",
        "tests/test_w.py",
    ]

    assert (
        review_commit_diff(
            fixture.work, fixture.pushed_sha, fixture.baseline_sha, fixture.pushed_sha
        )
        == ""
    )
    assert (
        review_commit_diff(
            fixture.work,
            fixture.pushed_sha,
            fixture.baseline_sha,
            fixture.restacked_copy,
        )
        == ""
    )


def test_review_commit_diff_is_empty_when_no_packaged_commit_is_on_head(tmp_path):
    from saffron.regate import review_commit_diff

    fixture = _build_commit_diff_fixture(tmp_path)

    non_empty = review_commit_diff(
        fixture.work, fixture.pushed_sha, fixture.baseline_sha, fixture.ordinary_head
    )
    assert non_empty != ""

    for bad_pushed_sha in (None, "", "0" * 40, fixture.stray_sha):
        assert (
            review_commit_diff(
                fixture.work,
                bad_pushed_sha,
                fixture.baseline_sha,
                fixture.ordinary_head,
            )
            == ""
        )


# --- wrong-version re-asking (`b-d9a027`, `SA-0404`) -----------------------

_WV_SPEC_FILENAME = "SA-0005-wrong-version.md"
_WV_W1_WITNESS = "tests/test_w.py::test_w1"
_WV_W2_WITNESS = "tests/test_w.py::test_w2"
_WV_X_WITNESS = "tests/test_x.py::test_x1"
_WV_M_WITNESS = "tests/test_m.py::test_m1"
_WV_P_WITNESS = "tests/test_p.py::test_p1"
_WV_COLLECTED = [_WV_W1_WITNESS, _WV_X_WITNESS, _WV_P_WITNESS, _WV_M_WITNESS]


def _wv_killed(version: str, file: str, find: str, replace: str) -> dict:
    return {
        "version": version,
        "edit": {"file": file, "find": find, "replace": replace},
        "reason": "",
        "outcome": "killed",
        "summary": "",
    }


def _wv_child_spec_text() -> str:
    return (
        "---\n"
        "id: SA-0005\n"
        "title: wrong version re-ask\n"
        "type: bug\n"
        "depends_on: ['SA-0003']\n"
        "acceptance:\n"
        f"  - claim: c1\n    witness: {_WV_W1_WITNESS}\n"
        "    wrong_versions:\n      - v1\n"
        f"  - claim: c2\n    witness: {_WV_W2_WITNESS}\n"
        "    wrong_versions:\n      - v2\n"
        f"  - claim: c3\n    witness: {_WV_X_WITNESS}\n"
        "    wrong_versions:\n      - v3\n"
        f"  - claim: c4\n    witness: {_WV_M_WITNESS}\n"
        "    wrong_versions:\n      - v4\n"
        "---\n"
    )


def _wv_parent_spec_text(*, with_wrong_versions: bool) -> str:
    body = (
        "---\n"
        "id: SA-0003\n"
        "title: wrong version parent\n"
        "type: bug\n"
        "acceptance:\n"
        f"  - claim: cp\n    witness: {_WV_P_WITNESS}\n"
    )
    if with_wrong_versions:
        body += "    wrong_versions:\n      - vp\n"
    return body + "---\n"


def _write_wv_policy(work: Path, *, moved: bool = False) -> None:
    """One declared test path, one inert pattern (so `pv3` below is refused
    before any cell), and one gate env entry, as the witness names. One
    `witness.assertion` too (`b-c2f264`). `moved` changes every member, so a
    member read from the checkout is caught."""
    gates_dir = work / ".saffron" / "gates"
    gates_dir.mkdir(parents=True, exist_ok=True)
    tests_gate = gates_dir / "tests"
    if not tests_gate.exists():
        tests_gate.write_text('#!/bin/sh\necho "{}"\n')
        tests_gate.chmod(0o755)
    gate, paths, inert, env, assertion = (
        ("checks", "spec/**", "# never: {name}", "2", "^assert")
        if moved
        else ("tests", "tests/**", "\\s*# noop: {name}", "1", "^KeyError")
    )
    (work / ".saffron" / "policy.yaml").write_text(
        "gates:\n"
        f"  {gate}: {{blocking: true}}\n"
        "integrity:\n"
        f"  test_paths: ['{paths}']\n"
        "probes:\n"
        f"  inert: ['{inert}']\n"
        "thread_env:\n"
        f"  SOME_ENV: '{env}'\n"
        "witness:\n"
        f"  assertion: '{assertion}'\n"
    )


@dataclass
class WrongVersionFixture:
    """Every sha and path the wrong-version witnesses need.

    `checkout` is a transport clone holding `main` alone. It lacks the
    task's own branch, so a mutation that reads the review diff from it,
    rather than the mirror, is distinguishable. `main`'s own tip keeps
    moving after `head` is cut, so the base branch's fetched tip is never
    the baseline (`b-d9a027`)."""

    checkout: Path
    base_sha: str
    baseline_sha: str
    packaged_sha: str
    review_sha: str
    origin_url: str
    spec_sha: str


def _build_wrong_version_fixture(tmp_path: Path) -> WrongVersionFixture:
    """A packaged commit adds a binary file and `tests/test_x.py`, neither
    edited again. A review commit then adds `tests/test_w.py` and
    `tests/test_p.py`, merged with a `main` that moved once first.

    The review range and the baseline range then share only
    `tests/test_w.py` and `tests/test_p.py` (`SA-0403`'s narrowing).
    `main` moves once more afterward: `tests/test_m.py` again, the
    policy's own gate env, and the parent spec losing its wrong versions.
    None of that reaches the task's own base, read from the export."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True)
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "config", "user.name", "T")
    _git(work, "symbolic-ref", "HEAD", "refs/heads/main")

    _write_wv_policy(work)
    specs_dir = work / ".saffron" / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / _WV_SPEC_FILENAME).write_text(_wv_child_spec_text())
    (specs_dir / "SA-0003-parent.md").write_text(
        _wv_parent_spec_text(with_wrong_versions=True)
    )
    (work / "src").mkdir()
    (work / "src" / "b.py").write_text("def g():\n    return 2\n")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "base")
    base_sha = _git(work, "rev-parse", "HEAD")
    spec_sha = hashlib.sha256((specs_dir / _WV_SPEC_FILENAME).read_bytes()).hexdigest()

    (work / "main.txt").write_text("main moved\n")
    (work / "tests").mkdir(exist_ok=True)
    (work / "tests" / "test_m.py").write_text("m test\n")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "main moved")
    baseline_sha = _git(work, "rev-parse", "HEAD")

    _git(work, "checkout", "-q", "-b", "saffron/SA-0005", base_sha)
    (work / "tests").mkdir(exist_ok=True)
    (work / "tests" / "test_x.py").write_text("x test\n")
    (work / "image.bin").write_bytes(b"\x00\x01\x02binary")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "packaged commit")
    packaged_sha = _git(work, "rev-parse", "HEAD")

    (work / "tests" / "test_w.py").write_text("w test\n")
    (work / "tests" / "test_p.py").write_text("p test\n")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "review commit")
    _git(work, "merge", "-q", "--no-ff", "-m", "Merge main (update branch)", "main")
    review_sha = _git(work, "rev-parse", "HEAD")

    # `main` keeps moving after `head` is cut: its own tip is never the
    # baseline, and its own files disagree with the export at `base_sha`.
    _git(work, "checkout", "-q", "main")
    (work / "tests" / "test_m.py").write_text("m test v2\n")
    _write_wv_policy(work, moved=True)
    (specs_dir / "SA-0003-parent.md").write_text(
        _wv_parent_spec_text(with_wrong_versions=False)
    )
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "main moved again")

    _git(work, "push", "-q", "origin", "main")
    _git(work, "push", "-q", "origin", "saffron/SA-0005")
    origin_url = _git(work, "remote", "get-url", "origin")

    checkout = tmp_path / "checkout"
    subprocess.run(
        [
            "git",
            "clone",
            "-q",
            "--no-local",
            "--single-branch",
            "--branch",
            "main",
            origin_url,
            str(checkout),
        ],
        check=True,
    )

    return WrongVersionFixture(
        checkout=checkout,
        base_sha=base_sha,
        baseline_sha=baseline_sha,
        packaged_sha=packaged_sha,
        review_sha=review_sha,
        origin_url=origin_url,
        spec_sha=spec_sha,
    )


def _wv_own_record() -> list[dict]:
    return [
        {
            "witness": _WV_W1_WITNESS,
            "claim": "c1",
            "versions": [
                _wv_killed("v1", "src/a.py", "X1", "Y1"),
                _wv_killed("v2", "src/a.py", "X2", "Y2"),
                _wv_killed("v1b", "src/a.py", "X1b", "Y1b"),
            ],
        },
        {
            "witness": _WV_W2_WITNESS,
            "claim": "c2",
            "versions": [_wv_killed("v3", "src/a.py", "X3", "Y3")],
        },
        {
            "witness": _WV_X_WITNESS,
            "claim": "c3",
            "versions": [_wv_killed("vx", "src/d.py", "X4", "Y4")],
        },
        {
            "witness": _WV_M_WITNESS,
            "claim": "c4",
            "versions": [_wv_killed("vm", "src/e.py", "Xm", "Ym")],
        },
    ]


def _wv_parent_record() -> list[dict]:
    # Order matches the printed line order the witness names: the survivor,
    # then the inert version, then the errored one.
    return [
        {
            "witness": _WV_P_WITNESS,
            "claim": "cp",
            "versions": [
                _wv_killed("pv1", "src/c.py", "Xp1", "Yp1"),
                _wv_killed("pv3", "src/b.py", "return 2", "return 2\n    # noop: zzz"),
                _wv_killed("pv2", "src/c.py", "Xp2", "Yp2"),
            ],
        }
    ]


def _seed_wv_task(ledger: Ledger, fixture: WrongVersionFixture, mirror_path) -> int:
    return _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="saffron/SA-0005",
        pr_url="https://github.com/o/r/pull/9",
        pushed_sha=fixture.packaged_sha,
    )


def _install_wrong_version_stubs(monkeypatch, results: list):
    """Stubs `session.critic_cell`, `runner.run_gate`, `worktree.source_mutated`
    and `worktree.read_at_head`, so the real `_apply_criterion_probes` decides
    each pair's outcome from `results`, consumed in call order. Returns the
    ordered `critic_cell` keyword logs, the edits mutated (named by their
    own `replace` text) and the `run_gate` calls."""
    from saffron.cell import session as session_mod
    from saffron.cell import worktree as worktree_mod
    from saffron.gates import runner as runner_mod

    kwargs_log: list = []

    @contextlib.contextmanager
    def _critic_cell(**kwargs):
        kwargs_log.append(kwargs)
        yield "gate-1"

    monkeypatch.setattr(session_mod, "critic_cell", _critic_cell)

    mutate_log: list = []

    @contextlib.contextmanager
    def _source_mutated(_container, edit):
        mutate_log.append(edit.replace)
        yield None

    monkeypatch.setattr(worktree_mod, "source_mutated", _source_mutated)
    monkeypatch.setattr(
        worktree_mod,
        "read_at_head",
        lambda _container, _path: "X1 X2 X3 X1b Xp1 Xp2 content\n",
    )

    run_gate_calls: list = []
    results_iter = iter(results)

    def _run_gate(name, executable, cwd, *, subset=None, executor=None, **kw):
        run_gate_calls.append({"executable": executable, "subset": subset})
        return next(results_iter)

    monkeypatch.setattr(runner_mod, "run_gate", _run_gate)

    return kwargs_log, mutate_log, run_gate_calls


def _wv_full_results() -> list[GateResult]:
    """The eight `tests` gate results the full own+parent scenario asks, in
    call order: the own killed version, each own survivor's two asks, each
    parent survivor's two asks, then the parent's errored version."""
    collected = GateResult(
        gate="tests", status="pass", tool="pytest 1", collected=_WV_COLLECTED
    )

    def _plain(status: GateStatus) -> GateResult:
        return GateResult(gate="tests", status=status, tool="pytest 1")

    return [
        _plain("fail"),
        _plain("pass"),
        collected,
        _plain("pass"),
        collected,
        _plain("pass"),
        collected,
        GateResult(gate="tests", status="error", tool="pytest 1", summary="boom"),
    ]


def _prepare_wrong_version_run(
    monkeypatch, checkout: Path, results: list, new_failures: tuple = ()
) -> dict:
    """Everything but the own/parent record files: `gh`, the image build, the
    probe and `reverify`, so the `cli.main` call under test reaches the
    wrong-version asking and the probe cell alone."""
    monkeypatch.setattr(cli, "run_gh", _gh_pr_view("unused", "OPEN", "main", []))
    monkeypatch.setattr(repo_image, "build_cell_image", lambda repo: "fake-image:tag")
    _install_probe_fakes(monkeypatch, [])
    reverify_calls: list = []
    monkeypatch.setattr(
        package_phase,
        "reverify",
        _fake_reverify(
            reverify_calls, new_failures=new_failures, tests_collected=_WV_COLLECTED
        ),
    )
    monkeypatch.chdir(checkout)
    kwargs_log, mutate_log, run_gate_calls = _install_wrong_version_stubs(
        monkeypatch, results
    )
    return {
        "kwargs_log": kwargs_log,
        "mutate_log": mutate_log,
        "run_gate_calls": run_gate_calls,
        "reverify_calls": reverify_calls,
    }


def _seed_wv_records(home: Path) -> None:
    own_dir = home / "batches" / "v0" / "SA-0005"
    parent_dir = home / "batches" / "v0" / "SA-0003"
    own_dir.mkdir(parents=True)
    parent_dir.mkdir(parents=True)
    (own_dir / "wrong-versions.json").write_text(json.dumps(_wv_own_record()))
    (parent_dir / "wrong-versions.json").write_text(json.dumps(_wv_parent_record()))


def test_regate_asks_the_tasks_own_and_each_parents_killed_versions_in_one_probe_cell(
    monkeypatch, tmp_path, capsys
):
    fixture = _build_wrong_version_fixture(tmp_path)
    home = tmp_path / "home"
    checkout = fixture.checkout.resolve()
    mirror_path = cli._mirror_path(checkout, home)

    ledger = _seeding_ledger(home / "ledger.db", fixture.origin_url)
    task_id = _seed_wv_task(ledger, fixture, mirror_path)
    ledger.close()
    _seed_wv_records(home)

    logs = _prepare_wrong_version_run(monkeypatch, checkout, _wv_full_results())
    result = cli.main(["--home", str(home), "regate", str(task_id), "--repo", "."])
    capsys.readouterr()
    assert result == 1

    kwargs_log = logs["kwargs_log"]
    assert len(kwargs_log) == 1
    call = kwargs_log[0]
    assert call["spec"].spec_id == "SA-0005"
    assert call["spec"].tree_base == fixture.baseline_sha
    assert call["repo"] == checkout
    assert call["mirror"] == mirror_path
    assert (
        call["gates_dir"] == home / "batches" / "v0" / "regate" / str(task_id) / "gates"
    )
    assert call["env"] == {"SOME_ENV": "1"}

    expected_patch = subprocess.run(
        [
            "git",
            "-C",
            str(mirror_path),
            "-c",
            "core.quotePath=false",
            "diff",
            *DIFF_FLAGS,
            "--binary",
            "--full-index",
            fixture.baseline_sha,
            fixture.review_sha,
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert call["patch"] == expected_patch

    for entry in logs["run_gate_calls"]:
        assert entry["executable"] == Path(GATES_MOUNT) / ".saffron" / "gates" / "tests"

    assert logs["mutate_log"] == [
        "Y1",
        "Y2",
        "Y2",
        "Y1b",
        "Y1b",
        "Yp1",
        "Yp1",
        "Yp2",
    ]


def _wv_raised_results() -> list[GateResult]:
    """`_wv_full_results`, with the own first version's kill replaced by a
    raise under the task's base policy (`^KeyError`), which an `assert`
    detail misses (`b-c2f264`)."""
    results = _wv_full_results()
    results[0] = GateResult(
        gate="tests",
        status="fail",
        tool="pytest 1",
        failures=[Failure(file=_WV_W1_WITNESS, code="FAILED", detail="assert 1 == 2")],
    )
    return results


def test_regate_prints_a_version_that_only_raised_and_counts_it_nowhere(
    monkeypatch, tmp_path, capsys
):
    """`regate` passes the base policy's `witness.assertion` to
    `_apply_criterion_probes`. A revived version that only raised prints its
    own line and adds no new failure (`b-c2f264`). An `assert` detail misses
    the base's `^KeyError` and reads `raised`. A `KeyError` detail reads
    `killed`, as before, and prints no raised line at all."""
    fixture = _build_wrong_version_fixture(tmp_path)
    home = tmp_path / "home"
    checkout = fixture.checkout.resolve()
    mirror_path = cli._mirror_path(checkout, home)

    ledger = _seeding_ledger(home / "ledger.db", fixture.origin_url)
    task_id = _seed_wv_task(ledger, fixture, mirror_path)
    ledger.close()
    _seed_wv_records(home)

    _prepare_wrong_version_run(monkeypatch, checkout, _wv_raised_results())
    cli.main(["--home", str(home), "regate", str(task_id), "--repo", "."])
    out = capsys.readouterr().out

    lines = [line for line in out.splitlines() if line.startswith("regate: SA-")]
    before_parens = [line.split(" (", 1)[0] for line in lines]
    assert before_parens[:2] == [
        "regate: SA-0005 wrong version raised: v1",
        "regate: SA-0005 wrong version survived: v2",
    ]
    assert "3 new failure" in out.splitlines()[-1]

    killed_results = _wv_full_results()
    killed_results[0] = GateResult(
        gate="tests",
        tool="pytest 1",
        status="fail",
        failures=[Failure(file=_WV_W1_WITNESS, code="FAILED", detail="KeyError: 'x'")],
    )
    _prepare_wrong_version_run(monkeypatch, checkout, killed_results)
    cli.main(["--home", str(home), "regate", str(task_id), "--repo", "."])
    out = capsys.readouterr().out
    assert "wrong version raised" not in out


def test_regate_counts_each_surviving_wrong_version_as_a_new_failure_and_names_its_spec(
    monkeypatch, tmp_path, capsys
):
    fixture = _build_wrong_version_fixture(tmp_path)
    home = tmp_path / "home"
    checkout = fixture.checkout.resolve()
    mirror_path = cli._mirror_path(checkout, home)

    ledger = _seeding_ledger(home / "ledger.db", fixture.origin_url)
    task_id = _seed_wv_task(ledger, fixture, mirror_path)
    ledger.close()
    _seed_wv_records(home)

    gate_failure = (NewFailure("lint", Failure(file="x.py", code="E1", message="m1")),)
    logs = _prepare_wrong_version_run(
        monkeypatch, checkout, _wv_full_results(), new_failures=gate_failure
    )
    result = cli.main(["--home", str(home), "regate", str(task_id), "--repo", "."])
    out = capsys.readouterr().out

    lines = [line for line in out.splitlines() if line.startswith("regate: SA-")]
    before_parens = [line.split(" (", 1)[0] for line in lines]
    assert before_parens == [
        "regate: SA-0005 wrong version survived: v2",
        "regate: SA-0005 wrong version survived: v1b",
        "regate: SA-0005 wrong version unproven: v3",
        "regate: SA-0003 wrong version survived: pv1",
        "regate: SA-0003 wrong version unproven: pv3",
        "regate: SA-0003 wrong version error: pv2",
    ]
    for line in lines:
        assert line.endswith(")")

    assert "regate: lint E1 x.py" in out
    assert "4 new failures" in out.splitlines()[-1]
    assert len(logs["reverify_calls"]) == 1

    ledger = Ledger(home / "ledger.db")
    row = ledger.regate(task_id)
    assert row is not None
    assert row["head_sha"] == fixture.review_sha
    assert row["new_failures"] == 4
    ledger.close()
    assert result == 1


def test_regate_prints_each_record_it_cannot_read_and_enters_no_cell_without_a_pair(
    monkeypatch, tmp_path, capsys
):
    fixture = _build_wrong_version_fixture(tmp_path)
    home = tmp_path / "home"
    checkout = fixture.checkout.resolve()
    mirror_path = cli._mirror_path(checkout, home)

    ledger = _seeding_ledger(home / "ledger.db", fixture.origin_url)
    task_id = _seed_wv_task(ledger, fixture, mirror_path)
    ledger.close()

    own_path = home / "batches" / "v0" / "SA-0005" / "wrong-versions.json"
    parent_path = home / "batches" / "v0" / "SA-0003" / "wrong-versions.json"
    own_path.parent.mkdir(parents=True)
    parent_path.parent.mkdir(parents=True)

    # First: own broken, parent readable. Only the parent's pairs get asked,
    # in one cell. The parent survivor's line prints and the exit is 1.
    own_path.write_text("not json")
    parent_path.write_text(json.dumps(_wv_parent_record()))
    results_1 = [
        GateResult(gate="tests", status="pass", tool="pytest 1"),
        GateResult(
            gate="tests", status="pass", tool="pytest 1", collected=_WV_COLLECTED
        ),
        GateResult(gate="tests", status="error", tool="pytest 1", summary="boom"),
    ]
    logs_1 = _prepare_wrong_version_run(monkeypatch, checkout, results_1)
    result_1 = cli.main(["--home", str(home), "regate", str(task_id), "--repo", "."])
    out_1 = capsys.readouterr().out
    assert "regate: no wrong-version record read for SA-0005" in out_1
    assert "regate: no wrong-version record read for SA-0003" not in out_1
    assert "regate: SA-0003 wrong version survived: pv1" in out_1
    assert len(logs_1["kwargs_log"]) == 1
    assert result_1 == 1

    # Second: own restored, parent deleted. Only the own pairs get asked, in
    # one cell. The own survivors' lines print and the exit is 1.
    own_path.write_text(json.dumps(_wv_own_record()))
    parent_path.unlink()
    collected = GateResult(
        gate="tests", status="pass", tool="pytest 1", collected=_WV_COLLECTED
    )
    results_2 = [
        GateResult(gate="tests", status="fail", tool="pytest 1"),
        GateResult(gate="tests", status="pass", tool="pytest 1"),
        collected,
        GateResult(gate="tests", status="pass", tool="pytest 1"),
        collected,
    ]
    logs_2 = _prepare_wrong_version_run(monkeypatch, checkout, results_2)
    result_2 = cli.main(["--home", str(home), "regate", str(task_id), "--repo", "."])
    out_2 = capsys.readouterr().out
    assert "regate: no wrong-version record read for SA-0005" not in out_2
    assert "regate: no wrong-version record read for SA-0003" in out_2
    assert "regate: SA-0005 wrong version survived: v2" in out_2
    assert "regate: SA-0005 wrong version survived: v1b" in out_2
    assert len(logs_2["kwargs_log"]) == 1
    assert result_2 == 1

    # Third: own broken again, parent still deleted. Both lines print, own
    # first. No pair line prints, no cell is entered, and the exit is 0.
    own_path.write_text("not json")
    logs_3 = _prepare_wrong_version_run(monkeypatch, checkout, [])
    result_3 = cli.main(["--home", str(home), "regate", str(task_id), "--repo", "."])
    out_3 = capsys.readouterr().out
    lines_3 = out_3.splitlines()
    own_index = next(
        i
        for i, line in enumerate(lines_3)
        if line == "regate: no wrong-version record read for SA-0005"
    )
    parent_index = next(
        i
        for i, line in enumerate(lines_3)
        if line == "regate: no wrong-version record read for SA-0003"
    )
    assert own_index < parent_index
    assert not any("wrong version" in line for line in lines_3)
    assert logs_3["kwargs_log"] == []
    assert "green" in out_3.splitlines()[-1]
    assert result_3 == 0

    # Fourth: both restored, with the task's own `pushed_sha` now `head`.
    # The review diff is then empty, so neither line nor cell appears.
    own_path.write_text(json.dumps(_wv_own_record()))
    parent_path.write_text(json.dumps(_wv_parent_record()))
    push_ledger = _seeding_ledger(home / "ledger.db", fixture.origin_url)
    push_ledger.record_push(task_id, fixture.review_sha)
    push_ledger.close()

    logs_4 = _prepare_wrong_version_run(monkeypatch, checkout, [])
    result_4 = cli.main(["--home", str(home), "regate", str(task_id), "--repo", "."])
    out_4 = capsys.readouterr().out
    assert "no wrong-version record read" not in out_4
    assert "wrong version" not in out_4
    assert logs_4["kwargs_log"] == []
    assert result_4 == 0

    ledger = Ledger(home / "ledger.db")
    row = ledger.regate(task_id)
    assert row is not None
    assert row["new_failures"] == 0
    ledger.close()
