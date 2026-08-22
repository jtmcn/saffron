# PACKAGE + index — design

Sub-project A of v1 (`DESIGN.md` §9). Turns a green cell into a branch on the
real remote, a draft pull request, and a line in the morning queue.

Backlog item 5 is the whole of it: *"There is no PR, no push, no index. A green
run leaves `patch.diff` and `patch.json` in the batch tree and nothing tells you
they are there."* And the sharper half of that item — patches decay. `SA-0003`'s
patch stopped applying three hours after it was written, because commits moved
`session.py` underneath it. **A verified-green change has a shelf life measured
against the branch it was cut from**, and every hour v0.5's pipeline spends
producing one is spent against that clock.

## Why this before the gates

`docs/BACKLOG.md` ranks the `integrity` gate first, on principle 49: a
verification an agent can run itself is one it will have already passed, so the
core gates are the only gates that can ever fire. That is true and it is not the
argument for building them first.

§7 names **two** countermeasures for gate gaming, not one: *"`integrity` gate;
test-file diff shown separately in the PR."* The second is a PACKAGE feature.
Until a night's work reaches a pull request somebody reads, the morning review is
not the last line of defence — it does not exist, and the gates are carrying a
load they were never able to carry. Appendix K is the measurement: the factory
produced plausible, verified, broken code, **no gate could have caught any of
it**, and adversarial review found it in under an hour.

So this sub-project is what makes the review that already works reachable, and
what stops the pipeline's output expiring before it is read.

## Scope

In: PACKAGE (§5.7) for a task that reached `READY_FOR_REVIEW`, the pull-request
body §5.7 describes, and §5.7 step 4's append to the morning-queue index (§6).

Out, and each is another sub-project rather than an omission: the `attempts` and
`findings` tables (B), the batch orchestrator and the index header's trailing
accept rate (C), the merge train's re-verification (§6.1, v2), DIAGNOSE's root
cause (E), and per-criterion critic assessment (F).

---

## 1. Where PACKAGE sits, and what it is given

`saffron/phases/package.py`, host-side, no model and **no cell**. It runs after
`run_one_cell` has returned and the container, network and volumes are gone —
PACKAGE needs no cell, and the host should not be talking to the real remote
while one is alive. `cli._run_cell` calls it when, and only when, the returned
state is `READY_FOR_REVIEW`.

`run_one_cell` stops returning `str` and returns a `CellOutcome`:

```python
@dataclass
class CellOutcome:
    state: str
    task_id: int
    spent_usd: float
    attempts: int
    cell_head_sha: str | None
    task_dir: Path
    gates: list[GateResult]
    new_failures: list[NewFailure]
    reviews: list[review.LensReview]
    rebut_result: rebut.RebutResult | None
    agent_subjects: list[str]
```

Every field is already computed inside `run_one_cell` and discarded at
`return outcome`. Nothing is re-read from `/work`, and nothing is re-parsed out
of the JSON the same function just serialised — the artifacts in the batch tree
stay the durable record, and this is the in-process one.

This is also the seam sub-project C replaces: `session.py:4` already carries
`ponytail: this is v0.5's supervisor. v1 replaces it with supervisor.py`. A
supervisor that returns a bare string cannot be given a caller.

`CellSpec` gains `risk` and `title`. `report/index.py`'s `sort_key` has read
`line.risk` since v0 and has never once been handed a real one.

## 2. The git operations

**No named remote is ever added to the mirror.** Every call takes the URL
directly: there is no config left behind for an agent to have written, and no
remote name to collide with the mirror's own `origin` — which points at the local
working copy, not at GitHub.

1. **Resolve the real remote.** `git -C <repo> remote get-url origin`.

   This closes a live defect. `session.py:363` calls
   `ledger.upsert_repo(repo.name, str(repo), ...)`, storing the **local
   filesystem path** in `repos.origin`. §4.1 means two different things by
   `origin` and `mirror_path`, and the code currently puts the mirror's source in
   both. Nothing downstream knows where the real remote is.

2. **Find the default branch.** `git ls-remote --symref <url> HEAD`; the first
   line is `ref: refs/heads/main<TAB>HEAD`. Measured on git 2.50.1.

   Not hardcoded `main`. Three lines buys correctness on `master` and `trunk`,
   and repo two is not required to look like repo one (§9).

3. **Fetch it** into the mirror:
   `git fetch <url> +refs/heads/<default>:refs/saffron/base`.

4. **Cut a scratch worktree** off `refs/saffron/base` with the existing
   `repos.mirror.add_worktree`, then `git checkout -b <branch>`. `add_worktree`
   already survives a worktree that a killed process left registered.

