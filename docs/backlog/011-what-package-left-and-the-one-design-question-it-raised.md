---
id: 11
title: What PACKAGE left, and the one design question it raised
status: done
tier: null
closed: 2026-08-23
specs: []
prs: [5]
commits: []
cites: [§4.2, §5.1, §5.4, §5.5, §5.7, §9]
related: []
---

## Problem

**Status:** **done**, 2026-08-23 — all six, plus the design decision the
first one asked for, in `DESIGN.md` rev 16. The full account is in this item's
own body below. **One accepted risk stands and is not closed by it:** the
credential refusal keeps a secret off the remote, not off the host, and §5.4's
`secrets` gate is still v1's to build.

Written at the close of sub-project A (PR #5). Every item was found by review or
by measurement during that build; none is speculation. The first is a design
decision, the rest are small.

### The base a task is cut from is the working copy's `HEAD`, not the default branch

`cli.py` sets `base_sha` from `git rev-parse HEAD` in the repo you invoked it in.
Run from a feature branch, `base_sha` is that branch's tip, so the fetched
default-branch head never equals it: re-verification fires on **every** package,
starting two containers and running two full suites, and the "provably redundant
skip" is only reachable from a checkout sitting exactly on an up-to-date default
branch. Worse, the patch is cut against a tree the default branch has never seen,
so `--3way` merges onto a base missing every commit the feature branch carries,
and a task touching a file the branch also touched conflicts — a `MERGE_FAILED`
that is an artifact of where the operator was standing.

**This is a design question, not a defect.** §5.7 is silent on where `base_sha`
comes from, and the scheduler (§4.2) will need an answer before it can start
tasks unattended. **Done looks like:** §5.7 saying whether a task's base is the
invoking checkout's `HEAD` or the remote's default branch, and the code agreeing.

### `github_slug` fails quiet on anything that is not a two-segment GitHub URL

Measured: `/Users/joel/Code/saffron` returns `Code/saffron`, and a GitLab-style
`group/owner/repo` returns `owner/repo` — the leading segment is dropped rather
than refused. Harmless for `github.com`, which is always two segments, but a
local-path origin is exactly what `session.py` falls back to, and a wrong slug
reaches `gh` as a repo that does not exist. **Done looks like:** a URL that is not
a recognisable forge remote raises rather than guessing.

### A pushed branch whose `gh pr create` failed is recorded nowhere but stdout

`_finish` runs after `open_draft_pr`, so a `gh` that is missing, unauthenticated,
or refused leaves the branch pushed and the ledger still reading
`READY_FOR_REVIEW` with no `branch` and no `pushed_sha`. A re-run self-heals — the
lease matches the branch it pushed — but the operator has to know that. **Done
looks like:** branch and pushed sha recorded before the pull request is opened,
and only the URL after.

### `reverify`'s cell does not get the repo's `thread_env`

The in-cell suite runs under `cell_env(proxy_ip, policy.thread_env)`; the
re-verification cell gets `env={}`. Empty for Saffron, so it changes nothing
today — but the two suites being subtracted are run under different environments
by construction, which is a suite-drift vector for the second repo onboarded
(§9's v2 is where that bites).

### Three test gaps, each one assertion

The pipe-escaping test covers only `_new_failures`, not the two tables added for
findings and disagreements — and a `|` is likelier in a model-authored `claim`
than in a gate message. `test_an_unanchored_finding_still_appears` checks the
claim renders but never that the row is marked `no`, which is the half that makes
drop rate visible (§5.5). And no test exercises `attempts`, `new_failures`,
`reviews` or `rebut_result` on `CellOutcome`'s success path.

### §5.7 says "rebase" and means `git apply --3way`

Step 1 says *rebase onto current `main`*; the v1 subsection describes applying one
squashed patch. Both are true — step 1 is the intent, the subsection is the
mechanism — but the document never says so, and a reader meeting them in order
will think one contradicts the other. One sentence, no renumbering.

### And one accepted risk, restated so it does not go quiet

The credential refusal keeps a secret off the *remote*, not off the *host*:
`patch.diff` and `pr_body.md` still sit in the batch tree with it in them.
`_CREDENTIAL_SHAPES` is a partial list under a `ponytail:` comment naming that
ceiling, and the real answer is §5.4's `secrets` gate, which is still v1's to
build.

**Done, 2026-08-23.** All six, and the design decision the first one asked for
is written down: `DESIGN.md` rev 16 — §5.1 for the fetch, §5.4 for the gate
source, §5.7 for the base, Appendix N for what building it found. A task's base
is now the head of the remote's default branch as of task start, so both ends of
the comparison read one source and the redundant-suite skip is reachable by
construction rather than from a checkout that happened to be standing in the
right place. Two things this item got wrong, both measured rather than
re-reasoned:

**`github_slug` was wrong on three of five real inputs, not on GitLab alone.** A
one-segment URL — `https://example.com/repo` — takes the **host** as the owner,
which this item does not name and which is the case where a wrong slug looks most
plausible. And the first fix was itself wrong, caught in review: a pattern
matching `github.com` after any of `^ @ / .` let `/Users/joel/go/src/github.com/owner/repo`
through, and twelve fixtures had by then been moved to a path shape that
satisfied it. Appendix N carries the 14-case table the shipped pattern is
measured against.

**The ledger defect is one column, not two.** `branch` was already written at
insert time by `create_task`, from `spec.branch`; only `pushed_sha` was missing,
written solely by `set_task_package` after `open_draft_pr`. What ships records
the pushed sha before the pull request is opened and the URL after.

`reverify` takes `dict(policy.thread_env)` rather than `cell_env(...)`: the
obvious route would have put `CLAUDE_CODE_OAUTH_TOKEN` into a gate-only cell with
no proxy and no egress. The three test gaps are closed, and §5.7 now says in one
sentence that step 1's "rebase" is the intent and `git apply --3way` the
mechanism. The accepted credential risk above is unchanged and still §5.4's
`secrets` gate to close.
