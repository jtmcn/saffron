# Jev noise pre-registration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Carry backlog item b-ef334d to the point where only the measurement is left. Jev stops asking Q6. A PR review round's `pr_seats` label means a later review round. A pre-registration fixes how Q2's noise score on review notes is judged out of sample.

**Architecture:** Three changes, by hand, outside `saffron/`. `harness/jev_observe.py` loses Q6. `driver.py labels` learns a schema-2 rule that a label about a later review round needs that review round. A dated `docs/evidence/` pre-registration takes effect when its pull request merges. The item stays open until the measurement is scored.

**Tech Stack:** Python 3.14, pytest, `uv`, `prek`, `typesafe-sdk` (faked in tests).

**Spec:** `docs/backlog/b-ef334d-jev-sorts-review-notes-and-its-stop-signal-adds-nothing.md`, with its evidence `docs/evidence/2026-10-02-jev-scores-graded.md`.

## Global Constraints

- Touch zero lines of `saffron/` (§2.1). Jev lives in `harness/` and the spec loop's driver.
- Comments are one or two lines naming the non-obvious why.
- New Markdown and comments take no em-dash, semicolon, contraction, perfect tense, hedge or sentence over 25 words. Check each file with `python3 hooks/prose_limit.py --file <path>`.
- Vocabulary from `CONTEXT.md`: "review round", never bare "round" in prose. "Cell", never "sandbox".
- Commit subjects are lowercase `type(scope): what changed`, a sentence about the defect. No co-author line.
- A new test must fail against the unfixed code before the fix lands.
- Schema-1 `labels.json` files already under `~/.saffron/batches/spec-loop/` must keep passing `driver.py labels` unchanged.

## Review Focus