5. **Apply** `patch.diff` with `git apply --3way --index`. This is §5.7's rebase,
   for a branch that is one commit long.

6. **Commit once**, as `saffron <spec_id>: <spec title, lowercased first word>`.

   Not the repo's own `type(scope):` convention: that convention describes a
   commit a person wrote about a defect they understood, and this one is
   generated. A subject that mimics it would claim a judgement nothing made.
   The body carries `base_sha`, the
   cell's head sha, attempt count, cost — and the agent's own commit subjects,
   captured by one `git log --format=%s <base>..HEAD` exec added beside
   `export_patch`, before teardown. Five lines, and it keeps a record that
   otherwise survives only in a transcript nobody opens.

7. **Push**, with the lease read rather than assumed: `git ls-remote <url>
   refs/heads/<branch>` first, then
   `--force-with-lease=refs/heads/<branch>:<what ls-remote said>`, empty when the
   branch does not exist.

8. **Open the draft pull request.** `gh pr create --repo <slug> --draft --base
   <default> --head <branch> --body-file <path>`, slug derived from the URL. If a
   pull request already exists on the branch, the push has already updated it —
   `gh pr view <branch> --json url` and report that. That is §4.2's
   `CHANGES_REQUESTED` re-queue path, and handling it costs one call now instead
   of a confusing failure later.

9. **Append the queue line**, then `mirror.remove_worktree`.

**Push precedes the pull-request call, deliberately.** A missing or
unauthenticated `gh` then leaves a pushed branch you can open by hand; the other
order loses the work to a CLI.

### 2.1 What was measured, and the one hazard it found

All on git 2.50.1 (Apple Git-155), against real repositories, because a claim
about git's behaviour taken from its documentation is the kind this project has
been wrong about before:

- `--force-with-lease=<ref>:` with an **empty** expectation pushes a branch that
  does not exist (rc 0), and is **rejected with `stale info`** if that branch
  appeared in the meantime. The absent-branch case is not a special case to write
  around; it is the same flag.
- A **stale** expectation — the branch moved after `ls-remote` read it — is
  rejected with `stale info`. §5.7's "turning a race into an error costs one
  flag" holds exactly as written.
- `git apply --3way --index` finds the preimage blob from the patch's own index
  line, so a patch cut at `base_sha` applies against a moved default branch with
  no extra plumbing.

And the hazard, which is why this section exists:

> **A conflicting `--3way` apply exits 1 and still writes the file.** It reports
> `Applied patch to 'f.txt' with conflicts`, leaves `<<<<<<< ours` markers in the
> worktree, and stages a `U` entry. "The apply failed" and "nothing happened" are
> **not** the same state. Anything that committed after a non-zero apply would
> commit conflict markers to a branch, push them to the real remote, and open a
> pull request on them.

So: a non-zero exit from step 5 is `MERGE_FAILED`, the scratch worktree is
discarded unread, and no step 6 through 9 runs. A test asserts the conflict case
produces `MERGE_FAILED` **and** that nothing was pushed — asserting the state
alone would pass against an implementation that pushed markers first.

## 3. The pull-request body

`report/pr_body.py` today renders the title, an acceptance-criteria checklist,
new failures, the gate table and provenance. It gains, in §6's order —
**disagreements first, above the gate table, because that is where your judgment
is worth the most**:

- **Disagreements.** Every anchored blocker with the rebuttal's `verdict`,
  `adjudication` and `rebuttal`. `rebut.py` already keeps those as three distinct
  keys, which is §4.1's "three distinct columns that must not collapse" in the
  right shape and the wrong place; this renders them without moving them.
- **Findings.** Lens, severity, `file:line`, message, and whether it anchored.
  Unanchored findings are rendered, never dropped — `agents/findings.py` keeps
  `anchored = False` precisely so the drop rate per lens stays visible.
- **The test-file diff, shown separately.** §7's second countermeasure for gate
  gaming. Filtered by `policy.integrity.test_paths`, which `repos/policy.py`
  already parses and nothing has ever read. Repo-declared data; **not one line of
  language knowledge enters core** (§2.1).
- Attempt count and cost on the header line.

`pr_body.py`'s `ponytail:` comment says to move to Jinja when REVIEW lands and
the conditionals arrive. REVIEW has landed and the conditionals are arriving:
this is that move, and the f-strings go.

Two deviations from §5.7 as written, recorded in `DESIGN.md` rather than left as
drift:

- The acceptance-criteria checklist stays **unchecked**. §5.7 asks for "the
  critic's assessment of each"; no lens produces a per-criterion mapping, and
  inventing one here would be a checkbox with nothing behind it. Sub-project F.
