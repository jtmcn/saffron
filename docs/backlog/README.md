# Backlog — what v0.5 left, and why each thing matters

Written at the close of v0.5 (`DESIGN.md` rev 14). Every item here is a gap a
live run exposed or a decision deliberately deferred — none is speculation about
what might be nice. Each says what "done" looks like, so it can be picked up
cold.

**Numbered in filing order, not priority order.** The numbers are an API — ten
comments under `saffron/` cite them (`BACKLOG item 33`, `backlog item 41`), so
an item is appended and never renumbered, exactly as `DESIGN.md`'s sections
are. The header line here used to claim the file was ordered by what would hurt
most on the first unattended night; it never was, and as items were appended it
drifted further. **The order to work in is the index below.**

**Where the evidence lives.** `DESIGN.md` Appendices I–L narrate what building
and running v0.5 found. The per-task briefs and implementation reports were
written under `.superpowers/`, which is gitignored and does **not** survive a
merge — anything from them worth keeping was moved into the appendices or into
`docs/superpowers/plans/2026-08-19-v0.5-findings.md` before this was written.

---

## What is *not* here, deliberately

DIAGNOSE and `SCOPE_REVIEW`, the scheduler's conflict sets and stacking, `saffron
gc`, multi-repo, the merge train, and the `secrets` gate. All are v1+ by
`DESIGN.md` §9's own build order, and none of them is blocked by anything
above. `size` left this list on 2026-08-25: it is built and unwired, which is
item 17. `revert` left it with `SA-0044`: it is built and wired into `_suite`,
which is item 49. §4.2's own argument applies: at a two-deep queue they
arbitrate contention that never arrives.

---

## How to add an item

Copy the frontmatter shape from any open item: each field is defined in `records/kinds.py` and
validated on load. Set `id` to one more than the highest existing item, and use that id at
the start of the filename as `NNN-slug.md`. The body must have three sections in order:
`## Problem`, `## Done looks like`, and `## Record`. Before committing, run `uv run pytest tests/records -q` to
validate the record. If a spec's `## Context` section cites this item, add that spec's id to this
item's `specs:` list in the same commit.
