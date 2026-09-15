"""PostgreSQL access: profiles, history, task bank, request and attempt logs (SPEC 5.5, 7).

Every function takes an open connection and never commits: the caller owns the transaction, so the rows of one
step are written together or not at all. Ratings are read and stored here; their math is in rating.py.
"""

import os
import sys
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from taskgen import ROOT

HISTORY_LIMIT = 5  # the Methodist gets the last 5 history rows (SPEC 3, 4.1)
OPTIONS = ("A", "B", "C", "D", "E")
TUTOR_MODES = ("llm", "rule")
SOURCES = ("bank", "generated", "failed")
STATUSES = ("accepted", "rejected", "generator_answer_error")
PACES = ("fast", "normal", "struggled")


def database_url() -> str:
    """DATABASE_URL from the environment, otherwise from the .env file in the repository root."""
    if url := os.environ.get("DATABASE_URL"):
        return url
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == "DATABASE_URL" and value.strip():
                return value.strip().strip("\"'")
    sys.exit("DATABASE_URL is not set: copy .env.example to .env")


def grade_level(grade: int) -> str:
    """Grade level of a school grade: tasks and their ratings are kept per level (SPEC 4.3, 5.6)."""
    if grade not in (1, 2, 3, 4):
        raise ValueError(f"grade must be 1-4, got {grade!r}")
    return "1-2" if grade <= 2 else "3-4"


# Students


def list_students(conn: psycopg.Connection) -> list[str]:
    """Ids of all students, sorted."""
    return [row[0] for row in conn.execute("SELECT student_id FROM students ORDER BY student_id").fetchall()]


def load_student(conn: psycopg.Connection, student_id: str, history_limit: int | None = HISTORY_LIMIT) -> dict | None:
    """Profile, overall rating, per-topic offsets and the last history rows (oldest first); None if unknown.

    history_limit=None gives the whole history, as the rule tutor needs.

    topic_ratings maps a topic id to {"offset": delta, "answers_count": n}; a topic without a row has offset 0.
    """
    with conn.cursor(row_factory=dict_row) as cursor:
        student = cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,)).fetchone()
        if student is None:
            return None
        ratings = cursor.execute(
            "SELECT topic, topic_offset, answers_count FROM student_topic_ratings WHERE student_id = %s ORDER BY topic",
            (student_id,),
        ).fetchall()
        student["topic_ratings"] = {
            row["topic"]: {"offset": row["topic_offset"], "answers_count": row["answers_count"]} for row in ratings
        }
        # Rows issued in one transaction share issued_at, so the id breaks the tie.
        history = cursor.execute(
            """
            SELECT id, task_id, topic, difficulty, issued_at, correct, chosen_option, trap_hit, feedback,
                   hint_used, pace
            FROM student_tasks
            WHERE student_id = %s
            ORDER BY issued_at DESC, id DESC
            LIMIT %s
            """,
            (student_id, history_limit),
        ).fetchall()
    student["history"] = history[::-1]
    return student


def update_consecutive_failures(conn: psycopg.Connection, student_id: str, correct: bool | None) -> int:
    """Reset the counter after a correct answer, add 1 after a wrong one or "?" (correct is None); returns it."""
    row = conn.execute(
        """
        UPDATE students
        SET consecutive_failures = CASE WHEN %s THEN 0 ELSE consecutive_failures + 1 END
        WHERE student_id = %s
        RETURNING consecutive_failures
        """,
        (correct is True, student_id),
    ).fetchone()
    if row is None:
        raise LookupError(f"no student {student_id!r}")
    return row[0]


# Ratings (SPEC 5.6): each value is stored with its own answer count n


def save_student_rating(conn: psycopg.Connection, student_id: str, theta: float, answers_count: int) -> None:
    """Store the student's overall level theta and answer count."""
    cursor = conn.execute(
        "UPDATE students SET rating = %s, answers_count = %s WHERE student_id = %s",
        (theta, answers_count, student_id),
    )
    if cursor.rowcount != 1:
        raise LookupError(f"no student {student_id!r}")


def save_topic_rating(conn: psycopg.Connection, student_id: str, topic: str, offset: float, answers_count: int) -> None:
    """Store the student's offset delta for a topic and its answer count; the row appears with the first answer."""
    conn.execute(
        """
        INSERT INTO student_topic_ratings (student_id, topic, topic_offset, answers_count)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (student_id, topic) DO UPDATE SET
          topic_offset = EXCLUDED.topic_offset,
          answers_count = EXCLUDED.answers_count
        """,
        (student_id, topic, offset, answers_count),
    )


def save_task_rating(conn: psycopg.Connection, task_id: str, beta: float, rating_count: int) -> None:
    """Store a bank task's difficulty beta and answer count."""
    cursor = conn.execute(
        "UPDATE tasks SET rating = %s, rating_count = %s WHERE task_id = %s", (beta, rating_count, task_id)
    )
    if cursor.rowcount != 1:
        raise LookupError(f"no task {task_id!r} in the bank")


