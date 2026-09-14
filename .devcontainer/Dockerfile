# Версии только конкретные: тег базового образа плавающий, поэтому закреплён digest.
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm@sha256:7876580dc67fd460fd962f004cbeb480027e9bbc0657096f1087db11f9eaff39

# uv: зависимости проекта (pyproject.toml, uv.lock)
COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /uvx /usr/local/bin/

# psql: смотреть БД руками (T07).
# Источник Yarn из базового образа убираем: его ключ подписи устарел, и apt-get update падает.
RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*
