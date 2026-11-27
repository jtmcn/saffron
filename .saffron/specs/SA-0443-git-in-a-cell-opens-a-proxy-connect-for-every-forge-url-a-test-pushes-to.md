---
id: SA-0443
title: "The cell image declares nothing that stops git's CONNECT to a forge, so a test without its own guard sends one to the proxy"
type: bug
priority: 3
estimated_lines: 8
estimate_measured: true
touches:
  - images/cell-base.python.Dockerfile
  - tests/test_image.py
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
  - harness/**
  - records/**
  - hooks/**
  - images/agent_runner.py
  - images/squid.conf
  - images/proxy.Dockerfile
  - images/unprivileged.sh
  - saffron/**
  - tests/conftest.py
  - tests/test_proxy.py
  - tests/test_cli.py
  - tests/test_adopt_stack_layer.py
  - tests/test_ledger_fold_task.py
  - tests/test_witness_gate.py
  - tests/test_suite.py
  - tests/test_session.py
  - tests/test_parent_versions.py
  - tests/test_regate.py
  - tests/test_report.py
  - tests/test_record_refs.py
  - tests/test_record_routed.py
  - tests/test_record_migrate.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 30
max_attempts: 3
max_turns: 120
acceptance:
  - claim: >-
      `images/cell-base.python.Dockerfile` declares `GIT_ALLOW_PROTOCOL` with
      an `ENV` instruction. git, given every `ENV` pair that file declares
      and none of the test's own `GIT_` settings, reaches no forge. Each of
      five URLs on a `.invalid` host is asked twice with `git ls-remote`:
      `https://`, `http://`, `ssh://`, the scp form `git@host:path` and
      `git://`. No ask reaches the instrument its transport would use.
      Under the same environment three local transports land: a fetch in
      the worktree seed's shape from a bare path, a push to a bare path, and
      a clone from a `file://` URL. The witness reads the declaration as a
      standalone `ENV` instruction or as a member of a continued one.
    witness: tests/test_image.py::test_the_base_image_declares_a_git_that_reaches_no_forge
    positive_case: >-
      The same five URLs, asked twice each with no declared pair applied,
      reach their instruments twice each. The http forms reach the test's
      own proxy listener, the ssh forms the `GIT_SSH` recorder, and
      `git://` the `GIT_PROXY_COMMAND` recorder. So the empty record under
      the declared environment comes from instruments that do see an ask.
    wrong_versions:
      - "The image declares `GIT_ALLOW_PROTOCOL=file:https`, so an https push still reaches the proxy as a CONNECT."
      - "The image declares `GIT_ALLOW_PROTOCOL=file:http`, so a plain http fetch still reaches the proxy."
      - "The image declares `GIT_ALLOW_PROTOCOL=file:ssh`, so an ssh URL still starts ssh."
      - "The image declares `GIT_ALLOW_PROTOCOL=file:git`, so a `git://` URL still opens a connection."
      - "The image declares `GIT_ALLOW_PROTOCOL` empty, so git refuses the local mirror too and every worktree seed fails."
      - "The image declares `GIT_ALLOW_PROTOCOL=none`, so git refuses every local path."
      - "The value is an `ARG`, so it holds at build time and no process in a cell inherits it."
      - "The value is exported inside a `RUN` step, so no later layer and no process in a cell holds it."
      - "The value is set in `images/agent_runner.py`'s environment, so the agent's Bash holds it and a gate's `exec` does not."
    covers:
      - set: the forge transports
        members:
          - member: "`https://`"
            driven_by: "The image declares `GIT_ALLOW_PROTOCOL=file:https`, so an https push still reaches the proxy as a CONNECT."
          - member: "`http://`"
            driven_by: "The image declares `GIT_ALLOW_PROTOCOL=file:http`, so a plain http fetch still reaches the proxy."
          - member: "`ssh://`"
            driven_by: "The image declares `GIT_ALLOW_PROTOCOL=file:ssh`, so an ssh URL still starts ssh."
          - member: the scp form `git@host:path`
            driven_by: tests/test_image.py::test_the_base_image_declares_a_git_that_reaches_no_forge
          - member: "`git://`"
            driven_by: "The image declares `GIT_ALLOW_PROTOCOL=file:git`, so a `git://` URL still opens a connection."
      - set: the asks of one forge URL
        members:
          - member: the first
            driven_by: tests/test_image.py::test_the_base_image_declares_a_git_that_reaches_no_forge
          - member: a second, on the same URL
            driven_by: tests/test_image.py::test_the_base_image_declares_a_git_that_reaches_no_forge
      - set: the local transports a cell uses
        members:
          - member: a fetch in the worktree seed's shape from a bare path
            driven_by: "The image declares `GIT_ALLOW_PROTOCOL` empty, so git refuses the local mirror too and every worktree seed fails."
          - member: a push to a bare path
            driven_by: "The image declares `GIT_ALLOW_PROTOCOL=none`, so git refuses every local path."
          - member: a clone from a `file://` URL
            driven_by: tests/test_image.py::test_the_base_image_declares_a_git_that_reaches_no_forge
      - set: the spellings of the declaration
        members:
          - member: a standalone `ENV` instruction
            driven_by: tests/test_image.py::test_the_base_image_declares_a_git_that_reaches_no_forge
          - member: a member of a continued `ENV` instruction
            driven_by: tests/test_image.py::test_the_base_image_declares_a_git_that_reaches_no_forge
          - member: an `ARG`, which no cell process inherits
            driven_by: "The value is an `ARG`, so it holds at build time and no process in a cell inherits it."
          - member: an export inside a `RUN` step
            driven_by: "The value is exported inside a `RUN` step, so no later layer and no process in a cell holds it."
          - member: a value outside this file
            driven_by: "The value is set in `images/agent_runner.py`'s environment, so the agent's Bash holds it and a gate's `exec` does not."
---

## Context

Backlog item **b-71f95f**, tier 2. It cites §2, and the change sits in
§5.1's cell construction. That section's bullet says the cell's git remote
is a local bare mirror and the cell cannot reach GitHub (`DESIGN.md:731`).
Every line below was read at `254f0a14`.

**What the item found.** `SA-0334`'s teardown logged proxy denials of
`CONNECT github.com:443`, and `SA-0335`'s logged two. The item concluded
that git made none of them, because the finished suite makes none.

**What made them, measured on 2026-11-27.** It was git, in each cell's own
unfinished code. Each burst falls inside one pytest command the agent sent
in IMPLEMENT. For `SA-0334` that command began 3.9 seconds before the first
denial, over `tests/test_cli.py`, `tests/test_regate.py` and
`tests/test_commit_review.py`. For `SA-0335` it began 0.5 seconds before,
over three `tests/test_cli.py` tests. Those files name `https://github.com/`
origins. `SA-0334`'s change had added a fetch from the origin, and
`SA-0335`'s a push at command exit. Neither tree yet held the conftest
fixture that `SA-0335` added 76 seconds later. Each command was replayed
on the host with a recording listener as `HTTPS_PROXY`. `SA-0334`'s sat on
its batch's base `7a8e5cc0`, and `SA-0335`'s on `SA-0334`'s pushed head
`a632a846`. Each had its own patch's `saffron/` files applied.
`SA-0334`'s command sent 7 CONNECTs to `github.com:443` and `SA-0335`'s
sent 2. Those counts match each teardown log. `lsof` named the caller each time as `git-remote-https`, with the
`User-Agent` `git/2.54.0`.

**What stops it today.** `tests/conftest.py:116-126` sets
`GIT_ALLOW_PROTOCOL=file` for every test not marked `cell`. That is one
repo's test fixture. A target repo without one, or a test that builds its
own environment, still sends a forge URL's CONNECT to the proxy. The proxy
denies it, since its allowlist names one host (`images/squid.conf:8-14`).
Across the 91 task directories after `SA-0335`, no teardown logged a
`github.com` denial.

**The image.** `images/cell-base.python.Dockerfile` declares one continued
`ENV` instruction (`:27-29`) and no `GIT_` variable. A repo's image builds
`FROM` it, as `.saffron/Dockerfile:3` does. The host's `exec` passes no
environment of its own (`saffron/cell/runtime.py:526-546`). The agent's
Bash goes through a wrapper that drops only the OAuth token
(`images/unprivileged.sh:13-16`).

**The seed.** `_seed_script` fetches the mirror into the worktree from the
bind-mounted path `/mirror` (`saffron/cell/worktree.py:60-87`).
`_run_seed` starts it in an ephemeral container of the same image
(`saffron/cell/worktree.py:90-101`).

## Problem

Make git inside every cell refuse a forge transport before it opens a
connection, and leave every local path working.

1. **Declare it.** Add `GIT_ALLOW_PROTOCOL=file` to
   `images/cell-base.python.Dockerfile` with an `ENV` instruction. A
   standalone line or a member of the existing block both serve. Give it a
   one-line comment naming the item.
2. **Run it in the build.** After the declaration, add a `RUN` step. It
   asks git for an `https://` URL on a `.invalid` host. It fails the
   build unless git's output names the https transport as not allowed. Do
   not let `set -e` end the step on git's own nonzero exit. A step that
   fails here fails every cell's image build, so read the notes on the
   measured text first.
3. **Witness it** in `tests/test_image.py`, as the notes describe.

## Out of scope

- **Naming the caller in a teardown line.** The item's first "done" clause
  asks for it, and this spec leaves it undone. The proxy sees the cell's
  address and port and no process. The one caller it can see is the
  `User-Agent`, which the cell chooses. `denied_egress` also caps what
  teardown reads at 10 lines (`saffron/cell/proxy.py:88`).
- The `pypi.org` denials in `SA-0116`, `SA-0257` and `SA-0378`. They have
  another caller.
- A test or tool that hands git an environment of its own without this
  value. git then sends the CONNECT, and the proxy still denies it.
- `tests/conftest.py`'s fixture stays. It covers a host session of the
  suite, where no image applies.
- **A repo's image build.** A `.saffron/Dockerfile` step that fetches a
  git-sourced dependency over https now fails at build. `uv.lock` holds
  none at your base. Such a repo sets its own value on that step.

## Notes for the agent

**Edit or new.** The declaration, the build step and the witness are all
new text. No `find` written now pins them, so no mutant is on the ref and
`witness` reports `skip`.

**git's text, measured.** On git 2.47.3 in `saffron/cell-base:python` and on
the host's git 2.54.0, with `GIT_ALLOW_PROTOCOL=file`, each forge form
printed `fatal: transport '<name>' not allowed` and opened nothing. The
name was `https`, `http`, `ssh` (for both ssh forms) or `git`. A push to
a path, a fetch from a path and a clone from `file://` all landed. An empty
value and `none` both refused every local transport with
`fatal: transport 'file' not allowed`. A prototype base image built with
the step above passed it, and failed it with `file:https` declared. Its
value reached a process started by `container exec` and one started
through the wrapper. That probe is the only evidence that the value
reaches a live cell. No test in the default suite sees it there.

The step built was this one, and it is a shape, not a required spelling.

```
RUN set -eu; \
    out=$(git ls-remote https://forge.invalid/r.git 2>&1 || true); \
    case $out in *"transport 'https' not allowed"*) ;; \
      *) echo "git did not refuse https: $out" >&2; exit 1 ;; esac
```

Your task's image is built from the operator's checkout, never from your
edit (§5.1), so no gate builds your step. Keep it to what git prints.

**Witness shape.**

- Read the declared pairs from the Dockerfile's text. Join continued lines
  first, and split only instructions that begin `ENV`. Other lines hold
  apostrophes a shell splitter refuses. Before the real file, assert the
  reader on two small strings of your own: one standalone instruction and
  one continued instruction with a quoted value.
- Build git's environment from `os.environ` with every `GIT_` name and
  every `*_proxy` name dropped, in either case. The conftest's own value is
  `GIT_ALLOW_PROTOCOL=file`. A witness that inherits it passes with no
  declaration at all.
- Then isolate git's configuration: `HOME` set to `tmp_path`,
  `GIT_CONFIG_GLOBAL` set to `/dev/null`, `GIT_CONFIG_NOSYSTEM` set, and
  `GIT_TERMINAL_PROMPT=0`. A host's `url.<base>.insteadOf` would otherwise
  rewrite a URL.
- The instruments: a listener on `127.0.0.1` that records each request
  line and answers 403, named as `HTTPS_PROXY` and `HTTP_PROXY` in both
  cases. Add a recorder script named by `GIT_SSH`, with
  `GIT_SSH_VARIANT=simple`. Without it git starts ssh once more to probe
  its variant, so one ask records twice. The same recorder serves as
  `GIT_PROXY_COMMAND` for `git://`. Use a `.invalid` host throughout. This
  witness runs inside a cell, and a real forge host would put the denial
  this spec removes into its own teardown log.
- Run each git command with `cwd` under `tmp_path`. A worktree whose
  `.git` points elsewhere made `ls-remote` fail before any transport in a
  prototype, and the positive case read nothing.
- Apply every declared pair on top, not only `GIT_ALLOW_PROTOCOL`. That is
  the environment a process in a cell inherits.
- The prototype witness passed in the host's suite, and inside
  `saffron/cell:saffron` as root and through the wrapper.

**No `retired_first`.** Nothing here adds or widens a refusal a spec can
meet. The conftest already sets the same value for every unmarked test, so
no queued witness meets a new environment.
`tests/test_record_refs.py:424` sets its own value and keeps it.
