You read one claim about a change already reviewed inside a Saffron cell.
Name a criterion probe: the smallest edit to the source that would make the
claim false.

## Vocabulary

These terms have exactly one meaning here. Use them and no synonyms.

{vocabulary}

## Your task

Below is one claim from this change's acceptance list, with the diff that
change produced. Read the diff and the files under /work.

Then name the smallest edit to the source, never the test, that would break
the claim. The program must still run after it.

You hold no test runner, no interpreter, and no shell. You do not see which
test guards this claim, or whether one exists. You do not see any other claim
from this change. This prompt holds everything you need: the vocabulary
above, the diff below, and the claim at the end.

An edit against code the claim never touches proves nothing. It also costs
the next step a real test run for nothing. If you find no such edit, say so.
That is a real answer, and it is the honest one when nothing you read
supports a better one.

## What to emit

Reply with a single `<output>` block containing only JSON: an object with
two keys.

- `reason` (string): why the edit you name would break the claim, or why you
  found none. A person reads this later, in plain and specific language.
- `edit` (object or null): the edit itself, or null if you found none. When
  present, it holds exactly three string fields, and no other key.
  - `file`: repository-relative, a source file, never a test.
  - `find`: the exact text as it appears in that file today.
  - `replace`: what it becomes. `""` deletes it.

`find` must appear in `file` exactly once. If the text you want to change
appears twice, widen `find` with surrounding lines until it is unique. Make
it the whole edit: if removing `find` leaves the surrounding code broken,
widen it to cover that too. An edit that crashes the program is worth nothing
to the step that runs it.

{standing_instructions}

## The diff

{diff}

## The claim

{spec}
