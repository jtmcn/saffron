# Spec writers wait on the whole suite

Read-only, on 2026-11-09. No call was made. Script in
`scripts/2026-11-09-spec-writer-suite-waits.py`.

## What was read

The twelve newest `spec-writer` subagent transcripts, `SA-0338` to
`SA-0356`. Each holds a draft and every revision sent to the same writer.
The script splits a transcript at each prompt and drops gaps under half a
minute. A suite wait is a whole `make check` or `pytest`, or a poll on one.

## Result

| Measure | Value |
|---|---|
| Active writer minutes | 565 |
| Minutes waiting on a whole suite | 226, about 40% |
| Draft rounds | 16 to 47 minutes, 0.4 to 25 of them waiting |
| Revision rounds | often 75 to 90% waiting, such as 9.1 of 11.8 minutes |

Across 47 suite results, the failed hooks were `prose` five times and `ty`
once. Four failed tests sat in the live-tree paths the writer now runs. Eleven
sat in `tests/test_session.py`, a file a prototype edits.

## Two measurements beside it

- Two `pytest -n 4` runs started together on the 11-core host each took about
  six minutes. Both failed
  `test_runtime.py::test_a_stop_during_a_silent_turn_unwinds_without_waiting_for_the_turn`
  and `test_view_server.py::test_serve_prints_the_bound_address_before_it_serves`.
  One `-n 8` run alone passed all 4997 tests in 170 seconds.
- The `prose-limit` hook reads only the index. It passed an unstaged file it
  never read, and failed the same file once staged.

## What could not be measured

The time a chain saves under the new rules. No chain has run under them.
