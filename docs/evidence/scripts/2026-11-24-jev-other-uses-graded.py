"""Grade Jev's other saved answers against later outcomes, after Q2's noise test failed.

`usage: uv run python <this>`

Reads every review round under `~/.saffron/batches/spec-loop/`. Read-only, and it makes
no call. AUC is the chance a score ranks a positive case above a negative one.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from saffron.intake import load_spec

ROOT = Path.home() / ".saffron" / "batches" / "spec-loop"
ASSERTION = re.compile(
    r"earl:subject <urn:software-factory:jev:[^:]+:[^:]+:([^>]+)> ;\s*"
    r"earl:test jev:(Q\d) ;.*?jev:distribution (\".*?\")\^\^rdf:JSON",
    re.S,
)
SEVERITY = {"blocker": 3, "concern": 2, "note": 1}
LEFT = {"no-action", "deferred-to-seat", "filed-backlog"}
Row = dict[str, Any]


def answers(ttl: Path) -> dict[tuple[str, str], dict[str, float]]:
    return {
        (question, subject): json.loads(json.loads(literal))
        for subject, question, literal in ASSERTION.findall(ttl.read_text())
    }


def auc(pos: Sequence[float], neg: Sequence[float]) -> str:
    if not pos or not neg:
        return "n/a"
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return f"{wins / (len(pos) * len(neg)):.3f}"


def rounds(spec: Path, kind: str) -> list[Path]:
    found = [p for p in (spec / kind).glob("round-*") if p.is_dir()]
    return sorted(found, key=lambda p: int(p.name.removeprefix("round-")))


def claims(spec_md: Path) -> list[str] | None:
    try:
        spec, _sha = load_spec(spec_md)
    except Exception:
        return None
    return [c.claim for c in spec.acceptance] or list(spec.acceptance_criteria)


def findings(directory: Path) -> list[Row]:
    path = directory / "findings.json"
    return json.loads(path.read_text()) if path.is_file() else []


def table(
    rows: list[Row], outcome: str, scores: dict[str, Callable[[Row], float]]
) -> None:
    pos = [r for r in rows if r[outcome]]
    neg = [r for r in rows if not r[outcome]]
    for name, score in scores.items():
        print(
            f"  {name:38s} AUC {auc([score(r) for r in pos], [score(r) for r in neg])}"
        )


def criteria_vs_pr_blockers() -> None:
    """Q7, Q8 and Q9 at the last spec review round, against a PR seat blocker on that criterion."""
    rows: list[Row] = []
    for spec in sorted(ROOT.glob("SA-*")):
        reviewed = [
            r
            for r in rounds(spec, "spec-review")
            if (r / "jev.ttl").is_file() and (r / "spec.md").is_file()
        ]
        if not reviewed or not rounds(spec, "pr-review"):
            continue
        last = reviewed[-1]
        texts = claims(last / "spec.md")
        if not texts:
            continue
        said = answers(last / "jev.ttl")
        cited: Counter[int] = Counter()
        for r in rounds(spec, "spec-review"):
            for f in findings(r):
                if isinstance(f.get("criterion"), int):
                    cited[f["criterion"]] += 1
        hit: Counter[int] = Counter()
        for r in rounds(spec, "pr-review"):
            pr_texts = claims(r / "spec.md") if (r / "spec.md").is_file() else None
            if not pr_texts:
                continue
            for f in findings(r):
                k = f.get("criterion")
                if (
                    f["severity"] == "blocker"
                    and isinstance(k, int)
                    and 1 <= k <= len(pr_texts)
                    and pr_texts[k - 1] in texts
                ):
                    hit[texts.index(pr_texts[k - 1]) + 1] += 1
        for k, text in enumerate(texts, 1):
            q7, q8 = said.get(("Q7", f"c{k}")), said.get(("Q8", f"c{k}"))
            if q7 is None or q8 is None:
                continue
            q9 = said.get(("Q9", f"c{k}"), {})
            rows.append(
                {
                    "spec": spec.name,
                    "q7": q7["true"],
                    "q8": q8["true"],
                    "q9": 1 - q9.get("none", 1.0),
                    "cited": cited[k],
                    "length": len(text),
                    "blocked": hit[k] > 0,
                }
            )
    blocked = sum(r["blocked"] for r in rows)
    specs = len({r["spec"] for r in rows})
    print(
        f"criteria vs PR seat blockers: {len(rows)} criteria, {specs} specs, {blocked} blocked"
    )
    table(
        rows,
        "blocked",
        {
            "1 - Q7 (testable)": lambda r: 1 - r["q7"],
            "1 - Q8 (names its evidence)": lambda r: 1 - r["q8"],
            "Q9 (conflicts)": lambda r: r["q9"],
            "spec review findings citing it": lambda r: r["cited"],
            "criterion length": lambda r: r["length"],
        },
    )


def criteria_vs_rewrite() -> None:
    """Q7 and Q8 at spec review round N, against the criterion's text changing by round N+1."""
    rows: list[Row] = []
    for spec in sorted(ROOT.glob("SA-*")):
        saved = [r for r in rounds(spec, "spec-review") if (r / "spec.md").is_file()]
        for a, b in zip(saved, saved[1:], strict=False):
            if not (a / "jev.ttl").is_file():
                continue
            before, after = claims(a / "spec.md"), claims(b / "spec.md")
            if not before or not after:
                continue
            said = answers(a / "jev.ttl")
            cited: Counter[int] = Counter()
            for f in findings(a):
                if isinstance(f.get("criterion"), int):
                    cited[f["criterion"]] += SEVERITY[f["severity"]]
            for k, text in enumerate(before, 1):
                q7, q8 = said.get(("Q7", f"c{k}")), said.get(("Q8", f"c{k}"))
                if q7 is None or q8 is None:
                    continue
                rows.append(
                    {
                        "spec": spec.name,
                        "q7": q7["true"],
                        "q8": q8["true"],
                        "cited": cited[k],
                        "length": len(text),
                        "rewritten": text not in after,
                    }
                )
    rewritten = sum(r["rewritten"] for r in rows)
    specs = len({r["spec"] for r in rows})
    print(
        f"criteria vs a rewrite next round: {len(rows)} criteria, {specs} specs, {rewritten} rewritten"
    )
    jev: dict[str, Callable[[Row], float]] = {
        "1 - Q7": lambda r: 1 - r["q7"],
        "1 - Q8": lambda r: 1 - r["q8"],
    }
    table(
        rows,
        "rewritten",
        {
            **jev,
            "same round's citations, by severity": lambda r: r["cited"],
            "criterion length": lambda r: r["length"],
        },
    )
    uncited = [r for r in rows if r["cited"] == 0]
    print(
        f"  criteria the reviewer did not cite: {len(uncited)}, {sum(r['rewritten'] for r in uncited)} rewritten"
    )
    table(uncited, "rewritten", jev)


