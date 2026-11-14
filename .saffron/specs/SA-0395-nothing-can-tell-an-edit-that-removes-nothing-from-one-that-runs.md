---
id: SA-0395
title: "Nothing host-side can tell an edit that keeps its find and adds only unread definitions from one that changes what the file runs"
type: feature
priority: 3
risk: standard
estimated_lines: 187
estimate_measured: true
touches:
  - saffron/probe.py
  - tests/test_probe_check.py
pending_symbols:
  - saffron/probe.py::inert_edit
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
  - saffron/repos/**
  - saffron/phases/**
  - saffron/gates/**
  - saffron/qualify.py
  - saffron/intake.py
  - saffron/task.py
  - saffron/cli.py
  - tests/test_session.py
  - tests/test_review.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 26
max_attempts: 3
max_turns: 150
acceptance:
  - claim: >-
      `saffron/probe.py` gains `inert_edit(before, edit)`. It returns a reason
      when the edit cannot change what the file runs, and `None` otherwise.
      `before` is the edited file's text. The reason starts with the edit's
      file and says the edit removed nothing of its find. It is returned only
      when all of these hold. The file ends `.py`. Its `find` matches
      `before` exactly once. Its `replace` holds the whole `find`. Both
      `before` and the edited text parse. Every top-level statement of
      `before` is still in the edited text, in order and unchanged. Every
      other top-level statement there is a definition that runs no
      expression when the module loads. Its name starts with an underscore,
      is no dunder, and no word of `before` spells it. Such a definition is
      a `def` or an `async def` with no decorator, no annotation on any
      parameter or its return, and only literal defaults, keyword-only ones
      included. It can also be a `class` with no decorator, base or keyword,
      whose body holds only `pass`, a docstring or such definitions. The
      witness drives eight refused edits against one file. It appends a
      `def`, puts one before the find, and appends an `async def`. It
      appends a `class` holding a docstring, a method and a bare nested
      `class`. It appends a `def` with a literal default and a literal
      keyword-only default, and two `def`s where one calls the other. It
      repeats the find unchanged, and adds only a comment. It drives
      twenty-nine edits that return `None`, and one more against a `before`
      that does not parse. Four of the twenty-nine keep the find and add code
      that runs: an early `return` inside the function, the call wrapped in
      another, a top-level call and a top-level constant. One deletes part of
      the find, and one reformats it with the same syntax tree. Ten change
      an added `def` or `async def`. They are a decorator on each, a call
      default and a keyword-only call default, and a return annotation. The
      other five are an annotation on a plain, a positional-only, a
      keyword-only, a `*` and a `**` parameter. Five give an added `class` a
      decorator, a base, a keyword, a statement in its body, or a nested
      `class` holding a statement. Four name the added definition after a
      function the file defines, after a name the file only calls, as a
      dunder, or with no leading underscore. The last four aim at a `.txt`
      file, use a find that matches twice, use one that is absent, and
      leave the edited text unparseable.
    witness: tests/test_probe_check.py::test_an_edit_that_keeps_its_find_and_adds_only_unread_definitions_is_inert
    wrong_versions:
      - The syntax trees compared alone, so a reformat that changes the find's text is refused.
      - The find's count never checked, so an edit whose find matches twice is judged and refused.
      - Only the edited text guarded against a parse error, so a `before` that does not parse raises.
      - Decorators never read, so a decorated added `def` is refused.
      - Decorators read on a `def` alone, so a decorated `async def` is refused.
      - Default values never read, so a `def` whose default is a call is refused.
      - Keyword-only defaults never read, so a `def` whose keyword-only default is a call is refused.
      - Annotations read on plain parameters alone, so a positional-only, keyword-only, `*` or `**` annotation is refused.
      - The return annotation never read, so a `def` with one is refused.
      - The added name never looked for in the file, so a `def` that redefines one of the file's functions is refused.
      - The added name looked for only among the file's definitions, so a `def` named after a function the file only calls is refused.
      - A dunder name admitted, so an added module `__getattr__` is refused.
      - A public name admitted, so an added `def` a star import would carry is refused.
      - Every file judged, so a `.txt` edit that keeps its find is refused.
      - A `class` never admitted, so an appended bare class is not refused.
      - A class's bases never read, so a `class` with a base is refused.
      - A class's decorators never read, so a decorated `class` is refused.
      - A class's keywords never read, so a `class` with a metaclass is refused.
      - A class's body never read, so a `class` whose body calls a function is refused.
      - A nested `class` admitted without reading its body, so one holding a call is refused.
      - Only text after the find judged, so a `def` put before the find is not refused.
      - At least one added definition required, so an edit that repeats its find or adds a comment is not refused.
      - Any added top-level statement admitted, so an appended top-level call is refused.
---

## Context

Backlog item **b-7fc792**, filed from spec loop run 70 while reviewing
#1203 (`SA-0390`). It cites `DESIGN.md` §5.4.1 and §5.5. Every line number
below was read at `dffa5474`.

**What happened**. `SA-0390` declared a wrong version for its queue line.
It reads "`risk` is left out, so it reads `standard`." REVIEW's wrong-version session gave a reason
that names deleting the `risk=` keyword from `queue_line`. Its edit kept
the whole `find` and appended `def _risk_placeholder_removed_marker():
pass` after it. The witness passed under an edit that changed nothing, and
the host filed the version `survived` as an adequacy blocker. The task's
`wrong-versions.json` under `~/.saffron/batches/v0/SA-0390/` holds the
edit and its outcome.

**What judges an edit today**. The REVIEW block puts each criterion probe
and each wrong version into one list of pairs
(`saffron/cell/session.py:3514`). `_apply_criterion_probes` takes that list
(`saffron/cell/session.py:2072`). It refuses a pair host-side when
`probe.probe_refusal` names a reason (`saffron/cell/session.py:2109-2120`).
`probe_refusal` reads only the path (`saffron/probe.py:154`). In the cell,
`worktree.source_mutated` yields a reason for six edits that apply nothing
(`saffron/cell/worktree.py:712-717`). Nothing judges an edit that applies
and changes nothing.

**This spec is the rule alone**. It adds a pure function beside
`probe_refusal`. The function reads a file's text and one edit. It says
whether the edit can change what the file runs. `saffron/probe.py` already imports
`Mutant` (`saffron/probe.py:40`). `SA-0396` calls the function, so it is
listed under `pending_symbols`.

## Problem

Add `inert_edit(before: str, edit: Mutant) -> str | None` to
`saffron/probe.py`, beside `probe_refusal`. It reads text and runs nothing.
Use `ast` from the standard library. Compare top-level statements with
`ast.dump`, which leaves out line numbers. Look for a name in `before` as a
whole word. The rule is the criterion's claim.

Every condition the claim lists is a reason to return `None`, so a case the
rule cannot show runs nothing is left to run. A `find` that does not match
`before` exactly once returns `None` too. `source_mutated` then judges it in
the cell, as at base.

## Out of scope

- **The call**. `SA-0396` wires `inert_edit` into `_apply_criterion_probes`.
  The host-side read through `SA-0394`'s `files_after` lands there. So do
  the handling of an empty read and of a `GitError`, and the `unproven`
  record with its `refusal` key. So do the reworded docstrings that name
  `probe_refusal` as the only refusal.
- **Hand edits**. `DESIGN.md` §5.4.1's wrong-version paragraph and
  `CONTEXT.md`'s Wrong version entry change with `SA-0396`, when the host
  starts declining such an edit. This spec changes nothing a reader sees.
- **A lens's own adequacy probe** (`saffron/cell/session.py:1877`). A later
  spec can call `inert_edit` there.
- **An inert edit outside the narrow shape**. An added top-level constant,
  a decorated helper, a public name or a non-Python file returns `None`. So
  does a reformat that keeps the syntax tree but not the find's text.
- **A `retired_first`**. Nothing calls the rule until `SA-0396`, and it
  refuses edits REVIEW names, never a spec.

## Notes for the agent

**The function is new code**, so the criterion declares a witness and no
mutant, and `witness` will report `skip`.

**At base the witness fails in its body**. `probe.inert_edit` does not
exist there. `tests/test_probe_check.py` imports the module as
`probe_check` (`tests/test_probe_check.py:18`), so call the function
through it and never import the name at module scope.

**The witness** is one plain `def`, not a parametrised test. Hold one
`before` text with an import, one private function and a return that calls
a private name the file does not define. Keep a dict of refused edits and
one of edits that return `None`, keyed by a case name. Pass the name as
each assertion's message. Assert a refused reason's prefix and its words
"removed nothing". For "find twice", pick a word the text holds twice and
make the edit's `replace` that same word. For "find absent", let the
`replace` hold the absent `find`, so only the count can return `None`.
Drive the unparseable `before` by prefixing the text with a line that does
not parse.

**The `dead` gate** reads `pending_symbols` while this spec is open, so
`inert_edit` with no caller passes it.

**The `prose` gate** counts each new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size**. A prototype measured 347 counted tokens in `saffron/probe.py`
and 399 in the witness, about 187 changed lines.
