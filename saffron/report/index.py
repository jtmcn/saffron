"""The morning queue — an index, not a viewer (DESIGN.md §6).

ponytail: f-strings, not Jinja; see report/pr_body.py.
"""

from __future__ import annotations

import html
from dataclasses import dataclass

_STATE_RANK = {"SKIPPED": 0, "SCOPE_REVIEW": 1, "MERGE_FAILED": 2, "PLAN_REJECTED": 2}
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

    Skipped repos, then `SCOPE_REVIEW`, then `MERGE_FAILED`/`PLAN_REJECTED`,
    then elevated risk, then concern count descending. Sorted by state, never
    grouped by repo.
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
        f'<a href="{html.escape(line.link)}">artifacts</a>' if line.link else "",
    ]
    note = f'<td class="note">{html.escape(line.note)}</td>' if line.note else "<td></td>"
    return "  <tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + note + "</tr>"
