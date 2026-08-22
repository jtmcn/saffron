"""The morning queue — an index, not a viewer (DESIGN.md §6).

ponytail: f-strings, not Jinja; see report/pr_body.py.
"""

from __future__ import annotations

import fcntl
import html
import json
import os
import tempfile
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path

_STATE_RANK = {
    "SKIPPED": 0,
    "SCOPE_REVIEW": 1,
    "MERGE_FAILED": 2,
    "PLAN_REJECTED": 2,
    # Ranked with the rest of what needs you rather than sorting in among
    # ordinary outcomes (§3.3): two infrastructure aborts, and an attempt that
    # produced nothing — which is the task's own failure, and exits 1, not 2.
    "PREFLIGHT_FAILED": 2,
    "GATE_ERROR": 2,
    "NOT_IMPLEMENTED": 2,
    # The rest of what `run_one_cell` can return or stamp. Absent, they fell to
    # `_ORDINARY` and sorted below elevated-risk green tasks: a task that could
    # not pass its own gates, or one whose cell died, reading as reviewable.
    "EXHAUSTED": 2,
    "ORPHANED": 2,
    # The provider's wall, not the task's: it needs you, and a retry is all it
    # needs. Absent, it sorted below green reviewable tasks.
    "RATE_LIMITED": 2,
    "REVIEWING": 3,
    "REBUTTING": 3,
}
_ORDINARY = 4


@dataclass
class QueueLine:
    """One task's entry in the index. Its outcome summary — never a verdict."""

    repo: str
    spec_id: str
    state: str
    attempts: int
    cost_usd_est: float | None
    concerns: int
    added: int
    removed: int
    link: str
    note: str = ""
    risk: str = "standard"


def sort_key(line: QueueLine) -> tuple[int, int, int, str]:
    """§6's order: dismiss in ten seconds, accept in two minutes.

    Skipped repos, then `SCOPE_REVIEW`, then the states that need you —
    `MERGE_FAILED`, `PLAN_REJECTED`, `PREFLIGHT_FAILED`, `GATE_ERROR` and
    `NOT_IMPLEMENTED` — then elevated risk, then concern count descending.
    Sorted by state, never grouped by repo.
    """
    rank = _STATE_RANK.get(line.state, 3 if line.risk == "elevated" else _ORDINARY)
    return (rank, -line.concerns, -line.attempts, line.spec_id)


def render_index(lines: list[QueueLine], *, header: dict[str, str]) -> str:
    rows = "\n".join(_row(line) for line in sorted(lines, key=sort_key))
    header_html = " · ".join(
        f"{html.escape(k)} <strong>{html.escape(v)}</strong>" for k, v in header.items()
    )
    return f"""<!doctype html>
<meta charset="utf-8">
<title>Saffron — morning queue</title>
<style>
  body {{ font: 14px/1.6 ui-monospace, SFMono-Regular, Menlo, monospace;
         margin: 2rem auto; max-width: 62rem; color: #111; }}
  header {{ margin-bottom: 1.5rem; color: #444; }}
  table {{ border-collapse: collapse; width: 100%; }}
  td {{ padding: .35rem .6rem; border-bottom: 1px solid #eee; white-space: nowrap; }}
  td.note {{ white-space: normal; color: #555; }}
  code {{ background: #f4f4f4; padding: .1rem .3rem; border-radius: 3px; }}
  @media (prefers-color-scheme: dark) {{
    body {{ background: #111; color: #eee; }}
    td {{ border-bottom-color: #262626; }}
    code {{ background: #1e1e1e; }}
    header {{ color: #aaa; }}
    td.note {{ color: #999; }}
  }}
</style>
<header>{header_html}</header>
<table>
{rows}
</table>
"""


def _row(line: QueueLine) -> str:
    cost = f"${line.cost_usd_est:.2f}" if line.cost_usd_est is not None else "—"
    concerns = f"{line.concerns} concern" + ("s" if line.concerns != 1 else "")
    cells = [
        html.escape(line.repo),
        html.escape(line.spec_id),
        f"<code>{html.escape(line.state)}</code>",
        f"{line.attempts} att",
        cost,
        concerns,
        f"+{line.added}/−{line.removed}",
        _link(line.link),
    ]
    note = (
        f'<td class="note">{html.escape(line.note)}</td>' if line.note else "<td></td>"
    )
    return "  <tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + note + "</tr>"