1. A first-round PR review with no findings, and a cell review round with none, ask Jev nothing once Q6 is gone. The driver must skip the call and write no `jev.ttl`, not send an empty request. Task 1 pins it.
2. A killed run can leave an empty `round-N+1` directory (run 24's feedback). The schema-2 check must want `round.json` in it, not just the directory. Task 2 pins it.
3. The 153 schema-1 labelled review rounds on the host must still pass `driver.py labels`. Task 2 runs it before and after.
4. `jev.ttl` files written before this change still carry Q6. The 2026-10-02 grading script must read them with output unchanged. Task 1 reruns it.
5. A schema-2 label that sets `pr_seats` to null on the last PR review round is correct, not a gap. Task 2 pins it.

---

### Task 0: Commit the evidence record and the backlog item

The branch `joel/jev-scores-graded` holds them staged and uncommitted.

- [ ] **Step 1: Commit**

```bash
git commit -m "docs(evidence): jev's scores were never graded, so nobody knew its stop signal reads nothing"
```

---

### Task 1: Jev stops asking Q6

**Files:**
- Modify: `harness/jev_observe.py:162` (drop Q6) and `harness/jev_observe.py:266` (drop the `round` subject branch)
- Modify: `.claude/skills/run-saffron-spec-loop/driver.py:1263-1266` (skip an empty ask)
- Modify: `docs/superpowers/specs/2026-09-21-jev-review-observer-design.md` (a "Changed after measuring" section)
- Test: `tests/test_jev_observe.py:161-180`, `tests/test_jev_driver.py`

**Interfaces:**
- Consumes: `build_asks(r: ReviewRound) -> dict[str, dict]`, `observe(r, client, model) -> tuple[str, list[Answer]]`.
- Produces: `build_asks` never returns a `Q6_*` key. `cmd_jev` returns 0 and writes no `jev.ttl` when `build_asks` returns `{}`.

- [ ] **Step 1: Change the question-set tests to the set without Q6**

In `tests/test_jev_observe.py`, edit the three tests:

```python
def test_a_spec_review_with_an_earlier_round_asks_every_question():
    assert _codes(jo.build_asks(_round("spec-review", prior=1))) == {
        f"Q{n}" for n in range(1, 10) if n != 6
    }


def test_a_pr_review_asks_no_criterion_questions():
    assert _codes(jo.build_asks(_round("pr-review", prior=1))) == {
        "Q1",
        "Q2",
        "Q3",
        "Q4",
        "Q5",
    }


def test_a_cell_asks_nothing_about_earlier_rounds():
    assert _codes(jo.build_asks(_round("cell"))) == {"Q1", "Q2", "Q3"}
```

- [ ] **Step 2: Add the driver test for a review round with nothing to ask**

In `tests/test_jev_driver.py`, after `test_the_first_round_diffs_from_base`:

```python
def test_a_review_round_with_nothing_to_ask_makes_no_call(monkeypatch, loop, capsys):
    first, second, _ = loop.commits
    empty = _report(loop, "r1.md", [])
    argv = ("--report", empty, "--commit", second, "--base", first)
    assert _review(monkeypatch, loop, *argv) == 0
    round_dir = loop.batches / "spec-loop" / "SA-0901" / "pr-review" / "round-1"
    assert (round_dir / "round.json").is_file()
    assert not (round_dir / "jev.ttl").exists()
    assert loop.client.questions == {}
    assert "nothing to ask" in capsys.readouterr().out
```

- [ ] **Step 3: Run both files and watch them fail**

Run: `uv run pytest tests/test_jev_observe.py tests/test_jev_driver.py -q`
Expected: the three set tests FAIL with an extra `Q6`. The new driver test FAILS because a call was made with `Q6_round`.

- [ ] **Step 4: Drop Q6 and the branch only it reached**

In `harness/jev_observe.py`, delete this line from `build_asks`:

```python
    asks["Q6_round"] = _noul("Would another review round surface a blocking finding?")
```

In `to_turtle`, the subject `"round"` came only from Q6. Replace

```python
        subject = f"round-{r.number}" if a.subject == "round" else a.subject
        parts.append(
```

with

```python
        parts.append(
```

and change the subject line in that f-string from `{subject}` to `{a.subject}`:

```python
            f"  earl:subject <urn:software-factory:jev:{r.kind}:{r.spec_id}:{a.subject}> ;\n"
```

- [ ] **Step 5: Skip the call when there is nothing to ask**

In `driver.py` `cmd_jev`, after `(directory / "jev.ttl").unlink(missing_ok=True)`:

```python
    # A first review round with no findings asks Jev nothing, and an empty request is refused.
    if not jev_observe.build_asks(round_):
        print(f"{spec.id}  {args.kind} review round {round_.number}  nothing to ask")
        return 0
```

- [ ] **Step 6: Run the tests and watch them pass**

Run: `uv run pytest tests/test_jev_observe.py tests/test_jev_driver.py -q`
Expected: all PASS.

- [ ] **Step 7: Record the change in the design note**

Append to `docs/superpowers/specs/2026-09-21-jev-review-observer-design.md`:

```markdown
## Changed after measuring

1. **Q6 is no longer asked.** Graded on 2026-10-02 against 153 labelled
   review rounds, it lost to a constant answer in three of five rows. The
   review round's own blocker count beat it for the next spec review round
   (`docs/evidence/2026-10-02-jev-scores-graded.md`, item b-ef334d).
2. **A review round with nothing to ask makes no call.** Without Q6, a first
   review round with no findings has no question left.
```

- [ ] **Step 8: Confirm the old records still grade the same**

Run: `uv run python docs/evidence/scripts/2026-10-02-jev-scores-graded.py | tail -6`
Expected: the six Q6 lines match the evidence record's table, for example `spec-review vs next_spec_round: n=40 base=0.15 Q6 AUC=0.600`.

- [ ] **Step 9: Lint and commit**

```bash
python3 hooks/prose_limit.py --file docs/superpowers/specs/2026-09-21-jev-review-observer-design.md
git add harness/jev_observe.py .claude/skills/run-saffron-spec-loop/driver.py tests/test_jev_observe.py tests/test_jev_driver.py docs/superpowers/specs/2026-09-21-jev-review-observer-design.md
prek run
git commit -m "fix(jev): jev asked whether another review round would find a blocker, and its answer predicted less than a blocker count"
```

---

### Task 2: A label about a later review round needs that review round

**Files:**
- Modify: `.claude/skills/run-saffron-spec-loop/driver.py:1291-1347` (`LABEL_*`, `_label_gaps`, `cmd_labels`)
- Modify: `.claude/skills/run-saffron-spec-loop/SKILL.md:436-441` (what each `blocker_followed` key means)
- Test: `tests/test_jev_driver.py` (after `test_labels_skips_a_round_jev_never_scored`)

**Interfaces:**
- Consumes: `_two_rounds(monkeypatch, loop) -> Path` (the `pr-review` folder holding `round-1` and `round-2`), `_label_all(round_dir, **override)`.
- Produces: `_label_gaps(directory: Path, kind: str) -> list[str]`. The gap text is `"<key> reads review round <n+1>, which never ran"`.

- [ ] **Step 1: Record what the host's labels say now**

Run: `uv run .claude/skills/run-saffron-spec-loop/driver.py labels > "$TMPDIR/labels-before.txt"; echo $?`
Keep the exit code and file for Step 7.

- [ ] **Step 2: Write the failing tests**

```python
def _follow(round_dir: Path, schema: int | None, **followed) -> None:
    path = round_dir / "labels.json"
    doc = json.loads(path.read_text())
    if schema is not None:
        doc["schema"] = schema
    doc["blocker_followed"].update(followed)
    path.write_text(json.dumps(doc))


def test_a_schema_2_label_about_a_later_review_round_needs_that_review_round(
    monkeypatch, loop, capsys
):
    base = _two_rounds(monkeypatch, loop)
    for n in (1, 2):
        _label_all(base / f"round-{n}")
        _follow(base / f"round-{n}", 2, pr_seats=True)
    (base / "round-3").mkdir()
    assert _run(monkeypatch, "labels", "SA-0901") == 1
    out = capsys.readouterr().out
    assert "pr-review round-2  pr_seats reads review round 3, which never ran" in out
    assert "round-1  pr_seats" not in out


def test_a_schema_2_null_on_the_last_review_round_is_no_gap(monkeypatch, loop):
    base = _two_rounds(monkeypatch, loop)
    for n in (1, 2):
        _label_all(base / f"round-{n}")
    _follow(base / "round-1", 2, pr_seats=False)
    _follow(base / "round-2", 2, pr_seats=None)
    assert _run(monkeypatch, "labels", "SA-0901") == 0


def test_a_schema_1_label_keeps_its_old_reading(monkeypatch, loop):
    base = _two_rounds(monkeypatch, loop)
    for n in (1, 2):
        _label_all(base / f"round-{n}")
    _follow(base / "round-2", None, pr_seats=True)
    assert _run(monkeypatch, "labels", "SA-0901") == 0
```

The empty `round-3` directory is Review Focus 2. A run killed before `round.json` was written leaves one.

- [ ] **Step 3: Run them and watch the first fail**

Run: `uv run pytest tests/test_jev_driver.py -q -k "schema"`
Expected: `test_a_schema_2_label_about_a_later_review_round_needs_that_review_round` FAILS on the exit code, 0 against 1. The other two pass, and they guard the schema-1 reading against Step 4.

- [ ] **Step 4: Implement the rule**

In `driver.py`, after `LABEL_FOLLOWED`:

```python
# Which `blocker_followed` key names the next review round of the same kind.
LABEL_LATER = {"spec-review": "next_spec_round", "pr-review": "pr_seats"}
```

Change the signature to `def _label_gaps(directory: Path, kind: str) -> list[str]:`. Before `labels = doc.get("findings") or {}`, add:

```python
    if doc.get("schema") == 2 and isinstance(followed, dict):
        key = LABEL_LATER[kind]
        later = int(directory.name.removeprefix("round-")) + 1
        ran = (directory.parent / f"round-{later}" / "round.json").is_file()
        if followed.get(key) is not None and not ran:
            gaps.append(f"{key} reads review round {later}, which never ran")
```

In `cmd_labels`, change `_label_gaps(directory)` to `_label_gaps(directory, kind)`. Run `grep -n "_label_gaps(" .claude/skills/run-saffron-spec-loop/driver.py` and update any other caller the same way.

- [ ] **Step 5: Run the tests and watch them pass**

Run: `uv run pytest tests/test_jev_driver.py -q`
Expected: all PASS.

- [ ] **Step 6: Say what each key means in the skill**

In `SKILL.md`, replace the paragraph that starts "For the round, record `blocker_followed`." with:

```markdown
For the round, record `blocker_followed` and set `"schema": 2`. Each key says
whether a later stage found a blocker, or holds `null` for a stage that never
ran. `cell_review` is the in-cell REVIEW. On a spec review round,
`next_spec_round` is the next spec review and `pr_seats` is the first PR seat
review. On a PR review round, `pr_seats` is the next PR seat review of the same
pull request, and `next_spec_round` is `null`. A label never reads the review
round it sits in. Schema 1 read `pr_seats` that way, and it graded nothing
(`docs/evidence/2026-10-02-jev-scores-graded.md`). A defect no findings block
carried, such as one you found yourself, goes in `run-NN-unscored.json` beside
the spec folders. Run 13's files show the shape.
```

In the paragraph after the `driver.py labels` block, add "or a schema-2 label that names a later review round which never ran" to the list of gaps.

- [ ] **Step 7: Confirm the host's labels read the same**

Run: `uv run .claude/skills/run-saffron-spec-loop/driver.py labels > "$TMPDIR/labels-after.txt"; echo $?; diff "$TMPDIR/labels-before.txt" "$TMPDIR/labels-after.txt"`
Expected: the same exit code as Step 1 and no diff. Every label on the host is schema 1.

- [ ] **Step 8: Lint and commit**

```bash
python3 hooks/prose_limit.py --file .claude/skills/run-saffron-spec-loop/SKILL.md
git add .claude/skills/run-saffron-spec-loop/driver.py .claude/skills/run-saffron-spec-loop/SKILL.md tests/test_jev_driver.py
prek run
git commit -m "fix(spec-loop): a pr review round's pr_seats label read its own blockers, so it graded nothing"
```

---

### Task 3: The pre-registration, and the item's record

**Files:**
- Create: `docs/evidence/2026-10-02-jev-noise-preregistration.md`
- Modify: `docs/evidence/README.md` (one row)
- Modify: `docs/backlog/b-ef334d-jev-sorts-review-notes-and-its-stop-signal-adds-nothing.md` (done looks like, record)

**Interfaces:**
- Consumes: Task 2's schema-2 labels, and the `ACTED` set in `docs/evidence/scripts/2026-10-02-jev-scores-graded.py`.
- Produces: the values the measurement is held to. The operator approves them by merging.

- [ ] **Step 1: Write the pre-registration**

The pilot figures below were measured on 2026-10-02 over the reviewer's notes alone.

```markdown
# Jev's noise score on review notes: the pre-registration

**PROPOSED.** Every value below is a proposal. It takes effect when the
operator approves the pull request that adds this file. Backlog item b-ef334d.

## The pilot, which counts for nothing

`2026-10-02-jev-scores-graded.md` graded Jev's saved answers by hand labels
nobody pre-registered. Over the reviewer's notes alone, at three cutoffs on
Q2's probability of severity 0:

| Cutoff | not-a-defect flagged | acted on and flagged |
|---|---|---|
| 0.4 | 43 of 63 | 20 of 356 |
| 0.5 | 38 of 63 | 10 of 356 |
| 0.6 | 26 of 63 | 8 of 356 |

## 1. What is scored

Every finding a reviewer marks `note` in a counted spec review or PR review
round. A cell review round is out, since nothing labels it. A note is
flagged when Q2's probability of severity 0 in `jev.ttl` is at least 0.5.

## 2. The two classes

- **Noise.** A note labelled `not-a-defect`.
- **Acted on.** A note labelled `real` whose disposition is anything but
  `no-action`.

A `real` note left alone and an `unverified` note count in neither class.

## 3. The bar

Both counts are required.

- **Catch.** At least half of the noise is flagged.
- **Cost.** At most one acted-on note in twenty is flagged.

## 4. The cutoff

A review round counts when the commit in its `round.json` descends from the
merge commit of this file. `git merge-base --is-ancestor` decides it. Its
`labels.json` carries `"schema": 2` and is written before anyone reads its
`jev.ttl`.

## 5. The stopping rule

Scoring ends at 40 noise notes. A hard stop falls on 2026-12-31 in case they
never arrive. The scorer copies the 2026-10-02 script, adds the cutoff filter
and changes nothing else.

## What the result decides

A pass files an item to let step 1b and step 2c leave a flagged note
unanswered, still saved and labelled. A fail keeps Q2 as an observation and
closes b-ef334d.
```

- [ ] **Step 2: Check its prose**

Run: `python3 hooks/prose_limit.py --file docs/evidence/2026-10-02-jev-noise-preregistration.md`
Expected: a clean count or "out of the gates' scope". Then reread it by hand against the Global Constraints, since the gate does not read `docs/evidence/`.

- [ ] **Step 3: Add the README row**

After the `2026-10-02-jev-scores-graded.md` row in `docs/evidence/README.md`:

```markdown
| `2026-10-02-jev-noise-preregistration.md` | Item b-ef334d: the bar Q2's noise score must pass on review notes scored after its merge. Half the noise caught, at most one acted-on note in twenty flagged. **PROPOSED** until merged. |
```

- [ ] **Step 4: Bring the item's record up to date**

In the backlog item, add a fourth line to "Done looks like":

```markdown
4. The pre-registered measurement is scored, and its result is recorded here.
```

Append to "Record":

```markdown
- 2026-10-02: Q6 dropped, schema-2 labels defined and the pre-registration
  proposed. Point 4 waits on the stopping rule.
```

Set `status: partial`.

- [ ] **Step 5: Check the records and commit**

```bash
uv run pytest tests/records -q
git add docs/evidence/2026-10-02-jev-noise-preregistration.md docs/evidence/README.md docs/backlog/b-ef334d-jev-sorts-review-notes-and-its-stop-signal-adds-nothing.md
prek run
git commit -m "docs(evidence): jev's noise score had no bar it could fail, so a pass would mean nothing"
```

---

### Task 4: Whole-branch check

- [ ] **Step 1: Run the default target**

Run: `make check`
Expected: exit 0.

- [ ] **Step 2: Open the pull request**

Read `.github/pull_request_template.md` first, since `gh pr create --body` skips it. The body names the three pre-registered values for the operator to approve: the 0.5 cutoff, the two bars and the stopping rule.
