---
id: SA-0170
title: A pushed stack batch is never linked into one stack, and no layer is marked ready
type: feature
priority: 1
depends_on: [SA-0167]
touches:
  - saffron/finish.py
  - saffron/cli.py
  - tests/test_finish.py
  - tests/test_cli.py
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
  - saffron/task.py
  - saffron/batch.py
  - saffron/ledger.py
  - saffron/end_review.py
  - saffron/spec_review.py
  - saffron/qualify.py
  - saffron/follow_up.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/events.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/report/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - tests/test_package.py
  - tests/test_batch.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_task.py
budget_usd: 22
max_attempts: 3
max_turns: 120
acceptance:
  - claim: >-
      `finish.link_stack(ledger, batch_id, *, mirror, url, gh, ready)` links
      a pushed stack, the finishing layer included, and returns its lines.
      It runs `gh stack link --base <default branch>` with each layer's
      pull request URL, bottom to top, then the URL
      `Ledger.stack_finish(batch_id)` holds. With `ready`, it runs `gh pr
      ready` on each of those URLs in the same order, and stops at the first
      that fails. A failed link marks nothing. The lines are `linked <n>
      pull requests`, then `marked <n> ready`, each only where it happened.
      A failed link's line replaces both. A failed mark's line follows
      `marked <k> ready`, where `k` counts the marks made before it. A
      batch with no finishing URL recorded raises `ValueError` before any
      `gh` call. The witness drives three layers with `ready` and without
      it, and one layer with it. It drives a failed link, a failed mark on
      the middle layer, and a batch with no finishing URL, on a remote whose
      default branch is not `main`.
    witness: tests/test_finish.py::test_a_pushed_stack_is_linked_bottom_to_top_and_marked_ready_on_request
  - claim: >-
      `saffron batch --stack` links the finish it pushed, and only that.
      `cli._stack_finish` calls `finish.link_stack` only when some line
      `publish_finish` returned starts with `finish.PUSHED`. It prints each
      line `link_stack` returns after `finish: `. No link runs when the
      publish escalates or raises, when the commit raises, or when the
      commit returns `None`. It passes the pinned
      mirror and url, `ready` from `--ready`, and `_finish_gh`'s runner as
      `gh`. That runner runs its argv in the repository `_batch` resolves.
      It sets `GH_REPO` to the slug `github_slug` reads from the url, beside
      the rest of the environment. It returns exit 127 when the program
      cannot start. A raise from `link_stack`, or from `github_slug` before
      it, prints one line naming its type and message, and the exit code
      stays the stop reason's. `--ready` without `--stack` exits 2 with a
      usage message. The witness drives `--ready` and its absence. It
      drives an escalated and a raising publish, a raising commit, and a
      `None` commit with a layer. It drives a raising link, and each of the
      two outcomes of the runner.
    witness: tests/test_cli.py::test_a_stack_batch_links_its_pushed_stack_through_a_repo_bound_gh
  - claim: >-
      `saffron batch` without `--stack` still hands `run_batch` its budget
      and its defaults.
    witness: tests/test_cli.py::test_saffron_batch_runs_a_night_with_the_defaults_4_2_1_fixes
    preserves: true
---

## Context

