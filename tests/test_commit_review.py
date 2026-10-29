"""`saffron review <task id> --repo .` (backlog item b-549012, `DESIGN.md` §5.7).

Every witness drives a real git fixture: a bare origin and a checkout. The
checkout commits a base carrying a marker in the policy, the spec and
`CLAUDE.md`. It moves the default branch past the base, then forks the
task's branch with a packaged commit and one or more review commits on
top. `gh`, `end_review.layer_cell` and `implement.run_agent` are faked.
The mirror and the fetches stay real git.
"""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import pytest

from saffron import cli
from saffron.agents.findings import Finding
from saffron.ledger import Ledger
from saffron.phases import implement

SPEC_ID = "SA-0900"
SPEC_FILENAME = f"{SPEC_ID}-commit-review-test.md"


@pytest.fixture(autouse=True)
def _token(monkeypatch):
    """Every witness but the decline test runs with a token set, since the
    decline test needs to prove the one case where it is unset."""
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "a-token")


@pytest.fixture(autouse=True)
def _no_cell(monkeypatch):
    """Every witness runs with `task.run_one_cell` forbidden: `review` opens
    its own critic cell through `end_review.layer_cell`, never a task cell."""
    from saffron import task

    def _reached(*_args, **_kwargs):
        raise AssertionError("review reached task.run_one_cell")

    monkeypatch.setattr(task, "run_one_cell", _reached)


def _git(repo, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _spec_text(marker: str) -> str:
    return (
        "---\n"
        f"id: {SPEC_ID}\n"
        "title: commit review fixture\n"
        "type: feature\n"
        "risk: standard\n"
        "touches: ['src/**']\n"
        "---\n\n"
        f"spec body marker {marker}\n\n"
        "## Acceptance criteria\n- [ ] it works\n"
    )


def _write_policy(work: Path, marker: str) -> None:
    gates_dir = work / ".saffron"
    gates_dir.mkdir(parents=True, exist_ok=True)
    (gates_dir / "policy.yaml").write_text(f"thread_env:\n  MARKER: {marker}\n")


def _write_spec(work: Path, marker: str) -> None:
    specs_dir = work / ".saffron" / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / SPEC_FILENAME).write_text(_spec_text(marker))


def _write_claude(work: Path, marker: str) -> None:
    (work / "CLAUDE.md").write_text(f"standing instructions marker {marker}\n")


@dataclass
class Fixture:
    """Every sha a witness needs: the task's own base, the packaged commit
    and the newest review commit, named the way the spec's own notes do."""

    work: Path
    no_spec_sha: str
    base_sha: str
    spec_sha: str
    packaged_sha: str
    review_sha: str
    origin_url: str


def _build_fixture(tmp_path: Path, *, review_lines: int = 1) -> Fixture:
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True)
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "config", "user.name", "T")
    _git(work, "symbolic-ref", "HEAD", "refs/heads/main")

    _write_policy(work, "p0")
    _write_claude(work, "c0")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "policy, no spec")
    no_spec_sha = _git(work, "rev-parse", "HEAD")

    _write_policy(work, "p1")
    _write_spec(work, "s1")
    _write_claude(work, "c1")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "base")
    base_sha = _git(work, "rev-parse", "HEAD")
    spec_sha = hashlib.sha256(
        (work / ".saffron" / "specs" / SPEC_FILENAME).read_bytes()
    ).hexdigest()

    # The default branch moves on, after the fork point. A read from its
    # head rather than `base_sha` would see these markers instead.
    _write_policy(work, "p2")
    _write_spec(work, "s2")
    _write_claude(work, "c2")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "main moved")

    branch = f"saffron/{SPEC_ID}"
    _git(work, "checkout", "-q", "-b", branch, base_sha)
    (work / "work.txt").write_text("packaged change\n")
    _git(work, "add", "-A")
    _git(
        work,
        "commit",
        "-q",
        "-m",
        f"saffron {SPEC_ID}: packaged change\n\nthe packaged commit's own body",
    )
    packaged_sha = _git(work, "rev-parse", "HEAD")

    review_sha = packaged_sha
    for i in range(review_lines):
        (work / f"review{i}.txt").write_text(f"review commit's own line {i}\n")
        _git(work, "add", "-A")
        _git(work, "commit", "-q", "-m", f"review({SPEC_ID}): round {i}")
        review_sha = _git(work, "rev-parse", "HEAD")

    _git(work, "push", "-q", "origin", "main")
    _git(work, "push", "-q", "origin", branch)

    origin_url = _git(work, "remote", "get-url", "origin")

    # The checkout's own files, dirtied last and never committed: a read
    # from the working tree rather than a mirror export would see these.
    _write_policy(work, "p-dirty")
    _write_spec(work, "s-dirty")
    _write_claude(work, "c-dirty")

    return Fixture(
        work=work,
        no_spec_sha=no_spec_sha,
        base_sha=base_sha,
        spec_sha=spec_sha,
        packaged_sha=packaged_sha,
        review_sha=review_sha,
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
    if pushed_sha is not None and pr_url is not None:
        ledger.set_task_package(task_id, "READY_FOR_REVIEW", branch, pushed_sha, pr_url)
    elif pushed_sha is not None:
        ledger.record_push(task_id, pushed_sha)
    elif pr_url is not None:
        ledger.adopt_pull_request(task_id, pr_url)
    return task_id


def _gh_state(state: str, calls: list):
    def _gh(argv: list[str]):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, json.dumps({"state": state}), "")

    return _gh


