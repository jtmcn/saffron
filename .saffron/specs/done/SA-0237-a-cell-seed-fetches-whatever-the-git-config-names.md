---
id: SA-0237
title: A cell's seed fetches whatever the git config names, so a ref outside the branches can reach the cell
type: bug
priority: 2
depends_on: [SA-0232]
estimated_lines: 99
estimate_measured: true
touches:
  - saffron/cell/worktree.py
  - saffron/phases/package.py
  - tests/test_worktree.py
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
  - saffron/cell/session.py
  - saffron/cell/runtime.py
  - saffron/cell/runtimes/**
  - saffron/record/**
  - saffron/repos/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/task.py
  - saffron/intake.py
  - saffron/ledger.py
  - saffron/cli.py
  - tests/test_package.py
  - tests/test_package_cell.py
  - tests/test_session.py
  - tests/test_record_refs.py
budget_usd: 20
max_attempts: 3
max_turns: 130
risk: elevated
acceptance:
  - claim: >-
      The seed `prepare_worktree` runs fetches the mirror's branches by an
      explicit refspec and takes no tags. So no ref outside `refs/heads/*`
      reaches the worktree under either of two git configs that widen a
      bare fetch. One sets `remote.origin.fetch` to
      `+refs/saffron/*:refs/saffron/*`, and the other sets
      `remote.origin.tagOpt` to `--tags`. The witness's mirror holds three
      such refs. They are refs/saffron/mutants on a commit holding one
      blob, refs/saffron/tasks/t-1 on a commit holding another, and an
      annotated tag on that second commit. The witness's base is a commit
      on a branch other than the default, saffron/parent, and the mirror's
      `main` stays at the root commit. Under each config the seed checks
      out that base, and the worktree holds its file. The worktree lists
      its own branch as its only ref, and holds neither commit and neither
      blob.
    witness: tests/test_worktree.py::test_a_seed_fetches_no_non_branch_ref_whatever_the_git_config_names
    wrong_versions:
      - The refspec named but tags still followed, so the tag on the record commit arrives under `tagOpt`.
      - Tags refused but no refspec named, so the configured `remote.origin.fetch` brings both `refs/saffron/*` refs.
      - The refspec written into the worktree's own config before a bare fetch, which the configured value then extends.
      - A refspec over every ref, `+refs/*:refs/remotes/origin/*`, so both `refs/saffron/*` refs arrive.
      - Every tag fetched with `--tags` beside the branch refspec, so the tag arrives under either config.
      - Only the default branch fetched, as `git fetch --no-tags origin HEAD`, so the base off `main` never arrives and the checkout fails.
      - Only `main` fetched, by the refspec +refs/heads/main:refs/remotes/origin/main, so the base off `main` never arrives and the checkout fails.
      - The fetch runs as GIT_CONFIG_COUNT=0, so the environment's config is dropped and a global gitconfig still widens the fetch.
      - The fetch unsets GIT_CONFIG_COUNT with env -u, with the same result.
  - claim: >-
      A worktree seeded at a stacked task's parent head still holds the
      parent's commits, and a patch exported against that head holds only
      the child's own commit.
    witness: tests/test_worktree.py::test_a_stacked_worktree_holds_the_parents_real_commits_and_only_the_childs_new_commit_is_exported
    preserves: true
---

## Context

Backlog item **80**, the first part of it a spec can land alone. It cites
`DESIGN.md` §5.4.1. The cell construction this edits is §5.1.

**The seed today.** `prepare_worktree` (`saffron/cell/worktree.py:41`)
seeds a cell's worktree in an ephemeral container. Its script initialises
a repository, adds the bind-mounted mirror as its remote, fetches, checks
out the base and removes the remote. At this spec's base the seed's
fetch step is a bare `git fetch -q origin` (`saffron/cell/worktree.py:94`).
Three call sites reach it. Two are in the cell's own module, at
`saffron/cell/session.py:1083` and `saffron/cell/session.py:1413`. The
third is PACKAGE's gate cell, at `saffron/phases/package.py:541`.

**What `SA-0232` changes first.** This cell runs on `SA-0232`'s head. Line
numbers in `saffron/cell/worktree.py` move there, so this spec names the
seed's steps by their role. `SA-0232` retries a seed whose fetch step
failed. It marks that step in the script, so a failed fetch exits with its
own code. It also clears the volume at the start of each seed. Its
witnesses count the seeds by the fetch step's text. Its prototype counts
the scripts holding `git fetch`, which the new spelling keeps. If the
landed tests match more of the old text, update them.
`tests/test_worktree.py` is in `touches`.

**What the mirror holds.** `ensure_mirror` fetches `+refs/*:refs/*`
(`saffron/repos/mirror.py:72`). So the mirror carries every ref its origin
has. That includes the record under `refs/saffron/tasks` and
`refs/saffron/values` (`saffron/record/refs.py:23-24`). Item 80's
chosen design adds `refs/saffron/mutants`, whose blobs a cell must never
hold.

**What a bare fetch takes.** With no refspec, git fetches what the
config names. `git remote add` writes `+refs/heads/*:refs/remotes/origin/*`,
and tags pointing into that history follow. The 2026-09-17 probe measured
that a cell then holds no record object
(`docs/evidence/2026-09-17-state-on-git-refs.md`). It measured only that
default.

## Problem

The default is whatever git config says, and config adds to it. Measured
on 2026-10-07 with the host's git 2.54, seeded with this script's own
commands against a mirror holding a non-branch ref:

| config | bare fetch | named refspec, `--no-tags` |
|---|---|---|
| `remote.origin.fetch=+refs/saffron/*:refs/saffron/*` | ref and blob arrive | absent |
| `remote.origin.tagOpt=--tags`, a tag on that commit | tag and blob arrive | absent |
| none | absent | absent |

A system or global gitconfig in an image, or `GIT_CONFIG_*` in the seed's
environment, is all it takes. The boundary then depends on a file the
host never reads.

Name what the seed fetches:

- **The fetch.** In the seed's fetch step, replace the bare fetch with one
  naming `+refs/heads/*:refs/remotes/origin/*` and passing `--no-tags`.
  Keep the rest of the script as it is. That includes `SA-0232`'s mark on
  the step, its volume clearing and its retry.
- **The comment.** `saffron/phases/package.py:143-147` says the seed uses
  the "default refspec". Reword it to say the seed fetches `refs/heads/*`
  by name. The reasoning in it still holds.

## Out of scope

- **Two forbidden sentences.** `saffron/task.py:227` and
  `tests/test_package.py:197` say the seed fetches the default refspec.
  They stay true, since the named refspec is the one `remote add` writes.
- **The image's git.** The measurements ran on host git 2.54. The cell
  image's git (2.47.3, measured for `SA-0232`) is unmeasured for this fetch.

- **The mutants ref.** Moving mutants out of spec frontmatter is item
  80's remaining work, parked for an operator decision. This spec
  closes the fetch path whatever that ref ends up holding.
- **Other config keys.** The witness drives `remote.origin.fetch` and
  `remote.origin.tagOpt`, the two measured to widen a bare fetch. Keys
  such as `url.<base>.insteadOf` are not driven.
- **The evidence probes.** `docs/evidence/scripts/2026-09-17-*.sh` copy
  the old seed. They record what was measured then, so they stay.

## Notes for the agent

**Why every base still arrives.** A cell is seeded at the run's pin, a
stacked parent's head, or a packaged head. The first two land in the
mirror under a branch ref (`saffron/phases/package.py:149` and
`saffron/phases/package.py:189`).
The bare fetch reaches a commit only through a branch today, since a
followed tag points into history already fetched. So a branch refspec
reaches every base the bare fetch did. It must take every branch, not the
default one alone. A stacked parent sits on its own branch, and PACKAGE's
head gate cell seeds the packaged head (`saffron/phases/package.py:579`).
Criterion 1's base off `main` is what holds that. Criterion 2's stacked
test builds its parent on `main`, so it passes a seed fetching `main`
alone (measured).

**What `--no-tags` costs.** A cell no longer carries tags. Nothing in
`saffron/` or `.saffron/gates/` reads one. A target repo whose version
comes from a tag, as with setuptools_scm, reads no version in its cell.

**Which criteria have a mutant.** The fetch line is new text, so no
mutant can pin its spelling. Criterion 1 declares a witness alone and
accepts a `skip` from `witness`. Criterion 2 passes today and must keep
passing.

**Criterion 1's witness.** Drive the production script on the host with
`_no_cell_runtime` (`tests/test_worktree.py:669`). The stacked test
calls it the same way (`tests/test_worktree.py:757`). Build the origin
with `_seed_repo`, which leaves `main` at the root commit. Commit the base
with `_commit_file` on a new branch, `saffron/parent`, then check `main`
out again in the origin. Write the two `refs/saffron/*` commits and the
annotated tag with `git hash-object`, `git mktree`, `git commit-tree` and
`git update-ref`. Take the mirror with `ensure_mirror`. Seed once per
config, each into its own volume. Drive `tagOpt` through a global
gitconfig file named by `GIT_CONFIG_GLOBAL`, as tests/test_worktree.py:1762
does. Drive the fetch refspec through `GIT_CONFIG_COUNT`, `GIT_CONFIG_KEY_0`
and `GIT_CONFIG_VALUE_0`. Set both with `monkeypatch.setenv` after the
fixture is built, and point `GIT_CONFIG_SYSTEM` at an empty file so the
host's own config stays out. Patch `SA-0232`'s pause, so a wrong version
whose fetch fails costs nothing. Isolating git config is not the build: the
explicit refspec and `--no-tags` are. Quote the refspec in the script. The host-side seed
inherits that environment. Assert the base's file, `git cat-file -e`
failing on each of the four objects, and the ref list from
`git for-each-ref`. Do not set `remote.origin.fetch` to `+refs/*:refs/*`.
Git refuses to fetch into the branch a fresh repository holds checked
out, so the seed fails before the claim is tested.

**What fails at base, measured.** Both kinds of assertion fail at base on
their own. The seed's `git remote remove origin` leaves `refs/saffron/*`
and tags in place. Under the fetch config, all four objects arrive, with
both `refs/saffron/*` refs and the tag. Under `tagOpt`, the record commit,
its blob and the tag arrive.

**The cell-marked test.** Also write
`test_a_cell_seeded_from_a_mirror_holding_non_branch_refs_holds_none_of_them`,
marked `cell`, modelled on the test at `tests/test_worktree.py:401`. It
seeds a real cell with `image.BASE_TAG`, the way production does, from a
mirror built the same way, base off `main` included. From inside the cell it asserts the head is the
base, the branch is the only ref, and no hidden object is present. It
proves the new command line runs under the image's git and seeds a usable
worktree there. That is git 2.39.5 as of 2026-09-18, not measured against
this change. It cannot set a config. At this spec's base,
`prepare_worktree` passes the seed's `run_ephemeral` no `env`
(`saffron/cell/worktree.py:86-104`). `pyproject.toml:53` deselects it by
default, so no gate in this cell runs it. Do not run it either.

**How the lists were measured.** On 2026-10-07 a prototype of this change
and both new tests ran on a copy of `SA-0232`'s prototype tree. That tree
holds its retry and its tests. Criterion 1's witness failed there under
each config alone. Each wrong version above was applied in turn and failed
it. The unfixed fetch failed it too. Criterion 2's witness and `SA-0232`'s
retry witness passed under every one of them. The whole of
`tests/test_worktree.py` passed on the prototype.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. A docstring stays within ten lines.

**Size.** `saffron/cell/**` is in `elevate_on`, so `size` blocks at the
`bug` ceiling of 1300 tokens (`saffron/gates/core/size.py:26`). Against
`SA-0232`'s prototype tree, the prototype measured 384 tokens by
`size_gate`, 96 lines at 4 tokens a line. The comment in `package.py` is
unmeasured, and three lines are added for it.
