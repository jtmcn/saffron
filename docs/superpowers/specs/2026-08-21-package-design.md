# PACKAGE + index — design

Sub-project A of v1 (`DESIGN.md` §9). Turns a green cell into a branch on the
real remote, a draft pull request, and a line in the morning queue.

Backlog item 5 is the whole of it: *"There is no PR, no push, no index. A green
run leaves `patch.diff` and `patch.json` in the batch tree and nothing tells you
they are there."* And the sharper half of that item — patches decay. `SA-0003`'s
patch stopped applying three hours after it was written, because commits moved
`session.py` underneath it. **A verified-green change has a shelf life measured
against the branch it was cut from.**

> **Citations:** a bare `§` cites `DESIGN.md`, per repo convention. This
> spec's own sections are cited as *part N*.

> Revised after adversarial review. Six blocking findings, all upheld against
> the code and the design; the review's own account of `git apply --3way` was
> then found incomplete by measurement (part 2.1). What that round changed is
> listed throughout, because a spec that quietly absorbs a review teaches nothing.

## Why this before the gates

`docs/BACKLOG.md` ranks the `integrity` gate first, on principle 49: a
verification an agent can run itself is one it will have already passed, so the
core gates are the only gates that can ever fire. That is true, and it is an
argument about *which gates can fire* — not about what to build next.

Appendix K settles the sequencing directly: *"§5.5's critic is not a refinement
to add once the loop is trustworthy. It is the component that makes the loop's
output mean anything."* **That component is already built.** `phases/review.py`
and `phases/rebut.py` run, and they write `findings.json` and `rebuttal.json`
into the batch tree where **nothing reads them**. The most valuable thing v0.5
has is write-only. PACKAGE is what renders it.

Two more things settle it. Backlog item 1 is not shovel-ready — its own text
says half of `integrity` may not belong in a core gate at all, and needs a
`DESIGN.md` decision *and* a change to the `tests` gate contract before a line
is written. And only item 5 has a clock on it: item 1's value does not expire,
while every green run made before PACKAGE exists produces a patch that is
decaying from the moment it is written.

What the backlog's ordering has genuinely in its favour is **risk direction**.
Item 1's gates are all local. PACKAGE is the first component in the system that
lets cell-authored bytes leave the host. That is not a reason to reorder; it is
the reason part 6 of this spec exists.

An earlier draft of this section claimed the morning review "does not exist"
without PACKAGE. That is false, and Appendix K is the refutation: the review
that found the broken diff happened with no PACKAGE at all. The true claim is
narrower and sufficient — PACKAGE makes a review that already works *reachable*,
and stops its output expiring unread.

## Scope

In: PACKAGE (§5.7) for a task that reached `READY_FOR_REVIEW` — rebase,
conditional re-verification, push, draft pull request, and §5.7 step 4's append
to the morning-queue index (§6).

Out, each a sub-project rather than an omission: the `attempts` and `findings`
tables (B), the batch orchestrator and the index header's trailing accept rate
(C), the full §5.4 `secrets` gate (D — part 6 below carries only the refusal that
PACKAGE itself makes necessary), the merge train (§6.1, v2), DIAGNOSE's root
cause (E), per-criterion critic assessment (F).

---

## 1. Where PACKAGE sits, and what it is given

`saffron/phases/package.py`, host-side. It runs after `run_one_cell` has
returned and the cell is gone. `cli._run_cell` calls it when, and only when, the
returned state is `READY_FOR_REVIEW`.

`run_one_cell` returns a `CellOutcome` instead of `str`:

```python
@dataclass
class CellOutcome:
    state: str
    task_id: int
    run_id: int
    task_dir: Path
    spent_usd: float = 0.0
    attempts: int = 0
    cell_head_sha: str | None = None
    gates: list[GateResult] = field(default_factory=list)
    new_failures: list[NewFailure] = field(default_factory=list)
    reviews: list[review.LensReview] = field(default_factory=list)
    rebut_result: rebut.RebutResult | None = None
    agent_subjects: list[str] = field(default_factory=list)
```

