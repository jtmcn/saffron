"""Re-verification against a real cell. Needs the images CLAUDE.md names:

container build -t saffron/cell-base:python -f images/cell-base.python.Dockerfile .
"""

from pathlib import Path

import pytest

from saffron.phases.package import reverify
from saffron.repos import image as repo_image
from saffron.repos import mirror as mirror_ops
from saffron.repos.policy import load_policy

pytestmark = pytest.mark.cell

SAFFRON_ROOT = Path(__file__).resolve().parent.parent


def test_reverification_runs_the_suite_inside_a_cell(tmp_path, capsys):
    """The gates come from the host-side export, mounted read-only; running them
    on the host would be the control plane executing model-authored code (§2).

    Asserts `reverify` completes and prints both suites — a direct `print`,
    per `events.FINDINGS[1]`, not routed through any callback the caller
    supplies. The empty-diff assertion below is not vacuous: `reverify`
    raises `PackageError` if either suite has an errored gate
    (`aborted_gates`), so two silently-broken suites cannot net to
    `new_failures == []` here — only two suites that both actually ran can
    produce this result.
    """
    mirror = mirror_ops.ensure_mirror(SAFFRON_ROOT, tmp_path / "m.git")
    head = mirror_ops._git(mirror, "rev-parse", "HEAD")
    policy, _ = load_policy(SAFFRON_ROOT)
    tag = repo_image.build_cell_image(SAFFRON_ROOT)

    # Same sha for both suites: the subtraction must then be empty, which is
    # the invariant worth pinning — a non-empty result here would mean the
    # gates are not deterministic, not that the packaged commit is bad.
    new_failures, head_results = reverify(
        mirror=mirror,
        packaged_sha=head,
        new_base_sha=head,
        policy=policy,
        gates_dir=mirror_ops.export_saffron_dir(mirror, head, tmp_path / "gates"),
        image=tag,
    )
    assert new_failures == []
    # The head results are returned, not just the subtraction: the body's gate
    # table has to show the run its own sentence claims.
    assert head_results and all(r.status != "error" for r in head_results)
    printed = capsys.readouterr().out
    assert "re-verify: baseline suite" in printed
    assert "re-verify: head suite" in printed


def test_the_reverification_cell_carries_no_credential(tmp_path, monkeypatch):
    """It runs gates and nothing else: no agent, no credential, no egress.

    Probed at the call rather than by reading source: a cell started without an
    explicit network joins the runtime's default one with full egress, and
    every control the caller ran then applies to some other container
    (Appendix I). `runtime.create_network` hardcodes --internal, so what is
    worth pinning here is that a network is passed at all and that `env` holds
    the repo's declared gate env and nothing more — CLAUDE_CODE_OAUTH_TOKEN
    must not reach a cell that only runs gates.
    """
    seen = {}

    def spy(**kwargs):
        seen.update(kwargs)
        raise RuntimeError("stop after the arguments are captured")

    monkeypatch.setattr("saffron.cell.worktree.prepare_worktree", spy)
    mirror = mirror_ops.ensure_mirror(SAFFRON_ROOT, tmp_path / "m.git")
    # Marked, because this repo's own `thread_env` is empty: against `{}` the
    # equality below passes whether the declared env was forwarded or dropped,
    # and would not notice `cell_env` being wired in here by mistake.
    loaded, _ = load_policy(SAFFRON_ROOT)
    policy = loaded.model_copy(update={"thread_env": {"SAFFRON_GATE_ENV": "1"}})
    with pytest.raises(RuntimeError):
        reverify(
            mirror=mirror,
            packaged_sha="a" * 40,
            new_base_sha="a" * 40,
            policy=policy,
            gates_dir=tmp_path / "gates",
            image="unused",
        )
    # Exact: the declared gate env and nothing else. `cell_env` would add
    # CLAUDE_CONFIG_DIR and the proxy variables, and fail here.
    assert seen["env"] == {"SAFFRON_GATE_ENV": "1"}
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in seen["env"]
    assert seen["network"]
    # The gates the cell runs are the host's export, never the applied tree's.
    assert seen["gates_dir"] == tmp_path / "gates"
