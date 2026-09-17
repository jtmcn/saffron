#!/usr/bin/env python3
"""The `prose` gate's limit, applied to a commit.

Each staged Markdown file in scope may not carry more findings of any `prose`
rule than its `HEAD` version. A new file compares against zero, and a rename
against its old path. The gate gets the same limit from baseline subtraction.
Standard library only, like the gate it loads.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PROSE = Path(__file__).resolve().parent.parent / ".saffron" / "gates" / "prose.py"


def load_prose() -> Any:
    spec = importlib.util.spec_from_file_location("saffron_prose_gate", PROSE)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(PROSE)
    module = importlib.util.module_from_spec(spec)
    # Registered first: `Finding` is a dataclass under postponed annotations.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def staged(root: Path) -> list[tuple[str | None, str]]:
    """`(path at HEAD or None, staged path)` for each added, modified or renamed file."""
    done = _git(
        root, "diff", "--cached", "--name-status", "-M", "-z", "--diff-filter=AMR"
    )
    done.check_returncode()
    fields = done.stdout.split("\0")
    pairs: list[tuple[str | None, str]] = []
    i = 0
    while i < len(fields) and fields[i]:
        status = fields[i]
        if status.startswith("R"):
            pairs.append((fields[i + 1], fields[i + 2]))
            i += 3
        else:
            pairs.append((None if status == "A" else fields[i + 1], fields[i + 1]))
            i += 2
    return pairs


def new_findings(
    prose: Any, root: Path, gate: str, path: str, old_text: str | None, new_text: str
) -> list[Any]:
    """Findings in `new_text` with no matching excerpt in `old_text`, counted."""
    before = Counter(
        f.excerpt for f in prose.check(old_text or "", path, gate, root=root)
    )
    fresh = []
    for finding in prose.check(new_text, path, gate, root=root):
        if before[finding.excerpt]:
            before[finding.excerpt] -= 1
        else:
            fresh.append(finding)
    return fresh


def rises(
    prose: Any, root: Path, gate: str, path: str, old_text: str | None, new_text: str
) -> dict[str, tuple[int, int]]:
    """Rule codes whose count went up, as `code -> (before, after)`."""
    before = Counter(f.code for f in prose.check(old_text or "", path, gate, root=root))
    after = Counter(f.code for f in prose.check(new_text, path, gate, root=root))
    return {code: (before[code], n) for code, n in after.items() if n > before[code]}


def _show(root: Path, spec: str) -> str:
    done = _git(root, "show", spec)
    done.check_returncode()
    return done.stdout


def commit_time(root: Path) -> int:
    prose = load_prose()
    failed = False
    for old, new in staged(root):
        if not prose.in_scope(new):
            continue
        old_text = _show(root, f"HEAD:{old}") if old else None
        new_text = _show(root, f":{new}")
        risen = rises(prose, root, "prose", new, old_text, new_text)
        for code, (was, now) in sorted(risen.items()):
            print(f"{new}: {code} rose from {was} to {now}")
            failed = True
        for finding in new_findings(prose, root, "prose", new, old_text, new_text):
            if finding.code in risen:
                print(f"  {new}:{finding.line}: {finding.code}: {finding.excerpt}")
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    if argv:
        print(f"unexpected arguments: {argv}", file=sys.stderr)
        return 2
    return commit_time(Path.cwd())


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
