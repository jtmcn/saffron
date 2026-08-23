import importlib.util, subprocess, sys
sys.path.insert(0, "/Users/joel/Code/saffron")
spec = importlib.util.spec_from_file_location("ri",
    "/private/tmp/claude-501/-Users-joel-Code-saffron/048123ee-fefb-49c2-b32a-b235869b91dd/scratchpad/sa4/saffron/gates/core/integrity.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
from saffron.repos.policy import load_policy
from saffron.cell.worktree import DIFF_FLAGS
pol, _ = load_policy(__import__("pathlib").Path("/Users/joel/Code/saffron"))
P = pol.integrity
print("policy patterns:", P)
for rev in ["d1141d0", "24bd0dd", "0e56b56", "3994fc6", "ba1386a"]:
    diff = subprocess.run(["git","diff",*DIFF_FLAGS,f"{rev}^",rev],
                          cwd="/Users/joel/Code/saffron",capture_output=True,text=True).stdout
    r = m.integrity_gate(diff, P)
    codes = {}
    for f in r.failures: codes[f.code] = codes.get(f.code,0)+1
    print(f"{rev} {r.status:6s} {codes}")

print("\n=== what the two suppression failures actually are ===")
diff = subprocess.run(["git","diff",*DIFF_FLAGS,"d1141d0^","d1141d0"],
                      cwd="/Users/joel/Code/saffron",capture_output=True,text=True).stdout
for f in m.integrity_gate(diff, P).failures:
    print(f"  {f.file}:{f.line}  {f.code}\n    {f.message[:160]}")
