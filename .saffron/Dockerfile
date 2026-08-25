# Saffron as a target repo — same shape as any other (DESIGN.md §10).
# Toolchain and dependencies only; the agent runtime came from the base.
FROM saffron/cell-base:python

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

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
RUN ruff --version && pytest --version && git --version && pgrep --version \
 && cd /seed && UV_OFFLINE=1 uv run python -c "import pytest" && rm -rf /seed
