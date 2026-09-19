# Backlog — what v0.5 left, and why each thing matters

Written at the close of v0.5 (`DESIGN.md` rev 14). Every item here is a gap a
live run exposed or a decision deliberately deferred — none is speculation about
what might be nice. Each says what "done" looks like, so it can be picked up
cold.

**Items 1–177 are numbered in filing order, not priority order.** The numbers are an API —
comments across `saffron/` cite them (`BACKLOG item 33`, `backlog item 41`), so
an item is never renumbered, exactly as `DESIGN.md`'s sections are. Every later item
takes a random id (`b-3f9a2c`), because sessions filing in parallel kept claiming the
same next number. The header line here used to claim the file was ordered by what would hurt
most on the first unattended night; it never was, and as items were appended it
drifted further. **The order to work in is `PRIORITY.md`.**

**Where the evidence lives.** Appendices I–L narrate what building
and running v0.5 found. The per-task briefs and implementation reports were
written under `.superpowers/`, which is gitignored and does **not** survive a
merge — anything from them worth keeping was moved into the appendices or into
`docs/superpowers/plans/2026-08-19-v0.5-findings.md` before this was written.

---

## What is *not* here, deliberately

DIAGNOSE and `SCOPE_REVIEW`, the scheduler's conflict sets and stacking, `saffron
gc`, multi-repo, the merge train, and the `secrets` gate. All are v1+ by
`DESIGN.md` §9's own build order, and none of them is blocked by any open item.
`size` left this list on 2026-08-25: it is built and unwired, which is
item 17. `revert` left it with `SA-0044`: it is built and wired into `_suite`,
which is item 49. §4.2's own argument applies: at a two-deep queue they
arbitrate contention that never arrives.

---

## How to add an item

Copy the frontmatter shape from any open item: each field is defined in `records/kinds.py` and
validated on load. Take `id` from `uv run python -m records new-id`, use it at the start
of the filename as `b-xxxxxx-slug.md`, and set `filed:` so `make backlog` lists it in filing
order. Cite it as `item b-xxxxxx`, and in `PRIORITY.md` as `**b-xxxxxx**`. The body must have three sections in order:
`## Problem`, `## Done looks like`, and `## Record`. Before committing, run `uv run pytest tests/records -q` to
validate the record. If a spec's `## Context` section cites this item, add that spec's id to this
item's `specs:` list in the same commit.

- Set `tier` (0–3) only if the item is named under that tier's heading in `PRIORITY.md` — the
  check enforces it.
- `done`, `superseded` and `wontfix` need `closed` plus at least one of `specs`/`prs`/`commits`
  (`superseded` also needs `superseded_by`).
- `partial` needs a dated `## Record` entry.
- Set `by_hand: true` when the item's own prose says the work that closed it, or the work still
  left, cannot go through a cell.
- An open item with no stated exit criterion writes `_Not stated in the original item._` under
  `## Done looks like`.
- Quote commit shas in YAML (`commits: ["0123456"]`) so an all-digit sha is not read as a number.

## Closing an item

**The pull request that finishes an item closes it in its own diff**: `status: done`,
`closed:`, its own number in `prs:`, and a dated `## Record` entry. Never write "open until
this merges". The record lands only if the pull request merges, so the item is already done
by the time anyone reads it. #287 did this in five records, and four of them stayed open on
`main` until #296.

**An item waiting on a *different* pull request lists it in `awaiting:`**, and the record
says "open as PR #N". `tests/records` enforces the rest:

- An `awaiting` pull request that has merged fails the check, on every branch, until the item
  is closed, or its record says what is left and the number moves to `prs`.
- In a pull request's own CI, `awaiting` naming that same pull request fails. That is the
  #287 shape, caught before merge.
- A record in an open item that says "open as PR #N" must list N in `awaiting`, or say
  "PR #N merged" in a later entry.

The check reads merge-commit subjects (`Merge pull request #N from …`), so it depends on this
repository merging rather than squashing, and on CI's full clone. It does not see an item
waiting on something other than a pull request, such as another item or a live run. Item 69
waited on one of those for eight days.
