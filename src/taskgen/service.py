"""Logic of the MCP tools (SPEC 5.8): plain functions over the database, tested without MCP.

mcp_server.py only adapts them to MCP. Every function takes an open connection; the adapter opens one per tool call,
so a tool call is one transaction. Nothing here prints: over stdio, stdout carries the protocol.
"""

import hashlib
import json
import re
import time
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

import psycopg
import yaml

from taskgen import ROOT
from taskgen.catalogs import load_catalog
from taskgen.db import (
    HISTORY_LIMIT,
    bank_candidates,
    close_request,
    create_request,
    database_url,
    grade_level,
    issue_task,
    list_students,
    load_student,
    task_questions,
)
from taskgen.filters import load_thresholds
from taskgen.rating import DIFFICULTIES, Params, corridor, difficulty_to_beta, elo
from taskgen.tutor_rule import make_brief, pick_traps
from taskgen.validate_examples import load_examples

INSTRUCTIONS = ROOT / "prompts" / "mcp_instructions.md"
GUIDE = ROOT / "prompts" / "task_writing.md"
PROMPT_FILES = (INSTRUCTIONS, GUIDE)
RECENT_ANSWERS = 10  # get_progress shows this many latest answers
RECENT_TASKS = 5  # get_next_task lists the questions of this many latest bank tasks, so the model does not repeat them
EXAMPLES_PER_PACKAGE = 3
LANGUAGE = re.compile(r"[a-z]{2}")  # ISO 639-1
BANK_TASK_NOTE = (
    "Show the question and the options A-E. Give the hint only when the child asks for help. "
    "The correct answer, the trap texts and the solution come after the child answers."
)


class StudentNotFound(LookupError):
    """No student with this pseudonym; the message lists the known ones for the model."""


class InvalidRequest(ValueError):
    """The model's arguments cannot be used; the message says how to fix them."""


def instructions() -> str:
    """The server's instructions for the client's model."""
    return INSTRUCTIONS.read_text(encoding="utf-8")


