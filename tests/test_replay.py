import json
import subprocess
from pathlib import Path

import pytest

from saffron.ledger import Ledger
from saffron.replay import replay

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
    repo = tmp_path / "target"
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
    (repo / "src" / "a.py").write_text("\n".join(f"pad_{i} = {i}" for i in range(30))
                                       + "\nx = 1\ntoo_long = 2\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "the change")

    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "--no-ff", "-q", "feature", "-m",
        "Merge pull request #7 from someone/feature")
    return repo


@pytest.fixture
def ledger(tmp_path):
    made = Ledger(tmp_path / "ledger.db")
    yield made
    made.close()


def test_replay_produces_a_queue_line(target, ledger, tmp_path):
    line = replay(target, 7, ledger=ledger, out_dir=tmp_path / "out",
                  mirrors_dir=tmp_path / "mirrors")
    assert line.spec_id == "SY-9001"
    assert line.repo == "target"
    assert line.state == "READY_FOR_REVIEW"
    assert line.added == 30


def test_the_shifted_pre_existing_failure_is_not_reported_as_new(target, ledger, tmp_path):
    """End to end, on a real diff, with a real gate. The whole point of v0."""
    replay(target, 7, ledger=ledger, out_dir=tmp_path / "out",
           mirrors_dir=tmp_path / "mirrors")
    body = (tmp_path / "out" / "SY-9001" / "pr_body.md").read_text()
    assert "No new failures" in body
    assert "E501" not in body


def test_both_suites_are_recorded_against_the_right_owner(target, ledger, tmp_path):
    replay(target, 7, ledger=ledger, out_dir=tmp_path / "out",
           mirrors_dir=tmp_path / "mirrors")
    (run,) = list(ledger.queue_lines())
    baseline = ledger.baseline_results(1)
    assert {r.gate for r in baseline} == {"lint", "tests", "scope"}
    assert {r.gate for r in ledger.task_results(run["task_id"])} == {"lint", "tests", "scope"}


def test_the_scope_gate_runs_at_head_and_not_only_in_theory(target, ledger, tmp_path):
    replay(target, 7, ledger=ledger, out_dir=tmp_path / "out",
           mirrors_dir=tmp_path / "mirrors")
    (run,) = list(ledger.queue_lines())
    scope = [r for r in ledger.task_results(run["task_id"]) if r.gate == "scope"]
    assert scope[0].status == "pass"


def test_a_diff_outside_touches_fails_scope(target, ledger, tmp_path):
    spec = target / ".saffron" / "specs" / "SY-9001-silent-success.md"
    spec.write_text(SPEC.replace("  - src/**", "  - docs/**"))
    git(target, "add", "-A")
    git(target, "commit", "-qm", "narrow the touches")

    line = replay(target, 7, ledger=ledger, out_dir=tmp_path / "out",
                  mirrors_dir=tmp_path / "mirrors")
    body = (tmp_path / "out" / "SY-9001" / "pr_body.md").read_text()
    assert "| `scope` | `fail` |" in body
    assert "src/a.py" in body
    assert line.state == "EXHAUSTED"


def test_a_new_failure_at_head_is_reported(target, ledger, tmp_path):
    (target / ".saffron" / "gates" / "tests").write_text(
        '#!/bin/sh\n'
        'if [ -f src/a.py ] && grep -q pad_0 src/a.py; then\n'
        '  echo \'{"gate":"tests","status":"fail","summary":"1 failed",'
        '"failures":[{"file":"t/x.py","line":3,"code":"assert","message":"boom"}]}\'\n'
        'else\n'
        '  echo \'{"gate":"tests","status":"pass","summary":"12 passed"}\'\n'
        'fi\n'
    )
    (target / ".saffron" / "gates" / "tests").chmod(0o755)
    git(target, "add", "-A")
    git(target, "commit", "-qm", "gate that fails only at head")

    replay(target, 7, ledger=ledger, out_dir=tmp_path / "out",
           mirrors_dir=tmp_path / "mirrors")
    body = (tmp_path / "out" / "SY-9001" / "pr_body.md").read_text()
    assert "### New failures" in body
    assert "t/x.py:3" in body


def test_an_index_is_written(target, ledger, tmp_path):
    replay(target, 7, ledger=ledger, out_dir=tmp_path / "out",
           mirrors_dir=tmp_path / "mirrors")
    assert "SY-9001" in (tmp_path / "out" / "index.html").read_text()


def test_worktrees_are_cleaned_up(target, ledger, tmp_path):
    replay(target, 7, ledger=ledger, out_dir=tmp_path / "out",
           mirrors_dir=tmp_path / "mirrors")
    worktrees = list((tmp_path / "mirrors").glob("**/wt-*"))
    assert worktrees == []


def test_the_gate_results_are_kept_as_json_in_the_batch_tree(target, ledger, tmp_path):
    replay(target, 7, ledger=ledger, out_dir=tmp_path / "out",
           mirrors_dir=tmp_path / "mirrors")
    recorded = json.loads((tmp_path / "out" / "SY-9001" / "head.json").read_text())
    assert {r["gate"] for r in recorded} == {"lint", "tests", "scope"}


def test_a_corrupt_lines_json_does_not_wedge_the_replay(target, ledger, tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "lines.json").write_text("{not valid json")

    line = replay(target, 7, ledger=ledger, out_dir=out_dir,
                  mirrors_dir=tmp_path / "mirrors")

    assert line.spec_id == "SY-9001"
    assert "SY-9001" in (out_dir / "index.html").read_text()
    rewritten = json.loads((out_dir / "lines.json").read_text())
    assert [item["spec_id"] for item in rewritten] == ["SY-9001"]


def test_a_lines_json_of_the_wrong_shape_does_not_wedge_the_replay(target, ledger, tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    # Well-formed JSON, but not a list of QueueLine-shaped objects.
    (out_dir / "lines.json").write_text(json.dumps({"unexpected": "shape"}))

    line = replay(target, 7, ledger=ledger, out_dir=out_dir,
                  mirrors_dir=tmp_path / "mirrors")

    assert line.spec_id == "SY-9001"
    assert "SY-9001" in (out_dir / "index.html").read_text()
    rewritten = json.loads((out_dir / "lines.json").read_text())
    assert [item["spec_id"] for item in rewritten] == ["SY-9001"]