Backlog item **b-792ab2**, step 8 of its Done. It cites `DESIGN.md` §4.2
and §5.7. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides that the batch links the stack, that `--ready` marks it ready, and
that nothing merges. Section 4 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md`, under
"Linking", is the design.

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**. The next task is cut from
the last layer, its **predecessor**, and its pull request targets that
layer's branch. PACKAGE opens each pull request as a draft (§5.7).

**Step 8 is four specs.** `SA-0151` builds the finishing commit, and
`SA-0174` the findings file. `SA-0167` judges the commit with the gate
suite, compares each predecessor's head and reads every base back. It
pushes the commit to the finishing layer's own branch, and opens that
branch's draft pull request against the top layer's branch. This spec
links the pushed stack, and with `--ready` marks each layer ready. Both
take in the finishing layer, which ADR 7 adds above every task.

**What the tree base holds.** This spec's tree base is `SA-0167`'s head.
Only `depends_on[0]` stacks (`saffron/task.py:144-147`). None of the chain
from `SA-0142` on exists at `475929b1`, where every line number below was
read. So chain names are cited by symbol.

- From `SA-0151`: `Ledger.stack_layers(batch_id)`, the batch's rows by
  `position`, each with its task's `pr_url`. `run_stack_batch` calls
  `finish(batch_id, unrun)`, and `cli._stack_finish` builds it.
- From `SA-0167`: `finish.publish_finish`, which returns lines. Its one
  success line starts with `finish.PUSHED`, `pushed `, and each
  escalation line with `finish.ESCALATE`. Before that line, it records
  the finishing layer in the ledger's `stack_finishes` table, one row per
  batch. `Ledger.record_stack_finish(batch_id, *, branch, head_sha,
  pr_url=None)` writes the row, and `Ledger.stack_finish(batch_id)`
  returns it with `branch`, `head_sha` and `pr_url`, or `None`. The
  branch is `saffron/batch-<batch id>-finish`. `_stack_finish` takes `repo`. It
  calls `publish_finish` inside its own `try` only after `commit_finish`
  returns a sha, and prints each line after `finish: `. `tests/test_finish.py`
  holds a helper, `_stack(root, count)`, that builds a stack of layers on
  `trunk` with a bare remote, its mirror and a ledger. It holds a fake
  `gh` that answers `pr view` and records each argv.
- From `SA-0144`: `saffron batch --stack`, and `args.stack`.

**What the base already offers.** `default_branch` reads the remote's
`HEAD` (`saffron/phases/package.py:123-131`), and `github_slug` its
`owner/repo` (`saffron/phases/package.py:112-120`). `_guarded_gh` wraps `run_gh`, and turns a `gh`
that cannot start into exit 127 (`saffron/cli.py:1075-1090`). `run_gh`
takes an argv alone (`saffron/scheduler.py:60-61`). The `saffron batch`
parser holds `--repo`, `--budget` and `--until` (`saffron/cli.py:110-121`),
and `main` parses at `:180`. An unmarked test that starts `gh` raises
(`tests/conftest.py:13`, `:86-94`).

**What gh-stack does, measured.** `gh stack link --help` for gh-stack
0.1.1, read on 2026-09-24, says the arguments go bottom to top. A branch
argument is pushed to the remote first, and a pull request URL never is.
`--base` names the bottom's base branch, and `--open` marks pull requests
ready. There is no `--repo` flag, and `-R` is refused as unknown. Run
outside a git checkout, `gh stack link` exits 4 with "determining
repository: ... not a git repository". With `GH_REPO` set, it gets past that
point. Given one argument, it exits 1 with "requires at least 2 arg(s)".
A successful link, with pull request URLs, run from the operator's
checkout, is unmeasured. No run here linked a real stack.

## Problem

Build three things.

1. **The link.** In `saffron/finish.py`, add `link_stack`, as criterion 1
   states. Read the layers with `ledger.stack_layers`, the finishing
   layer's URL with `ledger.stack_finish`, and the default branch with
   `package_phase.default_branch(url, cwd=mirror)`. Pass pull request URLs,
   never branch names, since gh-stack pushes a branch it is given. The
   finishing layer's URL goes last, since the layer sits above every task.
   So a pushed stack holds two pull requests or more, which gh-stack
   requires. Mark with `gh pr ready` on each URL, not with `--open` on the
   link, so a failed mark names its URL. On a failed mark, append `marked
   <k> ready` for the marks made before it, then the failure's line.
2. **The runner.** In `saffron/cli.py`, add `_finish_gh(slug, repo)`. It is
   `_guarded_gh`'s shape, and runs `subprocess.run` with
   `capture_output=True`, `text=True`, `check=False`, `cwd=repo` and
   `env={**os.environ, "GH_REPO": slug}`. It cannot reuse `run_gh`, which
   takes no environment and no directory.
3. **The wiring.** `_stack_finish` gains a `ready` keyword. After it prints
   the publish lines, it links only when one of them starts with
   `finish.PUSHED`. Every other path returns first: a `None` commit, a
   raise from the commit or the publish, and an escalation. Inside its own
   `try`, it computes `package_phase.github_slug(pinned.url)`, then calls
   `finish.link_stack` with `gh` of `_finish_gh(<slug>, repo)`. It prints
   each returned line after `finish: `. A raise prints `finish: nothing
   linked: <type>: <message>`. Build `_stack_finish` with
   `ready=args.ready`. Add `--ready` to `saffron batch` as a `store_true`
   flag. In `main`, after `parse_args`, a `batch` with `--ready` and no
   `--stack` calls `parser.error` with the words `--ready needs --stack`.
   That exits 2, as every other malformed argv does
   (`saffron/cli.py:987-990`). Reach `finish.link_stack` through the module
   at call time, since the witness replaces it there.

**Why the link waits for a positive signal.** `SA-0167` pushes nothing when
it escalates, and each base it read back could be wrong then. A wrong base
leaves every pull request a draft (design section 4). An absent escalation
is not a push: a `None` commit and a raise both leave no escalation line.
So the link runs only after a line that starts with `PUSHED`.

**Why the runner carries the repository twice.** gh-stack names the
repository from the working directory's git remote, and has no flag for
it. The batch runs from the repository under launchd
(`docs/host/dev.saffron.batch.plist:32-33`), but `--repo` can name any
path. So the runner sets both the directory and `GH_REPO`. `gh pr ready`
names its repository by the URL, and reads neither.

## Out of scope

- **A failed link or mark as an escalation.** The design's list of
  escalations names neither. Each prints its line and leaves the rest as
  it stands, so a failed link leaves every pull request a draft.
- **A repository with stacked pull requests turned off.** Measured,
  gh-stack exits 9 with "Stacked PRs are not enabled for this repository".
  That is a failed link, and marks nothing.
- **A lower branch moved after `SA-0167`'s comparison.** The link reads no
  head.
- **Merging.** Nothing merges. `--ready` marks each layer ready, and
  merging stays the operator's.
- **The vocabulary.** `CONTEXT.md` has no entry for linking a stack.
  Backlog item b-466005 files it by hand.

## Notes for the agent

**Both new criteria are new code.** No text at the tree base links a
stack. So criteria 1 and 2 declare a witness and no mutant, and `witness`
reports `skip` for them. Import `link_stack` inside each test body, so the
reverted run fails rather than failing to collect. Criterion 3 names a
test that passes now.

**Tests at the tree base that drive `_stack_finish` to a publish** stub
`finish.publish_finish`. Where one returns a line that starts with
`PUSHED`, also replace `finish.link_stack` there with a recorder that
returns an empty list.

**Criterion 1's witness** builds on `SA-0167`'s `_stack` helper, and needs
no push. In each case but the last, it records the finishing layer with
`ledger.record_stack_finish`. The row holds `saffron/batch-<batch
id>-finish`, the top head, and `https://github.com/o/r/pull/200`. Give the
fake `gh` a way to fail one argv with exit 1 and `boom` on stderr. It runs
six cases and asserts in each that `gh`'s calls and the lines are exactly
as the claim states:

