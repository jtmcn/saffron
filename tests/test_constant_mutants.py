"""Tests for `constant_mutants` (DESIGN.md §5.4.1, backlog item b-5b1f8a).

Every test imports `constant_mutants` and `WitnessPatterns` inside its body.
A module-scope import would make `revert`'s reverted run a collection error.
"""

from __future__ import annotations

import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from saffron.cell.worktree import DIFF_FLAGS
from saffron.gates import runner
from saffron.gates.contract import GateResult
from saffron.gates.suite import GateSuite
from saffron.intake import Criterion
from saffron.repos.policy import GateDeclaration, IntegrityPatterns, Policy
from tests.mutation import host_mutator

# Verbatim from the spec's own notes. This repo declares the identical
# block by hand after this spec merges.
_NAME = r"(?m)^(?P<name>[A-Z][A-Z0-9_]*)(?:: [^=\n]+)? = "
PATTERNS = dict(
    witness_name=r"::(?P<name>\w+)$",
    witness_body=r"(?m)^(?P<i>[ \t]*)def {name}\(.*(?:\n(?:(?P=i)[ \t]+.*|[ \t]*))*",
    constants=[
        {
            "pattern": _NAME + r"\(?\s*(?P<value>[rbfuRBFU]{0,2}(?:\"\"\"|'''|\"|'))",
            "replace": r"\g<value>saffron constant mutant ",
        },
        {
            "pattern": _NAME
            + r"(?P<value>-?(?:0[xX][0-9a-fA-F_]+|0[oO][0-7_]+|0[bB][01_]+"
            + r"|\d[\d_]*(?:\.[\d_]*)?(?:[eE][-+]?\d+)?j?))(?![\w.])",
            "replace": r"(\g<value> + 1)",
        },
    ],
)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


class _GitTree:
    """A real host git tree, standing in for a cell's worktree. The same
    shape `saffron.cell.worktree.CellTree` takes, without a container."""

    def __init__(self, repo: Path) -> None:
        self.repo = repo
        self.cwd = repo

    @property
    def executor(self) -> runner.GateExecutor:
        return runner.LocalExecutor()

    def _read(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=self.repo, check=True, capture_output=True, text=True
        ).stdout

    def changed_files(self, base: str) -> list[str]:
        out = self._read("diff", *DIFF_FLAGS, "--name-only", "-z", f"{base}..HEAD")
        return [path for path in out.split("\0") if path]

    def patch(self, base: str) -> str:
        return self._read("diff", *DIFF_FLAGS, f"{base}..HEAD")

    def dirty_paths(self) -> list[str]:
        return []

    @contextmanager
    def reverted(self, base: str, paths):
        yield

    def mutated(self, mutant):
        return host_mutator(self.repo)(mutant)


@dataclass(frozen=True)
class _Spec:
    risk: str = "standard"
    touches: list[str] = field(
        default_factory=lambda: ["prompts.py", "pytest.ini", "tests/test_prompts.py"]
    )
    forbidden: list[str] = field(default_factory=list)
    acceptance: list = field(default_factory=list)
    spec_type: str = "feature"


_TESTS_GATE = """\
#!{python}
import json
import subprocess
import sys

args = sys.argv[1:]
exe = sys.executable
collect = subprocess.run(
    [exe, "-m", "pytest", "-q", "--collect-only", *args],
    capture_output=True,
    text=True,
)
collected = [line.strip() for line in collect.stdout.splitlines() if "::" in line.strip()]
run = subprocess.run([exe, "-m", "pytest", "-q", *args], capture_output=True, text=True)
failed = [
    line.split(" ", 2)[1] for line in run.stdout.splitlines() if line.startswith("FAILED ")
]
version = subprocess.run([exe, "-m", "pytest", "--version"], capture_output=True, text=True)
tool = (version.stdout or version.stderr).strip().splitlines()[0]
status = "fail" if failed else "pass"
print(json.dumps({{
    "gate": "tests",
    "status": status,
    "tool": tool,
    "collected": collected,
    "failures": [{{"file": n, "code": n, "message": "failed"}} for n in failed],
    "summary": f"{{len(collected)}} collected, {{len(failed)}} failed",
}}))
"""


