"""Loads or resets starting student profiles from data/seed/*.json (SPEC 4.1).

Every run resets the chosen students to their starting state: history and topic ratings are deleted and written
again from the JSON file, so rerunning never duplicates data. Request and attempt logs are kept.
Ratings come from replaying the starting history through rating.py: theta and the per-topic offsets delta (SPEC 5.6).

Run: uv run python -m taskgen.seed [--student masha]
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
from jsonschema import Draft202012Validator

from taskgen import ROOT
from taskgen.catalogs import load_catalog
from taskgen.db import database_url, save_student_rating, save_topic_rating
from taskgen.rating import Params, Ratings, corridor, elo, load_params, replay_history

SEED_DIR = ROOT / "data" / "seed"
PROFILE_SCHEMA = json.loads((ROOT / "schemas" / "profile.json").read_text(encoding="utf-8"))


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
            errors.append(f"{field}: unknown ids {unknown}, not in data/catalogs/{catalog}.json")

    expected = trailing_failures(history)
    if profile["consecutive_failures"] != expected:
        errors.append(
            f"consecutive_failures is {profile['consecutive_failures']}, "
            f"but the history ends with {expected} failures in a row"
        )
    return errors


def seed_student(conn: psycopg.Connection, profile: dict, params: Params | None = None) -> Ratings:
    """Write the profile, its starting history and the ratings replayed from it, replacing whatever the student had."""
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

    ratings = replay_history(history, params or load_params())
    save_student_rating(conn, student_id, ratings.theta, ratings.answers)
    for topic, (offset, answers) in ratings.topics.items():
        save_topic_rating(conn, student_id, topic, offset, answers)
    return ratings


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
    parser = argparse.ArgumentParser(description="Load or reset starting student profiles from data/seed/*.json.")
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

    params = load_params()
    with psycopg.connect(database_url()) as conn:
        for profile in profiles:
            ratings = seed_student(conn, profile, params)
            print(
                f"{profile['id']}: grade {profile['grade']}, {len(profile['history'])} history rows, "
                f"theta {ratings.theta:+.3f} (R {elo(ratings.theta):.0f})"
            )
            for topic, (offset, answers) in sorted(ratings.topics.items()):
                level = ratings.theta + offset
                fit = corridor(level, params.corridor)
                print(
                    f"  {topic}: delta {offset:+.3f} after {answers} answers, level {level:+.3f} "
                    f"(R {elo(level):.0f}), recommended difficulty {fit.recommended} ({fit.fit})"
                )


if __name__ == "__main__":
    main()
