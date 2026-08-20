import json
import subprocess
from pathlib import Path

import pytest

from saffron.ledger import Ledger
from saffron.replay import replay
from saffron.repos import mirror as git_mirror

SPEC = """---
id: SY-9001
title: Stop the silent success
type: bug
touches:
  - src/**
---

## Acceptance criteria
- [ ] Ingest raises on zero-row responses
"""

# A lint gate whose one pre-existing failure moves down the file at head. If
# the identity includes `line`, replay reports it as new and this test fails.
#
# Note it reads `src/a.py` relative to its cwd — the worktree the host put it
# in — and never cds anywhere. That is the contract every real gate follows.
LINT_GATE = r"""#!/bin/sh
LINE=$(grep -n too_long src/a.py | cut -d: -f1)
printf '{"gate":"lint","status":"fail","summary":"1 error","failures":[{"file":"src/a.py","line":%s,"code":"E501","message":"line too long"}]}\n' "$LINE"
"""

TESTS_GATE_PASSES = """#!/bin/sh
echo '{"gate":"tests","status":"pass","summary":"12 passed"}'
"""

POLICY = """
gates:
  lint:  { blocking: true }
  tests: { blocking: true }
"""


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def target(tmp_path):
    """A target repo with one merged pull request and real .saffron/ gates."""
    return make_target(tmp_path / "target")


def make_target(repo: Path):
    (repo / "src").mkdir(parents=True)
    gates = repo / ".saffron" / "gates"
    gates.mkdir(parents=True)
    (repo / ".saffron" / "policy.yaml").write_text(POLICY)
    (gates / "lint").write_text(LINT_GATE)
    (gates / "tests").write_text(TESTS_GATE_PASSES)
    for name in ("lint", "tests"):
        (gates / name).chmod(0o755)
    (repo / ".saffron" / "specs").mkdir()
    (repo / ".saffron" / "specs" / "SY-9001-silent-success.md").write_text(SPEC)

    (repo / "src" / "a.py").write_text("x = 1\ntoo_long = 2\n")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "Test")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")

    git(repo, "checkout", "-qb", "feature")
    # Thirty inserted lines above the pre-existing failure.
    (repo / "src" / "a.py").write_text(
        "\n".join(f"pad_{i} = {i}" for i in range(30)) + "\nx = 1\ntoo_long = 2\n"
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "the change")

    git(repo, "checkout", "-q", "main")
    git(
        repo,
        "merge",
        "--no-ff",
        "-q",
        "feature",
        "-m",
        "Merge pull request #7 from someone/feature",
    )
    return repo


@pytest.fixture
def ledger(tmp_path):
    made = Ledger(tmp_path / "ledger.db")
    yield made
    made.close()


def test_replay_produces_a_queue_line(target, ledger, tmp_path):
    line = replay(
        target,
        7,
        ledger=ledger,
        out_dir=tmp_path / "out",
        mirrors_dir=tmp_path / "mirrors",
    )
    assert line.spec_id == "SY-9001"
    assert line.repo == "target"
    assert line.state == "READY_FOR_REVIEW"
    assert line.added == 30


def test_the_shifted_pre_existing_failure_is_not_reported_as_new(
    target, ledger, tmp_path
):
    """End to end, on a real diff, with a real gate. The whole point of v0."""
    replay(
        target,
        7,
        ledger=ledger,
        out_dir=tmp_path / "out",
        mirrors_dir=tmp_path / "mirrors",
    )
    body = (tmp_path / "out" / "SY-9001" / "pr_body.md").read_text()
    assert "No new failures" in body
    assert "E501" not in body


def test_both_suites_are_recorded_against_the_right_owner(target, ledger, tmp_path):
    replay(
        target,
        7,
        ledger=ledger,
        out_dir=tmp_path / "out",
        mirrors_dir=tmp_path / "mirrors",
    )
    (run,) = list(ledger.queue_lines())
    baseline = ledger.baseline_results(1)
    assert {r.gate for r in baseline} == {"lint", "tests", "scope"}
    assert {r.gate for r in ledger.task_results(run["task_id"])} == {
        "lint",
        "tests",
        "scope",
    }


def test_the_scope_gate_runs_at_head_and_not_only_in_theory(target, ledger, tmp_path):
    replay(
        target,
        7,
        ledger=ledger,
        out_dir=tmp_path / "out",
        mirrors_dir=tmp_path / "mirrors",
    )
    (run,) = list(ledger.queue_lines())
    scope = [r for r in ledger.task_results(run["task_id"]) if r.gate == "scope"]
    assert scope[0].status == "pass"


