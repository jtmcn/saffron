# The two boundaries — design

Sub-project SP-1 of closing out v0.5's backlog. Items 11 and 12, together,
because they are the same question asked twice: **what tree is a task actually
about, and who is allowed to have written it.**

> **Citations:** a bare `§` cites `DESIGN.md`, per repo convention. This spec's
> own sections are cited as *part N*.

Both items are design decisions `docs/BACKLOG.md` deliberately left open, and
both block §4.2's scheduler: a scheduler cannot start a task unattended until it
knows what base to cut it from, and cannot trust a gate result whose runner the
cell supplied.

## What was measured

Run, not reasoned. Two claims below were re-measured against the code rather
than read out of the backlog, and one of them found a case the backlog does not
name.

**`github_slug` against five real remote shapes** (`uv run python`, this tree):

| Input | Returns |
|---|---|
| `/Users/joel/Code/saffron` | `Code/saffron` |
| `git@gitlab.com:group/owner/repo.git` | `owner/repo` |
| `https://github.com/jtmcn/saffron.git` | `jtmcn/saffron` ✓ |
| `git@github.com:jtmcn/saffron.git` | `jtmcn/saffron` ✓ |
| `https://example.com/repo` | `example.com/repo` |

The last row is not in item 11. With only one path segment, `_SLUG`
(`saffron/phases/package.py:31`) takes the **host** as the owner — so a remote
that is not a forge at all still yields a plausible-looking `owner/repo`, and
`gh` is handed a repository that cannot exist. Three of five inputs return a
wrong answer rather than refusing.

**The base asymmetry, in this working copy.** `local HEAD`, `local main` and the
remote's default-branch head are all `3d4df2c` right now — which is exactly the
one configuration item 11 says the "provably redundant skip" is reachable from:
a checkout sitting on an up-to-date default branch. It stops being true the
moment this spec is committed to a branch, and every task started from here
after that point is cut from a tree the remote has never seen.

**Read from the code, not run** — flagged as such, per repo convention:
`cli.py:114` sets `base_sha` from `git rev-parse HEAD` in the invoking repo,
while `package.py:485-491` fetches the remote's default branch and compares
against that; the baseline suite runs in the same cell and the same worktree as
head (`session.py:607`); and this repo's `gate_config` is
`["pyproject.toml", ".saffron/**"]`, which does not cover `conftest.py`.

## The shape of the answer

One invariant, stated in §5.4, that both parts serve:

> **Anything that changes what the suite measures must appear in the patch a
> human reads.**

Not *the cell cannot lie*. It can, and a design that assumes otherwise is how
v0.5 got a cell where every control reported green and none was connected
(Appendix I). The achievable property is weaker and worth more: a lie has to be
**visible in the diff**, where the reviewer and `integrity` both already look.

Item 12's two candidate halves each close a different route to an invisible
change, so both are built. Neither makes the cell trustworthy; together they
make it *legible*.

## 1. The base is the remote's default-branch head

§5.7 is silent on where `base_sha` comes from. It now says: the head of the
remote's default branch, read at task start.

### 1.1 The mechanism already exists, one phase too late

PACKAGE does this today at `package.py:485-491` — `default_branch(url, cwd=mirror)`
reads the remote's symbolic HEAD, `git fetch url refs/heads/<default>` lands it
in the mirror, `rev-parse FETCH_HEAD` names it. The change is to run that at task
start, before `prepare_worktree`, and to set `CellSpec.base_sha` from it.

Item 11 is therefore an asymmetry rather than a missing feature: one end reads
the invoking checkout, the other reads the remote, and every consequence it
lists falls out of making both ends read the same source.

- `needs_reverification(fetch_head, base_sha)` is false in the common case, so
  the redundant-suite skip stops being reachable only by accident.
- `git apply --3way` applies onto a tree the default branch has actually seen,
  so `MERGE_FAILED` stops being an artifact of where the operator was standing.

### 1.2 The fetch must happen at task start, not only at package time

`ensure_mirror` clones from the **local working copy** (`repos/mirror.py:39`),
so the mirror's refs are the local repo's. If local `main` is behind the remote,
the remote's head is not an object the mirror holds and `prepare_worktree` fails
on a base it cannot check out. The fetch is therefore part of cell construction,
not a PACKAGE-only step. §5.1's *"the mirror is the only remote anything
downstream ever reads"* is unchanged — the mirror is where the fetch lands.

### 1.3 What it costs, stated rather than discovered

1. **Network at task start.** Already true (`ensure_mirror`, the proxy), so this
   moves *when* an unreachable remote fails, not whether. Failing before the
   cell starts is the better end.
2. **Uncommitted and unpushed local work leaves a task's base.** Today, running
   from a dirty feature branch silently includes it. This is the change most
   likely to surprise an operator at the terminal, and it is the property §4.2
   requires: a task's base must not depend on where the operator was standing,
   or two tasks queued the same night are cut from different trees for no
   recorded reason.

The alternative — keep `HEAD`, make PACKAGE compare against it too — is
symmetric and needs no network. It is rejected because it makes a task's base
unreproducible from the ledger: nothing records what the working copy happened
to be at the time.

## 2. Gates come from `base_sha`, not from `/work`

`.saffron/gates/` is copied out of the mirror at `base_sha` into its own
read-only mount (`/gates`), and `CellExecutor` (`gates/runner.py:83`) execs from
there rather than from `WORKTREE_MOUNT`. An in-cell edit to a gate — committed
or not — no longer reaches the runner.

### 2.1 It closes a baseline drift nothing had recorded

