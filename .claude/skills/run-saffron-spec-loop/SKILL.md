---
name: run-saffron-spec-loop
description: Use when running the Saffron spec loop — every queued spec through an attended cell and an independent review, stacked as draft pull requests instead of merged.
---

# Run the Saffron spec loop

Every queued spec goes through an attended `saffron cell`, an independent
review, and review commits; the pull requests are then linked into one stack
for the operator. **Nothing is merged.** You are the operator's delegate
(`CONTEXT.md`), so ask them once, before the first review push, for ordinary
pushes to the loop's `saffron/SA-NNNN` branches. Every force-push and every
gate-policy call is asked separately, each time.

The driver is `.claude/skills/run-saffron-spec-loop/driver.py`, run with
`uv run` from the repo root (`--help` lists its commands). It starts no cell —
`saffron cell` takes a credential scoped to its own invocation — so you start
each cell and tell the driver what happened. Exit `0` means the command did
what it says, `1` everything else.

When a step's output surprises you, [GOTCHAS.md](GOTCHAS.md) is grouped by
step.

## 1. Snapshot the run order

```bash
uv run .claude/skills/run-saffron-spec-loop/driver.py snapshot
```

The live queue cannot drive this loop: `saffron queue` refuses every spec whose
`touches` overlap an open PR, and this loop leaves every PR open, so the queue
empties after the first cell packages. `snapshot` writes the run order once, to
`.saffron-loop/order.json` — parents before children, then priority, then id,
including a spec refused only for an unmet `depends_on` on a parent in the
order — and every later command reads that file.

An existing order is kept until `snapshot --force`, which rescans and keeps
every recorded outcome still true — a reviewable PR, a drop, an undecided cell.
`status` and `next` call an order **stale** when a spec file moved or changed or
a PR merged or closed, and `next` refuses a stale one. A spec queued since the
snapshot is not in it: re-snapshot to add it.

**Done when** `status` lists the specs you mean to run and reports nothing
stale.

## 2. Run each spec

`uv run .claude/skills/run-saffron-spec-loop/driver.py next` names the next
spec, or exits 1 saying why none is left.

**One cell at a time, reviewing while the next runs.** A cell's worktree is cut
from the remote, not the checkout, so PR N can be reviewed on its branch while
cell N+1 runs. A spec with `depends_on` has its worktree cut from its parent's
branch, so it starts after the parent's review commits are pushed; when `next`
names such a child first, it says so, and the next independent spec can be
started by its path meanwhile. `next` skips a child whose parent has no
reviewable branch — rate-limited, decided otherwise, or dropped — because
`saffron cell` would cut it from main, and names the child it skipped.

### a. Start the cell in the background

```bash
PYTHONUNBUFFERED=1 env CLAUDE_CODE_OAUTH_TOKEN="$(bash -c 'source ~/.secrets; printf %s "$CLAUDE_CODE_OAUTH_TOKEN"')" \
  uv run saffron cell .saffron/specs/SA-NNNN-*.md --repo . > /tmp/SA-NNNN.log 2>&1
```

A host that tolerates a listener also puts its `SAFFRON_ALLOW_HOST_PROCESS` on
this command (GOTCHAS, Starting cells). Watch it with a Monitor:

```bash
tail -F /tmp/SA-NNNN.log | grep -E --line-buffered "$(uv run .claude/skills/run-saffron-spec-loop/driver.py pattern)"
```

`pattern` prints the phase lines plus every terminal state in the ontology's
closed set, unanchored, since the CLI prints a state after a padded spec id. A
cell takes 30–60 minutes.

### b. Record it once the process exits

The background task's completion notice says the process exited; a terminal
state in the log does not, because PACKAGE runs after it.

```bash
uv run .claude/skills/run-saffron-spec-loop/driver.py record SA-NNNN   # SA-NNNN  READY_FOR_REVIEW  #228
```

It reads the ledger, never the transcript (§4.3), and exits 0 only for
`READY_FOR_REVIEW`. A **decided** state — one in `scheduler.DONE_STATES` —
settles the spec for this loop, and only `READY_FOR_REVIEW` joins the stack. A
state that decided nothing (a rate limit, a cell still in flight) keeps the
spec pending, and `next` moves past it (GOTCHAS, Recording).
`drop SA-NNNN --why "…"` takes a spec out for good.

### c. Review it

1. **The in-cell critic's findings** are in
   `~/.saffron/batches/v0/SA-NNNN/findings.json`: a list of lenses, each with
   `findings` carrying `severity`, `file`, `line` and `claim`.
2. **Independent review:** one background `general-purpose` subagent per PR,
   prompted from [REVIEW-PROMPT.md](REVIEW-PROMPT.md). Its criterion walk is
   what finds the defects — in stack #233 each of four reviews found a witness
   that survived an edit breaking its line, after three clean lenses.
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
   ```

**Done when** each criterion has a file:line and a probe result, each finding is
fixed, answered, or kept, `make check` echoes `make exit: 0`, and the commit is
pushed.

## 3. Stack the pull requests

```bash
uv run .claude/skills/run-saffron-spec-loop/driver.py stack             # dry run
uv run .claude/skills/run-saffron-spec-loop/driver.py stack --execute   # gh stack link, then bases read back
```

The stack order is the run order rearranged so each child sits directly above
its parent. The dry run prints it, runs `git merge-tree` on every adjacent pair,
and shows the `gh stack link` command. `link` retargets each PR onto the one
below; its diff stays right and only what merging it would do changes. A
`CONFLICT` between neighbours goes to the operator before linking (GOTCHAS,
Stacking). Every PR stays a draft: ratifying is `gh pr ready <n>`, the
operator's.

**Done when** `--execute` reports every PR's base as the branch below it.

## 4. Chain the siblings — when the operator asks

Specs with no `depends_on` were cut from the default branch, so after linking
they are siblings rather than a chain.

```bash
uv run .claude/skills/run-saffron-spec-loop/driver.py rebase             # dry run: fork points, targets, the push
uv run .claude/skills/run-saffron-spec-loop/driver.py rebase --execute   # local rebase, then each layer's patch-id
```

It records every branch's SHA before moving any, restores all of them on a
conflict, and prints the push with each lease pinned to the recorded SHA. Run
`make check` on the top branch, then ask the operator before running the push:
it rewrites branches with open PRs.

**Done when** every layer reports `identical` or its range-diff has been read,
`make check` echoes `make exit: 0` on the top branch, and the operator has
approved and seen the push run, or declined it.

## 5. File what the reviews left

Findings kept in step 2 become items in `docs/BACKLOG.md`, in its format and
placed in its tier index, and each item a spec came from gets its `Status` line
updated with the PR and the stack. They go in a standalone PR off the default
branch unless the operator says otherwise.

**Done when** every kept finding has an item and every spec's origin item names
its PR.
