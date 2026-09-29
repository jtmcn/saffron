---
id: SA-0194
title: A finding outside every hunk anchors through a shared common word, so a line naming no changed identifier counts
type: bug
priority: 2
depends_on: []
estimated_lines: 110
touches:
  - saffron/agents/findings.py
  - tests/test_findings.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - records/**
  - harness/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/qualify.py
  - saffron/ledger.py
  - tests/test_session.py
  - tests/test_review.py
  - tests/test_qualify.py
  - tests/test_rebut.py
budget_usd: 14
max_attempts: 3
max_turns: 60
acceptance:
  - claim: >-
      A finding on a line outside every hunk does not anchor when each word
      the line shares with the diff is one of the 54 common English words
      this spec lists. That holds for each of the 54, spelled in lower case and
      capitalised, whether the diff carries it on an added line, on a removed
      line or in a renamed path.
    witness: tests/test_findings.py::test_a_line_sharing_only_common_words_with_the_diff_does_not_anchor
    wrong_versions:
      - A comparison that does not fold case, so a capitalised word from the list still anchors.
      - A list missing one of the 54 words.
      - A filter applied to the tokens of added lines alone, so a shared word from a removed line still anchors.
      - A filter applied inside the hunk walk, so a word from a renamed path still anchors.
      - A filter applied only to findings on a Python file.
      - Every token under five characters dropped in place of a list.
  - claim: >-
      `SA-0192`'s probe line anchors through `changed`, `code` and `lenses`,
      and through each of them alone. With those three taken out it does not
      anchor, and neither does a line sharing `is`, `other`, `the` or `what`
      alone. A Markdown line is read like any other: a shared word off the
      list anchors it.
    witness: tests/test_findings.py::test_sa_0192s_probe_line_anchors_through_its_content_words_alone
    wrong_versions:
      - Identifier-shaped tokens only, meaning a token with an underscore, a digit beside a letter, or a lower-case letter before a capital.
      - A line anchored only when it shares two or more words off the list.
      - A list that also holds the word code.
      - A list missing the word other.
  - claim: >-
      An adequacy finding on an untouched line of a Python test file anchors
      when the line calls a function the diff changed, even when that
      function's name is one plain lower-case word. A finding on the next
      line of the same file, sharing only words on the list, does not.
    witness: tests/test_findings.py::test_an_adequacy_finding_on_an_untouched_test_line_anchors_through_a_one_word_identifier
    mutant:
      file: saffron/agents/findings.py
      find: "content = read_head(finding.file)"
      replace: "content = None"
    wrong_versions:
      - Identifier-shaped tokens only, meaning a token with an underscore, a digit beside a letter, or a lower-case letter before a capital.
      - A filter applied only to findings on a Markdown file.
      - A line anchored only when it shares two or more words off the list.
  - claim: >-
      A finding on an untouched line calling a function the diff renamed still
      anchors.
    witness: tests/test_findings.py::test_blast_radius_finding_on_an_untouched_line_anchors
    preserves: true
---

## Context

Backlog item **b-38d45f**, found in the spec loop's run 21 on #581
(`SA-0192`). It cites `DESIGN.md` §5.5. Every line number below was read at
`60510037`.

**The second target.** `_is_anchored` anchors a finding whose line sits in
a hunk (`saffron/agents/findings.py:149-153`). Otherwise it reads the
cited file at head (`saffron/agents/findings.py:158`). It anchors the
finding when the cited line shares any token with the diff
(`saffron/agents/findings.py:166`). A token is a match of
`_WORD = re.compile(r"\w+")` (`saffron/agents/findings.py:26`).
`DiffFacts.tokens` holds every token of the diff
(`saffron/agents/findings.py:63-67`). Each added and removed line feeds it
(`saffron/agents/findings.py:124`), and so does each renamed path
(`saffron/agents/findings.py:86-89`). Nothing filters them, so `the` and
`is` anchor a line as well as a function name does.

**What the glossary says.** `CONTEXT.md:532-536` defines **Anchored** as a
finding that falls inside a hunk "or cites a line naming an identifier the
diff changed". It adds that the second target is load-bearing for test
adequacy, "whose finding is often about a test that already existed". The
comment at `saffron/agents/findings.py:154-157` says the same.

**The case that found it.** `SA-0192`'s host probe filed an adequacy
blocker on `saffron/agents/prompts/review-correctness.md:30` at `07e0ad21`.
That line is
`other lenses redundant. Yours is what the changed code *computes*:`.
The diff was `44dd8e17..07e0ad21`, whose only hunk in that file starts at
new line 55. Run over that diff and line on 2026-09-29, the shared tokens
were these.

```
today: ['changed', 'code', 'is', 'lenses', 'other', 'the', 'what']
identifier-shaped only: []
common words dropped: ['changed', 'code', 'lenses']
```

**Who reads the result.** `anchor` has three callers:
`saffron/phases/review.py:363` for REVIEW's lenses,
`saffron/cell/session.py:1704` for a surviving criterion probe, and
`saffron/qualify.py:131` for the end review. None reads `DiffFacts` itself.

## Problem

A finding outside every hunk anchors when its line shares one common English
word with any changed line. Such a line names no identifier the diff changed,
so the finding reaches REBUT and the queue as if it pointed at this change.

Drop common words from the comparison, and keep everything else as it is.

1. **The list.** Add a module-scope `frozenset` of these 54 words to
   `saffron/agents/findings.py`.

   ```
   a an and are as at be been being but by else for from here how if in into
   is it its no nor not of on or other so than that the then there these this
   those to was we were what when where which who whom whose why with you your
   yours
   ```

2. **The comparison.** Keep the intersection that
   `saffron/agents/findings.py:166` computes today. Return true when any token in it, folded with
   `str.casefold`, is not in the list. Change nothing before that line.
3. **Leave `parse_diff` alone.** `DiffFacts.tokens` still holds every token,
   and its docstring stays true. A filter at the comparison reaches every
   source of a token at once: added lines, removed lines and renamed paths.

**Why a list, and not identifier-shaped tokens.** The item offered both. On
2026-09-29 both were run over every finding the host ledger records with a
`pushed_sha`. That was 188 findings, of which 28 sit outside every hunk. The
identifier-shaped arm counts a token with an underscore, a digit beside a
letter, or a lower-case letter before a capital. It unanchored 14 of the 28.
Thirteen were contract findings on stale docstrings, comments or documents,
anchored through words such as `scope`, `verdicts` and `worktree`. The
fourteenth was `SA-0192`'s real blocker. This list unanchored none of the 28.
A one-word function name like `fold` is an identifier, and only the list
keeps a line calling it anchored.

**What a prose file means here.** Markdown has no identifiers to shape-test.
A shared word off the list counts in a prompt or a document as it does in
code. So `SA-0192`'s line still anchors, through `changed`, `code` and
`lenses`. The finding was real, and the item records the anchor did no harm.

## Out of scope

- **`DESIGN.md` §5.5 and `CONTEXT.md`.** §5.5 describes the second test as
  tokenise, intersect, "no language knowledge anywhere". The operator edits
  that sentence by hand in this spec's pull request to name the list.
  `CONTEXT.md`'s **Anchored** entry already says "naming an identifier", and
  needs no edit.
- **Unanchored probe survivors.** A surviving criterion probe goes through
  `anchor` too (`saffron/cell/session.py:1704`), so one on a line sharing
  only listed words now drops. Item b-e40d09 owns the question of such a
  survivor reaching REBUT.
- **REBUT.** `saffron/phases/rebut.py` is item b-cd5fd2's, specced beside
  this one.
- **Stemming, plurals and identifiers inside backticks.** None is measured
  to matter.

## Notes for the agent

**New or edit.** The change rewrites the last line of `_is_anchored` and
adds a constant. Criteria 1 and 2 pin behaviour whose code does not exist
yet. So each declares a witness and no mutant, and `witness` reports `skip`
for them.
Criterion 3 declares a mutant on text the existing function already holds.
Keep the head read and the hunk check in `_is_anchored` as they stand.
Criterion 4 is `preserves`, and names a test that passes now.

**Write each witness's own copy of the list.** Criterion 1's witness spells
the 54 words as a literal in the test module. It asserts there are 54. It
never imports the module's constant. A loop over that constant passes
whatever the constant holds. Use the names `tests/test_findings.py:6`
already imports, and import nothing new at module scope.

**Build diffs as text.** `anchor` takes the diff as a string and `read_head`
as any callable (`saffron/agents/findings.py:128-146`). A dict's `get` is
enough. One helper that renders a unified diff for one path from a list of
removed and a list of added lines serves every witness. A pure rename is
the four header lines `diff --git`, `similarity index 100%`, `rename from`
and `rename to`, with no hunk.

**Criterion 1's witness.** Each of the 54 words has two spellings: as
listed, and with its first letter upper-cased. For each spelling, build
three diffs. The first adds the line `<spelling> zebra` against a removed
`yak`. The second removes `<spelling> zebra` and adds `yak`. The third
renames `<spelling>.md` to `yak.md`. Cite line 1 of a file `cited.md` whose
content is `<spelling> owl`. Each of the 324 findings reads
`anchored` false. At base every one reads true.

**Criterion 2's witness.** The diff adds three lines to
`tests/test_review.py`, taken from `44dd8e17..07e0ad21`.

```
    "What else in the repository calls the changed code, and what breaks "
    reaches the conventions prompt as before, and the other three lenses
  every other promise to something outside the change. That is the contract
```

Cite line 30 of `saffron/agents/prompts/review-correctness.md`, whose
content is 29 empty lines and then the cited line. Nine cited lines, each
with its expected `anchored` value, compared with `is`.

```
other lenses redundant. Yours is what the changed code *computes*:   True
other redundant. Yours is what the *computes*:                       False
changed redundant.                                                   True
code redundant.                                                      True
lenses redundant.                                                    True
other redundant.                                                     False
is redundant.                                                        False
what redundant.                                                      False
the redundant.                                                       False
```

At base the four `False` rows read `True`.

**Criterion 3's witness.** The diff edits `src/fold.py`. It removes
`def fold(rows):` and adds two lines.

```
def fold(rows, strict):
    """Return the rows, and fail if it is empty."""
```

The cited file is `tests/test_fold.py`, with these three lines.

```
def test_fold_keeps_order():
    assert fold([]) == []
    # it is the same list, and that is all
```

Two adequacy findings, on lines 2 and 3, read `[True, False]` in that
order. At base they read `[True, True]`.

**Measured on a prototype, 2026-09-29.** The change and these three
witnesses were written against `60510037`. Each witness failed with the
source reverted to the base. Each wrong version under the three criteria
was applied to the prototype, and at least one of the three witnesses failed
it. Each criterion's own witness failed every wrong version listed under
it. Criterion 3's declared mutant failed its witness. The rest of the suite
passed on the prototype, and no existing test needed an edit.

**The `prose` gate** reads every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words.

**Size.** No touched path is in `elevate_on`, so `size` is advisory. The
prototype counted 441 changed tokens by `size_gate`, against the `bug`
ceiling of 1300. `estimated_lines` is those 441 tokens over four, with no
overrun added. About a quarter is `saffron/`, the rest tests.
