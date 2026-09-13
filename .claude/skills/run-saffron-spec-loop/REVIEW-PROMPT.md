# Independent review prompt

One background `general-purpose` subagent per pull request. Fill the
placeholders; send everything below the rule verbatim.

- `{REPO}` — the checkout driving the loop (`git rev-parse --show-toplevel`)
- `{PR}`, `{BRANCH}` (`saffron/SA-NNNN`), `{SPEC}` (the spec's path)
- `{BASE}` — `git merge-base origin/main origin/{BRANCH}`; for a spec with
  `depends_on`, `origin/saffron/<parent id>` in place of `origin/main`
- `{HEAD}` — `git rev-parse origin/{BRANCH}`
- `{WHAT}` — two sentences on what the diff does, and its `git diff --stat`
- `{KNOWN}` — the in-cell critic's findings you have already verified or
  fixed, and any blocker a lens withdrew after REBUT

---

You are reviewing PR #{PR} (branch `{BRANCH}`) in {REPO},
produced by an agent in a Saffron cell. Read `CLAUDE.md` first: its invariants
and vocabulary apply, and `DESIGN.md` is cited by section number.

**What it does:** {WHAT}

**Already raised — re-check each one yourself:** {KNOWN}

**Requirements:** read the whole spec, frontmatter and body: `{SPEC}`.

**Range:** `git diff {BASE}..{HEAD}`.

**Walk the acceptance criteria one at a time, give the file:line that
satisfies each, then try to kill that line with a vacuity probe** — a
find-and-replace edit that breaks the behaviour in a way an inattentive test
would miss: delete it, invert it, a near-miss value, a narrower exception, the
same call on a different path. Run the criterion's witness under each probe and
report killed or survived. A probe that survives its witness is a finding; so is
a criterion satisfied only by a comment. Show each `preserves: true` criterion
still holds, and each new witness failing at `{BASE}`.

Then look past the criteria: call sites the fix should also cover; the spec's
`touches` boxing the fix in; and anything the diff does to get past a gate — an
alias, an exemption, a disabled check — reported as its own finding.

Demonstrate every finding with a command and its output, or mark it unverified.

**Working copy:** {REPO} is read-only to you, because another process edits
it. Probe in your own worktrees
(`git -C {REPO} worktree add /tmp/review-{PR} {HEAD}`, then
`uv sync` inside) and remove them when done. Run only the default suite;
`pytest -m cell`, pushing, committing and commenting on the PR are left to the
operator. You are the only review seat, so do the whole review yourself.

**Report, in this order:**

1. **Criteria walk** — per criterion: the satisfying file:line, each probe,
   killed or survived.
2. **Findings** — each with a severity (`blocker`: the diff is wrong or a
   witness cannot fail; `concern`: needs the operator's judgement; `note`: true
   but trivial), file:line, what is wrong, the command and output that
   demonstrate it, and the fix.
3. **Out of scope** — real defects outside the spec's `touches`, for the
   backlog.
4. **Assessment** — ready, ready with the listed fixes, or not ready, in two
   sentences.
