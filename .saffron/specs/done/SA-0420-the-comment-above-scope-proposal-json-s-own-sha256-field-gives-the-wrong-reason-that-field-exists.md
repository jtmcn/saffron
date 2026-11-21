---
id: SA-0420
title: "The comment above scope_proposal.json's own sha256 field gives the wrong reason that field exists"
type: bug
priority: 3
estimated_lines: 28
estimate_measured: true
touches:
  - saffron/cell/session.py
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
  - saffron/intake.py
  - saffron/cli.py
  - saffron/projection.py
  - saffron/finish.py
  - saffron/gates/**
  - saffron/agents/**
  - saffron/credentials.py
  - saffron/events.py
  - saffron/task.py
  - saffron/phases/package.py
  - tests/test_credentials.py
  - tests/test_events.py
  - tests/test_intake.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
  - tests/test_constant_mutants.py
  - tests/test_package.py
  - tests/test_suite.py
  - tests/test_task.py
  - tests/test_worktree.py
budget_usd: 20
max_attempts: 2
max_turns: 60
acceptance:
  - claim: >-
      The two-line comment that sits above `scope_proposal.json`'s own
      `sha256` field (`saffron/cell/session.py:2691-2692`) names the right
      cause for that field's existence. It says `plan.json` needs no
      embedded hash because the whole file *is* the raw block, and that
      `scope_proposal.json` carries its own `sha256` precisely because it
      is not that raw block but a JSON wrapper holding it under a `raw`
      key, so a whole-file hash would not match the hash of that key alone.
      It no longer says the wrapper "holds raw text, so it carries its own
      hash too," which names holding raw text as the cause when the
      opposite is true: `scope_proposal.json` carries its own hash because
      it does *not* equal raw text on its own, unlike `plan.json`. The
      witness reads the comment lines directly above the dict's `"sha256":
      artifacts.hash_artifact(proposed.raw),` line from the file as
      written on disk, joins them, and checks the joined text both for the
      phrase `plan.json needs no embedded hash` tied to `the whole file
      *is* the raw block`, and for `scope_proposal.json` being named a JSON
      wrapper around a `raw` key — the bare word `raw` next to `key`, with
      no requirement that the comment itself spell the key as a quoted
      string — while the phrase `holds raw text` is absent from it.
    witness: tests/test_session.py::test_the_scope_proposals_hash_comment_names_why_it_differs_from_plans_json
    wrong_versions:
      - "The comment left as it was, saying the wrapper \"holds raw text, so it carries its own hash too.\""
      - "The comment's first line corrected to name plan.json's own property, with the second line still blaming the wrapper's own hash on holding raw text."
      - "The comment's two causes swapped, so plan.json is said to carry its own hash because it holds raw text, and the wrapper is said to need none because it is JSON around a raw key."

---

## Context

Filed from review of `SA-0417`, at its own head
`52b5138b7b2d1eb5399c07d434446810a3e3f254`. That spec reworded the
two-line comment above `scope_proposal.json`'s own `sha256` field
(`saffron/cell/session.py:2691-2692`). It fixed one stale line and left
the other line's cause backward.

**What each file is, read at the base commit.** `plan.json` is written at
`saffron/cell/session.py:2777` as `redacted_plan` itself. Nothing else
sits beside it in the file. The PLAN watch line at `:2781` hashes that
same text directly, so `sha256sum plan.json` reproduces it. No hash sits
stored inside `plan.json`.

`scope_proposal.json` is written at `saffron/cell/session.py:2686-2695` as
a `json.dumps` dict literal. Its `"raw"` key (`:2690`) holds
`proposed.raw`. Its own `"sha256"` key (`:2693`) holds
`artifacts.hash_artifact(proposed.raw)`. A whole-file hash of
`scope_proposal.json` would also cover the dict's braces and its other
keys. That gap is why the field exists, not anything about holding raw
text.

**The comment as it reads today.** Line 2691 names a true fact about
`plan.json`, not about this file. Line 2692 reads
`This wrapper holds raw text, so it carries its own hash too`. That names
holding raw text as the cause of needing a separate hash. `plan.json` is
the file that holds nothing but raw text, and that fact is why it needs
no separate hash at all. `scope_proposal.json` needs one for the opposite
reason: it holds the block inside a `raw` key, not as the whole file. The
comment names the wrong cause for the fact it documents.

## Problem

Reword the comment at `saffron/cell/session.py:2691-2692`. State that
`plan.json` needs no embedded hash because the whole file *is* the raw
block. Use that literal emphasis: asterisks around the word `is`. This
file already stresses single words that way, as four examples show.
`saffron/cell/session.py:170` uses `*absence*`, and
`saffron/cell/session.py:278` uses `*failed*`.
`saffron/cell/session.py:624` uses `*missing*`, and
`saffron/cell/session.py:1220` uses `*nearly*`. State that
`scope_proposal.json` carries its own `sha256` because it is a JSON
wrapper around a `raw` key, not the block itself. Write that second line
in plain prose. Name the key by the bare word `raw`. Use the same
unquoted-backtick style this file already uses for an identifier. The
line being replaced names the command as `` `sha256sum plan.json` ``, not
`` `"sha256sum plan.json"` ``. Do not wrap `raw` in a literal pair of
quote marks inside the comment. Only that field's own hash then matches
`artifacts.hash_artifact(proposed.raw)`. Keep the comment at two lines. A
comment over `COMMENT_LIMIT` lines (`.saffron/gates/prose.py:67`) is a
fresh `prose` hit against this file's own baseline. Change nothing else.
`proposed.raw`, the `"raw"` key, the `"sha256"` key and every other line
of the dict literal stay as written.

## Out of scope

- **Every other file `SA-0417` touched.** The token thread through
  `run_one_cell`, `run_task` and PACKAGE stays as that spec left it. So do
  `plan.json`, `notes.json`, the task's own `findings.json`, and
  `saffron/credentials.py`'s `redact` and `redact_nested`.
- **The docstring at `tests/test_session.py:16989`**, for
  `test_the_recorded_proposal_carries_the_hash_of_its_own_raw_block`. It
  states two true facts about two files side by side. It names no wrong
  cause.
- **Every other comment in the file.** This spec's witness reads only the
  two lines directly above `scope_proposal.json`'s `"sha256"` key.

## Notes for the agent

**Two lines, two facts.** Keep both sentences, one about `plan.json` and
one about `scope_proposal.json`'s own reason, inside `COMMENT_LIMIT = 2`
(`.saffron/gates/prose.py:67`). Keep each sentence under the 25-word
`SENTENCE_LIMIT` (`.saffron/gates/prose.py:73`). Use no colon, no
semicolon and no dash joining the two lines.

**The literal phrase, asterisks included.** The witness checks the
comment for one exact substring: `the whole file *is* the raw block`. It
must include the asterisks. It rejects a paraphrase, such as `equals the
raw block` or `is identical to the raw block`. Write the first line with
that exact wording.

**The second line's check is on the bare word, not a quoted key.** The
witness's second check looks for the word `raw` next to `key`.
For example, it matches `raw key` or `a raw key`, treated as plain words
in the comment text. It does not look for a literal `"raw"` substring
with quote marks. The first line's instructed wording, `the whole file
*is* the raw block`, names an identifier without quote marks. The
`` `sha256sum plan.json` `` text in the line being replaced follows that
same convention. A correctly worded comment that follows the Problem
section's instructions must pass this check. Do not add a requirement
that would fail it.

**The witness reads the file, not the import.** It opens
`Path(session.__file__)`, finds the line
`"sha256": artifacts.hash_artifact(proposed.raw),` by a substring search.
It then walks backward over the comment lines directly above that match.
It drops the line fragment before the match itself, since that fragment
is only the match's own leading indentation. `Path`, `re` and `session`
are already imported at module scope in `tests/test_session.py`. The
witness adds no new import.

**Measured.** A fix at this spec's own base measured 164 changed tokens
with the `size` gate (`saffron/gates/core/size.py::size_gate`), under the
`bug` ceiling of 1300. It touched two files: four lines in
`saffron/cell/session.py` and one new test in `tests/test_session.py`. The
witness failed against the comment left as it was. It also failed against
a version that fixed only the first line, and against a version that
swapped which file gets which reason.
