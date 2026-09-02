"""Saffron's own gates satisfy the contract they are declared against.

This file is the §2.1 boundary test in miniature: it exercises .saffron/ and
imports nothing from saffron/ except the contract parser.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from saffron.gates.contract import parse_gate_json
from saffron.repos.policy import load_policy

REPO = Path(__file__).resolve().parent.parent
GATES = REPO / ".saffron" / "gates"


def test_the_policy_parses():
    policy, _ = load_policy(REPO)
    assert set(policy.gates) == {"format", "lint", "types", "tests", "shacl"}


def test_the_type_checker_override_is_scoped_to_the_one_file_that_needs_it():
    """`unresolved-import = "ignore"` is load-bearing — the host is forbidden to
    import the Agent SDK (§2.1) and the cell image installs it where it is used
    — and it is the one rule in this repo turned off rather than satisfied.
    `agent_runner.py` runs inside the cell where nothing else type-checks it, so
    a widened `include` would let a typo'd import there go unreported."""
    config = tomllib.loads((REPO / "pyproject.toml").read_text())
    (override,) = config["tool"]["ty"]["overrides"]
    assert override["include"] == ["images/agent_runner.py"]
    assert override["rules"] == {"unresolved-import": "ignore"}


def test_no_gate_script_shadows_a_stdlib_module():
    """python puts a script's own directory on `sys.path[0]`, so a `types.py`
    beside the gates shadowed the stdlib `types` that every `import json` and
    `import subprocess` reaches through. Measured: it crashed under the pyenv
    interpreter and survived under the venv's, writing nothing to stdout —
    which is indistinguishable from a gate that never ran (§5.4)."""
    shadowed = {p.stem for p in GATES.glob("*.py")} & set(sys.stdlib_module_names)
    assert not shadowed, f"gate scripts shadow stdlib modules: {sorted(shadowed)}"


def test_types_names_its_tool_and_passes_on_a_clean_tree():
    """Invoked directly rather than through `run_gate`, for the reason the
    ruff gates state below: `_gate_env` strips the venv that is this repo's
    own declared toolchain."""
    done = subprocess.run(
        [str(GATES / "types")], cwd=REPO, capture_output=True, text=True, timeout=300
    )
    result = parse_gate_json(done.stdout, expected_gate="types")
    assert result.status == "pass", result.summary
    assert result.tool and result.tool.startswith("ty ")


