"""Live-run journal (T23): a readiness check, the log of requests, attempts and answers, and the tasks to review.

  uv run python -m taskgen.journal check    # before a live run: schema, students, sandbox, server instructions
  uv run python -m taskgen.journal log      # what happened: requests, attempts, answers, a short summary
  uv run python -m taskgen.journal tasks    # the tasks the model wrote, in full, for the manual review
log and tasks take --student masha and --hours 24 (the default window).
"""

import argparse
import sys
from collections import Counter

import psycopg
from psycopg.rows import dict_row

from taskgen import sandbox, service
from taskgen.db import database_url

WINDOW_SQL = "created_at > now() - make_interval(hours => %(hours)s) AND (%(student)s::text IS NULL OR student_id = %(student)s)"


# check


def check(conn: psycopg.Connection) -> list[tuple[str, bool, str]]:
    """(name, ok, detail) for everything a live run needs."""
    has_language = conn.execute(
        "SELECT count(*) FROM information_schema.columns WHERE table_name = 'tasks' AND column_name = 'language'"
    ).fetchone()[0] == 1
    students = [row[0] for row in conn.execute("SELECT student_id FROM students ORDER BY student_id")]
    bank = conn.execute("SELECT count(*) FROM tasks").fetchone()[0]
    return [
        ("schema", has_language, "up to date" if has_language else
         "old schema: run uv run python -m taskgen.apply_schema --force, then uv run python -m taskgen.seed"),
        ("students", len(students) >= 5, ", ".join(students) or "none: run uv run python -m taskgen.seed"),
        ("bank", True, f"{bank} tasks"),
        sandbox_check(),
        ("instructions", True, f"prompt_version {service.prompt_version()}"),
    ]  # fmt: skip


def sandbox_check() -> tuple[str, bool, str]:
    limits = sandbox.load_limits()
    try:
        sandbox.ensure_image(limits.image)  # pulls the image once if it is missing
    except sandbox.SandboxUnavailable as error:
        return ("sandbox", False, f"{error}; is Docker running?")
    return ("sandbox", True, limits.image.split("@")[0])


# log


def answer_text(row: dict | None) -> str:
    text = "not answered" if row is None else service.answer_result(row)
    if text == "not answered":
        return text
    if text == "wrong":
        text += f" ({row['chosen_option']}, trap {row['trap_hit']})"
    return f"{text}{', hint' if row['hint_used'] else ''}, pace {row['pace']}"


def log_lines(conn: psycopg.Connection, student: str | None = None, hours: float = 24) -> list[str]:
    """One block per request, oldest first, and a summary."""
    window = {"hours": hours, "student": student}
    with conn.cursor(row_factory=dict_row) as cursor:
        requests = cursor.execute(f"SELECT * FROM requests WHERE {WINDOW_SQL} ORDER BY created_at, request_id",
                                  window).fetchall()  # fmt: skip
        ids = [request["request_id"] for request in requests]
        attempts = cursor.execute(
            "SELECT * FROM attempts WHERE request_id = ANY(%s) ORDER BY request_id, attempt_no", (ids,)
        ).fetchall()
        answers = cursor.execute(
            "SELECT * FROM student_tasks WHERE task_id = ANY(%s)", ([r["task_id"] for r in requests if r["task_id"]],)
        ).fetchall()
    by_request: dict[int, list[dict]] = {}
    for attempt in attempts:
        by_request.setdefault(attempt["request_id"], []).append(attempt)
    answer_of = {(row["student_id"], row["task_id"]): row for row in answers}

    lines = []
    for request in requests:
        brief = request["brief"]
        outcome = {
            "bank": f"from the bank: {request['task_id']}",
            "generated": f"generated {request['task_id']} in {request['attempt_count']} attempt(s)",
            "failed": ("abandoned: no task handed in" if request["attempt_count"] == 0 else
                       f"failed after {request['attempt_count']} attempt(s)"),
        }[request["source"]]  # fmt: skip
        seconds = f", {request['duration_ms'] / 1000:.0f} s" if request["duration_ms"] is not None else ""
        lines.append(f"#{request['request_id']} {request['created_at']:%H:%M} {request['student_id']} "
                     f"[{request['tutor_mode']}] {brief['target_concept']} d{brief['difficulty']} "
                     f"{brief['pedagogical_goal']} -> {outcome}{seconds}")  # fmt: skip
        for attempt in by_request.get(request["request_id"], []):
            reason = f": {attempt['reason']}" if attempt["reason"] else ""
            lines.append(f"    attempt {attempt['attempt_no']} {attempt['status']}{reason}")
        if request["task_id"]:
            lines.append(f"    answer: {answer_text(answer_of.get((request['student_id'], request['task_id'])))}")
    return lines + [""] + summary_lines(requests, attempts, answer_of.values())


