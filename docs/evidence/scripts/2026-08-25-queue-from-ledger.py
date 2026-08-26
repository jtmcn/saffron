"""Issue #28: §6's morning queue rendered from the ledger, not from `queue.json`.

Renders §6's morning queue from `~/.saffron/ledger.db` instead of from the
`queue.json` store PACKAGE appends to, and shows where the two disagree.
Reuses the real `render_index`/`QueueLine`/`sort_key` so the page under test
is the shipped one; only the *source* is new.

    uv run python docs/evidence/scripts/2026-08-25-queue-from-ledger.py
"""

from __future__ import annotations

import html
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from saffron.report.index import QueueLine, render_index, sort_key  # noqa: E402

LEDGER = Path.home() / ".saffron" / "ledger.db"
STORE = Path.home() / ".saffron" / "batches" / "v0" / "queue.json"
OUT = Path("/tmp/2026-08-25-queue-from-ledger.html")

# `attempts` rows are one per phase-session (§4.1: "`phase` is the state the
# task was in when the turn started"), so COUNT(*) is turns, not attempts.
# A repair-loop attempt is the initial implement plus each REPAIRING cycle.
ROWS = """
SELECT r.name AS repo, t.spec_id, t.state, t.risk, t.pr_url,
       t.spent_usd_est AS cost,
       1 + (SELECT COUNT(*) FROM attempts a
             WHERE a.task_id = t.task_id AND a.phase = 'REPAIRING') AS attempts,
       (SELECT COUNT(*) FROM findings f
         WHERE f.task_id = t.task_id AND f.severity = 'concern'
           AND f.anchored = 1) AS concerns,
       (SELECT COUNT(*) FROM findings f
         WHERE f.task_id = t.task_id AND f.severity = 'blocker'
           AND f.anchored = 1 AND f.verdict = 'confirmed'
           AND f.rebuttal LIKE 'argued:%') AS sustained_blockers,
       (SELECT COUNT(*) FROM findings f
         WHERE f.task_id = t.task_id AND f.severity = 'blocker'
           AND f.anchored = 1 AND f.verdict = 'confirmed'
           AND f.rebuttal LIKE 'fixed:%') AS confirmed_then_fixed,
       (SELECT COUNT(*) FROM gate_results g
         WHERE g.run_id = runs.run_id) AS baseline_results
  FROM tasks t
  JOIN runs  ON runs.run_id = t.run_id
  JOIN repos r ON r.repo_id = runs.repo_id
 ORDER BY t.task_id
"""


def load():
    db = sqlite3.connect(f"file:{LEDGER}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        return db.execute(ROWS).fetchall()
    finally:
        db.close()


def main() -> None:
    rows = load()
    lines = [
        QueueLine(
            repo=r["repo"],
            spec_id=r["spec_id"],
            state=r["state"],
            attempts=r["attempts"],
            cost_usd_est=r["cost"],
            concerns=r["concerns"],
            # HOLE 1: the ledger records no diff stat. Only queue.json has it.
            added=0,
            removed=0,
            link=r["pr_url"] or "",
            note="",
            risk=r["risk"],
        )
        for r in rows
    ]

    page = render_index(
        lines,
        header={
            "batch": "— (no `batches` table)",
            "tasks": str(len(lines)),
            "spend": f"${sum(r['cost'] or 0 for r in rows):.2f}",
            "wall clock": "— (no batch row)",
            "trailing accept rate": "— (nothing records a merge)",
        },
    )

    store = {(d["repo"], d["spec_id"]): d for d in json.loads(STORE.read_text())}
    diffs = []
    for r, line in zip(rows, lines, strict=True):
        was = store.get((r["repo"], r["spec_id"]))
        if not was:
            continue
        for field, ledger_v in (
            ("risk", line.risk),
            ("attempts", line.attempts),
            ("concerns", line.concerns),
        ):
            if was[field] != ledger_v:
                diffs.append((r["spec_id"], field, was[field], ledger_v))

    extra = [
        "<h2>Ledger vs the queue.json PACKAGE wrote</h2>",
        "<table>",
        "<tr><td><strong>spec</strong></td><td><strong>field</strong></td>"
        "<td><strong>queue.json</strong></td><td><strong>ledger</strong></td></tr>",
        *(
            f"<tr><td>{html.escape(s)}</td><td>{f}</td>"
            f"<td>{was}</td><td>{now}</td></tr>"
            for s, f, was, now in diffs
        ),
        "</table>",
        "<h2>What the sort actually separated</h2>",
        "<table>",
        *(
            f"<tr><td>{html.escape(q.spec_id)}</td><td>{html.escape(q.state)}</td>"
            f"<td>risk={html.escape(q.risk)}</td>"
            f"<td>rank={sort_key(q)[0]}</td><td>concerns={q.concerns}</td></tr>"
            for q in sorted(lines, key=sort_key)
        ),
        "</table>",
        "<h2>Blockers the page has no column for</h2>",
        "<table>",
        *(
            f"<tr><td>{html.escape(r['spec_id'])}</td>"
            f"<td>{r['sustained_blockers']} sustained (argued + confirmed)</td>"
            f"<td>{r['confirmed_then_fixed']} confirmed after a fix</td>"
            f"<td>rendered as “{r['concerns']} concern(s)”</td></tr>"
            for r in rows
            if r["sustained_blockers"] or r["confirmed_then_fixed"]
        ),
        "</table>",
        "<h2>Baseline gate results per run</h2>",
        "<table>",
        *(
            f"<tr><td>{html.escape(r['spec_id'])}</td>"
            f"<td>{r['baseline_results']} rows with run_id</td></tr>"
            for r in rows
        ),
        "</table>",
    ]
    OUT.write_text(page + "\n".join(extra))
    print(f"wrote {OUT}  ({len(lines)} rows, {len(diffs)} disagreements)")
    for s, f, was, now in diffs:
        print(f"  {s:9} {f:9} queue.json={was!r:12} ledger={now!r}")


if __name__ == "__main__":
    main()
