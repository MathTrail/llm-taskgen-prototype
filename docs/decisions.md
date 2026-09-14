# Decision log

Why the prototype looks the way it does. Every entry: what was decided, why, what was rejected, where it lives in [SPEC.md](../SPEC.md).

**Rule:** do not re-propose a rejected alternative without new evidence. If a decision has to change, ask the author and update this file.

The spec grew out of a chat with Gemini, then a research phase ([research/](../research/)), then a review of SPEC against that research, then phase 0 of [RUN.md](../RUN.md) (architecture diagrams). Several early ideas from that chat were later reversed; the reversals are recorded below.

## Scope

**D01. Throwaway Python prototype.** Plain scripts, console only. No k8s, Kafka, Go, workers, UI. — *Why:* test the hypothesis fast; only prompts, schemas and conclusions move to MathTrail later. — SPEC 1, 2, 11.

**D02. Grades 1–4, adapted per student.** No per-grade rules (e.g. "shorter questions for grade 1"): the Methodist tunes length and wording from the student's own history and feedback. How a student gives feedback (button, video, voice, text) is out of scope — just a `feedback` field. — *Rejected:* grades 2–4 only; per-grade constraints. — SPEC 1, 2, 4.1.

**D03. Language.** Problems, prompts, data, code comments, `CLAUDE.md`, this file — English. SPEC, RUN, docs, research and reports to the author — Russian. — *Rejected:* Russian-language problems.

**D04. Text-only problems.** — *Why:* 60–70% of real Kangaroo problems use a picture, and even top models are much weaker on visual problems (research/01–02). The prototype tests only the text part of the contest. Pictures (SVG or image generation) come after the prototype. — SPEC 1, 2, 4.2, 11.

**D05. Closed topic catalog.** 10 text-solvable topics in `topics.json`. Excluded: spatial geometry, visual counting, symmetry, geometry described in words, heavy arithmetic and fractions, school motion/work problems, and `patterns.sequences` (several plausible continuations; code cannot prove the rule is unique). All remaining topics are brute-force computable — the program check depends on that. — SPEC 4.2.

## Agents and pipeline

**D06. The Methodist picks the target.** The caller does not specify topic or difficulty; an LLM Methodist chooses topic, points, pedagogical goal, setting and traps from the profile. — *Why:* the author corrected an early design where the target was an input. — SPEC 5.1.

**D07. Four roles: Methodist → Generator → Analyst ∥ Skeptic.** Analyst and Skeptic see only question and options, run in parallel. — *Rejected:* single blind verifier (shared blind spots); multi-agent framework such as LangChain (plain code is clearer for a fixed workflow, per Anthropic's "Building effective agents"). — SPEC 5, 10.

**D08. Acceptance needs all six conditions.** Valid structure; X = Y = Z; the Analyst's program returns exactly `[X]`; no blocking Skeptic issue; readability filter; no near duplicate. — *Why:* three matching letters alone do not prove the problem is unambiguous. — SPEC 6.

**D09. Attempt limit is 3.** The rejection reason goes to the Generator; the Methodist is not re-called; the brief stays the same. — *Why:* after two targeted fixes models mostly reshuffle the same broken ideas; cost; a failure after 3 attempts is itself a useful signal. — *Rejected:* 5 attempts. — SPEC 6.

**D10. Generator answer error is fixed, not swapped.** If Analyst, Skeptic and the program agree and differ from the Generator, the next attempt repairs the same problem (answer, solution, distractors, hint) with question and options unchanged; verifiers are not re-run; the fix counts as an attempt. — *Rejected:* just replacing `correct_answer` (distractor texts and the solution would become wrong). — SPEC 6.

**D11. No separate hint/explanation agent.** The Generator writes `hint` and a child-facing `text` per distractor up front; the full explanation is the Analyst's reasoning, written in plain language for grades 1–4. — *Why:* no extra call per hint or mistake. — *Rejected:* a dedicated tutor-feedback agent (moved to MathTrail's mentor-api later). — SPEC 5.2, 5.3, 11.

