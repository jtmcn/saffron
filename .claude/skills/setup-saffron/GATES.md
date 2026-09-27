# Writing a gate and the Dockerfile

§5.4 is authoritative, and `saffron/gates/contract.py` is the schema. This file is the part a gate author trips on.
Saffron's own `.saffron/gates/format` is a worked shell example, and `.saffron/gates/tests.py` a worked test runner.

## The contract

A gate is an executable that prints one JSON object on stdout and nothing else there:

```json
{ "gate": "lint", "status": "fail", "tool": "eslint 9.3.0",
  "failures": [ { "file": "src/a.ts", "line": 4, "code": "no-unused-vars", "message": "..." } ],
  "summary": "1 problem" }
```

- `gate` equals the file name and the name `policy.yaml` declares.
- `tool` comes from running the tool, as `ruff --version` does. A literal string reads the same whether the tool ran or was absent (Appendix H).
- The gate reads its tool's exit code. Nonzero with no parsed failures is `error`, because the output shape changed and a parser that matched nothing reads as a pass.
- `error` means the gate broke and `fail` means the code is wrong. A missing tool, a crash or a timeout is `error`.
- A run that broke part-way is `error` for the whole run, never `fail` on what it collected.
- `skip` names no tool, carries no failures and exits `0`.
- `code` is stable across runs. The baseline matches on `(gate, file, code, message)` with digits collapsed, so a line number inside `code` breaks it.
- Diagnostics go to stderr. A stray line on stdout makes the result unparseable, which is `error`.

## The `tests` gate

- It takes test names as arguments and runs only those. `revert` and `witness` call it this way.
- It fills `collected` with every name it enumerated, in the form the runner accepts back as an argument. Without it `census` and `criteria` skip.
- A failed test's `code` is its collected name, so `criteria` can tell which witness failed.
- A handed name the runner cannot find goes in `uncollected`. A subset run that accounts for every name is `pass` or `fail`, never `error` (SA-0127). Only `revert` reads the field.

## Where a gate executes

- In a cell, gates run from a read-only copy at `/gates` with the worktree at `/work` as the working directory. Reach a helper beside the gate through `$(dirname "$0")`.
- The gate inherits no Saffron virtualenv. It calls the repo's own toolchain from the image.
- A gate that writes a build artifact leaves it in the tree, and `committed` fails on it. Cover the artifact in `.gitignore`.
- A Python helper beside a gate takes a name no stdlib module uses. A `types.py` shadows `types` for every import after it.

## The Dockerfile

- `FROM saffron/cell-base:python`. The base carries the agent runtime and git, and nothing of the repo's.
- Bake every dependency at build time. A cell reaches one host, so a gate that downloads at run time errors.
- Bake a service the suite needs, such as a database, with its migrations and seed data.
- End with one `RUN` that runs every gate's tool, as `ruff --version && pytest --version`. A path that exists but cannot execute passes `which` and fails the gate.
- Add no credential. The cell's only credential is the agent's own token.
- Build a virtualenv where it will run. A moved one keeps its old path in each script's shebang and exits `127`.
