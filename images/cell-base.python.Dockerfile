# saffron/cell-base:python — agent runtime and git. Nothing else: the host execs
# the repo's own gate executables, so there is no shim here to carry.
# A toolchain here means §2.1's boundary has moved into Saffron. It belongs in
# the target repo's .saffron/Dockerfile.
#
# Debian, not Alpine: claude-agent-sdk ships manylinux wheels with a bundled
# Claude Code binary, and a musl image silently falls back to the sdist with no
# binary at all. glibc is the requirement; the distribution is not.
#
# `BASE_IMAGE` is an argument because a host whose egress refuses every registry
# cannot pull the default and can still build every layer below it —
# `images/bootstrap-base.sh` produces one from an apt mirror alone. The default
# is what this project is measured against, so nothing changes for a host that
# can pull; what a host built *from* is recorded below rather than assumed
# (DESIGN.md §5.1.2).
ARG BASE_IMAGE=python:3.12-slim-bookworm
FROM ${BASE_IMAGE}

# python3 and pip explicitly: the default base has them and a bootstrapped one
# does not, and a base that silently lacks an interpreter fails at the SDK
# install with an error nobody would trace back to here. `python` is the name
# everything below uses, so a base providing only `python3` gets the link.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      git ca-certificates python3 python3-pip python3-venv \
 && rm -rf /var/lib/apt/lists/* \
 && { command -v python >/dev/null || ln -s "$(command -v python3)" /usr/local/bin/python; } \
 && update-ca-certificates

# pip verifies against certifi's bundle, not the system store, so a host behind
# a TLS-terminating proxy fails here with a self-signed-certificate error even
# though `ca-certificates` is installed and apt is happy. Pointing it at the
# system store is what makes the `update-ca-certificates` above reach pip, and
# it is a no-op on a host with nothing extra to trust — such a host's bundle is
# the standard set. Mount the CA into /usr/local/share/ca-certificates at build
# time; do not disable verification.
# `SSL_CERT_FILE` is the one most tools honour and `uv` is among them — measured,
# it reads neither of the other two and fails `uv sync` with `UnknownIssuer`
# while pip a layer above is content.
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# Pinned: unpinned, the agent runtime drifts between rebuilds and the version
# that ran a task is recorded nowhere. Bump deliberately.
ARG SDK_VERSION=0.2.142
# --break-system-packages unconditionally: a distribution base marks itself
# externally managed (PEP 668) and the default slim image does not, and this
# image *is* the environment — there is no system here to protect from it. Not
# guarded by a fallback: measured, an `||` here reported the second command's
# PEP 668 complaint for a first command that had failed on TLS, which sent the
# reader to the wrong problem entirely.
RUN python -m pip install --no-cache-dir --break-system-packages \
      "claude-agent-sdk==${SDK_VERSION}"

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
      || { echo "the bundled Claude Code binary reported no version" >&2; exit 1; }; \
    mkdir -p /opt/saffron; \
    ln -sf "$bin" /opt/saffron/claude-code

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

# What this image actually is, written by running each tool rather than by
# restating the arguments it was built with. Two hosts that built by different
# routes are then comparable rather than assumed equal, which is the whole cost
# of `BASE_IMAGE` being an argument (DESIGN.md §5.1.2). Every line is a version
# some tool printed about itself; a build that could not produce one fails here
# instead of shipping a blank.
RUN set -eu; \
    { echo "base=$(. /etc/os-release && echo "$ID $VERSION_ID")"; \
      echo "python=$(python --version 2>&1)"; \
      echo "git=$(git --version)"; \
      echo "claude-agent-sdk=$(python -c 'import claude_agent_sdk as s; print(s.__version__)' 2>/dev/null || echo unknown)"; \
      echo "claude-code=$(/opt/saffron/claude-code --version 2>&1 | head -1)"; \
    } > /opt/saffron/provenance; \
    grep -q '^python=Python 3\.12\.' /opt/saffron/provenance \
      || { echo "base image is not Python 3.12:" >&2; cat /opt/saffron/provenance >&2; exit 1; }
