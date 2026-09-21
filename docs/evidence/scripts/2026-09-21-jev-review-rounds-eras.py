"""Spike: bootstrap intervals for the review-round backtest, pooled and by era.

uv run python docs/evidence/scripts/2026-09-21-jev-review-rounds-eras.py <rounds.json>
"""

from __future__ import annotations

import datetime as dt
import json
import random
import statistics as st
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

FEATURES: dict[str, Callable[[dict], float]] = {
    "another_round_blocks": lambda r: r["answers"]["another_round_blocks"]["noul"],
    "fix_settles": lambda r: r["answers"]["fix_settles"]["noul"],
    "baseline:round": lambda r: r["round"],
    "baseline:diff_lines": lambda r: r["diff_lines"],
}


def auc(rs: list[dict], f: Callable[[dict], float]) -> float:
    pos = [f(r) for r in rs if r["more"]]
    neg = [f(r) for r in rs if not r["more"]]
    return sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (
        len(pos) * len(neg)
    )


def report(label: str, rs: list[dict]) -> None:
    print(
        f"{label}: {sum(r['more'] for r in rs)} more, {sum(not r['more'] for r in rs)} final"
    )
    for name, f in FEATURES.items():
        bs = sorted(
            auc(s, f)
            for s in ([random.choice(rs) for _ in rs] for _ in range(2000))
            if 0 < sum(r["more"] for r in s) < len(s)
        )
        lo, hi = bs[int(len(bs) * 0.025)], bs[int(len(bs) * 0.975)]
        print(f"  {name:22} {auc(rs, f):.3f} [{lo:.3f}, {hi:.3f}]")


def main() -> None:
    d = json.loads(Path(sys.argv[1]).read_text())
    for r in d:
        out = subprocess.run(
            ["git", "show", "-s", "--format=%ct", r["sha"]],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        r["t"] = int(out)
    d.sort(key=lambda r: r["t"])
    random.seed(0)
    for kind in ("all", "spec", "code"):
        report(kind, [r for r in d if kind in ("all", r["kind"])])
    third = len(d) // 3
    for name, rs in (
        ("oldest third", d[:third]),
        ("middle third", d[third : 2 * third]),
        ("newest third", d[2 * third :]),
    ):
        first, last = (dt.date.fromtimestamp(rs[i]["t"]) for i in (0, -1))
        report(f"{name} {first} to {last}", rs)
    v = sorted(r["answers"]["another_round_blocks"]["noul"] for r in d)
    print(
        f"another_round_blocks p25 {v[len(v) // 4]:.2f} "
        f"median {st.median(v):.2f} p75 {v[3 * len(v) // 4]:.2f}"
    )


if __name__ == "__main__":
    main()