# Requests and attempts


def create_request(conn: psycopg.Connection, student_id: str, tutor_mode: str, brief: dict) -> int:
    """Open a request once the brief is known; returns request_id.

    The outcome is unknown yet, but source is NOT NULL: the row says 'failed' until close_request sets the real
    source, so a run that stops half-way is logged as failed.
    """
    if tutor_mode not in TUTOR_MODES:
        raise ValueError(f"tutor_mode must be one of {TUTOR_MODES}, got {tutor_mode!r}")
    return conn.execute(
        """
        INSERT INTO requests (student_id, tutor_mode, brief, source)
        VALUES (%s, %s, %s, 'failed')
        RETURNING request_id
        """,
        (student_id, tutor_mode, Jsonb(brief)),
    ).fetchone()[0]


def close_request(
    conn: psycopg.Connection,
    request_id: int,
    source: str,
    task_id: str | None = None,
    attempt_count: int = 0,
    tokens: int | None = None,
    cost_usd: float | None = None,
    duration_ms: int | None = None,
) -> None:
    """Record where the task came from and the request totals; a 'failed' request has no task."""
    if source not in SOURCES:
        raise ValueError(f"source must be one of {SOURCES}, got {source!r}")
    if (task_id is None) != (source == "failed"):
        raise ValueError(f"a {source!r} request {'must not have' if source == 'failed' else 'needs'} a task_id")
    cursor = conn.execute(
        """
        UPDATE requests
        SET source = %s, task_id = %s, attempt_count = %s, tokens = %s, cost_usd = %s, duration_ms = %s
        WHERE request_id = %s
        """,
        (source, task_id, attempt_count, tokens, cost_usd, duration_ms, request_id),
    )
    if cursor.rowcount != 1:
        raise LookupError(f"no request {request_id}")


def record_attempt(
    conn: psycopg.Connection,
    request_id: int,
    attempt_no: int,
    status: str,
    prompt_version: str,
    *,
    reason: str | None = None,
    generator: dict | None = None,
    analyst: dict | None = None,
    skeptic: dict | None = None,
    solver_result: object = None,
    models: dict | None = None,
    tokens: int | None = None,
    cost_usd: float | None = None,
    duration_ms: int | None = None,
) -> int:
    """Log one generation attempt, rejected ones included; returns attempt_id.

    Reason codes are not checked here: the list in SPEC 6 is still open (bad_structure, fix_changed_task).
    """
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}, got {status!r}")
    if status == "accepted" and reason is not None:
        raise ValueError("an accepted attempt has no rejection reason")

    def json_or_null(value):
        return None if value is None else Jsonb(value)

    return conn.execute(
        """
        INSERT INTO attempts (request_id, attempt_no, status, reason, generator, analyst, skeptic, solver_result,
                              prompt_version, models, tokens, cost_usd, duration_ms)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING attempt_id
        """,
        (
            request_id,
            attempt_no,
            status,
            reason,
            json_or_null(generator),
            json_or_null(analyst),
            json_or_null(skeptic),
            json_or_null(solver_result),
            prompt_version,
            json_or_null(models),
            tokens,
            cost_usd,
            duration_ms,
        ),
    ).fetchone()[0]


# Task bank


