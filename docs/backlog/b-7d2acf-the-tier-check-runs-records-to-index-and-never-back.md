---
id: b-7d2acf
title: The tier check runs records to index and never back, so an item the index ranks with no `tier` field passes
status: open
tier: 3
filed: 2026-09-20
specs: []
prs: [388]
commits: []
cites: []
related: [128, 129, 170]
---

## Problem

Found 2026-09-20, placing the 16 open items that carried no `tier` field.

`check_priority` in `tests/records/check.py:441` compares the records against
the index in one direction. It reads `PRIORITY.md`, collects every bold or
struck id under a tier heading, and then walks the records. An item whose
`tier` is set must appear under that tier's heading, or the check files a
violation. An item whose `tier` is `None` is never looked at.

Two items sat in that gap. 127 and 131 are named under Tier 3's heading, and
neither record carried the field. `uv run python -m records list backlog`
printed `-` for both, `--tier 3` left both out, and the check stayed green from
2026-09-15 to 2026-09-20. The prose ranked them and the index did not.

`docs/backlog/README.md` states the rule in one direction as well: set `tier`
only for an item named under that tier's heading. The reverse duty is the one
nobody wrote down. An index that names an item under a tier ranks it, and
the record is where every tool reads that ranking from.

## Done looks like

`check_priority` files a violation for an item the index names under a tier
heading whose record carries no `tier`. The violation names the record, the
field and the tier the index gave it.

A test breaks the property by clearing `tier` on a fixture item the fixture
index ranks, and the check kills that mutant. The existing direction keeps its
own test.

## Record

**Filed 2026-09-20**, from #388. That pull request set the field on 127 and 131
by hand and left the hole open.
