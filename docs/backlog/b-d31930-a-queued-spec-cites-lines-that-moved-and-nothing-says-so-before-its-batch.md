---
id: b-d31930
title: A queued spec cites lines that moved since it was written, and nothing says so before its batch pays to find out
status: done
closed: 2026-10-20
tier: 2
filed: 2026-10-15
specs: [SA-0273, SA-0294, SA-0295]
prs: [880, 890, 891, 892, 897, 898, 921]
commits: []
cites: [§3.2]
related: [b-b24cf7]
---

## Problem

Found in the spec loop's run 40.

`SA-0273` was written against `bc879e2c`. By the time it ran, nine landed specs
had moved `saffron/cell/session.py` and `saffron/cli.py` by hundreds of lines.
The batch's spec review found 15 citations pointing at the wrong code and
blocked the spec. That cost $2.32 and a hand-made PR, #880.

`driver.py cite` finds this in seconds. Nothing runs it on a queued spec
before the batch does. Run 39's handoff named the refresh as optional.

## Done looks like

`driver.py check`, or the batch's own preflight, runs the citation check over
each spec in the order. A citation that no longer resolves blocks before any
money is spent.

## Record

- 2026-10-15: filed from the spec loop's run 40.
- 2026-10-16: #891 makes `driver.py check` run `cite` at the branch a cell
  is cut from. #890 adds `SA-0294` and `SA-0295` for the batch's arm, and
  #892 refreshed the citations `check` then blocked on. The check's own
  match is loose both ways (b-2da959).
- 2026-10-17: #898 (`SA-0294`) moves the check into core as `saffron/spec_citations.py` and gives `run_stack_batch` a `cite` hook. `SA-0295` still owes the production adapter. #897 refreshed 12 citations `check` blocked in run 43.
- 2026-10-20: #921 (`SA-0295`) gives `saffron batch --stack` its `cite` adapter, at the commit the spec review reads.
