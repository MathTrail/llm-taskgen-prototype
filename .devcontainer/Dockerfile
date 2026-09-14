# Exact versions only: the base image tag floats, so it is pinned by digest.
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm@sha256:7876580dc67fd460fd962f004cbeb480027e9bbc0657096f1087db11f9eaff39

# uv: project dependencies (pyproject.toml, uv.lock)
COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /uvx /usr/local/bin/

# psql: inspect the database by hand (T07).
# The base image ships a Yarn apt source with an expired signing key that breaks apt-get update, so drop it.
RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*
