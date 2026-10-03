---
id: SA-0170
title: A pushed stack batch is never linked into one stack
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
budget_usd: 23
max_attempts: 3
max_turns: 130
estimated_lines: 262
estimate_measured: true
acceptance:
  - claim: >-
      `finish.link_stack(ledger, batch_id, *, mirror, url, gh)` links a
      pushed stack, the finishing layer included, and returns its lines. It
      makes one `gh` call, `gh stack link --base <default branch>`, with each
      layer's pull request URL bottom to top. The URL
      `Ledger.stack_finish(batch_id)` holds comes last. It marks no pull
      request ready. A link that exits 0 returns `linked <n> pull
      requests`, where `n` counts every URL passed. A link that exits 127,
      because `gh` could not start, returns its own line. Any other failed
      link returns the refused link's line. A batch with no finishing URL
      raises `ValueError` naming the batch before any `gh` call. That holds
      whether it has no finishing row or a row whose `pr_url` is `None`. The
      witness drives three layers and one layer. It drives a link that exits
      0, one that exits 1 and one that exits 127. It drives a batch with no
      finishing row and one whose row has no URL. Every case runs on a
      remote whose default branch is `trunk`.
    witness: tests/test_finish.py::test_a_pushed_stack_is_linked_bottom_to_top_with_its_finishing_layer_last
    wrong_versions:
      - The URLs passed top to bottom, or branch names in place of URLs.
      - The finishing layer's URL left out of the link, or put first.
      - A link that exits 127 read as a refused link.
      - A count of the task layers alone in `linked <n> pull requests`.
      - A finishing row checked for presence alone, which passes `None` to `gh`.
  - claim: >-
      `saffron batch --stack` links the finish it pushed, and only that.
      `cli._stack_finish` calls `finish.link_stack` only when some line
      `publish_finish` returned starts with `finish.PUSHED`, wherever that
      line falls. It prints each line `link_stack` returns after `finish: `.
      No link runs when the publish escalates or raises, when the commit
      raises `GitError` or `ValueError`, or when the commit returns `None`.
      Each of those prints `finish: linked nothing, the finish did not push`
      once, and a linked finish never prints it. It passes the pinned mirror
      and url, and `_finish_gh`'s runner as `gh`. That runner runs its argv
      in the repository `_batch` resolves. It sets `GH_REPO` to the slug the
      publish block already read, beside the rest of the environment. It
      returns exit 127 when the program cannot start. A raise from
      `link_stack` prints one line naming its type and message, and the exit
      code stays the stop reason's. The witness drives a publish whose pushed
      line comes first with another line after it, and one whose pushed line
      comes second. It drives an escalated and a raising publish. It drives
      a commit raising `GitError` and one raising `ValueError`. It drives a
      `None` commit with no layer and with one. It drives a raising link, and
      both outcomes of the runner.
    witness: tests/test_cli.py::test_a_stack_batch_links_its_pushed_stack_through_a_repo_bound_gh
    wrong_versions:
      - "`_guarded_gh` passed as `gh`, which sets no `GH_REPO`."
      - An environment of `GH_REPO` alone, which drops `PATH`.
      - A runner with no `cwd`, which leaves the command's own working directory.
      - A link unless some line starts with `ESCALATE`, which links after a raising publish.
      - A check of the first line alone for `PUSHED`, or a substring check in place of `startswith`.
      - No `linked nothing` line for a `None` commit when the batch has no layer.
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
decides that the batch links the stack and that nothing merges. Section 4
of `docs/superpowers/specs/2026-09-23-stack-batch-design.md`, under
"Linking", is the design.

ADR 7 (`:129`) and that section also give a `--ready` flag that marks each
layer ready. The operator withdrew it on 2026-10-02, and this spec builds no
such flag. Marking a draft ready is the operator's one approval
(`DESIGN.md:1289`). `saffron reconcile` records a pull request that is open
and ready as `APPROVED` (`saffron/reconcile.py`, `_next_state`). So a batch that
marked its own layers ready would approve work nobody read.

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**. The next task is cut from
the last layer, its **predecessor**, and its pull request targets that
layer's branch. PACKAGE opens each pull request as a draft (§5.7).

**Step 8 is five specs.** `SA-0151` builds the finishing commit,
`SA-0174` the findings file, and `SA-0177` the finishing layer's ledger
row. `SA-0167` judges the commit with the gate suite, compares each
predecessor's head and reads every base back. It pushes the commit to the
finishing layer's own branch, and opens that branch's draft pull request
against the top layer's branch. This spec links the pushed stack, the
finishing layer included, and leaves every pull request a draft.

**What the tree base holds.** This spec's tree base is `main` with
`SA-0167` merged, read at `39864aea`. All four parents are in
`.saffron/specs/done/`.

