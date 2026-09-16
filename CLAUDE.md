# CLAUDE.md — working rules for this repository

Prototype: an MCP server lets the chat client's own model (Claude, ChatGPT and others) generate olympiad-style math problems for grades 1–4 (5 options A–E; style follows Soviet problem books). The server keeps the student's profile and ratings, recommends the next task, gives the model reference examples and checks what it writes; it makes no LLM API calls of its own (D42). The code is throwaway; the goal is to test the hypothesis in SPEC.

## Documents

- [SPEC.md](SPEC.md) — what we build. The source of truth.
- [RUN.md](RUN.md) — implementation plan: tasks T01–T24, run one at a time. Full executor rules are in its «Как пользоваться» section.
- [docs/decisions.md](docs/decisions.md) — decision log: what was decided, why, and which alternatives were rejected. Read it before proposing design changes.
- [docs/architecture/](docs/architecture/) — diagrams. Each file ends with a «Замечания к SPEC» section. Diagram 01 shows the MCP server (redrawn in T19); 02 and 04 describe the old Claude API pipeline and are kept as history (D42).
- [research/](research/) — pre-prototype research; summary in [research/11-spec-recommendations.md](research/11-spec-recommendations.md).
- [PRODUCT-V1.md](PRODUCT-V1.md) — product spec for MathTrail Olympiad v1 (a free, open-source, stateless Go service): requirements, chat platform research, open questions. The starting point for the new repository.

Project context lives in these files, not in chat history: Claude sessions on the host and in the devcontainer cannot see each other.

## How we work

- The author runs tasks one at a time: «Выполни задачу Txx из RUN.md». Do only that task.
- When done, mark the task in the `RUN.md` summary table: `[ ]` → `[x]`.
- Finish with a short report in Russian: what was done, which files, how to check it, what is still open.
- Do not commit: the author commits after review.
- If a task contradicts SPEC or something is missing, stop and ask. Do not silently fill SPEC gaps — record them in the «Замечания к SPEC» section of the document being worked on.
- The prototype makes no paid LLM API calls (D42): do not propose API keys or API pipelines. If a task ever needs a paid call, state the expected cost and wait for confirmation. Live runs in Claude Code spend the author's subscription limits — say so before starting one.
- Do not re-propose alternatives rejected in `docs/decisions.md` without new evidence. If a decision has to change, ask the author and update the log.

## Hard rules

- **Exact versions only.** No `latest`, no floating tags. Docker images: exact tag or digest; tools (`uv`, `claude`), devcontainer features, VS Code extensions: exact version; Python dependencies are pinned in `uv.lock`.
- **Language.** Code, server instructions for the model (`prompts/`), data, `CLAUDE.md` and every comment in code and config files (Python, SQL, YAML, Dockerfile, `.env.example`, etc.) — strictly English. Tasks for the child are written by the client's model in the chat language. Project documents (SPEC, RUN, docs, research) and reports to the author — Russian.
- **One contest is never named.** Our tasks are olympiad-style problems; the repository never names the international multiple-choice contest the project started from, in any language (D36). Other olympiads may be named, e.g. as problem sources.
- **Children's data.** Profiles and everything the server sends to the model use pseudonyms like `masha` only: no real names, birth dates or schools (SPEC 4.1).
- **Secrets** live only in `.env`, which is never committed.

## The author

The author is an experienced olympiad problem solver and coaches a child on such problems; they review task quality themselves. Do not suggest external experts or review panels.

## Environment

We work from the devcontainer (`.devcontainer/`): Python 3.12, `uv`, Docker inside the container (docker-in-docker), `psql`, Claude Code CLI.

- `uv sync` installs dependencies, `uv run pytest` runs the tests.
- All code lives in the `taskgen` package in `src/taskgen/` (src layout, installed editable by `uv sync`); run modules with `uv run python -m taskgen.<module>`, e.g. `uv run python -m taskgen.seed`. Nothing but code goes into `src/`; the repo root holds config (`config.yaml`, `.mcp.json`), docs, `db/schema.sql`, contracts (`schemas/`, `prompts/`) and `data/` with all hand-written data — catalogs, examples, seed profiles, eval scenarios (D35).
- PostgreSQL (from T07): `docker compose up -d`; inside the devcontainer it is reachable on `localhost:5432`, `DATABASE_URL` is in `.env` (template: `.env.example`).
- The MCP server (from T19) runs over stdio and is connected to Claude Code through `.mcp.json`.

## What is open

Progress is tracked in the `RUN.md` summary table.

`docs/architecture/01…05` hold 20 remarks on SPEC; 4 are still open: 01-2 (story seed lists), 03-2 (no created_at in attempts, noted), 03-3 (`requests.source` while a request is open), 03-4 (bank tie-break). The rest were resolved in T09, T13, T15 or closed by the move to MCP (D42).
