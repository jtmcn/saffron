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

from saffron.cell.worktree import STATUS_ARGS, porcelain_paths
from saffron.gates.contract import GateResult
from saffron.gates.core.revert import _argv_safe
from saffron.gates.runner import run_gate
from saffron.repos.image import BASE_TAG
from saffron.repos.policy import Policy, PolicyError, load_policy

# `FROM saffron/cell-base:`, with any runtime after the colon.
BASE_PREFIX = "FROM " + BASE_TAG.rsplit(":", 1)[0] + ":"


def layout_problems(repo: Path) -> list[str]:
    """What a cell needs beside the policy: a Dockerfile on core's base, and a queue."""
    problems = []
    dockerfile = repo / ".saffron" / "Dockerfile"
    if not dockerfile.is_file():
        problems.append(f"{dockerfile} is missing")
    elif not any(
        line.startswith(BASE_PREFIX) for line in dockerfile.read_text().splitlines()
    ):
        problems.append(f"{dockerfile} does not start {BASE_PREFIX}<runtime>")
    if not (repo / ".saffron" / "specs").is_dir():
        problems.append(f"{repo / '.saffron' / 'specs'} is missing")
    return problems


def collected_problems(full: GateResult) -> list[str]:
    """`census`, `criteria`, `revert` and `witness` each read `collected`."""
    if not full.collected:
        return [
            "tests: reports no `collected`, so `census`, `criteria`, `revert` "
            "and `witness` skip"
        ]
    codes = {f.code for f in full.failures}
    if codes and not codes & set(full.collected):
        return ["tests: no failure `code` is a collected name, so `criteria` skips"]
    return []


def subset_problems(name: str, probe: GateResult) -> list[str]:
    """The witness probe's two refusals (`runner.run_witness`)."""
    if probe.status == "error":
        return [f"tests: a one-name subset errored: {probe.summary}"]
    if probe.collected is None or set(probe.collected) - {name}:
        return [f"tests: handed {name!r}, it collected more than that name"]
    return []


def dirty_paths(repo: Path) -> set[str]:
    done = subprocess.run(
        ["git", *STATUS_ARGS], cwd=repo, capture_output=True, text=True, check=True
    )
    return set(porcelain_paths(done.stdout))


def run_gates(repo: Path, policy: Policy) -> list[str]:
    problems = []
    for name, executable in policy.gate_executables(repo).items():
        result = run_gate(name, executable, repo)
        print(f"{name:12} {result.status:6} {result.tool or '-':24} {result.summary}")
        if result.status == "error":
            problems.append(f"{name}: error: {result.summary}")
            continue
        if name != "tests":
            continue
        problems += collected_problems(result)
        probe_name = next((n for n in result.collected or [] if _argv_safe(n)), None)
        if probe_name is not None:
            probe = run_gate(name, executable, repo, subset=[probe_name])
            problems += subset_problems(probe_name, probe)
    return problems


def check(repo: Path) -> list[str]:
    problems = layout_problems(repo)
    try:
        policy, _ = load_policy(repo)
    except PolicyError as exc:
        return [*problems, f"policy: {exc}"]
    # The onboarding itself is uncommitted, so only a path the gates add counts.
    before = dirty_paths(repo)
    problems += run_gates(repo, policy)
    problems += [
        f"committed: a gate left {path}, which .gitignore does not cover"
        for path in sorted(dirty_paths(repo) - before)
    ]
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
