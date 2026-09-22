---
id: SA-0122
title: The host and the lens-corpus driver each author `probes.json`'s entry shape, and nothing holds the two together
type: bug
priority: 3
depends_on: [SA-0120]
touches:
  - saffron/probe.py
  - saffron/cell/session.py
  - docs/evidence/scripts/2026-09-08-lens-corpus.py
  - tests/test_session.py
  - tests/test_corpus.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - ontology/**
  - tests/ontology/**
  - images/**
  - harness/**
  - docs/backlog/**
  - docs/appendices/**
  - docs/adr/**
  - docs/evidence/fixtures/**
  - docs/evidence/passes/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/cell/worktree.py
  - saffron/cell/runtime.py
  - saffron/repos/**
  - saffron/intake.py
  - saffron/ledger.py
  - saffron/task.py
  - tests/test_probe_check.py
  - tests/test_review.py
  - tests/test_worktree.py
budget_usd: 17
max_attempts: 3
max_turns: 120
risk: elevated
acceptance:
  - claim: >-
      The host builds each `probes.json` entry from one helper in the probe
      module, and adds only its own `probe_verdict` and `findings`. Every other
      key in the entry, and its value, is the helper's. The helper returns ten
      fields and no verdict key. They are the probe, the reason, the failures,
      the tool, the collected count, the summary, and four baseline fields.
      The witness drives two probes in one review. One has a baseline in hand,
      and its baseline failures are an empty list. The other is on a declared
      test path and was refused before any baseline was read, and all four of
      its baseline fields are null.
    witness: tests/test_session.py::test_the_host_writes_each_probes_json_entry_from_the_shared_helper
  - claim: >-
      The lens-corpus driver builds each `probes.json` entry from the same
      helper, and adds only its own `verdict`. Every other key in the entry,
      and its value, is the helper's, and the helper returns the same ten
      fields. The witness drives two passes. In one the baseline suite
      answered with one failure that was already there, and the entry's
      baseline failures list that one failure. In the other the baseline
      suite raised, and all four baseline fields are null.
    witness: tests/test_corpus.py::test_the_driver_writes_each_probes_json_entry_from_the_shared_helper
---

## Context

Backlog item **b-e403c1**, found by the spec loop's Standards seat reviewing
#375 (`SA-0109`) on 2026-09-19. It is related to item 94, which added the
baseline fields, and item 117, which made the host run the vacuity probe
(`DESIGN.md` §5.5, §5.5.1).

Every sentence below about current code was read at `dd25ea92` on
2026-09-21. `SA-0119` and `SA-0120` land first and move line numbers in the
source files. Find each cited name by its name at the base you are cut from.
`depends_on` names `SA-0120`, whose own parent is `SA-0119`. Both edit
`saffron/cell/session.py`, and the scheduler exempts an overlap only along
the first dependency's chain.

**Two writers spell the same record.**

- The host builds one entry per distinct probe inside `decide`, a closure in
  `_probe_adequacy` (`saffron/cell/session.py:1293-1321`). It is a dict
  literal of twelve keys. Every path through the function records its
  entry through `decide`, the refusals and raises included
  (`saffron/cell/session.py:1323-1325`, `:1332-1340`, `:1400-1411`). The
  function imports the probe module as `probe_check` inside its own body
  (`saffron/cell/session.py:1277`).
- The lens-corpus driver builds one entry per probe in
  `_write_probes` (`docs/evidence/scripts/2026-09-08-lens-corpus.py:171-200`).
  Its baseline keys come from `_baseline_keys` (`:160-168`). It imports the
  probe module as `probe_check` at module scope (`:85`).

The ten shared keys match today, key for key. They are `probe`, `reason`,
`failures`, `tool`, `collected`, `summary`, `baseline_failures`,
`baseline_tool`, `baseline_collected` and `baseline_summary`. Both spell a
missing baseline as `null` in all four baseline keys
(`saffron/cell/session.py:1307-1310`, `docs/evidence/scripts/2026-09-08-lens-corpus.py:160-168`).
No test compares the two.

**The verdict key differs, and each has readers.** The host writes
`probe_verdict`, which `describe_probes` counts
(`saffron/phases/review.py:533`). The driver writes `verdict`, which
`tests/test_corpus.py` reads at `:698` and elsewhere, and which the
committed pass records under `docs/evidence/passes/` carry. The host also
writes `findings`, which the driver has no counterpart for.

## Problem

Item 94's fields will drift the first time either writer gains one, and the
corpus is what a lens's kill rate is measured against. Make one helper own
the shared fields, and have both writers call it.

1. **The helper.** Add one function to `saffron/probe.py` that takes a
   probe and its `ProbeResult` and returns the ten shared fields, flat. A
   missing baseline is `null` in all four baseline fields, never `[]`,
   which is a baseline read and green. It returns no verdict key and no
   `findings`. Name it as you like.
2. **The host calls it.** `decide`'s entry becomes the helper's fields plus
   `probe_verdict` and `findings`, spelled as they are now.
3. **The driver calls it.** `_write_probes`'s entry becomes the helper's
   fields plus `verdict`. `_baseline_keys` goes, since nothing else calls
   it.
4. **Reach the helper through the module.** Call it as an attribute of the
   imported probe module, as both callers already name the module
   `probe_check`. Both witnesses replace it on `saffron.probe` and must see
   the replacement called.

## Out of scope

- Closing item b-e403c1. `docs/backlog/**` is `forbidden`, so the operator
  closes it by hand after merge.
- Renaming either verdict key. Each has readers named in the Context, and
  the committed pass records cannot be rewritten.
- `criterion-probes.json`. It is a different record with different fields
  (`saffron/cell/session.py:2398-2400`), and `SA-0120` owns what it gains.
- The key order inside an entry. JSON readers here index by key.
- `SA-0119`'s test-path rule and `SA-0118`'s files. This spec edits
  neither. `saffron/cell/worktree.py` and `tests/test_worktree.py` are in
  `forbidden`.

## Notes for the agent

**This change is new code, so no criterion declares a mutant** (§5.4.1).
Nothing at base spells the helper, its name or its call. The `witness` gate
will report `skip` for this spec.

**The shape of both witnesses.** Each replaces the helper on `saffron.probe`
with a wrapper, using `monkeypatch.setattr`. The wrapper calls the real
helper and keeps its return. It returns a different dict instead, holding a
sentinel string for every key the real one returned plus one extra key.
Then read `probes.json` back and assert three things.

- Each entry, minus the writer's own keys, equals the wrapper's return for
  that probe.
- The real return's keys are exactly the ten names in the Context.
- Every value of the real return against its source, for each case the
  claim names. Where a baseline was in hand, the two runs must differ. Give
  the baseline and the probed run a different `tool`, `collected` set and
  `summary`. Today both suites a witness can reuse share all
  three, and both summaries default to `""`. So a helper that reads the
  probed run into a baseline key, or the reverse, passes unless they differ.

Also assert the writer's own verdict value for each entry. Take the real
helper from the module inside the test body, and import nothing the change
adds at module scope. At base the patch raises `AttributeError`, which is a
failure and not a collection error, so `revert` sees the witness fail.

**The host witness.** Put it in `tests/test_session.py`, after
`test_a_probe_cell_that_never_comes_up_leaves_the_findings_as_filed`. Drive
one review through `_drive` with `_PROBE_POLICY` and `gates=("tests",)`.
File two findings with `_adequacy_finding`, one probing `src/a.py` and one
probing `spec/a.py`. Answer the probe cell with `_stub_probe_gates`: a green
baseline, then a failing suite. Give the two answers a different `tool` and
`summary`, and a different count of collected ids. The probed run must
collect every baseline id plus at least one more, such as
`["t.py::test_a"]` then `["t.py::test_a", "t.py::test_b"]`.
`check_probe` returns `unproven` when a baseline id goes missing
(`saffron/probe.py:214-225`). The helper records only a count, so two sets of
one size would hide a swap. `_GREEN_TESTS` (`tests/test_session.py:2729-2731`)
and the failing suite in
`test_two_findings_naming_one_probe_are_decided_by_a_single_suite_run`
share all three, so build new answers rather than reuse them. The source
probe is then `killed`, and the task ends `READY_FOR_REVIEW` with no REBUT
turn. The `spec/a.py` probe is refused on the
declared test path before any cell, so it has no baseline, at base and
after `SA-0119` alike.

**The driver witness.** Put it in `tests/test_corpus.py`, after
`test_a_probe_with_no_baseline_in_hand_writes_null_not_an_empty_list`. Call
`_drive` twice, each into its own subdirectory of `tmp_path`: once with the
new parameter below, and once with `baseline_raises=CellRuntimeError(...)`. Each pass
files one probe, so each writes one entry. `_write_probes` rewrites the file
after every probe, so match each entry to the wrapper's last return for its
pass. Compare the ten names with `BASELINE_KEYS` (`tests/test_corpus.py:716`)
and the six others. The stub `gate` inside `_drive` answers every call with
one `GateResult` (`tests/test_corpus.py:524-528`). Add a `_drive` parameter
that sets the baseline's `tool`, `collected` count and `summary` apart from
the probed run's, and gives the baseline one pre-existing failure. Default it
to `None` and replace only the first call's answer, as `baseline_raises` does
(`tests/test_corpus.py:526`), so every existing caller sees what it sees now.
Then assert every value in that pass.

**The wrong implementations each witness must fail.** Each of these failed
its witness on a prototype of this change.

- The helper added and a writer still spelling its own literal. The wrapper
  is never called for that writer.
- A writer that sets a shared key after the helper's fields, so its value
  wins. The entry then differs from the wrapper's return.
- The helper holding only the four baseline fields, with each writer
  keeping the other six. The real return then has four keys, not ten.
- The helper returning a verdict key, or `[]` for a missing baseline.

Five more no prototype has run yet. Each witness must also fail a helper that
swaps a value with its counterpart: `failures`, `tool`, `collected` or
`summary` with its baseline field, and `reason` with `summary`. Run each
swap against both witnesses before you commit them.

**What is left unwitnessed.** Each witness drives two of its writer's
paths. The host's other paths are a survivor, a mutator refusal, a raise, a
cell that never came up and a repo with no `tests` gate. The driver's are a
mutator raise and a head with no `tests` gate. Every one of them records its
entry through the same `decide` or `_write_probes`, so each writer has one
call to the helper. The existing tests of those paths still read the
record's fields.

**The tests already pinning the record stay green unchanged.** On the
prototype, every test in `tests/test_session.py`, `tests/test_corpus.py`,
`tests/test_probe_check.py` and `tests/test_review.py` passed. Those
include the ones asserting `probe_verdict`, `verdict` and the baseline
fields in `probes.json`. Rename none of them, since `census` reads a rename
as a removal.

**Each witness is a plain `def`, never parametrised.** `criteria` matches a
bare node id by exact string.

**`size` blocks at 300 changed lines here.** `saffron/cell/**` is in
`.saffron/policy.yaml`'s `elevate_on`. A prototype of this change measured
185 changed lines. That was 19 in `saffron/probe.py`, 12 in
`saffron/cell/session.py`, 23 in the driver, 84 in `tests/test_session.py`
and 47 in `tests/test_corpus.py`. Keep the helper's docstring and each
comment to one or two lines.

Commit after each coherent step. Uncommitted work dies with the cell.