- three layers with `ready`, and three without it, where the link names
  four URLs, pull 200 last
- one layer with `ready`, where the link names pull 101, then pull 200
- three layers with `ready` and the link failing, which gives `gh stack
  link failed, so every pull request stays a draft: boom`
- three layers with `ready` and the middle URL's mark failing, which gives
  `linked 4 pull requests`, `marked 1 ready`, then `gh pr ready <url>
  failed: boom`
- three layers and no finishing row, which raises `ValueError` with no
  `gh` call

`_stack` creates tasks and records layers top first, so neither order
follows position. These fail it:

- the layers taken by task id
- the default branch spelled `main`
- the URLs passed top to bottom, or branch names in place of URLs
- the finishing layer's URL left out of the link or the marks, or put
  first
- the link skipped with one task layer, which leaves the finishing layer
  unlinked
- a batch with no finishing URL linked without it
- marks made without `ready`, or `--open` on the link in place of each mark
- marks made after a failed link, or past a failed mark
- no count of the marks made before a failed one

**How the list was measured.** A throwaway run on 2026-09-24 at
`68892367` stood in for `SA-0145`'s table and writer and `SA-0151`'s
`Ledger.stack_layers`. It loaded a prototype of `link_stack` with a
prototype of `SA-0167`'s `_stack`. The right build passed. Each of the 10
wrong builds that run named was applied as a text edit to `link_stack`
alone, and each failed the witness. That prototype linked the task layers
alone. ADR 7's revision then gave the finishing layer its own pull
request. So the three wrong builds on the finishing layer are unmeasured,
and so is the witness's finishing row.

