---
id: b-2dc561
title: Preflight's host-port refusal names the address, not the process, and the allow list must spell `lsof`'s truncation
status: superseded
tier: 3
filed: 2026-09-30
closed: 2026-11-07
specs: [SA-0244]
prs: [796]
commits: []
cites: [§5.1]
related: [b-e0cd57]
superseded_by: b-e0cd57
---

## Problem

Found in the spec loop's run 23, 2026-09-30.

`SA-0196`'s first start exited 2 at preflight:

```
host services answered from inside a cell at 10.88.0.1:9200, 10.0.0.105:9200 — bind them to 127.0.0.1.
```

The refusal names the port but not the listener. The delegate ran
`lsof -nP -iTCP:9200 -sTCP:LISTEN` by hand and found RAATServer, Roon's
audio endpoint. The operator chose to tolerate it. `lsof` truncates command
names to nine characters, so `SAFFRON_ALLOW_HOST_PROCESS` has to spell it
`RAATServe`. Nothing says so.

## Done looks like

The refusal names each listener's process as `lsof` reports it. That is the
exact spelling `SAFFRON_ALLOW_HOST_PROCESS` accepts.

## Record

- 2026-09-30: filed from the spec loop's run 23.
- 2026-11-07: closed in grooming as superseded by b-e0cd57. That item, filed from run 16, named the same refusal and the same `RAATServe` spelling. `SA-0244` (#796) closed it. `assert_host_is_unreachable` now appends each port's listeners as `lsof` reports their COMMAND, through `_named_hits` (`saffron/preflight.py:217-244`). That truncated name is the exact spelling `SAFFRON_ALLOW_HOST_PROCESS` matches.
