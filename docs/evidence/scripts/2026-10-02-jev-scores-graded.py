"""Grade Jev's saved answers against the delegate's labels of the same review rounds.

`usage: python <this>`

Reads every round under `~/.saffron/batches/spec-loop/` that holds a `jev.ttl`,
a `labels.json` and a `findings.json`. Read-only, and it makes no call.
AUC is the chance a score ranks a positive case above a negative one.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from collections.abc import Sequence
from typing import Any

ROOT = Path.home() / ".saffron" / "batches" / "spec-loop"
ASSERTION = re.compile(
    r"earl:subject <urn:software-factory:jev:[^:]+:[^:]+:([^>]+)> ;\s*"
    r"earl:test jev:(Q\d) ;.*?jev:distribution (\".*?\")\^\^rdf:JSON",
    re.S,
)
SEVERITY = {"blocker": 3, "concern": 2, "note": 1}
ACTED = {
    "fixed-pre-cell",
    "fixed-in-review",
    "deferred-to-seat",
    "operator-decided",
    "filed-backlog",
}
FOLLOWED = ("next_spec_round", "cell_review", "pr_seats")


def answers(ttl: Path) -> dict[str, dict[str, dict[str, float]]]:
    out: dict[str, dict[str, dict[str, float]]] = {}
    for subject, question, literal in ASSERTION.findall(ttl.read_text()):
        out.setdefault(subject, {})[question] = json.loads(json.loads(literal))
    return out


def auc(pos: Sequence[float], neg: Sequence[float]) -> str:
    if not pos or not neg:
        return "n/a"
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return f"{wins / (len(pos) * len(neg)):.3f}"


def load() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    rounds: list[dict[str, Any]] = []
    for d in sorted(ROOT.glob("*/*/round-*")):
        ttl, lab, fj = d / "jev.ttl", d / "labels.json", d / "findings.json"
        if not (ttl.is_file() and lab.is_file() and fj.is_file()):
            continue
        kind, scored = d.parent.name, answers(ttl)
        labels = json.loads(lab.read_text())
        raw = {f["id"]: f for f in json.loads(fj.read_text())}
        for fid, label in (labels.get("findings") or {}).items():
            got = scored.get(fid, {})
            q2 = got.get("Q2")
            findings.append(
                {
                    "kind": kind,
                    "verified": label.get("verified"),
                    "disposition": label.get("disposition"),
                    "severity": raw.get(fid, {}).get("severity"),
                    "q2_mean": sum(int(k) * v for k, v in q2.items()) if q2 else None,
                    "q2_noise": q2.get("0") if q2 else None,
                    "q3": got.get("Q3", {}).get("true"),
                    "q1_nomatch": got.get("Q1", {}).get("noMatch"),
                    "q4": got.get("Q4", {}).get("true"),
                }
            )
        followed = labels.get("blocker_followed") or {}
        rounds.append(
            {
                "kind": kind,
                "q6": scored.get(d.name, {}).get("Q6", {}).get("true"),
                "blockers": sum(f.get("severity") == "blocker" for f in raw.values()),
                **{k: followed.get(k) for k in FOLLOWED},
            }
        )
    return findings, rounds


def per_finding(findings: list[dict[str, Any]]) -> None:
    for kind in ("spec-review", "pr-review", "all"):
        rows = [
            r
            for r in findings
            if r["verified"] in ("real", "not-a-defect")
            and kind in ("all", r["kind"])
        ]
        real = [r for r in rows if r["verified"] == "real"]
        not_a_defect = [r for r in rows if r["verified"] == "not-a-defect"]
        print(f"{kind}: {len(real)} real, {len(not_a_defect)} not-a-defect")
        for feature, sign in (
            ("q2_noise", -1),
            ("q2_mean", 1),
            ("q3", 1),
            ("q1_nomatch", -1),
        ):
            pos = [sign * r[feature] for r in real if r[feature] is not None]
            neg = [sign * r[feature] for r in not_a_defect if r[feature] is not None]
            print(f"  real vs not-a-defect  {feature:10s} {auc(pos, neg)}")
        pos = [SEVERITY.get(r["severity"], 0) for r in real]
        neg = [SEVERITY.get(r["severity"], 0) for r in not_a_defect]
        print(f"  real vs not-a-defect  reviewer severity {auc(pos, neg)}")
        acted = [r["q3"] for r in rows if r["q3"] is not None and r["disposition"] in ACTED]
        idle = [r["q3"] for r in rows if r["q3"] is not None and r["disposition"] == "no-action"]
        print(f"  acted vs no-action    q3 {auc(acted, idle)}")
        print(f"  Q4 answers: {sum(r['q4'] is not None for r in rows)}")


def by_severity(findings: list[dict[str, Any]]) -> None:
    for severity in SEVERITY:
        rows = [
            r
            for r in findings
            if r["severity"] == severity and r["verified"] in ("real", "not-a-defect")
        ]
        pos = [-r["q2_noise"] for r in rows if r["verified"] == "real"]
        neg = [-r["q2_noise"] for r in rows if r["verified"] == "not-a-defect"]
        print(f"{severity}: {len(pos)} real, {len(neg)} not-a-defect, q2_noise {auc(pos, neg)}")
    real = [r for r in findings if r["verified"] == "real"]
    not_a_defect = [r for r in findings if r["verified"] == "not-a-defect"]
    for cut in (0.3, 0.5, 0.7):
        flagged_real = [r for r in real if r["q2_noise"] >= cut]
        flagged_not = sum(r["q2_noise"] >= cut for r in not_a_defect)
        print(
            f"q2_noise >= {cut}: {flagged_not}/{len(not_a_defect)} not-a-defect, "
            f"{len(flagged_real)}/{len(real)} real, of which no-action "
            f"{sum(r['disposition'] == 'no-action' for r in flagged_real)}"
        )


def per_round(rounds: list[dict[str, Any]]) -> None:
    for kind in ("spec-review", "pr-review"):
        for target in FOLLOWED:
            rows = [
                r
                for r in rounds
                if r["kind"] == kind and isinstance(r[target], bool) and r["q6"] is not None
            ]
            if not rows:
                print(f"{kind} vs {target}: no labelled rounds")
                continue
            base = sum(r[target] for r in rows) / len(rows)
            brier = sum((r["q6"] - r[target]) ** 2 for r in rows) / len(rows)
            q6 = [r["q6"] for r in rows]
            print(
                f"{kind} vs {target}: n={len(rows)} base={base:.2f} "
                f"Q6 AUC={auc([r['q6'] for r in rows if r[target]], [r['q6'] for r in rows if not r[target]])} "
                f"blockers AUC={auc([r['blockers'] for r in rows if r[target]], [r['blockers'] for r in rows if not r[target]])} "
                f"Brier={brier:.3f} constant={base * (1 - base):.3f} "
                f"Q6 range {min(q6):.2f}-{max(q6):.2f}"
            )


def main() -> None:
    findings, rounds = load()
    print(f"findings {len(findings)}, rounds {len(rounds)}")
    print(f"verified {dict(Counter(r['verified'] for r in findings))}")
    print(f"rounds {dict(Counter(r['kind'] for r in rounds))}\n")
    per_finding(findings)
    print()
    by_severity(findings)
    print()
    per_round(rounds)


if __name__ == "__main__":
    main()
