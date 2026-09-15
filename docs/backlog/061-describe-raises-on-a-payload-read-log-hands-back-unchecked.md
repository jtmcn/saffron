---
id: 61
title: '`describe` raises on a payload `read_log` hands back unchecked'
status: done
tier: 1
closed: 2026-09-12
specs: [SA-0053, SA-0070]
prs: [119, 221]
commits: []
cites: []
related: [63]
---

## Problem

**Status:** **done**, with item 63 — `SA-0070`, PR #221, merged 2026-09-12.

**Tier 3.** Found reviewing `SA-0053` (PR #119), and fixed *around* rather than
fixed: `saffron/events.py` was `forbidden` to that spec.

`read_log` type-checks nothing — it is `cls(**obj)` onto a plain dataclass — so
a corrupt or hand-edited line round-trips into `Agent(event='not an object')`
and `describe` raises `AttributeError` on `.get`. Measured:

```
read_log tolerates it: [Agent(timestamp=1.0, spec_id='T1', raw=False, event='x', …)]
describe RAISED: AttributeError 'str' object has no attribute 'get'
```

That is per-line corruption defeating the per-line tolerance `read_log`'s own
docstring promises, and it takes the whole caller down with it. `watch.py`
guards its own call (`_is_malformed`), so the follower is safe; every other
caller of `describe` is not.

**Done looks like** `read_log` refusing to build an event whose field is the
wrong type at all — the drop it already performs for a missing field, extended
to a present one of the wrong shape — so no caller has to guard. The producer
side is already guarded (`implement.py:255` checks `isinstance(event, dict)`),
so nothing hostile reaches this today; a hand-edited log does.

**Not** each caller repeating `watch.py`'s guard. That is the duplication the
guard exists to make unnecessary once, and `describe`'s contract should be
"any `Event`" or it is not the single renderer this repo relies on it being.