def _gh_states(states: dict[str, str], calls: list):
    def _gh(argv: list[str]):
        calls.append(argv)
        pr_url = argv[3]
        state = states.get(pr_url, "OPEN")
        return subprocess.CompletedProcess(argv, 0, json.dumps({"state": state}), "")

    return _gh


def _fake_layer_cell(calls: list, *, container: str = "endreview-fake", raises=None):
    @contextmanager
    def fake(fields, **kwargs):
        entry = {"fields": fields, "kwargs": kwargs, "exited": False}
        calls.append(entry)
        if raises is not None:
            raise raises
        try:
            yield container
        finally:
            entry["exited"] = True

    return fake


def _turn(text: str, *, session_id: str, cost: float, turns: int = 1):
    return implement.AttemptResult(
        session_id=session_id,
        subtype="success",
        terminal_reason="completed",
        num_turns=turns,
        cost_usd_est=cost,
        text=text,
    )


def _output_block(findings: list[dict]) -> str:
    return "reply\n<output>\n" + json.dumps({"findings": findings}) + "\n</output>"


def _lens_of(system_prompt: str) -> str:
    if "Spec lens" in system_prompt:
        return "spec"
    if "Standards lens" in system_prompt:
        return "standards"
    raise AssertionError(f"prompt names neither lens: {system_prompt[:120]!r}")


def _lens_agent(handlers: dict, calls: list):
    def run(container, *, prompt, options, **kwargs):
        lens = _lens_of(options["system_prompt"])
        calls.append(
            {"container": container, "lens": lens, "prompt": prompt, "options": options}
        )
        return handlers[lens]()

    return run


def _pr_view(self_pr: str = "https://github.com/o/r/pull/9") -> str:
    return self_pr