def test_a_witness_reading_its_constant_back_survives_a_constant_mutant(
    tmp_path, monkeypatch
):
    """Criterion 1: a real git tree and a real `tests` gate, driven through
    `GateSuite._run`. A witness that reads `GREETING` back survives the
    constant mutant `constant_mutants` derives from the diff. The sibling
    witness that pins the literal dies under the same edit."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("base\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    base_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()

    (repo / "prompts.py").write_text(
        'GREETING = (\n    "hello "\n    "world"\n)\n\n\ndef greet():\n'
        "    return GREETING\n"
    )
    (repo / "pytest.ini").write_text("[pytest]\npythonpath = .\n")
    (repo / "tests").mkdir()
    (repo / "tests" / "test_prompts.py").write_text(
        'import prompts\n\nEXPECTED = "hello world"\n\n\n'
        "def test_a():\n    assert prompts.greet() == prompts.GREETING\n"
        "    assert EXPECTED\n\n\n"
        "def test_b():\n    assert prompts.greet() == EXPECTED\n"
        "    assert prompts.GREETING\n"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "head")

    gate = tmp_path / "tests_gate.py"
    gate.write_text(_TESTS_GATE.format(python=sys.executable))
    gate.chmod(0o755)

    acceptance = [
        Criterion(
            claim="reads the greeting back", witness="tests/test_prompts.py::test_a"
        ),
        Criterion(
            claim="matches the pinned literal", witness="tests/test_prompts.py::test_b"
        ),
    ]
    policy = Policy(
        gates={"tests": GateDeclaration()},
        integrity=IntegrityPatterns(test_paths=["tests/**"]),
        witness=PATTERNS,  # a plain dict: `Policy` still imports at the tree base.
    )
    suite = GateSuite(
        gates={"tests": gate},
        spec=_Spec(acceptance=acceptance),
        policy=policy,
        diff_base=base_sha,
    )
    prior = [GateResult(gate="tests", status="pass", tool="pytest 0", collected=[])]

    run = suite._run(_GitTree(repo), prior=prior)

    criteria = next(r for r in run.results if r.gate == "criteria")
    assert criteria.status == "pass"
    assert criteria.summary == "2 criteria witnessed at head"

    witness = next(r for r in run.results if r.gate == "witness")
    assert witness.status == "fail"
    assert [(f.file, f.code) for f in witness.failures] == [
        ("tests/test_prompts.py::test_a", "survived-mutant")
    ]
    assert witness.summary == "1 of 2 witness(es) survived their own mutant"
    assert witness.failures[0].message.endswith(
        "the witness names `GREETING` and passes with any value of it, so "
        "pin the value as a literal"
    )

    assert _git(repo, "diff", "HEAD").stdout == ""


_DIFF = """\
diff --git a/a.py b/a.py
index 1111111..2222222 100644
--- a/a.py
+++ b/a.py
@@ -1,2 +1,6 @@
 CTX = "ctx-value"
+NEW = "value"
+SPREAD = (
+    "text"
+)
 TAIL = "tail-value"
diff --git a/b.py b/b.py
index 5555555..6666666 100644
--- a/b.py
+++ b/b.py
@@ -1,2 +1,2 @@
 KEEP = 1