**D12. Program verification: the Analyst writes `solver_code` in the same call.** The code brute-forces every option and prints the list of correct letters; it runs in a network-less Docker sandbox. — *Why:* all agents are Claude models and same-provider errors correlate (research/05); code fails for different reasons. — *Rejected:* a separate Programmer agent (extra call); no program check. — *Known limit:* the code shares the Analyst's reading of the problem; the Skeptic covers ambiguity in the text. — SPEC 5.3, 6.

**D13. Skeptic prompt carries an explicit ambiguity checklist.** — *Why:* models recognize ambiguity but rarely report it unless asked (research/05). — SPEC 5.4.

**D14. Closed traps catalog.** `traps.json`; `traps_to_use`, `distractors[].trap` and `trap_hit` use ids only. — *Why:* free text cannot be aggregated; Eedi ties distractors to a misconception taxonomy (research/04). — SPEC 4.5.

## Student model and adaptivity

**D15. Profile fields.** `cognitive_profile` (merged from `notes` + `error_patterns`), `mastered_topics`, `excluded_skills` (ids from `skills.json`), `consecutive_failures`, full history with `pace` tags instead of raw seconds, `trap_hit`, `feedback`, `hint_used`. The Methodist gets the last 5 history rows; the DB keeps all. The Methodist reports `profile_fields_used` so the prototype shows which fields matter. — SPEC 4.1, 5.1.

**D16. `--answer` mode simulates a student.** Needed to test how the Methodist changes strategy after mistakes. Inputs `A`–`E`, `?` ("don't understand"), `H` (hint), `exit`; a hint does not count as a failure. — SPEC 3.

**D17. Ratings are computed by code (Elo + IRT), not by the LLM.** P = 0.2 + 0.8·σ(θ + δ_topic − β): global level θ, per-topic offset δ, task difficulty β, guessing floor 0.2 (5 options, no penalty); Elo-style online updates with K decaying by answer count; difficulty corridor P ∈ [0.70, 0.85]. The Methodist picks difficulty inside the corridor. — *Why:* LLMs are worse learner models than classic knowledge tracing (research/06); Math Garden targets ~75% success. — *From the ChatGPT discussion:* adopted global level plus topic offset, lower corridor bound 0.70, chess-scale display; rejected "recent results" and "age" terms (the Methodist handles streaks; task ratings are already per grade level). — SPEC 5.6.

**D18. Rule-based tutor as a baseline.** `--tutor rule` produces a brief in the same format without an LLM. Hypothesis 1 is "the LLM Methodist beats a simple rule". — SPEC 5.7, 9.

## Data and storage

**D19. Everything lives in PostgreSQL (Docker).** Profiles, history, ratings, task bank, request and attempt logs; datasets are views. Starting profiles are hand-written JSON loaded by `seed.py`, which also resets a student. Answers persist across runs. — *Rejected:* files in `output/`; profile kept in memory. — SPEC 3, 7.

**D20. Task bank with reuse.** Before generating, search the bank: exact SQL filter (topic, rating in corridor, grade level, `tasks.excluded_skills @> student's`, never issued to this student) plus ranking in code (setting, shared traps). `--fresh` skips the bank for experiments. — SPEC 5.5.

**D21. No pgvector for now.** Exact fields (grade, topics, skills) must never be vectors. Semantic memory comes later, and serves the Generator (topic already chosen), not the Methodist (topic not chosen yet) — this corrects Gemini's suggestion. — SPEC 2, 4.1, 11.

**D22. Datasets are collected but never used for fine-tuning.** Anthropic's terms forbid using Claude outputs as training targets without written permission (research/08). The collected views are an evaluation reference for local models; phase 2 fine-tuning uses ready open datasets (licenses to be checked). — *Rejected:* distilling Claude into a local model. — SPEC 1, 7, 11.

**D23. Reference examples are written by the author.** ~30 Kangaroo-style problems (3 per topic) with trap annotations. Real Kangaroo problems are never used: SMART-840 forbids commercial use and AI training, MathArena's set is CC BY-NC-SA (research/02). — SPEC 4.3.

**D24. Children's data: pseudonyms only.** No real names, birth dates or schools in profiles or prompts. Video and voice feedback would be biometric data under COPPA 2025 — legal review before any use. — SPEC 4.1, 11.

