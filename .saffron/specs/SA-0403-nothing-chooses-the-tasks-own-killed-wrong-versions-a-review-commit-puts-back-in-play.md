---
id: SA-0403
title: "Nothing chooses which of a task's own killed wrong versions a review commit's diff puts back in play"
type: feature
priority: 3
risk: standard
estimated_lines: 283
estimate_measured: true
pending_symbols:
  - saffron/parent_versions.py::own_version_pairs
  - saffron/regate.py::review_commit_diff
touches:
  - saffron/parent_versions.py
  - saffron/regate.py
  - tests/test_parent_versions.py
  - tests/test_regate.py
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
  - saffron/ledger.py
  - saffron/commit_review.py
  - saffron/end_review.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/gates/**
  - saffron/repos/**
  - saffron/task.py
  - saffron/cli.py
  - tests/test_commit_review.py
  - tests/test_session.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 46
max_attempts: 3
max_turns: 200
acceptance:
  - claim: >-
      `own_version_pairs` in `saffron/parent_versions.py` pairs each of
      the task's own killed wrong versions under a witness the diff edits.
      Its keywords are `spec`, `out_dir` and `diff`, and it returns the
      pairs and a boolean. A changed path is the path each `diff --git`
      block of `diff` names. A criterion is chosen when it declares wrong
      versions and `names_file` holds for its witness and some changed
      path. Chosen criteria are read in declared order. The record is
      `out_dir / <spec id> / wrong-versions.json`. Each entry whose
      `witness` equals a chosen criterion's adds each of its versions
      whose `outcome` is `killed`, in recorded order. Each pair is that
      criterion and an entry holding `parent`, `witness`, `version`, the
      recorded `edit` and an empty `reason`, the shape
      `parent_version_pairs` returns. `parent` holds the spec's own id.
      The boolean is false. The witness parses spec `SP-1` with five
      criteria. Their witnesses are the distinct node ids
      tests/test_a.py::test_one, tests/test_a.pyi::test_two,
      tests/test_b.py::test_three, tests/test_c.py::test_four and
      tests/test_a.py::test_five. The first four declare one wrong version each, and the fifth declares
      none. Its diff modifies tests/test_a.py, then src/a.py, then
      tests/test_c.py. The record holds killed `k1`, a survived version
      and killed `k2` under the first witness. It holds one killed version
      under each of the other four witnesses, and one under `test_old` on
      tests/test_a.py, a witness no criterion declares. The fourth
      witness's entry comes first in the record. The witness asserts the
      exact pairs, `k1`, `k2`, then the fourth criterion's
      version, each with its criterion, and a false boolean.
    witness: tests/test_parent_versions.py::test_the_tasks_own_killed_versions_are_paired_for_each_witness_its_diff_edits
    wrong_versions:
      - A witness matched as a plain prefix of the path, so the version on tests/test_a.pyi is paired.
      - Every criterion that declares wrong versions chosen whatever the diff, so the version on tests/test_b.py is paired.
      - A criterion chosen whether or not it declares wrong versions, so the fifth criterion's version is paired.
      - Every recorded version paired whatever its outcome, so the survived version is paired.
      - Only the first killed version of each entry paired, so `k2` is missing.
      - Only the first `diff --git` block read, so the version on tests/test_c.py is missing.
      - Only the last `diff --git` block read, so `k1` and `k2` are missing.
      - The record read from `out_dir / wrong-versions.json`, so nothing is paired and the boolean is true.
      - Each recorded entry paired by its own witness with no criterion declaring it, so the version under `test_old` is paired.
      - The `parent` key left empty, so no pair equals the expected entry.
      - Pairs taken in recorded order rather than declared order, so the fourth criterion's version comes first.
  - claim: >-
      `own_version_pairs` returns no pair and a true boolean when the
      task's own record cannot be read. A record cannot be read when it is
      missing or is not JSON. It also cannot when it holds no list. Only
      an entry whose `witness` equals a chosen criterion's is read
      further. Such an entry makes the record unreadable when it lacks
      `versions`. It does so too when a version recorded `killed` holds an
      `edit` that `Mutant` refuses, null or a mapping with no `find`
      alike, even after a valid killed version. A version recorded with
      another outcome is never validated. A spec with no chosen criterion
      never reads its record and returns no pair and a false boolean. Each
      case is its own spec, with one criterion on tests/test_a.py. `SP-5`
      has no record. `SP-6` holds broken JSON, and `SP-7` a JSON object.
      `SP-8`'s matching entry lacks `versions`. `SP-9`'s killed version
      has a null edit. `SP-13`'s matching entry holds a valid killed
      version and then a killed one whose edit has no `find`. Each of
      these returns no pair and true. `SP-10` holds broken JSON, and its
      diff modifies src/a.py alone. `SP-11`'s criterion declares no wrong
      versions and has no record. `SP-12` holds broken JSON, and its diff
      is empty. Each of these returns no pair and false. `SP-99`'s
      matching entry holds a killed version and an unproven one with a
      null edit. Its record also holds an entry under another witness
      that lacks `versions`, and one whose killed version has a null
      edit. It returns its one killed version and false.
    witness: tests/test_parent_versions.py::test_the_tasks_own_record_that_cannot_be_read_is_reported_and_pairs_nothing
    wrong_versions:
      - A missing record read as an empty one, so `SP-5` returns false.
      - Only `OSError` caught, so `SP-6`'s broken JSON raises.
      - A record holding no list iterated as found, so `SP-7` returns false.
      - An entry lacking `versions` read as an empty list, so `SP-8` returns false.
      - A killed version with a refused edit skipped, so `SP-9` returns false.
      - Pairs kept as each version validates, so `SP-13` returns its valid version.
      - The record read before any criterion is chosen, so `SP-10` and `SP-12` return true.
      - A criterion chosen whether or not it declares wrong versions, so `SP-11` returns true.
      - Every entry read for `versions` whatever its witness, so `SP-99` returns true.
      - Every version's edit validated whatever its outcome, so `SP-99` returns true.
      - The boolean never set, so `SP-5` returns false.
  - claim: >-
      `review_commit_diff(mirror, pushed_sha, baseline_sha, head)` in
      `saffron/regate.py` returns the diff `head`'s review commits make.
      When `pushed_sha` is an ancestor of `head` and is not `head`, the
      range starts at `pushed_sha`. The paths kept are those that
      `pushed_sha..head` and `baseline_sha..head` both change, each read
      with `DIFF_FLAGS`, so a rename counts as both of its paths. The
      result is `git diff` over that range with `DIFF_FLAGS`, limited to
      those paths in sorted order. A head whose only commit past
      `pushed_sha` merges the base branch returns empty. The witness
      builds a checkout that stands for the mirror, with `main` as the
      base branch. Its packaged commit edits src/p.py, src/q.py and
      tests/test_w.py. `main` then edits main.txt. A review commit edits
      tests/test_w.py again, sets src/q.py back to its base text, and
      renames tests/test_old.py to tests/test_new.py. A merge of `main`
      follows, as GitHub's update branch makes. `baseline_sha` is
      `main`'s head. The witness asserts the returned diff's paths are
      exactly tests/test_new.py, tests/test_old.py and tests/test_w.py. It asserts the text equals the test's own
      `DIFF_FLAGS` diff of `pushed_sha..head` over those three paths. A
      second head merges `main` straight onto the packaged commit, and
      returns empty.
    witness: tests/test_regate.py::test_review_commit_diff_keeps_the_review_commits_paths_the_task_also_changed
    wrong_versions:
      - The review commits' paths kept whether or not `baseline_sha..head` changes them, so main.txt is in the diff.
      - The diff read from `baseline_sha` rather than from `pushed_sha`, so tests/test_w.py's hunk starts at the base text.
      - The range started at `pushed_sha`'s parent, so src/p.py is in the diff.
      - The paths read without `--no-renames`, so tests/test_old.py is missing.
      - The final diff read without `DIFF_FLAGS`, so the rename shows as one block.
      - An empty shared path list passed to `git diff` as no path at all, so the merge-only head returns main.txt.
      - The paths read from each first-parent commit past the start that is not a merge, with `baseline_sha` never read, so src/q.py is in the diff.
  - claim: >-
      `review_commit_diff` starts a restacked branch's range at the
      packaged commit's rebased copy, as `commit_review._rebased_copy`
      finds it, when `pushed_sha` is no ancestor of `head`. The kept
      paths and the text follow the rule of the criterion above. The
      witness rebases the packaged commit onto the moved `main`
      and adds a review commit that edits tests/test_w.py. The original
      packaged commit stays reachable from another branch, so the
      checkout still holds it. The witness asserts the returned diff's
      paths are exactly tests/test_w.py. It asserts the text equals the
      test's own `DIFF_FLAGS` diff of the copy to that head over that one
      path.
    witness: tests/test_regate.py::test_review_commit_diff_starts_a_restacked_branch_at_the_packaged_commits_copy
    wrong_versions:
      - No rebased copy sought, so the restacked head returns empty.
      - The range started at the merge base of `pushed_sha` and `head`, so src/p.py is in the diff.
      - The range started at the copy's parent, so src/p.py is in the diff.
      - The diff read from `baseline_sha` rather than from the copy, so tests/test_w.py's hunk starts at the base text.
  - claim: >-
      `review_commit_diff` returns an empty string when `head` is the
      packaged commit or its rebased copy. The witness first asserts that
      the first criterion's head returns a non-empty diff on the same
      checkout. It then asserts empty for `head` equal to `pushed_sha`,
      and for `head` equal to the rebased copy.
    witness: tests/test_regate.py::test_review_commit_diff_is_empty_for_a_head_that_is_the_packaged_commit
    wrong_versions:
      - A head equal to the range's start read from `baseline_sha` instead, so src/p.py and tests/test_w.py are returned.
  - claim: >-
      `review_commit_diff` returns an empty string, and raises nothing,
      when the mirror holds no packaged commit `head` carries. That is a
      `pushed_sha` that is `None`, empty, forty zeros, or a commit the
      mirror holds that is neither an ancestor of `head` nor copied onto
      its first-parent chain. The witness first asserts that the first
      criterion's head returns a non-empty diff on the same checkout. It
      then asserts empty for each of the four.
    witness: tests/test_regate.py::test_review_commit_diff_is_empty_when_no_packaged_commit_is_on_head
    wrong_versions:
      - A `pushed_sha` handed to `git merge-base --is-ancestor` before the mirror is asked whether it holds the commit, so forty zeros raises `GitError`.
      - A commit with no copy read from `baseline_sha` instead, so the stray commit returns a diff.
      - A commit with no copy started at its merge base with `head`, so the stray commit returns a diff.
---

## Context

Backlog item **b-d9a027**, left by b-9efbe2. It cites `DESIGN.md` §5.4
and §5.5, and §5.4.1 holds the wrong-version paragraph `SA-0401` and
`SA-0402` extended. REVIEW never reads a review commit, so nothing asks it
the wrong versions REVIEW once killed. In the spec loop's 70th pass a
review commit on #1202 rewrote `SA-0389`'s clause. The spec's own wrong
version 8 then passed the witness. This spec is the first of two. It
chooses which recorded versions a review commit puts back in play.
`SA-0404` asks them from `saffron regate`. Every line number below was
read at `d72d0733`.

**What `parent_versions.py` already does**. `_changed_paths` reads the
path of each `diff --git` block and returns none for a diff `integrity`
refuses (`saffron/parent_versions.py:36`). `_chosen_criteria` picks the
criteria that declare wrong versions and whose witness names a changed
path (`saffron/parent_versions.py:45`). `_load_record` reads `out_dir / <id> / wrong-versions.json`
and raises `_Unreadable` for a missing file, broken JSON or a non-list
(`saffron/parent_versions.py:72`). `_parent_pairs` builds each pair and raises `_Unreadable` on a
bad matching entry (`saffron/parent_versions.py:86`). Its entry's `parent` key holds the id it is
given (`saffron/parent_versions.py:113`). `parent_version_pairs` composes them for each
`depends_on` parent (`saffron/parent_versions.py:124`). REVIEW writes the task's own record at
`task_dir / "wrong-versions.json"` (`saffron/cell/session.py:3622`), and
`task_dir` is `out_dir / spec.spec_id` (`saffron/cell/session.py:2372`).
`run_regate` reads the same task directory for `revert-exempt.json`
(`saffron/regate.py:169`).

**Which spec the task ran**. `run_regate` parses the task's latest
recorded spec text when the ledger holds one, and reads the file at
`base_sha` otherwise (`saffron/regate.py:151-156`). The two can differ, so
the new function takes that `Spec` rather than a spec directory.

**What `regate.py` reads of the range**. `run_regate` fetches the task's
branch as `head` and sets `baseline_sha` to the merge base of the
pull request's base branch and `head` (`saffron/regate.py:144-146`).
The base branch is the `baseRefName` `gh pr view` reports
(`saffron/regate.py:62-66`), a parent's branch for a stacked task.
`_TASK_ROW` selects no `pushed_sha` (`saffron/regate.py:24-29`). In the tests,
`_seed_task` stores forty zeros when no `pushed_sha` is given
(`tests/test_regate.py:235`).

**What already finds a range's start**. `commit_review._range_start`
starts at `pushed_sha` when it is an ancestor of `head`, and at its
rebased copy otherwise (`saffron/commit_review.py:106`). It declines
rather than returning empty, so it does not fit here.
`commit_review._rebased_copy` returns the newest commit on `head`'s
first-parent chain whose full message equals `pushed_sha`'s, or `None`
(`saffron/commit_review.py:93`). It reads `pushed_sha`'s message through
`_git`, which raises on any non-zero exit
(`saffron/repos/mirror.py:64-67`). `end_review._is_ancestor` raises
`GitError` on any exit but 0 and 1 (`saffron/end_review.py:155-166`).
On git 2.54 on the host, `git merge-base --is-ancestor` with forty zeros
exited 128 (measured). `mirror.has_commit` answers whether the mirror
holds a commit and returns false rather than raising
(`saffron/repos/mirror.py:357-366`).
`DIFF_FLAGS` carries `--no-renames` (`saffron/cell/worktree.py:207`).

**Why the import waits until the call**. `commit_review` imports
`saffron.regate` at module scope (`saffron/commit_review.py:35`). A
module-scope import of `commit_review` in `regate.py` would cycle.
`saffron/commit_review.py` is not in `touches`, so moving
`_rebased_copy` cannot land here. `_drive_cell` already imports inside
its body (`saffron/cell/session.py:2337`), and no rule under
`.saffron/rules/` forbids it.

## Problem

Add two functions. Nothing in `saffron/` calls either yet, which is why
both are in `pending_symbols`. `SA-0404` calls them from `run_regate`.

- `own_version_pairs(*, spec, out_dir, diff)` in
  `saffron/parent_versions.py`. Compose `_changed_paths`,
  `_chosen_criteria`, `_load_record` and `_parent_pairs`, passing
  `spec.id` as the id. Return no pair and false before reading the
  record when no criterion is chosen. Catch `_Unreadable` and return no
  pair and true.
- `review_commit_diff(mirror, pushed_sha, baseline_sha, head)` in
  `saffron/regate.py`. Find the range's start as the criteria state. Ask
  `git_mirror.has_commit` before any ancestry call. Test ancestry with
  `end_review._is_ancestor`, which raises on exit 128. Importing
  `end_review` at module scope does not cycle. Import `_rebased_copy`
  inside the function body, for the reason the context gives. Its
  arguments run `(mirror, head, pushed_sha)`, the reverse of this
  function's order. Read each side's changed paths with `DIFF_FLAGS` and
  `--name-only -z`. Return empty before `git diff` when no path is
  shared. Otherwise pass the shared paths after `--`.
  `--literal-pathspecs` is a global git option and goes before `diff`,
  as in `_git(mirror, "--literal-pathspecs", "diff", *DIFF_FLAGS, ...)`.
  `_git` puts `git -C <repo>` in front (`saffron/repos/mirror.py:64-65`).
  On the host's git 2.54, `git --literal-pathspecs diff` exited 0 and
  `git diff --literal-pathspecs` exited 129 (measured).
- `parent_versions.py`'s module docstring speaks only of a child's diff.
  Add one sentence saying a task's own review commit puts its own killed
  versions back in play too.

Keeping only the paths `baseline_sha..head` also changes is what keeps a
merge from the base branch out. That merge's files are in the review
range, and not in the task's own diff against the baseline.

## Out of scope

- **Wiring into `run_regate`**. `SA-0404` adds `pushed_sha` to
  `_TASK_ROW`, asks the chosen versions and fails the re-gate on a
  survivor. This spec changes no line of `run_regate` and no output of
  `saffron regate`.
- **Parents' versions**. `SA-0404` feeds the same diff to
  `parent_version_pairs`.
- **A withdrawn parent survivor in REBUT**. b-d9a027's second gap is a
  separate spec.
- **A file both the packaged commit and the base branch edit**. A
  merge from the base branch changes it in the review range. The task
  changed it against the baseline too. So its witness is chosen though no
  review commit touched it. It over-asks, and no witness drives it.
- **A witness file a review commit sets back to its baseline text**.
  `baseline_sha..head` no longer changes it, so its witness is not
  chosen. The test then reads the file the baseline holds. The witness
  drives this as src/q.py's absence.
- **A path with pathspec magic**. `--literal-pathspecs` reads each path
  as written. No witness drives a path holding `*` or `:`.
- **A `retired_first`**. This spec adds no refusal of a spec.
- **Hand edits**. None. The `DESIGN.md` and `CONTEXT.md` sentences belong
  to `SA-0404`, which adds the behaviour they describe.

## Notes for the agent

**The behaviour is new code**, so each criterion declares a witness and no
mutant, and `witness` will report `skip`.

**At base each witness fails in its body**. Import each new name inside
each test function, never at module scope, so the reverted suite fails
rather than erroring at collection.

**The `parent_versions` witnesses** reuse the module's `_spec_text`,
`_killed` and `DIFF` helpers, and build each `Spec` with
`intake.parse_spec`. Write each record with `json.dumps`, except the
broken ones.

**The `regate` witnesses** share one builder. It initialises a plain
checkout with a `main` branch, which `review_commit_diff` reads as its
mirror. No bare origin, no ledger and no `gh` fake is needed. Give the
packaged commit a message no other commit repeats. Keep a branch on the
original packaged commit after the rebase, as
`tests/test_commit_review.py:510` does, or the restacked case turns into
the absent one. Make the renamed file long enough for git to read the
pair as a rename. The module docstring says every witness drives a bare
origin and a checkout, so add one sentence naming the checkout-only
builder.

**The `prose` gate** counts each new comment and docstring from zero.
Write none with an em dash, a semicolon, a contraction, the perfect tense
or a sentence over 25 words.

**Git's own behaviour**. Each git fact these criteria rest on was seen
on the host's git 2.54 alone. That covers rename pairing without
`--no-renames`, an empty pathspec printing the whole diff, and
the placement of `--literal-pathspecs`. The cell image carries git
2.39.5, and none of these facts was measured there. The witnesses
settle them in the cell.

**Size**. A prototype measured 302 changed tokens outside `tests/` and
828 under it, about 283 changed lines.
