---
id: 98
title: The spec loop hands untrusted critic output to a delegate holding the operator's push credentials
status: open
tier: 2
specs: []
prs: []
commits: []
cites: [§2]
related: [97]
---

## Problem

**Tier 2.** Found alongside item **97**. `findings.json` is written by a model that
read the implementer's diff, and the diff is cell output — untrusted by the one
rule that governs everything (§2). Step 2c of `run-saffron-spec-loop` feeds each
finding's `claim` to a delegate on the host, holding the operator's git identity,
`gh` token and push access with no cell around it, and tells it to fix what the
claim describes. A diff built to steer a lens can put instructions into finding
text that a delegate then carries out outside any cell: the confused-deputy shape.
The one line standing against it — "verify each claim against the code before
acting on it" — is a prompt, and prompts shape behaviour; they are never the
boundary.

**Tier 2, not 1,** because the loop is attended: someone is at the keyboard. But
attended is not reviewing each finding before the delegate acts on it, and the
loop's value is that nobody has to.

**Done looks like** the fix step running where the operator's credentials are not
— a cell of its own, where a finding is input to an implementer rather than to a
delegate — or, short of that, the delegate that reads findings holding no push or
`gh` credential, with the push a separate step taken after the operator reads the
diff.

Not item 97: that is what the fix skips on the way out. This is what reaches the
delegate on the way in.
