"""The vacuity probe's Gate-only cell, started as REVIEW starts it. Needs the
image CLAUDE.md names:

container build -t saffron/cell-base:python -f images/cell-base.python.Dockerfile .
"""

import subprocess
from pathlib import Path

import pytest

from saffron.agents.findings import Finding
from saffron.cell import session, worktree
from saffron.intake import Mutant
from saffron.phases.review import LensReview
from saffron.repos import image as repo_image
from saffron.repos import mirror as mirror_ops
from saffron.repos.policy import load_policy

pytestmark = pytest.mark.cell

# Reports from inside the cell which of three names its environment holds.
_TESTS_GATE = """#!/bin/sh
seen() { if [ -n "$(printenv "$1")" ]; then echo present; else echo absent; fi; }
printf '{"gate":"tests","status":"pass","tool":"%s","collected":["t::a"],"summary":"%s"}\\n' \\
  "$(python3 --version)" \\
  "ANTHROPIC_API_KEY=$(seen ANTHROPIC_API_KEY) CLAUDE_CODE_OAUTH_TOKEN=$(seen CLAUDE_CODE_OAUTH_TOKEN) SAFFRON_PROBE_MARK=$(seen SAFFRON_PROBE_MARK)"
"""

_POLICY = """gates:
  tests: { blocking: true }
integrity:
  test_paths: ["tests/**"]
thread_env:
  SAFFRON_PROBE_MARK: "1"
"""

_EXPECTED = (
    "ANTHROPIC_API_KEY=absent CLAUDE_CODE_OAUTH_TOKEN=absent SAFFRON_PROBE_MARK=present"
)


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    )
    return done.stdout.strip()


def _fixture_repo(root: Path) -> tuple[Path, str, str]:
    """A repo with its own image, policy and `tests` gate, and one commit of
    source on top of its base: the patch REVIEW would have probed."""
    repo = root / "probe-cell-origin"
    (repo / ".saffron" / "gates").mkdir(parents=True)
    (repo / "src").mkdir()
    (repo / ".saffron" / "Dockerfile").write_text("FROM saffron/cell-base:python\n")
    (repo / ".saffron" / "policy.yaml").write_text(_POLICY)
    gate = repo / ".saffron" / "gates" / "tests"
    gate.write_text(_TESTS_GATE)
    gate.chmod(0o755)
    (repo / "src" / "app.py").write_text("LIMIT = 1\n")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "src" / "app.py").write_text("LIMIT = 1\nif LIMIT < 0:\n    raise\n")
    _git(repo, "commit", "-qam", "the change under review")
    patch = subprocess.run(
        ["git", "diff", *worktree.DIFF_FLAGS, f"{base}..HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return repo, base, patch


def test_the_probe_cell_holds_the_declared_gate_env_and_no_host_credential(
    tmp_path, monkeypatch
):
    """`_probe_adequacy` runs the repo's `tests` gate as root over the
    implementer's code. Its cell carries the declared gate env and nothing
    from the host. The gate reports its own environment from inside, as
    CLAUDE.md asks of isolation tests (b-ce93aa). `SAFFRON_PROBE_MARK` is the
    control. A gate blind to its cell's env reports every name absent.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-host-key-must-not-reach")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "host-token-must-not-reach")
    repo, base, patch = _fixture_repo(tmp_path)
    repo_image.build_cell_image(repo)
    mirror = mirror_ops.ensure_mirror(repo, tmp_path / "m.git")
    policy, _ = load_policy(repo)
    gates_dir = mirror_ops.export_saffron_dir(mirror, base, tmp_path / "gates")
    spec = session.CellSpec(
        spec_id="SA-9123",
        spec_sha="0" * 40,
        branch="saffron/SA-9123",
        base_sha=base,
        touches=["src/app.py"],
        spec_type="bug",
        body="",
    )
    finding = Finding(
        lens="adequacy",
        severity="concern",
        file="src/app.py",
        line=2,
        claim="nothing tests the guard",
        anchored=True,
        probe=Mutant(file="src/app.py", find="if LIMIT < 0:", replace="if False:"),
    )
    created: set[str] = set()
    survived: list[str] = []

    entries = session._probe_adequacy(
        spec=spec,
        repo=repo,
        mirror=mirror,
        gates_dir=gates_dir,
        thread_env=policy.thread_env,
        test_paths=policy.integrity.test_paths,
        gates=policy.gate_executables(Path(worktree.GATES_MOUNT)),
        patch=patch,
        reviews=[LensReview(lens="adequacy", findings=[finding])],
        created=created,
        note=lambda step, ok, detail: survived.append(detail),
    )

    assert len(entries) == 1, entries
    entry = entries[0]
    # Both runs, the baseline and the one under the probe, answered from inside.
    assert entry["baseline_summary"] == _EXPECTED, entry
    assert entry["summary"] == _EXPECTED, entry
    assert entry["probe_verdict"] == "survived", entry
    assert survived == []
