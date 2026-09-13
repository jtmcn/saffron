# Saffron as a target repo — same shape as any other (DESIGN.md §10).
# Toolchain and dependencies only; the agent runtime came from the base.
FROM saffron/cell-base:python

# uv from pypi, not `COPY --from=ghcr.io/astral-sh/uv`: a registry copy is a
# second registry this image needs, and ghcr.io refuses at its blob CDN exactly
# as docker.io does (docs/evidence/2026-09-11-podman-as-a-second-cell-runtime.md).
# pypi is already required by the base. Pinned to the host's uv, which writes the
# `uv.lock` that `uv sync --frozen` reads below — bump the two together.
ARG UV_VERSION=0.12.11
RUN python -m pip install --no-cache-dir --break-system-packages "uv==${UV_VERSION}" \
 && uv --version

# procps for pgrep: the suite asserts that a timed-out gate leaves no surviving
# process. A repo declares what its own tests need; the base image does not.
RUN apt-get update \
 && apt-get install -y --no-install-recommends procps \
 && rm -rf /var/lib/apt/lists/*

# Build straight into /opt/venv rather than syncing elsewhere and moving it: a
# console script bakes its interpreter into its shebang, so a relocated venv
# leaves `pytest` pointing at a path that no longer exists and exiting 127.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

# Dependencies bake into the image layer so a cell starts from it rather than
# resolving on every task. No fixture services: Saffron's own suite needs none.
COPY pyproject.toml uv.lock /seed/
RUN cd /seed && uv sync --frozen --no-install-project
# `uv run` re-resolves the project on every invocation, and the proxy allows one
# host — so an agent's habitual `uv run pytest` takes a 403 from pypi.org and
# spends turns recovering. Measured on SA-0002. It runs out of the baked venv.
ENV VIRTUAL_ENV=/opt/venv PATH="/opt/venv/bin:$PATH" UV_NO_SYNC=1

# Run the toolchain, do not merely locate it. `which pytest` prints a path for a
# console script whose shebang is broken, which is how the relocated venv above
# shipped: a green check that reads identically when the tool cannot run
# (Appendix H, principle 34). The last clause is UV_NO_SYNC's own check, with
# the network refused: the defect it closes stays green and bills the agent a
# turn, so nothing else would report the ENV going missing. /seed survives the
# sync above only to give `uv run` a project here.
RUN ruff --version && ty --version && pytest --version && git --version \
 && pgrep --version \
 && pyshacl --version \
 && ast-grep --version \
 && cd /seed && UV_OFFLINE=1 uv run python -c "import pytest" && rm -rf /seed
