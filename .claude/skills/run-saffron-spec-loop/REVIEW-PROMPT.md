# Independent review prompts

Two seats per pull request, each a background `general-purpose` subagent,
dispatched together: **Spec** asks whether the diff does what the spec says,
**Standards** whether it follows what the repo has written down. Read their
reports side by side and never merge or rerank them — a pass on one axis hides
a failure on the other. On SA-0029's packaged head, a single seat walked every
criterion twice and never raised `PhaseName` listing PLAN as a phase, which
`CONTEXT.md` puts on an _Avoid_ line; the Standards seat raised it as a
`blocker` both times (2026-09-13).

Each seat's prompt is **Opening + its seat + Report rules**, verbatim, with
the placeholders filled:

- `{REPO}` — the checkout driving the loop (`git rev-parse --show-toplevel`)
- `{PR}`, `{BRANCH}` (`saffron/SA-NNNN`), `{SPEC}` (the spec's path)
- `{BASE}` — the commit the cell was cut from, on the log's `cell:` line
  (`worktree at <sha>`); for a spec with `depends_on`, the parent's pushed
  head. In run 7, `git merge-base origin/main origin/{BRANCH}` gave `main` as
  it stood at PACKAGE, a later commit, and a witness must fail at the cell's
  base
- `{HEAD}` — `git rev-parse origin/{BRANCH}`
- `{WHAT}` — two sentences on what the diff does, and its `git diff --stat`
- `{KNOWN}` — the in-cell critic's findings you have already verified or
  fixed, and any blocker a lens withdrew after REBUT. Add step 1b's concerns
  for this spec.

## Opening

You are reviewing PR #{PR} (branch `{BRANCH}`) in {REPO}, produced by an agent
in a Saffron cell. `DESIGN.md` is cited by section number.

**What it does:** {WHAT}

**Already raised — re-check each one yourself:** {KNOWN}

**Spec:** `{SPEC}` — read the whole of it, frontmatter and body.

**Range:** `git diff {BASE}..{HEAD}`.

{REPO} is read-only to you, because another process edits it; commits,
pushes and PR comments are the operator's. You are one of two review seats,
each with its own remit: do the whole of yours yourself, and leave the other's.

## Spec seat

Your remit is whether the diff does what the spec asks — no more and no less.
Read `CLAUDE.md` for its invariants.

**Walk the acceptance criteria one at a time, give the file:line that
satisfies each, then try to kill that line with a vacuity probe** — a
find-and-replace edit that breaks the behaviour in a way an inattentive test
would miss: delete it, invert it, a near-miss value, a narrower exception, the
same call on a different path. Run the criterion's witness under each probe and
report killed or survived. A probe that survives its witness is a finding; so is
a criterion satisfied only by a comment. Show each `preserves: true` criterion
still holds, and each new witness failing at `{BASE}`.

Then look past the criteria: behaviour the spec did not ask for; call sites the
fix should also cover; the spec's `touches` boxing the fix in; and anything the
diff does to get past a gate — an alias, an exemption, a disabled check —
reported as its own finding.

Probe in your own worktrees (`git -C {REPO} worktree add /tmp/review-{PR}-spec
{HEAD}`, then `uv sync` inside) and remove them when done. Run only the default
suite; `pytest -m cell` is the operator's. Run every probe with
`PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`, and confirm the edit
applied before reading its result: a stale `.pyc` and an edit that never landed
both read as "survived", and a mutant that raises `TypeError` reads as "killed".
The loop's driver checks all three for you:
`uv run {REPO}/.claude/skills/run-saffron-spec-loop/driver.py probe <file> --find … --replace … --root <worktree> -- uv run pytest …`.

## Standards seat

Your remit is whether the diff follows what this repo has written down. Read
`CLAUDE.md`, `CONTEXT.md` and the `DESIGN.md` sections the diff touches, then
judge every hunk — code, names, comments, docstrings, messages — against them:

- **Vocabulary.** Each term means what its `CONTEXT.md` entry says, and no
  word from an _Avoid_ line appears. A closed set restated in code — phases,
  states, statuses, severities — has exactly the members `CONTEXT.md` and
  `ontology/factory.ttl` give it.
- **Invariants and conventions** in `CLAUDE.md`, each checked against the
  hunks it could reach.
- **One source.** A type, constant or helper the repo already defines is
  imported, not restated.

A gate already enforces formatting, lint, types and the `.saffron/rules/`
structure rules: read `.saffron/gates/` and `saffron/gates/core/` for what each
gate checks, and leave those to it. Read with `git show {HEAD}:<path>` and the
range diff; you need no worktree and run no tests.

## Report rules

Demonstrate every finding with a command and its output, or mark it
unverified. Each finding is one bullet: severity (`blocker`: the diff is wrong
or a witness cannot fail; `concern`: needs the operator's judgement; `note`:
true but trivial), the file:line, the rule or criterion it breaks quoted with
its own file:line, what is wrong, the evidence, and the fix. The operator's
judgement is for a diff that gets past a gate, a fix outside the spec's
`touches`, and a fix incomplete without one; a witness to strengthen inside
`touches` is a `blocker` with its fix.

Report, in this order:

1. **Criteria walk** (Spec seat only) — per criterion: the satisfying
   file:line, each probe, killed or survived.
2. **Findings.**
3. **Out of scope** — real defects outside the spec's `touches`, for the
   backlog.
4. **Assessment** — ready, ready with the listed fixes, or not ready, in two
   sentences, for your remit alone.
