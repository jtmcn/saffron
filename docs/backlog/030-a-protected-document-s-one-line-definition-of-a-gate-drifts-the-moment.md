---
id: 30
title: A protected document's one-line definition of a gate drifts the moment the gate changes, and the fix is always by hand
status: done
tier: null
closed: 2026-08-31
specs: [SA-0011, SA-0018, SA-0021, SA-0023, SA-0024]
prs: []
commits: []
cites: [§3.1, §5.2, §5.4]
related: [27, 28, 31]
---

## Problem

`SA-0024` widened `scope_gate` (`saffron/gates/core/scope.py`) to also fail a
changed file matching a spec's `forbidden` list or the repo's `protected` list,
not only a file outside `touches`. `CONTEXT.md` §3 still defines the gate in
one line: *"The check that changed files are a subset of `touches`."* That
sentence is now false — it describes half the gate — and nothing in this
spec's `touches` can fix it: `CONTEXT.md` is `protected`, so no plan naming it
can be validated (item 28's `SA-0023` refusal), and it is in this spec's own
`forbidden` list besides. The correction is a by-hand follow-up, the same
shape item 27 (`SA-0018`/`SA-0021`) and item 28 (`SA-0023`) already
established for a protected document a spec cannot reach.

**This is the second instance of that drift, not the first.** Item 27 is the
first: `SA-0018` added a second producer of `SCOPE_REVIEW` and could not update
`CONTEXT.md`'s **Touches** entry to say so, because `DESIGN.md` and
`CONTEXT.md` were both in `SA-0018`'s own `forbidden` list — the same
structural reason this item exists. `SA-0021` closed that one, by hand, one
spec later. The pattern both instances share: a spec that changes what a core
mechanism does can never be the spec that updates the one document defining it
in prose, because that document is `protected` by the same policy the spec's
own change makes more precise. A third instance should not need a third
backlog item before it is treated as a rule of the process rather than a
one-off gap: **any spec that changes core gate or phase behaviour should name,
in its own notes, the `CONTEXT.md`/`DESIGN.md` sentence its change makes
stale**, so the by-hand follow-up has a known list rather than a fresh reading
of both documents each time.

## Record

**Status:** **done** — by hand on the host, 2026-08-31, in `SA-0024`'s own
pull request.

**And the enumeration is what the item was actually for.** `CONTEXT.md` §3 was
the sentence this item named, and it was the *least* load-bearing of the six.
`DESIGN.md` — authoritative for what the system does, and cited by section
number from specs — carried four more, one of which stated the shipped
behaviour's exact opposite:

- §3.1's frontmatter example: `forbidden: # denied at the plan checkpoint, not
  against the diff`
- §3.1's paragraph *"**`forbidden` and `protected` bind the plan, not the
  diff** … No gate reads either against a diff."*
- §3.1's next paragraph, describing the gap as *"Stated rather than fixed"*
  after `SA-0024` fixed it
- §5.4's gate table row: `| scope | core | yes | changed files ⊆ touches |`
- §5.2's writeback rule, which item 31 covers separately

The second of those already carried a scar — *"the wording here said otherwise
until `SA-0011` leaned on it"* — so a spec that read it would have leaned on
wording false in the opposite direction. The by-hand list this item asks specs
to carry was written into `SA-0024` and still named only one of six documents,
which is the argument for making it a check rather than a request: **the spec
that proposed the rule did not follow it.** A plan-checkpoint or gate-0 check
that a spec changing a core gate names the `DESIGN.md`/`CONTEXT.md` sentences
its change makes stale is the shape; it is not written.
