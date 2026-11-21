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
from saffron.intake import Criterion, Mutant
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
            "pattern": _NAME
            + r"\(?\s*(?P<value>[rbfuRBFU]{0,2}(?:(?P<t>\"\"\"|''')|\"|'))"
            + r"(?(t)[\s\S]*?(?P=t)).*(?:\n(?:[ \t]+\S|\)).*)*",
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

    def absent_at(self, tree_base: str, paths) -> list[str]:
        out = self._read(
            "--literal-pathspecs",
            "ls-tree",
            "-z",
            "--name-only",
            "--full-tree",
            tree_base,
            "--",
            *paths,
        )
        present = {name for name in out.split("\0") if name}
        return [path for path in paths if path not in present]

    def patch(self, base: str) -> str:
        return self._read("diff", *DIFF_FLAGS, f"{base}..HEAD")

    def head_text(self, path: str) -> str | None:
        done = subprocess.run(
            ["git", "show", f"HEAD:{path}"],
            cwd=self.repo,
            capture_output=True,
            text=True,
        )
        return done.stdout if done.returncode == 0 else None

    def dirty_paths(self) -> list[str]:
        return []

    def spec_ids(self) -> list[str]:
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
    spec_id: str = "SA-0001"
    acceptance: list = field(default_factory=list)
    spec_type: str = "feature"
    renames: dict = field(default_factory=dict)


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


