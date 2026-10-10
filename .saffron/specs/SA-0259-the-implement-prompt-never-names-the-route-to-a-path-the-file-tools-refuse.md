---
id: SA-0259
title: IMPLEMENT's prompt never says the file tools refuse a `touches` path, or that a python3 write through Bash reaches it
type: feature
priority: 1
depends_on: []
estimated_lines: 170
estimate_measured: true
touches:
  - saffron/agents/context.py
  - saffron/cell/session.py
  - tests/test_context.py
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
  - saffron/agents/prompts/**
  - saffron/phases/**
  - saffron/gates/**
  - saffron/scheduler.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/end_review.py
  - saffron/intake.py
  - saffron/ledger.py
  - tests/test_end_review.py
  - tests/test_scheduler.py
budget_usd: 42
max_attempts: 3
max_turns: 150
acceptance:
  - claim: >-
      A `touches` entry naming any path the evidence record shows refused is
      named in the route section, and no other entry is. The nineteen file
      names the record shows refused are each named as the whole entry, one
      directory down and two down. Its five directory names are each named
      as the whole entry, as the last of two components, as a first
      component, as a second and as a middle one. Each is driven beside "src/**", which the section must not name.
      The witness spells all twenty-four names itself, from the record's
      tables, and drives each one in every one of those positions.
    witness: tests/test_context.py::test_every_measured_unwritable_name_is_named_at_any_depth
    wrong_versions:
      - A set missing one of the names measured at the root only, such as "lefthook.yaml".
      - A match on the whole entry alone, so "sub/.gitmodules" is not named.
      - A match on the first component alone, so "sub/.vscode/x.md" is not named.
      - A directory name matched as a last component only when it is the whole entry, so "sub/.claude" is not named.
      - A section that names every `touches` entry, so "src/**" is named too.
  - claim: >-
      An entry the record shows written gets no route section at all, each
      as its own `touches`. That covers its twenty-one written paths and its
      seven near misses. A refused file name as a non-final component gets
      none, as in "docs/.envrc/notes.md". A component holding `*`, `?` or
      `[` is skipped, so ".claud?/x.md", "[.]claude/x.md", ".vscode*/x.txt"
      and "**" get none. A literal component beside a glob one still
      decides the entry, so ".claude/**", "**/.pre-commit-config.yaml" and
      "docs/*/.husky/pre-commit" are named. An empty `touches` gets none.
    witness: tests/test_context.py::test_a_near_miss_or_a_glob_component_is_not_named
    wrong_versions:
      - A prefix match on a name, so ".claudeignore" and ".vscode-test/x.txt" are named.
      - A file name matched at any component, so "docs/.envrc/notes.md" is named.
      - A glob component matched as a pattern against the names, so ".claud?/x.md" is named.
      - An entry skipped whole when any component holds a glob character, so ".claude/**" is not named.
  - claim: >-
      IMPLEMENT's system prompt, as the cell builds it, names each `touches`
      entry in the measured set, in one section. The section says the
      Write tool is refused on them. It says Edit and shell redirects were
      refused on ".pre-commit-config.yaml" in one cell. It says to write
      each with a python3 script run through Bash. The salvage turn's
      system prompt carries the same section. `constraints_block`, which
      the end review also reads, carries no route for those same
      `touches`. A spec with no such entry gets a prompt byte for byte
      equal to the one `build_system_prompt` assembles from today's four
      values. The witness drives two cells. One touches "src/**",
      "tests/**", two near misses, ".pre-commit-config.yaml" and
      "sub/.claude/skills/x.md", and is cut off and salvaged. The other
      drops the last two and is compared whole.
    witness: tests/test_session.py::test_the_implement_prompt_routes_each_unwritable_touch_and_no_other
    wrong_versions:
      - The section built and never added to the prompt the cell sends.
      - A section that names only the first matching entry.
      - A separator added even when no entry matches, so a spec with none gets a changed prompt.
      - A section that never names shell redirects.
      - A section that never names python3 or Bash.
      - The section appended inside `constraints_block`, so the end review's prompt carries the route too.
      - The section added only to IMPLEMENT's own `agent_options` call, so the salvage turn's prompt lacks it.
  - claim: >-
      Core records the SDK version the set was measured at, and it equals
      the one `ARG SDK_VERSION` line in `images/cell-base.python.Dockerfile`.
      So a version bump fails this test until the set is measured again.
    witness: tests/test_context.py::test_the_unwritable_set_was_measured_at_the_cell_images_sdk
    wrong_versions:
      - The image's `SDK_VERSION` bumped with the recorded version left as it is.
      - A recorded version other than the image's.
---

## Context

Backlog item **b-f8fa24**, from the spec loop's run 32, with its
measurement in `docs/evidence/2026-10-10-agent-unwritable-paths.md`. It
also settles **b-e471bd**, the same refusal for `.claude/` alone. It
cites `DESIGN.md` §5.3. Every line number below was read at `5bdf2103`.

