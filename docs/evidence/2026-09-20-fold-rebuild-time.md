# What it costs to delete the index and fold it back

Measured 2026-09-20 on macOS 25.6, `git 2.51.0`, Python 3.14.7, APFS. The
instrument is `scripts/2026-09-20-fold-rebuild-time.py`; it copies the ledger
first and writes nothing to `~/.saffron`.

## Which artifact establishes which half of the criterion

Design §4's criterion — delete the index, rebuild it, get the same rows — is
proved in two places and neither alone is enough.

- `tests/test_fold.py` pins the **mechanism** on a fixture it builds itself. It
  can only show the fold agreeing with a night the same process wrote, so it
  proves the rules and not the corpus. It is the half that runs in CI, because
  a unit test cannot depend on a developer's private `~/.saffron/ledger.db`.
- `scripts/2026-09-20-fold-rebuild-time.py` carries the **real-nights** claim.
  It ends by comparing `synth.db`, the ledger `_synthesize` built from the real
  ledger's own write methods, against `rebuilt.db`, the fold's output, as
  multisets, and prints the verdict. Neither is the real `~/.saffron/ledger.db`
  copy: `record_key` alone differs on all 118 rows against that copy, so this
  is the closest comparison the script can make, and what it proves is real —
  118 stored tasks' shapes came back. `_SAME` (the script's own comparison
  columns) leaves out `runs.preflight`/`status`/`ended_at`, `batches`,
  `repos.*`, `tasks.updated_at`, `findings.adjudication`, and every parent id,
  so `tasks 118 -> 118 identical` is not "the real ledger came back" — it is
  "the fold's rules reproduce what `_synthesize` fed them." Anyone with a
  ledger can re-run it; the table below is its output, not a transcription.

## Why the benchmark synthesises its own record

The plan's step said to fold `~/.saffron/mirrors/saffron.git`. There is no
record on any ref yet — the appends landed the same week — so folding a real
mirror measures zero tasks. Instead the script replays the real ledger's 118
tasks through `Ledger`'s own write methods into a throwaway `RefsRecord`, which
produces the fact shapes and counts a night actually appends, then folds that.
Real shapes and real counts, not a synthetic corpus; what it cannot claim is
that facts written a night at a time pack as the ones written in one pass do.

Source: a copy of `~/.saffron/ledger.db`, 51,515,392 bytes, 118 tasks, 626
attempts, 1,971 attempt-scoped gate results, 250,136 failure rows, 149 findings.

## The numbers

| | |
|---|---|
| tasks folded | 118 |
| facts | 3,805 |
| **fold, loose record** | **90.61 s** |
| fold, after `git gc --aggressive` | 89.70 s |
| index rebuilt | 30.6 MB |
| record built (not the fold) | 363.4 s |

The fold is 24 ms per fact, and almost all of it is `git cat-file` one fact at a
time. Packing the record saves 1%, so the cost is process spawns, not object
lookup — the shape a batched `cat-file --batch` would move and that nothing else
would.

It reads the record **twice**: once to order tasks by the time their
`task_created` fact was appended, once to replay them. Key order will not do —
a record key is random hex, and `ORDER BY t.task_id` is read as a chronology by
`queue_lines` and `tasks_by_spec` — and holding 33.9 MB of fact JSON in memory
to sort by one field of it is the wrong trade for a tool that has to survive a
year of nights. Half of the 90 s is that choice, and it is reversible.

Building the record took four times as long as folding it, because
`RefsRecord.append` rewrites the whole facts tree per fact. That is the write
path's number, not the fold's, and it is here so the 90 s is not read as the
system's whole cost.

## What came back

The script's own comparison, every table as a multiset:

```
  tasks             118 ->     118  identical
  attempts          626 ->     626  identical
  gate_results     1971 ->    1971  identical
  failures       147591 ->  147591  identical
  findings          149 ->     149  identical
  runs              118 ->      74  declared collapse on base_sha
```

`tasks` there includes `pushed_sha`, `pr_url`, `policy_sha` and
`merged_head_sha` — the columns `queue_lines` and `reconcile` read, and the
ones a criterion that excluded them could not have shown dropped. `attempts`
includes `started_at` and `ended_at`, so the times came back too and not the
fold's own clock.