def test_an_edit_deep_inside_a_long_constant_derives_its_mutant(tmp_path, monkeypatch):
    """Criterion 1: `LONG` is a name, ` = (`, nine string lines and a closing
    paren. The head edits only its fifth string line, five lines from each
    end. That edit's hunk holds neither `LONG`'s opening line nor its
    closing line. `AFTER` follows the closing paren unedited, at line 21.
    The same commit edits line 21 of `alpha.py` too, proving one file's
    added lines never leak into another file's matches."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")

    base_long = [f'    "line{n} "' if n < 9 else '    "line9"' for n in range(1, 10)]
    base_prompts = "\n".join(
        [
            "def first():",
            "    return 1",
            "",
            "",
            "",
            "",
            "",
            "",
            "LONG = (",
            *base_long,
            ")",
            'AFTER = "after"',
            "def long():",
            "    return LONG",
            "",
            "",
            "",
            "",
            "",
            "",
            "def last():",
            "    return 2",
        ]
    )
    base_alpha = "\n".join(f"# comment {n}" for n in range(1, 31))
    (repo / "prompts.py").write_text(base_prompts + "\n")
    (repo / "alpha.py").write_text(base_alpha + "\n")
    (repo / "pytest.ini").write_text("[pytest]\npythonpath = .\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    base_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()

    head_long = [f'    "line{n} "' if n < 9 else '    "line9"' for n in range(1, 10)]
    head_long[4] = '    "line5-edited "'
    head_prompts = "\n".join(
        [
            "def first():",
            "    x = 1",
            "    return x",
            "",
            "",
            "",
            "",
            "",
            "",
            "LONG = (",
            *head_long,
            ")",
            'AFTER = "after"',
            "def long():",
            "    return LONG",
            "",
            "",
            "",
            "",
            "",
            "",
            "def last():",
            "    return 3",
        ]
    )
    head_alpha_lines = [f"# comment {n}" for n in range(1, 31)]
    head_alpha_lines[20] = "# comment 21 edited"
    head_alpha = "\n".join(head_alpha_lines)
    assert head_prompts.splitlines()[20] == 'AFTER = "after"'  # line 21 at head

    (repo / "prompts.py").write_text(head_prompts + "\n")
    (repo / "alpha.py").write_text(head_alpha + "\n")
    (repo / "tests").mkdir()
    (repo / "tests" / "test_prompts.py").write_text(
        "import prompts\n\n\n"
        "def test_long():\n"
        "    assert prompts.long() == prompts.LONG\n"
        "    assert prompts.AFTER\n\n\n"
        "def test_pin():\n"
        "    assert prompts.long() == (\n"
        '        "line1 line2 line3 line4 line5-edited line6 line7 line8 line9"\n'
        "    )\n"
        "    assert prompts.LONG\n"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "head")

    prompts_diff = _git(repo, "diff", f"{base_sha}..HEAD", "--", "prompts.py").stdout
    hunk_lines = [line for line in prompts_diff.splitlines() if line.startswith("@@ ")]
    assert len(hunk_lines) == 3
    assert "LONG = (" not in prompts_diff.splitlines()
    assert ")" not in [
        line[1:] for line in prompts_diff.splitlines() if line[:1] in "+- "
    ]

    gate = tmp_path / "tests_gate.py"
    gate.write_text(_TESTS_GATE.format(python=sys.executable))
    gate.chmod(0o755)

    acceptance = [
        Criterion(claim="reads long back", witness="tests/test_prompts.py::test_long"),
        Criterion(claim="pins the literal", witness="tests/test_prompts.py::test_pin"),
    ]
    policy = Policy(
        gates={"tests": GateDeclaration()},
        integrity=IntegrityPatterns(test_paths=["tests/**"]),
        witness=PATTERNS,
    )
    suite = GateSuite(
        gates={"tests": gate},
        spec=_Spec(
            touches=["prompts.py", "alpha.py", "pytest.ini", "tests/test_prompts.py"],
            acceptance=acceptance,
        ),
        policy=policy,
        diff_base=base_sha,
    )
    prior = [GateResult(gate="tests", status="pass", tool="pytest 0", collected=[])]

    run = suite._run(_GitTree(repo), prior=prior)

    witness = next(r for r in run.results if r.gate == "witness")
    assert witness.status == "fail"
    assert [(f.file, f.code) for f in witness.failures] == [
        ("tests/test_prompts.py::test_long", "survived-mutant")
    ]
    assert witness.summary == "1 of 2 witness(es) survived their own mutant"
    assert "`LONG`" in witness.failures[0].message

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

# Each hunk above covers its whole file, so this text's own line numbers
# match the hunk's new-side numbering exactly.
_DIFF_HEAD_TEXTS = {
    "a.py": (
        'CTX = "ctx-value"\n'
        'NEW = "value"\n'
        "SPREAD = (\n"
        '    "text"\n'
        ")\n"
        'TAIL = "tail-value"\n'
    ),
    "b.py": 'KEEP = 1\nOLD = "b"\n',
}


def _diff_head_reader(path: str) -> str | None:
    return _DIFF_HEAD_TEXTS.get(path)


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

    derived = constant_mutants(
        _DIFF, acceptance, patterns, ["tests/**"], _diff_head_reader
    )

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
    assert (
        constant_mutants(
            _DIFF, acceptance, WitnessPatterns(), ["tests/**"], _diff_head_reader
        )
        == []
    )

    # `witness_name` absent.
    no_name = full.model_copy(update={"witness_name": None})
    assert (
        constant_mutants(_DIFF, acceptance, no_name, ["tests/**"], _diff_head_reader)
        == []
    )

    # `witness_body` absent.
    no_body = full.model_copy(update={"witness_body": None})
    assert (
        constant_mutants(_DIFF, acceptance, no_body, ["tests/**"], _diff_head_reader)
        == []
    )

    # No constant pattern.
    no_constants = full.model_copy(update={"constants": []})
    assert (
        constant_mutants(
            _DIFF, acceptance, no_constants, ["tests/**"], _diff_head_reader
        )
        == []
    )

    # A diff it cannot read: a header line `_split_blocks` refuses.
    unreadable = "diff --git a/x b/y\nnot the a/X b/X shape\n"
    assert (
        constant_mutants(unreadable, acceptance, full, ["tests/**"], _diff_head_reader)
        == []
    )


def test_a_quantifier_in_witness_body_is_regex_not_a_format_field():
    """`{name}` is filled as text, so a body's `{0,2}` stays a quantifier."""
    from saffron.gates.core.witness import constant_mutants
    from saffron.repos.policy import WitnessPatterns

    body = r"(?m)^(?P<i>[ \t]*)def {name}\({0,2}.*(?:\n(?:(?P=i)[ \t]+.*|[ \t]*))*"
    patterns = WitnessPatterns.model_validate({**PATTERNS, "witness_body": body})
    acceptance = [Criterion(claim="c", witness="tests/test_stuff.py::test_uses_new")]

    derived = constant_mutants(
        _DIFF, acceptance, patterns, ["tests/**"], _diff_head_reader
    )

    assert [(c.witness, c.mutant.file, c.mutant.find) for c in derived if c.mutant] == [
        ("tests/test_stuff.py::test_uses_new", "a.py", 'NEW = "')
    ]


