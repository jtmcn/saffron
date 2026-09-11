# The fixtures' commits are kept alive by `refs/fixtures/*`. Do not delete them.

Each fixture freezes one merged pull request's diff, spec body, gate summary and
context, and declares the defects a critic lens should raise against it. The
frozen files in each directory are the inputs a scoring pass actually reads.

What makes them trustworthy is a test: every fixture's `diff.patch`,
`spec_body.md`, `context.md` and `claude.md` must reproduce from git at the
`base_sha` and `head_sha` its own `fixture.toml` declares. A fixture that
cannot reproduce its range fails loudly rather than grading a lens against a
tree nobody reviewed.

**That test needs commits which are not reachable from `main`.** Five of the
eight pull requests were squash-merged, so their branch commits are referenced by
nothing: not by `main`, and not by the `refs/pull/N/head` refs GitHub retains —
those point at a later push than the one the batch tree recorded. The objects
survived only in one working clone until they were pushed here.

So sixteen refs exist, two per fixture:

    refs/fixtures/<SPEC>-base
    refs/fixtures/<SPEC>-head

They are the only thing keeping those commits from being garbage collected.
Deleting one does not break a test that day — the frozen files are committed and
a pass still runs — it breaks the *audit*, silently, on the next machine that
tries to verify the range. `.github/workflows/ci.yml` fetches them; measured, a
shallow checkout plus that fetch is enough, and no clone depth substitutes for it.

Adding a fixture means pushing its two refs at the same time. The recovery script
(`docs/evidence/scripts/2026-09-08-recover-fixture.py`) rebuilds a directory from
the ledger and the batch tree; it does not push refs, and nothing yet checks that
a fixture's refs exist. That gap is worth closing the first time someone adds a
ninth fixture and CI goes red for a reason the error message does not name.