- **No root-cause section.** DIAGNOSE does not exist. Sub-project E.

## 4. States, and what each one costs

**No new state.** `MERGE_FAILED` covers both the apply conflict and the broken
lease — §5.7 discusses them in the same breath, and both mean the same thing:
the branch moved underneath. `report/index.py`'s `_STATE_RANK` already ranks it
at 2, with the rest of what needs you.

| Outcome | State | Exit | Why |
|---|---|---|---|
| Applied, pushed, PR open | `READY_FOR_REVIEW` | 0 | reviewable |
| `apply --3way` conflicted | `MERGE_FAILED` | 1 | the task did not make it |
| Lease rejected (`stale info`) | `MERGE_FAILED` | 1 | a race, turned into an error |
| `gh` missing/unauthenticated | `READY_FOR_REVIEW` | 2 | infrastructure; branch **is** pushed, message says so |
| Remote unreachable | unchanged | 2 | infrastructure, charged to nobody |

The last two need care, because the obvious answer is wrong. `GATE_ERROR` is
defined narrowly in §3.3 — *a gate errored, or the two suites drifted* — and a
`gh` binary that is not installed is neither. Reaching for it because it is the
nearest infrastructure-shaped state is principle 34 wearing a state name.

So PACKAGE **raises**, and `cli.main`'s existing handler catches it, prints and
returns 2. That path is already documented in `cli.py`: *"a driver or runtime
crash is the same class of failure and takes 2 by the handler in `main`."* The
task's state is untouched, and it is untouched because it is still **true** —
the diff passed its gates and its critic, and the branch is on the remote. The
state describes the task; the exit code describes the invocation. Conflating
them would report a reviewable change as a failed one over a missing CLI.

## 5. The index

§5.7 step 4's mechanism, no more. Each packaged task appends a `QueueLine` — the
dataclass exists — to `out_dir / "queue.json"`, and `index.html` is re-rendered
beside it from the full list; `render_index` and `sort_key` are unchanged from
v0. Appending rather than rewriting is what lets a second task join a first
without the orchestrator that does not exist yet.

**A PACKAGE that raises appends nothing**, and that is deliberate rather than
overlooked: the branch is pushed, the error names it, and an index line whose
`link` points at a pull request that was never opened is worse than no line.
Whether a batch tolerates one such task or stops is sub-project C's decision,
because C is the first thing that has more than one task to decide about. `link` becomes the pull-request URL,
which is the point of §6: *the queue is an index, not a viewer*, because GitHub
is already the viewer.

The batch header stays as it is. Its one field that matters — **trailing** accept
rate — is unanswerable until sub-project C has batches to trail, and a header
that scored the night it printed would be reporting on work that had not
happened.

## 6. Testing

No `cell`-marked tests: PACKAGE never starts a container. Real temporary git
repositories throughout, no network, `gh` behind a callable seam the way `agent`
already is in `session.py`.

- A patch applied onto a default branch that moved **elsewhere** in the file:
  applies, commits, pushes.
- The same patch onto a branch that moved **into the same lines**: `MERGE_FAILED`,
  and `ls-remote` against the stand-in remote proves nothing was pushed.
- The absent-branch lease, and a branch moved underneath between `ls-remote` and
  push: pushed, then rejected.
- A second package of the same branch: existing pull request found, URL reported,
  no duplicate `gh pr create`.
- Body rendering: disagreements sort above the gate table; a path matching
  `integrity.test_paths` renders in the test-diff section and not the main one;
  an unanchored finding still appears.
- `repos.origin` holds the real remote after a package, not the local path.

## 7. `DESIGN.md` edits, written before the code

New subsections only — §9's section numbers are an API and specs cite them, so
nothing is renumbered.

- **§5.7** — v1 packages one squashed commit and opens a **draft** pull request.
  The provenance consequence is named: the pushed sha is not the cell's head sha,
  because the cell's commits die with the volume, and the body carries both. The
  two deviations in §3 above are recorded here.
- **§4.1** — `repos.origin` is the real remote; `mirror_path` is the local
  mirror. Stated because the code has conflated them since v0.
- **§5.7** — the measured `--3way` hazard from §2.1, in the Appendix idiom: a
  non-zero apply is not a no-op.

## 8. Success criterion

`uv run saffron cell .saffron/specs/<spec>.md --repo .` on a green task leaves a
draft pull request on `jtmcn/saffron` whose body tells you something you would
have had to read the diff to learn — and the branch is cut from **today's**
`main`, not from the `base_sha` the cell started at hours earlier.
