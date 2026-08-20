# saffron/cell-base:python — agent runtime, git, and the gate shim. Nothing else.
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

RUN pip install --no-cache-dir claude-agent-sdk

# The bundled binary is the whole reason this image is Debian. If a source
# distribution was installed instead, the agent has no runtime and every cell
# fails at turn one with an error nobody would trace back to the image.
RUN python -c "import claude_agent_sdk, pathlib, sys; \
p = pathlib.Path(claude_agent_sdk.__file__).parent; \
found = list(p.rglob('claude-code*')) + list(p.rglob('claude')); \
sys.exit(0) if found else sys.exit('no bundled Claude Code binary in the wheel')"

WORKDIR /work
