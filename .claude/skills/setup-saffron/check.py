#!/usr/bin/env python3
"""Check a target repo's `.saffron/` the way Saffron will read it.

It loads the policy with Saffron's own loader. It runs every declared gate on
the host through `run_gate`, so a contract rule changed in `saffron/` changes
here too. Exit `0` means nothing was found, `1` that something was.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from saffron.gates.contract import GateResult
from saffron.gates.runner import run_gate
from saffron.repos.policy import Policy, PolicyError, load_policy

BASE_PREFIX = "FROM saffron/cell-base:"


def layout_problems(repo: Path) -> list[str]:
    """What a cell needs beside the policy: a Dockerfile on core's base, and a queue."""
    problems = []
    dockerfile = repo / ".saffron" / "Dockerfile"
    if not dockerfile.is_file():
        problems.append(f"{dockerfile} is missing")
    elif not any(
        line.startswith(BASE_PREFIX) for line in dockerfile.read_text().splitlines()
    ):
        problems.append(f"{dockerfile} does not build {BASE_PREFIX}<runtime>")
    if not (repo / ".saffron" / "specs").is_dir():
        problems.append(f"{repo / '.saffron' / 'specs'} is missing")
    return problems


def result_problems(result: GateResult) -> list[str]:
    """`fail` at base is fine: the baseline subtracts it. `error` never is."""
    if result.status == "error":
        return [f"{result.gate}: error: {result.summary}"]
    return []


def tests_problems(full: GateResult, subset: GateResult | None) -> list[str]:
    """`census`, `criteria` and `revert` each need one more thing of `tests`."""
    problems = []
    if not full.collected:
        problems.append(
            "tests: reports no `collected`, so `census` and `criteria` skip"
        )
        return problems
    codes = {f.code for f in full.failures}
    if codes and not codes & set(full.collected):
        problems.append(
            "tests: no failure `code` is a collected name, so `criteria` skips"
        )
    if subset is not None and subset.status == "error":
        problems.append(f"tests: a one-name subset errored: {subset.summary}")
    return problems


def dirty_paths(repo: Path) -> list[str]:
    """What `committed` would fail on after the suite: a gate's leftovers."""
    out = subprocess.run(
        ["git", "status", "--porcelain", "-uall"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [line[3:] for line in out.splitlines()]


def check(repo: Path) -> list[str]:
    problems = layout_problems(repo)
    try:
        policy, _ = load_policy(repo)
    except PolicyError as exc:
        return [*problems, f"policy: {exc}"]
    problems += run_gates(repo, policy)
    problems += [f"committed: a gate left {p} in the tree" for p in dirty_paths(repo)]
    return problems


def run_gates(repo: Path, policy: Policy) -> list[str]:
    problems = []
    for name, executable in policy.gate_executables(repo).items():
        result = run_gate(name, executable, repo)
        print(f"{name:12} {result.status:6} {result.tool or '-':24} {result.summary}")
        problems += result_problems(result)
        if name == "tests" and result.status != "error":
            subset = None
            if result.collected:
                subset = run_gate(name, executable, repo, subset=result.collected[:1])
            problems += tests_problems(result, subset)
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path, help="the target repo's root")
    args = parser.parse_args(argv)
    problems = check(args.repo.resolve())
    for problem in problems:
        print(f"PROBLEM {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