def test_review_reads_the_review_commits_with_both_end_review_lenses_and_charges_the_task(
    monkeypatch, tmp_path, capsys
):
    fixture = _build_fixture(tmp_path)
    home = tmp_path / "home"
    work = fixture.work.resolve()
    mirror_path = cli._mirror_path(work, home)
    pr_url = _pr_view()

    ledger = Ledger(home / "ledger.db")
    task_id = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch=f"saffron/{SPEC_ID}",
        pr_url=pr_url,
        pushed_sha=fixture.packaged_sha,
    )
    ledger.record_findings(
        task_id,
        [
            Finding(
                lens="correctness",
                severity="concern",
                file="q.py",
                line=1,
                claim="pre-existing",
            )
        ],
    )
    out_dir = home / "batches" / "v0"
    task_dir = out_dir / SPEC_ID
    task_dir.mkdir(parents=True)
    (task_dir / "findings.json").write_text('{"findings": []}')
    ledger.close()

    gh_calls: list = []
    monkeypatch.setattr(cli, "run_gh", _gh_state("OPEN", gh_calls))

    cell_calls: list = []
    from saffron import end_review

    monkeypatch.setattr(end_review, "layer_cell", _fake_layer_cell(cell_calls))

    agent_calls: list = []
    handlers = {
        "spec": lambda: _turn(
            _output_block(
                [
                    {
                        "file": "a.py",
                        "line": 2,
                        "severity": "concern",
                        "claim": "spec concern",
                    }
                ]
            ),
            session_id="spec-session",
            cost=0.11,
            turns=3,
        ),
        "standards": lambda: _turn(
            _output_block(
                [
                    {
                        "file": "b.py",
                        "line": 5,
                        "severity": "note",
                        "claim": "standards note",
                    }
                ]
            ),
            session_id="standards-session",
            cost=0.07,
            turns=2,
        ),
    }
    monkeypatch.setattr(implement, "run_agent", _lens_agent(handlers, agent_calls))

    monkeypatch.chdir(work)
    result = cli.main(["--home", str(home), "review", str(task_id), "--repo", "."])

    assert result == 0
    out = capsys.readouterr().out
    assert "spec concern" in out
    assert "standards note" in out

    assert gh_calls == [["gh", "pr", "view", pr_url, "--json", "state"]]

    assert len(cell_calls) == 1
    call = cell_calls[0]
    assert call["fields"].head == fixture.review_sha
    assert call["kwargs"]["mirror"] == mirror_path
    assert call["kwargs"]["gates_dir"] == out_dir / "review" / str(task_id) / "gates"
    assert call["kwargs"]["thread_env"] == {"MARKER": "p1"}
    assert call["exited"] is True

    assert {c["lens"] for c in agent_calls} == {"spec", "standards"}
    for call in agent_calls:
        assert call["container"] == "endreview-fake"
        prompt = call["options"]["system_prompt"]
        assert "review commit's own line 0" in prompt
        assert "packaged change" not in prompt
        assert f"**Range:** `{fixture.packaged_sha}..{fixture.review_sha}`" in prompt
        # The task's own in-cell finding, from `ledger.findings`.
        assert "- concern (correctness) q.py:1: pre-existing" in prompt
        # `CLAUDE.md` at `base_sha`, never the default branch's or the
        # checkout's own dirtied copy.
        assert "standing instructions marker c1" in prompt
        assert "standing instructions marker c2" not in prompt
        assert "standing instructions marker c-dirty" not in prompt
        # The end review's own ceilings, never the spec's declared ones
        # (50 turns / $2.50 here, where the spec defaults to 60 / $12).
        assert call["options"]["max_turns"] == end_review.LENS_MAX_TURNS
        assert call["options"]["max_budget_usd"] == end_review.LENS_BUDGET_USD

    ledger = Ledger(home / "ledger.db")
    attempts = ledger.attempts(task_id)
    assert len(attempts) == 2
    assert {a["phase"] for a in attempts} == {"COMMIT_REVIEW"}
    assert {a["session_id"] for a in attempts} == {"spec-session", "standards-session"}
    assert {a["num_turns"] for a in attempts} == {3, 2}
    assert {round(a["cost_usd_est"], 2) for a in attempts} == {0.11, 0.07}

    row = ledger._db.execute(
        "SELECT state, pushed_sha, pr_url FROM tasks WHERE task_id = ?", (task_id,)
    ).fetchone()
    assert row["state"] == "READY_FOR_REVIEW"
    assert row["pushed_sha"] == fixture.packaged_sha
    assert row["pr_url"] == pr_url
    assert len(ledger.findings(task_id)) == 1
    assert (
        ledger._db.execute("SELECT COUNT(*) AS c FROM end_reviews").fetchone()["c"] == 0
    )
    ledger.close()

    assert (task_dir / "findings.json").read_text() == '{"findings": []}'

    path = task_dir / "commit-reviews" / f"{fixture.review_sha}.json"
    assert path.is_file()
    payload = json.loads(path.read_text())
    assert payload["task_id"] == task_id
    assert payload["range_start"] == fixture.packaged_sha
    assert payload["head"] == fixture.review_sha
    lenses = {r["lens"] for r in payload["reviews"]}
    assert lenses == {"spec", "standards"}
    assert f"{out}".count("review:") >= 2
    assert str(path) in out


