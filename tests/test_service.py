"""service.py (T19): the profile and progress tools on the test database from conftest.py, and prompt_version."""

import json

import pytest

from taskgen import service
from taskgen.rating import corridor, load_params
from taskgen.seed import SEED_DIR, seed_student

PARAMS = load_params()


def seed(conn, name):
    seed_student(conn, json.loads((SEED_DIR / f"{name}.json").read_text(encoding="utf-8")), PARAMS)


def by_topic(rows):
    return {row["topic"]: row for row in rows}


# get_student_profile


def test_profile_of_masha(conn):
    seed(conn, "masha")
    profile = service.student_profile(conn, "masha", PARAMS)

    assert (profile["student_id"], profile["grade"], profile["grade_level"]) == ("masha", 3, "3-4")
    assert profile["consecutive_failures"] == 2
    assert profile["cognitive_profile"]  # the coach needs it; progress() leaves it out
    assert len(profile["topics"]) == 10  # grade 3 gets every catalog topic
    assert profile["overall"]["answers"] == 3

    clocks = by_topic(profile["topics"])["time.clocks"]
    assert clocks["answers"] == 1
    fit = corridor(clocks["level"], PARAMS.corridor)
    assert (clocks["recommended_difficulty"], clocks["corridor_fit"]) == (fit.recommended, fit.fit)
    assert 0.2 < clocks["success_chance"] < 1

    assert [row["result"] for row in profile["recent_history"]] == ["correct", "wrong", "did not understand"]
    assert profile["recent_history"][1]["trap_hit"] == "missed_case"
    assert all(len(row["date"]) == 10 for row in profile["recent_history"])
    json.dumps(profile)  # the tool result must be plain JSON


def test_first_grader_sees_only_the_topics_of_grades_1_2(conn):
    seed(conn, "dima")
    topics = by_topic(service.student_profile(conn, "dima", PARAMS)["topics"])
    assert len(topics) == 8
    assert "logic.knights_liars" not in topics and "algorithms.weighing_pouring" not in topics


def test_new_student_starts_at_1500(conn):
    seed(conn, "sasha")
    profile = service.student_profile(conn, "sasha", PARAMS)
    assert profile["overall"] == {"level": 0.0, "rating": 1500, "answers": 0}
    assert profile["recent_history"] == []
    assert {row["recommended_difficulty"] for row in profile["topics"]} == {2}


def test_unknown_student_lists_the_known_ones(conn):
    seed(conn, "masha")
    with pytest.raises(service.StudentNotFound, match="masha"):
        service.student_profile(conn, "nobody", PARAMS)


# get_progress


def test_progress_of_masha(conn):
    seed(conn, "masha")
    summary = service.progress(conn, "masha", PARAMS)

    assert "cognitive_profile" not in summary  # sensitive notes are not for the child
    assert summary["answers"] == 3 and summary["failures_in_a_row"] == 2
    assert summary["mastered_topics"] == ["Knights and liars"]
    assert set(by_topic(summary["topics"])) == {"logic.knights_liars", "combinatorics.enumeration", "time.clocks"}
    assert [row["result"] for row in summary["recent_answers"]] == ["correct", "wrong", "did not understand"]
    assert summary["recent_answers"][0]["topic"] == "Knights and liars"
    json.dumps(summary)


def test_progress_of_a_new_student(conn):
    seed(conn, "sasha")
    summary = service.progress(conn, "sasha", PARAMS)
    assert (summary["overall_rating"], summary["topics"], summary["recent_answers"]) == (1500, [], [])


def test_unanswered_task_is_not_a_failure():
    assert service.answer_result({"correct": None, "feedback": None}) == "not answered"
    assert service.answer_result({"correct": None, "feedback": "didn't understand the question"}) == \
        "did not understand"


# Instructions and prompt_version


def test_instructions_name_the_tools():
    text = service.instructions()
    assert "get_student_profile" in text and "get_progress" in text


def test_prompt_version(tmp_path):
    first, second = tmp_path / "a.md", tmp_path / "b.md"
    first.write_text("Be kind.", encoding="utf-8")
    second.write_text("Be brief.", encoding="utf-8")
    version = service.prompt_version((first, second))
    assert len(version) == 12 and int(version, 16) >= 0
    assert service.prompt_version((second, first)) == version  # order does not matter
    first.write_text("Be kind!", encoding="utf-8")
    assert service.prompt_version((first, second)) != version
    assert len(service.prompt_version()) == 12  # the real instructions file
