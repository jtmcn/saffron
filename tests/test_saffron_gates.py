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
import re
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


def _rule_test_files():
    """Every file ast-grep would load as a rule test. `_rule_files`' reasons, for
    the same globber — minus `__snapshots__/`, which carries the rule's own `id`
    and would let a rule whose test file was deleted still read as verified."""
    return sorted(
        p
        for p in (REPO / ".saffron" / "rule-tests").rglob("*")
        if p.suffix in (".yml", ".yaml") and "__snapshots__" not in p.parts
    )


def _scan_ignore_flags() -> list[str]:
    """The `--no-ignore` values the gate actually passes, read from its source.

    Read rather than restated: these decide which files the scan can see at all,
    and a copy in this file would let the gate lose one while everything here
    still certified the set the test wished for."""
    found = re.findall(
        r'"--no-ignore",\s*\n\s*"(\w+)"', (GATES / "structure.py").read_text()
    )
    assert len(found) >= 3, (
        "found no `--no-ignore` pairs in the gate — this reader has gone stale "
        f"against the gate's source, not the other way round (got {found})"
    )
    return found


def _scan_globs() -> list[str]:
    """The `--globs` the gate passes, read from its source for `_scan_ignore_flags`'
    reason. These are the *only* thing holding a directory out of the scan now that
    every ignore source is refused, so a copy of them here would let the gate lose
    one while everything in this file still certified the set the test wished for.
    """
    found = re.findall(
        r'"--globs",\s*\n\s*"([^"]+)"', (GATES / "structure.py").read_text()
    )
    assert found, (
        "found no `--globs` in the gate — with `--no-ignore vcs` these are what "
        "keep `.venv` out, so this reader has gone stale, not the gate"
    )
    return found


def test_the_hook_and_the_gate_scan_the_same_files():
    """The hook's own comment says the flags are the gate's, for the gate's
    reasons; nothing checked it. A hook that honours an ignore source the gate
    refuses passes a commit the gate then fails, which is the disagreement the
    comment warns about — and the reverse hides a violation until PACKAGE.

    The globs count as much as the `--no-ignore` values: they are the whole of
    what either one excludes."""
    hook = (REPO / ".pre-commit-config.yaml").read_text()
    entry = hook[hook.index("id: ast-grep") :]
    assert sorted(re.findall(r"--no-ignore (\w+)", entry)) == sorted(
        _scan_ignore_flags()
    )
    assert sorted(re.findall(r'--globs "([^"]+)"', entry)) == sorted(_scan_globs())
    # Both must name the config rather than let ast-grep walk up and find one.
    assert entry.count("-c .saffron/sgconfig.yml") == 2, (
        "the hook must pass `-c` to both `test` and `scan`"
    )


def test_a_rules_exemptions_are_the_three_named_files():
    """The half of a rule that `ast-grep test` structurally cannot see, and that
    reaching a file cannot certify either. Measured: widening the container
    rule's `ignores` to `saffron/cell/**` leaves `ast-grep test` reporting
    `3 passed; 0 failed` and the gate reporting `pass` on a tree carrying the
    violation — a rule disarmed without a snippet changing.

    Reach is not the check, because a wider glob reaches *more* files. These are
    three named files and one test tree; they are not supposed to move without a
    person saying so."""
    exemptions = {
        yaml.safe_load(p.read_text())["id"]: yaml.safe_load(p.read_text()).get(
            "ignores"
        )
        for p in _rule_files()
    }
    assert exemptions == {
        "container-runtime-is-runtime-only": ["saffron/cell/runtime.py"],
        "agent-sdk-import-is-runner-only": ["images/agent_runner.py"],
        "gate-tool-must-be-executed": ["tests/**"],
    }


