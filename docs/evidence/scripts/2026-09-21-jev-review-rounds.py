"""Spike: after a review round, does Jev know whether another round will find a defect?

Throwaway. Each `review(SA-NNNN)` commit on main is one round that found something.
A loop is one spec's rounds of one kind: spec rounds edit `.saffron/specs/`, code
rounds do not. Round N is labelled `more` when round N+1 exists in its loop.

    uv run python docs/evidence/scripts/2026-09-21-jev-review-rounds.py --out <dir> [--dry]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.13.0"
SUBJECT = re.compile(r"^review\((SA-\d{4})\): ")
SPEC_CHARS = 45_000
DIFF_CHARS = 30_000
HISTORY_CHARS = 8_000

QUESTIONS = {
    "another_round_blocks": {
        "type": "noul",
        "instructions": (
            "A reviewer read the `spec` and found the defects described in "
            "`this_round.message`. The fix in `this_round.diff` was applied. "
            "`earlier_rounds` lists what previous rounds found. Would one more "
            "independent review round find another defect serious enough to fix?"
        ),
    },
    "fix_settles": {
        "type": "noul",
        "instructions": (
            "Does the change in `this_round.diff` fully settle every defect "
            "`this_round.message` names, without opening a new gap of the same kind?"
        ),
    },
}


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout


def rounds() -> list[dict]:
    """Every review round on main, oldest first, with its loop and label."""
    log = git(
        "log",
        "origin/main",
        "--no-merges",
        "--reverse",
        "--format=%x00%H%x01%B%x01",
        "--name-only",
    )
    loops: dict[tuple[str, str], list[dict]] = {}
    for rec in log.split("\x00")[1:]:
        sha, body, names = rec.split("\x01")
        subject = body.strip().splitlines()[0]
        m = SUBJECT.match(subject)
        if not m:
            continue
        files = [n for n in names.split("\n") if n]
        kind = "spec" if any(f.startswith(".saffron/specs/") for f in files) else "code"
        loops.setdefault((m.group(1), kind), []).append(
            {"sha": sha, "spec_id": m.group(1), "kind": kind, "message": body.strip()}
        )
    out = []
    for loop in loops.values():
        for n, r in enumerate(loop):
            r["round"] = n + 1
            r["more"] = n + 1 < len(loop)
            r["earlier"] = [p["message"].splitlines()[0] for p in loop[:n]]
            out.append(r)
    return out


def spec_text(sha: str, spec_id: str) -> str:
    paths = git("ls-tree", "-r", "--name-only", sha, ".saffron/specs").split()
    hit = [p for p in paths if Path(p).name.startswith(f"{spec_id}-")]
    return git("show", f"{sha}:{hit[0]}") if hit else ""


def state(r: dict) -> dict:
    diff = git("show", "--format=", r["sha"])
    r["diff_lines"] = sum(
        1
        for line in diff.splitlines()
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    )
    r["message_chars"] = len(r["message"])
    return {
        "spec": spec_text(r["sha"], r["spec_id"])[:SPEC_CHARS],
        "earlier_rounds": "\n".join(r["earlier"])[-HISTORY_CHARS:],
        "this_round": {"message": r["message"], "diff": diff[:DIFF_CHARS]},
    }


def read_key(path: Path) -> str:
    for line in path.read_text().splitlines():
        m = re.match(r"^\s*(?:export\s+)?TYPESAFE_API_KEY=(.*)$", line)
        if m:
            return m.group(1).strip().strip("'\"")
    raise SystemExit(f"no TYPESAFE_API_KEY line in {path}")


def ask(key: str, st: dict) -> dict:
    body = json.dumps({"state": st, "model": MODEL, "questions": QUESTIONS}).encode()
    for backoff in (1, 2, 4, 8, 16, 0):
        req = urllib.request.Request(
            ENDPOINT,
            data=body,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code in (429, 529) and backoff:
                time.sleep(backoff)
                continue
            raise RuntimeError(f"{e.code}: {e.read().decode()[:500]}") from e
    raise RuntimeError("retries exhausted")


def auc(rows: list[dict], f: Callable[[dict], float]) -> float:
    """The chance a round with more to come outscores a final round."""
    pos = [f(r) for r in rows if r["more"]]
    neg = [f(r) for r in rows if not r["more"]]
    return sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (
        len(pos) * len(neg)
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--key-file", type=Path, default=Path.home() / ".secrets")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    data = rounds()
    states = [state(r) for r in data]
    for kind in ("spec", "code"):
        rs = [r for r in data if r["kind"] == kind]
        loops = {r["spec_id"] for r in rs}
        print(
            f"{kind}: {len(loops)} loops, {len(rs)} rounds, {sum(r['more'] for r in rs)} with more"
        )
    print(f"largest state {max(len(json.dumps(s)) for s in states)} chars")
    if args.dry:
        return

    key = os.environ.get("TYPESAFE_API_KEY") or read_key(args.key_file)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda s: ask(key, s), states))
    for r, res in zip(data, results, strict=True):
        r["answers"] = res["answers"]
        r["input_tokens"] = res["usage"]["input_tokens"]
    (args.out / "rounds.json").write_text(json.dumps(data, indent=1))

    features: dict[str, Callable[[dict], float]] = {
        q: (lambda r, q=q: r["answers"][q]["noul"]) for q in QUESTIONS
    }
    # Baselines: what the loop already knows without a model.
    features["baseline:round"] = lambda r: r["round"]
    features["baseline:diff_lines"] = lambda r: r["diff_lines"]
    features["baseline:message_chars"] = lambda r: r["message_chars"]
    for kind in ("all", "spec", "code"):
        rs = [r for r in data if kind in ("all", r["kind"])]
        print(
            f"\n{kind}: {sum(r['more'] for r in rs)} more, {sum(not r['more'] for r in rs)} final"
        )
        for name, f in features.items():
            print(f"  {name:24} AUC {auc(rs, f):.3f}")
    tokens = sum(r["input_tokens"] for r in data)
    print(f"\ninput tokens {tokens}, cost ${tokens * 0.042 / 1e6:.4f}")


if __name__ == "__main__":
    main()
