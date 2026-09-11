---
id: SA-0073
title: the retired-vocabulary hook reads line by line, so a retired term split by a line wrap passes
type: bug
priority: 3
depends_on: []
touches:
  - .pre-commit-config.yaml
  - hooks/retired_vocabulary.py
  - tests/test_retired_vocabulary_hook.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/**
  - pyproject.toml
  - uv.lock
budget_usd: 5
max_attempts: 3
max_turns: 40
risk: standard
acceptance:
  - claim: >-
      A retired term split across a line break is reported, in either of the
      two separator forms the pattern already accepts on one line: a plain wrap
      between the two words, and a hyphen that ends one line. `pygrep` searches
      line by line and every prose file here is hard-wrapped. The same words
      caught on one line pass when a wrap separates them.
    witness: tests/test_retired_vocabulary_hook.py::test_a_retired_term_split_by_a_line_break_is_caught
  - claim: >-
      A wrap cannot manufacture a hit either. A near miss that the pattern's
      word boundary rejects on one line is still rejected when a break falls
      inside it, and two words on either side of a blank line are not joined
      into one. Reading across lines must widen what is seen, not what counts.
    witness: tests/test_retired_vocabulary_hook.py::test_a_near_miss_stays_a_near_miss_across_a_break
  - claim: >-
      A hit names the file and the line it starts on. The author is looking for
      a term the file's own line structure hid, and a file name alone sends
      them to grep for words that grep will not find on one line.
    witness: tests/test_retired_vocabulary_hook.py::test_a_hit_names_the_file_and_the_line_it_starts_on
  - claim: >-
      The configured hook runs the new check over the same files it covers
      today: `types: [text]`, and the four excluded paths, which state the
      vocabulary rules and so must quote the words they forbid. The witness
      pins those four paths and that type as its expected value, and reads the
      hook's `entry` without executing it.
    witness: tests/test_retired_vocabulary_hook.py::test_the_configured_hook_runs_the_check_over_the_same_files
  - claim: >-
      The tree carries no retired term under the file-wide reading. A cell runs
      no prek hooks, so a test in the suite is the only way the rule reaches the
      `tests` gate an agent is judged by. The one straddled instance this repo
      held when the spec was queued was reworded by hand.
    witness: tests/test_retired_vocabulary_hook.py::test_the_tree_carries_no_retired_term_across_a_line_break
---

## Context

`docs/BACKLOG.md` item **57**. `.pre-commit-config.yaml`'s `retired-vocabulary`
hook is `language: pygrep`, and pygrep matches within a line. It has already
missed one. Item 25 carried a retired phrase for a week, split by a wrap, and it
was found only because a later edit put the same words on one line.

That is Appendix I's shape in the vocabulary layer: a control that reads as
present, reports green, and is not applying. The rate is estimated, not
measured: at about twelve words per line in the files the hook covers, roughly
one occurrence in twelve of any two-word term falls across a break. That is low
enough that the hook looks like it works.

**Measured when this spec was queued, and again in review**, over every tracked
text file the hook covers with its exclusions applied: one file held a hit that
only a cross-line reading sees, in `docs/BACKLOG.md`. It was the verb, not the
retired noun, but the pattern cannot tell those apart, and on one line the hook
would already have refused it. It was reworded in the commit that queued this
spec. Review re-measured zero hits with whitespace normalised, with line-final
hyphens joined, and with comment leaders stripped.

## Problem

The check has to read the file rather than the line. `pygrep` cannot do that,
and a `multiline` flag on the existing pattern is the wrong fix: its separator
class and word boundary would each have to grow a newline case, and the next
term added would need the same care. That is the part that rots.

## Out of scope

**New retired terms.** Put the pattern somewhere a second one can be added, and
add none. Which words are retired is `CONTEXT.md`'s decision.

**Comment leaders.** A term wrapped across two lines of a code comment has a
`#` between its halves after the break is normalised. Seeing through comment
and quote markers is a real extension, and one this spec does not need to make.
File it in your notes if you think it matters.

**The other hooks.** Leave ruff, ty and ast-grep exactly as configured.

## Notes for the agent

**This spec creates new code, so its criteria carry witnesses and no mutants.**
The script does not exist yet, so there is no spelling to pin.

**The normaliser owns line breaks, not the pattern.** Delete the whitespace
after a hyphen that ends a line, so the hyphenated form joins. Turn any other
run of whitespace containing exactly one line break into a single space. Leave a
blank line, two or more breaks, alone. Plain whitespace normalisation turns a
hyphen at the end of a line into a hyphen and a space, which the pattern's
separator class does not match. That would pass a test covering only the plain
wrap.

**Every witness exercises `hooks/retired_vocabulary.py` itself.** Run it as a
subprocess with `sys.executable`, or import it inside the test, never at module
scope. The `revert` gate re-runs each new witness with the script removed, and
a module-scope import turns that run into a collection error, which `revert`
reads as `skip`: the anti-theater check then checks nothing. The fifth
criterion's test calls the script's own check. It never contains a copy of it.

**Enumerate the tree with `git ls-files`, not a filesystem walk.** On the
operator's host, `.claude/worktrees/` is gitignored and holds full checkouts of
other branches, so a walk from the repo root reads text this branch does not
contain. In a cell, `/work` is a git checkout, so `git ls-files` works there too.
Apply `exclude` as read from `.pre-commit-config.yaml` (PyYAML is already a
dependency), and approximate `types: [text]` by skipping files that contain a
NUL byte or are not valid UTF-8. prek's `identify` library is not installed, and
`pyproject.toml` is forbidden, so do not add it.

**The fourth and fifth criteria read the config differently, on purpose.** The
fourth pins the four paths and `types: [text]` as literal expected values, so a
change to them fails a test. The fifth reads them from the config, so it cannot
drift from what the hook actually does.

**Describe a token, never quote one.** The hook runs over its own script and
over its own tests, and so does the fifth criterion's walk. A test file spelling
the retired term in a string literal is a hit. Build test inputs from parts at
runtime, the way `.saffron/policy.yaml`'s suppression list is written about
rather than quoted.

**Match the local hooks' shape, and stay after `ast-grep`.** The other local
hooks run through `uv run` with `language: system`. The script receives
filenames from prek and exits non-zero on a hit. `tests/test_saffron_gates.py`
reads `.pre-commit-config.yaml` from `id: ast-grep` to the end of the file and
counts ast-grep's flags there, so do not name `--no-ignore`, `--globs` or the
sgconfig path in this hook's comment. Any `§` or Appendix you cite in the new
files must resolve: `tests/test_citations.py` checks every one.

**The fifth criterion depends on the whole tree staying clean.** If a straddled
term lands on `main` before this runs, it is unsatisfiable, because `docs/**` is
forbidden. Re-measure before queueing if the base moves.
