import importlib.util, subprocess, sys, tempfile, os, pathlib
sys.path.insert(0, "/Users/joel/Code/saffron")
spec = importlib.util.spec_from_file_location(
    "rejected_integrity",
    "/private/tmp/claude-501/-Users-joel-Code-saffron/048123ee-fefb-49c2-b32a-b235869b91dd/scratchpad/sa4/saffron/gates/core/integrity.py",
)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
from saffron.repos.policy import IntegrityPatterns
from saffron.cell.worktree import DIFF_FLAGS

P = IntegrityPatterns(
    test_paths=["tests/**"],
    suppressions=["@pytest.mark.skip", "# type: ignore"],
    gate_config=["pyproject.toml"],
)

def scenario(name, before, after):
    d = tempfile.mkdtemp()
    run = lambda *a: subprocess.run(a, cwd=d, capture_output=True, text=True, check=True)
    run("git", "init", "-q", ".")
    run("git", "config", "user.email", "a@b.c"); run("git", "config", "user.name", "t")
    os.makedirs(os.path.join(d, "tests"), exist_ok=True)
    for f, c in before.items():
        pathlib.Path(d, f).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(d, f).write_text(c)
    run("git", "add", "-A"); run("git", "commit", "-qm", "base")
    for f, c in after.items():
        if c is None: pathlib.Path(d, f).unlink()
        else:
            pathlib.Path(d, f).parent.mkdir(parents=True, exist_ok=True)
            pathlib.Path(d, f).write_text(c)
    run("git", "add", "-A")
    diff = subprocess.run(["git", "diff", "--cached", *DIFF_FLAGS], cwd=d,
                          capture_output=True, text=True, check=True).stdout
    r = m.integrity_gate(diff, P)
    print(f"{name:52s} -> {r.status:6s} {[f.code for f in r.failures]}")
    return diff

TESTS = """def test_a():
    assert 1 == 1


def test_b():
    assert 2 == 2


def test_c():
    assert 3 == 3
"""

# 1. plain deletion of one test
scenario("delete one test, nothing in its place",
    {"tests/test_x.py": TESTS},
    {"tests/test_x.py": TESTS.replace("def test_b():\n    assert 2 == 2\n\n\n", "")})

# 2. delete a test and leave a comment where it was
scenario("delete one test, leave a comment in its place",
    {"tests/test_x.py": TESTS},
    {"tests/test_x.py": TESTS.replace("def test_b():\n    assert 2 == 2",
                                      "# removed: test_b was flaky")})

# 3. gut the test body in place
scenario("gut a test body in place (assert -> pass)",
    {"tests/test_x.py": TESTS},
    {"tests/test_x.py": TESTS.replace("    assert 2 == 2", "    pass")})

# 4. parametrize consolidation
scenario("consolidate two tests into one parametrize",
    {"tests/test_x.py": TESTS},
    {"tests/test_x.py": '''import pytest


@pytest.mark.parametrize("n", [1, 2])
def test_ab(n):
    assert n == n


def test_c():
    assert 3 == 3
'''})

# 5. delete the whole test file
scenario("delete the whole test file", {"tests/test_x.py": TESTS}, {"tests/test_x.py": None})

# 6. rename a test out of collection
scenario("rename test file out of tests/ (still collected? no)",
    {"tests/test_x.py": TESTS},
    {"tests/test_x.py": None, "scripts/test_x.py": TESTS})

# 7. rename the function so pytest stops collecting it
scenario("rename test_b -> check_b (silenced, body intact)",
    {"tests/test_x.py": TESTS},
    {"tests/test_x.py": TESTS.replace("def test_b():", "def check_b():")})

# 8. no trailing newline on the touched file
d = scenario("file with no trailing newline (the \\\\ marker)",
    {"tests/test_x.py": TESTS.rstrip("\n")},
    {"tests/test_x.py": TESTS.rstrip("\n") + "\n\n\ndef test_d():\n    assert 4 == 4"})
print("---- marker present in diff:", "\\ No newline" in d)