`error` and `fail` stay apart at scale: 1,631 `pass`, 194 `fail`, 145 `skip`,
1 `error`.

**The 74 is the one disagreement, and it is declared.** `fold` keys a run on
`(repo_id, base_sha)` because `batch_key` is NULL on every task stored today,
so the batch-and-repo identity design §5 gives a run cannot serve yet. 118 runs
off 74 distinct base commits fold into 74 rows. The `ponytail:` comment in
`saffron/record/fold.py` names it; the run and batch folds are the next plan's.

The 147,591 against the ledger's 250,136 is not a loss either: the difference is
baseline failures, which hang off a run's gate results, belong to no task, and
are appended by nothing.

## What the record costs on disk

| | |
|---|---|
| fact JSON, uncompressed | 33.9 MB across 3,805 facts |
| median fact | 315 bytes |
| **largest single fact** | **1,273,877 bytes (1.27 MB)** |
| facts over 1 MB | 27 |
| facts between 100 KB and 1 MB | 0 |
| loose, compressed bytes | 5.5 MB |
| loose, blocks allocated | 64.3 MB |
| packed (`git gc --aggressive`) | one 2.32 MiB pack, 2,916,352 bytes allocated |

Three quantities that differ by an order of magnitude, which is why the script
prints all three: `st_size` alone reads as the smallest of them and flatters the
record by 12x.

The largest fact is one `prose` gate result carrying 5,693 failures inline. The
distribution has no middle: a fact is a few hundred bytes or it is a megabyte,
and which one it is depends entirely on how many failures the gate found.

**This is not the size the design argued from.** `DESIGN.md` reasons from a
2026-09-17 measurement of 6.7 MB for 102 tasks — about 65 KB of facts per task.
The same quantity today is 287 KB per task uncompressed, four times that, and
the whole of the gap is inline failure lists. Two readings of the same fact,
both true:

- **Uncompressed, it is worse than assumed.** 33.9 MB of JSON, and a single
  append that hands git a 1.27 MB blob.
- **Packed, it is better.** 2.32 MiB for all 118 tasks, 20 KB per task, because
  27 near-identical megabyte failure lists delta against each other almost
  perfectly. A record that is gc'd and pushed costs less than the design
  supposed; one left loose costs 64 MB of allocated blocks for 5.5 MB of
  content.

Nothing here is a proposal. What to do about a multi-megabyte fact — carry
failures by reference, cap them, or leave them — is a decision this record does
not make.

## One measurement the fold's code cites

`_discard_task` says a `with` block around the replay would not roll it back.
That is measured, not supposed:

```
>>> with db:
...     db.execute('INSERT INTO t VALUES (1)')
...     db.commit()            # what every Ledger write method does
...     db.execute('INSERT INTO t VALUES (2)')
...     raise RuntimeError('boom')
rows after the rollback: [(1,)]
```

`Ledger`'s methods commit as they go, so the inner `COMMIT` ends the outer
transaction and the first row survives. The fold therefore compensates — a task
that fails mid-replay is deleted rather than rolled back — and says so where it
does it.

## What this record does not establish

**Steady-state growth.** One pass, one repo, one host. Whether a record written
a night at a time packs as well, and what a year of nights costs, is unmeasured.

**Push.** Nothing was pushed. Whether a remote accepts a 1.27 MB blob on
`refs/saffron/*` at the rate a night produces them is untested; the 2026-09-17
record covers only that the namespace is accepted at all.

**Concurrency.** The fold ran alone against a record nothing was writing.

**`task_policy`.** Ten of the eleven fact kinds the fold replays are exercised
above. `task_policy` is not, because nothing in a stored row says whether
`record_policy` ran after creation or the `policy_sha` came from `create_task`;
the unit tests pin it instead.

## The clause that would reopen it

A fold that stops fitting in the window an operator will wait through — or a
remote that refuses the blobs. The first is a factor of forty away at
`cat-file --batch` plus a single read pass; the second is untested.