def _covers(glob: str, language: str, tmp_path) -> int:
    """How many files in this repo a rule's path glob actually reaches.

    Asked of ast-grep rather than of `fnmatch` or `Path.glob`: the question is
    what *this* globber does, and a reimplementation that disagreed would pass
    while the rule it certifies covers nothing. The probe carries the one glob
    and a body matching every file of the language — `module` is the root node
    of a Python parse — so the count is the scope's reach and nothing else.

    It walks with the gate's own ignore flags *and* its globs: a glob whose reach
    depended on a source the gate refuses — or on a directory only the gate's
    globs hold out — would be judged here by a different walk than the one it is
    certifying.
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
            *[a for f in _scan_ignore_flags() for a in ("--no-ignore", f)],
            *[a for g in _scan_globs() for a in ("--globs", g)],
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
    tested = {yaml.safe_load(p.read_text())["id"] for p in _rule_test_files()}
    declared = {yaml.safe_load(p.read_text())["id"] for p in _rule_files()}
    assert declared - tested == set(), f"rules with no test: {declared - tested}"
    assert tested - declared == set(), f"tests for no rule: {tested - declared}"


def test_every_rule_test_declares_a_snippet_that_must_fire():
    """A rule test's `valid` snippets say what must *not* match; only an `invalid`
    one says the rule matches anything at all. Measured: delete a rule's `invalid`
    list and neuter its body, and `ast-grep test` reports `PASS <rule>` and counts
    it in `3 passed; 0 failed` — a rule matching nothing satisfies every `valid`
    snippet left — so the gate's count is satisfied by a rule guarding nothing.

    The gate refuses this too, and for the same reason it counts rules rather than
    trusting an exit status. This names the file; the gate can only turn `error`."""
    for p in _rule_test_files():
        assert yaml.safe_load(p.read_text()).get("invalid"), (
            f"{p.name} declares no `invalid` snippet, so it certifies that the "
            "rule does not fire on things it should not — never that it fires"
        )


# The two spellings that carry an `invalid` snippet while an earlier `^invalid:\s*\n\s*-`
# read neither. Both are one edit from what ships: these files are densely
# commented everywhere except directly under `invalid:`.
INVALID_DECLARED_ANYWAY = {
    "a comment under the key": (
        "invalid:\n  - ",
        "invalid:\n  # the plainest form\n  - ",
    ),
    "a flow sequence": (
        "invalid:\n  - ",
        "invalid: ['import claude_agent_sdk']\nunused:\n  - ",
    ),
}


@pytest.mark.parametrize("spelling", sorted(INVALID_DECLARED_ANYWAY))
def test_the_gate_reads_an_invalid_snippet_in_any_yaml_spelling(tmp_path, spelling):
    """The check above parses YAML; the gate is a stdlib script that reads lines,
    and the two disagreed. Measured against the unfixed gate: both spellings below
    turned it to `error` with a summary saying the file declared no `invalid`
    snippet, while `yaml.safe_load` — and this file's own twin of the check — saw
    one and stayed green, so the suite could not notice the divergence.

    `error` aborts the attempt and is charged to nobody (§5.4), so a false one
    costs a task and tells its operator something untrue about why."""
    gate = _rules_tree(tmp_path)
    victim = (
        tmp_path
        / ".saffron"
        / "rule-tests"
        / "agent-sdk-import-is-runner-only-test.yml"
    )
    old, new = INVALID_DECLARED_ANYWAY[spelling]
    assert old in victim.read_text(), "the fixture no longer spells `invalid:` this way"
    victim.write_text(victim.read_text().replace(old, new, 1))
    assert yaml.safe_load(victim.read_text()).get("invalid"), (
        "the mutant must still declare a snippet, or it is testing the wrong thing"
    )
    (tmp_path / "bad.py").write_text('emit({"gate": "lint", "tool": "ruff 9.9.9"})\n')

    done = subprocess.run(
        [str(gate)], cwd=tmp_path, capture_output=True, text=True, timeout=120
    )
    result = parse_gate_json(done.stdout, expected_gate="structure")
    assert result.status == "fail", result.summary
    assert [f.code for f in result.failures] == ["gate-tool-must-be-executed"]


def test_the_gate_still_refuses_an_invalid_list_that_is_empty(tmp_path):
    """The mutant that proves the fix above is not a blanket yes. An `invalid:`
    key with nothing under it certifies exactly what a missing one does."""
    gate = _rules_tree(tmp_path)
    victim = (
        tmp_path
        / ".saffron"
        / "rule-tests"
        / "agent-sdk-import-is-runner-only-test.yml"
    )
    victim.write_text(
        re.split(r"^invalid:", victim.read_text(), flags=re.M)[0] + "invalid: []\n"
    )

    done = subprocess.run(
        [str(gate)], cwd=tmp_path, capture_output=True, text=True, timeout=120
    )
    result = parse_gate_json(done.stdout, expected_gate="structure")
    assert result.status == "error", result.summary
    assert victim.name in result.summary


def test_no_rules_regex_anchors_on_the_quote_its_author_typed():
    """The defect two review rounds found in a different spelling each time. A
    tree-sitter `string` node's text carries its quotes *and* its `r`/`f`/`b`
    prefix, so a regex anchored on a quote character reads only the spellings its
    author happened to type: `'container'` walked past in round 2, `r"container"`
    in round 3, and ruff neither lints nor reformats a raw string, so nothing else
    in the loop caught it either.

    A regex belongs on the `string_content` child, which carries neither. This is
    the class, not the two instances — the next prefix costs nothing to add."""
    offenders = []
    for p in _rule_files():
        for regex in re.findall(r"regex:\s*(\S.*)", p.read_text()):
            body = regex.strip().strip("'\"")
            # The anti-pattern exactly: an anchor onto a quote character, however
            # many spellings the class lists. Not any regex containing a quote —
            # matching a `"tool":` *inside* a string's content is the fix, not
            # the defect.
            if re.match(r"\^(\[[^\]]*['\"][^\]]*\]|['\"])", body):
                offenders.append(f"{p.name}: {regex.strip()}")
    assert not offenders, (
        "regexes anchored on a quote character, which read only the spellings "
        "their author typed: " + "; ".join(offenders)
    )


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
    rather than trusting the exit status.

    The rule tests stay on disk and only `testConfigs` goes: removing the files
    instead would trip the 1:1 count beside this one, and this check is the one
    that reads what `ast-grep test` actually ran rather than what is on disk."""
    gate = _rules_tree(tmp_path)
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
    # The gate resolves this one itself too, to find the tests whose `invalid`
    # lists it checks — the same two-sources-of-truth shape as `ruleDirs`.
    assert '"rule-tests"' in (GATES / "structure.py").read_text()


