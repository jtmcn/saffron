---
name: run-saffron-spec-loop
description: Run, review, fix and stack every active Saffron spec. Use when asked to run all specs, drive the whole spec queue, run the loop over the backlog, batch the specs, or produce a stack of PRs for review instead of merging each one.
---

# Run the Saffron spec loop, stacking the PRs

Drives every active spec through `saffron cell` → independent code review →
fixes, then links the resulting pull requests into one GitHub stack for a
final human review. **Nothing is merged.**

All paths are relative to the repo root (`/Users/jm/Code/saffron`).

The driver is `.claude/skills/run-saffron-spec-loop/driver.py`. It does not run
cells — `saffron cell` needs a credential scoped to its own invocation, so the
agent runs that directly and tells the driver what happened.

## Why a driver at all

`saffron queue` is computed against **open** pull requests, and this workflow
deliberately leaves them open. The moment the first cell packages, gate 0
refuses the rest. Measured by driving `build_queue` against this repo's two
real queued specs, with a **simulated** open pull request on `saffron/SA-0028`
(the PR number below is the simulation's, not a real one):

```
--- no open PRs ---
candidates: ['SA-0028', 'SA-0027'] refusals: []

--- SA-0028's PR now open, changing docs/BACKLOG.md ---
candidates: []
REFUSED: SA-0027…md -> touches overlaps open pull request …/pull/99's changed files: docs/BACKLOG.md
REFUSED: SA-0028…md -> an open pull request from another task already targets this spec: …/pull/99
```

**Zero candidates.** A loop that re-reads the queue each iteration runs one
spec, sees an empty queue, and reports success with work left undone. The
driver snapshots the run order once, before any pull request exists, and
everything afterwards reads that plan.

## Prerequisites

```bash
gh stack --version          # gh stack version 0.1.0 — the extension, required
uv run pytest --version     # the repo's own toolchain
```

If `gh stack` is missing: `gh extension install github/gh-stack`.

## 1. Snapshot the plan — before anything else

```bash
uv run .claude/skills/run-saffron-spec-loop/driver.py plan
```

```
plan: 2 spec(s), bottom of the stack first

  1. SA-0028  priority=1
  2. SA-0027  priority=2

written to .saffron-loop/plan.json

note: 1 spec(s) declare no depends_on, so their branches will be siblings
      cut from the default branch rather than a real chain. See SKILL.md, Gotchas.
```

Order is parents before children, then priority, then spec id. A spec refused
*only* for an unmet `depends_on` on another spec in the plan is included —
running the parent is what admits it. Every other refusal is printed and left
out. `--force` re-snapshots.

## 2. Loop, one spec at a time

```bash
uv run .claude/skills/run-saffron-spec-loop/driver.py next     # prints e.g. SA-0028; exit 1 when done
```

For each spec `next` names:

**a. Run the cell.** The token is scoped to this one command and must not
reach any other shell (`.envrc` deliberately does not load it):

```bash
env CLAUDE_CODE_OAUTH_TOKEN="$(bash -c 'source ~/.secrets; printf %s "$CLAUDE_CODE_OAUTH_TOKEN"')" \
  uv run saffron cell .saffron/specs/SA-0028-*.md --repo .
```

Run it in the background — a cell takes 30–60 minutes — and watch for phase
lines with a Monitor on the output file:

```
^(IMPLEMENT|GATE|REVIEW|REBUT|PACKAGE|READY|EXHAUSTED|NOT_IMPLEMENTED|PLAN_REJECTED|MERGE_FAILED|gates:|baseline:|ceilings:|teardown:)|Traceback
```

Exit codes are load-bearing: `0` reviewable, `1` the task did not make it,
`2` infrastructure failed.

**b. Record it.**

```bash
uv run .claude/skills/run-saffron-spec-loop/driver.py record SA-0028
```

Prints `<SPEC-ID>  <state>  #<pr>` and exits 0 only for `READY_FOR_REVIEW`.
Real output, from a spec this repo has actually run:

```
$ uv run .claude/skills/run-saffron-spec-loop/driver.py record SA-0013
SA-0013  MERGED  #51
```

Read from the ledger, never from the transcript (§4.3). Any state other than
`READY_FOR_REVIEW` exits 1 — that spec is out of the stack; keep going.

If `record` errors (`no task for SA-00NN at <sha> — did the cell run?`), the
spec's state stays unset and **`next` will hand you the same spec again**.
Re-run the cell once, or take it out of the loop deliberately:

```bash
uv run .claude/skills/run-saffron-spec-loop/driver.py skip SA-0028 --why "cell died in PREFLIGHT twice"
```

Never re-run a cell more than once on the same failure — that is an hour and
real money per pass.

**c. Address the in-cell critic.** Findings are at
`~/.saffron/batches/v0/<SPEC-ID>/findings.json`:

```bash
python3 -c "
import json
for lens in json.load(open('/Users/jm/.saffron/batches/v0/SA-0028/findings.json')):
    for f in lens['findings']:
        print(f\"--- {f['lens']} / {f['severity']} / {f['file']}:{f['line']}\")
        print(f['claim'])
"
```

Check out the branch, verify each claim against the code before acting on it,
fix, and commit on the branch. `git checkout saffron/SA-0028`.

**d. Independent review.** Invoke `superpowers:requesting-code-review` and
dispatch one `general-purpose` subagent per PR with the full spec text, the
git range, and an instruction to mutation-test its own findings. Fix what
survives verification.

**e. Verify and push.**

```bash
make check > /tmp/check.log 2>&1; echo "make exit: $?"; tail -3 /tmp/check.log
git add -A && git commit -q -m "review(SA-0028): <the defect, not the file>" && git push -q origin HEAD
```

Then `next` again. **Do not merge.**

## 3. Stack the pull requests

```bash
uv run .claude/skills/run-saffron-spec-loop/driver.py stack            # dry run
uv run .claude/skills/run-saffron-spec-loop/driver.py stack --execute  # links them on GitHub
```

With nothing run yet it refuses, which is the state you will see first:

```
$ uv run .claude/skills/run-saffron-spec-loop/driver.py stack
error: a stack needs two or more reviewable pull requests; have 0
```

Once two specs are `READY_FOR_REVIEW` the dry run prints the plan and the
command. **The block below was produced by forcing two merged specs' states in
`plan.json` by hand** — the PR numbers are real, the stack has never been built:

```
stack, bottom to top:
  #82  SA-0025  (saffron/SA-0025)
  #84  SA-0026  (saffron/SA-0026)

  gh stack link 82 84

not passing --open: PACKAGE opens drafts on purpose (DESIGN.md §5.7),
and ratifying one is `gh pr ready <n>` — the operator's call, not this
script's.

(dry run — pass --execute to run it)
```

`gh stack link` is the right command because Saffron's PACKAGE **already
opened** each pull request. `link` takes existing PR numbers bottom-to-top,
does not rely on local stack state, and never removes existing PRs.

Check the result. **Not `gh stack view`** — it only views the stack containing
the *current* branch, and `link` keeps no local tracking, so from anywhere else
it prints `✗ current branch "…" is not part of a stack` and looks like a
failure. Read the PRs themselves:

```bash
gh pr view 86 --json number,isDraft,baseRefName,headRefName \
  -q '{n:.number,draft:.isDraft,base:.baseRefName,head:.headRefName}'
```

```
{"base":"main","draft":false,"head":"joel/spec-loop-skill","n":86}
```

Run it per PR and record `baseRefName` **before and after** `--execute`:
whether `link` retargets an existing PR's base is the one thing about it this
skill has not measured. Then hand the operator the stack URL `link` printed.

## Exit codes

`0` the command did what it says; `1` everything else — a usage error, an empty
plan, a spec that is not reviewable, or `next` with nothing left. The driver
never returns `2`: `saffron/cli.py` reserves that for infrastructure, and this
script is not it.

## Status at any point

```bash
uv run .claude/skills/run-saffron-spec-loop/driver.py status
```

```
  SA-0028  pending
  SA-0027  pending

0/2 reviewable
```

## Gotchas

- **The queue collapses after the first PR opens.** See the measurement above.
  Never re-derive the run order mid-loop; that is the entire reason
  `.saffron-loop/plan.json` exists. `saffron cell` is the attended path and
  does not run gate 0's overlap check, so a spec refused there still runs.

- **Independent specs make sibling branches, not a stack.** Saffron cuts each
  branch from the default branch. Adopting two siblings really does mark the
  upper one as needing a rebase — verified locally:

  ```
  $ gh stack init tmp/sib-a tmp/sib-b
  ✓ Adopted 2 branches: main ← tmp/sib-a ← tmp/sib-b
  $ gh stack view --short
  » tmp/sib-b ⚠ (current)
  ├ tmp/sib-a
  └ main
  ```

  `gh stack rebase --no-trunk` chains them (`✓ Rebased tmp/sib-b onto
  tmp/sib-a`) but **rewrites branches Saffron has already pushed**, so every
  PR's commits change and `gh stack push` force-with-leases them. Two specs
  that both touch `docs/BACKLOG.md` will usually conflict. Prefer letting
  Saffron stack for real: a spec with `depends_on` gets its worktree cut from
  the parent's branch and its PR opened against it, so the chain already
  exists and no rebase is needed. For genuinely independent specs, link them
  and leave them based on the default branch — a "stack" of siblings is a
  review convenience, not a claim about the code.

- **`gh stack submit` opens an interactive editor** and cannot be driven by an
  agent. `--auto` skips it but creates *new* PRs. Since PACKAGE already opened
  them, `gh stack link` is the non-interactive path. Don't reach for `submit`.

- **Do not pass `--open`.** It flips every PR in the stack from draft to ready
  for review. PACKAGE opens drafts deliberately (§5.7).

- **`make check | tail` masks make's exit status.** Redirect to a file and echo
  `$?` instead. And `ruff format` *rewrites* files then reports failure — a
  second run passes. Always re-run before believing a red result.

- **Every spec that runs will produce findings that are the spec's fault, not
  the agent's.** Three consecutive specs shipped with a `touches` list that
  boxed the agent in. When a review finding says the agent gamed a check, read
  the spec's `touches` before blaming the diff.

- **`gh stack unstack --local` with no argument is not the no-op it looks
  like.** Run from `main` with no stack of your own, it still finds "the active
  stack" and drops its local tracking — it silently untracked an unrelated,
  already-merged stack (#67) during this skill's own authoring. Pass the stack
  number explicitly, or check `gh stack view --short` first. Recovery is
  `gh stack checkout <n>`, which refetches the stack from GitHub; nothing on
  the remote is touched by `--local`.

- **`.saffron-loop/` is gitignored.** Run state, not source. A cell never sees
  it — the mirror is a `git clone --mirror`, so an untracked file cannot reach
  one — but it must never ride along in a review fix's commit either.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `error: no plan at .saffron-loop/plan.json — run \`plan\` first` | Run `plan`. It refuses to overwrite; use `--force` to re-snapshot. |
| `plan` prints `nothing to run: no candidate specs` | Every spec is already done at its current `spec_sha`, or all are refused — the refusals are printed under the plan. |
| `record` says `no task for SA-00NN at <sha> — did the cell run?` | The spec file was edited after the cell ran, so its `spec_sha` moved. Re-run the cell, or revert the edit. |
| `CLAUDE_CODE_OAUTH_TOKEN is unset` | The token must be scoped to the `saffron cell` invocation itself. Refresh with `claude setup-token`. |
| Cell exits 2 | Infrastructure, not the task. Check `container system status` and that the images in `CLAUDE.md` are built. |
| `gh stack link` rejects an argument | An argument already belongs to a different stack. `gh stack view --json` shows current tracking; `gh stack unstack --local <n>` clears local state for that stack without touching GitHub. |
| `gh stack view` shows a stack you did not create | Local tracking from an earlier session. It is read-only information; leave it alone unless it collides. |

## Verified

Against this repo at `7ab27cf`, 2026-09-01.

**Run, output reproduced above verbatim:** `plan` (including a throwaway spec
touching `DESIGN.md`, to prove the `protected` refusal fires), `next`,
`record SA-0013` (ten ledger rows at one sha — it picks the `MERGED` one
carrying `#51`, not the `NOT_IMPLEMENTED` row after it), `skip`, `status`,
`stack` with nothing reviewable, `gh pr view --json`, and the
`gh stack init` / `view --short` / `view --json` / `rebase --no-trunk` /
`unstack --local` sequence on throwaway local branches.

**Run, output labelled above as reconstructed:** the populated `stack` dry run
(states forced in `plan.json` by hand; PR numbers real) and the queue-collapse
measurement (real `build_queue`, simulated open pull request).

**Not run:** `driver.py stack --execute`, and therefore `gh stack link` itself.
It needs two open Saffron pull requests and none existed at authoring time.
Everything said about it comes from `gh stack link --help`. In particular,
whether it retargets an existing PR's base branch is **unmeasured** — record
`baseRefName` before and after the first time you use it.
