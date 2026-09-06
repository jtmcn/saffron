"""Saffron's own gates satisfy the contract they are declared against.

This file is the §2.1 boundary test in miniature: it exercises .saffron/ and
imports nothing from saffron/ except what reads a repo's own declarations — the
contract parser, the policy loader, and the globber `integrity` judges paths
with. A reimplementation of that globber here would agree with itself and with
nothing that runs.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

from saffron.gates.contract import parse_gate_json
from saffron.gates.core.scope import matches
from saffron.repos.policy import load_policy

REPO = Path(__file__).resolve().parent.parent
GATES = REPO / ".saffron" / "gates"


def test_the_policy_parses():
    policy, _ = load_policy(REPO)
    assert set(policy.gates) == {
        "format",
        "lint",
        "types",
        "tests",
        "shacl",
        "structure",
    }


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


SGCONFIG = REPO / ".saffron" / "sgconfig.yml"


def _rule_files():
    """Every file ast-grep would load as a rule, which is not just `*.yml` at the
    top level: measured, a rule directory is walked recursively and `.yaml` is
    taken as readily as `.yml`. The gate counts them the same way, so a narrower
    list here would certify rules it never sees."""
    return sorted(
        p
        for p in (REPO / ".saffron" / "rules").rglob("*")
        if p.suffix in (".yml", ".yaml")
    )


def _covers(glob: str, language: str, tmp_path) -> int:
    """How many files in this repo a rule's path glob actually reaches.

    Asked of ast-grep rather than of `fnmatch` or `Path.glob`: the question is
    what *this* globber does, and a reimplementation that disagreed would pass
    while the rule it certifies covers nothing. The probe carries the one glob
    and a body matching every file of the language — `module` is the root node
    of a Python parse — so the count is the scope's reach and nothing else.
    """
    probe = tmp_path / glob.replace("/", "_").replace("*", "x")
    # exist_ok: two rules may share a scope, and the probe built for it is the
    # same probe. Without this the second one raises instead of reporting.
    (probe / "rules").mkdir(parents=True, exist_ok=True)
    (probe / "sgconfig.yml").write_text("ruleDirs:\n  - rules\n")
    (probe / "rules" / "probe.yml").write_text(
        yaml.safe_dump(
            {
                "id": "probe",
                "language": language,
                "severity": "error",
                "message": "probe",
                "files": [glob],
                "rule": {"kind": "module"},
            }
        )
    )
    done = subprocess.run(
        [
            "ast-grep",
            "scan",
            "-c",
            str(probe / "sgconfig.yml"),
            "--no-ignore",
            "hidden",
            "--json=compact",
            ".",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return len({m["file"] for m in json.loads(done.stdout)})


def test_every_rules_path_scope_still_reaches_a_file(tmp_path):
    """The gap the rule tests cannot close. `ast-grep test` runs rules against
    snippets, which have no paths, so a `files:` glob that has gone stale — the
    tree restructured to `src/saffron/`, a guarded file renamed — leaves the rule
    matching nothing and reporting green, with every snippet still passing.
    Measured: `files: ["src/saffron/**/*.py"]` reaches 0 files here.

    `ignores:` too. A stale exemption fails loudly rather than silently, but it
    names a file that is supposed to exist and is worth knowing has moved.
    """
    dead = []
    for rule_file in _rule_files():
        rule = yaml.safe_load(rule_file.read_text())
        assert rule["language"] == "python", (
            f"{rule_file.name} is not Python; `_covers` probes with `kind: module`, "
            "which is Python's root node — give it the new language's root first"
        )
        for key in ("files", "ignores"):
            for glob in rule.get(key) or []:
                if _covers(glob, rule["language"], tmp_path) == 0:
                    dead.append(f"{rule['id']}: {key}: {glob}")
    assert not dead, "path scopes that reach no file in this repo: " + "; ".join(dead)


def test_every_rule_is_verified_by_a_test_of_its_own():
    """The `structure` gate counts `ast-grep test`'s passes against the rules on
    disk, so a rule added without a test turns the gate to `error` for the whole
    repo rather than reporting the one rule that is unguarded. This says which."""
    tested = {
        yaml.safe_load(p.read_text())["id"]
        for p in (REPO / ".saffron" / "rule-tests").glob("*.yml")
    }
    declared = {yaml.safe_load(p.read_text())["id"] for p in _rule_files()}
    assert declared - tested == set(), f"rules with no test: {declared - tested}"
    assert tested - declared == set(), f"tests for no rule: {tested - declared}"


def test_structure_names_its_tool_and_passes_on_this_repos_code():
    done = subprocess.run(
        [str(GATES / "structure")],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
    )
    result = parse_gate_json(done.stdout, expected_gate="structure")
    assert result.status == "pass", result.summary
    assert result.tool and result.tool.startswith("ast-grep ")


def _rules_tree(tmp_path) -> Path:
    """This repo's whole `structure` surface — the rules, their tests, the config
    that names both, and the gate — in a tree of its own, and the gate to judge it
    by. The gate resolves its config from its own location rather than from the
    cwd, so a subject has to carry the gate it is measured with; that is also the
    shape production runs, where `/work/.saffron/gates/` and the code under test
    are one checkout.

    The rule tests come too: the gate verifies its own rules before scanning, so
    a subject carrying rules without them is not the shape production runs.
    """
    shutil.copytree(REPO / ".saffron" / "rules", tmp_path / ".saffron" / "rules")
    shutil.copytree(
        REPO / ".saffron" / "rule-tests", tmp_path / ".saffron" / "rule-tests"
    )
    shutil.copytree(REPO / ".saffron" / "gates", tmp_path / ".saffron" / "gates")
    shutil.copy(SGCONFIG, tmp_path / ".saffron" / "sgconfig.yml")
    return tmp_path / ".saffron" / "gates" / "structure"


def test_structure_fails_on_code_its_rules_reject(tmp_path):
    """A gate that has only ever passed is not known to be a gate."""
    gate = _rules_tree(tmp_path)
    (tmp_path / "bad.py").write_text('emit({"gate": "lint", "tool": "ruff 9.9.9"})\n')
    done = subprocess.run(
        [str(gate)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    result = parse_gate_json(done.stdout, expected_gate="structure")
    assert result.status == "fail", result.summary
    assert len(result.failures) == 1
    assert result.failures[0].file.endswith("bad.py")
    assert result.failures[0].code == "gate-tool-must-be-executed"
    # ast-grep counts lines from zero and every other gate here reports them from
    # one, so an unconverted line reads as the line above the defect.
    assert result.failures[0].line == 1


def test_structure_scans_the_dot_directory_its_rules_most_need(tmp_path):
    """Measured: a bare `ast-grep scan` walks past `.saffron/` because it is a
    dot-directory, and `.saffron/gates/` is exactly where the `tool` rule matters
    — a mutant planted there went unreported until `--no-ignore hidden`. The
    subject is `.saffron/gates/`, not any hidden path, because that is the one
    the omission actually silenced."""
    gate = _rules_tree(tmp_path)
    (tmp_path / ".saffron" / "gates" / "bad.py").write_text(
        'emit({"gate": "lint", "tool": "ruff 9.9.9"})\n'
    )
    done = subprocess.run(
        [str(gate)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    result = parse_gate_json(done.stdout, expected_gate="structure")
    assert result.status == "fail", result.summary
    assert [f.file for f in result.failures] == [".saffron/gates/bad.py"]


def test_structure_errors_rather_than_passes_when_it_has_no_rules(tmp_path):
    """`ast-grep` pointed at a `sgconfig.yml` that is not there exits non-zero and
    writes nothing to stdout. Read as a verdict that would be a clean pass over
    every rule at once — the founding defect of Appendix I. Charged to nobody
    instead (§5.4). The gate carries its config path, so the subject is a gate
    with its rules taken away rather than a bare directory."""
    shutil.copytree(REPO / ".saffron" / "gates", tmp_path / ".saffron" / "gates")
    (tmp_path / "a.py").write_text("x = 1\n")
    done = subprocess.run(
        [str(tmp_path / ".saffron" / "gates" / "structure")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    result = parse_gate_json(done.stdout, expected_gate="structure")
    assert result.status == "error", result.summary
    assert result.tool, "a scan failure is not a reason to drop the tool identifier"


def test_structure_errors_when_a_rule_has_stopped_guarding(tmp_path):
    """The gap `integrity` leaves. A rule weakened until its own invalid snippet
    no longer matches leaves `ast-grep scan` exiting 0 — a clean report from a
    rule guarding nothing — and `gate-config-changed` exempts a task whose spec
    declared the `.saffron/**` touch. `fail` would charge the repo's code for a
    broken control surface, so it is `error` (§5.4)."""
    gate = _rules_tree(tmp_path)
    rule = tmp_path / ".saffron" / "rules" / "agent-sdk-import-is-runner-only.yml"
    rule.write_text(rule.read_text().replace("claude_agent_sdk", "never_matches_this"))
    (tmp_path / "bad.py").write_text("import claude_agent_sdk\n")

    done = subprocess.run(
        [str(gate)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    result = parse_gate_json(done.stdout, expected_gate="structure")
    assert result.status == "error", result.summary
    assert result.status != "pass", "a rule that guards nothing scans clean"


def test_structure_errors_when_its_rules_are_verified_by_nothing(tmp_path):
    """Measured: with `testConfigs` absent `ast-grep test` prints "Running 0
    tests" and exits 0. Read as a verdict that is every rule verified at once
    while nothing ran — so the gate counts the tests against the rules on disk
    rather than trusting the exit status."""
    gate = _rules_tree(tmp_path)
    shutil.rmtree(tmp_path / ".saffron" / "rule-tests")
    (tmp_path / ".saffron" / "sgconfig.yml").write_text("ruleDirs:\n  - rules\n")

    done = subprocess.run(
        [str(gate)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    result = parse_gate_json(done.stdout, expected_gate="structure")
    assert result.status == "error", result.summary
    # Against the live rule count, not a number: a fourth rule is not a reason
    # for this test to fail.
    assert f"0 of {len(_rule_files())} rules verified" in result.summary


def _stub_ast_grep(tmp_path, version_body: str, scan_body: str = "echo '[]'"):
    """An `ast-grep` on PATH whose version no string literal in the gate could
    guess."""
    stub = tmp_path / "bin"
    stub.mkdir()
    # The `test` branch reports the rule count these tests run against, so the
    # gate's own verification passes and the assertion below reaches `scan`.
    # Left to the `*)` catch-all it would answer the count check with scan output.
    rules = len(_rule_files())
    (stub / "ast-grep").write_text(
        f'#!/bin/sh\ncase "$1" in\n  --version) {version_body} ;;\n'
        f'  test) echo "test result: ok. {rules} passed; 0 failed;" ;;\n'
        f"  *) {scan_body} ;;\nesac\n"
    )
    (stub / "ast-grep").chmod(0o755)
    return {**os.environ, "PATH": f"{stub}:{os.environ['PATH']}"}


def test_structure_reports_the_version_the_tool_printed_not_a_literal(tmp_path):
    """The invariant `tool` exists for: obtained *by executing* the tool (§5.4,
    Appendix H). This gate's own rules forbid the literal it would otherwise be,
    which is a rule and not a test — asserting the prefix "ast-grep " cannot tell
    an executed version from one written down."""
    env = _stub_ast_grep(tmp_path, 'echo "ast-grep 9.9.9-stub"')
    done = subprocess.run(
        [str(GATES / "structure")],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    result = parse_gate_json(done.stdout, expected_gate="structure")
    assert result.tool == "ast-grep 9.9.9-stub"


def test_structure_errors_when_its_tool_runs_and_reports_no_version(tmp_path):
    """A tool that runs and identifies nothing cannot produce the field that
    separates a gate that ran from one that did not, so it is `error` — not a
    pass carrying `tool: ""`, which is how the `shacl` gate first shipped."""
    env = _stub_ast_grep(tmp_path, "exit 0")
    done = subprocess.run(
        [str(GATES / "structure")],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    result = parse_gate_json(done.stdout, expected_gate="structure")
    assert result.status == "error", result.summary
    assert "no version" in result.summary


def test_the_config_names_the_directories_the_gate_and_these_tests_count():
    """The gate cannot read YAML — it is a stdlib script — so it resolves
    `.saffron/rules/` by name and asks ast-grep to load whatever the config says.
    Two sources of truth for one question: repoint `ruleDirs` and the gate counts
    rules that never ran. Nothing in the gate can notice, so the test does."""
    config = yaml.safe_load(SGCONFIG.read_text())
    assert config["ruleDirs"] == ["rules"], (
        "the gate counts `.saffron/rules/*.yml` against what ast-grep loaded; "
        "a config naming a different directory makes those two questions differ"
    )
    assert [t["testDir"] for t in config["testConfigs"]] == ["rule-tests"]


def test_structure_ignores_a_config_planted_where_ast_grep_would_find_one(tmp_path):
    """`sgconfig.yml` at the repo root is where a bare `ast-grep` looks first, and
    it is outside `.saffron/**` — outside `protected` and outside
    `integrity.gate_config`. Measured on the first cut of this gate: a root config
    pointing `ruleDirs` at a copy of the rules re-scoped to a directory that does
    not exist reported `pass` on a tree carrying all three violations, with
    `ast-grep test` still reporting every rule verified. The gate passes `-c`
    anchored on its own location, so the decoy is inert."""
    gate = _rules_tree(tmp_path)
    (tmp_path / "saffron" / "cell").mkdir(parents=True)
    (tmp_path / "saffron" / "cell" / "bad.py").write_text(
        'subprocess.run(["container", "run"])\n'
    )

    shutil.copytree(tmp_path / ".saffron" / "rules", tmp_path / "decoy-rules")
    for rule in (tmp_path / "decoy-rules").glob("*.yml"):
        body = yaml.safe_load(rule.read_text())
        body["files"] = ["nowhere/**/*.py"]
        rule.write_text(yaml.safe_dump(body))
    shutil.copytree(tmp_path / ".saffron" / "rule-tests", tmp_path / "decoy-tests")
    (tmp_path / "sgconfig.yml").write_text(
        "ruleDirs:\n  - decoy-rules\ntestConfigs:\n  - testDir: decoy-tests\n"
    )

    done = subprocess.run(
        [str(gate)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    result = parse_gate_json(done.stdout, expected_gate="structure")
    assert result.status == "fail", result.summary
    assert [f.code for f in result.failures] == ["container-runtime-is-runtime-only"]


@pytest.mark.parametrize("ignore_file", [".ignore", ".git/info/exclude"])
def test_an_ignore_file_outside_the_diff_cannot_hide_a_violation(tmp_path, ignore_file):
    """ast-grep walks with the `ignore` crate, which has no notion of what git
    tracks: one line naming a *tracked* file removes it from the scan while it
    stays in the commit. Measured, in a real repository, on all three sources.

    `.gitignore` is the one this repo needs — it is what keeps `.venv` and
    `.claude/worktrees/` out — and an edit to it is in the diff, so
    `integrity.gate_config` routes it to a person. These two are not: `.ignore`
    buys nothing here, and `.git/info/exclude` never appears in a diff at all, so
    no policy list can reach it. The gate refuses both."""
    gate = _rules_tree(tmp_path)
    (tmp_path / "saffron" / "cell").mkdir(parents=True)
    (tmp_path / "saffron" / "cell" / "bad.py").write_text(
        'subprocess.run(["container", "run"])\n'
    )
    hidden = tmp_path / ignore_file
    hidden.parent.mkdir(parents=True, exist_ok=True)
    hidden.write_text("saffron/cell/bad.py\n")

    done = subprocess.run(
        [str(gate)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    result = parse_gate_json(done.stdout, expected_gate="structure")
    assert result.status == "fail", result.summary
    assert [f.file for f in result.failures] == ["saffron/cell/bad.py"]


def test_what_decides_which_files_a_gate_sees_is_routed_to_a_person():
    """`integrity.gate_config` exists because the rules a gate enforces have to
    reach a human, not just the gate's own executable. What a gate can *see* is
    the same question one step earlier: `.gitignore` removes a tracked file from
    `lint`, `format` and `structure` at once, and the config naming the rules
    decides which rules run at all. Nested `.gitignore` files count too."""
    policy, _ = load_policy(REPO)
    for path in (
        ".gitignore",
        "saffron/cell/.gitignore",
        ".saffron/sgconfig.yml",
        ".saffron/rules/container-runtime-is-runtime-only.yml",
    ):
        assert any(matches(path, p) for p in policy.integrity.gate_config), (
            f"{path} decides what a blocking gate can see and no gate_config "
            "pattern covers it, so an agent can edit it and go green"
        )


def test_structure_errors_when_its_tool_is_present_but_not_runnable(tmp_path):
    """`FileNotFoundError` is not the only way a tool fails to start. A file on
    PATH without the execute bit raises `PermissionError`, and an uncaught one
    writes a traceback to stderr and nothing to stdout — which `run_gate` reads
    as a gate that produced no contract at all. The verdict is `error` either
    way; caught, it also says which of the two happened.

    The PATH carries no other ast-grep, deliberately: `execvp` treats a candidate
    it cannot execute as a miss and keeps walking, so a stub in front of a real
    binary is not a broken tool — it is a working one found second."""
    stub = tmp_path / "bin"
    stub.mkdir()
    (stub / "ast-grep").write_text("#!/bin/sh\necho 'ast-grep 0.0.0-stub'\n")
    (stub / "ast-grep").chmod(0o644)
    done = subprocess.run(
        [str(GATES / "structure")],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "PATH": f"{stub}:/usr/bin:/bin"},
    )
    result = parse_gate_json(done.stdout, expected_gate="structure")
    assert result.status == "error", result.summary
    assert "could not be run" in result.summary
