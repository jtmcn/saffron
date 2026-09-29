# Run 20's Standards defects, as lens-scoring fixtures

Each directory under `run-20/` freezes one pull request of run 20. It declares the one
defect the Standards seat found there and no REVIEW lens filed. ADR 8's measured pass
scores the `conventions` lens against them, before and after a prompt change.

They live outside `docs/evidence/fixtures/` on purpose. The corpus loader reads every
directory there, and the baseline pass's tests pin that set to eight fixtures.

`docs/evidence/scripts/2026-09-08-recover-fixture.py` wrote every frozen file, with
`--out docs/evidence/fixtures-standards/run-20`. Each `fixture.toml` then gained its
defect by hand, from the measurement plan in `SA-0191`'s notes.

## The refs these fixtures need

Two heads are reachable from no branch. `SA-0184` and `SA-0186` were restacked
before they merged. The copies on `main` carry other trees, and `SA-0186`'s copy
reproduces no recorded diff. So each fixture pins the ledger's `pushed_sha`, and
two refs keep those commits alive.

    refs/fixtures/SA-0184-head  69083659ac10552659399d61e74ce603ac6f9b06
    refs/fixtures/SA-0186-head  3c2bdd4171db1c1d648b02eac5f8ae85feffd3f8

The scoring driver builds its cell from a mirror of every ref. A head that no ref
names never reaches the cell. The other eight `refs/fixtures/*` entries for these
five specs name commits on `main`, and follow the convention of two refs per fixture.

## Scoring a fixture

The driver takes any fixture directory. It reads the lens prompts from the checkout
it runs in, so run it once from `main` and once from the changed branch.

    uv run python docs/evidence/scripts/2026-09-07-lens-scoring.py \
        --fixture docs/evidence/fixtures-standards/run-20/SA-0160 --runs 3

The driver passes `claude_md=None`, so every lens reads an empty standing-instructions
section. Production passes the base `CLAUDE.md`, frozen here as `claude.md`. A pass
that wants production's prompt must change that argument first.

Every `min_severity` is `concern`. The seat's own grade was never recorded.
