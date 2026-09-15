"""Logic of the MCP tools (SPEC 5.8): plain functions over the database, tested without MCP.

mcp_server.py only adapts them to MCP. Every function takes an open connection; the adapter opens one per tool call.
Nothing here prints: over stdio, stdout carries the protocol.
"""

import hashlib
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import psycopg

from taskgen import ROOT
from taskgen.catalogs import load_catalog
from taskgen.db import HISTORY_LIMIT, database_url, grade_level, list_students, load_student
from taskgen.rating import Params, corridor, elo

INSTRUCTIONS = ROOT / "prompts" / "mcp_instructions.md"
RECENT_ANSWERS = 10  # get_progress shows this many latest answers


class StudentNotFound(LookupError):
    """No student with this pseudonym; the message lists the known ones for the model."""


def instructions() -> str:
    """The server's instructions for the client's model."""
    return INSTRUCTIONS.read_text(encoding="utf-8")


def prompt_version(paths: tuple[Path, ...] = (INSTRUCTIONS,)) -> str:
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


def student_profile(conn: psycopg.Connection, student_id: str, params: Params) -> dict:
    """Everything the model needs to choose the next task (get_student_profile)."""
    student = require_student(conn, student_id)
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
        "recent_history": [
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
            for row in student["history"]
        ],
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
