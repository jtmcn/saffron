"""Compare each packaged task's `pushed_sha` with its pull request's final head.

`docs/BACKLOG.md` item 97. Read-only: the ledger and `gh pr view`, no spend.
Run from the repo root: `uv run python docs/evidence/scripts/review_fixes_past_package.py`.
"""

import json
import sqlite3
import subprocess
from pathlib import Path

db = sqlite3.connect(Path.home() / ".saffron" / "ledger.db")
rows = db.execute(
    "SELECT spec_id, pushed_sha, pr_url FROM tasks "
    "WHERE pr_url IS NOT NULL AND pushed_sha IS NOT NULL ORDER BY task_id"
).fetchall()
moved = 0
for spec, pushed, url in rows:
    done = subprocess.run(
        ["gh", "pr", "view", url, "--json", "headRefOid,commits,state"],
        capture_output=True,
        text=True,
    )
    if done.returncode != 0:
        print(f"{spec} {url.rsplit('/', 1)[-1]} gh failed: {done.stderr.strip()}")
        continue
    pr = json.loads(done.stdout)
    head = pr["headRefOid"]
    shas = [c["oid"] for c in pr["commits"]]
    # `?`: the packaged commit is not in the PR's history — rewritten after PACKAGE.
    after = len(shas) - 1 - shas.index(pushed) if pushed in shas else "?"
    tag = "same" if head == pushed else "MOVED"
    moved += head != pushed
    print(
        f"{spec} #{url.rsplit('/', 1)[-1]} {pr['state']:6} pushed={pushed[:9]} "
        f"head={head[:9]} {tag} commits_after_package={after}"
    )
print(f"\n{moved}/{len(rows)} pull requests moved past what PACKAGE pushed")
