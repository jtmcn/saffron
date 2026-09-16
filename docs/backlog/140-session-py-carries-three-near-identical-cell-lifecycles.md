---
id: 140
title: Three near-identical cell lifecycles live in `session.py`, and the second one's docstring says why there should be one
status: open
tier: 1
filed: 2026-09-16
by_hand: false
specs: [SA-0089, SA-0093]
prs: [282]
commits: []
cites: [§5.5]
related: [118, 134, 141]
---

## Problem

**Tier 1.** Found reviewing `SA-0089` (PR #282), by diffing the two bodies.

`critic_cell` and `_gate_cell_suite` are 73 and 81 lines with comments stripped,
and differ in **six** code lines: the network create/remove pair, `subnet=`,
`env=cell_env(proxy_ip, thread_env)` versus `env=dict(thread_env)`, the proxy-IP
read, and `yield container` versus `return suite.against(...)`. The 13-line
`prepare_worktree` call and the container-and-volume half of the pre-clean are
verbatim.

**Corrected 2026-09-16**, writing `SA-0093` against this record: the pre-clean
and the `finally` teardown are *not* verbatim. The gate cell removes its own
network in both, so it pre-cleans four names and tears down four where
`critic_cell` does three. It matters because
`test_the_lens_gate_cell_holds_no_credential_and_is_gone_before_any_lens_runs`
counts each name's removals rather than testing membership, and a unified
lifecycle that always pre-cleans a network, or never does, fails it or its
critic-cell counterpart. Found by the spec review before the cell ran. The teardown loop is now in the file three times — `cell_down`,
`critic_cell`, `_gate_cell_suite` — and `reverify` has a fourth nested
`_gate_cell` in `package.py`.

`critic_cell`'s own docstring states the rule this breaks, in the repo's words:

> `SA-0088` calls this again for REBUT's verdict lenses, which is why the whole
> lifecycle lives in one function rather than being inlined at this spec's one
> call site.

The spec did not force it. `package.py` is `forbidden` so `reverify`'s copy was
out of reach, but `session.py` is in `touches` and nothing forbade generalising
`critic_cell`.

This is how item 134's duplication grew by one more copy in the same file.

## Done looks like

`critic_cell` taking `network: str | None` (None → create and tear down its own)
and `env: Mapping[str, str]`, with `_gate_cell_suite` reduced to entering it and
running the suite — or a recorded decision that three copies is the price of the
`touches` boundary, with the reason written where the next spec will read it.
