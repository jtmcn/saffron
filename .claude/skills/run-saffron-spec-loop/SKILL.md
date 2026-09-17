---
name: run-saffron-spec-loop
description: Use when asked to run the Saffron spec loop over the queued specs, or to stack spec pull requests for review instead of merging them.
---

# Run the Saffron spec loop

Every queued spec goes through an attended `saffron cell`, an independent
review, and review commits; the pull requests are then linked into one stack
for the operator. **Nothing is merged.** You are the operator's delegate
(`CONTEXT.md`), so ask them once, before the first cell, which pushes are yours:
ordinary pushes to the loop's `saffron/SA-NNNN` branches, force-pushes to them
with a lease, and step 5's branch and draft PR. Every other branch, and every
gate-policy call, is asked separately, each time.

The driver is `.claude/skills/run-saffron-spec-loop/driver.py`, run with
`uv run` from the repo root (`--help` lists its commands). It starts no cell —
`saffron cell` takes a credential scoped to its own invocation — so you start
each cell and tell the driver what happened. Exit `0` means the command did
what it says, `1` everything else.

When a step's output surprises you, [GOTCHAS.md](GOTCHAS.md) is grouped by
step; it also says why this loop runs attended cells rather than `saffron batch`.

## 1. Snapshot the loop's order

```bash
uv run .claude/skills/run-saffron-spec-loop/driver.py snapshot
```

The live queue cannot drive this loop: `saffron queue` checks every spec
against a conflict set that includes open PRs, and this loop leaves every PR
open, so the queue empties after the first cell packages. `snapshot` writes the
loop's order once, to
`.saffron-loop/order.json` — parents before children, then priority, then id,
including a spec refused only for an unmet `depends_on` on a parent in the
order — and every later command reads that file.

An existing order is kept until `snapshot --force`, which rescans and keeps
every recorded outcome still true — a reviewable PR, a drop, an undecided cell.
A spec edited while its PR is open is held out of the new order and named.
`status` and `next` call an order **stale** when a spec file moved or changed or
a PR merged or closed, and `next` refuses a stale one. A spec queued since the
snapshot is not in it: re-snapshot to add it.

**Done when** `status` lists the specs you mean to run, reports nothing stale,
and the operator has seen `snapshot`'s table in your reply: each spec's title
and budget, the total, and every spec it refused.

## 1b. Review each spec before its first cell

Every spec in the order gets one spec review before any cell runs: one
background subagent per spec, dispatched together. Use `subagent_type:
spec-reviewer`, or `Plan` handed the body of
`.claude/agents/spec-reviewer.md` if the session started before that file
existed: `Plan` has no Edit or Write. Neither restricts Bash; the prompt
limits it to reading. Prompt
each with its spec's path, `base: origin/main`, and
`history: run it yourself`. `snapshot` reads the specs from the checkout, so
run this step from an up-to-date `main`; a spec that exists only on a branch
is reviewed at that branch's head.

Verify each blocker before acting on it: read its line at `origin/main`. A
verified blocker goes to the operator before that spec's cell, as a question:
fix the spec, run it as written, or drop it. Concerns and notes are kept for
step 5. A spec edited here changes its `spec_sha`, so run `snapshot --force`
after the edit merges.

**Only a spec that has not run.** Editing one whose pull request is already
open — which is what an operator wants to do after reading its review — stops
the ledger's task matching it, so `snapshot --force` holds it out of the order
*and* refuses every dependent, and the held-out spec loses its recorded
outcome, so step 3's `stack` silently omits its pull request. `status` names
the cost now (item 137); it did not on 2026-09-16, and the recovery was a
second pull request reverting the edit to the exact sha the task ran at. Hash
the file before committing the revert and check it matches the order's
`spec_sha`. If the edit must happen, let the pull request merge first.

