"""`saffron regate <task id> --repo .` (backlog item 97).

Every witness drives a real git fixture: a bare origin and a checkout. The
checkout commits a base, forks a parent branch and a packaged commit, then
adds a review commit. That commit merges a moved default branch into the
task's branch, the way GitHub's "update branch" does. `reverify`, the probe
and `gh` are faked. The mirror, the fetches and the merge base stay real git.
"""

from __future__ import annotations

import contextlib
import errno
import hashlib
import json
import os
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from saffron import cli, preflight
from saffron.cell import runtime
from saffron.gates.baseline import NewFailure
from saffron.gates.contract import Failure, GateResult
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


def _fake_reverify(calls: list, new_failures=()):
    def _reverify(**kwargs):
        calls.append(kwargs)
        run = SuiteRun(
            results=[], effective_risk="standard", advisory_gates=frozenset()
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
        f"task {task_recorded_text} ran a recorded spec text",
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
