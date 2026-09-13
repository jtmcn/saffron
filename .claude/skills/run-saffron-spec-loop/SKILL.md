---
name: run-saffron-spec-loop
description: Use when asked to run every queued Saffron spec, drive the spec queue through attended cells, or produce a stack of spec pull requests for review instead of merging each one.
---

# Run the Saffron spec loop

Every queued spec goes through an attended `saffron cell`, an independent
review, and review commits; the pull requests are then linked into one stack
for the operator. **Nothing is merged.** You are the operator's delegate
(`CONTEXT.md`): every push, force-push and gate-policy call is theirs.

The driver: `D=.claude/skills/run-saffron-spec-loop/driver.py`, run as
`uv run $D <command>` from the repo root (`--help` lists them). It starts no
cell — `saffron cell` takes a credential scoped to its own invocation — so you
start each cell and tell the driver what happened. Exit `0` means the command
did what it says, `1` everything else.

When a step's output surprises you, [GOTCHAS.md](GOTCHAS.md) is grouped by
step.

## 1. Snapshot the run order

```bash
uv run $D snapshot
```

The live queue cannot drive this loop: `saffron queue` refuses every spec whose
`touches` overlap an open PR, and this loop leaves every PR open, so the queue
empties after the first cell packages. `snapshot` writes the order once, to
`.saffron-loop/order.json` — parents before children, then priority, then id,
including a spec refused only for an unmet `depends_on` on a parent in the
order — and every later command reads that file.

An existing order is kept until `snapshot --force`. `status` and `next` call an
order **stale** when a spec file moved or changed or a PR merged or closed, and
`next` refuses a stale one.

**Done when** `status` lists the specs you mean to run and reports nothing
stale.

## 2. Run each spec

`uv run $D next` names the next spec, or exits 1 saying why none is left.

**One cell at a time, reviewing while the next runs.** A cell's worktree is cut
from the remote, not the checkout, so PR N can be reviewed on its branch while
cell N+1 runs. A spec with `depends_on` starts after its parent's review
commits are pushed, because its worktree is cut from the parent's branch.

### a. Start the cell in the background

```bash
PYTHONUNBUFFERED=1 env CLAUDE_CODE_OAUTH_TOKEN="$(bash -c 'source ~/.secrets; printf %s "$CLAUDE_CODE_OAUTH_TOKEN"')" \
  uv run saffron cell .saffron/specs/SA-NNNN-*.md --repo . > /tmp/SA-NNNN.log 2>&1
```

A host that tolerates a listener also puts its `SAFFRON_ALLOW_HOST_PROCESS` on
this command (GOTCHAS, Starting cells). Watch it with a Monitor:

```bash
tail -F /tmp/SA-NNNN.log | grep -E --line-buffered "$(uv run $D pattern)"
```

`pattern` prints the phase lines plus every terminal state in the ontology's
closed set, unanchored, since the CLI prints a state after a padded spec id. A
cell takes 30–60 minutes.

### b. Record it once the process exits

```bash
uv run $D record SA-NNNN        # SA-NNNN  READY_FOR_REVIEW  #228
```

It reads the ledger, never the transcript (§4.3), and exits 0 only for
`READY_FOR_REVIEW`; any other decided state leaves the spec out of the stack.
A state that decided nothing — a rate limit, a cell still in flight — keeps it
pending and `next` moves past it (GOTCHAS, Recording). `drop SA-NNNN --why "…"`
takes a spec out for good.

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
   it, spell it plainly, or exempt it. It is policy, not code.
5. **Fix on the branch, check, commit, push:**

   ```bash
   make check > /tmp/check.log 2>&1; echo "make exit: $?"; tail -3 /tmp/check.log
   git add <files> && git commit -m "review(SA-NNNN): <the defect, as a sentence>" && git push -q origin HEAD
   ```

Keep every real finding outside the spec's `touches` for step 5.

**Done when** each criterion has a file:line and a probe result, each finding is
fixed, answered, or kept, `make check` is green, and the commit is pushed.

## 3. Stack the pull requests

```bash
uv run $D stack             # dry run: the order, merge-tree per adjacent pair, the command
uv run $D stack --execute   # gh stack link, then every PR's base read back
```

The order puts each child directly above its parent. `link` retargets each PR
onto the one below; its diff stays right and only what merging it would do
changes. Siblings — specs with no `depends_on` — were cut from the default
branch, so a `CONFLICT` between neighbours in the dry run is resolved before
the stack is handed over (GOTCHAS, Stacking). Every PR stays a draft: ratifying
is `gh pr ready <n>`, the operator's.

**Done when** `--execute` reports every PR's base as the branch below it.

## 4. Chain the siblings — when the operator asks

```bash
uv run $D rebase            # dry run: each layer's fork point and target, and the push
uv run $D rebase --execute  # rebases locally, then compares each layer's patch-id
```

It records every branch's SHA before moving any, restores all of them on a
conflict, and prints the push with each lease pinned to the recorded SHA. The
push rewrites branches with open PRs, so run `make check` on the top branch and
ask the operator before running it.

## 5. File what the reviews left

Findings kept in step 2 become items in `docs/BACKLOG.md`, in its format and
placed in its tier index, and each item a spec came from gets its `Status` line
updated with the PR and the stack. They go in a standalone PR off the default
branch unless the operator says otherwise.

**Done when** every kept finding has an item and every spec's origin item names
its PR.
