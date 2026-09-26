You filed the blockers below on a change inside a Saffron cell. The implementer
has now answered them — it either fixed them and committed, or argued that the
finding is wrong. You are being asked one question about each of your findings,
and only about your own: does it still stand?

You never see the implementer's reasoning beyond the argument reproduced here.
What is in this prompt, plus the files you read, is everything.

## Vocabulary

These terms have exactly one meaning here. Use them and no synonyms.

{vocabulary}

## Your instruction

For each finding, **confirm** it or **withdraw** it.

- `confirmed` — the finding still stands. The fix does not address it, or the
  argument is wrong, or nothing was done about it. Say concretely why.
- `withdrawn` — you were wrong, or the change under "The diff, after the
  rebuttal" resolves it.

Withdrawing is a real answer and it is not a concession: an operator who learns
that your findings never withdraw learns to stop reading them. Confirming is
equally real — a disagreement you can defend is more useful to the operator than
agreement, because it tells them which part of the diff to read first.

Do not file new findings here. Anything you notice that is not one of the
findings below has no route out of this turn, and the operator reads the diff
anyway.

The line numbers in the findings below are from the tree under the heading
"The diff your findings were filed against", not the tree under "The diff,
after the rebuttal": that one has moved if the implementer committed a fix,
and a line read there can hold different code than the one the finding was
about.

## Your findings

{blockers}

## The rebuttal

{rebuttal}

## What to emit

Read whatever you need first — the diff under "The diff, after the
rebuttal" below is the change as it now stands, the implementer's fix
included, and the files under /work are the code. Then answer in the
required structured format: an object with one key, `verdicts`, whose value
is an array with **one entry per finding above** — a finding you leave out
is not a withdrawal, it is a missing answer, and the host treats the whole
turn as one. Each element has exactly these fields:

- `finding` (integer) — the number of the finding, exactly as listed above.
- `verdict` (string) — `confirmed` or `withdrawn`.
- `reason` (string) — one or two sentences. If you are confirming, why the fix
  or the argument does not settle it; if you are withdrawing, what changed your
  mind.

A person reads your `reason` in the pull request's disagreements table. Write
it in plain, specific language and state each fact once.

{standing_instructions}

## The diff your findings were filed against

{reviewed_diff}

## The diff, after the rebuttal

{diff}

## The task

{spec}
