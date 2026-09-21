# Dispatching the writer and the reviewer

The shapes that worked across four specs on 2026-09-20. Each field says why it
is there, because a field left out comes back as a question in the report.

## The writer, drafting

Use the `spec-writer` agent.

```
item: <backlog id>

base: <commit>, the head of branch <branch> in the checkout at <path>.
The working tree is a clean snapshot of it. Write the spec there.
Do not commit, and stage nothing.

<What the base carries that the writer would not assume: unmerged specs it
may overlap, a rule added to docs/agents/issue-tracker.md this week, a
command that now exists. One sentence each.>

decisions (settled, do not re-argue):
- <Scope: the item's Done looks like, or the named half of it.>
- <Where a new command lives, when that is already settled.>
- <Which queued spec is the parent, and that it verifies this rather than
  assuming it.>
- <Ceilings to match, when a sibling of the same shape has not run.>

Report back with: the spec's path and id, its touches, depends_on,
ceilings and estimated size, which of the six checks it settled with
evidence, and how each claim that quantifies over a set is driven.
If the estimate splits, lead with that.
```

Hand it the pre-flight commands by name. A writer that knows `driver.py cite`
exists runs it on its own draft. One that does not writes a throwaway resolver
into the repository root to do the same job.

## The reviewer

Use the `spec-reviewer` agent.

```
spec: <path>

base: <commit>, the head of branch <branch> in the checkout at <path>.
The working tree is a clean snapshot of that commit, so plain Read,
Grep and Glob are fine. A cell would be cut from it.

history: run it yourself.

<What the pre-flight already settled, one line per check, so the reviewer
spends its rounds on judgement rather than re-deriving arithmetic.>

<Decisions the operator settled, marked as not open for re-argument.>

Report findings with severities as your instructions define them, say
which of the six checks you settled and on what evidence, and mark
anything you could not verify at base. Where the spec quotes a
measurement, check the number.
```

## The second reviewer

The same shape, plus two things a first review does not need.

- What the first review found. List each finding as applied, answered or
  rejected. The second reader then spends its rounds on what the revision
  introduced.
- The axis the first review missed. Told which class to read for, one reviewer
  found three blockers on a spec a first reviewer called runnable. Name the
  class. Name any criterion the revision removed, since a cut is where stale
  cross-references collect.

## The writer, revising

```
review: the findings below, on spec <path>, which you wrote.
It is committed as <commit> on branch <branch> in the checkout at <path>,
the base the reviewer read at. Revise in place. Do not commit.

<Apply all, unless reading the line at base shows a finding is wrong.
Then say so with the evidence and do not apply it.>

decisions (settled, do not re-argue):
- <Which arm of each design finding to take.>
- <Whether a cut is allowed if the size estimate moves inside 100 lines.>

--- REVIEW ---
<the review, verbatim>
--- END REVIEW ---
```

Pass the review verbatim. A paraphrase is a second citation nobody checked, and
a reviewer's line numbers are what the writer re-reads at the base.