def test_structure_errors_when_a_rule_test_certifies_nothing(tmp_path):
    """`ast-grep test` reports `PASS` for a rule whose body matches nothing, so
    long as its `invalid` list is gone: every remaining `valid` snippet is
    satisfied. Measured — `3 passed; 0 failed`, the gate's count met, and a tree
    carrying the violation reported `pass`.

    `error`, not `fail`: a control surface that cannot say whether it works is
    charged to nobody, like the missing config and the unrunnable binary."""
    gate = _rules_tree(tmp_path)
    victim = tmp_path / ".saffron" / "rule-tests"
    victim = next(p for p in victim.iterdir() if p.name.endswith("-test.yml"))
    victim.write_text(re.split(r"^invalid:", victim.read_text(), flags=re.M)[0])

    done = subprocess.run(
        [str(gate)], cwd=tmp_path, capture_output=True, text=True, timeout=120
    )
    result = parse_gate_json(done.stdout, expected_gate="structure")
    assert result.status == "error", result.summary
    assert victim.name in result.summary
    assert result.tool, "the gate ran ast-grep; the identifier is obtainable"


def test_structure_errors_when_every_rule_has_been_deleted(tmp_path):
    """The cheapest route to the shape the two checks above exist to refuse, and
    the one they both missed: no rule weakened, no config edited, no ignore file
    written — just `rm .saffron/rules/*.yml`. Measured against the unfixed gate,
    on this same tree carrying a real violation: `pass`, `0 violations`.

    `ast-grep test` prints "Configuration not found!" for each orphaned test and
    still exits 0, the count check compares `0 != 0` and is satisfied, and a scan
    that loads no rules matches nothing. So the count needs a floor: the gate
    cannot know how many rules the repo means to have, but it knows that none is
    not a verdict. `integrity` routes the deletion to a person and does not block
    it, and a repo adopting this gate inherits none of these tests."""
    gate = _rules_tree(tmp_path)
    for rule in (tmp_path / ".saffron" / "rules").glob("*.yml"):
        rule.unlink()
    (tmp_path / "bad.py").write_text('emit({"gate": "lint", "tool": "ruff 9.9.9"})\n')

    done = subprocess.run(
        [str(gate)], cwd=tmp_path, capture_output=True, text=True, timeout=120
    )
    result = parse_gate_json(done.stdout, expected_gate="structure")
    assert result.status == "error", result.summary
    assert result.status != "pass", "a scan with no rules matches nothing"
    assert result.tool, "an empty rule directory is not a reason to drop the tool"


