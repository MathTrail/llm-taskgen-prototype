# llm-taskgen-prototype
Standalone PoC for evaluating multi-agent LLM pipelines (Methodist, Generator, Analyst, Skeptic) to generate verified, adaptive Math Olympiad tasks and synthetic fine-tuning datasets.

## Getting started

Work from the devcontainer: it has Python 3.12, `uv`, Docker (docker-in-docker) and `psql`.

1. Open the folder in VS Code → "Reopen in Container". Creating the container runs `uv sync`.
2. `cp .env.example .env` and fill in `ANTHROPIC_API_KEY` (needed from T18).
3. `docker compose up -d --wait` — PostgreSQL 17 on `localhost:5432`.
4. `uv run python db/apply_schema.py` — create the schema from `db/schema.sql`. The script recreates the whole schema; if the tables already hold data, it refuses without `--force`.
5. `uv run python seed.py` — load the five starting profiles from `db/seed/*.json`. Rerunning resets them; `--student masha` resets one student.
6. `uv run pytest` — tests.

Next steps follow [RUN.md](RUN.md).

## Documents

- [SPEC.md](SPEC.md) — what we build.
- [RUN.md](RUN.md) — implementation plan, one task at a time.
- [docs/architecture/](docs/architecture/) — diagrams.
- [research/](research/) — research done before the prototype.
- [CLAUDE.md](CLAUDE.md) — rules for Claude Code in this repository.