**D34. Starting history has no `task_id`.** Seed profiles (`data/seed/*.json`) omit it and `schemas/profile.json` rejects it; `seed.py` writes `student_tasks.task_id` as NULL. — *Why:* those tasks are not in the bank, so the foreign key would fail (remark 03-1). — *Rejected:* keeping `task_id` in the file and dropping it on load (the file and the DB would silently disagree). — SPEC 4.1, 7.

## Models and cost

**D25. All agents run on Claude in the prototype.** Haiku 4.5 — Methodist; Opus 5 — Generator; Sonnet 5 — Analyst and Skeptic (the Skeptic deliberately uses a different model than the Generator). — *Reversals:* Gemini first proposed cloud models; the author then asked for a hybrid with local models (Methodist and Skeptic local); after the review the author chose all-Claude to keep things simple. Weak local verifiers would also degrade the dataset reference. Local models are phase 2. — *Rejected:* GPT/Gemini Skeptic (second paid provider). — SPEC 8.

**D26. No `temperature`.** Opus 5 and Sonnet 5 reject sampling parameters (HTTP 400); depth is set with `effort`. — SPEC 5.3, 8.

**D27. Budget.** Rough estimate $0.15–0.23 per attempt, driven by Opus 5 output with thinking. The target "< $0.10 per accepted task" is kept but expected to fail; an experiment compares the Generator on Sonnet 5 vs Opus 5 at low effort. — SPEC 8, 9.

**D28. Quality review is done by the author alone.** The author is an experienced Kangaroo solver and coach. — *Rejected:* external coach, child trials as a formal step. — SPEC 9.

**D29. "False accepts" means math failures only.** Wrong answer, ambiguity, no solution, several correct options. Style and age fit belong to the quality metric — this removed a contradiction between the two targets. — SPEC 9.

## Process and environment

**D30. RUN.md, one task at a time.** Architecture diagrams first (phase 0); the executor marks the task `[x]` when done; no commits; stop and ask on SPEC gaps and record them in «Замечания к SPEC». — RUN.md, CLAUDE.md.

**D31. Devcontainer.** Python 3.12 + `uv`, docker-in-docker (as in the author's `identity` repo), `psql`, Claude Code CLI and extension 2.1.270 with auto-update disabled; Claude config lives in a named volume so login survives rebuilds. — `.devcontainer/`.

**D32. Exact versions only.** No `latest` or floating tags anywhere: image tag or digest, tool and feature versions, VS Code extension versions, `uv.lock`. — CLAUDE.md.

**D33. Host and container sessions are separate.** Claude history is keyed by config dir and project path, both differ in the container. Context therefore lives in files: SPEC, RUN, docs, CLAUDE.md and this log. — *Rejected:* sharing the host `~/.claude` and mirroring the host path into the container.

**D35. src layout: all code in the `taskgen` package.** Every Python module lives in `src/taskgen/`, including utilities (`catalogs`, `apply_schema`, and later `validate_examples`, `try_<agent>`, `run_eval`, `report`, `review`); nothing but code goes into `src/`. The repo root keeps config (`config.yaml`), docs, `db/schema.sql`, the contracts `schemas/` and `prompts/` (they move to MathTrail, SPEC 11), and `data/` with all hand-written data: catalogs, examples, seed profiles, eval set. `uv sync` installs the package in editable mode (`uv_build` backend, pinned); modules run with `uv run python -m taskgen.<module>`. — *Why:* the author does not want code in the root; the src layout is the Python convention and removes the `db.py` / `db/` name clash. — *Rejected:* modules in the root (as SPEC 10 first had them); console scripts in `[project.scripts]` (one registration per program, about ten by T30); a separate `scripts/` folder. — SPEC 3, 10.

## Deferred

- **Where the verifiers live in MathTrail** (`llm-taskgen` or `solution-validator`) — decided later. SPEC 11.
- **17 remarks from phase 0** in `docs/architecture/01…05` («Замечания к SPEC») — to be resolved at the phase 0 checkpoint. Resolved so far: 03-1 (D34).
