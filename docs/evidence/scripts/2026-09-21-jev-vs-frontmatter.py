"""Spike: does Jev's change_size beat the size a spec already declares?

uv run python docs/evidence/scripts/2026-09-21-jev-vs-frontmatter.py <grades.json>
"""

import importlib.util
import json
import math
import random
import statistics as st
import sys
from pathlib import Path

import yaml

spec = importlib.util.spec_from_file_location(
    "g", "docs/evidence/scripts/2026-09-21-jev-spec-grading.py"
)
assert spec is not None and spec.loader is not None
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

grades = {r["spec_sha"]: r for r in json.loads(Path(sys.argv[1]).read_text())}
rows = []
for r in g.labelled():
    fm = yaml.safe_load(r["text"].split("---", 2)[1])
    gr = grades[r["spec_sha"]]
    rows.append(
        {
            "landed": r["landed"],
            "spec_id": r["spec_id"],
            "touches": len(fm.get("touches") or []),
            "criteria": len(fm.get("acceptance") or [])
            + len(fm.get("acceptance_criteria") or []),
            "budget_usd": float(fm.get("budget_usd") or 0),
            "elevated": 1.0 if fm.get("risk") == "elevated" else 0.0,
            "max_turns": float(fm.get("max_turns") or 0),
            "change_size": gr["answers"]["change_size"]["score"],
            "agent_lands_it": gr["answers"]["agent_lands_it"]["noul"],
        }
    )
print(len(rows), "rows,", sum(not r["landed"] for r in rows), "missed")
missing = {
    k: sum(1 for r in rows if r[k] == 0)
    for k in ("budget_usd", "max_turns", "touches", "criteria")
}
print("rows with a zero/absent field:", missing)


def auc_miss(rs, k):
    """Chance a missed spec scores higher than a landed one."""
    P = [r[k] for r in rs if not r["landed"]]
    N = [r[k] for r in rs if r["landed"]]
    return sum((p > n) + 0.5 * (p == n) for p in P for n in N) / (len(P) * len(N))


def rank(x):
    s = sorted(range(len(x)), key=lambda i: x[i])
    out = [0.0] * len(x)
    for k, i in enumerate(s):
        out[i] = k
    return out


random.seed(0)
feats = ["change_size", "touches", "criteria", "budget_usd", "elevated", "max_turns"]
print("\nfeature        AUC(miss)  95% interval     rho vs change_size")
for k in feats + ["agent_lands_it"]:
    bs = sorted(
        auc_miss(s, k)
        for s in ([random.choice(rows) for _ in rows] for _ in range(2000))
        if 0 < sum(not r["landed"] for r in s) < len(s)
    )
    rho = st.correlation(
        rank([r[k] for r in rows]), rank([r["change_size"] for r in rows])
    )
    print(
        f"{k:14} {auc_miss(rows, k):.3f}      [{bs[int(len(bs) * 0.025)]:.3f}, {bs[int(len(bs) * 0.975)]:.3f}]   {rho:+.2f}"
    )


def zs(rs, ks):
    out = []
    for k in ks:
        v = [r[k] for r in rs]
        m, sd = st.mean(v), st.pstdev(v) or 1.0
        out.append((m, sd))
    return out


def fit(train, ks, steps=3000, lr=0.1, l2=0.01):
    norm = zs(train, ks)

    def x(r):
        return [1.0] + [(r[k] - m) / sd for k, (m, sd) in zip(ks, norm, strict=True)]

    def dot(w, xi):
        return sum(a * b for a, b in zip(w, xi, strict=True))

    w = [0.0] * (len(ks) + 1)
    X = [x(r) for r in train]
    y = [0.0 if r["landed"] else 1.0 for r in train]
    for _ in range(steps):
        grad = [0.0] * len(w)
        for xi, yi in zip(X, y, strict=True):
            p = 1 / (1 + math.exp(-dot(w, xi)))
            for j in range(len(w)):
                grad[j] += (p - yi) * xi[j]
        w = [
            wj - lr * (gj / len(X) + l2 * wj * (j > 0))
            for j, (wj, gj) in enumerate(zip(w, grad, strict=True))
        ]
    return lambda r: dot(w, x(r))


def loo_auc(ks):
    """Leave-one-out: each spec is scored by a model fit without it."""
    scored = []
    for i, r in enumerate(rows):
        f = fit(rows[:i] + rows[i + 1 :], ks, steps=400)
        scored.append({"landed": r["landed"], "s": f(r)})
    return auc_miss(scored, "s")


fm = ["touches", "criteria", "budget_usd", "elevated"]
print("\nleave-one-out logistic AUC(miss)")
for ks in (
    fm,
    ["change_size"],
    fm + ["change_size"],
    fm + ["change_size", "agent_lands_it"],
):
    print(f"  {'+'.join(ks):55} {loo_auc(ks):.3f}")

print("\npaired bootstrap: AUC(change_size) minus AUC(other)")
for other in ("touches", "max_turns", "budget_usd"):
    diffs = []
    for _ in range(2000):
        s = [random.choice(rows) for _ in rows]
        if 0 < sum(not r["landed"] for r in s) < len(s):
            diffs.append(auc_miss(s, "change_size") - auc_miss(s, other))
    diffs.sort()
    lo, hi = diffs[int(len(diffs) * 0.025)], diffs[int(len(diffs) * 0.975)]
    print(
        f"  vs {other:10} {auc_miss(rows, 'change_size') - auc_miss(rows, other):+.3f}  [{lo:+.3f}, {hi:+.3f}]  P(diff<=0) {sum(d <= 0 for d in diffs) / len(diffs):.2f}"
    )
