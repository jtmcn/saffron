# Gotchas and troubleshooting

Grouped by the step in `SKILL.md` they belong to. Each entry leads with what to
do; the measurement behind it follows.

## Starting cells

- **Scope the token to the one command.** `.envrc` deliberately does not load
  `CLAUDE_CODE_OAUTH_TOKEN`: direnv would export it into every shell here. When
  a session's guard refuses `source ~/.secrets` (a worktree-isolated session
  did, 2026-09-12), write a token-only file under `umask 077` —
  `sed -n 's/^export \(CLAUDE_CODE_OAUTH_TOKEN=\)/\1/p' ~/.secrets > <scratch>/cell.env`
  — pass it with `uv run --env-file`, and delete it when the loop ends.
  `~/.secrets` itself holds other keys, so it is never the `--env-file`.
- **Put the host's preflight allowlist on the invocation.** A development host
  that tolerates a listener (`docs/HOST-HARDENING.md`) needs
  `SAFFRON_ALLOW_HOST_PROCESS=<name>` on every `saffron cell`. The delegate's shell
  does not run direnv, and preflight's failure names the ports, never the
  missing variable.
- **`PYTHONUNBUFFERED=1` on every cell.** Redirected to a file, the CLI's
  stdout is block-buffered: measured, the log stayed at 0 bytes while the cell
  ran and the batch directory filled.
- **A closed rate-limit window is the account's, not the spec's.** Start no
  cell before the reopen time a `rate limit:` line printed. A limit can land
  after the work is done: SA-0028's first cell had green gates and hit it in
  REBUT at $7.92 of $14. PACKAGE never ran, so there was no branch, and the
  next cell started over. The loop's cost is not bounded by the specs' budgets.
- **`baseline: … tests=fail` on every cell is expected.** One host-only test
  fails in every cell (backlog item 106); baseline subtraction cancels it.

## Recording

- **A state that decided nothing leaves the spec pending** with `last_state`
  set, and `next` walks past it so a closed rate-limit window cannot loop
  forever:
  - `RATE_LIMITED` (which is not `EXHAUSTED`): `next --again` once the window
    reopens — the cell's own `rate limit: … window reopens HH:MM local` line
    says when. The next cell starts from `base_sha`.
  - A state in `reconcile.IN_FLIGHT_STATES`: the cell is still running; wait
    for the process to exit.
- **A decided state is final for this loop.** `EXHAUSTED`, `NOT_IMPLEMENTED`
  and the rest of `scheduler.DONE_STATES` leave the stack and are not re-run. A
  cell that exits 2, or leaves `record` with no task, gets one more cell,
  started by its spec path; after that, `drop`. A cell is about an hour and
  real money. A rate limit does not count: nothing about the task failed.

## Reviewing

- **Read the spec's `touches` before blaming the diff.** Three consecutive
  specs shipped with a `touches` list that boxed the agent in; a finding that
  the agent gamed a check was the spec's fault each time.
- **Read every alias and exemption in the diff as a way past a gate.**
  SA-0077's agent bound pytest's skip to a private name so `integrity`'s
  substring scan would not fire, and said so in a comment; the gate passed and
  no lens raised it (backlog item 112).
- **Redirect `make check` to a file and echo `$?`.** `make check | tail` reports
  tail's status. `ruff format` rewrites files and then reports failure: run it
  again before believing red.
- **Stage review commits by name.** `.saffron-loop/` is gitignored loop state and
  stays out of every commit.

## Stacking

- **`stack` links with `gh stack link`**, which works on the PRs PACKAGE
  already opened and keeps no local tracking — the `gh-stack` skill's own path
  for branches another tool manages. `submit` works from local stack state and
  force-pushes every branch.
- **Link without `--open`.** It flips every draft PACKAGE opened on purpose
  (§5.7).
- **`link` retargets bases.** Each PR's diff stays right, because GitHub
  computes it from the merge base; what changes is what merging it would do.
  Siblings that both append to one document collide on the number as well as
  the text: SA-0027 and SA-0028 both appended `## 34.` to `docs/BACKLOG.md`,
  and the PR pages looked clean while `git merge-tree` reported a `CONFLICT`.
  `stack` runs that check on every adjacent pair. A conflict goes to the
  operator before linking: resolving it is a hand rebase of the upper branch
  onto the lower one, renumbering, a grep of the code for comments citing the
  old number, and a force-push they approve.
- **Read the bases back after linking.** A numeric first argument to `link` is
  taken as a stack number when a stack with that number exists, and the rest
  are appended to it. `stack --execute` reads every PR's base and flags one that
  is not the branch below it.
- **Read a linked stack through its PRs.** `gh stack view` shows only the stack
  containing the current branch, and a `link`-created stack has no local
  tracking until `gh stack checkout <n>`.
- **Pass the stack number to `gh stack unstack --local`.** Without one, run
  from `main`, it untracked an unrelated merged stack (#67). `gh stack checkout
  <n>` restores local tracking; nothing on GitHub changes.

## Rebasing

- **Use `driver.py rebase` for siblings.** `gh stack rebase` on a
  `link`-created stack stopped at the first sibling — `could not determine the
  previous base of saffron/SA-0076 after saffron/SA-0075 changed` — and
  restored every branch (stack #233, 2026-09-13). What worked, and what
  `rebase` does: take each layer's fork point before moving anything,
  `git rebase --onto <layer below> <fork point> <branch>` bottom to top, and
  compare each layer's patch-id before and after.
- **The push needs the operator's approval, every time.** It rewrites branches
  with open PRs; `rebase` prints it with each lease pinned to the recorded SHA.

## Troubleshooting

| Symptom | What to do |
|---|---|
| `no order at .saffron-loop/order.json` | Run `snapshot`. A leftover `plan.json` is the previous driver's file; delete it. |
| `next` or `status` says the order is stale | A spec moved or was edited, or a PR merged or closed since the snapshot. `snapshot --force`; it keeps every recorded outcome still true. |
| `next`: `held back SA-NNNN: its parent … so a cell would cut it from main` | The parent has no reviewable branch. `next --again` once a rate-limited parent's window reopens; `drop` the child otherwise. |
| `snapshot` prints `nothing to run: no candidate specs` | Every spec is done at its current `spec_sha`, or refused; the refusals are printed. |
| `record`: `no task for SA-NNNN at <sha>` | The spec was edited after its cell ran. Re-run the cell, or revert the edit. |
| `CLAUDE_CODE_OAUTH_TOKEN is unset` | Scope it to the `saffron cell` invocation (Starting cells); refresh with `claude setup-token`. |
| Cell exits 2 | Read the last lines first: `rate limit: rejected` means wait for the window. Otherwise `container system start`, then `container image list`. |
| Preflight fails naming host ports | The allowlist variable is missing from the invocation (Starting cells). |
| `next`: `nothing untouched left` | Every pending spec already had a cell that decided nothing. `next --again` after a reopened rate-limit window; `drop` otherwise. |
| `rebase` refuses: local branch differs from origin | Push or reset the local branch first; the rebase starts from what is on GitHub. |