def prompt_version(paths: tuple[Path, ...] = PROMPT_FILES) -> str:
    """12 hex digits of SHA-256 over the names and contents of the instruction files, in any order (SPEC 5.8)."""
    digest = hashlib.sha256()
    for path in sorted(Path(path) for path in paths):
        digest.update(path.name.encode("utf-8") + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()[:12]


@contextmanager
def connect(url: str | None = None) -> Iterator[psycopg.Connection]:
    """One connection and one transaction per tool call: committed on success, rolled back on an error."""
    with psycopg.connect(url or database_url()) as conn:
        yield conn


def require_student(conn: psycopg.Connection, student_id: str, history_limit: int | None = HISTORY_LIMIT) -> dict:
    student = load_student(conn, student_id, history_limit)
    if student is None:
        known = ", ".join(list_students(conn)) or "none"
        raise StudentNotFound(f"no student {student_id!r}; known students: {known}")
    return student


def grade_topics(grade: int) -> list[dict]:
    """Catalog topics taught at the student's grade level, in catalog order."""
    level = grade_level(grade)
    return [topic for topic in load_catalog("topics") if level in topic["grade_levels"]]


def topic_level(student: dict, topic: str) -> tuple[float, int]:
    """(theta + delta, answers in the topic); a topic without answers has delta 0."""
    rating = student["topic_ratings"].get(topic, {"offset": 0.0, "answers_count": 0})
    return student["rating"] + rating["offset"], rating["answers_count"]


def answer_result(row: dict) -> str:
    if row["correct"] is True:
        return "correct"
    if row["correct"] is False:
        return "wrong"
    return "did not understand" if row.get("feedback") else "not answered"


def history_rows(rows: list[dict]) -> list[dict]:
    return [
        {
            "topic": row["topic"],
            "difficulty": row["difficulty"],
            "result": answer_result(row),
            "chosen_option": row["chosen_option"],
            "trap_hit": row["trap_hit"],
            "hint_used": row["hint_used"],
            "pace": row["pace"],
            "date": row["issued_at"].date().isoformat(),
        }
        for row in rows
    ]


# get_student_profile and get_progress


def student_profile(conn: psycopg.Connection, student_id: str, params: Params) -> dict:
    """Everything the model needs to choose the next task, with the rule's brief as a recommendation."""
    student = require_student(conn, student_id, history_limit=None)  # the rule needs the whole history
    topics = []
    for topic in grade_topics(student["grade"]):
        level, answers = topic_level(student, topic["id"])
        fit = corridor(level, params.corridor)
        topics.append({
            "topic": topic["id"],
            "name": topic["name"],
            "level": round(level, 3),
            "rating": round(elo(level)),
            "answers": answers,
            "mastered": topic["id"] in student["mastered_topics"],
            "recommended_difficulty": fit.recommended,
            "corridor_fit": fit.fit,
            "success_chance": round(fit.probabilities[fit.recommended], 2),
        })  # fmt: skip
    return {
        "student_id": student["student_id"],
        "grade": student["grade"],
        "grade_level": grade_level(student["grade"]),
        "interests": student["interests"],
        "cognitive_profile": student["cognitive_profile"],
        "mastered_topics": student["mastered_topics"],
        "excluded_skills": student["excluded_skills"],
        "consecutive_failures": student["consecutive_failures"],
        "overall": {
            "level": round(student["rating"], 3),
            "rating": round(elo(student["rating"])),
            "answers": student["answers_count"],
        },
        "topics": topics,
        "recommendation": make_brief(student, params),
        "recent_history": history_rows(student["history"][-HISTORY_LIMIT:]),
    }


def progress(conn: psycopg.Connection, student_id: str, params: Params) -> dict:
    """A summary the model can share with the child (get_progress); no cognitive_profile here."""
    student = require_student(conn, student_id, history_limit=RECENT_ANSWERS)
    names = {topic["id"]: topic["name"] for topic in load_catalog("topics")}
    topics = []
    for topic in grade_topics(student["grade"]):
        level, answers = topic_level(student, topic["id"])
        mastered = topic["id"] in student["mastered_topics"]
        if answers or mastered:
            topics.append({"topic": topic["id"], "name": topic["name"], "rating": round(elo(level)),
                           "answers": answers, "mastered": mastered})  # fmt: skip
    return {
        "student_id": student["student_id"],
        "grade": student["grade"],
        "overall_rating": round(elo(student["rating"])),
        "answers": student["answers_count"],
        "failures_in_a_row": student["consecutive_failures"],
        "mastered_topics": [names.get(topic, topic) for topic in student["mastered_topics"]],
        "topics": topics,
        "recent_answers": [
            {
                "topic": names.get(row["topic"], row["topic"]),
                "difficulty": row["difficulty"],
                "result": answer_result(row),
                "hint_used": row["hint_used"],
                "date": row["issued_at"].date().isoformat(),
            }
            for row in student["history"]
        ],
    }


# get_next_task


@lru_cache(maxsize=None)
def load_schema(name: str) -> dict:
    return json.loads((ROOT / "schemas" / f"{name}.json").read_text(encoding="utf-8"))


def max_attempts() -> int:
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))["max_attempts"]


def pick_examples(topic: str, level: str, difficulty: int, offset: int) -> list[dict]:
    """EXAMPLES_PER_PACKAGE reference tasks of the topic and grade level nearest to the difficulty.

    Each cell holds 5 tasks; the offset (the number of history rows) rotates which of them the model sees.
    """
    pool = sorted(
        (task for task in load_examples() if task["topic"] == topic and task["grade_level"] == level),
        key=lambda task: (abs(task["difficulty"] - difficulty), task["id"]),
    )
    nearest = [task for task in pool if task["difficulty"] == pool[0]["difficulty"]] if pool else []
    start = offset % len(nearest) if nearest else 0
    return (nearest[start:] + nearest[:start])[:EXAMPLES_PER_PACKAGE]


def choose_brief(student: dict, params: Params, topic: str | None, difficulty: int | None,
                 reason: str | None) -> tuple[dict, str]:
    """The rule's brief, or that brief with the model's topic and difficulty (SPEC 5.1, D43); plus the tutor mode."""
    rule = make_brief(student, params)
    if topic is None and difficulty is None:
        return rule, "rule"
    if not (reason or "").strip():
        raise InvalidRequest("changing the topic or the difficulty needs a reason: say why in `reason`")
    allowed = [entry["id"] for entry in grade_topics(student["grade"])]
    chosen = topic or rule["target_concept"]
    if chosen not in allowed:
        raise InvalidRequest(f"topic {chosen!r} is not taught at grade {student['grade']}; choose one of {allowed}")
    if difficulty is None:
        difficulty = corridor(topic_level(student, chosen)[0], params.corridor).recommended
    elif difficulty not in DIFFICULTIES:
        raise InvalidRequest(f"difficulty must be 1-5, got {difficulty!r}")
    brief = dict(
        rule,
        target_concept=chosen,
        difficulty=difficulty,
        traps_to_use=rule["traps_to_use"] if chosen == rule["target_concept"] else pick_traps(student, chosen),
        rationale=(f"Changed by the model: {reason.strip()} The rule suggested {rule['target_concept']} at "
                   f"difficulty {rule['difficulty']}: {rule['rationale']}"),
    )  # fmt: skip
    return brief, "llm"


