---
id: 24
title: The fixture item 21 built drifts in value, not shape
status: done
tier: null
closed: 2026-08-28
specs: [SA-0012, SA-0013]
prs: [49, 51]
commits: []
cites: []
related: [21, 23]
---

## Problem

**Status:** **done** — `SA-0013` (PR #51), 2026-08-28. Found by review of
`SA-0012` (PR #49); the spec it was written into is
`.saffron/specs/done/SA-0013-fixture-values-are-witnessed.md`.

Item 21's fix replaced the two `SimpleNamespace` fakes with `_spec()`, which
builds a real `Spec` by putting a string literal through `parse_spec`. Nothing
asserts that the values handed to `_spec()` survive the trip. Measured, not
reasoned: break the `## Acceptance criteria` header so `_CRITERIA_SECTION`
misses, or corrupt the `touches` line to yield `["ZZZf.txt"]`, and the whole
module still reports **97 passed**. `["f.txt"]` and `["it works"]` appear in
`tests/test_package.py` only as arguments to the helper, and no assertion
mentions either.

So the `packageable` fixture that feeds most of PACKAGE's tests can start
handing `package()` a spec with no criteria and a scope matching nothing, and
every test stays green while exercising less than its name claims. `parse_spec`
changing its criteria regex is enough to trigger it, and that regex has no test
tying it to this fixture. It is item 21's own thesis — a fixture whose contents
nothing checks — one level down.

**Done looks like** one new test beside the existing one, asserting
`spec.touches` and `spec.acceptance_criteria` against what `_spec()` was called
with: two assertions, red under either mutation above. New rather than an
extension of `test_the_package_fixtures_build_a_real_spec`, which is green at
base and would fail `criteria`'s `witness-green-at-base` — item 23, met in the
wild while authoring the spec.
