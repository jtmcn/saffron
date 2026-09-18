---
id: 154
title: No mutant can be written to `session.py` any more, and trying wedged the cell
status: open
tier: 1
filed: 2026-09-16
by_hand: false
specs: [SA-0093, SA-0104]
prs: [293]
commits: []
cites: [§5.4]
related: [80, 140]
awaiting: [335]
---

## Problem

**Tier 1.** Found by `SA-0093`'s first cell, 2026-09-16 (spec loop run 5).

`worktree._write_file` sends a mutated file into the cell as one base64 `sh`
argument. Its own `ponytail:` names the ceiling: Linux caps a single argument
at 131,072 bytes (`MAX_ARG_STRLEN`), so a file over about 96 KiB cannot carry a
mutant. `saffron/cell/session.py` is about 102 KiB (105,076 bytes at `1dd2093`)
and still growing. **Every mutant declared against it is now `error`**, which
aborts the attempt and is charged to nobody.

That is two costs, and the second one is not in the `ponytail:`:

- **The spec loses its only mechanical check.** `SA-0093`, `SA-0094` and
  `SA-0095` all edit `session.py`, and none can declare a mutant there.
  `SA-0093`'s had to be dropped by #293 after it aborted the first cell
  (`GATE_ERROR`, $4.42). For the three specs, the witnesses were the only
  check, and each spec-loop review found at least one witness that survived a
  wrong implementation.
- **The failure was not clean on apple/container.** The `ponytail:` says "the
  exec never starts". Measured on this host, the exec failed with
  `Stream unexpectedly closed` and left `saffron-cell-SA-0093` wedged: listed
  `running`, refusing exec as "not running". Teardown could not remove the
  container, `saffron-cells` or either volume. No later cell could start until
  they were removed by hand with `container stop`/`rm`, `volume rm` and
  `network rm`.

Nothing warns before a cell is paid for. The spec review does not check a
mutant's target size, and neither does intake.

## Done looks like

`_write_file` carries a file of any size — several arguments under the cap,
appended in order, or another channel — with a test that writes a file over
131,072 bytes of base64. Until then, intake refuses a mutant whose `file` is
over the ceiling at the spec's base, naming the ceiling, so it costs no cell.

## Record

**Filed 2026-09-16** from the spec loop's run 5 (stack #308). `SA-0093`'s mutant
was dropped by #293 rather than wait on this.

- 2026-09-18: open as PR #335 (`SA-0104`, spec loop run 7), stacked in
  #335 ← #338 ← #339 ← #342 ← #340.
