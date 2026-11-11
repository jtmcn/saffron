---
id: b-16c819
title: A session test fakes `subprocess.run` for every argv, so new code under `cell_up` must avoid `run`
status: done
closed: 2026-11-10
tier: 2
filed: 2026-11-10
specs: []
prs: [1142]
commits: []
cites: []
related: [b-2bc0d5]
---

## Problem

Found by both review seats on `SA-0365` (#1137) in the spec loop's run 60.

`test_the_n1_refusal_names_the_processes_behind_each_answering_port` in
`tests/test_session.py` replaces `subprocess.run` for the whole process. It
answers every call, whatever its argv, from an ordered list of lsof listings.
`SA-0365` added a git read to `image.cell_tag`, which `session.cell_up` calls
first. That read took the first listing, and the test failed. So
`_origin_name` reads git through `subprocess.Popen`, and its comment names
the test.

## Done looks like

The fake answers only an `lsof` argv and passes every other call to the real
`subprocess.run`. `_origin_name` then reads git through `subprocess.run` with
its timeout, and the comment goes.

## Record

- 2026-11-10: filed from the spec loop's run 60.
- 2026-11-10: fixed by hand in #1142. The fake answers only `lsof`, and
  `_origin_name` reads git with `subprocess.run` and its timeout.