def next_task(conn: psycopg.Connection, student_id: str, language: str, params: Params, *,
              topic: str | None = None, difficulty: int | None = None, reason: str | None = None) -> dict:
    """A checked task from the bank, or everything the model needs to write a new one (get_next_task)."""
    started = time.monotonic()
    if not LANGUAGE.fullmatch(language or ""):
        raise InvalidRequest(f"language must be a two-letter ISO 639-1 code such as 'en' or 'ru', got {language!r}")
    student = require_student(conn, student_id, history_limit=None)
    brief, tutor_mode = choose_brief(student, params, topic, difficulty, reason)
    topic_id, level = brief["target_concept"], grade_level(student["grade"])
    value = topic_level(student, topic_id)[0]
    fit = corridor(value, params.corridor)
    if brief["difficulty"] == fit.recommended:
        betas = (fit.beta_min, fit.beta_max)
    else:  # the model chose another difficulty: look around its starting beta instead of the corridor
        beta = difficulty_to_beta(brief["difficulty"])
        betas = (beta - 0.5, beta + 0.5)

    request_id = create_request(conn, student_id, tutor_mode, brief)
    found = bank_candidates(conn, student, topic_id, betas, setting=brief["setting"],
                            traps_to_use=brief["traps_to_use"], language=language)  # fmt: skip
    if found:
        task = found[0]
        issue_task(conn, student_id, task["task_id"])
        close_request(conn, request_id, "bank", task["task_id"],
                      duration_ms=round((time.monotonic() - started) * 1000))  # fmt: skip
        return {
            "source": "bank",
            "request_id": request_id,
            "task_id": task["task_id"],
            "language": language,
            "topic": topic_id,
            "difficulty": task["difficulty"],
            "question": task["task"]["question"],
            "options": task["task"]["options"],
            "hint": task["task"]["hint"],
            "note": BANK_TASK_NOTE,
        }

    topics = {entry["id"]: entry for entry in load_catalog("topics")}
    skills = {entry["id"]: entry["description"] for entry in load_catalog("skills")}
    given = [row["task_id"] for row in reversed(student["history"]) if row["task_id"]][:RECENT_TASKS]
    questions = task_questions(conn, given)
    thresholds = load_thresholds()
    return {
        "source": "generate",
        "request_id": request_id,
        "language": language,
        "max_attempts": max_attempts(),
        "brief": brief,
        "tutor_mode": tutor_mode,
        "student": {
            "student_id": student["student_id"],
            "grade": student["grade"],
            "grade_level": level,
            "interests": student["interests"],
            "cognitive_profile": student["cognitive_profile"],
            "consecutive_failures": student["consecutive_failures"],
            "recent_history": history_rows(student["history"][-HISTORY_LIMIT:]),
        },
        "corridor": {
            "topic": topic_id,
            "level": round(value, 3),
            "recommended_difficulty": fit.recommended,
            "fit": fit.fit,
            "success_chance_by_difficulty": {str(d): round(p, 2) for d, p in fit.probabilities.items()},
        },
        "topic": {key: topics[topic_id][key] for key in ("id", "name", "description")},
        "traps": load_catalog("traps"),
        "excluded_skills": [{"id": skill, "description": skills.get(skill, "")} for skill in student["excluded_skills"]],
        "examples": pick_examples(topic_id, level, brief["difficulty"], len(student["history"])),
        "recent_tasks": [questions[task_id] for task_id in given if task_id in questions],
        "readability": {
            "max_sentence_words": thresholds.max_sentence_words[level],
            "max_flesch_kincaid_grade": student["grade"] + thresholds.max_grade_margin if language == "en" else None,
        },
        "formats": {"brief": load_schema("brief"), "task": load_schema("generator"), "self_check": load_schema("skeptic")},
        "guide": GUIDE.read_text(encoding="utf-8"),
    }
