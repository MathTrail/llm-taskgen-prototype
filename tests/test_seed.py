"""Seed profile checks: the five starting profiles are valid and broken profiles are rejected (T09);
seeding writes the ratings replayed from the starting history (T13, on the test database from conftest.py)."""

import copy
import json

import pytest

from taskgen.db import load_student
from taskgen.rating import load_params, replay_history
from taskgen.seed import SEED_DIR, profile_errors, seed_student

PATHS = sorted(SEED_DIR.glob("*.json"))


def load(name):
    return json.loads((SEED_DIR / f"{name}.json").read_text(encoding="utf-8"))


def errors_after(change, name="masha"):
    profile = copy.deepcopy(load(name))
    change(profile)
    return profile_errors(profile, name)


def test_seed_writes_ratings_replayed_from_history(conn):
    profile = load("olya")  # three topics, one of them answered three times
    params = load_params()
    seed_student(conn, profile, params)

    student = load_student(conn, "olya")
    expected = replay_history(profile["history"], params)
    assert student["rating"] == pytest.approx(expected.theta, abs=1e-6)
    assert student["answers_count"] == len(profile["history"])
    assert {topic: (row["offset"], row["answers_count"]) for topic, row in student["topic_ratings"].items()} == {
        topic: (pytest.approx(offset, abs=1e-6), answers) for topic, (offset, answers) in expected.topics.items()
    }


def test_reseeding_resets_ratings(conn):
    profile = load("masha")
    first = seed_student(conn, profile)
    conn.execute("UPDATE students SET rating = 3 WHERE student_id = 'masha'")
    seed_student(conn, profile)
    assert load_student(conn, "masha")["rating"] == pytest.approx(first.theta, abs=1e-6)


def test_new_student_keeps_zero_ratings(conn):
    seed_student(conn, load("sasha"))  # empty history
    student = load_student(conn, "sasha")
    assert (student["rating"], student["answers_count"], student["topic_ratings"]) == (0, 0, {})


@pytest.mark.parametrize("path", PATHS, ids=lambda path: path.stem)
def test_profile_is_valid(path):
    assert profile_errors(json.loads(path.read_text(encoding="utf-8")), path.stem) == []


def test_five_profiles_cover_the_cases():
    profiles = [json.loads(path.read_text(encoding="utf-8")) for path in PATHS]
    assert len(profiles) == 5
    assert any(profile["history"] == [] for profile in profiles)  # new student
    assert any(profile["grade"] == 1 for profile in profiles)  # first-grader
    assert any(profile["consecutive_failures"] >= 2 for profile in profiles)  # series of failures
    assert any(len(profile["mastered_topics"]) == 1 for profile in profiles)  # one topic mastered


def test_task_id_in_history_is_rejected():  # remark 03-1: starting history has no task_id
    assert errors_after(lambda profile: profile["history"][0].update(task_id="t-0012"))


def test_unknown_history_topic_is_rejected():
    errors = errors_after(lambda profile: profile["history"][0].update(topic="patterns.sequences"))
    assert any("patterns.sequences" in error for error in errors)


def test_unknown_mastered_topic_is_rejected():
    errors = errors_after(lambda profile: profile["mastered_topics"].append("geometry.cubes"))
    assert any("geometry.cubes" in error for error in errors)


def test_unknown_skill_is_rejected():
    errors = errors_after(lambda profile: profile["excluded_skills"].append("simple_fractions"))
    assert any("simple_fractions" in error for error in errors)


def test_unknown_trap_is_rejected():
    errors = errors_after(lambda profile: profile["history"][1].update(trap_hit="forgot_a_case"))
    assert any("forgot_a_case" in error for error in errors)


def test_wrong_answer_without_chosen_option_is_rejected():
    assert errors_after(lambda profile: profile["history"][1].pop("chosen_option"))


def test_correct_answer_with_trap_is_rejected():
    assert errors_after(lambda profile: profile["history"][0].update(trap_hit="off_by_one"))


def test_consecutive_failures_must_match_history():
    errors = errors_after(lambda profile: profile.update(consecutive_failures=1))
    assert any("consecutive_failures" in error for error in errors)


def test_id_must_match_file_name():
    errors = profile_errors(load("masha"), "petya")
    assert any("file name" in error for error in errors)


def test_grade_outside_1_to_4_is_rejected():
    assert errors_after(lambda profile: profile.update(grade=5))