def test_review_starts_a_restacked_branchs_range_at_the_packaged_commits_rebased_copy(
    monkeypatch, tmp_path, capsys
):
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True)
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "config", "user.name", "T")
    _git(work, "symbolic-ref", "HEAD", "refs/heads/main")

    _write_policy(work, "p1")
    _write_spec(work, "s1")
    _write_claude(work, "c1")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "base")
    base_sha = _git(work, "rev-parse", "HEAD")
    spec_sha = hashlib.sha256(
        (work / ".saffron" / "specs" / SPEC_FILENAME).read_bytes()
    ).hexdigest()

    _git(work, "branch", "parent", base_sha)
    branch = f"saffron/{SPEC_ID}"
    _git(work, "checkout", "-q", "-b", branch, base_sha)
    (work / "work.txt").write_text("packaged change\n")
    _git(work, "add", "-A")
    _git(
        work,
        "commit",
        "-q",
        "-m",
        f"saffron {SPEC_ID}: packaged change\n\nthe packaged commit's own body",
    )
    packaged_sha = _git(work, "rev-parse", "HEAD")
    # A branch that still names the original packaged commit, kept in the
    # checkout so `ensure_mirror` still fetches that object into the mirror.
    _git(work, "branch", "keeps-the-original", packaged_sha)

    _git(work, "checkout", "-q", "parent")
    (work / "parent.txt").write_text("parent moved\n")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "parent moved")
    moved_parent = _git(work, "rev-parse", "HEAD")

    _git(work, "checkout", "-q", branch)
    _git(work, "rebase", "-q", "--onto", moved_parent, base_sha, branch)
    rebased_copy = _git(work, "rev-parse", "HEAD")
    assert rebased_copy != packaged_sha

    # The second review commit repeats the packaged subject with a
    # different body. A subject-only match would start the range there.
    (work / "review0.txt").write_text("review commit's own line 0\n")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", f"review({SPEC_ID}): first round")

    (work / "review1.txt").write_text("review commit's own line 1\n")
    _git(work, "add", "-A")
    _git(
        work,
        "commit",
        "-q",
        "-m",
        f"saffron {SPEC_ID}: packaged change\n\na different body entirely",
    )
    newest_head = _git(work, "rev-parse", "HEAD")

    _git(work, "push", "-q", "origin", "parent")
    _git(work, "push", "-q", "origin", branch)
    _git(work, "push", "-q", "origin", "keeps-the-original")
    origin_url = _git(work, "remote", "get-url", "origin")

    home = tmp_path / "home"
    mirror_path = cli._mirror_path(work.resolve(), home)
    pr_url = _pr_view()

    ledger = Ledger(home / "ledger.db")
    task_id = _seed_task(
        ledger,
        origin_url=origin_url,
        mirror_path=mirror_path,
        base_sha=base_sha,
        spec_sha=spec_sha,
        branch=branch,
        pr_url=pr_url,
        pushed_sha=packaged_sha,
    )
    ledger.close()

    monkeypatch.setattr(cli, "run_gh", _gh_state("OPEN", []))

    from saffron import end_review

    cell_calls: list = []
    monkeypatch.setattr(end_review, "layer_cell", _fake_layer_cell(cell_calls))

    handlers = {
        "spec": lambda: _turn(_output_block([]), session_id="s1", cost=0.01),
        "standards": lambda: _turn(_output_block([]), session_id="s2", cost=0.01),
    }
    agent_calls: list = []
    monkeypatch.setattr(implement, "run_agent", _lens_agent(handlers, agent_calls))

    monkeypatch.chdir(work)
    result = cli.main(["--home", str(home), "review", str(task_id), "--repo", "."])

    assert result == 0
    for call in agent_calls:
        prompt = call["options"]["system_prompt"]
        assert "review commit's own line 0" in prompt
        assert "review commit's own line 1" in prompt
        assert "parent moved" not in prompt
        assert "packaged change" not in prompt
        assert f"**Range:** `{rebased_copy}..{newest_head}`" in prompt


def test_review_reads_a_task_against_its_newest_recorded_spec_text(
    monkeypatch, tmp_path, capsys
):
    fixture = _build_fixture(tmp_path)
    home = tmp_path / "home"
    work = fixture.work.resolve()
    mirror_path = cli._mirror_path(work, home)
    pr_url = _pr_view()

    ledger = Ledger(home / "ledger.db")
    task_id = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch=f"saffron/{SPEC_ID}",
        pr_url=pr_url,
        pushed_sha=fixture.packaged_sha,
    )
    ledger.record_spec_text(
        task_id,
        origin="revision",
        spec_id=SPEC_ID,
        path=f".saffron/specs/{SPEC_ID}.md",
        text=_spec_text("first-recorded-text"),
    )
    ledger.record_spec_text(
        task_id,
        origin="revision",
        spec_id=SPEC_ID,
        path=f".saffron/specs/{SPEC_ID}.md",
        text=_spec_text("second-recorded-text"),
    )
    ledger.close()

    monkeypatch.setattr(cli, "run_gh", _gh_state("OPEN", []))

    from saffron import end_review

    cell_calls: list = []
    monkeypatch.setattr(end_review, "layer_cell", _fake_layer_cell(cell_calls))

    agent_calls: list = []
    handlers = {
        "spec": lambda: _turn(_output_block([]), session_id="s1", cost=0.01),
        "standards": lambda: _turn(_output_block([]), session_id="s2", cost=0.01),
    }
    monkeypatch.setattr(implement, "run_agent", _lens_agent(handlers, agent_calls))

    monkeypatch.chdir(work)
    result = cli.main(["--home", str(home), "review", str(task_id), "--repo", "."])

    assert result == 0
    for call in agent_calls:
        prompt = call["options"]["system_prompt"]
        assert "second-recorded-text" in prompt
        assert "first-recorded-text" not in prompt
        assert "spec body marker s1" not in prompt


