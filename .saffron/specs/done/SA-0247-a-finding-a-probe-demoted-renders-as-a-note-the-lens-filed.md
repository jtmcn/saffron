---
id: SA-0247
title: A finding a probe demoted renders in the pull request body as a note the lens filed
type: bug
priority: 3
depends_on: [SA-0240, SA-0233]
estimated_lines: 110
estimate_measured: true
touches:
  - saffron/agents/findings.py
  - saffron/phases/review.py
  - saffron/report/pr_body.py
  - tests/test_review.py
  - tests/test_report.py
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
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/record/**
  - saffron/repos/**
  - saffron/view/**
  - saffron/ledger.py
  - saffron/qualify.py
  - saffron/follow_up.py
  - saffron/end_review.py
  - saffron/probe.py
  - saffron/phases/rebut.py
  - saffron/phases/package.py
  - saffron/report/index.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/cli.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
  - tests/test_ledger.py
budget_usd: 20
max_attempts: 3
max_turns: 150
acceptance:
  - claim: >-
      `apply_probe_verdict` keeps the severity a finding carried before the
      verdict, on a new `Finding` field, for each of `survived`, `killed`
      and `unproven`. It still decides `severity` from the verdict as it
      does at base. A finding no verdict was applied to holds `None` there.
      The witness applies each of the three verdicts to a finding filed at
      each of `blocker`, `concern` and `note`. For each of the nine it
      checks the decided severity, the verdict and the kept severity. It
      then checks one finding no verdict reached.
    witness: tests/test_review.py::test_a_probe_verdict_keeps_the_severity_the_lens_filed
    mutant:
      file: saffron/phases/review.py
      find: finding.severity = "note"
      replace: finding.severity = "concern"
    wrong_versions:
      - The kept severity is written after the verdict decides, so it equals the new severity.
      - The kept severity is written only when the verdict changes the severity, so `unproven` leaves it `None`.
      - The kept severity is written only for `killed`, so a promoted concern keeps none.
      - The field defaults to the finding's severity at construction, so a finding no probe reached carries one.
  - claim: >-
      The `### Findings` table in the pull request body gains a `probe`
      column between `severity` and `where`. It holds each finding's probe
      verdict in backticks, or the mark `_disagreements` writes for a
      missing verdict when the finding has none. The severity cell names
      the severity the lens filed, after the current one, exactly when a
      verdict changed it. The witness renders eleven findings through
      `render_pr_body`. Nine are filed at each of `blocker`, `concern` and
      `note` and decided by each of `survived`, `killed` and `unproven`
      through `apply_probe_verdict`. One has no probe. One is built
      `survived` with no kept severity, as `survivor_finding` builds a
      host-filed blocker. The witness pins every line of the table.
    witness: tests/test_report.py::test_the_findings_table_names_each_probe_verdict_and_the_filed_severity
    wrong_versions:
      - The filed severity renders only for `killed`, so a concern a surviving probe promoted reads as a blocker the lens filed.
      - The filed severity renders whenever a verdict was applied, unchanged severities included.
      - The probe cell renders a verdict only when the severity changed, so `unproven` shows the empty mark.
      - A finding with no probe renders `None` in the probe cell.
      - A host-filed survivor renders a filed severity of `None`.
      - The filed severity is inferred from the verdict, so a `killed` finding always reads as filed `blocker`.
      - The verdict is appended to the severity cell and the table keeps five columns.
---

## Context

Backlog item **b-7c41e0**, cited as `DESIGN.md` §5.5 and §5.7. It was
found on 2026-09-18 in the spec review of `SA-0109`, which built the probe
run that decides a finding (backlog item 117). `SA-0109` forbade
`saffron/report/**`, so its cell could not fix the body.

The operator set the scope. A finding whose severity a probe changed
renders with the severity it was filed at, the one it has now, and the
probe's verdict. A reader can then tell a demoted blocker from a note the
lens filed. The filed severity rides on `Finding`, set where the verdict is
applied. Nothing re-reads `probes.json`.

**The base this cell runs on carries its parents' code.** `SA-0240` edits
`saffron/report/pr_body.py`'s new-failures section. `SA-0233` edits
`saffron/phases/review.py`'s `describe_wrong_versions` and
`saffron/cell/session.py`. Line numbers below were read before they
landed. Follow the function named beside each one.

## Problem

**The verdict overwrites the filed severity.** `apply_probe_verdict` sets
`probe_verdict`, then sets `severity` to `blocker` for `survived` and to
`note` for `killed` (`saffron/phases/review.py:828-838`). It keeps nothing
of the severity the lens filed. `Finding` carries `probe_verdict` and no
filed severity (`saffron/agents/findings.py:89-115`).

**Only `probes.json` keeps it.** `probe_findings` keeps each target's
severity in a `filed` map before deciding it (`saffron/cell/session.py:1532`).
It writes that into each entry as `filed_severity`
(`saffron/cell/session.py:1553`). The finding object itself loses it.

**The body renders the decided severity alone.** `_findings` writes one row
per finding with the columns `lens`, `severity`, `where`, `claim` and
`anchored` (`saffron/report/pr_body.py:356-373`). The severity cell is
`finding.severity` in backticks (`saffron/report/pr_body.py:368`). So a
blocker a killed probe demoted renders as a `note`, the same as a note the
lens filed. A concern a surviving probe promoted renders as a `blocker` the
lens filed.

**The body reads findings in memory, not from the ledger.** `package()`
passes `outcome.reviews` to `render_pr_body`
(`saffron/phases/package.py:894`). Those are the objects REVIEW decided in
place. So the ledger's `findings` table needs no new column for this.

**Two records dump `Finding` whole.** Each lens's review record writes
`f.model_dump()` per finding (`saffron/phases/review.py:165`). REBUT's
record writes each blocker the same way (`saffron/phases/rebut.py:142`). A
new field reaches both as a new key. One test pins `rebuttal.json`'s
blockers as an exact dict. It is
`test_a_wrong_version_its_witness_survives_is_rebutted_as_a_blocker`
(`tests/test_session.py:8826-8941`). Its one blocker is a host-filed
survivor, which no verdict was applied to. Add the new key there with
`None`, and change nothing else in that test.

## Out of scope

- **The ledger and the run record view.** `record_findings` writes the
  decided severity and no probe verdict (`saffron/ledger.py:1814-1840`).
  The `findings` table has no column for either
  (`saffron/ledger.py:216-228`). Neither learns the filed severity here.
- **`probes.json`.** Its `filed_severity` key and the `filed` map that
  feeds it stay as they are (`saffron/cell/session.py:1532`).
- **End-review findings.** `qualify` reaches `apply_probe_verdict` through
  `probe_findings` too (`saffron/qualify.py:148`). Their findings render in
  no pull request body, so only the new field reaches them.
- **The Disagreements table.** It numbers anchored blockers and shows
  REBUT's answers (`saffron/report/pr_body.py:280-353`). REBUT's prompt
  already names a surviving probe (`saffron/phases/rebut.py:170-174`).

## Notes for the agent

**An edit with one mutant.** Criterion 1 declares a mutant on a line of
`apply_probe_verdict` the change keeps. Its witness checks the decided
severity beside the kept one, so the mutant dies for the claim's own
reason. Criterion 2's change replaces the row `_findings` writes, so no
line it depends on survives the change. It declares a witness alone, and
`witness` reports `skip` for it.

**The field.** Add it to `Finding` after `probe_verdict`, typed
`Severity | None` with a default of `None`. Name it `filed_severity`, the
key `probes.json` already writes. Give it a docstring of one or two
lines. In `apply_probe_verdict`, write it from `severity` before the
verdict decides. Update that function's docstring to say so.

**The table.** The header row becomes the six column names in this order:
`lens`, `severity`, `probe`, `where`, `claim`, `anchored`. The separator row
grows to six cells. `anchored` stays last, since
`test_an_unanchored_finding_still_appears` reads the row's end
(`tests/test_report.py:881-897`).

- The severity cell is the current severity in backticks. When the field
  is set and differs from it, a parenthesis follows after one space. It
  holds the word filed and the filed severity in backticks.
- The probe cell is the verdict in backticks. With no verdict it is the
  same one-character mark `_disagreements` writes for a missing critic
  verdict (`saffron/report/pr_body.py:280-334`).
- A host-filed survivor has a verdict and no filed severity. Its severity
  cell is the current severity alone.

A blocker a killed probe demoted, from the `adequacy` lens, renders as this
row.

```
| `adequacy` | `note` (filed `blocker`) | `killed` | a.py:3 | the claim | yes |
```

**Criterion 1's witness.** Build each finding with `Finding(...)` directly,
as `tests/test_review.py` does elsewhere. Loop over the three filed
severities and the three verdicts. For each, assert the tuple of severity,
verdict and kept severity, with the pair in the assertion message. Expect
`blocker` after `survived`, `note` after `killed`, and the filed severity
after `unproven`.

**Criterion 2's witness.** Build each finding with `_finding`
(`tests/test_report.py:711-722`), with the lens `adequacy` and a claim that
names its filed severity and verdict. Decide the nine with
`review.apply_probe_verdict`, imported inside the test. Build the
host-filed one through `_finding` with `probe_verdict` set to `survived`.
Render with one `LensReview` holding all eleven, in a fixed order. Take
the `### Findings` section up to its blank line, and assert its lines equal
a literal list of thirteen strings. Write each expected row out in full,
never built by the code under test.

**Every test you add must fail with this diff's source reverted.** The
field does not exist at base. So criterion 1's witness raises on reading it.
Criterion 2's header line differs. Import nothing new at module scope.

**Sentences this change makes false.** `Finding`'s docstring for
`probe_verdict` names its readers (`saffron/agents/findings.py:110-115`). Add
`pr_body._findings`. `apply_probe_verdict`'s docstring says what the
verdict decides (`saffron/phases/review.py:828-833`). Add that the filed
severity is kept.
