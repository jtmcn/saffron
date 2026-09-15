---
id: SA-0090
title: the result event drops the session's token counts, so whether a session read its prompt from the cache is a guess
type: feature
priority: 3
depends_on: []
touches:
  - images/agent_runner.py
  - tests/test_agent_runner.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - harness/**
  - saffron/**
  - images/*.Dockerfile
budget_usd: 4
max_attempts: 3
max_turns: 40
acceptance:
  - claim: >-
      A result event carries the session's input, output, cache-read and
      cache-write token counts, as the SDK's result message reports them.
      Today it carries `total_cost_usd` and no token count, so nothing in the
      event log can say whether a session read its prompt from the cache or
      paid to write it again.
    witness: tests/test_agent_runner.py::test_the_result_event_carries_the_sessions_token_counts
  - claim: >-
      A result message that reports no usage gives a result event whose token
      counts are present and null, not zero. A cache read of zero is a
      measurement, the prefix missed. An absent one is not a measurement.
    witness: tests/test_agent_runner.py::test_a_result_that_reports_no_usage_has_null_token_counts_not_zero
  - claim: >-
      A rate-limit message, which carries a `session_id` and no `num_turns`,
      still becomes a `rate_limit` event and never a result, as it does today.
    witness: tests/test_agent_runner.py::test_a_rate_limit_event_is_not_mistaken_for_a_result
    preserves: true
---

## Context

Found 2026-09-14 while checking REVIEW against the prompt-cache advice in
`keli-wen/agentic-harness-patterns-skill`: sibling sessions should share a
byte-identical prompt prefix, so each one reads what the one before it wrote.

`images/agent_runner.py` maps the SDK's result message to Saffron's `result`
event, and keeps `subtype`, `num_turns`, `total_cost_usd`, `session_id`,
`terminal_reason` and `is_error`. The message's `usage` is dropped. The host
emits the parsed event dict verbatim as `events.Agent(event=...)`
(`run_agent` in `saffron/phases/implement.py`), so whatever the runner puts on
the event reaches the event log with no host change.

Two cost questions are open because of this, and both have been reasoned,
never measured. `DESIGN.md` §7.1's one-hour cache TTL is set on every session
(`agent_options`), not only the repair loop it was argued for. The three REVIEW
lenses share most of their system prompt but not its first sentence (`SA-0091`).
Each answer is a cache-read count and a cache-write count per session. This
spec records them.

## Problem

The event log records what a session cost and nothing about why. A session
that read 30,000 tokens from the cache and one that wrote them fresh can report
different costs, with nothing to say which happened.

## Out of scope

**Any host-side use of the counts.** No `AttemptResult` field, no ledger column,
no `describe()` line. The event log is where they are measured first. A host
field is a later spec, once a night's log shows the counts are worth carrying.

**The per-TTL split of cache writes.** The API may break cache writes down by
TTL inside `usage`. Carry the four totals only.

**Rebuilding the base image.** The cell runs the runner baked into
`saffron/cell-base:python`, so this change reaches a cell only after the
operator rebuilds that image by hand (`CLAUDE.md`, Commands).

## Notes for the agent

**The criteria carry witnesses and no mutants.** The mapping is new code, so no
text exists yet that a mutant could pin honestly. `witness` will report `skip`,
and that is expected.

**Use the Messages API's own names, flat on the event.** `input_tokens`,
`output_tokens`, `cache_read_input_tokens` and `cache_creation_input_tokens`,
so an operator can search the event log for the names the API documents. The
SDK is not installed on the host (`pyproject.toml` says why), so the tests feed
fake messages, as every test in `tests/test_agent_runner.py` does. Give the fake
result a `usage` dict. Read it with `getattr` and `.get`, the way the rest of
`events()` reads the message: an SDK that renames or drops the field must give
nulls, never a crash inside a cell the host cannot see into.

**Assert presence, not only value, in the null-counts test.** `event.get(...)
is None` also passes on the reverted runner, which has no such keys at all, so
it would witness nothing. Assert that each key is in the event, and that its
value is `None`.

**Update `test_the_result_event_carries_what_the_supervisor_bounds_on`.** It
asserts the whole event dict, so adding keys fails it. Give its fake message a
`usage` and extend the expected dict; do not loosen it to a subset check.

**The `size` gate counts tests.** A `feature` gets 600 changed lines, tests
included. This is well inside that.
