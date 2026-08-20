# Saffron as a target repo — same shape as any other (DESIGN.md §10).
# Toolchain and dependencies only; the agent runtime came from the base.
FROM saffron/cell-base:python

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Dependencies bake into the image layer so a cell starts from it rather than
# resolving on every task. No fixture services: Saffron's own suite needs none.
COPY pyproject.toml uv.lock /seed/
RUN cd /seed && uv sync --frozen --no-install-project && \
    mv /seed/.venv /opt/venv && rm -rf /seed
ENV VIRTUAL_ENV=/opt/venv PATH="/opt/venv/bin:$PATH"
