# llm-taskgen-prototype
Standalone PoC for evaluating multi-agent LLM pipelines (Methodist, Generator, Analyst, Skeptic) to generate verified, adaptive Math Olympiad tasks and synthetic fine-tuning datasets.

## Запуск

Работаем из devcontainer: в нём Python 3.12, `uv`, Docker (docker-in-docker) и `psql`.

1. Открыть папку в VS Code → «Reopen in Container». При создании контейнера выполняется `uv sync`.
2. `cp .env.example .env` и вписать `ANTHROPIC_API_KEY` (нужен с T18).
3. `uv run pytest` — проверка каркаса.

Дальше — по [RUN.md](RUN.md): PostgreSQL (`docker compose up -d`) появится в T07, стартовые профили — в T09.

## Документы

- [SPEC.md](SPEC.md) — что строим.
- [RUN.md](RUN.md) — порядок работы, задачи по одной.
- [docs/architecture/](docs/architecture/) — схемы.
- [research/](research/) — исследование перед прототипом.
- [CLAUDE.md](CLAUDE.md) — правила для Claude Code в этом репозитории.
