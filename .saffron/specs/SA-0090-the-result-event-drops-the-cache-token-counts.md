---
id: SA-0090
title: the event log drops every token count the SDK reports, so whether a session read its prompt from the cache is a guess
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
budget_usd: 6
max_attempts: 3
max_turns: 50
acceptance:
  - claim: >-
      A result event carries the input, output, cache-read and cache-write
      token counts the SDK's result message reports, exactly as reported, a
      zero included. Today it carries `total_cost_usd` and no token count, so
      nothing in the event log can say whether a session read its prompt from
      the cache or paid to write it again.
    witness: tests/test_agent_runner.py::test_the_result_event_carries_the_sessions_token_counts
  - claim: >-
      A result message that reports no usage gives a result event whose token
      counts are present and null. Absent is null; a reported zero stays zero.
    witness: tests/test_agent_runner.py::test_a_result_that_reports_no_usage_has_null_token_counts_not_zero
  - claim: >-
      Each step's input, cache-read and cache-write counts reach the event log
      once, on an event that step's assistant message already produces, however
      many assistant messages share that step's message id.
    witness: tests/test_agent_runner.py::test_a_step_carries_its_cache_counts_once
  - claim: >-
      A rate-limit message, which carries a `session_id` and no `num_turns`,
      still becomes a `rate_limit` event and never a result, as it does today.
    witness: tests/test_agent_runner.py::test_a_rate_limit_event_is_not_mistaken_for_a_result
    preserves: true
---

## Context

Found 2026-09-14 while checking REVIEW against the prompt-cache advice in
`keli-wen/agentic-harness-patterns-skill`.

`images/agent_runner.py` maps the SDK's result message to Saffron's `result`
event, and keeps `subtype`, `num_turns`, `total_cost_usd`, `session_id`,
`terminal_reason` and `is_error`. The message's `usage` is dropped, and so is
the `usage` every assistant message carries. The host emits the parsed event
dict verbatim as `events.Agent(event=...)` (`run_agent` in
`saffron/phases/implement.py`), so whatever the runner puts on an event reaches
the event log with no host change.

Both fields exist in the SDK the base image pins, `claude-agent-sdk==0.2.142`:
`ResultMessage.usage`, and `AssistantMessage.usage` and `message_id`. Checked
2026-09-14 by installing that version outside the project.

The two are not the same number. The Agent SDK's cost-tracking documentation
says the result's `usage` is cumulative over every step of one `query()` call,
and each resumed call reports its own. A session reads its own earlier steps
from the cache, so a large cumulative cache read says nothing about whether the
session's *first* step read what another session wrote. Only the per-step
counts can say that, and the same documentation says their input and cache
figures are accurate while their `output_tokens` is not.

Two cost questions wait on these counts. `DESIGN.md` §7.1's one-hour cache TTL
is set on every session (`agent_options`), not only the repair loop it was
argued for. Whether the three REVIEW lenses could read a shared system prompt
from the cache is backlog item 126. Both have been reasoned, never
measured.

## Problem

The event log records what a turn cost and nothing about why. A turn that read
30,000 tokens from the cache and one that wrote them fresh can report different
costs, with nothing to say which happened.

## Out of scope

**Any host-side use of the counts.** No `AttemptResult` field, no ledger column,
no `describe()` line. The event log is where they are measured first.

**The per-TTL split of cache writes, and per-step output tokens.** Carry the
four totals on the result and the three per-step counts named above.

**Rebuilding the base image.** The cell runs the runner baked into
`saffron/cell-base:python`, so this change reaches a cell only after the
operator rebuilds that image by hand (`CLAUDE.md`, Commands).

## Notes for the agent

**The criteria carry witnesses and no mutants, except the `preserves` one.** The
mapping is new code, so no text exists yet that a mutant could pin honestly.
`witness` will report `skip` on the first three, and that is expected.

**Use the Messages API's own names.** `input_tokens`, `output_tokens`,
`cache_read_input_tokens` and `cache_creation_input_tokens`, flat on the event,
so an operator can search the event log for the names the API documents. The
SDK is not installed on the host (`pyproject.toml` says why), so the tests feed
fake messages, as every test in `tests/test_agent_runner.py` does. Read the
fields with `getattr` and `.get`, the way the rest of `events()` reads a
message: an SDK that renames or drops one must give nulls, never a crash inside
a cell the host cannot see into.

**Zero and absent are different here, and that is the opposite of the cost
field's rule.** The runner turns a missing `total_cost_usd` into `0.0`, pinned
by `test_a_result_that_reports_no_cost_is_zero_not_none`, because
`_reconcile_cost` reads `0.0` on a failed turn as the crash signal. Nothing on
the host reads the token counts, so they carry exactly what was reported: a
missing count is `None`, a reported `0` is `0`. Do not write `or None` or
`or 0` over them. A crashed turn may report zeros; a reader tells it apart by
the event's own `subtype` and `is_error`. Give the first witness's fake `usage`
at least one count of `0`, and assert it `== 0` and not `None`.

**Assert presence, not only value, in the null-counts test.** `event.get(...)
is None` also passes on the reverted runner, which has no such keys at all, so
it would witness nothing. Assert that each key is in the event, and that its
value is `None`.

**Put the per-step counts on an event the message already produces.** An
unknown event type is rendered by `describe()` as a line of its own, so a new
`usage` event would print one terminal line per step, and `saffron/**` is
forbidden here. The SDK can deliver one step as several assistant messages
sharing a `message_id`, each carrying the same `usage`; carry the counts on
the first event of the first such message, and on none of the others. An
assistant message that produces no events today may keep producing none.

**Carry the counts as the message reports them, and nothing more.** One result
event covers one `run_agent` call, and IMPLEMENT and the repair loop resume one
session across several. Do not sum, subtract or reconcile counts across calls or
steps.

**Update `test_the_result_event_carries_what_the_supervisor_bounds_on`.** It
asserts the whole event dict, so adding keys fails it. Give its fake message a
`usage` and extend the expected dict; do not loosen it to a subset check.

**The `size` gate counts tests.** A `feature` gets 600 changed lines, tests
included. This is well inside that.
