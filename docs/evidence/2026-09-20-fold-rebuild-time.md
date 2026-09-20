# What it costs to delete the index and fold it back

Measured 2026-09-20 on macOS 25.6, `git 2.51.0`, Python 3.14.7, APFS. The
instrument is `scripts/2026-09-20-fold-rebuild-time.py`; it copies the ledger
first and writes nothing to `~/.saffron`.

## Why the benchmark synthesises its own record

The plan's step said to fold `~/.saffron/mirrors/saffron.git`. There is no
record on any ref yet — Task 4 landed the appends the same week — so folding a
real mirror measures zero tasks. Instead the script replays the real ledger's
118 tasks through `Ledger`'s own write methods into a throwaway `RefsRecord`,
which produces the fact shapes and counts a night actually appends, then folds
that. Real shapes and real counts, not a synthetic corpus; what it cannot claim
is that facts written a night at a time pack as the ones written in one pass do.

Source: a copy of `~/.saffron/ledger.db`, 51,515,392 bytes, 118 tasks, 626
attempts, 1,971 attempt-scoped gate results, 250,136 failure rows.

## The numbers

| | |
|---|---|
| tasks folded | 118 |
| facts | 3,458 |
| **fold, loose record** | **44.63 s** |
| fold, after `git gc --aggressive` | 42.40 s |
| index rebuilt | 30.4 MB |
| record built (not the fold) | 337.6 s |

The fold is 13 ms per fact, and almost all of it is `git cat-file` one fact at a
time: 3,458 subprocesses. Packing the record saves 5%, so the cost is process
spawns, not object lookup — the shape that a batched `cat-file --batch` would
move and that nothing else would.

Building the record took seven times as long as folding it, because
`RefsRecord.append` rewrites the whole facts tree per fact. That is the write
path's number, not the fold's, and it is here so the 44 s is not read as the
system's whole cost.

## What came back

Every table the fold writes, compared as a multiset against the ledger the facts
were synthesised from:

```
                 source   rebuilt
repos                 1         1
runs                118        74
tasks               118       118   rows identical, record_key included
attempts            626       626   identical
gate_results      1,971     1,971   identical
failures        147,591   147,591   identical
```

`error` and `fail` stay apart at scale: 1,631 `pass`, 194 `fail`, 145 `skip`,
1 `error`.

**The 74 is the one disagreement, and it is declared.** `fold` keys a run on
`(repo_id, base_sha)` because no fact carries a run identity, so 118 runs off 74
distinct base commits fold into 74 rows. The run and batch folds are the next
plan's; the `ponytail:` comment in `saffron/record/fold.py` names it.

The 147,591 against the ledger's 250,136 is not a loss either: the difference is
baseline failures, which hang off a run's gate results, belong to no task, and
are appended by nothing.

## What the record costs on disk

| | |
|---|---|
| fact JSON, uncompressed | 33,652,032 bytes (33.7 MB) |
| median fact | 315 bytes |
| mean fact | 9,731 bytes |
| **largest single fact** | **1,273,877 bytes (1.27 MB)** |
| facts over 1 MB | 27 |
| facts between 100 KB and 1 MB | 0 |
| loose objects | 13,832 objects, 55.37 MiB by `count-objects` |
| loose, allocated on APFS | 58,621,952 bytes |
| packed (`git gc --aggressive`) | one pack, 2.01 MiB; 2,485,668 bytes on disk |

The largest fact is one `prose` gate result carrying 5,693 failures inline. The
distribution has no middle: a fact is a few hundred bytes or it is a megabyte,
and which one it is depends entirely on how many failures the gate found.

**This is not the size the design argued from.** `DESIGN.md` reasons from a
2026-09-17 measurement of 6.7 MB for 102 tasks — about 65 KB of facts per task.
The same quantity today is 285 KB per task uncompressed, four times that, and
the whole of the gap is inline failure lists. Two readings of the same fact,
both true:

- **Uncompressed, it is worse than assumed.** 33.7 MB of JSON, and a single
  append that hands git a 1.27 MB blob.
- **Packed, it is better.** 2.01 MiB for all 118 tasks, 17 KB per task, because
  27 near-identical megabyte failure lists delta against each other almost
  perfectly. A record that is gc'd and pushed costs less than the design
  supposed; one left loose costs 56 MB of allocated blocks for 4.9 MB of
  content.

Nothing here is a proposal. What to do about a multi-megabyte fact — carry
failures by reference, cap them, or leave them — is a decision this record does
not make.

## What this record does not establish

**Steady-state growth.** One pass, one repo, one host. Whether a record written
a night at a time packs as well, and what a year of nights costs, is unmeasured.

**Push.** Nothing was pushed. Whether a remote accepts a 1.27 MB blob on
`refs/saffron/*` at the rate a night produces them is untested; the 2026-09-17
record covers only that the namespace is accepted at all.

**Concurrency.** The fold ran alone against a record nothing was writing.

**The whole of a task.** This fold replays creation, attempts, gate results and
state. `task_package`, `task_push`, `task_merged_head`, `task_policy`, findings
and rebuttals are appended by `Ledger` and read back by nothing yet, so a
rebuilt index today has no `pr_url` and no findings. That is scope, not a
measurement — but it means "delete the index and rebuild it" is proven for the
six columns above and no others.

## The clause that would reopen it

A fold that stops fitting in the window an operator will wait through — or a
remote that refuses the blobs. The first is a factor of twenty away at
`cat-file --batch`; the second is untested.
