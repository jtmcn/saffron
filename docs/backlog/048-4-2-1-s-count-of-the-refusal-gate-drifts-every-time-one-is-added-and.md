---
id: 48
title: §4.2.1's count of the refusal gate drifts every time one is added, and has twice
status: open
tier: 2
specs: [SA-0021, SA-0023, SA-0024, SA-0027]
prs: []
commits: []
cites: [§4.2.1]
related: [30]
---

## Problem

`SA-0023` added `protected_touch_refusal` (`saffron/scheduler.py`), so
`DESIGN.md:383` — *"The refusal gate refuses six things, and the fifth is the
only one with a corpse behind it"* — undercounts by one, and the enumeration
that follows it does not mention the new one at all.

The drift was designed in rather than overlooked: `DESIGN.md` is `protected`,
so `SA-0023` could not touch it, and the module docstring is honest about the
gap ("beyond §4.2.1's own six"). What makes it worth an item rather than a
shrug is the circularity underneath. **The only spec that could repair a
sentence in `DESIGN.md` is one whose `touches` names `DESIGN.md` — and that is
now exactly what this refusal refuses.** `SA-0021` was the last such spec and
it was run by hand for this reason; after `SA-0023` it does not even reach a
cell. Every future correction to the two authoritative documents is a
by-hand correction, permanently.

That is the right trade — a cell rewriting the definition of its own
constraints is what a global deny list is for — but it means the documents
drift by default and nothing schedules the catch-up. §4.2.1's count is the
first instance.

**Status: the count is correct and the item stays open, which is the whole
argument.** Two corrections have now landed by hand. The six→seven one came
with `SA-0023`; it was already wrong again by the time that was written,
because `SA-0027` had added an eighth. `DESIGN.md:383` now reads *"The refusal
gate refuses eight things"* and names both, and `scheduler.py`'s docstring says
§4.2.1 counts them.

**Twice in one release, each time caught by a person who happened to be
looking, is the finding.** Neither correction was scheduled; both were noticed
while reading for something else, and between them the authoritative document
said the wrong number for the whole of that window. A ninth refusal will drift
exactly the same way. **Done looks like** a check that `DESIGN.md`'s stated
count matches what `_refuse` applies — it fails the moment the ninth lands,
which no sweep does. Whether that check is cheap is unmeasured: it needs the
refusals enumerable by something other than reading `_refuse`, and no registry
exists. Item 30 reached the same practice from `SA-0024`'s side of the same
wall; this is the third instance, which item 30 itself said should not need a
third item to become a rule.
