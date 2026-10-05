"""How many stored attempt failures survive baseline subtraction.

`usage: python <this> <copy-of-ledger.db>`

Run it on a copy: `Ledger` opens the file for writing.
"""

import sys
from collections import Counter
from pathlib import Path

from saffron.gates.baseline import subtract_baseline
from saffron.ledger import Ledger

led = Ledger(Path(sys.argv[1]))
head_total = new_total = no_base = 0
per_attempt: list[int] = []
gates: Counter[str] = Counter()
rows = led._db.execute(
    "SELECT a.attempt_id, t.run_id FROM attempts a JOIN tasks t USING (task_id)"
).fetchall()
for attempt_id, run_id in rows:
    head = led.attempt_results(attempt_id)
    if not head:
        continue
    base = led.baseline_results(run_id)
    if not base:
        no_base += 1
    new = subtract_baseline(head, base)
    head_total += sum(len(r.failures) for r in head)
    new_total += len(new)
    per_attempt.append(len(new))
    gates.update(f.gate for f in new)
per_attempt.sort()
print("attempts with results", len(per_attempt), "without baseline", no_base)
print("head failures", head_total, "new failures", new_total)
print(
    "new per attempt: median", per_attempt[len(per_attempt) // 2],
    "p95", per_attempt[int(len(per_attempt) * 0.95)], "max", per_attempt[-1],
)
print("new by gate", gates.most_common(8))