**The file tools refuse some paths, and Saffron does not choose which.**
IMPLEMENT passes `permission_mode="dontAsk"` and an empty
`setting_sources` (`saffron/phases/implement.py:164-167`). Under those
options the pinned SDK refused Write on 41 of 69 candidate paths. The
refusal keys on an exact path component at any depth. The record's
"Refused" table names nine file names and five directory names, each
refused at the root and nested. It then lists twelve paths refused at the
root, with the nested form untried. Ten of those are single file names.
A file named `.claude` is refused too. Its "Written" section names the
paths it wrote, near misses included. The image pins that SDK at
`images/cell-base.python.Dockerfile:33`.

**A python3 write through Bash is not refused.** The record's "What gets
past it" section measured it. An allow rule in `allowed_tools` did not
lift the refusal. A `python3` one-liner calling `pathlib.Path.write_text`
through Bash wrote all five refused paths it tried. `SA-0116` and
`SA-0196` merged that way. `SA-0255`'s agent tried a heredoc and `printf`,
never Python, and ended `EXHAUSTED` at $2.31. IMPLEMENT offers Bash
(`saffron/phases/implement.py:30`).

**Nothing in IMPLEMENT's prompt says so.** `_drive_cell` builds that
prompt with `build_system_prompt` (`saffron/cell/session.py:2090-2103`).
It passes four values
to `build_system_prompt`: the spec body, `constraints`, `witnesses` and
`standing_instructions`. `constraints_block` turns `touches`, `forbidden`
and the protected list into the `{constraints}` value
(`saffron/agents/context.py:74-98`). The template puts that value under
"## The paths you are judged against" (`saffron/agents/prompts/implement.md:86-94`).
`end_review.py` calls `constraints_block` too
(`saffron/end_review.py:184`).

## Problem

Name, in IMPLEMENT's prompt, each `touches` entry the file tools refuse.
Say the Write tool is refused on it, as the record measured over the
set. Say Edit and shell redirects were refused on
`.pre-commit-config.yaml` in one cell, as `SA-0255` saw. Say to write it
with a python3 script run through Bash. A spec with no such entry keeps
today's prompt exactly.

Build the section in `saffron/agents/context.py` from the spec's
`touches`. Add it to the `constraints` value `_drive_cell` passes for
IMPLEMENT alone. Every session resumed from IMPLEMENT then carries it,
the salvage turn included, since salvage rebuilds its options from the
same `system_prompt` (`saffron/cell/session.py:2446-2447`). Leave
`constraints_block` as it is, so the end review's prompt does not
change.

The refused names are one constant in `saffron/agents/context.py`, built
from the record's "Refused" section. A comment of one or two lines cites
the record. A constant beside it records the SDK version the set was
measured at.

A literal path component equal to a refused directory name matches the
entry. So does a literal final component equal to a refused file name. A
component holding a glob character is skipped.

## Out of scope

- **Whether the agent then writes the file.** No test here runs a model.
  The witnesses check the prompt the cell sends, never what an agent does
  with it.
- **A refusal at intake.** The operator chose the route over a refusal.
- **The template.** `saffron/agents/prompts/implement.md` stays as it is.
  A new slot there adds blank lines to every prompt, and changes
  `prompt_sha`.
- **Two refused paths that are not one name.** The record refused
  `.git/hooks/pre-commit` and `.config/git/config` at the root. Git tracks
  no path under `.git/`, so no diff carries the first. The second names
  no single component the refusal keys on, since `.config/` alone was never
  tried. Leave both out of the set.
- **Edit over the whole set.** The record measured Write alone over the
  whole list. `SA-0255`'s cell saw Edit and shell redirects refused on
  one path, `.pre-commit-config.yaml`.
- **`DESIGN.md` and `CONTEXT.md`.** §5.3 is edited by hand with this spec.

## Notes for the agent

**The change is new code**, so each criterion declares a witness and no
mutant, and `witness` will report `skip`.

**At base every witness fails.** Criteria 1, 2 and 4 read the new names
through `context` inside the test body. So the reverted run fails in the
test, not at collection. Criterion 3's first cell gets no section at
base.

**Criteria 1 and 2 spell the record's lists in the test.** A test that
iterates core's constant passes a constant missing a name. Copy the names
from the record's tables and its "Written" section.

**Criterion 3** drives `_drive` twice in one plain test, with `_spec`,
`_stub_the_runtime`, `_turn`, `_block` and `_PLAN` from
`tests/test_session.py`. The IMPLEMENT prompt is `cell.system_prompts[0]`.
The first cell copies the shape of
`test_a_turn_cut_off_at_the_ceiling_with_nothing_committed_is_salvaged`,
so its third turn is the salvage turn. Assert its system prompt equals
the first one.
Build the expected prompt for the second cell with `build_system_prompt`,
the template file and `constraints_block`, as `_drive_cell` does today.
Compare the whole string with `==`.

**The `dead` gate reads `saffron/` alone.** A constant only a test reads
fails it as unused. The section names the recorded version, which reads
the constant in core.

**`saffron/cell/**` is in `elevate_on`,** so this task runs `elevated`
and `size` blocks.

**Ponytails to write in the code.** Ten file names were measured at the
root only, and the set matches them at any depth. A glob component is
skipped as undecidable.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size.** A prototype with every witness measured 627 tokens with
`size_gate`'s counter, against the `feature` ceiling of 3000.
`estimated_lines` is that count over four, plus a margin for comments.
