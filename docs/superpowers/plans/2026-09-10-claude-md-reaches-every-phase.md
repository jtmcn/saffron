# `CLAUDE.md` Reaches Every Phase — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close `docs/BACKLOG.md` item 7 — every fresh agent session receives the target
repo's `CLAUDE.md`, read host-side at `base_sha` — staged so the lens half is measured
against item 93's spread rather than argued.

**Architecture:** Three stages, one layer of a `gh stack` each, bottom to top in this order.
**Stage 1** injects `CLAUDE.md` into IMPLEMENT only: a new `mirror.file_at` reads it
from the bare mirror at `base_sha`, `context.standing_instructions` renders it as a
substituted value, and `implement.md` gains one placeholder. REPAIR, the implementer's
REBUT turns and the extraction turns resume that session and inherit it (§5.3). **Stage
2** makes the corpus report a per-run total, then runs a `--runs 3` pass under today's
lenses and records the spread item 93 asks for. **Stage 3** freezes `CLAUDE.md` into
every fixture, injects it into the three review lenses and the verdict lenses, and
scores that change against stage 2's spread.

**Tech Stack:** Python 3.13, `uv`, pytest, `apple/container` (stage 2 and 3 passes only),
`ruff` + `ty` + `ast-grep` via `make check`.

**Spec:** `docs/BACKLOG.md` items 7 and 93; `DESIGN.md` §5.3 ("Configuration is loaded
from nowhere" names the fix); `docs/superpowers/plans/2026-09-07-trusting-the-queue.md`
(Track E, and the exit criterion stage 2 feeds).

## Global Constraints

- **`setting_sources: []` stays.** Nothing is read from `/work`. The file comes from the
  mirror at `base_sha` — the commit `.saffron/` is exported from — never the operator's
  working copy and never the worktree (§5.3, Appendix J).
- **`CLAUDE.md` is a substituted value, never a template.** It contains `{` and `}`.
  `build_system_prompt` already passes values as `.format` arguments; never splice it into
  a template string.
- **A repo with no `CLAUDE.md` gets no heading.** `None` or blank renders `""`, the way
  `constraints_block` and `witnesses_block` omit an empty list — a heading over nothing
  invites an invented list.
- **Lenses are not touched until stage 2's pass is recorded.** Stage 1 pins that with a
  test; stage 3 inverts it. Landing the lens half early spends the only clean baseline.
- **TDD, and a new test is not trusted until it has failed against the unfixed code**
  (`CLAUDE.md`). Every task names the mutant its test was run against.
- **`make check` before every commit.** Commit subjects are lowercase
  `type(scope): what changed`, a sentence about the defect, not the file.
- **Comments:** 1–2 lines, the non-obvious why only. Rationale goes in the commit body.
- **Vocabulary:** "cell", "gate result", "lens", "vacuity probe" — `CONTEXT.md` exactly.
- **Git:** stacked pull requests through `gh stack`, one layer per stage (see *The stack*);
  plain `git` for everything else. Branches `joel/<desc>`, under 50 characters. Never bare
  `git stash`. Ask before any push. `gh stack push`/`sync` after a restack rewrite remote
  history — that is a force-push, and needs explicit approval each time.
- **Stage 2 and 3 passes spend money and must not run while a batch is live** — the proxy
  and the `saffron-cells` network are shared (`2026-09-08-lens-corpus.py` docstring).

## The stack

```
(main) <- joel/claude-md-reaches-implementer <- joel/corpus-per-run-spread <- joel/claude-md-reaches-lenses
```

Each layer is one reviewable concern, and the order is the dependency: stage 2's pass must
run on code where only the implementer has changed, and stage 3 is scored against stage 2's
record. **Stacking is safe for stage 2's measurement only because stage 1 touches no lens
prompt** — `test_the_review_lenses_do_not_yet_carry_claude_md` is what holds that, and it
must stay green on layer 1 through every restack.

- **Adopt layer 1** (the branch exists already, with this plan on it):
  `gh stack init joel/claude-md-reaches-implementer`
- **Add a layer** from the top of the one below: `gh stack add <branch>`.
- **Submit** with `gh stack submit --auto` — it pushes every branch and opens a draft PR
  for each new one. Ask before running it.
- **A review fix to a lower layer:** `gh stack checkout <that branch>`, commit there,
  `gh stack rebase --upstack`, `gh stack top`. The push that follows is a force-push — ask.
  Never commit a lower layer's fix on a higher branch.
- **Read state** with `gh stack view --json`, never bare `view` (it opens a TUI).
- **Merge** bottom-up with `gh stack merge <pr> --yes` once approved — never `gh pr merge`.
- This plan document lives on layer 1.

---

# Stage 1 — IMPLEMENT

Layer 1: `joel/claude-md-reaches-implementer` (already created off `main`; adopt it with
`gh stack init joel/claude-md-reaches-implementer` before the first commit).

### Task 1: `mirror.file_at` — one file at a commit, absent distinct from unreadable

**Files:**
- Modify: `saffron/repos/mirror.py` (after `export_saffron_dir`, ~line 206)
- Test: `tests/test_mirror.py`

**Interfaces:**
- Produces: `file_at(mirror: Path, sha: str, path: str) -> str | None` — the file's exact
  text at `sha`; `None` when the tree has no such path; raises `GitError` on a bad `sha`.

- [ ] **Step 1: Write the failing tests**

Add `file_at` to the import block at the top of `tests/test_mirror.py`, then append:

```python
def test_file_at_reads_the_file_as_it_stood_at_the_sha(tmp_path, origin):
    """Two commits disagree on the file, so reading HEAD instead of the sha fails."""
    (origin / "CLAUDE.md").write_text("first rule\n")
    git(origin, "add", "-A")
    git(origin, "commit", "-qm", "rules")
    first = git(origin, "rev-parse", "HEAD")
    (origin / "CLAUDE.md").write_text("second rule\n")
    git(origin, "commit", "-qam", "rules again")
    mirror = ensure_mirror(origin, tmp_path / "mirror")
    assert file_at(mirror, first, "CLAUDE.md") == "first rule\n"


def test_file_at_is_none_for_a_path_the_tree_does_not_have(tmp_path, origin):
    mirror = ensure_mirror(origin, tmp_path / "mirror")
    assert file_at(mirror, git(origin, "rev-parse", "HEAD"), "CLAUDE.md") is None


def test_file_at_raises_on_a_sha_the_mirror_does_not_have(tmp_path, origin):
    """Absent and unreadable are different answers; a bad sha is the second."""
    mirror = ensure_mirror(origin, tmp_path / "mirror")
    with pytest.raises(GitError):
        file_at(mirror, "0" * 40, "CLAUDE.md")
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_mirror.py -k file_at -v`
Expected: collection error — `ImportError: cannot import name 'file_at'`.

- [ ] **Step 3: Implement**

In `saffron/repos/mirror.py`, after `export_saffron_dir`:

```python
def file_at(mirror: Path, sha: str, path: str) -> str | None:
    """`path` as it stood at `sha`, read from the bare mirror; `None` when that
    tree has no such path. A bad `sha` raises: absent is an answer, unreadable is not."""
    if not _git(mirror, "ls-tree", "--name-only", sha, "--", path):
        return None
    # strip=False: the file's own trailing newline is content.
    return _git(mirror, "show", f"{sha}:{path}", strip=False)
```

- [ ] **Step 4: Run the tests, then the mutant**

Run: `uv run pytest tests/test_mirror.py -v` — expected: all PASS.
Mutant: change `f"{sha}:{path}"` to `f"HEAD:{path}"`, rerun, confirm
`test_file_at_reads_the_file_as_it_stood_at_the_sha` FAILS, revert.

- [ ] **Step 5: Commit**

```bash
make check
git add saffron/repos/mirror.py tests/test_mirror.py
git commit -m "feat(mirror): nothing could read one file at a commit and tell absent from unreadable"
```

### Task 2: `context.standing_instructions` and the IMPLEMENT template placeholder

**Files:**
- Modify: `saffron/agents/context.py` (after `witnesses_block`)
- Modify: `saffron/agents/prompts/implement.md` (between `## Hard rules` and `## The paths you are judged against`)
- Test: `tests/test_context.py`

**Interfaces:**
- Produces: `standing_instructions(claude_md: str | None) -> str` — `""` for `None` or
  blank; otherwise a `## This repository's standing instructions` heading, a one-paragraph
  lead, and the file verbatim (trailing whitespace trimmed).
- Produces: `implement.md` now requires a `standing_instructions=` value.

- [ ] **Step 1: Write the failing tests**

In `tests/test_context.py`, add `standing_instructions=""` to `_assembled_implement_prompt`'s
`build_system_prompt` call, then append:

```python
def test_claude_md_reaches_the_implement_prompt_verbatim():
    root = Path(__file__).parent.parent
    rules = "- Never collapse `error` into `fail`.\n- A literal {vocabulary} stays literal.\n"
    prompt = context.build_system_prompt(
        "IMPLEMENT",
        (root / "CONTEXT.md").read_text(),
        template=(root / "saffron/agents/prompts/implement.md").read_text(),
        spec="(the task body)",
        constraints="",
        witnesses="",
        standing_instructions=context.standing_instructions(rules),
    )
    assert "## This repository's standing instructions" in prompt
    assert "- Never collapse `error` into `fail`." in prompt
    assert "A literal {vocabulary} stays literal." in prompt


@pytest.mark.parametrize("absent", [None, "", "  \n\n"])
def test_a_repo_with_no_claude_md_gets_no_standing_instructions_heading(absent):
    assert context.standing_instructions(absent) == ""
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_context.py -v`
Expected: FAIL — `AttributeError: module 'saffron.agents.context' has no attribute 'standing_instructions'`.

- [ ] **Step 3: Implement**

In `saffron/agents/context.py`, after `witnesses_block`:

```python
def standing_instructions(claude_md: str | None) -> str:
    """The target repo's `CLAUDE.md`, as prompt text (§5.3, §8 bucket 2).

    Substituted, never templated — it carries braces. Empty for a repo with
    none: a heading over nothing invites an invented list.
    """
    if claude_md is None or not claude_md.strip():
        return ""
    return "\n".join(
        [
            "## This repository's standing instructions",
            "",
            "The target repo's `CLAUDE.md` as it stood at this task's base commit, "
            "read by the host rather than from /work — an edit to the file there "
            "reaches no session of this task. Where it and the rules above "
            "disagree, the rules above win: the host enforces those.",
            "",
            claude_md.rstrip(),
        ]
    )
```

In `saffron/agents/prompts/implement.md`, insert between the end of `## Hard rules` (the
line `to install anything or reach any service.`) and `## The paths you are judged against`:

```markdown
{standing_instructions}

```

- [ ] **Step 4: Run the tests, then the mutant**

Run: `uv run pytest tests/test_context.py -v` — expected: all PASS.
Mutant: delete the `{standing_instructions}` line from `implement.md`, rerun, confirm
`test_claude_md_reaches_the_implement_prompt_verbatim` FAILS, restore.

- [ ] **Step 5: Commit** — together with Task 3; the template now requires a value that
  `session.py` does not pass yet, so `make check` is red until Task 3 lands. Do not commit
  between them.

### Task 3: session reads `CLAUDE.md` at `base_sha` and passes it to IMPLEMENT only

**Files:**
- Modify: `saffron/cell/session.py:1293-1307`
- Modify: `tests/test_session.py` — `_stub_the_export` (~line 871), `_drive` (~line 891), new tests

**Interfaces:**
- Consumes: `mirror_ops.file_at` (Task 1), `context.standing_instructions` (Task 2).
- Produces: a local `claude_md: str | None` in `run_one_cell`, bound once beside
  `context_md` — stage 3 passes it on to REVIEW and REBUT.

- [ ] **Step 1: Teach the test doubles a base-side file**

In `tests/test_session.py`, give `_stub_the_export` a `base_files` parameter and stub
`file_at` alongside the export. The working copy stands in for `base_sha`'s tree exactly as
`policy=` already does, and `base_files` is the override that makes the two diverge:

```python
def _stub_the_export(monkeypatch, repo, policy=None, recorded=None, base_files=None):
    ...  # existing body unchanged

    def _file_at(_mirror, _sha, path):
        if base_files is not None and path in base_files:
            return base_files[path]
        target = repo / path
        return target.read_text() if target.is_file() else None

    monkeypatch.setattr("saffron.repos.mirror.file_at", _file_at)
```

Give `_drive` two keyword parameters, `claude_md=None` and `base_claude_md=None`. After it
writes `policy.yaml`, add:

```python
    if claude_md is not None:
        (repo / "CLAUDE.md").write_text(claude_md)
```

and change its `_stub_the_export` call to:

```python
    _stub_the_export(
        monkeypatch,
        repo,
        base_policy,
        cell.removed,
        base_files=None if base_claude_md is None else {"CLAUDE.md": base_claude_md},
    )
```

- [ ] **Step 2: Write the failing tests**

After `test_a_spec_with_no_forbidden_shows_no_forbidden_list`:

```python
def test_the_implement_prompt_carries_claude_md_at_the_base_commit(
    monkeypatch, tmp_path
):
    """Item 7. The working copy and the base disagree, so a read of either the
    operator's checkout or /work instead of the mirror at base_sha fails here."""
    cell = _stub_the_runtime(monkeypatch)
    _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
        claude_md="working-copy rule\n",
        base_claude_md="base-commit rule\n",
    )
    prompt = cell.system_prompts[0]
    assert "base-commit rule" in prompt
    assert "working-copy rule" not in prompt


def test_a_repo_with_no_claude_md_implements_with_no_standing_instructions(
    monkeypatch, tmp_path
):
    cell = _stub_the_runtime(monkeypatch)
    _drive(monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PLAN)), _turn()])
    assert "standing instructions" not in cell.system_prompts[0]


def test_the_review_lenses_do_not_yet_carry_claude_md(monkeypatch, tmp_path):
    """Staged, not forgotten: a lens prompt change moves the corpus, and item 93's
    spread is measured under today's lenses first. Stage 3 inverts this test."""
    cell = _stub_the_runtime(monkeypatch)
    _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
        base_claude_md="base-commit rule\n",
    )
    assert len(cell.system_prompts) > 1  # REVIEW ran
    assert all("base-commit rule" not in p for p in cell.system_prompts[1:])
```

- [ ] **Step 3: Run them to verify they fail**

Run: `uv run pytest tests/test_session.py -k "claude_md or standing_instructions" -v`
Expected: the whole module errors on `KeyError: 'standing_instructions'` (Task 2's template),
or, once that is passed as `""`, `test_the_implement_prompt_carries_claude_md_at_the_base_commit`
FAILS on its first assert. The third test passes already — it pins a property that is
true; its mutant is in Step 5.

- [ ] **Step 4: Implement**

In `saffron/cell/session.py`, replace lines 1294–1307:

```python
        context_md = (_SAFFRON_ROOT / "CONTEXT.md").read_text()
        # From the mirror at base_sha, never /work — item 7, §5.3.
        claude_md = mirror_ops.file_at(mirror, spec.base_sha, "CLAUDE.md")
        template = (_SAFFRON_PKG / "agents" / "prompts" / "implement.md").read_text()
        system_prompt = context.build_system_prompt(
            "IMPLEMENT",
            context_md,
            template=template,
            spec=spec.body,
            # The body is prose; the paths the plan and the diff are judged
            # against live in frontmatter and policy.yaml, so they are injected.
            constraints=context.constraints_block(
                spec.touches, spec.forbidden, policy.protected
            ),
            witnesses=context.witnesses_block(spec.acceptance),
            standing_instructions=context.standing_instructions(claude_md),
        )
```

- [ ] **Step 5: Run the tests, then two mutants**

Run: `uv run pytest tests/test_session.py tests/test_context.py tests/test_mirror.py -v`
Expected: all PASS.
Mutant A: replace the `file_at` call with
`(repo / "CLAUDE.md").read_text() if (repo / "CLAUDE.md").is_file() else None`
(adjusting for the working-copy parameter's name in `run_one_cell`) — the base-commit test
must FAIL. Revert.
Mutant B: add `standing_instructions=` to the REVIEW path by prepending
`context.standing_instructions(claude_md)` to `spec_body` at the `review.run_review` call
(~line 1818) — the lens test must FAIL. Revert.

- [ ] **Step 6: Commit (Tasks 2 and 3 together)**

```bash
make check
git add saffron/agents/context.py saffron/agents/prompts/implement.md \
  saffron/cell/session.py tests/test_context.py tests/test_session.py
git commit -m "fix(session): the implementer never saw the repo's CLAUDE.md, so bucket 2 had no reader"
```

### Task 4: Record stage 1 where the documents say it is inert

**Files:**
- Modify: `DESIGN.md` §5.3 — the "Configuration is loaded from nowhere" paragraph (~line 644)
- Modify: `.saffron/rejections.md` — the bucket-2 entry (~line 42) and the summary table (~line 175)
- Modify: `docs/BACKLOG.md` — item 7, and its place in the tier-1 index

- [ ] **Step 1: `DESIGN.md` §5.3.** Replace the paragraph's last sentence ("The cost of the
  pin is that the repo's `CLAUDE.md` no longer loads either — …") with: "The pin also stops
  the repo's `CLAUDE.md` loading, so the host injects it instead: read from the mirror at
  `base_sha`, never from the tree the agent can rewrite, and substituted as a value like the
  spec body. IMPLEMENT receives it, and the sessions that resume IMPLEMENT inherit it; the
  review and verdict lenses do not yet — that change is staged behind the corpus measurement
  in `docs/BACKLOG.md` item 93." Do not edit Appendix J: appendices narrate what was found.
- [ ] **Step 2: `.saffron/rejections.md`.** On the bucket-2 entry, replace
  "**Inert:** item 7, `setting_sources: []`." with "**Live for the implementer** from
  Task 3's commit (cite its subject — a stacked layer has no merge sha yet); the lenses
  follow item 93." In the summary table, replace
  `inert, item 7` with `live for IMPLEMENT; lenses staged`. Leave the dated prose reading
  below the table as written — it records what was true on 2026-09-09.
- [ ] **Step 3: `docs/BACKLOG.md` item 7.** Add under the heading:
  "**Status: IMPLEMENT done, 2026-09-10; the lenses are open.** `mirror.file_at` reads
  `CLAUDE.md` at `base_sha` and `context.standing_instructions` injects it into IMPLEMENT,
  which REPAIR, REBUT and the extraction turns resume. The three review lenses and the
  verdict lenses still receive none, deliberately: a lens prompt change moves the corpus, and
  item 93's spread is measured first
  (`docs/superpowers/plans/2026-09-10-claude-md-reaches-every-phase.md`)."
- [ ] **Step 4: Commit and offer layer 1 for review**

```bash
make check
git add DESIGN.md .saffron/rejections.md docs/BACKLOG.md \
  docs/superpowers/plans/2026-09-10-claude-md-reaches-every-phase.md
git commit -m "docs(design): three documents called CLAUDE.md inert after the implementer began reading it"
```

Ask the operator, then `gh stack submit --auto` — it opens layer 1's draft PR against `main`.
Stage 2 does not wait for it to merge.

---

# Stage 2 — item 93's spread, under today's lenses

Layer 2: from the top of layer 1, `gh stack add joel/corpus-per-run-spread`. The pass below
runs on code that includes layer 1; that measures the same lenses as the baseline only
because layer 1 touches no lens prompt — confirm
`test_the_review_lenses_do_not_yet_carry_claude_md` is green before Task 6.

### Task 5: The corpus reports each run's own total

**Files:**
- Modify: `harness/corpus.py` — `score_corpus` docstring, new `graded_per_run`, `render_corpus_table`
- Modify: `docs/evidence/scripts/2026-09-08-lens-corpus.py:518-527` — pass `per_run=`
- Test: `tests/test_corpus.py`

**Interfaces:**
- Produces: `graded_per_run(fixtures, runs) -> list[CorpusScore | None]` — run index `k`
  scored alone as a whole corpus pass; `None` where no fixture's run `k` survived scoring.
- Produces: `render_corpus_table(..., per_run: Sequence[CorpusScore | None] = ())` — renders
  a `Per run` line under the headline only when `len(per_run) > 1`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_corpus.py`:

```python
def _dirty_restore_seen():
    # SA-0062's `dirty-restore`: correctness-owned, blocker floor, 386-426.
    return _finding("saffron/cell/worktree.py", 400, "restores over uncommitted work")


def test_each_run_is_scored_as_its_own_corpus_pass(sa0062):
    """Item 93. The headline counts a defect graded in any run, so it rises with
    --runs; the per-run totals are the spread, and they disagree here."""
    runs = {sa0062.spec_id: [_run([_dirty_restore_seen()]), _run()]}
    assert corpus.score_corpus([sa0062], runs).graded == 1
    per_run = corpus.graded_per_run([sa0062], runs)
    assert [(s.graded, s.declared) for s in per_run] == [(1, 2), (0, 2)]


def test_the_table_prints_the_per_run_totals_beside_the_best_of_n_headline(sa0062):
    runs = {sa0062.spec_id: [_run([_dirty_restore_seen()]), _run()]}
    table = corpus.render_corpus_table(
        [sa0062],
        corpus.score_corpus([sa0062], runs),
        corpus.anchored_blockers(runs),
        per_run=corpus.graded_per_run([sa0062], runs),
    )
    assert table.splitlines()[0].startswith("**1/2 declared defects graded**")
    assert "Per run, each scored alone: 1/2 · 0/2 graded" in table


def test_a_single_run_pass_prints_no_per_run_line(sa0062):
    """The baseline's `table.md` is pinned; one run has no spread to state."""
    runs = {sa0062.spec_id: [_run()]}
    table = corpus.render_corpus_table(
        [sa0062],
        corpus.score_corpus([sa0062], runs),
        corpus.anchored_blockers(runs),
        per_run=corpus.graded_per_run([sa0062], runs),
    )
    assert "Per run" not in table


def test_a_run_index_no_fixture_survived_reads_as_unscored_not_zero(sa0062):
    errored = [LensReview(lens="correctness", findings=[], error="boom")]
    runs = {sa0062.spec_id: [_run(), errored]}
    assert corpus.graded_per_run([sa0062], runs)[1] is None
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_corpus.py -k "per_run or each_run or no_fixture_survived" -v`
Expected: FAIL — `AttributeError: module 'harness.corpus' has no attribute 'graded_per_run'`.

- [ ] **Step 3: Implement**

In `harness/corpus.py`, correct `score_corpus`'s docstring — its second paragraph claims the
aggregate is comparable across depths, and best-of-n rises with n:

```python
    """k/n per fixture, and one aggregate over defects.

    `seen` and `graded` count *defects*, not runs: a defect seen in any run
    counts once. That makes the aggregate best-of-n, which rises with
    `--runs` — compare passes of different depth through `graded_per_run`,
    never through this.
    """
```

After `score_corpus`:

```python
def graded_per_run(
    fixtures: Sequence[Fixture],
    runs: Mapping[str, Sequence[Sequence[LensReview]]],
) -> list[CorpusScore | None]:
    """Run index k across every fixture, scored alone as one corpus pass —
    one sample of the aggregate per run, which is the spread item 93 asks for.
    `None` where no fixture's run k survived: unscored, never zero."""
    depth = max((len(r) for r in runs.values()), default=0)
    out: list[CorpusScore | None] = []
    for k in range(depth):
        sliced = {sid: list(r[k : k + 1]) for sid, r in runs.items() if len(r) > k}
        try:
            out.append(score_corpus(fixtures, sliced))
        except LensErrored:
            out.append(None)
    return out
```

In `render_corpus_table`, add the parameter `per_run: Sequence[CorpusScore | None] = ()`
after `probes`, and after the headline line (before the blank line and the table header):

```python
    if len(per_run) > 1:
        totals = " · ".join(
            "unscored" if s is None else f"{s.graded}/{s.declared}" for s in per_run
        )
        lines += [
            "",
            f"Per run, each scored alone: {totals} graded. The headline counts a "
            "defect graded in any run, so it rises with `--runs`; these are the spread.",
        ]
```

(`lines` starts as a list whose first element is the headline — restructure so the headline
is appended first, then this block, then the blank line and table header.)

In `docs/evidence/scripts/2026-09-08-lens-corpus.py`, add to the `render_corpus_table` call:

```python
        per_run=corpus.graded_per_run(fixtures, runs),
```

- [ ] **Step 4: Run the tests, then the mutant**

Run: `uv run pytest tests/test_corpus.py -v` — expected: all PASS, including
`test_the_baseline_pass_s_published_aggregate_is_re_derivable` (its headline is line 0 and
the baseline is one run, so no per-run line appears).
Mutant: in `graded_per_run`, slice `r[: k + 1]` instead of `r[k : k + 1]` — the first test
must FAIL (run 2 becomes best-of-2 and reads `1/2`). Revert.

- [ ] **Step 5: Commit**

```bash
make check
git add harness/corpus.py docs/evidence/scripts/2026-09-08-lens-corpus.py tests/test_corpus.py
git commit -m "fix(harness): the corpus headline was best-of-n and its docstring called it comparable across depths"
```

### Task 6: Run the `--runs 3` pass — operator step

Needs `CLAUDE_CODE_OAUTH_TOKEN`, a live cell runtime, the images, and no batch running.
Measured cost of one run over eight fixtures is $16.53, so expect ~$50; the default
`--max-spend-usd 20` would stop it after three or four fixtures. Estimated 3–4 hours.

- [ ] **Step 1: Pre-flight**

```bash
pgrep -fl 'saffron (batch|cell)' || echo 'nothing running'
container system status
container image list | grep -E 'saffron/(cell-base|proxy)'
```

- [ ] **Step 2: Run it (fish)**

```fish
env CLAUDE_CODE_OAUTH_TOKEN=(bash -c 'source ~/.secrets; printf %s $CLAUDE_CODE_OAUTH_TOKEN') \
  uv run python docs/evidence/scripts/2026-09-08-lens-corpus.py \
  --fixtures docs/evidence/fixtures --out ~/.saffron/lens-corpus-spread \
  --runs 3 --max-spend-usd 60
```

On a `--max-spend-usd` trip or a crash, rerun the same command with `--skip-existing`.
Note: `--skip-existing` keys on `run-1.json`, so a fixture interrupted between runs 1 and 3
is skipped with fewer runs — check every fixture has `run-1.json`…`run-3.json` before
recording, and delete a short fixture's directory and resume if one does not.

- [ ] **Step 3: Copy the raw runs into the repo**, the same layout as the baseline pass:

```bash
dest=docs/evidence/passes/2026-09-XX-lens-corpus-spread   # the pass's date
mkdir -p $dest
cp ~/.saffron/lens-corpus-spread/table.md $dest/
for d in ~/.saffron/lens-corpus-spread/SA-*; do
  name=$(basename "$d"); mkdir -p "$dest/$name"; cp "$d"/run-*.json "$d/probes.json" "$dest/$name/"
done
```

### Task 7: The spread record, pinned

**Files:**
- Create: `docs/evidence/2026-09-XX-lens-corpus-spread.md`
- Modify: `tests/test_corpus.py` — a re-derivation test for the new pass
- Modify: `docs/BACKLOG.md` item 93; `docs/superpowers/plans/2026-09-07-trusting-the-queue.md` exit criterion 3

- [ ] **Step 1: Write the pin first** — append to `tests/test_corpus.py`:

```python
SPREAD = REPO / "docs" / "evidence" / "passes" / "2026-09-XX-lens-corpus-spread"
SPREAD_RECORD = REPO / "docs" / "evidence" / "2026-09-XX-lens-corpus-spread.md"


def test_the_spread_pass_s_per_run_totals_are_re_derivable():
    """Item 93's number, recomputed from the runs beside it, never read off prose."""
    fixtures = corpus.load_corpus(FIXTURES)
    runs = {
        f.spec_id: [
            lens_scoring.reviews_from_json(p.read_text())
            for p in sorted((SPREAD / f.spec_id).glob("run-*.json"))
        ]
        for f in fixtures
    }
    assert all(len(r) == 3 for r in runs.values())
    per_run = corpus.graded_per_run(fixtures, runs)
    line = next(
        line for line in (SPREAD / "table.md").read_text().splitlines()
        if line.startswith("Per run")
    )
    totals = " · ".join(f"{s.graded}/{s.declared}" for s in per_run if s is not None)
    assert totals in line
    assert line in SPREAD_RECORD.read_text()
```

Run it — it FAILS (`StopIteration` or a missing path) until the record exists.

- [ ] **Step 2: Write the record** in the baseline record's shape
  (`docs/evidence/2026-09-09-lens-corpus-baseline.md`): *What was run* (the exact command,
  invocations, resumes); *The corpus table* pasted verbatim from `table.md`, per-run line
  included; *The spread* — the three per-run totals plus the baseline's 3/12 as a fourth
  sample of the same lenses, their range, and what the range means for exit criterion 3
  (`B = 3`); *Cost* per fixture, and whether $60 held; *Deviations*. Every number is read off
  `table.md` or the run JSON — none is typed from memory.
- [ ] **Step 3: Run the pin** — `uv run pytest tests/test_corpus.py -k spread -v` — PASS.
  Mutant: edit one total in the record's `Per run` line; it must FAIL. Revert.
- [ ] **Step 4: Update item 93** with a dated status line naming the record, the four
  samples, and the range; leave its confound half (a pass under the pre-probe prompt) open.
  In the trusting-the-queue plan's exit criterion 3, cite the record beside the baseline's.
- [ ] **Step 5: Commit and offer layer 2 for review**

```bash
make check
git add docs/evidence/ tests/test_corpus.py docs/BACKLOG.md docs/superpowers/plans/2026-09-07-trusting-the-queue.md
git commit -m "docs(evidence): the corpus had one sample of its aggregate and nobody knew the metric's resolution"
```

Ask the operator, then `gh stack submit --auto` — layer 2's draft PR is based on layer 1.
Task 5 can be submitted on its own before the pass if review should start early; the record
then lands as a second commit on the same layer.

---

# Stage 3 — the lenses, scored against the spread

Layer 3: from the top of layer 2, `gh stack add joel/claude-md-reaches-lenses`. Start it
only once layer 2's record is committed — Task 10 scores against it.

### Task 8: Every fixture freezes `CLAUDE.md` at its base

`CLAUDE.md` exists at all eight fixture bases (checked 2026-09-10 with
`git cat-file --batch-check`: three distinct blobs).

**Files:**
- Modify: `harness/lens_scoring.py:43-48` (`FROZEN`) and `Fixture` (a `claude_md` property)
- Modify: `harness/recovery.py:50-57` (`FIXTURE_FILES`) and `recover_fixture` (~line 296)
- Create: `docs/evidence/fixtures/*/claude.md` (eight files)
- Test: `tests/test_corpus.py` — the reproduce-from-git test; `one_defect_fixture`'s copy list

- [ ] **Step 1: Extend the reproduction test first.** In
  `test_every_shipped_fixture_s_spec_body_and_context_reproduce_from_git`, after the
  `context_md` assert:

```python
        claude_md = subprocess.run(
            ["git", "show", f"{fixture.base_sha}:CLAUDE.md"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert claude_md == fixture.claude_md, fixture.spec_id
```

  Add `"claude.md"` to `one_defect_fixture`'s copied names.
  Run: `uv run pytest tests/test_corpus.py -k reproduce_from_git -v` — FAIL,
  `AttributeError: 'Fixture' object has no attribute 'claude_md'`.

- [ ] **Step 2: Implement.** `FROZEN["claude_md"] = "claude.md"`; on `Fixture`:

```python
    @property
    def claude_md(self) -> str:
        return self._frozen("claude_md")
```

  In `harness/recovery.py`, add `"claude.md"` to `FIXTURE_FILES` after `"context.md"`, and in
  `recover_fixture` beside `context_md`:
  `claude_md = _git(repo, "show", f"{base}:CLAUDE.md")`, returned as `"claude.md": claude_md`.
  Check `recovery._git` strips output: if it does, `context.md` and `claude.md` must both be
  written the same way the test reads them, so compare one recovered `context.md` against its
  shipped file before backfilling.

- [ ] **Step 3: Backfill the eight fixtures**, unstripped, exactly as the test reads them:

```bash
for f in docs/evidence/fixtures/SA-*/; do
  git show "$(grep '^base_sha' $f/fixture.toml | cut -d'"' -f2):CLAUDE.md" > $f/claude.md
done
```

- [ ] **Step 4: Run the tests, then the mutant.** `uv run pytest tests/test_corpus.py -v` — PASS.
  Mutant: overwrite one fixture's `claude.md` with `git show HEAD:CLAUDE.md`; the reproduction
  test must FAIL. Restore it.
- [ ] **Step 5: Commit**

```bash
make check
git add harness/ docs/evidence/fixtures/ tests/test_corpus.py
git commit -m "feat(harness): a fixture froze every prompt input but the one the lenses were about to receive"
```

### Task 9: The review and verdict lenses receive `CLAUDE.md`

**Files:**
- Modify: `saffron/phases/review.py` — `lens_prompt`, `run_review` (required `claude_md: str | None`)
- Modify: `saffron/phases/rebut.py` — `verdict_prompt`, `run_rebut` (required `claude_md: str | None`)
- Modify: `saffron/agents/prompts/review-{correctness,contract,adequacy}.md`, `rebut-verdict.md`
- Modify: `saffron/cell/session.py` — the `run_review` (~1818) and `run_rebut` (~1920) calls
- Modify: `docs/evidence/scripts/2026-09-08-lens-corpus.py:435` and `2026-09-07-lens-scoring.py:162`
- Test: `tests/test_review.py`, `tests/test_rebut.py`, `tests/test_session.py`, `tests/test_events.py`

**Interfaces:**
- Consumes: `context.standing_instructions` (Task 2), `claude_md` local in `run_one_cell` (Task 3),
  `Fixture.claude_md` (Task 8).
- Produces: `lens_prompt(lens, *, context_md, claude_md, prompts_dir, spec_body, diff, gates)`,
  `run_review(..., context_md, claude_md, ...)`, `verdict_prompt(..., context_md, claude_md, ...)`,
  `run_rebut(..., context_md, claude_md, ...)` — required keywords, never defaulted, the
  module's existing rule for `spec_id` and `agent`.

- [ ] **Step 1: Write the failing tests.** In `tests/test_review.py`:

```python
@pytest.mark.parametrize("lens", sorted(review.LENSES))
def test_each_lens_prompt_carries_the_repo_s_claude_md(lens):
    prompt = review.lens_prompt(
        lens,
        context_md=CONTEXT_MD,
        claude_md="- Never collapse `error` into `fail`.\n",
        prompts_dir=PROMPTS,
        spec_body="fix the gap",
        diff=DIFF,
        gates="- tests: pass (pytest 8.0)",
    )
    assert "## This repository's standing instructions" in prompt
    assert "- Never collapse `error` into `fail`." in prompt
```

  In `tests/test_rebut.py`, the same assertion against `rebut.verdict_prompt(...,
  claude_md="- Never collapse `error` into `fail`.\n", ...)`, built like
  `test_the_verdict_prompt_carries_the_argument_the_finding_and_the_new_diff`.

  In `tests/test_session.py`, **invert** `test_the_review_lenses_do_not_yet_carry_claude_md`
  into `test_every_review_lens_carries_claude_md_at_the_base_commit`: pass
  `claude_md="working-copy rule\n"` too, and assert every `cell.system_prompts[1:]` entry
  contains `"base-commit rule"` and none contains `"working-copy rule"`. Delete the
  "Staged, not forgotten" docstring.

  Add `claude_md=None` to the existing calls at `tests/test_review.py:69` and `:335`,
  `tests/test_rebut.py:102`, `:296` and `:322`, and `tests/test_events.py:1498` and `:1533`.

  Run: `uv run pytest tests/test_review.py tests/test_rebut.py tests/test_session.py tests/test_events.py -v`
  Expected: FAIL — `TypeError: ... unexpected keyword argument 'claude_md'`.

- [ ] **Step 2: Templates.** In each of `review-correctness.md`, `review-contract.md` and
  `review-adequacy.md`, insert directly above `## The gate results`:

```markdown
{standing_instructions}

```

  In `rebut-verdict.md`, insert the same two lines directly above the `## ` heading of the
  section holding `{diff}`.

- [ ] **Step 3: Implement.** `lens_prompt` gains `claude_md: str | None` after `context_md`
  and passes `standing_instructions=context.standing_instructions(claude_md)` to
  `build_system_prompt`; `run_review` gains the same required keyword and forwards it to
  `lens_prompt`. Likewise `verdict_prompt` and `run_rebut` (forwarded at the `verdict_prompt`
  call, ~line 523). In `session.py`, pass `claude_md=claude_md` at both calls. In the corpus
  driver pass `claude_md=fixture.claude_md`; in the frozen single-fixture driver pass
  `claude_md=None` with the comment `# Its recorded passes ran with none (item 7).`

- [ ] **Step 4: Run the tests, then the mutant.** `make check` — all PASS.
  Mutant: in `review.lens_prompt`, pass `standing_instructions=context.standing_instructions(None)`;
  the parametrized lens test and the session test must FAIL. Revert.

- [ ] **Step 5: Docs.** `DESIGN.md` §5.3: replace stage 1's "the review and verdict lenses do
  not yet — …" clause with "every fresh session — the three review lenses and the verdict
  lenses — receives it too, because a critic judging a diff against invariants it was never
  shown is judging against nothing." `docs/BACKLOG.md` item 7: status **done**, citing the
  merge and the stage-3 record. `.saffron/rejections.md` table: `live in every phase`.

- [ ] **Step 6: Commit** — do not run `gh stack submit` while layer 3 is unrecorded: it
  pushes every layer and would open layer 3's PR before Task 10's record exists.

```bash
make check
git add saffron/ tests/ docs/evidence/scripts/ DESIGN.md docs/BACKLOG.md .saffron/rejections.md
git commit -m "fix(review): no lens was shown the invariants it judged a diff against"
```

### Task 10: Score the change against the spread — operator step

- [ ] **Step 1: Run the same pass on this branch**, Task 6's command with
  `--out ~/.saffron/lens-corpus-claude-md`. Same `--runs 3`, same cost (~$50), same
  pre-flight; the prompts are longer by `CLAUDE.md`, so watch the per-fixture cost against
  the $60 ceiling and raise it rather than resume blind.
- [ ] **Step 2: Copy and pin** as in Tasks 6–7, into
  `docs/evidence/passes/<date>-lens-corpus-claude-md/`, with a re-derivation test of the same
  shape.
- [ ] **Step 3: Write the record** beside the spread record. The comparison is the two
  per-run ranges, and the decision rule is fixed now, before the numbers exist:
  - **ranges do not overlap, new above** — the change helped at this resolution; say so.
  - **ranges overlap** — no measurable difference at n=3; say that, not "no effect".
  - **ranges do not overlap, new below** — stop. Do not submit layer 3; bring the record to
    the operator. `CLAUDE.md` may be crowding out the lens remit, which is the cost §5.3's
    per-phase slicing names. Layers 1 and 2 stand on their own and can merge without it.
- [ ] **Step 4: Commit the record and offer layer 3 for review** — ask, then
  `gh stack submit --auto`. Merge bottom-up with `gh stack merge <layer-3 pr> --yes` once all
  three are approved, or merge a lower layer alone by passing its PR number.

---

## Self-review notes

- **Coverage.** Item 7's "done looks like" (host-side, from the mirror, like `CONTEXT.md`):
  Tasks 1–3, then 9. Item 93's "higher `--runs` under the current prompt first": Tasks 5–7.
  The user's staging (IMPLEMENT → spread → lenses): the stage order and the Task 3 pin that
  Task 9 inverts. The confound half of item 93 stays open by design (Task 7 Step 4).
- **What this does not verify.** `recovery._git`'s stripping behaviour (Task 8 Step 2 checks
  it before backfilling). The ~3–4 hour pass time is an estimate from the baseline's ~80
  minutes at `--runs 1`; the $50 is arithmetic over the measured $16.53.
- **Stacking.** One `gh stack`, three layers, bottom-up in stage order. The one property
  stacking puts at risk — stage 2 measuring lenses that layer 1 changed — is held by a test
  on layer 1, and layer 3 is not submitted until its own record exists.
- **Names used across tasks:** `file_at`, `standing_instructions`, `claude_md` (the local,
  the keyword and the `Fixture` property), `graded_per_run`, `per_run=`. Consistent throughout.
