import importlib.util, subprocess, sys, tempfile, os, pathlib
sys.path.insert(0, "/Users/joel/Code/saffron")
spec = importlib.util.spec_from_file_location("ri",
    "/private/tmp/claude-501/-Users-joel-Code-saffron/048123ee-fefb-49c2-b32a-b235869b91dd/scratchpad/sa4/saffron/gates/core/integrity.py")
assert spec and spec.loader, "the spike's source path no longer exists"
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
from saffron.repos.policy import IntegrityPatterns
from saffron.cell.worktree import DIFF_FLAGS
P = IntegrityPatterns(test_paths=["tests/**"], suppressions=["# type: ignore"], gate_config=["pyproject.toml"])

def run_case(name, before, after, show=False):
    d = tempfile.mkdtemp()
    g = lambda *a: subprocess.run(a, cwd=d, capture_output=True, text=True, check=True)
    g("git","init","-q","."); g("git","config","user.email","a@b.c"); g("git","config","user.name","t")
    for f,c in before.items():
        pathlib.Path(d,f).parent.mkdir(parents=True,exist_ok=True); pathlib.Path(d,f).write_text(c)
    g("git","add","-A"); g("git","commit","-qm","base")
    for f,c in after.items():
        if c is None: pathlib.Path(d,f).unlink()
        else:
            pathlib.Path(d,f).parent.mkdir(parents=True,exist_ok=True); pathlib.Path(d,f).write_text(c)
    g("git","add","-A")
    diff = subprocess.run(["git","diff","--cached",*DIFF_FLAGS],cwd=d,capture_output=True,text=True,check=True).stdout
    r = m.integrity_gate(diff, P)
    print(f"{name:50s} -> {r.status:6s} {r.summary[:60]}")
    if show: print("".join("    |"+l+"\n" for l in diff.splitlines()[4:]))

T = "def test_a():\n    assert 1 == 1\n"

run_case("A: old has no newline, new does (marker mid-hunk)", {"tests/t.py": T.rstrip("\n")}, {"tests/t.py": T}, show=True)
run_case("B: old has newline, new does not (marker at end)", {"tests/t.py": T}, {"tests/t.py": T.rstrip("\n")}, show=True)
run_case("C: neither has newline, content changed", {"tests/t.py": T.rstrip("\n")}, {"tests/t.py": T.replace("1 == 1","2 == 2").rstrip("\n")}, show=True)
run_case("D: source file, no newline, suppression added",
         {"src/a.py": "x = 1"}, {"src/a.py": "x = 1  # type: ignore"}, show=True)
