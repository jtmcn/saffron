---
id: FX-0001
title: A child names what it consumes
type: feature
depends_on: [FX-0000]
consumes:
  - saffron/task.py
  - saffron/task.py:run_task
touches:
  - tests/fixtures/consumes/FX-0001-a-child-names-what-it-consumes.md
---

## Context

A stacked child's tree base is its parent's branch head. A criterion can
name work the parent already built under a different name.

## Problem

Nothing told the host what a child needs from its parent before this
fixture existed. A malformed entry reached the reader as a git error, not
a load-time refusal.

## Out of scope

This fixture names two consumed entries only, one bare path and one path
with a name. It never runs against a real tree, and no cell reads it.

## Notes for the agent

This file is a fixture, not a task. It exists so a witness in
`tests/test_consumes.py` can load it back and compare both lists.
