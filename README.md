# llm-taskgen-prototype
Prototype of an MCP server that lets the chat client's own model (Claude, ChatGPT and others) generate verified, adaptive olympiad-style maths tasks for grades 1–4. The server keeps the student's profile and ratings, recommends the next task, gives the model reference examples and checks every task it writes. It makes no LLM API calls of its own: the text is written within the user's own subscription.

## Getting started

Work from the devcontainer: it has Python 3.12, `uv`, Docker (docker-in-docker), `psql` and Claude Code.

1. Open the folder in VS Code → "Reopen in Container". Creating the container runs `uv sync`.
2. `cp .env.example .env`.
3. `docker compose up -d --wait` — PostgreSQL 17 on `localhost:5432`.
4. `uv run python -m taskgen.apply_schema` — create the schema from `db/schema.sql`. The script recreates the whole schema; if the tables already hold data, it refuses without `--force`.
5. `uv run python -m taskgen.seed` — load the five starting profiles from `data/seed/*.json`. Rerunning resets them; `--student masha` resets one student.
6. `uv run pytest` — tests.

From T19 the MCP server is connected to Claude Code through `.mcp.json` in the repository root: start `claude` in the project folder and check `/mcp`.

All code lives in the `taskgen` package in `src/taskgen/`, installed into the venv by `uv sync`. Run any module with `uv run python -m taskgen.<module>`.

Next steps follow [RUN.md](RUN.md).

## Documents

- [SPEC.md](SPEC.md) — what we build.
- [RUN.md](RUN.md) — implementation plan, one task at a time.
- [docs/decisions.md](docs/decisions.md) — decision log.
- [docs/architecture/](docs/architecture/) — diagrams.
- [research/](research/) — research done before the prototype.
- [CLAUDE.md](CLAUDE.md) — rules for Claude Code in this repository.