def test_review_exits_one_when_either_lens_files_a_blocker(monkeypatch, tmp_path):
    from saffron import end_review

    def _run_case(blocker_lens: str, other_breaks: bool) -> int:
        fixture = _build_fixture(tmp_path / blocker_lens / str(other_breaks))
        home = tmp_path / blocker_lens / str(other_breaks) / "home"
        work = fixture.work.resolve()
        mirror_path = cli._mirror_path(work, home)
        pr_url = _pr_view()

        ledger = Ledger(home / "ledger.db")
        task_id = _seed_task(
            ledger,
            origin_url=fixture.origin_url,
            mirror_path=mirror_path,
            base_sha=fixture.base_sha,
            spec_sha=fixture.spec_sha,
            branch=f"saffron/{SPEC_ID}",
            pr_url=pr_url,
            pushed_sha=fixture.packaged_sha,
        )
        ledger.close()

        monkeypatch.setattr(cli, "run_gh", _gh_state("OPEN", []))
        monkeypatch.setattr(end_review, "layer_cell", _fake_layer_cell([]))

        def _blocker():
            return _turn(
                _output_block(
                    [{"file": "a.py", "line": 1, "severity": "blocker", "claim": "bad"}]
                ),
                session_id="s-blocker",
                cost=0.02,
            )

        def _clean():
            return _turn(_output_block([]), session_id="s-clean", cost=0.01)

        def _failing():
            raise implement.AgentFailed(
                "boom", attempt=_turn("", session_id="s-fail", cost=0.03)
            )

        other_lens = "standards" if blocker_lens == "spec" else "spec"
        handlers = {
            blocker_lens: _blocker,
            other_lens: _failing if other_breaks else _clean,
        }
        monkeypatch.setattr(implement, "run_agent", _lens_agent(handlers, []))

        monkeypatch.chdir(work)
        return cli.main(["--home", str(home), "review", str(task_id), "--repo", "."])

    assert _run_case("standards", False) == 1
    assert _run_case("spec", False) == 1
    assert _run_case("standards", True) == 1


