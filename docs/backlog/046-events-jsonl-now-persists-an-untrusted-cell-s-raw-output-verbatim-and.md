---
id: 46
title: '`events.jsonl` now persists an untrusted cell''s raw output verbatim, and nothing bounds or scans it'
status: partial
tier: 1
specs: [SA-0041, SA-0068]
prs: [213]
commits: []
cites: [§5.4, §9]
related: []
---

## Problem

The deciding argument is §9's v1 criterion. The defining property of the
milestone is that *nobody was watching* — so a log reduced to bounded
renderings would discard the only account of the night it matters most on.
That rules out the cheaper answer.

Two specifics, so the spec does not have to re-derive them:

- **One value on both paths.** Reuse `implement.QUARANTINE_BYTES` (8192) rather
  than minting a second number — the item names "one value, both paths" as the
  open half, and a second constant is how the two drift.
- **`secrets` must reach the batch tree, not only the diff.** §5.4 lists it as
  a v1 gate, so this is written down now to be built into it rather than
  retrofitted after.

`SA-0041` makes `implement.run_agent` emit the parsed cell event under
`Agent.event`, which is the fix that spec exists for — the dict was previously
flattened to prose before the host ever saw it, so `Agent.event` was
permanently `None`.

The side effect, raised by that run's contract lens: **what reaches persistence
changed shape.** Before, only `_describe`'s bounded renderings were written — a
`tool_result` became the fixed string `agent: tool ok`, `text` was truncated at
160 characters and `tool_use` at 120. Now the raw dict is written verbatim to
`~/.saffron/batches/v0/<id>/events.jsonl`, and for `text`, `tool_use` and
`tool_result` that dict can carry full file contents, whole command outputs, or
anything else an untrusted cell chose to put on stdout.

Two things follow, neither addressed anywhere:

- **Volume is unbounded on the path that matters.** `SA-0041` bounded the raw
  quarantined line at capture (`implement.QUARANTINE_BYTES`, 8192) after review
  measured 5 MB of stdout writing 5 MB of log. That closes the accidental case
  only: the same payload wrapped in nine bytes of JSON takes the `Agent.event`
  path and still writes 5 MB, because bounding it needs `saffron/events.py`,
  which that spec forbids. One value, both paths, is still the open decision.
- **The `secrets` gate never sees it.** That gate reads the diff. A batch tree
  artifact is not a diff, so a credential a cell printed to stdout is persisted
  host-side and scanned by nothing. §5.4 lists `secrets` as a v1 gate, so this
  is a gap that widens rather than one that exists today — which is the reason
  to record it now rather than after it is built.

Neither the golden fixture nor the unit tests can see this: both exercise small
synthetic dicts, so the change is invisible to the suite by construction.

## Done looks like

Done looks like a decision about what the log is for. If it is an operator's
record of a night, the rendered line is sufficient and `Agent.event` should be
bounded the way the display already is. If it is evidence, it needs a size cap
and to be in the `secrets` gate's reach. `SA-0041` could not make that choice —
`saffron/events.py` is `forbidden` to it — and made the reachability fix it was
asked for, which is correct.

## Record

**Decided 2026-09-04: it is evidence, not an operator's record.** So it takes
a size cap and must come within the `secrets` gate's reach. **Tier 1.**

**Status: the size half is done — `SA-0068`, PR #213, merged 2026-09-12.**
The `secrets` half stays open here, because the gate it would extend does not
exist yet.