def test_structure_errors_when_one_rule_is_dropped_and_its_test_left(tmp_path):
    """The floor above catches an empty rule directory; this catches one rule
    short of it. The count check cannot: it recomputes `expected` from the rules
    on disk, so deleting a rule takes both sides down together and `2 == 2`.

    Measured: with the rule gone and its test kept, `ast-grep test` prints
    "Configuration not found! <id>", counts only the survivors, and exits 0 — a
    clean report over a rule that is not there. One `id:` per test file makes the
    two counts 1:1, so an inequality is the signal."""
    gate = _rules_tree(tmp_path)
    dropped = tmp_path / ".saffron" / "rules" / "container-runtime-is-runtime-only.yml"
    dropped.unlink()
    (tmp_path / "saffron" / "cell").mkdir(parents=True)
    (tmp_path / "saffron" / "cell" / "bad.py").write_text(
        'subprocess.run(["container", "run"])\n'
    )

    done = subprocess.run(
        [str(gate)], cwd=tmp_path, capture_output=True, text=True, timeout=120
    )
    result = parse_gate_json(done.stdout, expected_gate="structure")
    assert result.status == "error", result.summary
    # Against the live counts, not a number: a fourth rule is not a reason to fail.
    assert f"{len(_rule_files()) - 1} rules but {len(_rule_test_files())}" in (
        result.summary
    )


def test_structure_names_the_rule_that_stopped_guarding(tmp_path):
    """`rule tests did not pass (exit 4)` was the whole summary, and this summary
    is the night's only human-readable record of why a task died. Measured: the
    failing rule is in ast-grep's stdout as `FAIL <id>` and the remediation is on
    its stderr, and the gate was discarding both."""
    gate = _rules_tree(tmp_path)
    rule = tmp_path / ".saffron" / "rules" / "agent-sdk-import-is-runner-only.yml"
    rule.write_text(rule.read_text().replace("claude_agent_sdk", "never_matches_this"))

    done = subprocess.run(
        [str(gate)], cwd=tmp_path, capture_output=True, text=True, timeout=120
    )
    result = parse_gate_json(done.stdout, expected_gate="structure")
    assert result.status == "error", result.summary
    assert "agent-sdk-import-is-runner-only" in result.summary, (
        "the summary says a rule stopped guarding without saying which"
    )
    assert "container-runtime-is-runtime-only" not in result.summary, (
        "naming every rule is the same as naming none"
    )


def test_structure_passes_a_tool_field_the_gate_interpolated(tmp_path):
    """The `tool` rule is blocking, so a false positive costs a task and tells its
    author to execute the tool they executed. In tree-sitter-python an f-string is
    a `string` node like any other: measured against the unfixed rule, every one
    of these — including the direct Python translation of what
    `.saffron/gates/format` writes in shell — was reported as a literal."""
    gate = _rules_tree(tmp_path)
    (tmp_path / "good.py").write_text(
        'emit({"gate": "lint", "tool": f"ruff {version}"})\n'
        'payload["tool"] = f"ruff {version}"\n'
        'GateResult(gate="lint", tool=f"ruff {version}")\n'
        'tool = f"ruff {version}"\n'
        'result.tool = f"ruff {version}"\n'
        'payload.setdefault("tool", f"ruff {version}")\n'
        'print(f\'{{"gate":"lint","tool":"{version}"}}\')\n'
    )

    done = subprocess.run(
        [str(gate)], cwd=tmp_path, capture_output=True, text=True, timeout=120
    )
    result = parse_gate_json(done.stdout, expected_gate="structure")
    assert result.status == "pass", result.summary