def summary_lines(requests: list[dict], attempts: list[dict], answers) -> list[str]:
    sources = Counter(request["source"] for request in requests)
    abandoned = sum(1 for r in requests if r["source"] == "failed" and r["attempt_count"] == 0)
    generated = [request for request in requests if request["source"] == "generated"]
    first_try = sum(1 for request in generated if request["attempt_count"] == 1)
    reasons = Counter(attempt["reason"] for attempt in attempts if attempt["reason"])
    results = Counter(service.answer_result(row) for row in answers)
    return [
        f"requests: {len(requests)} (generated {sources['generated']}, bank {sources['bank']}, "
        f"failed {sources['failed']}, of them abandoned {abandoned})",
        f"accepted on the first attempt: {first_try} of {len(generated)} generated",
        "rejections: " + (", ".join(f"{reason} {count}" for reason, count in reasons.most_common()) or "none"),
        "answers: " + (", ".join(f"{result} {count}" for result, count in sorted(results.items())) or "none"),
    ]  # fmt: skip


# tasks


def tasks_lines(conn: psycopg.Connection, student: str | None = None, hours: float = 24) -> list[str]:
    """Every task the model wrote in the window, in full, for the manual review (SPEC 9)."""
    window = {"hours": hours, "student": student}
    with conn.cursor(row_factory=dict_row) as cursor:
        rows = cursor.execute(
            f"""
            SELECT r.request_id, r.student_id, t.*
            FROM (SELECT * FROM requests WHERE {WINDOW_SQL}) r
            JOIN tasks t ON t.task_id = r.task_id
            WHERE r.source = 'generated'
            ORDER BY r.created_at
            """,
            window,
        ).fetchall()
    lines = []
    for row in rows:
        task = row["task"]
        lines.append(f"{row['task_id']}  {row['topic']} d{row['difficulty']}  grades {row['grade_level']}  "
                     f"{row['language']}  for {row['student_id']}  ({row['attempt_count']} attempt(s), "
                     f"request #{row['request_id']})")  # fmt: skip
        lines.append(f"  Q: {task['question']}")
        for letter, option in task["options"].items():
            if letter == task["correct_answer"]:
                lines.append(f"  * {letter}) {option}   <- correct")
            else:
                trap = task["distractors"].get(letter, {})
                lines.append(f"    {letter}) {option}   [{trap.get('trap')}: {trap.get('text')}]")
        lines.append(f"  Hint: {task['hint']}")
        lines.append(f"  Solution: {task['solution']}")
        minor = [issue["comment"] for issue in (row["skeptic"] or {}).get("issues", []) if issue["severity"] == "minor"]
        if minor:
            lines.append(f"  Self-check notes: {'; '.join(minor)}")
        lines.append("")
    return lines or ["no tasks written by the model in this window"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Readiness check and journal of a live run in Claude Code.")
    parser.add_argument("command", choices=["check", "log", "tasks"])
    parser.add_argument("--student", help="only this student, e.g. masha")
    parser.add_argument("--hours", type=float, default=24, help="how far back to look (default 24)")
    args = parser.parse_args()

    try:
        conn = psycopg.connect(database_url(), connect_timeout=5)
    except psycopg.OperationalError as error:
        sys.exit(f"FAIL  database  {error.args[0].splitlines()[0]}; start it: docker compose up -d --wait")
    with conn:
        if args.command == "check":
            results = check(conn)
            for name, ok, detail in results:
                print(f"{'OK  ' if ok else 'FAIL'}  {name:<12} {detail}")
            if not all(ok for _, ok, _ in results):
                sys.exit(1)
        elif args.command == "log":
            print("\n".join(log_lines(conn, args.student, args.hours)))
        else:
            print("\n".join(tasks_lines(conn, args.student, args.hours)))


if __name__ == "__main__":
    main()
