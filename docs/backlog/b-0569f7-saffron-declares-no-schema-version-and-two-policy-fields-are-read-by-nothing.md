---
id: b-0569f7
title: "`.saffron/` declares no schema version, and two policy fields are parsed and read by nothing"
status: open
tier: 2
filed: 2026-10-06
specs: []
prs: []
commits: []
cites: [§3.2, §5.4]
related: [19, b-2e0b97]
---

## Problem

ADR 10 makes `.saffron/` an interface that other operators write against. One
operator changes a format and fixes every repo in an afternoon. Another
operator's repo meets the change at their next engine upgrade.

`policy.yaml`, the spec frontmatter and the gate contract carry no schema
version. An engine reading an older or newer file cannot say which it read.

Two policy fields are parsed and read by nothing.
`GateDeclaration.when` is one (`saffron/repos/policy.py:49`, item 19).
`envelope_default` is the other (`saffron/repos/policy.py:72`). This repo's
operator knows both are inert. An operator who declares `when:` expects a
conditional gate and gets one that runs on every task.

## Done looks like

`policy.yaml`, a spec and a gate result each declare a schema version. The
engine refuses a version it does not support, and the refusal names the ones
it does.

`when` and `envelope_default` are each either read or refused at load. A test
loads a policy declaring each and asserts which.

On a shared-kernel host, a policy that declares no `thread_env` is refused.
There it is the only CPU control (§5.1, ADR 10).