def test_review_exits_two_when_a_lens_or_its_cell_breaks_and_charges_the_failed_turn(
    monkeypatch, tmp_path, capsys
):
    from saffron import end_review

    def _seed(root: Path):
        fixture = _build_fixture(root)
        home = root / "home"
        work = fixture.work.resolve()
        mirror_path = cli._mirror_path(work, home)
        pr_url = _pr_view()
        ledger = Ledger(home / "ledger.db")
        task_id = _seed_task(
            ledger,
            origin_url=fixture.origin_url,
            mirror_path=mirror_path,
            base_sha=fixture.base_sha,
            spec_sha=fixture.spec_sha,
            branch=f"saffron/{SPEC_ID}",
            pr_url=pr_url,
            pushed_sha=fixture.packaged_sha,
        )
        ledger.close()
        return home, work, task_id, fixture

    # 1. The Spec lens's turn raises `AgentFailed`. Its attempt still charges.
    root = tmp_path / "case1"
    home, work, task_id, fixture1 = _seed(root)
    monkeypatch.setattr(cli, "run_gh", _gh_state("OPEN", []))
    monkeypatch.setattr(end_review, "layer_cell", _fake_layer_cell([]))

    def _spec_fails():
        raise implement.AgentFailed(
            "spec broke", attempt=_turn("", session_id="s-fail", cost=0.05)
        )

    handlers = {
        "spec": _spec_fails,
        "standards": lambda: _turn(_output_block([]), session_id="s-ok", cost=0.01),
    }
    monkeypatch.setattr(implement, "run_agent", _lens_agent(handlers, []))
    monkeypatch.chdir(work)
    assert cli.main(["--home", str(home), "review", str(task_id), "--repo", "."]) == 2

    ledger = Ledger(home / "ledger.db")
    attempts = ledger.attempts(task_id)
    assert any(
        a["session_id"] == "s-fail" and a["cost_usd_est"] == 0.05 for a in attempts
    )
    ledger.close()
    review_file = (
        home
        / "batches"
        / "v0"
        / SPEC_ID
        / "commit-reviews"
        / f"{fixture1.review_sha}.json"
    )
    errors = {
        r["lens"]: r["error"] for r in json.loads(review_file.read_text())["reviews"]
    }
    assert errors["spec"] is not None
    assert errors["standards"] is None

    # 2. The same break in the Standards lens's turn alone.
    root = tmp_path / "case2"
    home, work, task_id, _fixture2 = _seed(root)
    monkeypatch.setattr(cli, "run_gh", _gh_state("OPEN", []))
    monkeypatch.setattr(end_review, "layer_cell", _fake_layer_cell([]))

    def _standards_fails():
        raise implement.AgentFailed(
            "standards broke", attempt=_turn("", session_id="s-fail2", cost=0.02)
        )

    handlers = {
        "spec": lambda: _turn(_output_block([]), session_id="s-ok2", cost=0.01),
        "standards": _standards_fails,
    }
    monkeypatch.setattr(implement, "run_agent", _lens_agent(handlers, []))
    monkeypatch.chdir(work)
    assert cli.main(["--home", str(home), "review", str(task_id), "--repo", "."]) == 2

    # 3. `end_review.layer_cell` itself raises. The review file records an
    # error for both lenses, and no attempt opens.
    root = tmp_path / "case3"
    home, work, task_id, fixture = _seed(root)
    monkeypatch.setattr(cli, "run_gh", _gh_state("OPEN", []))
    monkeypatch.setattr(
        end_review,
        "layer_cell",
        _fake_layer_cell([], raises=RuntimeError("cell broke")),
    )

    def _unreached():
        raise AssertionError("the cell never opened, so no lens should run")

    monkeypatch.setattr(
        implement,
        "run_agent",
        _lens_agent({"spec": _unreached, "standards": _unreached}, []),
    )
    monkeypatch.chdir(work)
    assert cli.main(["--home", str(home), "review", str(task_id), "--repo", "."]) == 2

    ledger = Ledger(home / "ledger.db")
    assert ledger.attempts(task_id) == []
    ledger.close()

    out_dir = home / "batches" / "v0"
    review_file = out_dir / SPEC_ID / "commit-reviews" / f"{fixture.review_sha}.json"
    payload = json.loads(review_file.read_text())
    assert {r["lens"] for r in payload["reviews"]} == {"spec", "standards"}
    assert all(r["error"] is not None for r in payload["reviews"])

    # 4. `gh pr view` exits non-zero. No cell opens.
    root = tmp_path / "case4"
    home, work, task_id, _fixture4 = _seed(root)

    def _gh_fails(argv: list[str]):
        return subprocess.CompletedProcess(argv, 1, "", "gh is unauthenticated")

    monkeypatch.setattr(cli, "run_gh", _gh_fails)
    monkeypatch.setattr(end_review, "layer_cell", _fake_layer_cell([]))
    monkeypatch.setattr(
        implement,
        "run_agent",
        _lens_agent({"spec": _unreached, "standards": _unreached}, []),
    )
    monkeypatch.chdir(work)
    capsys.readouterr()
    assert cli.main(["--home", str(home), "review", str(task_id), "--repo", "."]) == 2
    # A failed `gh pr view` is a raise, not a decline: it must never print
    # the `review:` line a caller would read as one.
    printed = capsys.readouterr().out
    assert not printed.startswith("review:")
    assert printed.startswith("saffron: RuntimeError:")


