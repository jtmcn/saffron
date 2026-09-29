You read a list of wrong versions of one change already reviewed inside a
Saffron cell. Each version is a sentence a person wrote about how the change
could have gone wrong. Turn each into the smallest source edit that would
make the code match it.

## Vocabulary

These terms have exactly one meaning here. Use them and no synonyms.

{vocabulary}

## Your task

Below is the diff the change produced, the wrong versions its author
listed against one claim, and that claim from the change's acceptance list.
Read the diff and the files under /work.

For each wrong version, in order, name the smallest edit to the source,
never the test, that would make the code match it. The program must still
run after the edit. A version you cannot express as one edit gets a null
edit and a reason why.

You hold no test runner, no interpreter, and no shell. You are not told
which test guards this claim, or whether one exists. You are shown no other
claim from this change. This prompt holds everything you need: the
vocabulary above, the diff, the wrong versions, and the claim below.

An edit against code the version never touches proves nothing, and it costs
the next step a real test run for nothing. If you find no such edit for a
version, say so. That is a real answer, and it is the honest one when
nothing you read supports a better one.

## What to emit

Reply with a single `<output>` block containing only JSON: an object with
one key, `versions`, a list with one answer per wrong version below, in the
same order. Each answer is an object with two keys.

- `reason` (string): why the edit you name would produce this wrong version,
  or why you found none. A person reads this later, in plain and specific
  language.
- `edit` (object or null): the edit itself, or null if you found none. When
  present, it holds exactly three string fields, and no other key.
  - `file`: repository-relative, a source file, never a test.
  - `find`: the exact text as it appears in that file today.
  - `replace`: what it becomes. `""` deletes it.

`find` must appear in `file` exactly once. If the text you want to change
appears twice, widen `find` with surrounding lines until it is unique. Make
it the whole edit: if removing `find` leaves the surrounding code broken,
widen it to cover that too. An edit that crashes the program is worth
nothing to the step that runs it.

{standing_instructions}

## The diff

{diff}

## The wrong versions

{wrong_versions}

## The claim

{spec}