def test_the_tool_rule_still_reads_an_uninterpolated_f_string_as_a_literal(tmp_path):
    """The mutant that keeps the fix above from being a blanket exemption. The
    prefix is not what makes a string evidence: `f"ruff 0.16.3"` interpolates
    nothing, and a serialized contract can carry a literal `tool` beside an
    interpolated field — which is why the JSON branch tests the value rather than
    the string."""
    gate = _rules_tree(tmp_path)
    (tmp_path / "bad.py").write_text(
        'tool = f"ruff 0.16.3"\n'
        'print(f\'{{"gate":"lint","tool":"ruff 0.16.3","took":"{elapsed}"}}\')\n'
    )

    done = subprocess.run(
        [str(gate)], cwd=tmp_path, capture_output=True, text=True, timeout=120
    )
    result = parse_gate_json(done.stdout, expected_gate="structure")
    assert result.status == "fail", result.summary
    assert [f.line for f in result.failures] == [1, 2], result.failures


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


@pytest.mark.parametrize(
    ("ignore_file", "pattern"),
    [
        (".gitignore", "saffron/cell/bad.py"),
        # A nested one's patterns are relative to its own directory, not the root.
        # Written root-relative it silences nothing and the case proves nothing.
        ("saffron/.gitignore", "cell/bad.py"),
        (".ignore", "saffron/cell/bad.py"),
        (".git/info/exclude", "saffron/cell/bad.py"),
    ],
)
def test_an_ignore_file_outside_the_diff_cannot_hide_a_violation(
    tmp_path, ignore_file, pattern
):
    """ast-grep walks with the `ignore` crate, which has no notion of what git
    tracks: one line naming a *tracked* file removes it from the scan while it
    stays in the commit. Measured, in a real repository, on every source.

    `.gitignore` is here because routing an edit to a person is the tracked half
    only — see the test below. The gate refuses all of them and states its own
    file set with `--globs` instead, so what it scans is a property of the gate
    rather than of whichever files happen to be on disk."""
    _assert_hidden_violation_is_still_reported(
        tmp_path, ignore_file=ignore_file, pattern=pattern
    )


def test_a_gitignore_that_names_itself_cannot_hide_a_tracked_violation(tmp_path):
    """The half `integrity.gate_config` cannot close, and the reason `.gitignore`
    is refused outright rather than routed.

    A `.gitignore` naming both a tracked violating file and *itself* is never
    added by `git add -A`, so it reaches no diff, no commit, and nothing
    `git status --porcelain -uall` reports — which is `worktree.dirty_paths`, and
    so every host-side check that could notice. Measured against the gate before
    `--no-ignore vcs`: the violation stayed committed and the scan reported
    `pass`. The `.git` directory is load-bearing — the walker consults a
    `.gitignore` this way only for a tree that looks like a repository."""
    root = tmp_path / "repo"
    gate = _rules_tree(root)
    (root / ".git").mkdir(parents=True)
    (root / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    (root / "saffron" / "cell").mkdir(parents=True)
    (root / "saffron" / "cell" / "bad.py").write_text(
        'subprocess.run(["container", "run"])\n'
    )
    (root / "saffron" / "cell" / ".gitignore").write_text("bad.py\n.gitignore\n")

    done = subprocess.run(
        [str(gate)], cwd=root, capture_output=True, text=True, timeout=120
    )
    result = parse_gate_json(done.stdout, expected_gate="structure")
    assert result.status == "fail", result.summary
    assert [f.file for f in result.failures] == ["saffron/cell/bad.py"]


def test_the_global_excludes_file_cannot_hide_a_violation(tmp_path, monkeypatch):
    """`core.excludesFile` is the same defect one step further out of reach than
    `.git/info/exclude`: it is not merely absent from the diff, it is not in the
    repository at all, so no policy list can ever name it. Measured with the
    gate's flags before `--no-ignore global` was among them: a tracked violating
    file scanned clean because a file in `$HOME` said so.

    The `.git` directory is load-bearing, not scaffolding — measured, the walker
    consults the global excludes only for a tree that looks like a repository, so
    without it this test passes against the unfixed gate and proves nothing."""
    home = tmp_path / "home"
    (home / ".config" / "git").mkdir(parents=True)
    (home / ".config" / "git" / "ignore").write_text("saffron/cell/bad.py\n")
    (home / ".gitconfig").write_text(
        f"[core]\n\texcludesFile = {home / '.config' / 'git' / 'ignore'}\n"
    )
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(home / ".gitconfig"))
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    _assert_hidden_violation_is_still_reported(repo)


