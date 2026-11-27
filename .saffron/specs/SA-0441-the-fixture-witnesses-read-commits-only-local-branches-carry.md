---
id: SA-0441
title: "The lens fixtures' witnesses read commits that only local branches carry, so a repo without those branches fails four of them at base and at head"
type: test
priority: 3
estimated_lines: 798
estimate_measured: true
touches:
  - docs/evidence/fixtures/heads.bundle.b64
  - docs/evidence/fixtures/README.md
  - tests/test_corpus.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - .github/**
  - ontology/**
  - tests/ontology/**
  - images/**
  - records/**
  - hooks/**
  - docs/backlog/**
  - docs/evidence/fixtures/SA-*/**
  - docs/evidence/passes/**
  - docs/evidence/scripts/**
  - harness/**
  - saffron/**
  - tests/test_lens_scoring.py
  - tests/test_cli.py
  - tests/test_adopt_stack_layer.py
  - tests/test_ledger_fold_task.py
  - tests/test_witness_gate.py
  - tests/test_suite.py
  - tests/test_session.py
  - tests/test_parent_versions.py
  - tests/test_regate.py
  - tests/test_report.py
  - tests/test_record_refs.py
  - tests/test_record_routed.py
  - tests/test_record_migrate.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 60
max_attempts: 3
max_turns: 185
acceptance:
  - claim: >-
      `docs/evidence/fixtures/heads.bundle.b64` is a git bundle, base64 in
      76-character lines, with a last line of 1 to 76 characters. Every
      line holds base64 characters alone. For every `base_sha` and every `head_sha` a shipped
      fixture declares, either HEAD's history holds the commit or the bundle
      lists a ref pointing at it, named by that sha in the fixtures
      namespace the Problem gives.
    witness: tests/test_corpus.py::test_the_tracked_bundle_names_every_fixture_commit_head_lacks
    wrong_versions:
      - "The bundle omits `SA-0050`'s `base_sha`."
      - "The bundle omits `SA-0054`'s `head_sha`."
      - "The bundle carries each fixture's `head_sha` and no `base_sha`."
      - "The bundle names the four `fixtures/SA-00NN` branch tips by their branch names."
      - "The ref named for `SA-0050`'s `base_sha` points at `SA-0054`'s `head_sha`."
      - "The bundle is base64 on one unbroken line."
      - "The bundle is base64 in 64-character lines."
      - "The file ends with an empty line after the base64."
      - "The file ends with a line of three spaces after the base64."
      - "One full-width line near the end holds `-` in place of one base64 character."
    covers:
      - set: the commits a fixture declares
        members:
          - member: a `base_sha`
            driven_by: "The bundle omits `SA-0050`'s `base_sha`."
          - member: a `head_sha`
            driven_by: "The bundle omits `SA-0054`'s `head_sha`."
      - set: the name a bundled commit carries
        members:
          - member: the sha, in the fixtures namespace
            driven_by: "The bundle names the four `fixtures/SA-00NN` branch tips by their branch names."
      - set: what a bundled ref says
        members:
          - member: its name
            driven_by: "The bundle names the four `fixtures/SA-00NN` branch tips by their branch names."
          - member: the commit it points at
            driven_by: "The ref named for `SA-0050`'s `base_sha` points at `SA-0054`'s `head_sha`."
      - set: the encoding's line widths
        members:
          - member: one unbroken line
            driven_by: "The bundle is base64 on one unbroken line."
          - member: a width under 76
            driven_by: "The bundle is base64 in 64-character lines."
          - member: an empty last line
            driven_by: "The file ends with an empty line after the base64."
          - member: a blank last line
            driven_by: "The file ends with a line of three spaces after the base64."
      - set: the characters a line holds
        members:
          - member: a non-alphabet character on a full-width line
            driven_by: "One full-width line near the end holds `-` in place of one base64 character."
  - claim: >-
      `repo_from_head_and_bundle(source, bundle, into)` in
      `tests/test_corpus.py` builds a bare repo holding the history
      `source`'s HEAD reaches. Handed a `bundle` path, it also holds the
      commits that base64 bundle carries. It holds no other commit of
      `source`, whether another ref reaches it or no ref does. The four
      fixture witnesses read git only through a repo they are handed.
      Handed the helper's repo built from this repo and the tracked bundle,
      each passes with `REPO` and the working directory pointed at a path
      that is no repo. Handed the one built from HEAD alone, each fails.
      The hostile-config witness also asserts that its bare diff starts
      `diff --git`. Handed the HEAD-only repo with `recovery.pinned_diff`
      patched to return `SA-0045`'s frozen patch, it still fails, at that
      bare diff.
    witness: tests/test_corpus.py::test_each_fixture_witness_reads_the_repo_it_is_handed
    positive_case: >-
      On a scratch repo, the same `cat-file -e` probe that finds no
      side-branch commit finds the HEAD commit, and the bundled commit when
      handed the bundle. Each fixture witness is called on the bundle's repo
      first and passes there, under the same `REPO` and working directory.
      So its failure on the HEAD-only repo is the missing commits and never
      a broken call.
    wrong_versions:
      - "The new repo's alternates point at `source`'s object store."
      - "The helper fetches `+refs/*:refs/*` from `source` rather than HEAD alone."
      - "The helper ignores the `bundle` it is handed."
      - "The range witness skips a fixture whose `head_sha` its repo lacks."
      - "The range witness still hands `REPO` to `pinned_diff`."
      - "The hostile-config witness still hands `REPO` to `pinned_diff`."
      - "The hostile-config witness's bare diff still reads `REPO`."
      - "The hostile-config witness drops the `diff --git` assertion and its bare diff still reads `REPO`."
      - "The spec-body witness still hands `REPO` to `spec_body_at`."
      - "The spec-body witness reads `CONTEXT.md` with a `git show` that names no repo."
      - "The spec-body witness reads `CLAUDE.md` with a `git show` that names no repo."
      - "The head-gate witness reads `policy.yaml` with a `git show` that names no repo."
      - "The module's bundle repo is built with no bundle."
    covers:
      - set: the forms of the `bundle` argument
        members:
          - member: "`None`"
            driven_by: "The helper fetches `+refs/*:refs/*` from `source` rather than HEAD alone."
          - member: a path to a base64 bundle
            driven_by: "The helper ignores the `bundle` it is handed."
      - set: where a commit of `source` sits
        members:
          - member: on HEAD's history
            driven_by: tests/test_corpus.py::test_each_fixture_witness_reads_the_repo_it_is_handed
          - member: on another branch only
            driven_by: "The helper fetches `+refs/*:refs/*` from `source` rather than HEAD alone."
          - member: in `source`'s object store under no ref
            driven_by: "The new repo's alternates point at `source`'s object store."
      - set: the four fixture witnesses
        members:
          - member: "`test_every_shipped_fixture_reproduces_its_own_declared_range`"
            driven_by: "The range witness still hands `REPO` to `pinned_diff`."
          - member: "`test_pinned_diff_survives_a_hostile_git_config`"
            driven_by: "The hostile-config witness's bare diff still reads `REPO`."
          - member: "`test_every_shipped_fixture_s_spec_body_and_context_reproduce_from_git`"
            driven_by: "The spec-body witness still hands `REPO` to `spec_body_at`."
          - member: "`test_every_shipped_fixture_s_head_declares_a_tests_gate`"
            driven_by: "The head-gate witness reads `policy.yaml` with a `git show` that names no repo."
      - set: the git reads in those witnesses
        members:
          - member: "`pinned_diff`"
            driven_by: "The hostile-config witness still hands `REPO` to `pinned_diff`."
          - member: the bare `git diff`
            driven_by: "The hostile-config witness's bare diff still reads `REPO`."
          - member: the bare diff's `diff --git` check
            driven_by: "The hostile-config witness drops the `diff --git` assertion and its bare diff still reads `REPO`."
          - member: "`spec_body_at`"
            driven_by: "The spec-body witness still hands `REPO` to `spec_body_at`."
          - member: "`git show` of `CONTEXT.md`"
            driven_by: "The spec-body witness reads `CONTEXT.md` with a `git show` that names no repo."
          - member: "`git show` of `CLAUDE.md`"
            driven_by: "The spec-body witness reads `CLAUDE.md` with a `git show` that names no repo."
          - member: "`git show` of `.saffron/policy.yaml`"
            driven_by: "The head-gate witness reads `policy.yaml` with a `git show` that names no repo."
      - set: the repos each witness is handed
        members:
          - member: HEAD's history and the tracked bundle
            driven_by: "The module's bundle repo is built with no bundle."
          - member: HEAD's history alone
            driven_by: "The range witness skips a fixture whose `head_sha` its repo lacks."
---

## Context

Backlog item **b-055fa3**, tier 2. It cites no section. The lens corpus is
`harness/`'s, and §2.1 keeps repo knowledge out of `saffron/`. Every line
below was read at `254f0a14`.

**What the four witnesses read.** `tests/test_corpus.py` sets `REPO` to
the repo root (`tests/test_corpus.py:27`). Four tests read a fixture's
commits from it:

- `test_every_shipped_fixture_reproduces_its_own_declared_range` calls
  `recovery.pinned_diff(REPO, ...)` (`tests/test_corpus.py:232-244`).
- `test_pinned_diff_survives_a_hostile_git_config` does the same for
  `SA-0045`. Its bare diff runs `git -C REPO diff` and asserts only that
  the output differs from the frozen patch (`tests/test_corpus.py:275-283`).
- `test_every_shipped_fixture_s_spec_body_and_context_reproduce_from_git`
  calls `recovery.spec_body_at(REPO, ...)`. It then reads `CONTEXT.md` and
  `CLAUDE.md` with a `git show` that names no repo, so git reads the
  working directory's repo (`tests/test_corpus.py:347-366`).
- `test_every_shipped_fixture_s_head_declares_a_tests_gate` reads each
  `head_sha`'s `.saffron/policy.yaml` the same way
  (`tests/test_corpus.py:1061-1075`).

**Where the commits live.** Eight fixtures declare 15 distinct shas. Eight
of them are on no branch of `origin`. Five fixtures were squash-merged, so
nothing on `main` reaches their branch commits
(`docs/evidence/fixtures/README.md:13-17`). Those commits live on GitHub's
`refs/fixtures/*` (`docs/evidence/fixtures/README.md:19-24`). CI fetches
those refs by hand (`.github/workflows/ci.yml:16`). A plain fetch of
`origin` takes none of them.

**How a cell sees them.** The mirror copies every ref of the host's repo
(`saffron/repos/mirror.py:83`). The cell's seed fetches only
`+refs/heads/*` from the mirror (`saffron/cell/worktree.py:79`), then
removes the remote (`saffron/cell/worktree.py:84`). So a fixture commit
reaches `/work` only when a local branch on the host reaches it. Today
four local branches do: `fixtures/SA-0045`, `fixtures/SA-0048`,
`fixtures/SA-0050` and `fixtures/SA-0054`. The item's record says why
they exist. Without such branches, the cells of `SA-0276` and `SA-0294`
each failed four `tests/test_corpus.py` witnesses at baseline.

**Measured on the host.** Git 2.54, on 2026-11-27. Take a bare mirror of
the host's repo, and seed a copy from it the way `_seed_script` seeds `/work`.
That copy passes all 57 tests in `tests/test_corpus.py`. The same mirror with the four
`fixtures/*` branches deleted fails exactly these four. No other test
that reads a fixture or calls `pinned_diff` or `spec_body_at` fails
there.

## Problem

Whether these four witnesses pass depends on which local branches the
host keeps. Delete the four and every cell's baseline fails them. Make the
repo carry the commits, and make the witnesses read only what HEAD's
history and that file hold.

1. **The bundle.** Add `docs/evidence/fixtures/heads.bundle.b64`. It is
   a git bundle, base64-encoded in 76-character lines, as
   `base64.encodebytes` writes it. For each fixture sha that is no
   ancestor of HEAD, it lists one ref, `refs/fixtures/<sha>`, pointing at
   that commit. Its prerequisites are commits HEAD reaches. The Notes say
   how to build it.
2. **The helper.** Add `repo_from_head_and_bundle(source, bundle, into)`
   at module level in `tests/test_corpus.py`. It makes a bare
   repo at `into` and fetches `source`'s HEAD into it, and nothing else of
   `source`. Handed a `bundle` path, it decodes the file and fetches every
   ref the bundle lists into the new repo. It returns `into`. A failed git
   command raises.
3. **The witnesses.** In `tests/test_corpus.py`, add a module-scoped
   fixture `fixture_repo` that builds the helper's repo from `REPO` and
   the bundle. Add a second module-scoped fixture `head_only_repo`, built
   with no bundle. Each of the four witnesses takes `fixture_repo` as an
   argument. Every git read in them, the `git show` calls included, names
   that repo. The hostile-config witness also asserts that its bare diff
   starts `diff --git`. Today that diff is empty on a repo missing the
   commits, and the inequality still passes.
4. **The README.** Add one paragraph to
   `docs/evidence/fixtures/README.md`. It says the bundle carries the same
   commits and the tests read only HEAD's history and the bundle. It says
   a new fixture whose commits HEAD lacks needs the bundle rebuilt. It also
   replaces the claim that a shallow checkout plus CI's fetch is enough
   (`docs/evidence/fixtures/README.md:27-28`). The tests now need HEAD's
   history back to the bundle's prerequisite. It rewrites the title line
   (`docs/evidence/fixtures/README.md:1`) and the paragraph at
   `docs/evidence/fixtures/README.md:24-27`. Both say `refs/fixtures/*`
   alone keeps the commits alive. They now name the bundle beside the refs.

## Out of scope

- The cell's seed refspec (`saffron/cell/worktree.py:79`) and the mirror.
  A seed that also fetched `refs/fixtures/*` would still lean on refs a
  plain fetch of `origin` lacks. `.saffron/policy.yaml` is protected
  (`.saffron/policy.yaml:66`).
- CI's fetch of `refs/fixtures/*` (`.github/workflows/ci.yml:16`). It is
  harmless once the tests read the bundle. Removing it is a later edit.
  Its comment goes stale with this change and stays as it is here, since
  `.github/**` is forbidden. It says "`refs/fixtures/*` is what keeps them
  alive; deleting one makes that fixture unverifiable"
  (`.github/workflows/ci.yml:14-15`). The later edit that removes the fetch
  rewords it.
- `refs/fixtures/*` on GitHub and the four local `fixtures/*` branches.
  They stay. The scoring driver still needs a fixture head inside its own
  cell (backlog item b-9529e9).
- `docs/evidence/fixtures-standards/`. No test reads its commits.
- Every other test in `tests/test_corpus.py`.

## Notes for the agent

**Edit or new.** The helper and the two new tests are new code, and the
four witnesses change only the repo they read. No `find` written now pins
your spelling, so no mutant is on the ref, and `witness` reports `skip`
for each claim.

**Building the bundle in `/work`.** The eight commits are in `/work`'s
object store under no ref, since the seed removes `origin` after its
fetch. `git cat-file -e <sha>^{commit}` finds each one (measured on a
seeded copy). Build the bundle from a scratch bare repo outside `/work`:
point its `objects/info/alternates` at `/work/.git/objects`, run
`git update-ref refs/fixtures/<sha> <sha>` for each sha that is no
ancestor of HEAD, then `git bundle create <file> --all ^HEAD` with `HEAD`
spelled as `/work`'s HEAD sha. Read the shas from each `fixture.toml`,
never from a branch name. The prototype's bundle was 44,433 bytes. Once
encoded it was 60,024 bytes in 780 lines, with one prerequisite, `2e563cf0`, which `main`
reaches. The task needs every one of the eight in `/work`. A sha that
`cat-file` misses is not in `/work`, and no edit here can bring it in.

**Size.** The `size` gate counts each whitespace-separated token, and
`tests/**` is not counted. The prototype priced at 871 tokens: 780 for
the bundle and the rest for the README. A `test` spec's ceiling is 4200.
Any other line width moves the bundle's count, so keep 76. Write LF line
endings, as `base64.encodebytes` does. A CRLF file would still pass the
first witness, since `splitlines` drops the `\r`. The prototype
changed 798 lines outside `tests/` and 197 in `tests/test_corpus.py`. At
the plan checkpoint, declare `estimated_test_lines` for the `tests/`
share. The checkpoint prices the other lines at 4 tokens each, which is
about 3200 here and under 4200.

**Fetching HEAD.** `git -C <into> fetch --no-tags <source> +HEAD:refs/heads/head`
copies only what HEAD reaches. Alternates or `+refs/*:refs/*` would let
every local ref back in, and the second claim's witness rejects both.
The prototype's module fixture took about one second to build on the host.
The git commands here were measured with the host's git 2.54. The
prototype's two witnesses also pass inside `saffron/cell:saffron`, with
its git 2.47.3 from Debian trixie. That worktree was seeded with the four
`fixtures/*` branches deleted. At your base, the same image fails the four
fixture witnesses there.

**`spec_body_at`'s fallback.** `_spec_content_off_branch` runs
`git log --all` (`harness/recovery.py:194`). In the helper's repo, `--all`
is the one HEAD ref and the bundle's refs. The prototype's
`spec_body.md` reproductions all matched there. Leave that function
alone.

**Why the helper sits in the test module.** The `dead` gate scans
`harness/` and never `tests/`. So a `harness/` function that only a
test calls fails it (`.saffron/gates/dead.py:4-6`). A separate test of the
helper alone would pass with the bundle reverted, and `revert` blocks
that. So the second claim's witness probes the helper and the four
witnesses together, and it fails when the bundle is gone.

**The second claim's witness.** Start with the helper. Build a small repo
in `tmp_path`. Give it a commit on `main`, a commit on a side branch, and
a commit on a third branch. Bundle the third branch against `main` and
encode it with `base64.encodebytes`. Call the helper twice on that same
source, once with no bundle and once with it. Then call each witness
function directly, first with `fixture_repo`, then with `head_only_repo` inside `pytest.raises`.
Point the module's `REPO` at a missing path with `monkeypatch.setattr`
and `chdir` to `tmp_path` before either call. A read that still reaches
`REPO` or the working directory then fails the first call. The
hostile-config witness needs its own `tmp_path` and `monkeypatch`. Give
each call a fresh directory and a `pytest.MonkeyPatch.context()`, so the
fake `$HOME` does not leak into the next call. Keep that witness a plain
`def`. A parametrised witness collects under a bracketed name, and
`criteria` refuses that. Last, call the hostile-config witness on
`head_only_repo` once more, with `recovery.pinned_diff` patched to return
`SA-0045`'s frozen `diff.patch`. Its pinned check then passes, so only its
bare diff check can fail. Without this call, a witness can drop that
check and read `REPO`, and still pass. `REPO` points at no repo, and an
empty diff differs from the patch.

**No `retired_first`.** Nothing here adds or widens a refusal.
