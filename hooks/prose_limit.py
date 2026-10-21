#!/usr/bin/env python3
"""The `prose` gate's limit, applied to a commit and to each edit.

Each staged file in scope, Markdown or Python, must not carry a `prose` hit its
`HEAD` version lacks. A hit is its sentence, or its block's name and length. A new
file compares against zero, and a rename against its old path. The gate gets the
same limit from baseline subtraction (backlog item b-044ae7).
Standard library only, like the gate it loads.

With `--edited`, a Claude Code PostToolUse hook: the edited file's new hits
for both gates go to stderr with exit 2, which Claude Code shows the model.
PostToolUse cannot block, because the edit already happened.

With `--file <path>`, the same question about one file in the working tree,
answered on stdout before anything is staged.

With `--tree`, the commit mode's question asked of the whole working tree
instead of the index: every changed or untracked file, read at its
working-tree content, printed in the commit mode's format.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from collections import Counter
from collections.abc import Callable
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


def _diff_pairs(root: Path, *extra: str) -> list[tuple[str | None, str]]:
    """`(path at HEAD or None, new path)` for each added, modified or renamed
    file `git diff <extra>` reports."""
    done = _git(root, "diff", *extra, "--name-status", "-M", "-z", "--diff-filter=AMR")
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


def staged(root: Path) -> list[tuple[str | None, str]]:
    """`(path at HEAD or None, staged path)` for each added, modified or renamed file."""
    return _diff_pairs(root, "--cached")


def tree_pairs(root: Path) -> list[tuple[str | None, str]]:
    """`staged`'s pairs against the working tree instead of the index, plus
    every untracked file git does not ignore."""
    others = _git(root, "ls-files", "-z", "--others", "--exclude-standard")
    others.check_returncode()
    untracked = [(None, p) for p in others.stdout.split("\0") if p]
    return _diff_pairs(root, "HEAD") + untracked


def _identity(hit: Any) -> tuple[str, str]:
    return hit.code, hit.key or hit.excerpt


def new_hits(
    prose: Any, root: Path, gate: str, path: str, old_text: str | None, new_text: str
) -> list[Any]:
    """Hits in `new_text` whose identity `old_text` lacks, counted, the way
    baseline subtraction reads the gate's messages."""
    before = Counter(
        _identity(f) for f in prose.check(old_text or "", path, gate, root=root)
    )
    fresh = []
    for hit in prose.check(new_text, path, gate, root=root):
        if before[_identity(hit)]:
            before[_identity(hit)] -= 1
        else:
            fresh.append(hit)
    return fresh


def _show(root: Path, spec: str) -> str:
    done = _git(root, "show", spec)
    done.check_returncode()
    return done.stdout


def _report(
    prose: Any,
    root: Path,
    pairs: list[tuple[str | None, str]],
    new_text_of: Callable[[str], str | None],
) -> int:
    """New `prose` hits for each `(old, new)` pair whose new text `new_text_of`
    can read, printed in the commit mode's format."""
    failed = False
    for old, new in pairs:
        if not prose.in_scope(new):
            continue
        new_text = new_text_of(new)
        if new_text is None:
            continue
        old_text = _show(root, f"HEAD:{old}") if old else None
        hits = new_hits(prose, root, "prose", new, old_text, new_text)
        for code, n in sorted(Counter(hit.code for hit in hits).items()):
            print(f"{new}: {n} new {code} hit{'' if n == 1 else 's'}")
            failed = True
        for hit in hits:
            print(f"  {new}:{hit.line}: {hit.code}: {hit.excerpt}")
    return 1 if failed else 0


def commit_time(root: Path) -> int:
    prose = load_prose()
    return _report(prose, root, staged(root), lambda new: _show(root, f":{new}"))


def tree_time(root: Path) -> int:
    """The commit mode's question, asked of the working tree."""
    prose = load_prose()

    def read(new: str) -> str | None:
        file_path = root / new
        return _working_copy(file_path) if file_path.is_file() else None

    return _report(prose, root, tree_pairs(root), read)


def _in_repo(root: Path, file_path: Path) -> str | None:
    try:
        return file_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def _working_copy(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8", errors="replace")


def _against_head(root: Path, path: str, file_path: Path) -> tuple[str | None, str]:
    """The file at `HEAD` or None, and the working tree's copy of it."""
    head = _git(root, "show", f"HEAD:{path}")
    return (
        head.stdout if head.returncode == 0 else None,
        _working_copy(file_path),
    )


def _new_lines(
    prose: Any, root: Path, path: str, old_text: str | None, new_text: str
) -> list[str]:
    # An untouched hit sharing its line with an edit is not new.
    lines = []
    for gate in prose.GATES:
        hits = new_hits(prose, root, gate, path, old_text, new_text)
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
    # A path that is not there is answered before scope: "out of the gates'
    # scope" for a typo in a filename reads as a rule, not as a miss.
    if not file_path.is_file():
        print(f"no such file: {raw_path}", file=sys.stderr)
        return 2
    path = _in_repo(root, file_path)
    prose = load_prose()
    if path is None or not prose.in_scope(path):
        print(f"out of the gates' scope: {raw_path}", file=sys.stderr)
        return 2
    old_text, new_text = _against_head(root, path, file_path)
    lines = _new_lines(prose, root, path, old_text, new_text)
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
    lines = _new_lines(prose, root, path, old_text, new_text)
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
    if argv == ["--tree"]:
        return tree_time(Path.cwd())
    if argv:
        print(f"unexpected arguments: {argv}", file=sys.stderr)
        return 2
    return commit_time(Path.cwd())


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