# Nine constants back to back, one per declared spelling, verbatim from the
# spec's own notes. Each of its 56 lines is edited alone, below.
_CONSTS_MODULE = "\n".join(
    [
        'FIRST = """',
        "alpha",
        "beta",
        "",
        "gamma",
        "delta",
        "epsilon",
        "zeta",
        '"""',
        "PAREN = (",
        '    "one "',
        '    "two "',
        '    "three "',
        '    "four "',
        '    "five "',
        '    "six "',
        '    "seven "',
        '    "eight"',
        ")",
        'ONE_LINE = "a" "b"',
        "QUOTED = 'q' 'r'",
        "TUPLE = (",
        '    "t1",',
        '    "t2",',
        '    "t3",',
        '    "t4",',
        '    "t5",',
        '    "t6",',
        '    "t7",',
        '    "t8",',
        ")",
        "LIMIT = 7",
        "",
        "SINGLE = '''",
        "one",
        "two",
        "three",
        "'''",
        "SUM = (",
        '    "s1 "',
        "    + ONE_LINE",
        ")",
        "",
        "",
        "def f():",
        "    return FIRST",
        "LAST = (",
        '    "l1 "',
        '    "l2 "',
        '    "l3 "',
        '    "l4 "',
        '    "l5 "',
        '    "l6 "',
        '    "l7 "',
        '    "l8"',
        ")",
    ]
)

# Each constant's inclusive 1-indexed span, and the owner of each line
# in 1..56. `None` means no constant spans that line.
_CONSTS_SPANS = {
    "FIRST": (1, 9),
    "PAREN": (10, 19),
    "ONE_LINE": (20, 20),
    "QUOTED": (21, 21),
    "TUPLE": (22, 31),
    "LIMIT": (32, 32),
    "SINGLE": (34, 38),
    "SUM": (39, 42),
    "LAST": (47, 56),
}
_CONSTS_OWNER = {
    line: next(
        (
            name
            for name, (first, last) in _CONSTS_SPANS.items()
            if first <= line <= last
        ),
        None,
    )
    for line in range(1, 57)
}

# The bare `NAME = (` opening line of each parenthesized, multi-line
# constant, where an added trailing space falls inside `find` itself.
_CONSTS_OPENING_LINES = {
    _CONSTS_SPANS["PAREN"][0],
    _CONSTS_SPANS["TUPLE"][0],
    _CONSTS_SPANS["SUM"][0],
    _CONSTS_SPANS["LAST"][0],
}

# One witness function per constant, naming it and nothing else, so each
# constant's own mutant pairs with its own criterion alone.
_CONSTS_WITNESSES = {
    "FIRST": "test_first",
    "PAREN": "test_paren",
    "ONE_LINE": "test_one_line",
    "QUOTED": "test_quoted",
    "TUPLE": "test_tuple",
    "LIMIT": "test_limit",
    "SINGLE": "test_single",
    "SUM": "test_sum",
    "LAST": "test_last",
}

# The `find`/`replace` each constant's own mutant carries, the same
# whichever of its lines was edited.
_CONSTS_EXPECTED = {
    "FIRST": ('FIRST = """', 'FIRST = """saffron constant mutant '),
    "PAREN": ('PAREN = (\n    "', 'PAREN = (\n    "saffron constant mutant '),
    "ONE_LINE": ('ONE_LINE = "', 'ONE_LINE = "saffron constant mutant '),
    "QUOTED": ("QUOTED = '", "QUOTED = 'saffron constant mutant "),
    "TUPLE": ('TUPLE = (\n    "', 'TUPLE = (\n    "saffron constant mutant '),
    "LIMIT": ("LIMIT = 7", "LIMIT = (7 + 1)"),
    "SINGLE": ("SINGLE = '''", "SINGLE = '''saffron constant mutant "),
    "SUM": ('SUM = (\n    "', 'SUM = (\n    "saffron constant mutant '),
    "LAST": ('LAST = (\n    "', 'LAST = (\n    "saffron constant mutant '),
}


