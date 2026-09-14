"""Loads or resets starting student profiles from db/seed/*.json (SPEC 4.1).

Every run resets the chosen students to their starting state: history and topic ratings are deleted and written
again from the JSON file, so rerunning never duplicates data. Request and attempt logs are kept.
Ratings are not computed yet (T13): theta stays 0 and there are no per-topic offsets.

Run: uv run python seed.py [--student masha]
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
from jsonschema import Draft202012Validator

from scripts.validate_catalogs import load_catalog

ROOT = Path(__file__).resolve().parent
SEED_DIR = ROOT / "db" / "seed"
PROFILE_SCHEMA = json.loads((ROOT / "schemas" / "profile.json").read_text(encoding="utf-8"))


def database_url() -> str:
    """DATABASE_URL from the environment, otherwise from the .env file (same lookup as db/apply_schema.py)."""
    if url := os.environ.get("DATABASE_URL"):
        return url
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == "DATABASE_URL" and value.strip():
                return value.strip().strip("\"'")
    sys.exit("DATABASE_URL is not set: copy .env.example to .env")


def trailing_failures(history: list[dict]) -> int:
    """Failures in a row at the end of the history; a wrong answer and "didn't understand" both count."""
    count = 0
    for row in reversed(history):
        if row["correct"] is True:
            break
        count += 1
    return count


def profile_errors(profile: object, stem: str) -> list[str]:
    """Schema violations, unknown catalog ids and inconsistencies; an empty list means the profile is valid."""
    errors = [
        f"{'/'.join(map(str, error.absolute_path)) or '(root)'}: {error.message}"
        for error in Draft202012Validator(PROFILE_SCHEMA).iter_errors(profile)
    ]
    if errors:
        return errors

    if profile["id"] != stem:
        errors.append(f"id {profile['id']!r} does not match the file name {stem}.json")

    history = profile["history"]
    references = [
        ("mastered_topics", profile["mastered_topics"], "topics"),
        ("history topic", [row["topic"] for row in history], "topics"),
        ("excluded_skills", profile["excluded_skills"], "skills"),
        ("history trap_hit", [row["trap_hit"] for row in history if "trap_hit" in row], "traps"),
    ]
    for field, values, catalog in references:
        known = {entry["id"] for entry in load_catalog(catalog)}
        if unknown := sorted(set(values) - known):
            errors.append(f"{field}: unknown ids {unknown}, not in catalogs/{catalog}.json")

    expected = trailing_failures(history)
    if profile["consecutive_failures"] != expected:
        errors.append(
            f"consecutive_failures is {profile['consecutive_failures']}, "
            f"but the history ends with {expected} failures in a row"
        )
    return errors


def seed_student(conn: psycopg.Connection, profile: dict) -> None:
    """Write the profile and its starting history, replacing whatever the student had."""
    student_id = profile["id"]
    conn.execute(
        """
        INSERT INTO students (student_id, grade, interests, cognitive_profile, mastered_topics,
                              excluded_skills, consecutive_failures, rating, answers_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 0, 0)
        ON CONFLICT (student_id) DO UPDATE SET
          grade = EXCLUDED.grade,
          interests = EXCLUDED.interests,
          cognitive_profile = EXCLUDED.cognitive_profile,
          mastered_topics = EXCLUDED.mastered_topics,
          excluded_skills = EXCLUDED.excluded_skills,
          consecutive_failures = EXCLUDED.consecutive_failures,
          rating = 0,
          answers_count = 0
        """,
        (
            student_id,
            profile["grade"],
            profile["interests"],
            profile["cognitive_profile"],
            profile["mastered_topics"],
            profile["excluded_skills"],
            profile["consecutive_failures"],
        ),
    )
    conn.execute("DELETE FROM student_tasks WHERE student_id = %s", (student_id,))
    conn.execute("DELETE FROM student_topic_ratings WHERE student_id = %s", (student_id,))

    # The history is oldest first; one day between rows keeps issued_at ordered and in the past.
    history = profile["history"]
    now = datetime.now(timezone.utc)
    rows = [
        (
            student_id,
            row["topic"],
            row["difficulty"],
            now - timedelta(days=len(history) - index),
            row["correct"],
            row.get("chosen_option"),
            row.get("trap_hit"),
            row.get("feedback"),
            row.get("hint_used", False),
            row.get("pace"),
        )
        for index, row in enumerate(history)
    ]
    if rows:
        with conn.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO student_tasks (student_id, topic, difficulty, issued_at, correct,
                                           chosen_option, trap_hit, feedback, hint_used, pace)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                rows,
            )


def seed_paths(student: str | None) -> list[Path]:
    if student:
        path = SEED_DIR / f"{student}.json"
        if not path.exists():
            sys.exit(f"No starting profile {path.relative_to(ROOT)}")
        return [path]
    paths = sorted(SEED_DIR.glob("*.json"))
    if not paths:
        sys.exit(f"No starting profiles in {SEED_DIR.relative_to(ROOT)}")
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Load or reset starting student profiles from db/seed/*.json.")
    parser.add_argument("--student", help="reset only this student, e.g. masha; default: every profile")
    args = parser.parse_args()

    # Validate every profile before touching the database, so a typo never leaves a half-seeded state.
    profiles, failed = [], False
    for path in seed_paths(args.student):
        name = path.relative_to(ROOT)
        try:
            profile = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            print(f"{name}: invalid JSON: {error}")
            failed = True
            continue
        for error in profile_errors(profile, path.stem):
            print(f"{name}: {error}")
            failed = True
        profiles.append(profile)
    if failed:
        sys.exit(1)

    with psycopg.connect(database_url()) as conn:
        for profile in profiles:
            seed_student(conn, profile)
            print(f"{profile['id']}: grade {profile['grade']}, {len(profile['history'])} history rows")


if __name__ == "__main__":
    main()