- `finish.publish_finish` returns lines. Its one success line starts with
  `finish.PUSHED`, `pushed `, and each escalation line with
  `finish.ESCALATE`. Before that line, it records the finishing layer with
  `Ledger.record_stack_finish`. When removing its worktree raises
  `GitError`, a second line follows the pushed line. The branch is
  `saffron/batch-<batch id>-finish`.
- `cli._stack_finish(*, pinned, ledger, out_dir, pooled, repo)` writes the
  findings, then commits. It catches only `GitError` and `ValueError` from
  `finish.commit_finish`, and its docstring says any other raise reaches
  `main`. A `None` commit prints one of two lines, by whether
  `ledger.stack_layers` returns a row, and returns. A real commit then runs
  one `try` guarding `Exception`. That `try` computes
  `slug = package_phase.github_slug(pinned.url)`, then calls
  `finish.publish_finish` with `gh=_guarded_gh([])`. It prints each line
  after `finish: `, or one `finish: publish stopped: <type>: <message>`
  line on a raise.
- `Ledger.stack_layers(batch_id)` returns the batch's rows by `position`,
  each with its task's `pr_url` and `branch`. `Ledger.stack_finish` returns
  the finishing row as a `sqlite3.Row`, whose `pr_url` reads by key, or
  `None`. `record_stack_finish` takes `pr_url=None`.
- `tests/test_finish.py` holds `_stack(root, count)`. It builds a stack of
  layers on `trunk` with a bare remote, its mirror and a ledger. Its layers
  hold `https://github.com/o/r/pull/<100 + position>`. It returns `url` as
  the bare remote's path. The file also holds `_FakeGh`, which records
  each argv in `calls`. It answers `pr view`, `pr create` and `pr ready`,
  and raises `AssertionError` on any other argv.

**What the base already offers.** `default_branch` reads the remote's
`HEAD`, and `github_slug` its `owner/repo` (`saffron/phases/package.py`).
`cli._guarded_gh` wraps `run_gh`, and turns a `gh` that cannot start into
exit 127. `scheduler.run_gh` takes an argv alone. An unmarked test that
starts `gh` raises `HostToolExecInTest` (`tests/conftest.py`).

**What gh-stack does, measured.** `gh stack link --help` for gh-stack
0.1.1, read on 2026-09-24, says the arguments go bottom to top. A branch
argument is pushed to the remote first, and a pull request URL never is.
`--base` names the bottom's base branch. There is no `--repo` flag, and
`-R` is refused as unknown. Run outside a git checkout, `gh stack link`
exits 4 with "determining repository: ... not a git repository". With
`GH_REPO` set, it gets past that point. Given one argument, it exits 1
with "requires at least 2 arg(s)". A successful link, with pull request
URLs, run from the operator's checkout, is unmeasured. No run here linked
a real stack.

## Problem

Build three things.

1. **The link.** In `saffron/finish.py`, add `link_stack`, as criterion 1
   states. Read the finishing row with `ledger.stack_finish` first. A
   missing row, or a row whose `pr_url` is `None`, raises `ValueError`
   naming the batch. Then read the layers with `ledger.stack_layers`, and
   the default branch with `package_phase.default_branch(url, cwd=mirror)`.
   Pass pull request URLs, never branch names, since gh-stack pushes a
   branch it is given. The finishing layer's URL goes last, since the layer
   sits above every task. So a pushed stack holds two pull requests or
   more, which gh-stack requires. A link that exits 127 gives `gh could not
   start, so nothing is linked and every pull request stays a draft:
   <stderr>`. Any other failed link gives `gh stack link failed, so every
   pull request stays a draft: <stderr>`. Strip `stderr` in both.
2. **The runner.** In `saffron/cli.py`, add `_finish_gh(slug, repo)`. It is
   `_guarded_gh`'s shape. It runs `subprocess.run` with
   `capture_output=True`, `text=True`, `check=False`, `cwd=repo` and
   `env={**os.environ, "GH_REPO": slug}`. It returns
   `subprocess.CompletedProcess(argv, 127, "", str(exc))` on `OSError`. It
   cannot reuse `run_gh`, which takes no environment and no directory.
3. **The wiring.** After `_stack_finish` prints the publish lines, it links
   only when one of them starts with `finish.PUSHED`. Every other path
   prints `finish: linked nothing, the finish did not push` once and
   returns. Those paths are a `None` commit, a commit raising `GitError` or
   `ValueError`, a raising publish and an escalation. Leave the commit's
   `except` as narrow as it is. The link runs inside its own `try`
   guarding `Exception`. It calls `finish.link_stack` with `gh` of
   `_finish_gh(slug, repo)`, reusing the `slug` the publish block computed.
   It prints each returned line after `finish: `. A raise prints `finish:
   nothing linked: <type>: <message>`. Reach `finish.link_stack` through
   the module at call time, since the witness replaces it there. The
   signature of `_stack_finish` and the code in `_batch` stay as they are.

