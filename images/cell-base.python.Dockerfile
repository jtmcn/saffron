# saffron/cell-base:python — agent runtime and git. Nothing else: the host execs
# the repo's own gate executables, so there is no shim here to carry.
# A toolchain here means §2.1's boundary has moved into Saffron. It belongs in
# the target repo's .saffron/Dockerfile.
#
# Debian, not Alpine: claude-agent-sdk ships manylinux wheels with a bundled
# Claude Code binary, and a musl image silently falls back to the sdist with no
# binary at all. glibc is the requirement; the distribution is not.
#
# A host with no registry passes a base from images/bootstrap-base.sh (§5.1.2).
ARG BASE_IMAGE=python:3.12-slim-trixie
FROM ${BASE_IMAGE}

# Debian's python3 only when the base has none: beside the default's 3.12 it
# would be a second, older interpreter.
RUN set -eu; \
    pkgs="git ca-certificates"; \
    command -v python3 >/dev/null || pkgs="$pkgs python3 python3-pip python3-venv"; \
    apt-get update; \
    apt-get install -y --no-install-recommends $pkgs; \
    rm -rf /var/lib/apt/lists/*; \
    command -v python >/dev/null || ln -s "$(command -v python3)" /usr/local/bin/python; \
    update-ca-certificates

# pip trusts certifi and uv reads only SSL_CERT_FILE (measured), so a CA mounted
# into /usr/local/share/ca-certificates reaches neither without these.
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# Pinned: unpinned, the agent runtime drifts between rebuilds and the version
# that ran a task is recorded nowhere. Bump deliberately.
ARG SDK_VERSION=0.2.142
# Unconditionally: a distribution base is PEP 668 externally managed. No `||`
# fallback — measured, one reported PEP 668 for an install that had failed on TLS.
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

# A spec session's Bash runs as this account, never as root (§5.5). Its
# global git config trusts /work so a clone owned by it is not "dubious".
RUN groupadd --system unprivileged \
    && useradd --system --gid unprivileged --create-home \
         --home-dir /home/unprivileged --shell /usr/sbin/nologin unprivileged \
    && printf '[safe]\n\tdirectory = /work\n\tdirectory = /work/.git\n' \
         > /home/unprivileged/.gitconfig \
    && chown unprivileged:unprivileged /home/unprivileged/.gitconfig

COPY images/unprivileged.sh /opt/saffron/unprivileged
RUN chmod 0755 /opt/saffron/unprivileged

# Asserts the wrapper drops root, the account cannot write the runner, and
# the CLI still names the env var that routes Bash through the wrapper (§5.5).
RUN set -eu; \
    uid=$(/opt/saffron/unprivileged 'id -u'); \
    want=$(id -u unprivileged); \
    [ "$uid" = "$want" ] && [ "$uid" != "0" ] \
      || { echo "the wrapper did not drop to the unprivileged account" >&2; exit 1; }; \
    /opt/saffron/unprivileged 'test -w /opt/saffron/agent_runner.py' \
      && { echo "the unprivileged account can write the runner" >&2; exit 1; }; \
    grep -aqF CLAUDE_CODE_SHELL_PREFIX /opt/saffron/claude-code \
      || { echo "the CLI binary lost CLAUDE_CODE_SHELL_PREFIX" >&2; exit 1; }

WORKDIR /work

# Every line a version the tool printed about itself (§5.1.2). One substitution per
# step: `set -e` misses a failure inside `$(a | b)` or `echo "$(a)"` — measured, dash.
RUN set -eu; \
    base=$(. /etc/os-release && echo "$ID $VERSION_ID"); \
    py=$(python --version 2>&1); \
    gitv=$(git --version); \
    sdk=$(python -c 'import importlib.metadata as m; print(m.version("claude-agent-sdk"))'); \
    cc=$(/opt/saffron/claude-code --version 2>&1); \
    cc=$(printf '%s\n' "$cc" | head -n 1); \
    printf 'base=%s\npython=%s\ngit=%s\nclaude-agent-sdk=%s\nclaude-code=%s\n' \
      "$base" "$py" "$gitv" "$sdk" "$cc" > /opt/saffron/provenance; \
    if grep -q '=$' /opt/saffron/provenance; then \
      echo "a tool printed no version:" >&2; cat /opt/saffron/provenance >&2; exit 1; fi; \
    grep -q '^python=Python 3\.12\.' /opt/saffron/provenance \
      || { echo "base image is not Python 3.12:" >&2; cat /opt/saffron/provenance >&2; exit 1; }