def test_a_diff_outside_touches_fails_scope(target, ledger, tmp_path):
    spec = target / ".saffron" / "specs" / "SY-9001-silent-success.md"
    spec.write_text(SPEC.replace("  - src/**", "  - docs/**"))
    git(target, "add", "-A")
    git(target, "commit", "-qm", "narrow the touches")

    line = replay(
        target,
        7,
        ledger=ledger,
        out_dir=tmp_path / "out",
        mirrors_dir=tmp_path / "mirrors",
    )
    body = (tmp_path / "out" / "SY-9001" / "pr_body.md").read_text()
    assert "| `scope` | `fail` |" in body
    assert "src/a.py" in body
    assert line.state == "EXHAUSTED"


def test_a_new_failure_at_head_is_reported(target, ledger, tmp_path):
    (target / ".saffron" / "gates" / "tests").write_text(
        "#!/bin/sh\n"
        "if [ -f src/a.py ] && grep -q pad_0 src/a.py; then\n"
        '  echo \'{"gate":"tests","status":"fail","summary":"1 failed",'
        '"failures":[{"file":"t/x.py","line":3,"code":"assert","message":"boom"}]}\'\n'
        "else\n"
        '  echo \'{"gate":"tests","status":"pass","summary":"12 passed"}\'\n'
        "fi\n"
    )
    (target / ".saffron" / "gates" / "tests").chmod(0o755)
    git(target, "add", "-A")
    git(target, "commit", "-qm", "gate that fails only at head")

    replay(
        target,
        7,
        ledger=ledger,
        out_dir=tmp_path / "out",
        mirrors_dir=tmp_path / "mirrors",
    )
    body = (tmp_path / "out" / "SY-9001" / "pr_body.md").read_text()
    assert "### New failures" in body
    assert "t/x.py:3" in body


def test_an_index_is_written(target, ledger, tmp_path):
    replay(
        target,
        7,
        ledger=ledger,
        out_dir=tmp_path / "out",
        mirrors_dir=tmp_path / "mirrors",
    )
    assert "SY-9001" in (tmp_path / "out" / "index.html").read_text()


def test_worktrees_are_cleaned_up(target, ledger, tmp_path):
    replay(
        target,
        7,
        ledger=ledger,
        out_dir=tmp_path / "out",
        mirrors_dir=tmp_path / "mirrors",
    )
    worktrees = list((tmp_path / "mirrors").glob("**/wt-*"))
    assert worktrees == []


def test_the_gate_results_are_kept_as_json_in_the_batch_tree(target, ledger, tmp_path):
    replay(
        target,
        7,
        ledger=ledger,
        out_dir=tmp_path / "out",
        mirrors_dir=tmp_path / "mirrors",
    )
    recorded = json.loads((tmp_path / "out" / "SY-9001" / "head.json").read_text())
    assert {r["gate"] for r in recorded} == {"lint", "tests", "scope"}


def test_a_corrupt_lines_json_does_not_wedge_the_replay(target, ledger, tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "lines.json").write_text("{not valid json")

    line = replay(
        target, 7, ledger=ledger, out_dir=out_dir, mirrors_dir=tmp_path / "mirrors"
    )

    assert line.spec_id == "SY-9001"
    assert "SY-9001" in (out_dir / "index.html").read_text()
    rewritten = json.loads((out_dir / "lines.json").read_text())
    assert [item["spec_id"] for item in rewritten] == ["SY-9001"]


def test_a_lines_json_of_the_wrong_shape_does_not_wedge_the_replay(
    target, ledger, tmp_path
):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    # Well-formed JSON, but not a list of QueueLine-shaped objects.
    (out_dir / "lines.json").write_text(json.dumps({"unexpected": "shape"}))

    line = replay(
        target, 7, ledger=ledger, out_dir=out_dir, mirrors_dir=tmp_path / "mirrors"
    )

    assert line.spec_id == "SY-9001"
    assert "SY-9001" in (out_dir / "index.html").read_text()
    rewritten = json.loads((out_dir / "lines.json").read_text())
    assert [item["spec_id"] for item in rewritten] == ["SY-9001"]


def test_an_errored_gate_never_reaches_a_green_terminal_state(target, ledger, tmp_path):
    """An errored gate contributes no failures, so a state read from new
    failures alone calls a suite that never ran `READY_FOR_REVIEW`."""
    (target / ".saffron" / "gates" / "tests").write_text(
        "#!/bin/sh\necho 'ModuleNotFoundError: No module named pytest' >&2\nexit 1\n"
    )
    (target / ".saffron" / "gates" / "tests").chmod(0o755)
    git(target, "add", "-A")
    git(target, "commit", "-qm", "a gate whose toolchain is gone")

    line = replay(
        target,
        7,
        ledger=ledger,
        out_dir=tmp_path / "out",
        mirrors_dir=tmp_path / "mirrors",
    )

    assert line.state == "EXHAUSTED"
    assert "errored: tests" in line.note