def test_review_declines_each_task_it_cannot_read_before_any_cell_and_exits_two(
    monkeypatch, tmp_path, capsys
):
    from saffron import end_review

    fixture = _build_fixture(tmp_path)
    home = tmp_path / "home"
    work = fixture.work.resolve()
    mirror_path = cli._mirror_path(work, home)
    branch = f"saffron/{SPEC_ID}"

    cell_calls: list = []
    agent_calls: list = []
    monkeypatch.setattr(end_review, "layer_cell", _fake_layer_cell(cell_calls))

    def _never(*_a, **_k):
        raise AssertionError("an agent path ran for a decline")

    monkeypatch.setattr(implement, "run_agent", _never)

    ledger = Ledger(home / "ledger.db")

    unknown_task_id = 999_999

    task_no_pr = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch=branch,
        pr_url=None,
        pushed_sha=fixture.packaged_sha,
    )

    task_no_package = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch=branch,
        pr_url="https://github.com/o/r/pull/11",
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
        branch=branch,
        pr_url="https://github.com/o/r/pull/1",
        pushed_sha=fixture.packaged_sha,
        repo_id=other_repo_id,
    )

    pr_merged = "https://github.com/o/r/pull/2"
    task_merged = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch=branch,
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
        branch=branch,
        pr_url=pr_closed,
        pushed_sha=fixture.packaged_sha,
    )

    # The fetched head equals `pushed_sha`: no review commit yet.
    pr_no_range = "https://github.com/o/r/pull/4"
    _git(
        work,
        "push",
        "-q",
        "--force",
        "origin",
        f"{fixture.packaged_sha}:refs/heads/no-range",
    )
    task_no_range = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="no-range",
        pr_url=pr_no_range,
        pushed_sha=fixture.packaged_sha,
    )

    # A restacked copy with nothing on it: the head IS the rebased copy.
    # It lands on the moved default branch, so its sha differs, not its message.
    pr_bare_copy = "https://github.com/o/r/pull/5"
    rebase_src = tmp_path / "rebase-src"
    subprocess.run(
        ["git", "clone", "-q", fixture.origin_url, str(rebase_src)], check=True
    )
    _git(rebase_src, "config", "user.email", "t@example.com")
    _git(rebase_src, "config", "user.name", "T")
    _git(rebase_src, "checkout", "-q", "-b", "bare-copy-src", "origin/main")
    _git(rebase_src, "cherry-pick", fixture.packaged_sha)
    bare_copy_sha = _git(rebase_src, "rev-parse", "HEAD")
    assert bare_copy_sha != fixture.packaged_sha
    _git(rebase_src, "push", "-q", "origin", "HEAD:refs/heads/bare-copy")
    task_bare_copy = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="bare-copy",
        pr_url=pr_bare_copy,
        pushed_sha=fixture.packaged_sha,
    )

    # A head holding neither the packaged commit nor a commit carrying its
    # message: the branch reset to a fresh, unrelated commit.
    pr_unrelated = "https://github.com/o/r/pull/6"
    _git(rebase_src, "checkout", "-q", "-b", "unrelated", fixture.base_sha)
    (rebase_src / "unrelated.txt").write_text(
        "nothing to do with the packaged commit\n"
    )
    _git(rebase_src, "add", "-A")
    _git(rebase_src, "commit", "-q", "-m", "an unrelated commit")
    _git(rebase_src, "push", "-q", "origin", "HEAD:refs/heads/unrelated")
    task_unrelated = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch="unrelated",
        pr_url=pr_unrelated,
        pushed_sha=fixture.packaged_sha,
    )

    pr_bad_recorded = "https://github.com/o/r/pull/7"
    task_bad_recorded = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch=branch,
        pr_url=pr_bad_recorded,
        pushed_sha=fixture.packaged_sha,
    )
    ledger.record_spec_text(
        task_bad_recorded,
        origin="revision",
        spec_id=SPEC_ID,
        path=f".saffron/specs/{SPEC_ID}.md",
        text="not a valid spec at all",
    )

    pr_missing_spec = "https://github.com/o/r/pull/8"
    task_missing_spec = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.no_spec_sha,
        spec_sha="z" * 64,
        branch=branch,
        pr_url=pr_missing_spec,
        pushed_sha=fixture.packaged_sha,
    )

    pr_bad_sha = "https://github.com/o/r/pull/9"
    task_bad_sha = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha="0" * 64,
        branch=branch,
        pr_url=pr_bad_sha,
        pushed_sha=fixture.packaged_sha,
    )

    pr_no_token = "https://github.com/o/r/pull/10"
    task_no_token = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch=branch,
        pr_url=pr_no_token,
        pushed_sha=fixture.packaged_sha,
    )
    ledger.close()

    gh_states = {
        pr_merged: "MERGED",
        pr_closed: "CLOSED",
    }
    monkeypatch.setattr(cli, "run_gh", _gh_states(gh_states, []))
    monkeypatch.chdir(work)

    cases = [
        (unknown_task_id, "names no task"),
        (task_no_pr, "carries no pull request"),
        (task_no_package, "has no packaged head"),
        (task_foreign_repo, "belongs to another repo"),
        (task_merged, "is MERGED"),
        (task_closed, "is CLOSED"),
        (task_no_range, "is the packaged head"),
        (task_bare_copy, "is the packaged commit's rebased copy"),
        (task_unrelated, "holds no packaged commit"),
        (task_bad_recorded, "recorded text does not parse"),
        (task_missing_spec, "no spec file"),
        (task_bad_sha, "does not hash to"),
    ]
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "a-token")
    for task_id, fragment in cases:
        result = cli.main(["--home", str(home), "review", str(task_id), "--repo", "."])
        assert result == 2, (task_id, fragment)

    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    result = cli.main(
        ["--home", str(home), "review", str(task_no_token), "--repo", "."]
    )
    assert result == 2

    out = capsys.readouterr().out.splitlines()
    all_cases = [*cases, (task_no_token, "CLAUDE_CODE_OAUTH_TOKEN is unset")]
    assert len(out) == len(all_cases), out
    for line, (_task_id, fragment) in zip(out, all_cases, strict=True):
        assert line.startswith("review: "), line
        assert fragment in line, (fragment, line)

    assert cell_calls == []
    assert agent_calls == []


