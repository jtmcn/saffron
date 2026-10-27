---
id: SA-0323
title: A survivor's second ask drops a kill whenever the same run also leaves an uncounted failure
type: bug
priority: 2
estimated_lines: 40
estimate_measured: true
touches:
  - saffron/phases/review.py
  - tests/test_session.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/probe.py
  - saffron/gates/**
  - saffron/agents/**
  - saffron/record/**
  - saffron/report/**
  - saffron/cell/**
  - saffron/task.py
  - saffron/ledger.py
  - saffron/qualify.py
  - saffron/cli.py
  - saffron/batch.py
  - tests/ontology/**
  - tests/test_rebut.py
  - tests/test_cli.py
  - tests/test_qualify.py
  - tests/test_batch.py
  - tests/test_spec_citations.py
  - tests/test_spec_loop_driver.py
budget_usd: 8
max_attempts: 3
max_turns: 40
acceptance:
  - claim: >-
      `survivor_claim_with_suite_verdict` (saffron/phases/review.py:784-801)
      judges `result.verdict` before it ever reads `result.uncounted`. A
      `killed` result still gets the kill form of the claim — the opening
      text up to the quoted claim, then ". ", `SUITE_KILL_SENTENCE`, every
      id in `result.failures` joined by ", ", then ", and the criterion's
      witness did not fail." — whether or not `result.uncounted` is also
      non-empty. `result.uncounted`'s own ids never appear in that list.
      Only once `verdict` is not `"unproven"` and not `"killed"` does a
      non-empty `result.uncounted` send back `claim` unchanged, which is
      the one case `check_probe` (saffron/probe.py:291-299) can reach with
      both a `"survived"` verdict and a non-empty `uncounted`.
    witness: tests/test_session.py::test_a_kill_with_an_uncounted_failure_still_names_the_killing_tests
    wrong_versions:
      - The guard reads `result.verdict == "unproven" or result.uncounted` before the `killed` branch, exactly as it does at base, so a kill with a non-empty `uncounted` returns `claim` unchanged.
      - The `killed` branch is reached only `and not result.uncounted`, so a kill with a non-empty `uncounted` falls through to the "stayed green" sentence instead.
      - The kill form joins `result.failures + result.uncounted`, so an uncounted id appears in the list beside the killing ones.
      - The kill form joins only `result.failures[0]`, so a kill with two or more killing ids names just the first.
---

## Context

Backlog **b-b9365d**, the same item `SA-0322` (commit `f4afbd49`, reviewed
at `2742f631722db58c765b00200ff33c15194e19d7`) built
`survivor_claim_with_suite_verdict` for. That review commit fixed one gap
— a `survived` result whose new failure named no test the head collected
was being written as "stayed green" — by adding `or result.uncounted` to
the guard at what is now `saffron/phases/review.py:791`. The added clause
sits before the `killed` branch at line 794, so it now also catches a
`killed` result whenever that same result's `uncounted` is non-empty, and
returns `claim` unchanged instead of naming the kill. Read at head
`b8b02311ee526ccca0c83cb28e8fc689db80ecc9` (`saffron/phases/review.py` has
not changed since `2742f631`).

**A mixed result is real, not hypothetical.** `check_probe`
(`saffron/probe.py:264-299`) builds `killing` and `uncounted` from the
same `new` failures (lines 278-279): one new failure whose `code` is in
`counted`, one whose `code` is not. When `killing` is non-empty it returns
`verdict="killed"` at line 281, and the very same call passes the
non-empty `uncounted` at line 289. So a `killed` `ProbeResult` with a
non-empty `uncounted` is exactly what two new failures in one second ask
— one matching a counted test, one not — produces.

**The module's own invariant says a kill still wins.** `saffron/probe.py`'s
module docstring (lines 20-26) states the rule in prose: a new failure
not among `counted` "lands in `uncounted` and decides nothing" — it is not
read as vetoing a kill that a *different* new failure already earned.
The current guard at line 791 does exactly that veto, contradicting both
this sentence and `survivor_claim_with_suite_verdict`'s own docstring two
lines above it, which says plainly "`killed` names every killing node id"
with no exception carved out for a coexisting `uncounted`.

**No existing test reaches this branch.** The one test that exercises the
`uncounted` path,
`test_a_second_ask_whose_new_failure_no_head_test_names_keeps_todays_claim`
(`tests/test_session.py:14029-14053`), builds its `uncounted` case from a
pure `survived` result with no `failures` at all. Nothing in the suite
constructs a `ProbeResult` that is `killed` and carries a non-empty
`uncounted` at once, so this branch of the guard has never been asserted
either way.

## Problem

Fix the guard's order so a `killed` verdict is judged — and its killing
ids named — before `result.uncounted` is read for anything. Only once
`verdict` is neither `"unproven"` nor `"killed"` does a non-empty
`uncounted` keep today's claim unchanged (the `survived`-with-uncounted
case the existing test above already pins, which must keep passing).

1. **The guard.** Split the single combined check into two: an
   `"unproven"` verdict returns `claim` unchanged on its own, independent
   of `uncounted`. The `"killed"` branch runs next, unconditionally. Only
   after both does a non-empty `result.uncounted` return `claim` unchanged
   for whatever is left (the `"survived"` case).
2. **The kill form's text does not change.** It still lists exactly
   `result.failures`, joined by `", "`, and never anything from
   `result.uncounted`.
3. **The docstring.** Say plainly that a `killed` verdict names every
   killing id even when `result.uncounted` is also non-empty, so the next
   reader does not reintroduce the same veto.

## Out of scope

- **`saffron/probe.py`'s own docstring on `ProbeResult.uncounted`**
  (`saffron/probe.py:134-138`): "A `killed` result carries none of these
  codes." `check_probe` itself contradicts that sentence (lines 278-290
  pass a non-empty `uncounted` alongside a non-empty `killing`). The file
  is forbidden for this spec, so the sentence stays stale.
- **A second finding raised alongside this one, about
  `_WITNESS_ONLY_TAIL`.** It no longer holds at this head.
  `saffron/phases/review.py:736-738` defines the literal once, and both
  claim forms in `survivor_finding` (lines 757-766) already interpolate
  that one constant rather than writing a second copy of the text; the
  review commit `2742f631` consolidated it as a side effect of the fix it
  was making. Nothing here reopens it.
- **Any other reordering of `survivor_claim_with_suite_verdict`.** The
  function's shape, its callers (`saffron/cell/session.py`'s
  `_apply_criterion_probes`), and every other branch's wording are
  untouched.

## Notes for the agent

**The fix is a reorder, not new logic.** Today:

```python
    if result.verdict == "unproven" or result.uncounted:
        return claim
    head = claim.removesuffix(_WITNESS_ONLY_TAIL)
    if result.verdict == "killed":
        ...
    return f"{head}, and the whole `tests` gate stayed green under the edit too."
```

Change the first line to check only `result.verdict == "unproven"`, and
add an `if result.uncounted: return claim` immediately after the
`killed` branch's `return`, before the final `return` line. The `killed`
branch itself is untouched.

**The witness.** Build a `probe.ProbeResult` with `verdict="killed"`,
`failures=("t.py::b", "t.py::c")` and `uncounted=("t.py::zebra",)`. Start
from a claim `review.survivor_finding` built, exactly as
`test_a_second_ask_whose_new_failure_no_head_test_names_keeps_todays_claim`
does. Assert `survivor_claim_with_suite_verdict`'s result equals the
kill form in full: it ends with `"...failed t.py::b, t.py::c, and the
criterion's witness did not fail."` and contains no `"zebra"` anywhere.
Place the test directly after
`test_a_second_ask_whose_new_failure_no_head_test_names_keeps_todays_claim`
(`tests/test_session.py:14029`), in its shape: no fixture, no
monkeypatch, a handful of direct calls.

**Measured.** The four wrong versions above were each applied by hand
against a prototype of the fix and each failed the witness's equality
assertion. The production change is a one-line split plus a docstring
clause — well under the `bug` ceiling of 1300 changed tokens; the
witness test adds under 30 lines. The whole suite was not re-run for this
measurement since the change touches no other behaviour: every other
branch of the function, and every caller, is untouched.

Commit after the witness passes. Uncommitted work dies with the cell.