def q5_next_round() -> None:
    """Q5 asked at round N+1 about a finding of round N, against that finding's disposition."""
    fixed: list[float] = []
    left: list[float] = []
    for spec in ROOT.glob("SA-*"):
        saved = rounds(spec, "spec-review")
        for a, b in zip(saved, saved[1:], strict=False):
            if not ((a / "labels.json").is_file() and (b / "jev.ttl").is_file()):
                continue
            labels = json.loads((a / "labels.json").read_text()).get("findings", {})
            said = answers(b / "jev.ttl")
            for f in findings(a):
                label, q5 = labels.get(f["id"]), said.get(("Q5", f["id"]))
                if not isinstance(label, dict) or q5 is None:
                    continue
                if label.get("disposition") == "fixed-pre-cell":
                    fixed.append(q5["true"])
                elif label.get("disposition") in LEFT:
                    left.append(q5["true"])
    print(
        f"Q5 at the next round: fixed {len(fixed)}, left {len(left)}, AUC {auc(fixed, left)}, "
        f"mean P(addressed) fixed {sum(fixed) / len(fixed):.2f} left {sum(left) / len(left):.2f}"
    )


def labelled() -> list[Row]:
    """Every schema-2 labelled finding with a Q2 answer, with its kind and severity."""
    out: list[Row] = []
    for kind in ("cell", "spec-review", "pr-review"):
        for spec in ROOT.glob("SA-*"):
            for r in rounds(spec, kind):
                if not ((r / "labels.json").is_file() and (r / "jev.ttl").is_file()):
                    continue
                doc = json.loads((r / "labels.json").read_text())
                if doc.get("schema") != 2:
                    continue
                said = answers(r / "jev.ttl")
                for f in findings(r):
                    label, q2 = doc["findings"].get(f["id"]), said.get(("Q2", f["id"]))
                    if label and q2 is not None:
                        out.append(
                            {"kind": kind, "severity": f["severity"], "q2": q2, **label}
                        )
    return out


def q2_noise(rows: list[Row]) -> None:
    """Q2's probability of severity 0, separating `not-a-defect` from `real`."""
    print("Q2 noise, not-a-defect against real")
    groups: dict[tuple[str, str], tuple[list[float], list[float]]] = {}
    for r in rows:
        if r["verified"] not in ("real", "not-a-defect"):
            continue
        noise, real = groups.setdefault((r["kind"], r["severity"]), ([], []))
        (noise if r["verified"] == "not-a-defect" else real).append(
            r["q2"].get("0", 0.0)
        )
    for (kind, severity), (noise, real) in sorted(groups.items()):
        print(
            f"  {kind:12s} {severity:8s} noise {len(noise):3d} real {len(real):4d}  AUC {auc(noise, real)}"
        )


def acted_on(rows: list[Row]) -> None:
    """Among real findings, acted on against left alone: Q2's expected severity and the reviewer's."""
    print("real findings acted on against left alone")
    for kind in ("pr-review", "spec-review", "cell"):
        real = [r for r in rows if r["kind"] == kind and r["verified"] == "real"]
        acted = [r for r in real if r["disposition"] != "no-action"]
        left = [r for r in real if r["disposition"] == "no-action"]

        def expected(r: Row) -> float:
            return sum(int(k) * v for k, v in r["q2"].items())

        print(
            f"  {kind:12s} acted {len(acted):4d} left {len(left):3d}  "
            f"Q2 expected severity AUC {auc([expected(r) for r in acted], [expected(r) for r in left])}  "
            f"reviewer severity AUC {auc([SEVERITY[r['severity']] for r in acted], [SEVERITY[r['severity']] for r in left])}"
        )


def main() -> None:
    criteria_vs_pr_blockers()
    criteria_vs_rewrite()
    q5_next_round()
    rows = labelled()
    q2_noise(rows)
    acted_on(rows)


if __name__ == "__main__":
    main()