**Every field is defaulted, and that is load-bearing rather than tidy.**
`session.py`'s early returns precede the bindings: `spent` is first bound by
`plan_checkpoint` (`session.py`:488) while `PREFLIGHT_FAILED` and
`PLAN_REJECTED` return before it, and `reviews` is unbound on every path that
skipped REVIEW. A `CellOutcome` constructed at each `return` without defaults
raises `UnboundLocalError` on exactly the failure paths that matter most.

An earlier draft claimed every field was already computed and merely discarded.
That is true of seven and false of four, and the false ones are not free
plumbing: `attempts` and `new_failures` are locals inside `repair_loop`, which
returns `str` (`session.py`:219-260); `cell_head_sha` is computed in the
module-level `export_patch` helper (`session.py`:323), called from `finally`
*after* the state is decided; `agent_subjects` needs a new exec.

`CellSpec` gains **nothing**. An earlier draft added `risk` and `title` to it;
`cli._run_cell` already holds the whole `Spec`, which carries `title`, `risk`
and `acceptance_criteria`, and `render_pr_body` already takes a `Spec`. PACKAGE
takes the `Spec`. (`report/index.py`'s `sort_key` does get real risk tiers today
— `replay.py`:127 passes them — it is only the *cell* path that has none, and
passing the `Spec` fixes that too.)

This is also the seam sub-project C replaces: `session.py`:4 already says
`ponytail: this is v0.5's supervisor. v1 replaces it with supervisor.py`. A
supervisor returning a bare string cannot be given a caller.

## 2. The git operations

**No named remote is added to the mirror, and no long-lived ref is created.**
Every call takes the URL directly: no config for an agent to have written, and
no remote name colliding with the mirror's own `origin`, which points at the
local working copy rather than at GitHub.

The no-ref rule is not fastidiousness. `ensure_mirror` fetches
`+refs/*:refs/*` with `--prune` (`mirror.py`:43), so **any ref PACKAGE leaves in
the mirror that the local repo does not have is deleted on the next run** —
including a branch PACKAGE just created. A fixed `refs/saffron/base` would also
be moved under one task by another task's fetch. Everything below is per-task or
transient.

1. **Resolve the real remote.** `git -C <repo> remote get-url origin`.

   This closes a live defect. `session.py`:363 calls
   `ledger.upsert_repo(repo.name, str(repo), ...)`, storing the **local
   filesystem path** in `repos.origin`. §4.1 means two different things by
   `origin` and `mirror_path`; the code has put the mirror's source in both
   since v0, so nothing downstream knows where the real remote is.

   Both URL shapes are handled — `git@github.com:owner/repo.git` and
   `https://github.com/owner/repo.git` — and a repo with **no** `origin` is an
   infrastructure failure with a clear message, because that is every test
   fixture and every fresh `git init`.

2. **Find the default branch.** `git ls-remote --symref <url> HEAD`; line one is
   `ref: refs/heads/main<TAB>HEAD`. Measured, git 2.50.1. Not hardcoded `main`:
   three lines buys `master` and `trunk`, and repo two need not resemble repo
   one (§9).

3. **Fetch it**, to `FETCH_HEAD` rather than to a ref:
   `git -C <mirror> fetch <url> refs/heads/<default>`.

