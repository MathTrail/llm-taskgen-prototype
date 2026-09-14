"""Seed profile checks for T09: the five starting profiles are valid and broken profiles are rejected."""

import copy
import json

import pytest

from seed import SEED_DIR, profile_errors

PATHS = sorted(SEED_DIR.glob("*.json"))


def load(name):
    return json.loads((SEED_DIR / f"{name}.json").read_text(encoding="utf-8"))


def errors_after(change, name="masha"):
    profile = copy.deepcopy(load(name))
    change(profile)
    return profile_errors(profile, name)


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