**An edited spec is reviewed again before its cell.** The fix is spec text with
no reader, and the cell that runs into it pays. The loop's run 5 lost an attempt
to two tests an edit asked for that pass at base. It lost a repair turn to a
parametrised witness an edit offered (backlog item 159). Dispatch a second
`spec-reviewer` on the edited spec once the edit lands and `snapshot --force`
runs. Its `base` is the commit a cell would now be cut from, which is
`origin/main`, or the parent's pushed branch for a spec with `depends_on`.
Review the whole spec, not the edit. Checks 5 and 6 read it entire, and a report
whose six lines cover a diff is not one. Run 5's re-reviews also found a witness
stub answering every subnet alike (#304). Two notes named code seams that do not
exist (#306). Both sat in text the first review passed. An edited child needs
one re-review rather than two, and the parent-branch review below is that one.

Two kinds of blocker failed the backtest, and reading the line at base does
not filter them, because their premise holds there
(`docs/evidence/2026-09-14-spec-reviewer-backtest.md`; BACKLOG items 123–124). One is a
check 4 claim that the ceilings are below what similar cells spent; cells
finished inside the ceilings called too low. The other is a check 3 claim that a
witness is "already green at base" because the behaviour exists there; the cells
wrote witnesses that failed at base. Put either kind to the operator as a
forecast the backtest contradicted, not as a verified defect.

A spec with `depends_on` is reviewed at `origin/main` too, where its parent's
code does not exist yet, so a finding that rests on the parent is expected
there. Review it again at its parent's pushed branch
(`base: origin/saffron/<parent id>`) before its own cell starts.

**Done when** every spec in the order has a report with six check lines, and
every verified blocker has the operator's answer.

## 2. Run each spec

`uv run .claude/skills/run-saffron-spec-loop/driver.py next` names the next
spec, or exits 1 saying why none is left.

**One cell at a time, reviewing while the next runs.** A cell's worktree is cut
from the remote, not the checkout, so PR N can be reviewed on its branch while
cell N+1 runs. A spec with `depends_on` has its worktree cut from its parent's
branch, so it starts after the parent's review commits are pushed: until then
`next` names it as waiting and hands back the next spec that can start. Within
a priority, the order puts the parent with most descendants first, so its
children have something to run beside its review. `next` holds back a child
whose parent has no reviewable branch — rate-limited, decided otherwise, or
dropped — because `saffron cell` would cut it from main, and names the child it
held back.

### a. Start the cell in the background

```bash
PYTHONUNBUFFERED=1 SAFFRON_ALLOW_HOST_PROCESS=<listener> env CLAUDE_CODE_OAUTH_TOKEN="$(bash -c 'source ~/.secrets; printf %s "$CLAUDE_CODE_OAUTH_TOKEN"')" \
  uv run saffron cell .saffron/specs/SA-NNNN-*.md --repo . > /tmp/SA-NNNN.log 2>&1
```

`<listener>` is the process `docs/HOST-HARDENING.md` lets this host tolerate.
On a host that tolerates none, leave `SAFFRON_ALLOW_HOST_PROCESS=…` out
(GOTCHAS, Starting cells). Watch it with a Monitor:

```bash
tail -F /tmp/SA-NNNN.log | grep -E --line-buffered "$(uv run .claude/skills/run-saffron-spec-loop/driver.py pattern)"
```

`pattern` prints the phase lines plus every terminal state in the ontology's
closed set, anchored where the CLI prints one. A cell takes 30–60 minutes, and a
Monitor expires after 30. Re-arm it with `tail -n 0 -F` so it doesn't replay the
log. A silent Monitor ends nothing; only the process exit does (b).

### b. Record it once the process exits

The background task's completion notice says the process exited; a terminal
state in the log does not, because PACKAGE runs after it.

```bash
uv run .claude/skills/run-saffron-spec-loop/driver.py record SA-NNNN   # SA-NNNN  READY_FOR_REVIEW  #228
```

It reads the ledger, never the transcript (§4.3), prints what the cell spent
against the spec's budget, and exits 0 only for `READY_FOR_REVIEW`. Stop the
Monitor now: `tail -F` outlives the cell. A **decided** state — one in
`scheduler.DONE_STATES` — settles the spec for this loop, and only
`READY_FOR_REVIEW` joins the stack. A
state that decided nothing keeps the spec pending, and `next` moves past it.
Once the process has exited, an in-flight state is a **halt**: the cell stopped
at a ceiling and nothing decided the task. `record` says so, and a halt goes
to the operator (GOTCHAS, Recording).
`drop SA-NNNN --why "…"` takes a spec out for good.

### c. Review it

1. **The in-cell critic's findings** are in
   `~/.saffron/batches/v0/SA-NNNN/findings.json`: a list of lenses, each with
   `findings` carrying `severity`, `file`, `line` and `claim`, and an adequacy
   finding a `probe`. A blocker a lens withdrew after REBUT is in
   `rebuttal.json` beside it, with the implementer's argument.
2. **Independent review:** two background `general-purpose` subagents per PR,
   the Spec seat and the Standards seat, prompted from
   [REVIEW-PROMPT.md](REVIEW-PROMPT.md). The Spec seat's criterion walk is what
   finds the defects — in stack #233 each of four reviews found a witness that
   survived an edit breaking its line, after three clean lenses.
3. **Verify every finding yourself** before acting: read the line and re-run
   its probe. A finding's claim to have been verified is part of what you are
   reviewing.
4. **A diff that gets past a gate goes to the operator** as a question — keep
   it, spell it plainly, or exempt it — and the gate's hole is kept for step 5
   whatever they answer. The rest of the review carries on meanwhile.
5. **A real finding outside the spec's `touches`** is kept for step 5 — unless
   the fix is incomplete without it, which is a question for the operator.
6. **Fix on the branch, check, commit, push:**

   ```bash
   make check > /tmp/check.log 2>&1; echo "make exit: $?"; tail -3 /tmp/check.log
   git add <files> && git commit -m "review(SA-NNNN): <the defect, as a sentence>" && git push -q origin HEAD
   uv run .claude/skills/run-saffron-spec-loop/driver.py size SA-NNNN
   uv run .claude/skills/run-saffron-spec-loop/driver.py stack             # dry run
   ```

   `size` measures what was pushed, so it runs after the push; the PR is a
   draft, so a branch over its ceiling is still the operator's to answer. The
   dry `stack` finds a conflict between neighbours while the branch is fresh.

**Done when** each criterion has a file:line and a probe result, each finding is
fixed, answered, or kept, every witness the review added fails at the spec's
base with its imports inside the test, `size` reports the branch within its
ceiling or the operator has been asked, `make check` echoes `make exit: 0`, and
the commit is pushed.

## 3. Stack the pull requests

```bash
uv run .claude/skills/run-saffron-spec-loop/driver.py stack             # dry run
uv run .claude/skills/run-saffron-spec-loop/driver.py stack --execute   # gh stack link, then bases read back
```

The stack order is the loop's order rearranged so each child sits directly above
its parent. The dry run prints it, runs `git merge-tree` on every adjacent pair,
and shows the `gh stack link` command. `link` retargets each PR onto the one
below; its diff stays right and only what merging it would do changes. A
`CONFLICT` between neighbours, and a child whose parent is not in the stack,
go to the operator before linking (GOTCHAS, Stacking). Every PR stays a draft: ratifying is `gh pr ready <n>`, the
operator's.

**Done when** `--execute` reports every PR's base as the branch below it.

## 4. Chain the siblings — when the operator asks

Specs with no `depends_on` were cut from the default branch, so after linking
they are siblings rather than a chain.

```bash
uv run .claude/skills/run-saffron-spec-loop/driver.py rebase             # dry run: fork points, targets, the push
uv run .claude/skills/run-saffron-spec-loop/driver.py rebase --execute   # local rebase, then each layer's patch-id
```

It refuses a branch checked out in another worktree, records every branch's
SHA before moving any, restores all of them on a conflict, and prints the push
with each lease pinned to the recorded SHA. Run `make check` on the top branch,
then run the push: step 1's grant covers a leased force-push to the loop's
branches. It rewrites branches with open PRs, so show the operator its output.

**Done when** every layer reports `identical` or its range-diff has been read,
`make check` echoes `make exit: 0` on the top branch, and the operator has seen
the push run.

## 5. File what the reviews left

Findings kept in step 2 become a new `docs/backlog/NNN-slug.md` record each — the
frontmatter shape of any open item, next id = highest existing + 1 — placed in
`PRIORITY.md`'s tier index, with `uv run pytest tests/records -q` green before
committing. Each item a spec came from gets its frontmatter `status` / `closed`
/ `prs` (and `specs`/`commits` as applicable) set and a dated line added to
`## Record`. If the spec merged, retire it to `.saffron/specs/done/` (updating
the scheduler smoke test, `docs/agents/issue-tracker.md`) — an item whose
origin spec is in `done/` cannot stay `open`. They go in a standalone PR off
the default branch unless the operator says otherwise.

Every finding you verified that the in-cell critic did not raise, and that was
fixed or kept, is a change requested on the operator's behalf — a rejection:
append it to `.saffron/rejections.md` as its **Adding one** paragraph says, in
the same PR. A finding answered with no change rejected nothing. Those lines
are §8's evidence for which gate, `CLAUDE.md` line or lens comes next.

**Done when** every kept finding has an item, every spec's origin item names
its PR, and every fixed or kept finding the critic missed has a rejection line.
