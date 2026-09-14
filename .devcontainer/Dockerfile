FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# uv: зависимости проекта (pyproject.toml, uv.lock)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# psql: смотреть БД руками (T07).
# Источник Yarn из базового образа убираем: его ключ подписи устарел, и apt-get update падает.
RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*