**Why the link waits for a positive signal.** `SA-0167` pushes nothing when
it escalates, and each base it read back could be wrong then. A wrong base
leaves every pull request a draft (design section 4). An absent escalation
is not a push: a `None` commit and a raise both leave no escalation line.
So the link runs only after a line that starts with `PUSHED`. Each path
that links nothing says so in one line. In this repo every finish with a
layer escalates red (backlog item b-b0cd68). Without that line, a night's
log would not say why its stack stayed unlinked.

**Why the runner carries the repository twice.** gh-stack names the
repository from the working directory's git remote, and has no flag for
it. Under launchd the batch runs with the repository as its
`WorkingDirectory` (`docs/host/dev.saffron.batch.plist:32-33`). But the
`--repo` flag can name any path. So the runner sets both the directory and
`GH_REPO`.

## Out of scope

- **Marking a layer ready.** The batch never marks a layer ready, and adds
  no `--ready` flag. A pull request that is open and ready reconciles as
  `APPROVED` (`saffron/reconcile.py`), which is the operator's own approval
  (`DESIGN.md:1289`). Every layer and the finishing layer stay drafts.
  ADR 7's `--ready` sentence is the operator's to revise by hand.
- **A failed link as an escalation.** The design's list of escalations
  does not name it. It prints its line and leaves every pull request a
  draft.
- **A repository with stacked pull requests turned off.** Measured,
  gh-stack exits 9 with "Stacked PRs are not enabled for this repository".
  That is a failed link.
- **A lower branch moved after `SA-0167`'s comparison.** The link reads no
  head.
- **Linking the task layers after a finish that did not push.** A red
  finish leaves every layer unlinked. Their bases can still be right. This
  spec prints one line for it. Backlog item b-b0cd68 records why every
  finish here is red.
- **A missing gh-stack extension.** `gh` then starts and exits with its
  own code, which reads as a refused link. Which code it exits with is
  unmeasured.
- **Merging.** Nothing merges, and merging stays the operator's.
- **The vocabulary.** `CONTEXT.md` has no entry for linking a stack.
  Backlog item b-466005 files it by hand.

## Notes for the agent

**Both new criteria are new code.** No text at the tree base links a
stack. So criteria 1 and 2 declare a witness and no mutant, and `witness`
reports `skip` for them. Import `link_stack` inside the criterion 1 test
body, so the reverted run fails rather than failing to collect. Criterion
3 names a test that passes now.

**Tests at the tree base that assert `_stack_finish`'s printed lines** are
these three, all in `tests/test_cli.py`. Each stubs `publish_finish` with
no `PUSHED` line, so none reaches a real `link_stack`. Each asserts by
membership. In each, add an assertion that `finish: linked nothing, the
finish did not push` is printed after its first `main` call. Change nothing
else in them.

- `SA-0151`'s `test_a_stack_batch_commits_its_finish_and_survives_a_raise`
- `SA-0167`'s `test_a_stack_batch_publishes_its_finish_through_the_finishing_suite`
- `SA-0174`'s `test_a_stack_batch_writes_its_findings_from_the_pooled_list_its_writer_filled`

**Criterion 1's witness** builds on `_stack`, and needs no push. Add a
keyword `link=(0, "", "")` to `_FakeGh`. It answers `gh stack link` with
that exit code, stdout and stderr. In each case but the fifth, the witness
records the finishing layer with `ledger.record_stack_finish`. The row
holds `saffron/batch-<batch id>-finish`, the top head, and
`https://github.com/o/r/pull/200`. Each case uses its own `_stack` root.
It runs six cases, and asserts in each that `gh.calls` and the lines are
exactly as stated:

- three layers, where the one call is `["gh", "stack", "link", "--base",
  "trunk"]` then pulls 101, 102, 103 and 200, and the lines are `linked 4
  pull requests`
- one layer, where the URLs are pull 101 then pull 200, and the line is
  `linked 2 pull requests`
- three layers with `link=(1, "", "boom\n")`, which gives `gh stack link
  failed, so every pull request stays a draft: boom`
- three layers with `link=(127, "", "boom\n")`. That gives `gh could not
  start, so nothing is linked and every pull request stays a draft: boom`
- three layers and no finishing row, which raises `ValueError` matching
  the batch id, with `gh.calls` empty
- three layers and a finishing row recorded with no URL, which raises
  `ValueError` matching the batch id, with `gh.calls` empty

`_stack` creates tasks and records layers top first, so neither order
follows position.

