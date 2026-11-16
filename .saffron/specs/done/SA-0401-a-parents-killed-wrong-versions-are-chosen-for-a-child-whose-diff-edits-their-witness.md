---
id: SA-0401
title: "Nothing reads which killed wrong versions a parent recorded under a witness its child's diff edits"
type: feature
priority: 3
risk: elevated
estimated_lines: 294
estimate_measured: true
depends_on: [SA-0399]
consumes:
  - saffron/intake.py:RETIRED_DIRNAME
pending_symbols:
  - saffron/parent_versions.py::parent_version_pairs
touches:
  - saffron/parent_versions.py
  - tests/test_parent_versions.py
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
  - saffron/scheduler.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/gates/**
  - saffron/task.py
  - saffron/cli.py
  - tests/test_session.py
  - tests/test_intake.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 30
max_attempts: 3
max_turns: 150
acceptance:
  - claim: >-
      `parent_version_pairs` in the new `saffron/parent_versions.py` pairs
      each killed wrong version of each parent whose witness the diff
      edits. Its keywords are `depends_on`, `specs_dir`, `out_dir` and
      `diff`. A parent is a spec `depends_on` names, read from
      `specs_dir`'s retired directory or from `specs_dir` itself, taken in
      `depends_on` order. A name neither directory declares is left out,
      and a file in either that does not parse is skipped. A missing
      retired directory reads as empty, as `scheduler._retired_ids` reads
      it. A changed path is the path each `diff --git` block of `diff`
      names.
      `names_file(witness, path)` holds when the witness begins with the
      path and the next character, if any, is neither a letter, a digit
      nor one of `_`, `.`, `-` and `/`. A parent criterion is chosen when
      it declares wrong versions and `names_file` holds for its witness and
      some changed path. A parent's chosen criteria are read in declared
      order. Its record is
      `out_dir / <parent id> / wrong-versions.json`. Each entry whose
      `witness` equals the criterion's adds each of its versions whose
      `outcome` is `killed`, in recorded order. Each pair is that parent
      criterion and an entry holding `parent`, `witness`, `version`, the
      recorded `edit` and an empty `reason`. The function returns the pairs
      and an empty second list. The witness first asserts `names_file`
      true for a `::` suffix, a space suffix and the bare path. It asserts
      it false for a letter, a digit, `_`, `.`, `-` or `/` after the path,
      for another file, and for the path preceded by a directory. Its diff
      modifies tests/test_a.py, then src/a.py, then tests/test_c.py. It
      builds retired parents `SP-1` and `SP-2`, a retired non-parent
      `SP-4`, a queued parent `SP-3` and a queued non-parent `SP-5`. A
      `README.md` in the retired directory and a `broken.md` in the queue
      have no frontmatter. `depends_on` is `SP-3`, `SP-1`, `SP-7` and
      `SP-2`, and no file declares `SP-7`. `SP-1` declares four criteria,
      with witnesses on tests/test_a.py, tests/test_a.pyi,
      tests/test_b.py and tests/test_c.py, in that order. `SP-2`'s one
      witness is on tests/test_c.py. `SP-3`'s witness is the bare path
      tests/test_a.py. `SP-4` and `SP-5` each have one witness on
      tests/test_a.py. `SP-1`'s record holds killed, survived, unproven,
      error and killed versions under its first witness. It holds one
      killed version under each of its other three witnesses. It also
      holds one under `test_old` on tests/test_a.py, a witness no
      criterion declares. Every other record holds one killed version
      under its spec's witness. The witness asserts the exact pairs, each
      criterion's claim and witness included. `SP-1`'s pair from its
      fourth criterion comes after `k2`. It then builds a specs directory
      with no retired directory and the queued `SP-3`, and asserts
      `SP-3`'s one pair and an empty second list.
    witness: tests/test_parent_versions.py::test_a_childs_diff_pairs_each_killed_version_of_each_parent_whose_witness_it_edits
    wrong_versions:
      - Every spec in either directory read as a parent, so `SP-4` and `SP-5` are paired.
      - The queue never read, so `SP-3` is not paired.
      - The retired directory never read, so `SP-1` and `SP-2` are not paired.
      - Parents taken in file-name order rather than `depends_on` order, so `SP-3` comes last.
      - A name no file declares indexed directly, so `SP-7` raises `KeyError`.
      - Only the first `diff --git` block read, so `SP-2` and `SP-1`'s version on tests/test_c.py are not paired.
      - Only the last `diff --git` block read, so `SP-3` and `SP-1`'s versions on tests/test_a.py are not paired.
      - A missing retired directory handed to `discover_specs`, so the specs directory without one raises `SpecError`.
      - A witness matched as a plain prefix of the path, so the witness on tests/test_a.pyi is paired.
      - A witness matched only before a `::` separator, so `SP-3`'s witness, which is the whole path, is not paired.
      - A witness matched where the path occurs anywhere in it, so a path preceded by a directory names the file.
      - Every recorded version paired whatever its outcome, so the survived, unproven and error versions are paired.
      - Only the first killed version of each entry paired, so `k2` is missing.
      - Only the first chosen criterion of each parent read, so `SP-1`'s version on tests/test_c.py is not paired.
      - A recorded entry paired by its own witness with no criterion declaring it, so the version under `test_old` is paired.
      - Each retired file read with `load_spec`, so the `README.md` raises.
      - Each queued file read with `load_spec`, so `broken.md` raises.
  - claim: >-
      `parent_version_pairs` names a parent whose record cannot be read, in
      `depends_on` order, and pairs none of its versions. A record cannot
      be read when it is missing or is not JSON. It also cannot when it
      holds no list. Only an entry whose
      `witness` equals a chosen criterion's is read further. Such an entry
      makes the record unreadable when it lacks `versions`. It does so too
      when a version recorded `killed` holds an `edit` that is not an
      edit, null or a mapping `Mutant` refuses alike. A version recorded
      with another outcome is never validated. A parent with no chosen
      criterion is never named, even when its record is missing or broken.
      A parent after an unreadable one is still paired. The witness
      declares parents `SP-5` to `SP-13` and `SP-99`, in the
      `depends_on` order `SP-9`, `SP-5`, `SP-6`, `SP-7`, `SP-8`, `SP-13`,
      `SP-10`, `SP-11`, `SP-12`, `SP-99`. `SP-5` has no record. `SP-6`
      holds broken JSON, and `SP-7` a JSON object. `SP-8`'s entry lacks
      `versions`. `SP-9`'s killed version has a null edit. `SP-13`'s matching entry
      holds a valid killed version and then a killed one whose edit has
      no `find`. `SP-10`'s criterion names an unchanged file and
      has no record. `SP-11`'s criterion names the changed file, declares
      no wrong versions and has no record. `SP-12`'s criterion names an
      unchanged file, and its record is broken JSON. `SP-99`'s matching
      entry holds a killed version and an unproven one with a null edit.
      Its record also holds an entry under another witness that lacks
      `versions`, and one whose killed version has a null edit. The
      witness asserts the second list is exactly `SP-9`, `SP-5`, `SP-6`,
      `SP-7`, `SP-8` and `SP-13`, and the pairs are `SP-99`'s one version.
    witness: tests/test_parent_versions.py::test_a_parent_whose_record_cannot_be_read_is_named_and_pairs_nothing
    wrong_versions:
      - A missing record skipped without naming its parent, so `SP-5` is absent from the list.
      - Only `OSError` caught, so `SP-6`'s broken JSON raises out of the function.
      - A record that holds no list raising `TypeError` uncaught, so `SP-7` raises.
      - An entry lacking `versions` read as an empty list, so `SP-8` is not named.
      - A killed version with a null edit paired with a stand-in edit, so `SP-9` is paired.
      - Only a null edit counted unreadable, so `SP-13` is not named.
      - Pairs appended as each version validates, so `SP-13`'s valid version is paired.
      - The unread list sorted by name, so `SP-13` comes first.
      - Every entry read for `versions` whatever its witness, so `SP-99` is named.
      - Every entry's killed edits validated whatever its witness, so `SP-99` is named.
      - Every version's edit validated whatever its outcome, so `SP-99`'s unproven null edit makes it named.
      - An unreadable record ending the scan, so `SP-99`'s version is not paired.
      - The record read before any criterion is chosen, so `SP-10` and `SP-12` are named.
      - A criterion chosen whether or not it declares wrong versions, so `SP-11` is named.
---

## Context

Backlog item **b-9efbe2**, found by both review seats on #856. It
cites `DESIGN.md` §5.4 and §5.5, and §5.4.1 holds the wrong-version
paragraph this work extends. This spec is the first piece of a split.
It chooses which recorded versions to ask again. `SA-0402` makes REVIEW
ask them and file a survivor as a blocker. Every line number below was
read at `f0ffaad6`.

**What happened**. `SA-0270` declares `depends_on: [SA-0269]`
(`.saffron/specs/done/SA-0270-every-tasks-networks-take-the-same-fixed-subnets.md:6`).
Its cell had to edit `SA-0269`'s witness
`test_two_tasks_bring_up_and_tear_down_only_their_own_networks_and_proxy`,
and it deleted the seeding the test needed. `SA-0269`'s record
`~/.saffron/batches/v0/SA-0269/wrong-versions.json` holds six versions
under that witness. One is "A `cell_up` that pre-cleans every `saffron-`
holder on its subnets", recorded `killed`. After the child's edit that
version passed the witness, and no gate asked it again.

**Where a task's wrong versions are recorded**. `_drive_cell` sets
`task_dir = out_dir / spec.spec_id` (`saffron/cell/session.py:2352`).
REVIEW writes `wrong-versions.json` there as a JSON list
(`saffron/cell/session.py:3590-3594`). Each entry carries `witness`,
`claim` and `versions` (`saffron/phases/review.py:717-765`). Each version
holds `version`, `edit` and `reason`. The probe cell then writes its
`outcome` and `summary` (`saffron/cell/session.py:2210-2211`). A version
no session expressed keeps a null `edit`
(`saffron/phases/review.py:726-729`). `saffron cell` and `saffron batch`
default `out_dir` to the home's `batches/v0` (`saffron/cli.py:350-351`).
Nothing under `saffron/record/` names a wrong version
(`git grep wrong saffron/record` prints nothing). So the batch folder is
the one store the base can read.

**What this module reads with**. `discover_specs` parses every `*.md` in
one directory. It returns the files it could not parse apart and never
raises for one (`saffron/intake.py:557-601`). `discover_specs` does raise
for a directory that does not exist (`saffron/intake.py:580-581`).
`scheduler._retired_ids` reads a missing retired directory as empty
instead (`saffron/scheduler.py:652-654`). Its `retired=True` keeps a
retired spec as it shipped (`saffron/intake.py:560-561`). `Mutant` holds
`file`, `find`, `replace` and an optional `case` that `model_dump` leaves
out when it is `None` (`saffron/intake.py:96-147`). `intake.Spec` declares
`depends_on` (`saffron/intake.py:244`). The integrity gate's diff parser,
`_split_blocks` and `_parse_block`, splits a diff by its `diff --git`
headers (`saffron/gates/core/integrity.py:151`, `:170`). `revert` already
imports both (`saffron/gates/core/revert.py:26`).

**What the parent gives this spec**. `SA-0399` moves `RETIRED_DIRNAME`
to `saffron/intake.py`, and its first criterion makes that file the only
one under `saffron/` whose string literals spell the retired directory.
This spec `consumes` the name there.

## Problem

Add `saffron/parent_versions.py` with two public functions.

- `names_file(witness, path)`, the text comparison the first criterion
  states. It splits nothing and knows no test runner (§2.1).
- `parent_version_pairs(*, depends_on, specs_dir, out_dir, diff)`, which
  returns the pairs and the unread parents as the two criteria state.
  Read the parents with `discover_specs`, the retired directory with
  `retired=True`. Name that directory through `intake.RETIRED_DIRNAME` and
  never a string literal. Read changed paths with `_split_blocks` and
  `_parse_block`. Validate each killed `edit` with `Mutant.model_validate`
  and store its `model_dump()`. Return two empty lists when `depends_on`
  is empty, before any spec is read.

Nothing in `saffron/` calls `parent_version_pairs` yet, which is why it is
in `pending_symbols`. `SA-0402` calls it from REVIEW.

## Out of scope

- **REVIEW**. Asking the pairs in the gate-only cell, the survivor's
  blocker, `CellSpec.depends_on`, `parent-versions.json` and the REVIEW
  line are `SA-0402`'s.
- **A review commit**. #1202 rewrote `SA-0389`'s clause in a review
  commit, and no cell judged that commit. `saffron regate` is where a host
  could ask the same versions of a pull request's head. That is a later
  spec.
- **A retired spec that is no parent**. A child that edits a witness of a
  spec it does not depend on is not checked. Reading every retired spec
  would ask each child editing `tests/test_session.py` hundreds of
  versions.
- **A record of a later task**. The batch tree is keyed by spec, so a
  later task of the parent overwrites its record
  (`saffron/projection.py:14-17`). The newest record is the one read.
- **An added or deleted file**. The witnesses drive modified files only.
- **A retired file refused on policy**. `discover_specs` returns such a
  file among its failures, with its spec attached. This spec reads the
  parsed list only.
- **A diff `integrity` refuses**. `_split_blocks` raises on it, and the
  attempt has already ended before REVIEW. This module returns no changed
  path then, and no witness drives it.
- **Two chosen criteria sharing a witness**. Each reads the same entries, so their versions pair twice. No witness drives it.
- **A spec in both directories**. The retired copy is read. No witness drives it.
- **A name repeated in `depends_on`**. The parent is read once per mention. No witness drives it.
- **A `retired_first`**. This spec adds no refusal.
- **Hand edits**. None. The `DESIGN.md` and `CONTEXT.md` sentences belong
  to `SA-0402`, which adds the behaviour they describe.

## Notes for the agent

**The behaviour is new code**, so each criterion declares a witness and no
mutant, and `witness` will report `skip`.

**At base each witness fails in its body**. Import
`saffron.parent_versions` inside each test function, never at module
scope, so the reverted suite fails rather than erroring at collection.

**The witnesses** write each spec with frontmatter only: `id`, `title`,
`type` and an `acceptance` list. Each criterion declares one wrong
version, except `SP-11`'s, which declares none. Write each record with
`json.dumps`, except the broken ones. A recorded `edit` holds `file`,
`find` and `replace` only, which is what `model_dump()` returns. Build the
diff by hand, with one `diff --git` block each on `tests/test_a.py`,
`src/a.py` and `tests/test_c.py`, in that order.

**The `prose` gate** counts each new comment and docstring from zero.
Write none with an em dash, a semicolon, a contraction, the perfect tense
or a sentence over 25 words.

**Size**. A prototype measured 486 changed tokens outside `tests/` and 688
under it, about 294 changed lines.
