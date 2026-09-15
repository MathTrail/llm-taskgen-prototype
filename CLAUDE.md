# CLAUDE.md — working rules for this repository

Prototype: a chain of LLM agents generates olympiad-style math problems for grades 1–4 (5 options A–E; style follows Soviet problem books). The code is throwaway; the goal is to test the hypothesis in SPEC.

## Documents

- [SPEC.md](SPEC.md) — what we build. The source of truth.
- [RUN.md](RUN.md) — implementation plan: tasks T01–T31, run one at a time. Full executor rules are in its «Как пользоваться» section.
- [docs/decisions.md](docs/decisions.md) — decision log: what was decided, why, and which alternatives were rejected. Read it before proposing design changes.
- [docs/architecture/](docs/architecture/) — diagrams. Each file ends with a «Замечания к SPEC» section.
- [research/](research/) — pre-prototype research; summary in [research/11-spec-recommendations.md](research/11-spec-recommendations.md).

Project context lives in these files, not in chat history: Claude sessions on the host and in the devcontainer cannot see each other.

## How we work

- The author runs tasks one at a time: «Выполни задачу Txx из RUN.md». Do only that task.
- When done, mark the task in the `RUN.md` summary table: `[ ]` → `[x]`.
- Finish with a short report in Russian: what was done, which files, how to check it, what is still open.
- Do not commit: the author commits after review.
- If a task contradicts SPEC or something is missing, stop and ask. Do not silently fill SPEC gaps — record them in the «Замечания к SPEC» section of the document being worked on.
- Before any Claude API calls, state the expected cost and wait for confirmation.
- Do not re-propose alternatives rejected in `docs/decisions.md` without new evidence. If a decision has to change, ask the author and update the log.

## Hard rules

- **Exact versions only.** No `latest`, no floating tags. Docker images: exact tag or digest; tools (`uv`, `claude`), devcontainer features, VS Code extensions: exact version; Python dependencies are pinned in `uv.lock`.
- **Language.** Code, prompts, data, `CLAUDE.md` and every comment in code and config files (Python, SQL, YAML, Dockerfile, `.env.example`, etc.) — strictly English. Project documents (SPEC, RUN, docs, research) and reports to the author — Russian.
- **One contest is never named.** Our tasks are olympiad-style problems; the repository never names the international multiple-choice contest the project started from, in any language (D36). Other olympiads may be named, e.g. as problem sources.
- **Children's data.** Profiles and prompts use pseudonyms like `masha` only: no real names, birth dates or schools (SPEC 4.1).
- **Secrets** live only in `.env`, which is never committed.

## The author

The author is an experienced olympiad problem solver and coaches a child on such problems; they review task quality themselves. Do not suggest external experts or review panels.

## Environment

We work from the devcontainer (`.devcontainer/`): Python 3.12, `uv`, Docker inside the container (docker-in-docker), `psql`, Claude Code CLI.

- `uv sync` installs dependencies, `uv run pytest` runs the tests.
- All code lives in the `taskgen` package in `src/taskgen/` (src layout, installed editable by `uv sync`); run modules with `uv run python -m taskgen.<module>`, e.g. `uv run python -m taskgen.seed`. Nothing but code goes into `src/`; the repo root holds config, docs, `db/schema.sql`, contracts (`schemas/`, `prompts/`) and `data/` with all hand-written data — catalogs, examples, seed profiles, eval set (D35).
- PostgreSQL (from T07): `docker compose up -d`; inside the devcontainer it is reachable on `localhost:5432`, `DATABASE_URL` is in `.env` (template: `.env.example`).

## What is open

Progress is tracked in the `RUN.md` summary table.

The phase 0 checkpoint has not been passed: `docs/architecture/01…05` hold 19 remarks on SPEC, 18 still open (03-1 resolved in T09, see D34; 03-3 and 03-4 added in T12). Some are needed earlier than others:

- a module for checks (structure, readability, duplicates) — before T15;
- empty difficulty corridor and separate K₀ values — before T13 and T17;
- model prices in `config.yaml` — before T18;
- reason codes `bad_structure` and `fix_changed_task`, check order — before T23.
