"""Rule-based tutor: the baseline for the LLM Methodist (SPEC 5.7, D40).

From the whole history it builds a brief in the format of schemas/brief.json, always the same for the same input:
- after a failure (consecutive_failures > 0): goal reinforce, the topic of the last history row;
- otherwise: goal new_topic, the unmastered topic of the student's grade level given longest ago,
  topics never given first, in catalog order;
- difficulty: the recommended one for the topic (rating.corridor);
- setting: the student's interests in turn, by the number of history rows;
- traps: the student's most frequent trap_hit in the topic, topped up with the most frequent traps of the reference
  examples of this topic and grade level, TRAP_COUNT in all.

Show the briefs of students in the database: uv run python -m taskgen.tutor_rule [--student masha]
"""

import argparse
import json
import sys
from collections import Counter
from functools import lru_cache

import psycopg

from taskgen.catalogs import load_catalog
from taskgen.db import database_url, grade_level, list_students, load_student
from taskgen.rating import Params, corridor, load_params
from taskgen.validate_examples import load_examples

TRAP_COUNT = 2
FIT_TEXT = {
    "inside": "inside the corridor",
    "too_hard": "the closest to the corridor, which holds no level; a little too hard",
    "too_easy": "the closest to the corridor, which holds no level; a little too easy",
}


@lru_cache(maxsize=None)
def example_traps(topic: str, level: str) -> tuple[str, ...]:
    """Traps of the reference examples of a topic and grade level, most frequent first, ties by id."""
    counts = Counter(
        distractor["trap"]
        for task in load_examples()
        if task["topic"] == topic and task["grade_level"] == level
        for distractor in task["distractors"].values()
    )
    return tuple(trap for trap, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def student_traps(history: list[dict], topic: str) -> list[str]:
    """The student's trap_hit in the topic, most frequent first, ties to the more recent."""
    counts, last_seen = Counter(), {}
    for position, row in enumerate(history):
        if row["topic"] == topic and row.get("trap_hit"):
            counts[row["trap_hit"]] += 1
            last_seen[row["trap_hit"]] = position
    return sorted(counts, key=lambda trap: (-counts[trap], -last_seen[trap]))


def choose_topic(student: dict, topics: list[dict]) -> tuple[str, str, str]:
    """(topic, goal, reason in words) for the student."""
    history = student["history"]
    if student["consecutive_failures"] > 0 and history:
        topic = history[-1]["topic"]
        failures = student["consecutive_failures"]
        streak = "a failure" if failures == 1 else f"{failures} failures in a row"
        return topic, "reinforce", f"{streak}, the last one in {topic}"

    level = grade_level(student["grade"])
    available = [entry["id"] for entry in topics if level in entry["grade_levels"]]
    candidates = [topic for topic in available if topic not in student["mastered_topics"]] or available
    last_given = {row["topic"]: position for position, row in enumerate(history)}
    topic = min(candidates, key=lambda topic: (last_given.get(topic, -1), available.index(topic)))
    when = "never given yet" if topic not in last_given else "given longest ago"
    return topic, "new_topic", f"no failure now; {topic} is the unmastered topic {when}"


def make_brief(student: dict, params: Params, topics: list[dict] | None = None) -> dict:
    """A brief for the student; student is a db.load_student() result with the whole history (history_limit=None)."""
    topics = load_catalog("topics") if topics is None else topics
    topic, goal, reason = choose_topic(student, topics)

    offset = student["topic_ratings"].get(topic, {"offset": 0.0})["offset"]
    fit = corridor(student["rating"] + offset, params.corridor)

    traps = student_traps(student["history"], topic)[:TRAP_COUNT]
    for trap in example_traps(topic, grade_level(student["grade"])):
        if len(traps) == TRAP_COUNT:
            break
        if trap not in traps:
            traps.append(trap)

    interests = student["interests"]
    if not interests:
        raise ValueError(f"student {student['student_id']!r} has no interests to take a setting from")
    setting = interests[len(student["history"]) % len(interests)]

    used = ["grade", "interests", "excluded_skills", "consecutive_failures", "history"]
    if goal == "new_topic":
        used.insert(2, "mastered_topics")
    return {
        "rationale": f"Rule: {reason}, so {goal}. Difficulty {fit.recommended} is {FIT_TEXT[fit.fit]}.",
        "pedagogical_goal": goal,
        "target_concept": topic,
        "difficulty": fit.recommended,
        "setting": setting,
        "traps_to_use": traps,
        "constraints": [],
        "excluded_skills": list(student["excluded_skills"]),
        "profile_fields_used": used,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Print the rule tutor's brief for students in the database.")
    parser.add_argument("--student", help="only this student, e.g. masha; default: every student")
    args = parser.parse_args()

    params = load_params()
    with psycopg.connect(database_url()) as conn:
        student_ids = [args.student] if args.student else list_students(conn)
        if not student_ids:
            sys.exit("No students in the database: run uv run python -m taskgen.seed")
        for student_id in student_ids:
            student = load_student(conn, student_id, history_limit=None)
            if student is None:
                sys.exit(f"No student {student_id!r} in the database: run uv run python -m taskgen.seed")
            print(f"{student_id}, grade {student['grade']}, {len(student['history'])} history rows:")
            print(json.dumps(make_brief(student, params), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
