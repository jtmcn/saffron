---
id: b-61993a
title: The `cite` subcommand reports moved text at about one hit in four, and passes a line zero or a reversed range
status: open
tier: 2
filed: 2026-09-21
specs: []
prs: []
commits: []
cites: []
related: [b-b69bb6, b-281f0a]
---

## Problem

Measured in the spec loop's run 11, 2026-09-21, on the command `SA-0114` built.

The path and past-end half is sound. Across three specs it reported no false
result.

The moved-text half matches a sentence's quoted text as a substring, so it
reports a line that holds the same word.

- On `SA-0114`'s own spec at `901916a8`, all four moved reports were false. One
  sentence names `driver.REPO`, and the line it cites holds
  `monkeypatch.setattr(driver, "REPO", tmp_path)`, which the citation describes.
- On `SA-0115` against `d5de5176`, two of eight moved reports were real. One named
  a citation that now pointed into `SA-0114`'s new code, which no past-end check
  can see.
- On `SA-0116` against `f3dcae7c`, a real one-line drift from an added import sat
  first in a list of 47 line numbers. Nobody could act on it.

Two further defects.

- `CLAUDE.md:0` and `CLAUDE.md:20-5` are counted and never reported. With other
  quoted text in the sentence, line zero slices `lines[-1:0]` and prints a wrong
  moved report that names unrelated lines.
- A citation can resolve while its sentence turns false. "The last test" still
  resolves once other tests follow it.

## Done looks like

Moved-text precision is measured and raised before `cite` feeds the spec
reviewer, for example by matching quoted text as a whole token. A start below one
and a start past the end are each reported.

## Record

- 2026-09-21: filed from the spec loop's run 11 (#404).