The baseline suite runs in the same cell and the same worktree as head
(`session.py:607`), before the agent starts. So today the baseline runs the
**base tree's** gates and head runs whatever gates are in `/work` by then: a
task that edits `tests.py` changes what the two subtracted sides mean.

That is suite drift by construction — the identical shape item 11 flags for
`reverify`'s missing `thread_env` (part 5) — and pinning gates to `base_sha`
makes both sides provably the same executable. This is not why item 12 was
written, and it is the stronger of the two reasons.

### 2.2 A task whose job is to change a gate

It is judged by the pre-change gate, and the new gate takes effect for the next
task. This is correct and it must be **written down in §5.4**, because it reads
as a bug the first time `SA-0002` runs and someone finds their new gate did not
fire on its own patch. The edit still lands in the patch, and `integrity`'s
`gate_config` check still flags it for a human.

## 3. The suite does not run on a dirty worktree

`git status --porcelain` inside the cell, before the gate suite. Non-empty means
the tree being measured is not the tree the patch contains — `worktree.export_patch`
diffs `base_sha..HEAD` while `CellExecutor` execs against `/work` — so **any**
uncommitted change is absent from `scope`, from `integrity` and from the
packaged patch while being fully live for the suite.

Low disruption: §4.3 already measures doneness from commits, so an uncommitted
tree at gate time is already a mistake.

**On a dirty tree the attempt gets one repair turn** telling it to commit its
work, then the suite runs. Still dirty on the second look ends the attempt. The
turn is worth its cost because this is an honest mistake a capable agent will
make at least once before the prompt is tuned, and burning an attempt on it
teaches nothing.

Worth noting rather than relying on: this is a gate-shaped failure the agent
**cannot pre-check itself**, which makes it a candidate scenario for SP-4's
campaign, where GATE ⇄ REPAIR has never once fired (item 9, principle 49).

## 4. What stays open, and why it is stated rather than closed

A **committed** `conftest.py` whose `pytest_collection_modifyitems` drops a test
only when `config.option.collectonly` is false still defeats `census`:
enumeration reports a name the run never executes, `census` passes because the
name is collected, `tests` passes because the test never ran.

Parts 2 and 3 make that edit visible in the patch. Neither makes it fail, and
core cannot: collection happens inside the repo's own Python, and "what is a
collection hook" is language knowledge §2.1 keeps out of core.

The narrowing is repo-shaped and costs one line of YAML — add `**/conftest.py`
to `.saffron/policy.yaml`'s `gate_config`, and `integrity` fails any diff
touching it unless the spec's `touches` declares it. Zero core code. It does not
stop the lie; it routes the lie to a person, which is all this layer was ever
going to do.

The honest statement, for the backlog and for §5.4: **`census` buys exactness
against an honest suite; parts 2 and 3 buy visibility against a dishonest one.
Neither buys integrity, and no diff-shaped check will.**

## 5. The four smalls

All from item 11, all PACKAGE-adjacent.

1. **`github_slug` refuses instead of guessing.** Match a recognisable forge
   host; raise `PackageError` otherwise. The measured table above is the test
   case, including the one-segment host row the backlog does not name. A
   local-path origin is exactly what `session.py:487` falls back to, so the
   refusal has a real caller.
2. **Branch and `pushed_sha` recorded before `open_draft_pr`**, the URL after. A
   `gh` that is missing, unauthenticated or refused currently leaves the branch
   pushed and the ledger reading `READY_FOR_REVIEW` with neither.
3. **`reverify`'s cell gets `policy.thread_env`**, like the in-cell suite. Empty
   for Saffron, so it changes no behaviour here — it removes a suite-drift
   vector by construction, which is part 2.1's argument in a second place.
4. **§5.7's "rebase" wording.** One sentence saying step 1 is the intent and the
   v1 subsection is the mechanism (`git apply --3way`). No renumbering.

And the three test gaps item 11 names, each one assertion: pipe-escaping over
the findings and disagreements tables (a `|` is likelier in a model-authored
`claim` than in a gate message), `test_an_unanchored_finding_still_appears`
asserting the row is marked `no` — the half that makes drop rate visible — and
one test exercising `attempts`, `new_failures`, `reviews` and `rebut_result` on
`CellOutcome`'s success path.

## 6. `DESIGN.md`, before any code

- **§5.1** — cell construction gains the default-branch fetch and the `/gates`
  mount.
- **§5.4** — the visibility invariant (*the shape of the answer*, above), the gate source and its
  consequence for a gate-changing task (part 2.2), the dirty-tree rule (part 3),
  and the residual restated (part 4).
- **§5.7** — the base is the remote's default-branch head as of task start
  (part 1); the rebase wording (part 5, item 4).

Add subsections; never renumber. A rev bump, and an appendix narrating what
building this found — the convention every prior rev has followed.

## 7. Testing

TDD throughout. Three claims need a test that can go red for the right reason:

- **Gate pinning needs a cell-marked test** that commits a lying
  `.saffron/gates/tests.py` inside the cell and asserts the host-supplied gate
  ran anyway. Appendix I's rule binds here: start the cell the way production
  does and probe from inside it, or this is one more mechanism that reports
  success while applying to something else.
- **The dirty-tree check needs both halves** — the repair turn fires and the
  re-run is clean, and a still-dirty second look ends the attempt.
- **The base change needs `needs_reverification` false when nothing moved**, the
  path that has been unreachable since PACKAGE shipped.

## 8. Success criterion

A task started from a feature branch is cut from the remote's default-branch
head, packages without re-verification when the remote has not moved, and its
gate results come from executables the cell could not have written. Every
remaining route to changing what the suite measures appears in the patch.

Backlog items 11 and 12 close the way 1 and 3 did: with what turned out to be
wrong about them, measured rather than re-reasoned.
