---
id: I
title: "rev 11: what building v0.5 found"
revisions: [11]
question: "What building v0.5 found — including a cell whose every mechanism reported success against a different container"
---

Appendix H ended by arguing the next artifact should be v0.5 rather than another
document. It was. Eleven tasks, twenty-three commits, every task reviewed against
its own brief and the whole branch reviewed at the end. What follows is what only
building it could produce.

### The headline: every control reported green and none was connected

`prepare_worktree` created the long-lived cell with no `--network` and no proxy
environment, so it joined the runtime's default network with full internet
egress. Meanwhile the driver created the isolated network, ran the host-binding
probe against it, started the proxy on it, printed `preflight: proxy at
10.88.0.3` — and passed none of it to the container holding the agent. Measured
before the fix, from a cell built exactly the way production built one:

```
$ container run --rm --cap-drop ALL saffron/cell-base:python \
    python -c "...urlopen('https://example.com')..."
REACHED 200
```

`proxy_env()` had been written, was never called, and had no test.

This is §2's claim — *a cell is untrusted, and untrusted means every control that
matters lives outside it* — satisfied in every part and false as a whole. The
proxy was correct. The probe was correct. The network was correct. Nothing joined
them, and the thing that would have caught it is the one test nobody wrote: start
a cell **the way production starts one** and probe **from inside that container**.
Every isolation test on the branch used an ephemeral sibling instead, which is a
different container answering a different question. The distinction is what is
being asserted, not what runs the assertion: a claim about *this container's*
egress must be probed from inside the production-shaped cell, while a claim
about the *network* — N1's host-binding probe, which runs before any cell
exists — is properly made by a sibling on that same network.

38. **A control and its subject are wired somewhere, and the wiring is the
    control.** Verifying each mechanism in isolation verifies nothing about the
    system, because a mechanism that reports on a thing it was never attached to
    reports on nothing at all. Test the join, from the subject's side.

The fix makes `network` and `env` **required** arguments where a cell is created,
so omission is a `TypeError` rather than a silent unisolated cell — the guarantee
moved from a call site's memory into the signature.

### The same defect, five times, in five disguises

Appendix H named principle 34: *a green result and an absent result are the same
bytes.* v0.5 produced four more instances, and the fourth is the one worth
keeping.

- **A tool-output parser silently stopped matching.** The `format` gate was
  written against ruff's `Would reformat: <path>`; installed ruff emits
  `--> path:line:col`. It matched nothing. The gate reported `error` rather than
  a false `pass` — not by luck, but because its `pass` branch is gated solely on
  the exit code and is independent of the parse. Rule 2 working on first contact
  with a real tool upgrade.
- **A section slicer over-captured.** Vocabulary injection treated only `## N.`
  headings as boundaries, so §10 — which every phase receives — ran to
  end-of-file and swallowed `CONTEXT.md`'s two trailing unnumbered sections.
  Roughly 700 characters of naming-decision history went into every prompt of
  every attempt: precisely the cost §5.3 designed per-phase injection to avoid.
  Nine tests passed because all nine ran against a synthetic fixture that happens
  to end on a numbered section.
- **A dead seam nearly returned an earned state.** The driver was written to
  return `READY_FOR_REVIEW` at the point where the agent session would be driven.
  It is a real terminal state elsewhere, so a task that ran nothing would have
  reported as assessed. The implementer refused and invented `NOT_IMPLEMENTED`
  instead — applying this document's founding principle to a state string,
  unprompted, without having been told the v0 story.
- **`which` is not a check.** The fix wave verified the cell image's toolchain
  with `which uv pytest python git`. That prints a path. `pytest --version` exited
  127, because the image built the venv at `/seed/.venv` and moved it to
  `/opt/venv`, and a console script bakes its interpreter into its shebang.

39. **Locating a tool proves a file exists; only running it proves a tool works.**
    Every check of the form "is X present" is a check that reads identically when
    X is present and broken. The image build now asserts by executing
    (`RUN ruff --version && pytest --version`), the same shape as the base image's
    bundled-binary assertion.

### Seams between correct components

Two independently-correct pieces disagreeing at their boundary was the branch's
most common defect after the wiring one, and neither instance was reachable by
any test that existed.

- **Two glob matchers.** `saffron/gates/core/scope.py` already carried a
  hand-rolled translator whose docstring states it exists *because* "fnmatch lets
  `*` cross a `/`". The plan checkpoint then reached for `fnmatch` for the same
  job on the same patterns. Nothing triggered it, because every declared pattern
  uses `**`; the first bare `*` would have produced a plan that passes validation
  and then fails the `scope` gate mechanically, reading as the agent wandering out
  of scope. `scope.py` is now the single authority, imported by both — it is the
  authority by construction, because it is what enforces the diff.
- **`spec_sha` received `policy_sha`.** Same type, wrong value, right slot. The
  `cell` path silently lacked the mid-run spec-edit invalidation that `replay`
  has. Found by review; no test could have seen it.
- **`CONTEXT.md` read from the target repo.** It is a *host* artifact — that is
  the entire reason §5.3 injects it rather than referencing it. Reading it from
  the repo under work happens to succeed when the repo is Saffron and fails for
  every other repo.

40. **A reviewer scoped to one task cannot see the seam between two.** Every
    defect *inside* a task was caught by that task's own review. Both Criticals
    lived in the wiring between tasks and were found only by the whole-branch
    pass. Scope at least one review to the joins.

### The boundary held, and that is the best news here

§2.1 claims onboarding a repository touches zero lines of the orchestrator.
Saffron was onboarded to itself and the claim was **measured, not asserted**:
`git diff --stat -- saffron/` empty, the policy parser accepting the repo's
`policy.yaml` unmodified, the whole toolchain in `.saffron/`. The one leak found
— core hardcoding a Python base image as *the* cell image — was real and is
fixed, and its inverse appeared immediately afterwards when a core probe started
requiring a Python interpreter inside every repo's image. Both are the same
mistake in opposite directions.

41. **A boundary leaks in both directions, and the second is harder to see.**
    Core learning a language is the obvious failure. Core *demanding* one of every
    repo is the same failure wearing the opposite clothes, and it looks like
    thoroughness — "probe what actually runs" is a better argument than the one it
    replaced. Core's own checks run on artifacts core owns.

### Method

Rev 7 read the document and found nine defects. Rev 8 found that rev 7's central
fix was not implementable on this machine. Rev 9 replayed real pull requests and
found the contract could not tell a tool that ran from one that didn't. Rev 10
ran a spike and measured a `--cpus` offset no document would have predicted. Rev
11 built the thing, and found that the security architecture six revisions had
argued for was, in the shipped code, applied to the wrong container.

The trend is not that documents are useless — every one of those revisions was
written against the previous document and could not have been written without it.
It is that **the defects a document can find are a different class from the
defects execution finds, and the second class is where the expensive ones live.**
Nothing left in this document is worth another read-through. The next artifact is
the agent session at §9's v0.5 seam, and after it, v1.

---

