---
id: 151
title: A spec the order names that no longer parses takes out status, next and snapshot with a traceback
status: open
tier: 3
filed: 2026-09-16
by_hand: false
specs: []
prs: []
commits: []
cites: []
related: [137]
---

## Problem

**Tier 3.** Found writing item 137's witness on 2026-09-16: a test wrote a
malformed spec to make a row stale a second time, and the driver raised instead.
Measured against a scratch order afterwards.

`_stale_reasons` and `_edit_traps` both call `load_spec(path)[1]` unguarded, and
`_carried` does the same to record `edited_sha`. A spec the order names that no
longer parses therefore raises `SpecError` out of every command that reads the
order:

```
  SA-0001  READY_FOR_REVIEW   #10

1/1 reviewable
cmd_status: SpecError: spec frontmatter is not valid YAML: while scanning a simple key
cmd_next:   SpecError: spec frontmatter is not valid YAML: while scanning a simple key
```

`status` is the worst of the three, because it prints its whole table first and
*then* dies — the operator reads a complete, plausible report and an uncaught
traceback under it, with nothing naming the spec at fault. `next` and
`snapshot --force` die the same way, so the loop has no read command left and no
way to re-snapshot out of it.

The path this is reached by is the one item 137 is about: an operator editing a
spec because they have just read its review. A file saved in a broken
intermediate state is enough, and the traceback does not say which spec or that
an edit caused it.

`_order` already guards the same call and says why — *"A parse failure can name
`depends_on` too, and is not a deferral"* — so the scan path survives an
unreadable spec and the order path does not. One of the two is wrong.

`_fail` is the driver's own convention for this: exit 1 with a message on
stderr, which `cli.py` reserves for "the task did not make it" rather than
infrastructure.

## Done looks like

`_stale_reasons`, `_edit_traps` and `_carried` treating an unreadable spec the
way `_order` does — as a fact about that row rather than an exception. A row
whose spec will not parse reads as stale, naming the spec and the parse error,
and the other rows still report. A witness that puts a malformed spec in the
order and asserts `status` exits 1 with the spec id in the message, rather than
raising.
