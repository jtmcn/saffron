# The fold rebuild at 223 tasks

Measured 2026-10-04 with `scripts/2026-09-20-fold-rebuild-time.py`, unchanged,
against a copy of `~/.saffron/ledger.db`. It reruns
`2026-09-20-fold-rebuild-time.md` at today's size. Read that record for what the
script proves and what it leaves out.

## The numbers

| | 2026-09-20 | 2026-10-04 |
|---|---|---|
| tasks folded | 118 | 223 |
| facts | 3,805 | 9,435 |
| **fold** | **9.94 s** | **22.63 s** |
| record built (not the fold) | 387.5 s | 735.2 s |
| fact JSON, uncompressed | 33.9 MB | 414.6 MB |
| loose, compressed bytes | 5.5 MB | 61.9 MB |
| loose, blocks allocated | 64.3 MB | 205.2 MB |
| largest single fact | 1.27 MB | 3.04 MB |
| ledger rebuilt | 30.6 MB | 378.7 MB |

Every table came back identical. `runs` folds 223 rows into 124, the collapse
on `base_sha` the earlier record declares.

```
  tasks             223 ->     223  identical
  attempts         1777 ->    1777  identical
  gate_results     4708 ->    4708  identical
  failures      1808217 -> 1808217  identical
  findings          250 ->     250  identical
  runs              223 ->     124  declared collapse on base_sha
```

## What it says

**The fold grows with the record, at about 0.1 s a task.** Tasks grew 1.9x and
the fold grew 2.3x. On demand costs an operator 23 s a morning today. At ten
tasks a night a year adds some six minutes. That is the reopen clause the
design names, and it lies months away.

**The record grew twelvefold while tasks did not double.** Inline failure lists
explain it. Failure rows went from 147,591 to 1,808,217. The earlier record
left open whether to carry failures by reference, cap them, or leave them.
This measurement makes that question the larger cost.

**The budget check is unaffected.** It folds the night's own tasks, so its cost
follows the night and never the record.