def _link(url: str) -> str:
    """A pull request is not an artifact directory. §6's own mock reads
    `→ PR #211`, and a link captioned `artifacts` sends you to the wrong
    mental model of the page."""
    if not url:
        return ""
    label = (
        f"PR #{url.rstrip('/').rsplit('/', 1)[-1]}" if "/pull/" in url else "artifacts"
    )
    return f'<a href="{html.escape(url)}">{html.escape(label)}</a>'


def append_queue_line(
    out_dir: Path, line: QueueLine, *, header: dict[str, str] | None = None
) -> Path:
    """§5.7 step 4. Append, then re-render from the whole list.

    Appending rather than rewriting is what lets a second task join a first
    without the batch orchestrator that does not exist yet (sub-project C).
    The rendered output is computed before any write, so a render failure
    cannot leave persisted rows.

    An upsert, not a bare append: re-running a spec after a `MERGE_FAILED` is
    the operator's normal response, and two rows for it render twice — the
    stale `MERGE_FAILED` (rank 2) sorting *above* the fresh `READY_FOR_REVIEW`
    (rank 4), showing a spec they already resolved as still needing them. The
    header's counts double with it. Keyed on repo *and* spec: one batch tree
    holds several repos, and spec ids are only unique within one.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    store = out_dir / "queue.json"
    with _locked(out_dir):
        _migrate_v0_store(store)
        # Validate all rows before computing output; unrenderable rows are dropped.
        lines = [
            row
            for row in _existing_queue_rows(store)
            if (row.repo, row.spec_id) != (line.repo, line.spec_id)
        ]
        lines.append(line)
        # Counted here, and a caller cannot override either: `out_dir` is shared
        # and rows accumulate, so a caller's one-task spend would report only the
        # last one.
        counted = {
            "tasks": str(len(lines)),
            "spend": f"${sum(ln.cost_usd_est or 0 for ln in lines):.2f}",
        }
        header = counted | {k: v for k, v in (header or {}).items() if k not in counted}
        # Compute all outputs before any write, so render failures leave nothing
        # behind.
        queue_json = json.dumps([asdict(ln) for ln in lines], indent=2)
        index_html = render_index(lines, header=header)
        _atomic_write(store, queue_json)
        index = out_dir / "index.html"
        _atomic_write(index, index_html)
    return index


@contextmanager
def _locked(out_dir: Path):
    """Serialise the read-modify-write. Two tasks appending at once otherwise
    lose whichever row was read first — the defect one store was meant to end.

    A sibling lock file, not `queue.json` itself: `_atomic_write` renames a new
    inode over it, so a lock held on the store would guard a file that no
    longer exists. `flock` releases on close, including on a raise.
    """
    with (out_dir / ".queue.lock").open("w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def _migrate_v0_store(store: Path) -> None:
    """v0 named this file `lines.json`. Renamed with no migration, an existing
    `~/.saffron/batches/v0` starts from zero rows: every prior task vanishes
    from `index.html` and the old file is left with no reader."""
    legacy = store.with_name("lines.json")
    if not store.exists() and legacy.is_file():
        legacy.rename(store)


def _existing_queue_rows(path: Path) -> list[QueueLine]:
    """Read existing queue.json, tolerating absence, corruption and hand edits.

    A row is usable iff the rendering *entry point* can consume it, so the
    validator calls `render_index` rather than one of its parts: `sort_key`
    runs before `_row` and negates `concerns`/`attempts`, so an `_row`-only
    check passed rows that then wedged the render. `except Exception` is the
    right net for a validator whose whole job is "does this survive rendering".

    ponytail: per-row drop, not a whole-file discard — one hand-edited row
    should not cost the queue its good rows. The drop is silent because the
    queue is a rendered convenience and the ledger is the system of record; log
    the dropped rows if anyone needs to ask why one vanished.
    """
    if not path.is_file():
        return []
    try:
        items = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(items, list):
        return []
    lines = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            line = QueueLine(**item)
            render_index([line], header={})
        except Exception:
            continue
        lines.append(line)
    return lines


def _atomic_write(path: Path, text: str) -> None:
    """Write via a same-directory temp file + rename, so a crash mid-write
    never leaves a truncated file for the next append to trip over."""
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.replace(tmp_name, path)
    except BaseException:
        os.unlink(tmp_name)
        raise