def save_task(
    conn: psycopg.Connection,
    *,
    brief: dict,
    task: dict,
    analyst: dict,
    skeptic: dict,
    grade_level: str,
    attempt_count: int,
    rating: float,
) -> str:
    """Put an accepted task into the bank; returns its new task_id.

    Topic, difficulty, setting and excluded skills come from the Methodist brief the task was generated for,
    traps from the Generator's distractors. The starting rating beta is passed in: it is computed in rating.py.
    """
    if grade_level not in ("1-2", "3-4"):
        raise ValueError(f"grade_level must be '1-2' or '3-4', got {grade_level!r}")
    task_id = f"t-{uuid4().hex[:12]}"
    traps = sorted({distractor["trap"] for distractor in task["distractors"].values()})
    conn.execute(
        """
        INSERT INTO tasks (task_id, topic, difficulty, grade_level, setting, excluded_skills, traps,
                           brief, task, analyst, skeptic, attempt_count, rating)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            task_id,
            brief["target_concept"],
            brief["difficulty"],
            grade_level,
            brief.get("setting"),
            brief["excluded_skills"],
            traps,
            Jsonb(brief),
            Jsonb(task),
            Jsonb(analyst),
            Jsonb(skeptic),
            attempt_count,
            rating,
        ),
    )
    return task_id


def bank_candidates(
    conn: psycopg.Connection,
    student: dict,
    topic: str,
    beta_range: tuple[float, float],
    setting: str | None = None,
    traps_to_use: list[str] | tuple[str, ...] = (),
) -> list[dict]:
    """Bank tasks that fit the brief under the SPEC 5.5 conditions, best first; an empty list means generate.

    student is a load_student() result; beta_range is the student's corridor for the topic, bounds included.
    """
    beta_min, beta_max = beta_range
    with conn.cursor(row_factory=dict_row) as cursor:
        candidates = cursor.execute(
            """
            SELECT t.*
            FROM tasks t
            WHERE t.topic = %(topic)s
              AND t.rating BETWEEN %(beta_min)s AND %(beta_max)s
              AND t.grade_level = %(grade_level)s
              AND t.excluded_skills @> %(excluded_skills)s::text[]
              AND NOT EXISTS (
                SELECT 1 FROM student_tasks s WHERE s.student_id = %(student_id)s AND s.task_id = t.task_id
              )
            """,
            {
                "topic": topic,
                "beta_min": beta_min,
                "beta_max": beta_max,
                "grade_level": grade_level(student["grade"]),
                "excluded_skills": student["excluded_skills"],
                "student_id": student["student_id"],
            },
        ).fetchall()
    return rank_candidates(candidates, setting, traps_to_use)


def rank_candidates(candidates: list[dict], setting: str | None, traps_to_use) -> list[dict]:
    """Same setting as the brief first, then more traps shared with traps_to_use (SPEC 5.5).

    Ties go to the older task, then to task_id, so the choice is repeatable.
    """
    wanted = set(traps_to_use)
    return sorted(
        candidates,
        key=lambda row: (
            not (setting is not None and row["setting"] == setting),
            -len(wanted & set(row["traps"])),
            row["created_at"],
            row["task_id"],
        ),
    )


def similar_tasks(conn: psycopg.Connection, question: str, min_similarity: float, limit: int = 5) -> list[dict]:
    """Bank tasks whose question has pg_trgm similarity >= min_similarity, most similar first (SPEC 6)."""
    with conn.cursor(row_factory=dict_row) as cursor:
        # The % operator uses the trigram index; its threshold is set for this transaction only.
        cursor.execute("SELECT set_config('pg_trgm.similarity_threshold', %s, true)", (str(min_similarity),))
        return cursor.execute(
            """
            SELECT task_id, task ->> 'question' AS question, similarity(task ->> 'question', %(question)s) AS similarity
            FROM tasks
            WHERE (task ->> 'question') %% %(question)s
              AND similarity(task ->> 'question', %(question)s) >= %(min_similarity)s
            ORDER BY similarity DESC, task_id
            LIMIT %(limit)s
            """,
            {"question": question, "min_similarity": min_similarity, "limit": limit},
        ).fetchall()


def similarities(conn: psycopg.Connection, question: str, texts: list[str]) -> list[float]:
    """pg_trgm similarity of the question to each text, in order: for texts outside the bank, like the examples."""
    rows = conn.execute(
        """
        SELECT similarity(%s, text)
        FROM unnest(%s::text[]) WITH ORDINALITY AS given(text, position)
        ORDER BY position
        """,
        (question, list(texts)),
    ).fetchall()
    return [row[0] for row in rows]


# Issued tasks and answers


def issue_task(conn: psycopg.Connection, student_id: str, task_id: str) -> int:
    """Give a bank task to a student; returns the student_tasks row id.

    The UNIQUE (student_id, task_id) constraint raises psycopg.errors.UniqueViolation on a second issue:
    a student never gets the same task twice (SPEC 5.5).
    """
    row = conn.execute(
        """
        INSERT INTO student_tasks (student_id, task_id, topic, difficulty)
        SELECT %s, task_id, topic, difficulty FROM tasks WHERE task_id = %s
        RETURNING id
        """,
        (student_id, task_id),
    ).fetchone()
    if row is None:
        raise LookupError(f"no task {task_id!r} in the bank")
    return row[0]


def save_answer(
    conn: psycopg.Connection,
    student_task_id: int,
    *,
    correct: bool | None,
    chosen_option: str | None = None,
    trap_hit: str | None = None,
    feedback: str | None = None,
    hint_used: bool = False,
    pace: str | None = None,
) -> None:
    """Store the student's answer in the issued-task row; correct is None for "?" (SPEC 3, --answer mode)."""
    if chosen_option is not None and chosen_option not in OPTIONS:
        raise ValueError(f"chosen_option must be one of {OPTIONS}, got {chosen_option!r}")
    if pace is not None and pace not in PACES:
        raise ValueError(f"pace must be one of {PACES}, got {pace!r}")
    cursor = conn.execute(
        """
        UPDATE student_tasks
        SET correct = %s, chosen_option = %s, trap_hit = %s, feedback = %s, hint_used = %s, pace = %s
        WHERE id = %s
        """,
        (correct, chosen_option, trap_hit, feedback, hint_used, pace, student_task_id),
    )
    if cursor.rowcount != 1:
        raise LookupError(f"no issued task {student_task_id}")