**Criterion 2's witness** follows `SA-0167`'s witness for `saffron batch
--stack`, with `_readiness_passes` and `_fake_batch_resolution` in
`tests/test_cli.py`. The pinned url is `https://github.com/o/r.git`. The
fake `run_stack_batch` calls `finish(3, [5, 6])` and returns `UNTIL`. It
stubs `finish.write_findings` and `finish.commit_finish` with `*args,
**kwargs`, the commit returning `c`×40. `finish.publish_finish` returns
two lines. The first is `pushed cccccccccccc to saffron/batch-3-finish,
draft pull request https://github.com/o/r/pull/200`. The second is
`worktree left at /p: GitError: busy`. The fake `link_stack` records its
arguments and returns two lines.

The first run passes `--stack`. It asserts exit 0, and both publish lines
then both linked lines after `finish: `, as four consecutive printed
lines. It asserts the batch id, the mirror and the url passed, and no
`linked nothing` line. Then, under `monkeypatch.context()`, it replaces
`cli.subprocess.run` with a recorder and calls the kept `gh`. It asserts
the argv, `cwd` of `tmp_path.resolve()` (the `--repo` default, resolved),
`GH_REPO` of `o/r`, and `PATH` as `os.environ` holds it. A second recorder
raises `OSError`, and `gh` returns exit 127. Eight more runs follow, each
with its own `--home`:

- a publish returning the worktree line, then the pushed line, calls the
  link once and prints no `linked nothing` line
- a publish returning `escalate: nothing pushed to x` calls no link. The
  line holds `pushed ` so a substring check links on it.
- a publish raising `GitError("gone")` calls no link
- a commit raising `GitError("gone")` calls no link
- a commit raising `ValueError("off")` calls no link
- a commit returning `None`, with `Ledger.stack_layers` replaced to return
  no row, calls no link
- a commit returning `None`, with `Ledger.stack_layers` replaced to return
  one row, calls no link
- a `link_stack` raising `GitError("gone")` prints `finish: nothing
  linked: GitError: gone` and exits 0

Each of the six runs that call no link asserts that the printed lines hold
`finish: linked nothing, the finish did not push` exactly once.

**How the arrangement was measured.** On 2026-10-02, at `39864aea`, a
throwaway build of the change ran against both witnesses as written above.
Its source change was `link_stack`, `_finish_gh` and the wiring. Both
witnesses failed with the source change reverted, and passed with it. Each
wrong version below was applied as a text edit to that build, alone, and
the witness rerun. Every one failed its witness. The build was then
discarded.

| witness | wrong version | outcome |
|---|---|---|
| 1 | URLs top to bottom | killed |
| 1 | branch names in place of URLs | killed |
| 1 | layers taken by task id | killed |
| 1 | default branch spelled `main` | killed |
| 1 | finishing URL left out | killed |
| 1 | finishing URL first | killed |
| 1 | link skipped with one task layer | killed |
| 1 | no finishing URL, linked without it | killed |
| 1 | finishing row checked for presence alone | killed |
| 1 | exit 127 read as a refused link | killed |
| 1 | `n` counting the task layers alone | killed |
| 2 | `_guarded_gh([])` passed as `gh` | killed |
| 2 | an environment of `GH_REPO` alone | killed |
| 2 | no `cwd` | killed |
| 2 | a runner that lets `OSError` out | killed |
| 2 | a link unless some line starts with `ESCALATE` | killed |
| 2 | the first line alone checked for `PUSHED` | killed |
| 2 | the last line alone checked for `PUSHED` | killed |
| 2 | `PUSHED in line` in place of `startswith` | killed |
| 2 | no `linked nothing` after a raising commit | killed |
| 2 | no `linked nothing` for a `None` commit with no layer | killed |
| 2 | no `linked nothing` after a raising publish | killed |
| 2 | `linked nothing` printed after a link too | killed |
| 2 | a raise from the link that reaches `main` | killed |
| 2 | `finish.link_stack` bound at import time | killed |

**The `prose` gate** reads every new comment and docstring
(`.saffron/gates/prose.py`). Write no em dash, semicolon, contraction,
perfect tense, hedge or sentence over 25 words. Keep each docstring within
ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** No path in `touches` is in `elevate_on`, so `size` is advisory
at the `feature` ceiling of 3000 tokens (`saffron/gates/core/size.py`).
The measured build above, formatted with `ruff`, came to 978 tokens by
`size`'s own counter.

| part | tokens |
|---|---|
| `link_stack` in `saffron/finish.py` | 143 |
| `_finish_gh` and the wiring in `saffron/cli.py` | 109 |
| criterion 1's witness and `_FakeGh`'s `link` in `tests/test_finish.py` | 263 |
| criterion 2's witness and three ancestor assertions in `tests/test_cli.py` | 463 |

Its test docstrings were one line each. About 70 more tokens cover fuller
ones. So the estimate is about 1050 tokens, 35% of the ceiling.
