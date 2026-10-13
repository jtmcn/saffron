---
id: SA-0290
title: Two queued specs in separate chains can clash on a name one deletes and the other reads, and the queue compares only paths
type: feature
priority: 2
depends_on: [SA-0279]
estimated_lines: 300
estimate_measured: true
touches:
  - saffron/intake.py
  - saffron/scheduler.py
  - tests/test_intake.py
  - tests/test_scheduler.py
  - tests/test_refusal_count.py
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
  - saffron/cli.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/ledger.py
  - saffron/repos/**
  - saffron/agents/**
  - saffron/phases/**
  - saffron/gates/**
  - saffron/cell/**
  - tests/test_queued_specs.py
  - tests/test_consumes.py
budget_usd: 34
max_attempts: 3
max_turns: 160
acceptance:
  - claim: >-
      A spec may declare `removes`, a list of repo-relative `path` or
      `path:name` entries. It is empty when omitted, and it loads with no
      `depends_on`. Load refuses a `removes` entry on each shape it refuses
      a `consumes` entry, and the witness drives all eight. Those are an
      empty entry, an empty path, an empty name, an absolute path, a `.`
      segment, a `..` segment, a trailing `/` and a `//`. Each refusal
      names its entry and never says `consumes`.
    witness: tests/test_intake.py::test_a_removes_entry_is_refused_on_each_shape_consumes_refuses
    wrong_versions:
      - The `consumes` validator extended to `removes` with its messages unchanged, so a refused `removes` entry reads as a `consumes` entry.
      - The rule that `consumes` needs a `depends_on` copied, so a `removes` with no parent does not load.
      - A second validator written for `removes` that skips one shape, such as an empty name after the colon.
      - Only `path:name` accepted, so a bare path entry does not load.
  - claim: >-
      The queue scan refuses one of two candidate specs when one declares
      `removes: [saffron/cell/runtime.py:GATEWAY]`, the other's body says
      `runtime.GATEWAY`, and neither declares a `depends_on`. It holds the
      later id as a string, under the `depends_on` kind, and the earlier id
      stays a candidate. The witness drives both orientations, the remover
      as the later id and as the earlier one. It drives each with and
      without `stack=True`. The remover's own body names `GATEWAY` as well.
      The reason names both ids and `GATEWAY`.
    witness: tests/test_scheduler.py::test_a_spec_removing_a_name_another_reads_refuses_the_later_id
    wrong_versions:
      - The reader always held, so the pair whose remover has the later id refuses the reader.
      - The remover always held.
      - A spec compared with itself, so a remover whose own body names the name refuses itself.
      - The check made only where `_refuse` checks `depends_on`, which `stack=True` skips, so a stack batch admits both.
      - A reason that leaves out either id or the name.
      - Whitespace-separated words compared with the name, so `runtime.GATEWAY` is not read as naming it.
      - A refusal kind of its own, which `RefusalKind` and the count in §4.2.1 do not name.
  - claim: >-
      The scan reads a removed name from the other spec's body, from its
      acceptance claims and from its `consumes`. A `path:name` entry is
      matched on its name, and a bare `path` entry on its path. A `consumes`
      entry matches on its own name, or its path when it names none. The
      witness drives four pairs, each holding the name in one place only.
      Those are a bare path in the body, a name in a claim, a name as a
      `consumes` entry's name under another path, and a bare path as a
      `consumes` entry. Each refuses the reader, the later id.
    witness: tests/test_scheduler.py::test_a_removed_name_is_read_from_the_body_the_claims_and_consumes
    wrong_versions:
      - The body read alone, so a name in a claim admits the reader.
      - The reader's `consumes` left unread.
      - A `consumes` entry compared whole with the `removes` entry, so the same name under another path admits the reader.
      - A bare path entry skipped as naming nothing.
  - claim: >-
      A removed name matches only as a whole word. It needs no letter, digit
      or underscore on either side, and its case must match. A reader whose
      body holds only `GATEWAY_V2`, `NOGATEWAY` or `gateway` leaves both
      specs candidates. So does a reader holding `saffron/cell/old_py` or
      `saffron/cell/old.pyc` beside a removed `saffron/cell/old.py`. A
      reader whose body starts with `GATEWAY` is refused.
    witness: tests/test_scheduler.py::test_a_removed_name_matches_only_as_a_whole_word
    wrong_versions:
      - A substring test, so `GATEWAY_V2` and `NOGATEWAY` refuse the reader.
      - A match that ignores case, so `gateway` refuses the reader.
      - The name put into a regular expression unescaped, so `saffron/cell/old_py` refuses the reader.
      - A boundary that needs a character before the name, so a body starting with it admits the reader.
  - claim: >-
      No refusal names the removed name when a `depends_on` path joins the
      pair, in each of three arrangements. The reader depends on the
      remover, the remover depends on the reader, or the reader depends on
      a third spec that depends on the remover. Under `stack=True` all three
      specs are candidates. The same pair with no `depends_on` is still
      refused, in both modes. A remover whose task is `MERGED` at its
      `spec_sha` is no candidate, and the reader beside it is a candidate
      with no refusal.
    witness: tests/test_scheduler.py::test_a_depends_on_path_either_way_lifts_the_removed_name_refusal
    wrong_versions:
      - One direction checked, the reader on the remover only.
      - Direct `depends_on` entries read with no walk, so the path through a third spec still refuses.
      - Pairs drawn from every spec in the directory rather than the candidates, so a remover done at its `spec_sha` still holds the reader.
  - claim: >-
      No retired spec declares `removes`, so the whole retired corpus,
      scanned at top level, still refuses only on `depends_on` and on
      `SA-0063`'s disclosed mutant.
    witness: tests/test_scheduler.py::test_no_real_spec_is_refused_on_its_own_acceptance_criteria
    preserves: true
---

## Context

Backlog item **b-e773d9**, filed 2026-10-12 while writing `SA-0284`. It
cites `DESIGN.md` §4.2.1. Every line number below was read at `cf3db797`.

**The pair it was filed from.** `SA-0268` added a host probe to
`saffron/task.py` that read `runtime.GATEWAY`. `SA-0271` deletes
`GATEWAY` and forbids `saffron/task.py`. The two sat in separate chains
with no `depends_on` between them. Whichever landed second would end
`EXHAUSTED`. PR #849 fixed the pair by hand. At `cf3db797`,
`SA-0268` is retired to `done/` and names `GATEWAY` four times in its
body. `SA-0271` is queued and names it eleven times.

**The queue never compares two specs.** Each refusal in `_refuse`
(`saffron/scheduler.py:735-800`) judges one candidate alone, against the
policy, open pull requests, markers or the ledger. As filed, the two specs
above shared no path, because each forbade the file the other changed.
PR #849 then moved `saffron/task.py` into `SA-0271`'s `touches` and
added `SA-0268` to its `depends_on`.

**A spec declares the names it reads, and none it deletes.**
`Spec.consumes` holds a `path` or `path:name` a parent built
(`saffron/intake.py:169-171`). Its validator refuses an empty entry, an
empty path or name, and a path that is not canonical
(`saffron/intake.py:218-244`). A separate model validator refuses
`consumes` with no `depends_on` (`saffron/intake.py:246-254`). No field
names what a spec deletes. `Spec` sets `extra="forbid"`, so it
refuses an unknown key (`saffron/intake.py:160`).

**How the scan builds and refuses.** `build_queue`
(`saffron/scheduler.py:1000`) parses every spec in the directory with
`discover_specs` (`saffron/scheduler.py:1055`). It keeps as a candidate each one with no
task done with it at its `spec_sha`. It then runs `_refuse` on each
candidate in scan order (`saffron/scheduler.py:1150-1167`).
The loop passes `check_dependencies=not stack`
(`saffron/scheduler.py:1161`). So under `stack=True`, `_refuse` skips its
`depends_on` loop and `_stack_order` decides `depends_on` instead.
`_criteria_texts` (`saffron/scheduler.py:295-300`) returns a spec's
acceptance claims as prose.

**When two specs compete, the scheduler lets the lower id through.**
`_resolve_stack_base` takes the lowest qualifying id with
`min(qualifying)` (`saffron/scheduler.py:895`). A spec naming another qualifying id is
refused with a reason that names the winner "by the lower id"
(`saffron/scheduler.py:899-908`). `_stack_order` breaks a priority tie on
`c.spec.id`, the lower id first (`saffron/scheduler.py:977`).

**The refusal count is pinned.** `RefusalKind` names eight kinds
(`saffron/scheduler.py:172-181`). `tests/test_refusal_count.py` holds
that to the count in `DESIGN.md` §4.2.1, and pins each kind's sites in `SITES`
(`tests/test_refusal_count.py:37-49`). `depends_on` has two. No module in
`saffron/` but `scheduler.py` reads `Refusal.kind`.

## Problem

Add `removes:` to `Spec`, and make the queue scan refuse a pair of
candidate specs that clash on a removed name.

**The field.** `removes` is optional and empty by default. Each entry is
a `path` or `path:name`, validated exactly as a `consumes` entry is. A
validator shared by both fields names, in each message, the field it
read. `removes` needs no `depends_on`.

**The refusal.** Take two candidates, a remover and a reader. The
remover declares a `removes` entry. Its subject is the entry's name, or
its path when it names none. The reader clashes with it when either
holds.

- The reader's body or one of its acceptance claims holds the subject as
  a whole word. No letter, digit or underscore stands on either side, and
  case must match.
- One of the reader's `consumes` entries has the same subject, read the
  same way.

The pair is refused when no `depends_on` path joins the two, in either
direction. Walk the `depends_on` of every spec the directory parsed, live
specs only. The scan holds the later id of the two, compared as strings,
under the existing `depends_on` kind. The reason names both ids and the
subject, and says to add a `depends_on` in either direction.

Compute the clashes once in `build_queue`, over every candidate, before
the per-candidate loop. In the loop, refuse a candidate on a clash only
when `_refuse` let it through. That keeps one refusal per spec, keeps
refusals in scan order, and reaches both modes. Under `stack=True` a held
spec never reaches `_stack_order`.

Update `tests/test_refusal_count.py`: `depends_on` gains a third site,
and its comment names it. Add a paragraph on this refusal to the module
docstring of `saffron/scheduler.py`, and a sentence to `build_queue`'s.
Write the five new tests the criteria name.

## Out of scope

- **Declaring `removes` on `SA-0271` or any queued spec.** The operator
  adds them by hand later.
- **A pre-flight command over spec text** in `.claude/skills/`. `SA-0279`
  refuses any spec touching `.claude/`, so that arm lands by hand.
- **`saffron cell` and `run_task`.** Each runs one spec, and a clash
  needs two. The scan alone refuses it.
- **A pair where one spec is done at its `spec_sha` or retired to
  `done/`.** It is no candidate, so the other runs. A merged remover can
  still break a reader queued after it. The spec loop's operator owns
  that case.
- **The title, `wrong_versions` and every other frontmatter field** but
  `consumes`. The body and the claims are the reader's prose.
- **`DESIGN.md` §4.2.1 and `docs/agents/issue-tracker.md`.** Both are
  edited by hand with this spec. `CONTEXT.md` gets its **Removed name**
  entry by hand under backlog item b-f5ceaf.

## Notes for the agent

**Every criterion but the last is new code**, so each declares a witness
and no mutant, and `witness` will report `skip`. The last is
`preserves`, and its test exists at base.

**At base each new witness fails in its body.** `Spec` refuses the
unknown `removes` key. So every fixture spec that declares it is
refused as malformed. Each witness asserts candidates that are then
missing. No witness imports a name the change adds at module scope.

**Why the later id is held.** The scheduler already lets the lower id
through when two specs compete, in `_resolve_stack_base` and
`_stack_order` (see Context). The later id also needs no rule for a pair
where each removes a name the other reads. Neither "the reader" nor "the
remover" names one spec there.

**Why the `depends_on` kind.** The remedy is a `depends_on`, and the
reason says so. A new kind would change the count in §4.2.1, and
`DESIGN.md` is `protected`. `SA-0279` reused `protected_touch` for the
same reason. The site you add must be counted by
`tests/test_refusal_count.py`'s walk. So pass the kind as a `kind=`
keyword or as the first element of a returned tuple.

**The retired corpus test is the last criterion.**
`test_no_real_spec_is_refused_on_its_own_acceptance_criteria`
(`tests/test_scheduler.py:3620`) asserts every refusal but `SA-0063`'s
names `depends_on`. No retired spec declares `removes`, so it holds as
it is. Do not edit it.

**The fixtures.** `_write_spec` (`tests/test_scheduler.py:174`) writes
no `removes`, `consumes` or `acceptance`. Extend it or add a helper
beside it. A claim needs a `witness` line beneath it to parse. A reader
that declares `consumes` needs a `depends_on`. Give it a parent written
to the fixture's `done/`, so the default scan admits it. That parent
must not lead to the remover. Map each refusal back to its spec with
`load_spec`, as other tests in the file do. For the `MERGED` case, use
`_task_at` with the remover's `_sha`.

**The `prose` gate** counts each new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size.** A prototype measured 953 changed tokens with `size_gate`,
against the `feature` ceiling of 3000. It held the field, the refusal,
the count edit and the five witnesses, and the whole suite passed on it.
It did not hold the docstring paragraphs. `estimated_lines` is that
count over four, plus a margin for them.