def test_types_fails_on_code_ty_rejects(tmp_path):
    """A gate that has only ever passed is not known to be a gate."""
    (tmp_path / "bad.py").write_text("def f(x: int) -> str:\n    return x\n")
    done = subprocess.run(
        [str(GATES / "types")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=300,
    )
    result = parse_gate_json(done.stdout, expected_gate="types")
    assert result.status == "fail", result.summary
    assert len(result.failures) == 1
    assert result.failures[0].file.endswith("bad.py")
    assert result.failures[0].code == "invalid-return-type"
    assert result.failures[0].line == 2


def test_types_works_in_a_tree_that_has_no_venv(tmp_path):
    """A cell's worktree is a fresh `git init`/fetch/checkout into a volume and
    `.venv` is gitignored, so it is never there. A configured
    `environment.python` that does not resolve is a hard ty failure — exit 2,
    nothing on stdout — which this gate correctly calls `error`, and `error`
    aborts the attempt and is charged to nobody (§5.4). A blocking gate that
    can never run is the same defect as one that can never fail.

    The repo's own config, in a tree shaped like a cell's: neither of the other
    tests exercises that pair — one runs at `REPO`, which has a `.venv`, and
    the rest in a `tmp_path` with no config at all.
    """
    (tmp_path / "pyproject.toml").write_text((REPO / "pyproject.toml").read_text())
    (tmp_path / "bad.py").write_text("def f(x: int) -> str:\n    return x\n")
    done = subprocess.run(
        [str(GATES / "types")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=300,
    )
    result = parse_gate_json(done.stdout, expected_gate="types")
    assert result.status == "fail", result.summary


def _stub_ty(tmp_path, version_body: str, check_body: str = "exit 0") -> dict[str, str]:
    """A `ty` on PATH whose version no string literal in the gate could guess."""
    stub = tmp_path / "bin"
    stub.mkdir()
    (stub / "ty").write_text(
        f'#!/bin/sh\ncase "$1" in\n  --version) {version_body} ;;\n'
        f"  *) {check_body} ;;\nesac\n"
    )
    (stub / "ty").chmod(0o755)
    return {**os.environ, "PATH": f"{stub}:{os.environ['PATH']}"}


def test_types_reports_the_version_the_tool_printed_not_a_literal(tmp_path):
    """The invariant `tool` exists for: obtained *by executing* the tool
    (§5.4, Appendix H). Asserting the string starts with "ty" cannot tell an
    executed version from a literal in the gate."""
    env = _stub_ty(tmp_path, 'echo "ty 9.9.9-stub"')
    done = subprocess.run(
        [str(GATES / "types")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=300,
        env=env,
    )
    result = parse_gate_json(done.stdout, expected_gate="types")
    assert result.tool == "ty 9.9.9-stub"


def test_types_errors_when_its_tool_runs_and_reports_no_version(tmp_path):
    """A tool that runs and identifies nothing cannot produce the field that
    separates a gate that ran from one that did not, so it is `error`."""
    env = _stub_ty(tmp_path, "exit 0")
    done = subprocess.run(
        [str(GATES / "types")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=300,
        env=env,
    )
    result = parse_gate_json(done.stdout, expected_gate="types")
    assert result.status == "error"
    assert "no version" in result.summary


def test_types_errors_when_ty_exits_beyond_pass_or_fail(tmp_path):
    """ty exits 0 clean and 1 on diagnostics. Anything else is ty itself
    failing — an unresolvable configured environment, an unreadable file — and
    that is charged to nobody, not read as a verdict on the repo's code.

    The stub prints a well-formed diagnostic and a count that matches it, so
    only the exit code can distinguish this from an ordinary `fail` — with an
    empty stdout the count guard fires instead and the test passes without
    ever exercising the rule it names."""
    env = _stub_ty(
        tmp_path,
        'echo "ty 1.0.0"',
        check_body='echo "a.py:1:1: error[bad] nope"; echo "Found 1 diagnostic"; '
        "exit 2",
    )
    done = subprocess.run(
        [str(GATES / "types")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=300,
        env=env,
    )
    result = parse_gate_json(done.stdout, expected_gate="types")
    assert result.status == "error", result.summary


def test_types_errors_when_it_parses_fewer_diagnostics_than_ty_counted(tmp_path):
    """§5.4: partial results are not results. ty reports diagnostics this
    parser cannot key — one carrying no line, a message shape that moved — and
    a dropped failure is both a smaller repair target than the real one and a
    failure the baseline subtraction can never count as new."""
    env = _stub_ty(
        tmp_path,
        'echo "ty 1.0.0"',
        check_body='echo "b.py: error[io] Failed to read file"; '
        'echo "Found 1 diagnostic"; exit 1',
    )
    done = subprocess.run(
        [str(GATES / "types")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=300,
        env=env,
    )
    result = parse_gate_json(done.stdout, expected_gate="types")
    assert result.status == "error", result.summary
    assert "parsed 0" in result.summary


def test_types_errors_rather_than_passes_when_output_will_not_parse(tmp_path):
    """ty has no JSON output, so the gate parses `concise` lines. A non-zero
    exit that yields no parsed diagnostic means the format moved under us —
    and silence is bit-for-bit a pass (§5.4)."""
    env = _stub_ty(tmp_path, 'echo "ty 1.0.0"', check_body='echo "surprise"; exit 1')
    done = subprocess.run(
        [str(GATES / "types")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=300,
        env=env,
    )
    result = parse_gate_json(done.stdout, expected_gate="types")
    assert result.status == "error", result.summary
    assert result.tool == "ty 1.0.0", "a parse failure is not a reason to drop the tool"


@pytest.mark.parametrize("name", ["format", "lint"])
def test_the_fast_gates_name_their_tool_and_pass_on_a_clean_tree(name):
    """The subject is the gate's own output, not how the host resolves a PATH.

    Invoked directly rather than through `run_gate`, whose `_gate_env` strips
    Saffron's venv so a gate finds the *operator's* toolchain rather than
    Saffron's. That is right for every target repo and wrong when the target
    repo is Saffron: the stripped venv is then also the repo's own declared
    toolchain, so routing this test through `run_gate` made it assert against
    whichever ruff happened to be on the operator's global PATH — or none.
    (Cells are not involved: `_gate_env` reaches only `LocalExecutor`;
    `CellExecutor` execs through `cell_runtime.exec_`, which takes no env.)
    `tests/test_runner.py` owns the env-handling; this file owns the contract.
    """
    done = subprocess.run(
        [str(GATES / name)], cwd=REPO, capture_output=True, text=True, timeout=120
    )
    result = parse_gate_json(done.stdout, expected_gate=name)
    assert result.status == "pass", result.summary
    assert result.tool and result.tool.startswith("ruff")


def test_a_red_run_is_a_failure_even_when_a_test_is_named_for_a_crash(tmp_path):
    """`-q` echoes node ids in its FAILED lines, so keying the worker-crash
    check on "worker" and "crashed" anywhere in the output turned every red run
    in such a repo into an aborted gate — and an aborted gate is never charged
    to the task, so the failures it caused were never shown to it (§5.4)."""
    (tmp_path / "test_worker_crashed.py").write_text(
        "def test_worker_crashed():\n    assert False\n"
    )
    done = subprocess.run(
        [str(GATES / "tests")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    result = parse_gate_json(done.stdout, expected_gate="tests")
    assert result.status == "fail", result.summary
    assert result.failures


def test_shacl_names_its_tool_and_passes_on_this_repos_graphs():
    """pyshacl prints its version on stderr, so reading stdout alone produced a
    passing gate with `tool: ""` — a gate that ran and a gate that did not,
    reported identically (§5.4, Appendix H)."""
    done = subprocess.run(
        [str(GATES / "shacl")], cwd=REPO, capture_output=True, text=True, timeout=120
    )
    result = parse_gate_json(done.stdout, expected_gate="shacl")
    assert result.status == "pass", result.summary
    assert result.tool and "PySHACL" in result.tool


def test_shacl_fails_on_a_graph_its_shapes_reject(tmp_path):
    """A gate that has only ever passed is not known to be a gate. The subject
    is a repo of its own, because the gate reads `git ls-files` — validating the
    working tree would have walked `.venv` and judged pyshacl's own asset graphs
    as though this repo owned them, which a cell's venv at /opt/venv could not
    reproduce."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "ontology" / "shapes").mkdir(parents=True)
    (tmp_path / "ontology" / "shapes" / "s.ttl").write_text(
        "@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
        "@prefix ex: <https://example.invalid/#> .\n"
        "ex:Shape a sh:NodeShape ; sh:targetClass ex:Thing ;\n"
        "    sh:property [ sh:path ex:name ; sh:minCount 1 ] .\n"
    )
    (tmp_path / "ontology" / "broken.ttl").write_text(
        "@prefix ex: <https://example.invalid/#> .\nex:one a ex:Thing .\n"
    )
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)

    done = subprocess.run(
        [str(GATES / "shacl")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    result = parse_gate_json(done.stdout, expected_gate="shacl")
    assert result.status == "fail", result.summary
    assert len(result.failures) == 1
    assert result.failures[0].file == "ontology/broken.ttl"


def test_shacl_errors_rather_than_passes_when_a_graph_will_not_parse(tmp_path):
    """A graph that cannot be read produced no violations, and no violations is
    bit-for-bit a pass. `error` is the gate itself breaking and is charged to
    nobody (§5.4)."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "ontology" / "shapes").mkdir(parents=True)
    (tmp_path / "ontology" / "shapes" / "s.ttl").write_text(
        "@prefix sh: <http://www.w3.org/ns/shacl#> .\nex:Shape a sh:NodeShape .\n"
    )
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)

    done = subprocess.run(
        [str(GATES / "shacl")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    result = parse_gate_json(done.stdout, expected_gate="shacl")
    assert result.status == "error", result.summary


def _stub_pyshacl(tmp_path, body: str) -> dict[str, str]:
    """A `pyshacl` on PATH that this repo's own venv cannot supply."""
    stub = tmp_path / "bin"
    stub.mkdir()
    (stub / "pyshacl").write_text(f"#!/bin/sh\n{body}\n")
    (stub / "pyshacl").chmod(0o755)
    return {**os.environ, "PATH": f"{stub}:{os.environ['PATH']}"}


def test_shacl_reports_the_version_the_tool_printed_not_a_literal(tmp_path):
    """The invariant `tool` exists for: it must be obtained *by executing* the
    tool (§5.4, Appendix H). Asserting that the string contains "PySHACL" cannot
    tell an executed version from a string literal in the gate — replacing the
    probe with a hardcoded identifier passed that test. This one puts a version
    on PATH that no literal could have guessed."""
    env = _stub_pyshacl(tmp_path, 'echo "PySHACL Version: 9.9.9-stub" >&2')
    done = subprocess.run(
        [str(GATES / "shacl")],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    result = parse_gate_json(done.stdout, expected_gate="shacl")
    assert result.tool == "PySHACL Version: 9.9.9-stub"


def test_shacl_errors_when_its_tool_runs_and_reports_no_version(tmp_path):
    """A tool that runs and identifies nothing cannot produce the field that
    separates a gate that ran from one that did not, so it is `error`. The guard
    was unreachable as first written: an empty result indexed `splitlines()[0]`
    and raised before the check it was written for."""
    env = _stub_pyshacl(tmp_path, "exit 0")
    done = subprocess.run(
        [str(GATES / "shacl")],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    result = parse_gate_json(done.stdout, expected_gate="shacl")
    assert result.status == "error"
    assert "no version" in result.summary


def test_shacl_errors_on_an_unparseable_data_graph_beside_valid_shapes(tmp_path):
    """The realistic shape of the failure: the shapes are fine and one graph is
    not. An earlier version of this test broke the *shapes* file, which is the
    only case where a `NameError` from the same block would also read as
    `error`."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "ontology" / "shapes").mkdir(parents=True)
    (tmp_path / "ontology" / "shapes" / "s.ttl").write_text(
        "@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
        "@prefix ex: <https://example.invalid/#> .\n"
        "ex:Shape a sh:NodeShape ; sh:targetClass ex:Thing .\n"
    )
    (tmp_path / "ontology" / "torn.ttl").write_text("@prefix ex: <https://exa")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)

    done = subprocess.run(
        [str(GATES / "shacl")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    result = parse_gate_json(done.stdout, expected_gate="shacl")
    assert result.status == "error", result.summary
    assert result.tool, "a parse failure is not a reason to drop the tool identifier"