4. **Assert `base_sha`'s objects are present** — `git -C <mirror> cat-file -e
   <base_sha>^{tree}`. See part 2.1: without them, `--3way` degrades to a context
   match and reports success.

5. **Cut a scratch worktree** at `FETCH_HEAD`, at a **per-task path**, via
   `repos.mirror.add_worktree`, then `git checkout -B <branch>`.

   `-B`, not `-b`: `-b` fails when the ref already exists, which is precisely
   the second-package path part 7 designs a test for.

6. **Apply** `patch.diff` with `git apply --3way --index`, treating both the
   exit code **and** stderr as signal (part 2.1). This is §5.7's rebase, for a
   branch one commit long.

7. **Commit once**, as `saffron <spec_id>: <spec title>`.

   Not the repo's own `type(scope):` convention: that convention describes a
   commit a person wrote about a defect they understood, and this one is
   generated. A subject mimicking it would claim a judgement nothing made. The
   body carries `base_sha`, the cell's head sha, attempt count, cost, and the
   agent's own commit subjects — captured by one `git log --format=%s
   <base>..HEAD` exec beside `export_patch`, before teardown. All of it passes
   through part 6's neutralizer first.

8. **Re-verify, if and only if the base moved** — part 3.

9. **Push**, lease read rather than assumed: `git ls-remote <url>
   refs/heads/<branch>`, then
   `--force-with-lease=refs/heads/<branch>:<what ls-remote said>`, empty when the
   branch does not exist. Preceded by part 6's refusal scan.

10. **Open the draft pull request.** `gh pr create --repo <slug> --draft --base
    <default> --head <branch> --title <...> --body-file <...>`.

    `--title` is not optional: without it, and without `--fill`, `gh` prompts —
    which unattended is a hang. If a pull request already exists on the branch
    the push has already updated it, so `gh pr view <branch> --json url` reports
    that instead. That is §4.2's `CHANGES_REQUESTED` re-queue path, and handling
    it costs one call now rather than a confusing failure later.

11. **Persist the outcome** (part 5), **append the queue line** (part 8), and remove the
    scratch worktree **in a `finally`** — it otherwise leaks on every raise path,
    including the missing-`gh` case part 5 deliberately creates.

**Push precedes the pull-request call, deliberately.** A missing or
unauthenticated `gh` then leaves a pushed branch you can open by hand; the other
order loses the work to a CLI.

### 2.1 What was measured, and the two hazards it found

All on git 2.50.1 (Apple Git-155), against real repositories. A claim about
git's behaviour taken from its documentation is the kind this project has been
wrong about before.

Holding as §5.7 assumes:

- `--force-with-lease=<ref>:` with an **empty** expectation pushes a branch that
  does not exist (rc 0), and is rejected `stale info` if that branch appeared
  meanwhile. The absent-branch case is not a special case to write around.
- A **stale** non-empty expectation is rejected `stale info` (rc 1). §5.7's
  "turning a race into an error costs one flag" holds exactly as written.

And two hazards, both of which break the obvious implementation:

> **A conflicting `--3way` apply exits 1 and still writes the file.** It reports
> `Applied patch to 'f.txt' with conflicts`, leaves `<<<<<<< ours` markers, and
> stages a `U` entry. "The apply failed" and "nothing happened" are **not** the
> same state.

> **A degraded `--3way` apply exits 0.** With the preimage blob absent but the
> hunk's context matching, git prints `error: repository lacks the necessary
> blob to perform 3-way merge. / Falling back to direct application...` — to
> **stderr, with rc 0** — and stages the result. Conflict detection silently
> becomes a context match, which is the whole reason `--3way` was chosen.

So the exit code alone decides nothing. A non-zero exit is `MERGE_FAILED`, the
worktree is discarded unread, and steps 7 onward do not run. A **zero** exit
whose stderr contains `lacks the necessary blob` is an **`error`** — the
toolchain, not the code — which is why step 4 asserts the objects up front:
`error` and `fail` are different outcomes and must not be collapsed (§5.4).

A third, from the review: `worktree.DIFF_FLAGS` carries no `--binary` or
`--full-index`, so a binary change exports as `Binary files … differ` and
`--3way` fails with `cannot apply binary patch to 'b.bin' without full index
line` (rc 1). That is *also* not "the branch moved underneath" — it is a patch
that was never appliable, so it is an `error`, not `MERGE_FAILED`. Whether to
add `--binary` to `DIFF_FLAGS` is left to sub-project D, which owns the diff
gates; PACKAGE only has to stop reporting it as the task's fault.

## 3. Re-verification, and when it is skipped

`docs/BACKLOG.md`:211 requires *"re-run the full suite on the merged result"*,
and `DESIGN.md`:1880 names the mechanism **"rebase-and-re-verify"**. §5.7's
numbered steps are silent on it; the two narrative sources are not, and they
win. An earlier draft of this spec read the silence as a decision and was wrong.

Why it matters concretely: `pr_body.py`'s gate table would otherwise render
`pass` for a suite that ran against `base_sha`'s tree, published on a commit
whose tree is *today's default branch plus the patch*. That is the `tool`-field
defect of §5.4 and Appendix H in a new costume — a table claiming "ran and
passed" about a tree no gate ever saw — and it worsens in exact proportion to
the base movement this spec exists to handle.

**The rule:** if `FETCH_HEAD` equals `spec.base_sha`, the default branch has not
moved, the merged tree is byte-identical to the one the suite already ran on,
and re-verification is **provably** redundant. It is skipped, and the PR body
says it was skipped and why. Otherwise the suite re-runs.

**The re-run happens in a cell, never host-side.** The applied tree contains
`.saffron/gates/*` exactly as the patch left them, and exec'ing those on the
host is the control plane executing model-authored code — the one thing §2 says
it never does. This is a gate-only cell: `worktree.prepare_worktree` at the
packaged commit (which is reachable in the mirror, having just been committed
there), `network="none"`, no agent, no credential, `runner.CellExecutor` for the
suite. Every piece already exists; none of it is new machinery.

Because the base moved, the old baseline no longer describes it, and comparing
against it would attribute the default branch's own drift to this task. So the
gate-only cell runs the suite **twice** — at `FETCH_HEAD` for a fresh baseline,
and at the packaged commit — and `baseline.subtract_baseline` does what it
always does. This is §4.4 steps 2 and 3 applied to one commit instead of a run,
and it is the reason baseline subtraction is per-run rather than global.

New failures after the rebase mean the change does not survive contact with
today's default branch: **`MERGE_FAILED`**, with the failures named in the note.
No new state — `DESIGN.md` §6's own example note is `conflicts with #209`, which is the same
class of fact. A gate returning `error` here is infrastructure and is charged to
nobody, as everywhere else.

## 4. The pull-request body

`report/pr_body.py` today renders title, acceptance-criteria checklist, new
failures, gate table and provenance. It gains, in `DESIGN.md` §6's order — **disagreements
first, above the gate table, because that is where your judgment is worth the
most**:

- **Disagreements.** Every anchored blocker with the implementer's `rebuttal`
  and the critic's `verdict`.

  **Two columns, not three.** An earlier draft rendered `adjudication` beside
  them, claiming `rebut.py` already kept three distinct keys. It keeps two, and
  deliberately: `Verdict`'s docstring (`rebut.py`:73-75) reads *"never the
  operator's `adjudication`, which happens in GitHub against a PR"*, and
  `tests/test_rebut.py`:281 asserts `"adjudication" not in json.dumps(record)`.
  Adjudication is your judgment on the pull request **this phase is creating** —
  rendering it here is chronologically impossible, and shipping the column would
  have broken a test written specifically to keep §4.1's three from collapsing.
  It arrives with the `findings` table in sub-project B.
- **Findings.** Lens, severity, `file:line`, and the finding's `claim` —
  `findings.py`:36 names that field `claim`, and `CONTEXT.md` draws the line
  between a claim and a message. Unanchored findings render too, never dropped:
  `anchored = False` is kept precisely so drop rate per lens stays visible.
- **The test-file diff, shown separately.** `DESIGN.md` §7's second countermeasure for gate
  gaming, filtered by `policy.integrity.test_paths` — parsed by `policy.py`:42
  and read by nothing until now. `DESIGN.md` §2.1's table puts `integrity` at "**Core**,
  patterns from repo", so this holds the boundary: **not one line of language
  knowledge enters core.**
- Attempt count, cost, and **which tree the gates ran on** (part 3).

`pr_body.py`'s `ponytail:` comment says move to Jinja when REVIEW lands and the
conditionals arrive. Both have happened; the f-strings go.

Two deviations from §5.7 as written, recorded in `DESIGN.md` rather than left as
drift: the acceptance-criteria checklist stays **unchecked**, because no lens
produces a per-criterion mapping and a checkbox with nothing behind it is worse
than an empty one (sub-project F); and there is **no root-cause section**,
because DIAGNOSE does not exist (E).

## 5. Outcomes, and who writes them down

**PACKAGE persists its own outcome, and this is a gap the review found rather
than a restatement.** By the time PACKAGE runs, `run_one_cell` has already
called `ledger.set_task_state(task_id, "READY_FOR_REVIEW")` and
`ledger.finish_run(run_id, "COMPLETE")` (`session.py`:734-735). Left alone, a
`MERGE_FAILED` task would read `READY_FOR_REVIEW` in the ledger forever, against
a run already closed `COMPLETE`, with the failure existing nowhere but stdout.

So PACKAGE writes the terminal state itself, and records the **pushed sha, the
branch and the pull-request URL** — the three facts that did not exist before it
ran, and the only ones that can find the work again. They go to the task row and
to `patch.json` beside the artifacts they describe. The run row is reopened only
if PACKAGE changes the state; a run closed `COMPLETE` whose task later reads
`MERGE_FAILED` is the same class of lie as an open run that has ended.

| Outcome | State | Exit | Why |
|---|---|---|---|
| Applied, verified, pushed, PR open | `READY_FOR_REVIEW` | 0 | reviewable |
| `--3way` conflicted (rc≠0) | `MERGE_FAILED` | 1 | the branch moved underneath |
| New failures after re-verification | `MERGE_FAILED` | 1 | does not survive today's main |
| Lease rejected (`stale info`) | `MERGE_FAILED` | 1 | a race, turned into an error |
| Blob missing / binary patch / no `patch.diff` | raises | 2 | `error`, not `fail` — charged to nobody |
| `gh` missing or unauthenticated | `READY_FOR_REVIEW` | 2 | branch **is** pushed; message says so |
| Secret found in the patch | `MERGE_FAILED` | 1 | part 6; nothing is pushed |

The `gh` row needs care, because the obvious answer is wrong. `GATE_ERROR` is
defined narrowly in §3.3 — *a gate errored, or the two suites drifted* — and a
`gh` binary that is not installed is neither; reaching for it because it is the
nearest infrastructure-shaped state is principle 34 wearing a state name. So
PACKAGE **raises**, and `cli.main`'s existing handler catches, prints and returns
2 — a path `cli.py`:18-22 already documents. The task's state is untouched
because it is still **true**: the diff passed its gates and its critic, and the
branch is on the remote. The state describes the task; the exit code describes
the invocation.

There is one more, and it is not a failure of PACKAGE: `export_patch` writes no
`patch.diff` when the diff is empty, and swallows an export failure into a
`watch` line while `run_one_cell` still returns `READY_FOR_REVIEW`
(`session.py`:311-314, 330-331). Commits-ahead greater than zero with an empty
`base..HEAD` diff is reachable. PACKAGE needs a named outcome for "no patch to
package" rather than a traceback.

## 6. What must not leave the host

**PACKAGE is the first component in Saffron that moves cell-authored bytes off
the host.** Everything before it wrote to the batch tree, which is yours. This
section exists because of that, and it is the reason the risk-direction argument
in "Why this before the gates" did not change the ordering.

**The credential.** The cell carries `CLAUDE_CODE_OAUTH_TOKEN` — CLAUDE.md's one
sanctioned in-cell credential. An agent that writes it into a file gets it
pushed to a real remote, where it is effectively undeletable. Before step 9,
PACKAGE scans `patch.diff` for the token's literal value and for the credential
shapes we already know, and **refuses to push** if it finds one: `MERGE_FAILED`,
nothing pushed, the path named and the value never echoed. Roughly twenty lines.
The full §5.4 `secrets` core gate stays in sub-project D; this is only the
refusal that PACKAGE itself makes necessary, and `DESIGN.md` records the residual
risk the way Appendix G records the tolerated listener.

**The text.** The squash body carries the agent's own commit subjects; the pull
request body carries model-authored `claim` and `argument` strings. GitHub parses
`Fixes #12` and `Closes #45` in a commit message *and* in a pull request body and
**closes those issues on merge**, and `@name` notifies real accounts. This is the
one place in the spec where content authored inside a cell causes a side effect
on a real repository outside it — the exact shape §2's invariant is about, even
though no code executes. Every model-authored string is neutralized before it
enters a message or a body: closing keywords defanged, `@` broken.

## 7. Testing

No `cell`-marked tests for the git and rendering paths; the gate-only
re-verification cell is `cell`-marked, because it starts a container. Real
temporary git repositories throughout, no network, `gh` behind a callable seam
the way `agent` already is in `session.py`.

- A patch applied onto a default branch that moved **elsewhere** in the file:
  applies, commits, pushes.
- The same patch onto a branch that moved **into the same lines**: `MERGE_FAILED`
  — and `ls-remote` against the stand-in remote proves **nothing was pushed**.
  Asserting the state alone would pass against an implementation that pushed
  conflict markers first.
- **The degraded apply**: preimage blob absent, context matching. The
  implementation must report `error`, not success — the case that exits 0.
- A binary change: `error`, never `MERGE_FAILED`.
- The absent-branch lease, and a branch moved between `ls-remote` and push.
- A second package of the same branch: existing pull request found, URL
  reported, no duplicate `gh pr create`, and `checkout -B` does not fail.
- Base unmoved: re-verification **skipped**, and the body says so. Base moved:
  suite re-runs, and new failures give `MERGE_FAILED`.
- A patch containing the OAuth token: `MERGE_FAILED`, nothing pushed, token
  absent from every message and log line.
- `Fixes #1` and `@someone` in an agent commit subject and in a finding's
  `claim`: neutralized in both the commit body and the PR body.
- `repos.origin` holds the real remote after a package, not the local path; both
  URL shapes parse; a repo with no `origin` fails clearly.
- The scratch worktree is gone after a raise, not only after success.
- Body rendering: disagreements sort above the gate table and carry **two**
  columns; a `test_paths` match renders in the test-diff section and not the
  main one; an unanchored finding still appears.

## 8. The index

§5.7 step 4's mechanism, no more. Each packaged task appends a `QueueLine` — the
dataclass exists — to `out_dir / "queue.json"`, and `index.html` is re-rendered
beside it from the full list. Appending rather than rewriting is what lets a
second task join a first without the orchestrator that does not exist yet.

`render_index` and `sort_key` are unchanged from v0. **`_row` is not**:
`index.py`:113 labels the link `artifacts`, and `DESIGN.md` §6's own mock shows `→ PR #211`.
Repointing `link` at a pull request without relabelling would caption every PR
link "artifacts".

**A PACKAGE that raises appends nothing**, deliberately: the branch is pushed,
the error names it, and an index line whose link points at a pull request that
was never opened is worse than no line. Whether a batch tolerates one such task
or stops is sub-project C's decision, because C is the first thing with more
than one task to decide about.

The batch header stays as it is. Its one field that matters — **trailing**
accept rate — is unanswerable until C has batches to trail, and a header that
scored the night it printed would be reporting on work that had not happened.

## 9. `DESIGN.md` edits, written before the code

New subsections only — section numbers are an API that specs cite, so nothing is
renumbered.

- **§5.7** — v1 packages one squashed commit and opens a **draft** pull request.
  The provenance consequence is named: the pushed sha is not the cell's head sha,
  because the cell's commits die with the volume, and the body carries both.
- **§5.7** — re-verification runs when the base moved and is skipped, with the
  reason stated in the body, when it has not (part 3). The numbered steps gain the
  re-verify that Appendix K and BACKLOG item 5 already assume.
- **§5.7** — the two measured `--3way` hazards (part 2.1), in the appendix idiom: a
  non-zero apply is not a no-op, and a zero apply is not necessarily a merge.
- **§5.7 / Appendix** — the credential refusal and its residual risk (part 6),
  recorded the way Appendix G records the tolerated listener: an accepted risk
  that goes unwritten is the hazard the check exists for.
- **§4.1** — `repos.origin` is the real remote; `mirror_path` is the local
  mirror. Stated because the code has conflated them since v0.
- The two part-4 deviations — unchecked criteria, no root cause — recorded with the
  sub-project each waits on.

## 10. Success criterion

`uv run saffron cell .saffron/specs/<spec>.md --repo .` on a green task leaves a
draft pull request on `jtmcn/saffron` whose body tells you something you would
have had to read the diff to learn — and the branch is cut from **today's**
default branch, with the gate table saying honestly which tree it ran on.