def test_review_frames_the_spec_body_as_review_commits_over_a_packaged_head(
    monkeypatch, tmp_path
):
    fixture = _build_fixture(tmp_path)
    home = tmp_path / "home"
    work = fixture.work.resolve()
    mirror_path = cli._mirror_path(work, home)
    pr_url = _pr_view()

    ledger = Ledger(home / "ledger.db")
    task_id = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch=f"saffron/{SPEC_ID}",
        pr_url=pr_url,
        pushed_sha=fixture.packaged_sha,
    )
    ledger.close()

    monkeypatch.setattr(cli, "run_gh", _gh_state("OPEN", []))

    from saffron import end_review

    monkeypatch.setattr(end_review, "layer_cell", _fake_layer_cell([]))

    agent_calls: list = []
    handlers = {
        "spec": lambda: _turn(_output_block([]), session_id="s1", cost=0.01),
        "standards": lambda: _turn(_output_block([]), session_id="s2", cost=0.01),
    }
    monkeypatch.setattr(implement, "run_agent", _lens_agent(handlers, agent_calls))

    spec_text_before = (
        work.resolve() / ".saffron" / "specs" / SPEC_FILENAME
    ).read_text()

    monkeypatch.chdir(work)
    result = cli.main(["--home", str(home), "review", str(task_id), "--repo", "."])
    assert result == 0

    assert len(agent_calls) == 2
    for call in agent_calls:
        prompt = call["options"]["system_prompt"]
        heading = "## The spec"
        start = prompt.index(heading) + len(heading)
        marker = "## Acceptance criteria"
        end = prompt.index(marker, start)
        spec_slice = prompt[start:end]
        assert fixture.packaged_sha in spec_slice
        assert fixture.review_sha in spec_slice
        assert fixture.base_sha not in spec_slice

    # Neither the spec file nor the recorded texts moved.
    spec_path = work.resolve() / ".saffron" / "specs" / SPEC_FILENAME
    assert spec_path.read_text() == spec_text_before
    ledger = Ledger(home / "ledger.db")
    assert ledger.spec_text(task_id) is None
    ledger.close()


def test_review_stopped_by_sigterm_tears_its_cell_down_and_exits_143(
    monkeypatch, tmp_path
):
    fixture = _build_fixture(tmp_path)
    home = tmp_path / "home"
    work = fixture.work.resolve()
    mirror_path = cli._mirror_path(work, home)
    pr_url = _pr_view()

    ledger = Ledger(home / "ledger.db")
    task_id = _seed_task(
        ledger,
        origin_url=fixture.origin_url,
        mirror_path=mirror_path,
        base_sha=fixture.base_sha,
        spec_sha=fixture.spec_sha,
        branch=f"saffron/{SPEC_ID}",
        pr_url=pr_url,
        pushed_sha=fixture.packaged_sha,
    )
    ledger.close()

    monkeypatch.setattr(cli, "run_gh", _gh_state("OPEN", []))

    from saffron import end_review

    cell_calls: list = []
    monkeypatch.setattr(end_review, "layer_cell", _fake_layer_cell(cell_calls))

    def _sigtermed_turn(container, *, prompt, options, **kwargs):
        os.kill(os.getpid(), signal.SIGTERM)
        raise AssertionError("SIGTERM did not interrupt the turn")

    monkeypatch.setattr(implement, "run_agent", _sigtermed_turn)

    heard: list[int] = []

    def _record(signum: int, _frame: object) -> None:
        heard.append(signum)

    outer_previous = signal.signal(signal.SIGTERM, _record)
    try:
        monkeypatch.chdir(work)
        try:
            result = cli.main(
                ["--home", str(home), "review", str(task_id), "--repo", "."]
            )
        except BaseException as exc:  # a leak fails this one call, not the test
            result = exc
        restored = signal.getsignal(signal.SIGTERM)
    finally:
        signal.signal(signal.SIGTERM, outer_previous)

    assert result == 143
    assert heard == []
    assert restored == _record
    assert cell_calls and cell_calls[0]["exited"] is True
