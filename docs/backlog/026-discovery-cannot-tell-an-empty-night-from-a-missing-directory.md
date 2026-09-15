---
id: 26
title: Discovery cannot tell an empty night from a missing directory
status: done
tier: 1
closed: 2026-09-10
specs: [SA-0014, SA-0015, SA-0017, SA-0065]
prs: [56, 185]
commits: [30bd85c]
cites: []
related: [95]
---

## Problem

**Status: done** — `SA-0065`, PR #185, 2026-09-10, on its second run with the
corrected boundary. The refusal reaching a terminal and never the ledger is
item **95**. The first attempt is kept as filed:

**Attempted by the first `saffron batch` ever to run a task, 2026-09-09,
and `EXHAUSTED` on the spec's boundary rather than on the work.** `SA-0065`'s
implementation was correct — the guard, both tests, `$0.97` of a `$5` ceiling —
but making `discover_specs` refuse an absent directory breaks `_spec_path` in
`saffron/cell/session.py`, a caller the spec's `forbidden` list excluded and its
"Out of scope" section never named. The implementer found it, recorded it in the
notes channel rather than working around it, and declined to edit a forbidden
file; the no-progress breaker then stopped the task at attempt 2. `_spec_path`
now states its own precondition, and the spec is queued again with a corrected
boundary and unchanged criteria. The exit code item 26 argues for is still out of
its scope.

`discover_specs` (`saffron/intake.py`, landing with `SA-0014` in PR #56) returns
`(specs, failures)` and reaches the filesystem through `directory.glob("*.md")`.
`Path.glob` yields nothing for a directory that does not exist and nothing for a
path that is a file, so all three of these are the same value:

```
discover_specs(Path("/nope/nothing"))   -> ([], [])
discover_specs(Path("saffron/intake.py")) -> ([], [])
discover_specs(<an empty directory>)    -> ([], [])
```

Measured at `30bd85c`. The spec's second acceptance criterion asks only that a
*malformed spec* not raise past discovery, so this is not a violation of it —
the scan does what it was asked. It is the distinction this repo enforces
everywhere else that is missing: `error` ≠ `fail`, and a gate that never ran
must not read like one that ran and passed. A scan that never saw a directory
must not read like a night with no work in it.

It matters at the seam, not here. `SA-0017` resolves `base_sha` and exports
`.saffron/specs/` from a repo; `SA-0015` builds the queue from what discovery
returns. An export that silently produced nothing — wrong `base_sha`, a repo
that never had `.saffron/`, a path assembled with the wrong join — reaches the
scheduler as a quiet empty queue, and the first unattended night ends having
done nothing with no record saying why. That is the failure mode this backlog
is ordered by.

**Done looks like** `discover_specs` raising `SpecError` when `directory` is not
an existing directory, with a test for the missing path and the not-a-directory
path. The caller owns the export, so a directory that is not there is an
infrastructure fault (exit `2`), not an empty scan — the same call
`PREFLIGHT_FAILED` makes. An existing but empty directory stays `([], [])`,
which is a true statement about a repo with no specs.
