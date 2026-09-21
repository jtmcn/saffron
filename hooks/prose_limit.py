#!/usr/bin/env python3
"""The `prose` gate's limit, applied to a commit and to each edit.

Each staged file in scope, Markdown or Python, may not carry more hits of
any `prose` rule than its `HEAD` version. A new file compares against zero, and a rename
against its old path. The gate gets the same limit from baseline subtraction.
Standard library only, like the gate it loads.

With `--edited`, a Claude Code PostToolUse hook: the edited file's new hits
for both gates go to stderr with exit 2, which Claude Code shows the model.
PostToolUse cannot block, because the edit already happened.

With `--file <path>`, the same question about one file in the working tree,
answered on stdout before anything is staged.
"""

from __future__ import annotations

import importlib.util
import json
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
    # Registered first: `Hit` is a dataclass under postponed annotations.
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


def new_hits(
    prose: Any, root: Path, gate: str, path: str, old_text: str | None, new_text: str
) -> list[Any]:
    """Hits in `new_text` with no matching excerpt in `old_text`, counted."""
    before = Counter(
        f.excerpt for f in prose.check(old_text or "", path, gate, root=root)
    )
    fresh = []
    for hit in prose.check(new_text, path, gate, root=root):
        if before[hit.excerpt]:
            before[hit.excerpt] -= 1
        else:
            fresh.append(hit)
    return fresh


def rises(
    prose: Any, root: Path, gate: str, path: str, old_text: str | None, new_text: str
) -> dict[str, tuple[int, int]]:
    """Rule codes whose count went up, as `code -> (before, after)`."""
    before = Counter(f.code for f in prose.check(old_text or "", path, gate, root=root))
    after = Counter(f.code for f in prose.check(new_text, path, gate, root=root))
    return {code: (before[code], n) for code, n in after.items() if n > before[code]}


def risen_hits(
    prose: Any, root: Path, gate: str, path: str, old_text: str | None, new_text: str
) -> tuple[dict[str, tuple[int, int]], list[Any]]:
    """The codes whose count rose, and the new hits of those codes."""
    risen = rises(prose, root, gate, path, old_text, new_text)
    fresh = new_hits(prose, root, gate, path, old_text, new_text)
    return risen, [hit for hit in fresh if hit.code in risen]


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
        risen, hits = risen_hits(prose, root, "prose", new, old_text, new_text)
        for code, (was, now) in sorted(risen.items()):
            print(f"{new}: {code} rose from {was} to {now}")
            failed = True
        for hit in hits:
            print(f"  {new}:{hit.line}: {hit.code}: {hit.excerpt}")
    return 1 if failed else 0


def _in_repo(root: Path, file_path: Path) -> str | None:
    try:
        return file_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def _against_head(root: Path, path: str, file_path: Path) -> tuple[str | None, str]:
    """The file at `HEAD` or None, and the working tree's copy of it."""
    head = _git(root, "show", f"HEAD:{path}")
    return (
        head.stdout if head.returncode == 0 else None,
        file_path.read_text(encoding="utf-8", errors="replace"),
    )


def _risen_lines(
    prose: Any, root: Path, path: str, old_text: str | None, new_text: str
) -> list[str]:
    # Only a code whose count actually rose, like `commit_time` does: an
    # untouched hit sharing its line with an edit is not new.
    lines = []
    for gate in prose.GATES:
        _, hits = risen_hits(prose, root, gate, path, old_text, new_text)
        lines += [f"{path}:{hit.line}: {hit.code}: {hit.excerpt}" for hit in hits]
    return lines


def file_time(root: Path, raw_path: str) -> int:
    """What the gates would count for one path, staged or not.

    The question `commit_time` answers about the index and `edit_time` about an
    edit, asked about a file in hand. A new file compares against zero
    (backlog item b-929465).
    """
    file_path = Path(raw_path)
    if not file_path.is_absolute():
        file_path = root / file_path
    path = _in_repo(root, file_path)
    prose = load_prose()
    if path is None or not prose.in_scope(path):
        print(f"out of the gates' scope: {raw_path}", file=sys.stderr)
        return 2
    if not file_path.is_file():
        print(f"no such file: {raw_path}", file=sys.stderr)
        return 2
    old_text, new_text = _against_head(root, path, file_path)
    lines = _risen_lines(prose, root, path, old_text, new_text)
    baseline = "HEAD" if old_text is not None else "zero"
    plural = "" if len(lines) == 1 else "s"
    print(f"{path}: {len(lines)} new hit{plural} against {baseline}", *lines, sep="\n")
    return 1 if lines else 0


def edit_time(root: Path, event: object) -> int:
    """Print the edited file's new hits for the model. The edit already happened."""
    if not isinstance(event, dict):
        return 0
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0
    raw_path = tool_input.get("file_path", "")
    if not isinstance(raw_path, str):
        return 0
    file_path = Path(raw_path)
    if not file_path.is_absolute():
        cwd = event.get("cwd")
        file_path = (Path(cwd) if isinstance(cwd, str) else root) / file_path
    path = _in_repo(root, file_path)
    prose = load_prose()
    if path is None or not prose.in_scope(path) or not file_path.is_file():
        return 0
    old_text, new_text = _against_head(root, path, file_path)
    lines = _risen_lines(prose, root, path, old_text, new_text)
    if not lines:
        return 0
    print(
        "New house-style hits (.saffron/gates/prose.py):",
        *lines,
        sep="\n",
        file=sys.stderr,
    )
    return 2


def main(argv: list[str]) -> int:
    if argv == ["--edited"]:
        try:
            event = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            return 0
        return edit_time(Path.cwd(), event)
    if len(argv) == 2 and argv[0] == "--file":
        return file_time(Path.cwd(), argv[1])
    if argv:
        print(f"unexpected arguments: {argv}", file=sys.stderr)
        return 2
    return commit_time(Path.cwd())


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
