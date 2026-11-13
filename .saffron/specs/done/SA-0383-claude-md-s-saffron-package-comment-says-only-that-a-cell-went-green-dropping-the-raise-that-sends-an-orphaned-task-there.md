---
id: SA-0383
title: "CLAUDE.md's `saffron package` comment says only that a cell went green, dropping the raise that sends an ORPHANED task there"
type: bug
priority: 3
estimated_lines: 20
estimate_measured: true
touches:
  - CLAUDE.md
  - tests/test_task.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - harness/**
  - images/**
  - records/**
  - hooks/**
  - saffron/**
  - tests/test_cli.py
  - tests/test_citations.py
  - tests/test_batch.py
  - tests/test_session.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
  - tests/conftest.py
  - tests/fixtures/**
budget_usd: 12
max_attempts: 2
max_turns: 40
risk: standard
acceptance:
  - claim: >-
      CLAUDE.md:65's command-table comment for `saffron package` says
      "...whose own PACKAGE raised, or whose cell went green," naming the
      second, `SA-0380`-added case only by its green cell, with no raise
      in sight. Read alone, "whose cell went green" is equally true of an
      ordinary `READY_FOR_REVIEW` task, since reaching REVIEW is itself a
      green cell with no raise. CLAUDE.md's own `saffron/task.py` layout
      bullet already names that same second case precisely: the bullet
      starts at line 159 with "- `saffron/task.py` — `run_task` drives
      one task end to end...", and its clause "a task whose PACKAGE
      raised, or whose cell raised but rebuilds green" wraps onto line
      161, two physical lines below the bullet's own leading text. The
      command-table line instead carries that exact qualifier, "whose
      cell raised but rebuilds green," word for word, so an operator
      skimming either line reads the same gate.
    witness: tests/test_task.py::test_claude_md_command_table_names_the_cells_raise_not_just_its_green_review
    wrong_versions:
      - CLAUDE.md:65 is left reading "...or whose cell went green," unedited from base.
      - CLAUDE.md:65 is reworded to "...or an ORPHANED one whose cell went green," naming the task state but still dropping the raise.
      - CLAUDE.md:65 is reworded to "...or whose cell rebuilds green," dropping "raised but" and so dropping the raise again.
      - CLAUDE.md:161 is reworded to match line 65's old text instead of the other way around, leaving line 65 unedited.
---

## Context

`SA-0380` (backlog `b-f582ee`) taught `saffron package` to rebuild an
`ORPHANED` task too. Such a task's cell must have gone green, been
reviewed, and still end `READY_FOR_REVIEW`. That change touched five
files to say so, and kept one qualifier everywhere it landed except
one line.

**Every other landing spot names the raise, not only the green cell**.
`saffron/task.py:1166`, the `ReadyTask` docstring, says the second case
is "for an `ORPHANED` one whose cell went green and whose review would
end there". "ORPHANED" itself carries the raise. `saffron/task.py:962-996`,
`run_task`'s `except BaseException` block, is the only place a live row
reads `ORPHANED`, and it runs only after `run_one_cell` raises.
README.md:178-179 says "on an `ORPHANED` task whose cell went green",
likewise naming the state. `saffron/cli.py:250`'s `--help` text says
"an ORPHANED one whose cell went green", the same. CLAUDE.md's
`saffron/task.py` layout bullet, which starts at line 159 and wraps
across lines 160-162, skips naming the state outright. It says instead,
on line 161, "a task whose PACKAGE raised, or whose cell raised but
rebuilds green", naming the raise in so many words.

**CLAUDE.md:65 alone drops both**. The `saffron package` line in the
command table says "run PACKAGE alone on a task whose own PACKAGE
raised, or whose cell went green". That is the one line among the
whole change's five landing spots an operator skimming the table is
most likely to read. It names neither `ORPHANED` nor a raise for the
second case. Taken on its own, "a task whose cell went green" reads as
true of any ordinary task that reached REVIEW cleanly, with no raise.

## Problem

- **The one line an operator skims most understates the gate.** CLAUDE.md's
  command table is a quick-reference list. Every other entry in it is a
  single clause. Its `saffron package` entry's second clause, as it
  stands, reads as true of a case `saffron package` refused before
  `SA-0380` and still refuses today. A `READY_FOR_REVIEW` task whose cell
  never raised reaches REVIEW by going green too.

## Out of scope

**CLAUDE.md:162**. A review note asked to fix a sentence there, said to
call `ORPHANED` a cell's state rather than a task's. At this head,
CLAUDE.md:162 reads "It runs no agent and never reaches
`run_one_cell`". That sentence names no state at all. It is part of
the `saffron/task.py` bullet fixed above. CLAUDE.md contains no
occurrence of `ORPHANED`, and no occurrence of `ready_task` either.
There is nothing at that line, or anywhere else in CLAUDE.md, for this
spec to correct.

**Every other file the review note cited**. `saffron/task.py:1166`,
`README.md:178-179` and `saffron/cli.py:250` already carry the raise
qualifier shown above, each in that file's own house style. None of the
three needs editing, so `saffron/`, `README.md` and the other test
files stay forbidden.

## Notes for the agent

**The fix is one word-for-word substitution**. Replace CLAUDE.md:65's
trailing clause, "or whose cell went green", with the clause already on
CLAUDE.md:161, "or whose cell raised but rebuilds green". Nothing else
on the line, or elsewhere in the file, changes. The result still fits
under the file's own longest existing line, with a few characters to
spare.

**The witness reads CLAUDE.md itself, not a copy of its wording.** Load
`CLAUDE.md` from disk in the test. Find the `saffron package` line in
the command table by its leading text, e.g. the substring "run PACKAGE
alone on a task whose own PACKAGE raised". That whole clause sits on
one physical line, so a single-line check of it is enough: assert that
`"whose cell raised but rebuilds green"` appears on that line, and that
`"went green"` no longer does.

The `saffron/task.py` layout bullet is different. Its leading text is
the substring "- `saffron/task.py` — `run_task` drives one task end to
end". That leading text sits on one physical line. The qualifier
`"whose cell raised but rebuilds green"` wraps onto a later physical
line of the same bullet. It lands before the next bullet starts. The
next bullet's own leading text is "- `saffron/agents/`". Do not check
only the single line matched by the bullet's leading-text anchor for
the qualifier. It will not be there. Instead, find the index of the
bullet's leading text in the file's full, unsplit text. Then find the
index of the next bullet's leading text after it. Take the slice of
the full text between those two indices. Assert the qualifier appears
somewhere in that slice.

No new import is needed. `tests/test_task.py` already imports `Path`
from `pathlib`.