**Criterion 2's witness** follows `SA-0167`'s witness for `saffron batch
--stack`, with `_readiness_passes` (`tests/test_cli.py:2603-2621`) and
`_fake_batch_resolution` (`:2624-2640`). The pinned url is
`https://github.com/o/r.git`. The fake `run_stack_batch` calls `finish(3,
[5, 6])` and returns `UNTIL`. It stubs `finish.write_findings` and
`finish.commit_finish` with `*args, **kwargs`, the commit returning
`c`×40. `finish.publish_finish` returns `["pushed cccccccccccc to
saffron/batch-3-finish, draft pull request
https://github.com/o/r/pull/200"]`. The fake `link_stack` records its arguments and returns
two lines.

The first run passes `--stack --ready`. It asserts exit 0, the pushed line
then both linked lines after `finish: `, and each argument. Then, under
`monkeypatch.context()`, it replaces `subprocess.run` in `cli`'s namespace
with a recorder and calls the kept `gh`. It asserts the argv, `cwd` of the
resolved `--repo`, `GH_REPO` of `o/r`, and `PATH` as the process holds it.
The recorder then raises `OSError`, and `gh` returns exit 127. Seven more
runs follow, each with its own `--home`:

- `--stack` alone passes `ready` false
- a publish returning a line that starts with `ESCALATE` calls no link
- a publish raising `GitError("gone")` calls no link
- a commit raising `GitError("gone")` calls no link
- a commit returning `None`, with `Ledger.stack_layers` replaced to return
  one row, calls no link
- a `link_stack` raising `GitError("gone")` prints `finish: nothing
  linked: GitError: gone` and exits 0
- `--ready` without `--stack` raises `SystemExit` 2, and stderr names
  `--ready needs --stack`

These fail it:

- `_guarded_gh` passed as `gh`, which sets no `GH_REPO`
- an environment of `GH_REPO` alone, which drops `PATH`
- no `cwd`, which leaves the command's own working directory
- a `gh` that raises on a program it cannot start
- link unless `ESCALATE`, which links after a `None` commit or a raise
- `ready` fixed at either value
- a raise that reaches `main`, which exits 2
- `--ready` accepted without `--stack`

Criterion 2 is unmeasured. `saffron batch --stack` and `_stack_finish` do
not exist at `68892367`.

**The `prose` gate** reads every new comment and docstring
(`.saffron/gates/prose.py`). Write no em dash, semicolon, contraction,
perfect tense, hedge or sentence over 25 words. Keep each docstring within
ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** No path in `touches` is in `elevate_on`, so `size` is advisory
at the `feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`).
A prototype of the whole change, formatted with `ruff`, was measured with
`size_gate` at `68892367`. It came to 966 tokens.

| part | lines | tokens |
|---|---|---|
| `link_stack` in `saffron/finish.py` | 34 | 130 |
| criterion 1's witness in `tests/test_finish.py` | 39 | 224 |
| `_finish_gh`, the flag and the wiring in `saffron/cli.py` | 54 | 174 |
| criterion 2's witness in `tests/test_cli.py` | 175 | 438 |

It carried no docstrings and lacked the fake `gh`'s failing argv. About 80
more tokens cover those. The finishing layer's URL, its `ValueError` and
the witness's finishing row and sixth case add about 100 more, estimated
and not measured. So the estimate is about 1150 tokens, 38% of the
ceiling.