def test_a_gate_that_errored_at_base_says_so_rather_than_blaming_the_task(
    target, ledger, tmp_path
):
    """With no usable baseline, every head failure of that gate reads as new.
    The state is EXHAUSTED either way, but EXHAUSTED also means "this task
    broke things" — so the queue line has to name the missing baseline."""
    (target / ".saffron" / "gates" / "tests").write_text(
        "#!/bin/sh\n"
        "if grep -q pad_0 src/a.py; then\n"
        '  echo \'{"gate":"tests","status":"fail","summary":"1 failed",'
        '"failures":[{"file":"t/x.py","line":3,"code":"assert","message":"boom"}]}\'\n'
        "else\n"
        '  echo "ModuleNotFoundError: No module named pytest" >&2\n'
        "  exit 1\n"
        "fi\n"
    )
    (target / ".saffron" / "gates" / "tests").chmod(0o755)
    git(target, "add", "-A")
    git(target, "commit", "-qm", "a gate whose toolchain is only there at head")

    line = replay(
        target,
        7,
        ledger=ledger,
        out_dir=tmp_path / "out",
        mirrors_dir=tmp_path / "mirrors",
    )

    assert line.state == "EXHAUSTED"
    assert "errored at base: tests" in line.note


def test_two_repos_of_the_same_name_do_not_share_one_mirror(ledger, tmp_path):
    """Keyed on the directory name, the second replay would resolve its pull
    request against the first repo's history and never say so."""
    first = make_target(tmp_path / "a" / "target")
    second = make_target(tmp_path / "b" / "target")
    # A commit only the second repo has, so a shared mirror is visible in the diff.
    (second / "src" / "only_here.py").write_text("z = 3\n")
    git(second, "add", "-A")
    git(second, "commit", "-qm", "second repo only")

    mirrors = tmp_path / "mirrors"
    replay(first, 7, ledger=ledger, out_dir=tmp_path / "out", mirrors_dir=mirrors)
    replay(second, 7, ledger=ledger, out_dir=tmp_path / "out", mirrors_dir=mirrors)

    clones = sorted(mirrors.glob("*.git"))
    assert len(clones) == 2
    # Exactly one mirror carries the second repo's commit: neither fetched the
    # other's history.
    has_it = [c for c in clones if "only_here.py" in _ls_tree(c)]
    assert len(has_it) == 1


def _ls_tree(mirror):
    return subprocess.run(
        ["git", "-C", str(mirror), "ls-tree", "-r", "--name-only", "main"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_new_failures_survive_a_gate_that_errored_at_base(target, ledger, tmp_path):
    """One gate with no usable baseline does not erase what another gate
    reported — the queue line is the ten-second triage surface."""
    (target / ".saffron" / "gates" / "tests").write_text(
        "#!/bin/sh\n"
        "if grep -q pad_0 src/a.py; then\n"
        '  echo \'{"gate":"tests","status":"pass","summary":"12 passed"}\'\n'
        "else\n"
        '  echo "ModuleNotFoundError: No module named pytest" >&2\n'
        "  exit 1\n"
        "fi\n"
    )
    (target / ".saffron" / "gates" / "lint").write_text(
        "#!/bin/sh\n"
        "if grep -q pad_0 src/a.py; then\n"
        '  echo \'{"gate":"lint","status":"fail","summary":"1 error",'
        '"failures":[{"file":"src/a.py","line":1,"code":"E999","message":"new"}]}\'\n'
        "else\n"
        '  echo \'{"gate":"lint","status":"pass","summary":"clean"}\'\n'
        "fi\n"
    )
    for name in ("lint", "tests"):
        (target / ".saffron" / "gates" / name).chmod(0o755)
    git(target, "add", "-A")
    git(target, "commit", "-qm", "one gate errors at base, another fails at head")

    line = replay(
        target,
        7,
        ledger=ledger,
        out_dir=tmp_path / "out",
        mirrors_dir=tmp_path / "mirrors",
    )

    assert "errored at base: tests" in line.note
    assert "1 new in lint" in line.note


def test_two_repos_do_not_share_a_worktree_path(ledger, tmp_path, monkeypatch):
    """Both fixtures carry spec SY-9001. add_worktree deletes whatever sits at
    its path, so a path two repos can both claim is a live worktree deleted
    mid-gate the moment anything runs concurrently."""
    first = make_target(tmp_path / "a" / "target")
    second = make_target(tmp_path / "b" / "target")

    seen = []
    real = git_mirror.add_worktree
    monkeypatch.setattr(
        git_mirror,
        "add_worktree",
        lambda mirror, sha, dest: (seen.append(dest), real(mirror, sha, dest))[1],
    )

    mirrors = tmp_path / "mirrors"
    replay(first, 7, ledger=ledger, out_dir=tmp_path / "out", mirrors_dir=mirrors)
    boundary = len(seen)
    replay(second, 7, ledger=ledger, out_dir=tmp_path / "out", mirrors_dir=mirrors)

    assert boundary and len(seen) > boundary
    assert set(seen[:boundary]).isdisjoint(seen[boundary:])
