"""service.py (T19, T20): profile, progress and next-task tools on the test database from conftest.py."""

import json

import pytest
from jsonschema import Draft202012Validator

from taskgen import ROOT, db, service
from taskgen.catalogs import load_catalog
from taskgen.rating import corridor, load_params
from taskgen.seed import SEED_DIR, seed_student

PARAMS = load_params()
BRIEF_SCHEMA = json.loads((ROOT / "schemas" / "brief.json").read_text(encoding="utf-8"))


def seed(conn, name):
    seed_student(conn, json.loads((SEED_DIR / f"{name}.json").read_text(encoding="utf-8")), PARAMS)


def by_topic(rows):
    return {row["topic"]: row for row in rows}


def bank_task(conn, *, topic="logic.ordering", difficulty=2, rating=-1.0, language="en",
              question="Five children stand in a row. Who stands in the middle?"):
    """A task in the bank that fits sasha (grade 4, new student): the rule gives her logic.ordering at difficulty 2."""
    brief = {
        "rationale": "Test.", "pedagogical_goal": "new_topic", "target_concept": topic, "difficulty": difficulty,
        "setting": "music", "traps_to_use": ["reversed_relation", "ignored_condition"], "constraints": [],
        "excluded_skills": [], "profile_fields_used": ["history"],
    }  # fmt: skip
    task = {
        "core_idea": "Middle of five.", "design_thought_process": "Plot: a concert.", "question": question,
        "options": {"A": "Ann", "B": "Ben", "C": "Kim", "D": "Dan", "E": "Eva"}, "correct_answer": "C",
        "solution": "Kim is third of five.", "hint": "Who is first?",
        "distractors": {letter: {"trap": "reversed_relation", "text": "Count again."} for letter in "ABDE"},
    }  # fmt: skip
    return db.save_task(conn, brief=brief, task=task, analyst={"solver_code": "print('[\"C\"]')"},
                        skeptic={"issues": [], "final_answer": "C"}, grade_level="3-4", attempt_count=1,
                        rating=rating, language=language)  # fmt: skip


def request_row(conn, request_id):
    return conn.execute(
        "SELECT tutor_mode, source, task_id FROM requests WHERE request_id = %s", (request_id,)
    ).fetchone()


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

    recommendation = profile["recommendation"]  # the rule's brief (SPEC 5.1, D43)
    assert list(Draft202012Validator(BRIEF_SCHEMA).iter_errors(recommendation)) == []
    assert (recommendation["pedagogical_goal"], recommendation["target_concept"]) == ("reinforce", "time.clocks")

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


# get_next_task


def test_empty_bank_gives_a_package_for_writing_a_task(conn):
    seed(conn, "sasha")
    package = service.next_task(conn, "sasha", "en", PARAMS)

    assert (package["source"], package["tutor_mode"], package["max_attempts"]) == ("generate", "rule", 3)
    assert request_row(conn, package["request_id"]) == ("rule", "failed", None)  # open until submit_task
    brief = package["brief"]
    assert list(Draft202012Validator(BRIEF_SCHEMA).iter_errors(brief)) == []
    assert (brief["target_concept"], brief["difficulty"]) == ("logic.ordering", 2)
    assert package["topic"]["id"] == "logic.ordering"
    assert [(task["topic"], task["grade_level"], task["difficulty"]) for task in package["examples"]] == \
        [("logic.ordering", "3-4", 2)] * 3
    assert package["readability"] == {"max_sentence_words": 25, "max_flesch_kincaid_grade": 7}
    assert set(package["formats"]) == {"brief", "task", "self_check"}
    assert len(package["traps"]) == len(load_catalog("traps"))
    assert "solver_code" in package["guide"] and package["recent_tasks"] == []
    assert len(json.dumps(package)) < 40_000  # well inside the clients' tool result limits (SPEC 8)


def test_package_in_another_language_has_no_flesch_kincaid_limit(conn):
    seed(conn, "sasha")
    readability = service.next_task(conn, "sasha", "ru", PARAMS)["readability"]
    assert readability == {"max_sentence_words": 25, "max_flesch_kincaid_grade": None}


