"""Spike: do Jev's grades of a spec's text predict whether a cell lands it?

Throwaway. Labels come from the ledger, spec text from git by sha256, and
grades from TypeSafe's HTTP API. Needs TYPESAFE_API_KEY in the environment.

    uv run python docs/evidence/scripts/2026-09-21-jev-spec-grading.py --out <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

LEDGER = Path.home() / ".saffron" / "ledger.db"
ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.13.0"
LANDED = {"MERGED"}
MISSED = {"EXHAUSTED", "PLAN_REJECTED", "NOT_IMPLEMENTED"}
SPEC_PATH = re.compile(r"^\.saffron/specs/(?:.*/)?(SA-\d{4})-[^/]*\.md$")

QUESTIONS = {
    "criteria_checkable": {
        "type": "score",
        "instructions": (
            "The `spec` is a task for an autonomous coding agent. How concretely does each "
            "acceptance claim state an outcome a test can observe?"
        ),
        "criteria": [
            "Claims are aspirations or vague qualities with no observable outcome",
            "Some claims name an observable outcome, others stay vague",
            "Most claims name an observable outcome but leave inputs or expected values open",
            "Every claim names exact inputs, an observable outcome and the test that checks it",
        ],
    },
    "wrong_impl_excluded": {
        "type": "score",
        "instructions": (
            "The `spec` is a task for an autonomous coding agent. How well does the spec rule out "
            "a plausible wrong implementation that would still pass its named witness tests?"
        ),
        "criteria": [
            "No witness tests or mutants are named, so a wrong implementation could pass",
            "Witnesses are named but an obvious wrong implementation would still pass them",
            "Witnesses and mutants cover the main claim, with gaps on secondary claims",
            "Every claim has a witness and a mutant that a wrong implementation would fail",
        ],
    },
    "scope_bounded": {
        "type": "score",
        "instructions": (
            "The `spec` is a task for an autonomous coding agent. How precisely do its `touches` "
            "and `forbidden` lists match the files the described change must edit?"
        ),
        "criteria": [
            "No file scope is given, or it plainly omits files the change must edit",
            "Scope is given but loose or likely missing a caller or test file",
            "Scope names the main files with a small risk of a missing one",
            "Scope names exactly the files the change must edit and forbids the rest",
        ],
    },
    "change_size": {
        "type": "score",
        "instructions": (
            "The `spec` is a task for an autonomous coding agent. How large and entangled is the "
            "change it asks for?"
        ),
        "criteria": [
            "One small edit in one file",
            "A focused change across two or three files",
            "A change across several modules with new tests",
            "A cross-cutting change touching many modules, contracts and tests at once",
        ],
    },
    "one_reading": {
        "type": "noul",
        "instructions": (
            "The `spec` is a task for an autonomous coding agent. Could two careful engineers "
            "read this spec and build materially different implementations that both satisfy it?"
        ),
    },
    "agent_lands_it": {
        "type": "noul",
        "instructions": (
            "The `spec` is a task for an autonomous coding agent working alone, within a fixed "
            "budget, against hard test and lint gates. Will the agent implement it correctly on "
            "its own?"
        ),
    },
}


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], check=True, capture_output=True).stdout


def spec_texts() -> dict[str, tuple[str, str]]:
    """Every committed spec blob, keyed by the sha256 the ledger records."""
    out: dict[str, tuple[str, str]] = {}
    for line in (
        git("rev-list", "--all", "--objects", "--", ".saffron/specs")
        .decode()
        .splitlines()
    ):
        blob, _, path = line.partition(" ")
        m = SPEC_PATH.match(path)
        if not m:
            continue
        raw = git("cat-file", "blob", blob)
        out.setdefault(hashlib.sha256(raw).hexdigest(), (m.group(1), raw.decode()))
    return out


def labelled() -> list[dict]:
    """One row per spec version: landed if any task on it merged, missed if none did."""
    rows = sqlite3.connect(f"file:{LEDGER}?mode=ro", uri=True).execute(
        "SELECT spec_id, spec_sha, state FROM tasks"
    )
    states: dict[tuple[str, str], set[str]] = {}
    for spec_id, sha, state in rows:
        states.setdefault((spec_id, sha), set()).add(state)
    texts = spec_texts()
    out = []
    for (spec_id, sha), seen in sorted(states.items()):
        if seen & LANDED:
            landed = True
        elif seen & MISSED:
            landed = False
        else:
            continue
        if sha not in texts:
            print(f"skip {spec_id}: no committed text hashes to {sha[:12]}")
            continue
        out.append(
            {
                "spec_id": spec_id,
                "spec_sha": sha,
                "landed": landed,
                "text": texts[sha][1],
            }
        )
    return out


def grade(key: str, text: str) -> dict:
    body = json.dumps(
        {"state": {"spec": text}, "model": MODEL, "questions": QUESTIONS}
    ).encode()
    for backoff in (1, 2, 4, 8, 16, 0):
        req = urllib.request.Request(
            ENDPOINT,
            data=body,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
        )
        start = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code in (429, 529) and backoff:
                time.sleep(backoff)
                continue
            raise RuntimeError(f"{e.code}: {e.read().decode()[:500]}") from e
        result["latency_s"] = time.monotonic() - start
        return result
    raise RuntimeError("retries exhausted")


def read_key(path: Path) -> str:
    """The TYPESAFE_API_KEY assignment in a shell secrets file, read as text."""
    for line in path.read_text().splitlines():
        m = re.match(r"^\s*(?:export\s+)?TYPESAFE_API_KEY=(.*)$", line)
        if m:
            return m.group(1).strip().strip("'\"")
    raise SystemExit(f"no TYPESAFE_API_KEY line in {path}")


def auc(pos: list[float], neg: list[float]) -> float:
    """Mann-Whitney: the chance a landed spec outscores a missed one."""
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def value(answer: dict) -> float:
    return answer["noul"] if answer["type"] == "noul" else answer["score"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--key-file", type=Path, default=Path.home() / ".secrets")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    key = os.environ.get("TYPESAFE_API_KEY") or read_key(args.key_file)

    data = labelled()[: args.limit]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda r: grade(key, r["text"]), data))
    for row, res in zip(data, results, strict=True):
        row["answers"] = res["answers"]
        row["usage"] = res["usage"]
        row["latency_s"] = res["latency_s"]
        row["chars"] = len(row.pop("text"))
    (args.out / "grades.json").write_text(json.dumps(data, indent=1))

    landed = [r for r in data if r["landed"]]
    missed = [r for r in data if not r["landed"]]
    print(f"{len(landed)} landed, {len(missed)} missed, model {MODEL}")
    features: dict[str, Callable[[dict], float]] = {
        q: (lambda r, q=q: value(r["answers"][q])) for q in QUESTIONS
    }
    # Baselines: a grade that only tracks length or spec age says nothing new.
    features["baseline:chars"] = lambda r: r["chars"]
    features["baseline:spec_number"] = lambda r: int(r["spec_id"][3:])
    for name, f in features.items() if landed and missed else ():
        a = auc([f(r) for r in landed], [f(r) for r in missed])
        print(f"{name:24} AUC {a:.3f}  (|AUC-0.5| {abs(a - 0.5):.3f})")
    tokens = sum(r["usage"]["input_tokens"] for r in data)
    lat = sorted(r["latency_s"] for r in data)
    print(f"input tokens {tokens}, cost ${tokens * 0.042 / 1e6:.4f}")
    print(f"latency p50 {lat[len(lat) // 2]:.2f}s max {lat[-1]:.2f}s")


if __name__ == "__main__":
    main()