def _assert_hidden_violation_is_still_reported(
    root, ignore_file: str | None = None, pattern: str = "saffron/cell/bad.py"
):
    """Plant one violation the gate must report, plus optionally an in-tree ignore
    file naming it, and assert the gate reports it anyway.

    The `.git` directory is load-bearing for the `.gitignore` cases, not
    scaffolding: measured, the walker honours a `.gitignore` only in a tree that
    looks like a repository, so without one those two cases pass against a gate
    that has no `--no-ignore vcs` and prove nothing. `.ignore` is honoured either
    way, which is its own reason for being refused."""
    gate = _rules_tree(root)
    (root / ".git").mkdir(parents=True, exist_ok=True)
    (root / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    (root / "saffron" / "cell").mkdir(parents=True)
    (root / "saffron" / "cell" / "bad.py").write_text(
        'subprocess.run(["container", "run"])\n'
    )
    if ignore_file is not None:
        hidden = root / ignore_file
        hidden.parent.mkdir(parents=True, exist_ok=True)
        hidden.write_text(f"{pattern}\n")

    done = subprocess.run(
        [str(gate)],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=120,
    )
    result = parse_gate_json(done.stdout, expected_gate="structure")
    assert result.status == "fail", result.summary
    assert [f.file for f in result.failures] == ["saffron/cell/bad.py"]


def test_a_diff_touching_the_structure_surface_reaches_a_person():
    """`elevate_on` carried the rules and not their tests, though the tests are
    what prove a rule fires: deleting a rule's `invalid` list disarms it exactly
    as weakening its body does. `protected` reaches neither — `.saffron/**` is a
    glob, and `protected_touch_refusal` skips glob entries as undecidable — and
    `gate-config-changed` carries a `not declared` exemption, so `elevate_on` is
    the one that reaches a person unconditionally."""
    policy, _ = load_policy(REPO)
    for path in (
        ".saffron/rules/container-runtime-is-runtime-only.yml",
        ".saffron/rule-tests/container-runtime-is-runtime-only-test.yml",
    ):
        assert any(matches(path, p) for p in policy.elevate_on), (
            f"{path} decides whether the `structure` gate guards anything"
        )


def test_what_decides_which_files_a_gate_sees_is_routed_to_a_person():
    """`integrity.gate_config` exists because the rules a gate enforces have to
    reach a human, not just the gate's own executable. What a gate can *see* is
    the same question one step earlier: `.gitignore` removes a tracked file from
    `lint` and `format`, and the config naming the rules decides which rules run
    at all. Nested `.gitignore` files count too.

    `structure` no longer depends on this entry — it refuses every ignore source
    and states its own file set with `--globs`. The entry stays for ruff, which
    still walks with a gitignore filter (backlog item 76), and routing an edit to
    a person is the tracked half of that only: see the self-naming `.gitignore`
    above, which reaches no diff at all."""
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
