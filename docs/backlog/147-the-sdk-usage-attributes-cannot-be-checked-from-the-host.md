---
id: 147
title: Nothing on the host can check the SDK attributes the token counts depend on, and the fakes cannot fail
status: open
tier: 2
filed: 2026-09-16
by_hand: true
specs: [SA-0090]
prs: [278]
commits: []
cites: [§2.1]
related: [126, 146]
---

## Problem

**Tier 2.** Raised by both review seats on `SA-0090` (PR #278) and explicitly
**unverified** — the host is architecturally forbidden to import the SDK
(`pyproject.toml`), so neither seat could install it to check.

`SA-0090` rests on `ResultMessage.usage`, and on `AssistantMessage.usage` and
`message_id`, in `claude-agent-sdk==0.2.142`. The spec states its method and date
for checking them, which is the right disclosure. But every witness feeds a fake
`SimpleNamespace`, and the runner reaches the fields with `getattr(..., None)`
behind an `isinstance(usage, dict)` guard — correct, defensive, and unfalsifiable
from the host.

If `AssistantMessage` in fact carries no `usage`, criterion 3 is **vacuous in a
live cell**: no crash, no red gate, no event key, and every test still green.
Neither cell-marked test would notice — they prove the transport, not the shape.

This is the seam `CLAUDE.md`'s "Run the tool, don't merely locate it" is about,
one layer out: the fake fixes the shape, so the test cannot tell a working read
from a read of nothing.

## Done looks like

One real event log read after the next base-image rebuild, with the counts
present and non-null, recorded here — or a cell-marked test that asserts the
counts on a real session rather than a fake.
