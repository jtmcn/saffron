# saffron/cell-base:python — agent runtime and git. Nothing else: the host execs
# the repo's own gate executables, so there is no shim here to carry.
# A toolchain here means §2.1's boundary has moved into Saffron. It belongs in
# the target repo's .saffron/Dockerfile.
#
# Debian, not Alpine: claude-agent-sdk ships manylinux wheels with a bundled
# Claude Code binary, and a musl image silently falls back to the sdist with no
# binary at all.
FROM python:3.12-slim-bookworm

RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Pinned: unpinned, the agent runtime drifts between rebuilds and the version
# that ran a task is recorded nowhere. Bump deliberately.
ARG SDK_VERSION=0.2.142
RUN pip install --no-cache-dir "claude-agent-sdk==${SDK_VERSION}"

# The bundled binary is the whole reason this image is Debian. If a source
# distribution was installed instead, the agent has no runtime and every cell
# fails at turn one with an error nobody would trace back to the image.
# Located *and run*, and the version string is the assertion: an empty or
# non-ELF file fails `execve` with ENOEXEC and the shell then runs it as a
# script, so a zero-byte stub exits 0 with no output. Measured (principle 39).
RUN set -eu; \
    bin="$(python -c "import claude_agent_sdk, pathlib, sys; \
p = pathlib.Path(claude_agent_sdk.__file__).parent; \
found = list(p.rglob('claude-code*')) + list(p.rglob('claude')); \
print(found[0] if found else sys.exit('no bundled Claude Code binary in the wheel'))")"; \
    "$bin" --version | grep -q . \
      || { echo "the bundled Claude Code binary reported no version" >&2; exit 1; }

# The host drives the agent from outside; this is what it execs inside. It is
# agent-runtime code, so it belongs to the base image and not to any repo's.
COPY images/agent_runner.py /opt/saffron/agent_runner.py

# And so is the interpreter that can import the SDK. A repo's image puts its own
# venv first on PATH — Saffron's own does — and `python` there cannot import
# claude_agent_sdk. Measured, after the host stopped declaring the SDK and the
# repo venv stopped carrying it by accident.
RUN ln -s "$(command -v python)" /opt/saffron/python

# Run it, do not merely copy it — a file that is present and unrunnable reads
# identically to a working one (principle 39). Invalid JSON exercises the whole
# path down to the error event without the SDK, a key, or a network.
RUN echo 'not json' | /opt/saffron/python /opt/saffron/agent_runner.py \
      | grep -q '"type": "error"' \
      || { echo "agent_runner.py did not emit a Saffron event" >&2; exit 1; }

WORKDIR /work
