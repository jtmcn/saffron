---
id: N
title: "rev 16: what pinning the base and the gate runner found"
revisions: [16]
question: "What tree a task is about, and who may write the thing that judges it (backlog items 11 and 12)"
---

Backlog items 11 and 12 are the same question asked twice — what tree is a task
about, and who is allowed to have written the thing that judges it. Twelve tasks
closed both. Most of what follows is in neither item, and the three sharpest
findings were reached by reading rather than by running.

### `github_slug` was wrong in more ways than item 11 says, twice over

Item 11 describes a two-segment-GitHub-URL problem. Measured before any code was
written, three of five real inputs returned a wrong answer rather than refusing:

| Input | Old result |
|---|---|
| `/Users/joel/Code/saffron` | `Code/saffron` |
| `git@gitlab.com:group/owner/repo.git` | `owner/repo` — leading segment dropped |
| `https://example.com/repo` | `example.com/repo` — the **host** as the owner |

The last shape is not in the backlog at all. With one path segment the pattern
takes the host as the owner, so a remote that is not a forge still yields a
plausible `owner/repo` and `gh` is handed a repository that cannot exist.

**Then the first fix was still wrong, and review caught it.** The tightened
pattern matched `github.com` preceded by any of `^ @ / .`, which does not
distinguish a URL scheme from a filesystem path separator. Measured:
`slug('/Users/joel/go/src/github.com/owner/repo')` returned `owner/repo` — a
GOPATH-style checkout walking straight through the refusal the change existed to
add. Worse, twelve fixtures had by then been relocated to
`tmp_path/github.com/o/r.git` to satisfy that same pattern, so the test suite had come
to depend on the loophole. The shipped pattern anchors on a real remote URL — a
scheme, or the SCP-like `user@host:` form — and is measured against 19 cases:
nine accept, ten refuse, including `https://github.com.evil.com/a/b`, which
nobody had considered.

**A port is accepted, but only in the scheme form.** `ssh://git@github.com:22/o/r.git`
is a real remote and the `:22` is a port; in `git@github.com:1234/repo.git` the
colon introduces the path and `1234` is an owner. One pattern cannot read the
colon both ways, so the branch it sits in decides.

**The narrowing is real, and it is wider than "unreachable".** Measured against
the old pattern, two shapes returned a *correct* slug before this change and are
refused now: a GitHub Enterprise host (`git@github.example.com:owner/repo.git` →
`owner/repo`), and an SSH `Host` alias standing in for github.com
(`git@github-work:owner/repo.git` → `owner/repo`). Because `cli._run_cell` reads
the slug for its refusal (§5.7), such a repo can no longer start a cell at all.
Accepted rather than fixed: the slug is handed to `gh pr create --repo owner/repo`,
which resolves against `gh`'s own default host, so accepting any host is worse than
refusing — `git@gitlab.com:owner/repo.git` would open a pull request on the wrong
forge. GHE is the one shape where the old behaviour was right, and carrying it
properly means plumbing the host through to `GH_HOST`, which nothing here does.
A repo on either shape must point `origin` at github.com to run.

53. **A refusal that is loosened to make tests pass is a refusal that no longer
    exists.** The tell is not that the pattern is imperfect — it is that the
    repair reshapes a *fixture* rather than a caller. Twelve fixtures moved to a
    path shape no real checkout has, and after that the test suite was evidence for
    the loophole rather than against it.

### The baseline and head suites could run different gate executables

The baseline suite runs in the same cell and the same worktree as head, before
the agent starts. So the baseline ran the base tree's gates and head ran whatever
gates were in `/work` by then, and a task editing its own `tests` gate changed
what the two subtracted sides mean. That is suite drift by construction — the
identical shape item 11 flags for `reverify`'s missing `thread_env` — and pinning
gates to `base_sha` closes it as a side effect. **This is the stronger of the two
reasons for pinning, and it is not why item 12 was written.** Nothing had
recorded it; §5.4's `tool` field would have reported it after the fact, on a task
that had already spent its attempts.

### `reverify` was a second copy of the whole seam

It has its own cell, its own `prepare_worktree` call, and its own
`gate_executables(WORKTREE_MOUNT)`. Updating only the supervisor would have left
the two suites `reverify` subtracts coming from different executables —
reintroducing the finding above in the one place §5.7 already flags for drift —
and a required `gates_dir` argument would have broken PACKAGE at runtime.
Invisible to `make check`, because the tests covering that path are cell-marked
and excluded by default. Found by reading, not by running.

54. **A control applied at one call site is not applied; it is applied at one
    call site.** The question a boundary change has to answer is not "does the
    new path use it" but "how many paths are there" — and where the second path
    is exercised only by tests the default run excludes, green is not evidence.

### Item 11 overstated the ledger defect by half

`branch` was already written at insert time by `create_task`, fed from
`spec.branch`. Only `pushed_sha` was missing, written solely by
`set_task_package` after `open_draft_pr`. One column, not two — and the fix is
correspondingly smaller than the item's account of it.

### Three smaller ones

- **A path-lifetime hazard the plan walked into.** The first draft put
  `reverify`'s exported gates under the package scratch directory — which
  `add_worktree` hands to `shutil.rmtree` and which the `finally` hands to
  `remove_worktree`. Gates written there have the worktree's lifetime. The
  shipped path is a sibling, and `Spec.id`'s `^[A-Za-z0-9]+-[0-9]+$` pattern is
  what makes `<id>-gates` unable to collide with another spec's scratch dir.
- **`git status --porcelain -z` emits `RM`, not `R `, for a staged rename that
  was also modified**, so the rename skip tests `"R" in entry[:2]` rather than
  `entry[:1] == "R"`. Mutation-checked: removing the skip leaks `"xt"` — the tail
  of `a.txt`, sliced by `entry[3:]` — into the dirty-path list, which would then
  be reported to the agent as a path to commit.
- **`cell_env` would have put a credential in a gate-only cell.** The obvious way
  to give `reverify` its `thread_env` is the call the session cell uses, and that
  call injects `CLAUDE_CODE_OAUTH_TOKEN`. `reverify` has no proxy and an
  `--internal` network with no egress; it takes `dict(policy.thread_env)`
  instead. §5.1's one-credential exception is narrow enough that a convenience
  helper can widen it without anybody deciding to.

### The dirty-tree rule needed no new control flow, and the terminal state does not prove it

`committed` is a gate, so a dirty tree gets the repair turn the loop already
gives every `fail`, and a second identical look is the no-progress rule. Verified
by mutation: dropping the no-progress branch yields three repair turns and four
attempts instead of one and two — but `state` is `EXHAUSTED` either way, because
§3.3 deliberately maps no-progress and exhausted to one state. Only the call
count and the attempt count discriminate.

55. **Where two outcomes deliberately share a state, that state cannot be the
    assertion.** A test asserting the terminal state alone passes against the
    regression it was written to catch, and reads as coverage while providing
    none. The collapse is usually correct — the operator does not need the
    distinction — which is exactly why the test has to look somewhere else.

### Deferred, for the record

`out_dir/package/<id>-gates` and `task_dir/gates` are new batch-tree artifacts
with no manifest entry and no cleanup; nothing enumerates those directories
today, and `saffron gc` (§4.5) is v1 work. The `real_remote` → `github_slug`
composition inside `package()` is no longer covered end to end — both fixture
sites monkeypatch the slug — against a regex that is far better covered in
isolation. And the empty-head guard in the default-branch fetch is untested:
constructing a successful fetch with an empty `FETCH_HEAD` against real git is
harder than the guard is worth.

---