def test_bank_task_is_issued_without_the_answer(conn):
    seed(conn, "sasha")
    task_id = bank_task(conn)
    result = service.next_task(conn, "sasha", "en", PARAMS)

    assert (result["source"], result["task_id"]) == ("bank", task_id)
    assert result["question"].startswith("Five children") and set(result["options"]) == set("ABCDE")
    assert result["hint"] == "Who is first?"
    text = json.dumps(result)
    assert "correct_answer" not in text and "distractors" not in text and "Kim is third" not in text
    assert request_row(conn, result["request_id"]) == ("rule", "bank", task_id)
    issued = conn.execute("SELECT count(*) FROM student_tasks WHERE student_id = 'sasha' AND task_id = %s",
                          (task_id,)).fetchone()[0]  # fmt: skip
    assert issued == 1


def test_bank_task_in_another_language_is_not_given(conn):
    seed(conn, "sasha")
    bank_task(conn, language="ru")
    assert service.next_task(conn, "sasha", "en", PARAMS)["source"] == "generate"
    assert service.next_task(conn, "sasha", "ru", PARAMS)["source"] == "bank"


def test_bank_task_is_given_only_once(conn):
    seed(conn, "sasha")
    bank_task(conn)
    assert service.next_task(conn, "sasha", "en", PARAMS)["source"] == "bank"
    second = service.next_task(conn, "sasha", "en", PARAMS)
    assert second["source"] == "generate"
    assert second["recent_tasks"] == ["Five children stand in a row. Who stands in the middle?"]  # do not repeat it


def test_model_can_change_the_topic_and_difficulty(conn):
    seed(conn, "masha")
    package = service.next_task(conn, "masha", "en", PARAMS, topic="time.calendar", difficulty=1,
                                reason="Two failures in a row: an easy task in a fresh topic.")  # fmt: skip

    assert package["tutor_mode"] == "llm"
    assert request_row(conn, package["request_id"])[0] == "llm"
    brief = package["brief"]
    assert (brief["target_concept"], brief["difficulty"]) == ("time.calendar", 1)
    assert brief["rationale"].startswith("Changed by the model: Two failures")
    assert "time.clocks" in brief["rationale"]  # the rule's suggestion stays visible
    assert list(Draft202012Validator(BRIEF_SCHEMA).iter_errors(brief)) == []
    assert {(task["topic"], task["difficulty"]) for task in package["examples"]} == {("time.calendar", 1)}


def test_changed_difficulty_searches_the_bank_around_its_level(conn):
    seed(conn, "sasha")
    easy = bank_task(conn, difficulty=1, rating=-2.0)  # below sasha's corridor for difficulty 2
    assert service.next_task(conn, "sasha", "en", PARAMS)["source"] == "generate"
    result = service.next_task(conn, "sasha", "en", PARAMS, difficulty=1, reason="Warm-up.")
    assert (result["source"], result["task_id"]) == ("bank", easy)


@pytest.mark.parametrize(
    ("student", "arguments", "fragment"),
    [
        ("masha", {"topic": "time.calendar"}, "reason"),
        ("dima", {"topic": "logic.knights_liars", "reason": "Try logic."}, "not taught"),
        ("masha", {"difficulty": 6, "reason": "Harder."}, "1-5"),
        ("masha", {"language": "english"}, "ISO 639-1"),
    ],
    ids=["change without a reason", "topic above the grade level", "difficulty 6", "language name"],
)
def test_bad_arguments_are_explained(conn, student, arguments, fragment):
    seed(conn, student)
    language = arguments.pop("language", "en")
    with pytest.raises(service.InvalidRequest, match=fragment):
        service.next_task(conn, student, language, PARAMS, **arguments)


def test_examples_rotate_with_the_history():
    first = service.pick_examples("counting.gaps", "1-2", 3, offset=0)
    second = service.pick_examples("counting.gaps", "1-2", 3, offset=1)
    assert len(first) == len(second) == 3 and first != second
    assert {task["difficulty"] for task in first + second} == {3}


# Instructions and prompt_version


def test_instructions_name_the_tools():
    text = service.instructions()
    assert all(name in text for name in ("get_student_profile", "get_progress", "get_next_task", "submit_task"))


def test_prompt_version(tmp_path):
    first, second = tmp_path / "a.md", tmp_path / "b.md"
    first.write_text("Be kind.", encoding="utf-8")
    second.write_text("Be brief.", encoding="utf-8")
    version = service.prompt_version((first, second))
    assert len(version) == 12 and int(version, 16) >= 0
    assert service.prompt_version((second, first)) == version  # order does not matter
    first.write_text("Be kind!", encoding="utf-8")
    assert service.prompt_version((first, second)) != version
    assert len(service.prompt_version()) == 12  # the real instruction files
