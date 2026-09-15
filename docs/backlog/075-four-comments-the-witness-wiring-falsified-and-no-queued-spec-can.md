---
id: 75
title: Four comments the `witness` wiring falsified, and no queued spec can reach them
status: open
tier: 3
specs: [SA-0061, SA-0062]
prs: [150]
commits: []
cites: []
related: [74]
---

## Problem

**Tier 3.** Found reviewing `SA-0061` (PR #150), 2026-09-06. Small, mechanical,
and filed rather than fixed because filing is the whole point of item **74**.

`SA-0061` wired `witness` into a cell run and gave it a blocking level that
agrees with `contract.witness_blocking`. Four statements written while that was
*not* true are now false:

- `saffron/gates/contract.py` — *"**Nothing reads it yet, and the thing that
  will currently disagrees.** … a `witness` failure blocks at `standard`
  today."* Both halves. `session._blocking` now reads it.
- `saffron/gates/runner.py` — *"no production caller can supply one until
  `SA-0061` wires a stub"*. `SA-0061` is merged. **Corrected 2026-09-08 (#166)**,
  out of order with the other three: that branch added `package.reverify` as a
  second production caller supplying `mutate`, and leaving a comment known to be
  false in a file the same diff edits is worse than closing a quarter of this
  item early. The other three still want the single pass below.
- `tests/test_witness_gate.py` — *"the reaches half is currently false:
  `witness` is in no `advisory_gates` set, so a failure blocks at every tier"*.
- `tests/test_witness_gate.py` — *"inserting `if failure.gate == "witness":
  return False` into `session._blocking` … fails nothing in the whole suite"*.
  Measured: it now fails `test_a_witness_failure_is_advisory_at_standard_and_
  blocking_when_elevated`.

The last is the one that misleads worst. A reviewer reading it would believe
the reaches half is still open, when `SA-0061` closed it — and that docstring
was written *to record a gap*, which makes it exactly the kind of comment
someone trusts.

**Why it is filed and not fixed.** No queued spec can touch these.
`SA-0062`'s `forbidden` list contains `saffron/gates/**` and its `touches`
does not include `tests/test_witness_gate.py`. A commit message on `SA-0061`
first asserted the opposite — that `SA-0062` "already touches
`saffron/gates/**`" — which is precisely the item-71 failure repeating: a
finding handed to something that cannot act on it is a finding lost. Corrected
there, recorded here.

**Done looks like** one spec owning `saffron/gates/contract.py`,
`saffron/gates/runner.py` and `tests/test_witness_gate.py`, correcting all four
in a pass. It is comment-only, so `type: chore` and a small ceiling; the value
is that the next reader of any of them is not misled about what is built.

**Worth folding in while there:** `run_witness`'s subset probe is now live on
every suite call for any criterion declaring a `mutant` — one extra in-cell
`tests` invocation per `_suite`, baseline and head, to reach a guaranteed
`skip` while the mutator is a stub. Zero cost for this repo today, since no
spec declares one. A target repo that does would pay it, and nothing says so.