-OLD = "a"
+OLD = "b"
diff --git a/tests/helper.py b/tests/helper.py
new file mode 100644
index 0000000..3333333
--- /dev/null
+++ b/tests/helper.py
@@ -0,0 +1,1 @@
+NEW_IN_TEST = "x"
diff --git a/tests/test_stuff.py b/tests/test_stuff.py
new file mode 100644
index 0000000..4444444
--- /dev/null
+++ b/tests/test_stuff.py
@@ -0,0 +1,29 @@
+def test_uses_new():
+    assert NEW == "value"
+
+
+def test_a():
+    assert NEW == "value"
+
+
+def test_sibling():
+    assert True
+
+
+def test_prefix():
+    assert NEWER
+
+
+def test_suffix():
+    assert OLD_NEW
+
+
+def test_ctx():
+    assert CTX
+
+
+def test_in_test_const():
+    assert NEW_IN_TEST
+
+
+def test_spread():
+    assert SPREAD
+
+
+def test_changed():
+    assert OLD == "b"
"""


def test_only_a_constant_the_diff_writes_and_a_witness_names_is_mutated():
    """Criterion 2: every excluded shape sits beside two real pairs, in a
    single diff. A constant on a context line. A constant under a
    declared test path. A prefix (`NEW`/`NEWER`) and a suffix
    (`NEW`/`OLD_NEW`) collision. A sibling test that never names it. A
    bare witness id `witness_name` does not match. A second criterion
    naming a witness already paired. `test_uses_new` pairs with `NEW`.
    `test_spread` pairs with a constant whose own match spans two
    lines. `test_changed` pairs with `OLD`, a line the diff changes."""
    from saffron.gates.core.witness import constant_mutants
    from saffron.repos.policy import WitnessPatterns

    patterns = WitnessPatterns.model_validate(PATTERNS)
    acceptance = [
        Criterion(claim="c1", witness="tests/test_stuff.py::test_uses_new"),
        Criterion(claim="c2", witness="test_a"),
        Criterion(claim="c3", witness="tests/test_stuff.py::test_sibling"),
        Criterion(claim="c4", witness="tests/test_stuff.py::test_prefix"),
        Criterion(claim="c5", witness="tests/test_stuff.py::test_suffix"),
        Criterion(claim="c6", witness="tests/test_stuff.py::test_ctx"),
        Criterion(claim="c7", witness="tests/test_stuff.py::test_in_test_const"),
        Criterion(claim="c8", witness="tests/test_stuff.py::test_uses_new"),
        Criterion(claim="c9", witness="tests/test_stuff.py::test_spread"),
        Criterion(claim="c10", witness="tests/test_stuff.py::test_changed"),
    ]

    derived = constant_mutants(_DIFF, acceptance, patterns, ["tests/**"])

    tuples = []
    for criterion in derived:
        mutant = criterion.mutant
        assert mutant is not None  # every derived criterion carries one
        tuples.append((criterion.witness, mutant.file, mutant.find, mutant.replace))
    result = sorted(tuples)
    assert result == [
        (
            "tests/test_stuff.py::test_changed",
            "b.py",
            'OLD = "',
            'OLD = "saffron constant mutant ',
        ),
        (
            "tests/test_stuff.py::test_spread",
            "a.py",
            'SPREAD = (\n    "',
            'SPREAD = (\n    "saffron constant mutant ',
        ),
        (
            "tests/test_stuff.py::test_uses_new",
            "a.py",
            'NEW = "',
            'NEW = "saffron constant mutant ',
        ),
    ]


def test_a_repo_declaring_no_witness_patterns_derives_nothing():
    """Criterion 3: five ways to have nothing to derive from, and none of
    them raises. The same non-answer `witness_gate` gives a spec with no
    declared mutant."""
    from saffron.gates.core.witness import constant_mutants
    from saffron.repos.policy import WitnessPatterns

    acceptance = [Criterion(claim="c", witness="tests/test_stuff.py::test_uses_new")]

    full = WitnessPatterns.model_validate(PATTERNS)

    # No `witness:` block at all.
    assert constant_mutants(_DIFF, acceptance, WitnessPatterns(), ["tests/**"]) == []

    # `witness_name` absent.
    no_name = full.model_copy(update={"witness_name": None})
    assert constant_mutants(_DIFF, acceptance, no_name, ["tests/**"]) == []

    # `witness_body` absent.
    no_body = full.model_copy(update={"witness_body": None})
    assert constant_mutants(_DIFF, acceptance, no_body, ["tests/**"]) == []

    # No constant pattern.
    no_constants = full.model_copy(update={"constants": []})
    assert constant_mutants(_DIFF, acceptance, no_constants, ["tests/**"]) == []

    # A diff it cannot read: a header line `_split_blocks` refuses.
    unreadable = "diff --git a/x b/y\nnot the a/X b/X shape\n"
    assert constant_mutants(unreadable, acceptance, full, ["tests/**"]) == []
