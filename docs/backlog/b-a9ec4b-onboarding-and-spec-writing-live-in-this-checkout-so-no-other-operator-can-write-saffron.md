---
id: b-a9ec4b
title: Onboarding and spec writing live in this checkout's `.claude/`, so no other operator can write `.saffron/`
status: open
tier: 2
filed: 2026-10-06
specs: []
prs: []
commits: []
cites: [§2.1, §3.2]
related: [b-2e0b97, b-0569f7]
---

## Problem

ADR 10 expects other operators to onboard their own repos. The tools that
write `.saffron/` live in this repo's `.claude/`. They are the
`setup-saffron`, `create-saffron-spec` and `run-saffron-spec-loop` skills,
and the `spec-writer` and `spec-reviewer` agents.

They load only in a session started in this checkout. They also read this
repo's own files. They cite `DESIGN.md` sections and `docs/agents/`, and they
run `records` and `driver.py`. A target repo carries none of those.

## Done looks like

A Claude Code plugin installs the onboarding and spec tools for any repo. Each
tool names what it reads from the engine and what it reads from the target.
An operator onboards a repo and writes its first spec with no clone of this
repo.

This is also ADR 10's test of §2.1 across operators. A second operator
onboards a repo of their own, and the diff to `saffron/` that it needs is
empty. It tests the operator axis only. The language claim stays with §9's
v3 and its dissimilar third repo.
