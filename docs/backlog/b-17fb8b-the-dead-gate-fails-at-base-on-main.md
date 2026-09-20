---
id: b-17fb8b
title: '`dead` fails at base on the default branch, so subtraction hides it from every cell'
status: done
closed: 2026-09-19
tier: 2
filed: 2026-09-19
specs: []
prs: [379]
commits: []
cites: [§5.4]
related: [173, b-408cf5]
---

## Problem

Found in the spec loop's run 9, 2026-09-19, by running the gate by hand, then
confirmed on both cells' `baseline:` lines.

`.saffron/gates/dead` reports `unused variable 'APPENDIX_OPENS'`
(`ontology/design_record.py:33`) at every commit since `4c0a46e`. Its only
reader is `tests/ontology/test_design_record.py:244`, and the gate does not
scan `tests/`. That is the shape `.saffron/deadcode-allow.py` exists for, the
same as `_.related` and `_.supersedes`.

Baseline subtraction spares every cell, which is correct, and also means no
cell's operator sees it. `prose` fails at base by design. `dead` does not.

## Done looks like

`dead` passes at base on the default branch, so a `baseline: dead=fail` line
means something new.

## Record

- 2026-09-19: filed from the spec loop's run 9. The operator's call was to
  file it rather than fix it mid-loop.
- 2026-09-19: done by #379. `_.APPENDIX_OPENS` joins
  `.saffron/deadcode-allow.py` with its reason, and `dead` passes at base:
  `0 unused, 0 deferred by open specs, 0 stale pending entries`.