def test_an_edit_to_any_line_of_a_constant_derives_its_mutant(tmp_path, monkeypatch):
    """Criterion 2: an edit to any line of a constant derives that constant
    alone, with the same `find`/`replace` regardless of which line was
    touched. A blank line between two constants, the `def` line and its
    body derive nothing, five such lines in this module."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")

    from saffron.gates.core.witness import constant_mutants
    from saffron.repos.policy import WitnessPatterns

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "consts.py").write_text(_CONSTS_MODULE + "\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    base_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()

    patterns = WitnessPatterns.model_validate(PATTERNS)
    acceptance = [
        Criterion(claim=f"c_{fn}", witness=f"tests/test_consts.py::{fn}")
        for fn in _CONSTS_WITNESSES.values()
    ]
    witnesses_text = "\n\n\n".join(
        f"def {fn}():\n    assert {name}" for name, fn in _CONSTS_WITNESSES.items()
    )

    head_reader = _GitTree(repo).head_text

    base_lines = _CONSTS_MODULE.split("\n")
    for line_no in range(1, 57):
        edited = list(base_lines)
        edited[line_no - 1] = edited[line_no - 1] + " "
        (repo / "consts.py").write_text("\n".join(edited) + "\n")
        (repo / "tests").mkdir(exist_ok=True)
        (repo / "tests" / "test_consts.py").write_text(witnesses_text + "\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", f"edit line {line_no}")

        diff = _git(repo, "diff", *DIFF_FLAGS, f"{base_sha}..HEAD").stdout
        derived = constant_mutants(
            diff, acceptance, patterns, ["tests/**"], head_reader
        )

        owner = _CONSTS_OWNER[line_no]
        if owner is None:
            assert derived == [], line_no
        else:
            find, replace = _CONSTS_EXPECTED[owner]
            if line_no in _CONSTS_OPENING_LINES:
                # The opening line's own trailing space falls inside
                # `find`, right after the paren.
                find = find.replace(" (\n", " ( \n")
                replace = replace.replace(" (\n", " ( \n")
            fn = _CONSTS_WITNESSES[owner]
            assert len(derived) == 1, (line_no, owner, derived)
            (criterion,) = derived
            mutant = criterion.mutant
            assert mutant is not None
            assert criterion.witness == f"tests/test_consts.py::{fn}"
            assert mutant.file == "consts.py"
            assert mutant.find == find, (line_no, owner)
            assert mutant.replace == replace, (line_no, owner)

        _git(repo, "reset", "-q", "--hard", base_sha)


def test_a_constant_mutant_whose_find_matches_twice_stays_unproven(
    tmp_path, monkeypatch
):
    """A constant mutant whose `find` matches its file twice stays unproven,
    never a failure, because it is `derived` rather than spec-declared.
    Driven through one `GateSuite._run`, over a real git tree and a real
    `tests` gate. The diff gives `LIMIT` twice in one file. One criterion's
    witness reads it back, the constant mutant's own. Another declares its
    own mutant, whose `find` also matches the same file twice. Only the
    declared one fails."""
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
        "LIMIT = 3\nLIMIT = 3\n\n\ndef get_limit():\n    return LIMIT\n"
    )
    (repo / "pytest.ini").write_text("[pytest]\npythonpath = .\n")
    (repo / "tests").mkdir()
    (repo / "tests" / "test_prompts.py").write_text(
        "import prompts\n\n\n"
        "def test_a():\n    assert prompts.LIMIT == prompts.get_limit()\n\n\n"
        "def test_b():\n    assert prompts.LIMIT == 3\n"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "head")

    gate = tmp_path / "tests_gate.py"
    gate.write_text(_TESTS_GATE.format(python=sys.executable))
    gate.chmod(0o755)

    reads_limit_back = Criterion(
        claim="reads the limit back", witness="tests/test_prompts.py::test_a"
    )
    pins_the_literal = Criterion(
        claim="matches the pinned literal",
        witness="tests/test_prompts.py::test_b",
        mutant=Mutant(file="prompts.py", find="LIMIT = 3", replace="LIMIT = 4"),
    )
    policy = Policy(
        gates={"tests": GateDeclaration()},
        integrity=IntegrityPatterns(test_paths=["tests/**"]),
        witness=PATTERNS,
    )
    suite = GateSuite(
        gates={"tests": gate},
        spec=_Spec(acceptance=[reads_limit_back, pins_the_literal]),
        policy=policy,
        diff_base=base_sha,
    )
    prior = [GateResult(gate="tests", status="pass", tool="pytest 0", collected=[])]

    run = suite._run(_GitTree(repo), prior=prior)

    witness = next(r for r in run.results if r.gate == "witness")
    assert witness.status == "fail"
    assert [(f.file, f.code) for f in witness.failures] == [
        (pins_the_literal.witness, "mutant-find-repeated")
    ]
    assert reads_limit_back.witness in witness.summary

    assert _git(repo, "diff", "HEAD").stdout == ""


def test_a_find_repeated_at_head_is_one_new_failure_and_no_drift(tmp_path, monkeypatch):
    """A find-count failure at head against a base whose witness died is
    one new failure, and never drift. The `fail` carries the head `tests`
    result's own `tool`, which `suite_drift` reads as unchanged. One
    criterion's mutant matches once at base, where its witness dies, and
    twice at head. A second names a file that does not exist, and stays
    unproven on both sides, contributing no `tool` of its own."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    # Ignored up front: the tests gate's own `__pycache__` must never be
    # swept into the head commit by the `git add -A` below.
    (repo / ".gitignore").write_text("__pycache__/\n")
    (repo / "pytest.ini").write_text("[pytest]\npythonpath = .\n")
    (repo / "guard.py").write_text(
        "TARGET = 1\n\n\ndef check():\n    return TARGET == 1\n"
    )
    (repo / "tests").mkdir()
    (repo / "tests" / "test_guard.py").write_text(
        "import guard\n\n\n"
        "def test_guard():\n    assert guard.check()\n\n\n"
        "def test_other():\n    assert True\n"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    base_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()

    gate = tmp_path / "tests_gate.py"
    gate.write_text(_TESTS_GATE.format(python=sys.executable))
    gate.chmod(0o755)

    guard_dies = Criterion(
        claim="the guard holds",
        witness="tests/test_guard.py::test_guard",
        mutant=Mutant(file="guard.py", find="TARGET = 1", replace="TARGET = 42"),
        preserves=True,
    )
    file_missing = Criterion(
        claim="unrelated, by design",
        witness="tests/test_guard.py::test_other",
        mutant=Mutant(file="absent.py", find="X", replace="Y"),
        preserves=True,
    )
    policy = Policy(
        gates={"tests": GateDeclaration()},
        integrity=IntegrityPatterns(test_paths=["tests/**"]),
    )
    suite = GateSuite(
        gates={"tests": gate},
        spec=_Spec(
            touches=["guard.py", "pytest.ini", "tests/test_guard.py"],
            acceptance=[guard_dies, file_missing],
        ),
        policy=policy,
        diff_base=base_sha,
    )

    baseline = suite.baseline(_GitTree(repo))
    base_witness = next(r for r in baseline.results if r.gate == "witness")
    assert base_witness.status == "pass"
    assert base_witness.tool is not None

    # At head the same file holds `TARGET = 1` twice, still correct, so
    # the declared mutant's own `find` now matches twice instead of once.
    (repo / "guard.py").write_text(
        "TARGET = 1\nTARGET = 1\n\n\ndef check():\n    return TARGET == 1\n"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "head")

    comparison = suite.against(_GitTree(repo), baseline)

    assert comparison.aborted == ()
    assert comparison.drift == ()
    assert [(nf.gate, nf.failure.code) for nf in comparison.new_failures] == [
        ("witness", "mutant-find-repeated")
    ]
    head_witness = next(r for r in comparison.run.results if r.gate == "witness")
    assert head_witness.tool == base_witness.tool
