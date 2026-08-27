"""Saffron's own gates satisfy the contract they are declared against.

This file is the §2.1 boundary test in miniature: it exercises .saffron/ and
imports nothing from saffron/ except the contract parser.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from saffron.gates.contract import parse_gate_json
from saffron.gates.runner import run_gate
from saffron.repos.policy import load_policy

REPO = Path(__file__).resolve().parent.parent
GATES = REPO / ".saffron" / "gates"


def test_the_policy_parses():
    policy, _ = load_policy(REPO)
    assert set(policy.gates) == {"format", "lint", "types", "tests", "shacl"}


def test_types_skips_because_saffron_declares_no_type_checker():
    result = run_gate("types", GATES / "types", REPO)
    assert result.status == "skip"


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
