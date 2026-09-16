"""submit_answer (T22): the answer, the trap, pace, the failure streak and the ratings, on the test database."""

import json

import pytest

from taskgen import db, service
from taskgen.rating import load_params, update
from taskgen.seed import SEED_DIR, seed_student

PARAMS = load_params()
TRAPS = {"A": "reversed_relation", "B": "stopped_early", "D": "ignored_condition", "E": "number_from_text"}


def seed(conn, name="sasha"):
    seed_student(conn, json.loads((SEED_DIR / f"{name}.json").read_text(encoding="utf-8")), PARAMS)


def give_task(conn, student="sasha", topic="logic.ordering", difficulty=2):
    """A bank task issued to the student; sasha is a new grade 4 student with every rating at 0."""
    brief = {
        "rationale": "Test.", "pedagogical_goal": "new_topic", "target_concept": topic, "difficulty": difficulty,
        "setting": "music", "traps_to_use": ["reversed_relation"], "constraints": [], "excluded_skills": [],
        "profile_fields_used": ["history"],
    }  # fmt: skip
    task = {
        "core_idea": "Middle of five.", "design_thought_process": "Plot: a concert.",
        "question": "Five children stand in a row. Who stands in the middle?",
        "options": {"A": "Ann", "B": "Ben", "C": "Kim", "D": "Dan", "E": "Eva"}, "correct_answer": "C",
        "solution": "Kim is the third of five.", "hint": "Who is first?",
        "distractors": {letter: {"trap": trap, "text": f"Trap {trap}."} for letter, trap in TRAPS.items()},
    }  # fmt: skip
    task_id = db.save_task(conn, brief=brief, task=task, analyst={}, skeptic={}, grade_level="3-4",
                           attempt_count=1, rating=difficulty - 3.0)  # fmt: skip
    db.issue_task(conn, student, task_id)
    return task_id


def history_row(conn, task_id):
    return conn.execute(
        "SELECT correct, chosen_option, trap_hit, feedback, hint_used, pace FROM student_tasks WHERE task_id = %s",
        (task_id,),
    ).fetchone()


def ratings(conn, task_id, topic="logic.ordering"):
    student = conn.execute("SELECT rating, answers_count, consecutive_failures FROM students "
                           "WHERE student_id = 'sasha'").fetchone()  # fmt: skip
    offset = conn.execute("SELECT topic_offset, answers_count FROM student_topic_ratings "
                          "WHERE student_id = 'sasha' AND topic = %s", (topic,)).fetchone()  # fmt: skip
    task = conn.execute("SELECT rating, rating_count FROM tasks WHERE task_id = %s", (task_id,)).fetchone()
    return student, offset, task


# The three kinds of answer


def test_correct_answer(conn):
    seed(conn)
    task_id = give_task(conn)
    result = service.submit_answer(conn, "sasha", task_id, "C", False, PARAMS)

    assert (result["result"], result["correct"], result["correct_answer"], result["trap"]) == ("correct", True, "C",
                                                                                               None)  # fmt: skip
    assert result["solution"] == "Kim is the third of five." and result["failures_in_a_row"] == 0
    assert history_row(conn, task_id) == (True, "C", None, None, False, "fast")

    # Ratings move as in T13: theta, delta and beta of a new student, topic and task, each with its own K.
    expected = update(0.0, 0.0, -1.0, correct=True, student_answers=0, topic_answers=0, task_answers=0,
                      params=PARAMS)  # fmt: skip
    (theta, answers, failures), (offset, topic_answers), (beta, task_answers) = ratings(conn, task_id)
    assert (theta, offset, beta) == pytest.approx((expected.theta, expected.delta, expected.beta), abs=1e-6)
    assert (answers, topic_answers, task_answers, failures) == (1, 1, 1, 0)
    assert result["topic_rating"]["before"] == 1500 < result["topic_rating"]["after"]


def test_wrong_answer_records_the_trap(conn):
    seed(conn)
    task_id = give_task(conn)
    result = service.submit_answer(conn, "sasha", task_id, "A", False, PARAMS)

    assert (result["result"], result["correct"], result["chosen_option"]) == ("wrong", False, "A")
    assert result["trap"] == {"id": "reversed_relation", "text": "Trap reversed_relation."}
    assert "trap.text" in result["next"]
    assert history_row(conn, task_id) == (False, "A", "reversed_relation", None, False, "fast")
    (theta, _, failures), (offset, _), (beta, _) = ratings(conn, task_id)
    assert theta < 0 and offset < 0 and beta > -1.0 and failures == 1  # the student down, the task harder
    assert result["topic_rating"]["after"] < 1500


def test_did_not_understand(conn):
    seed(conn)
    task_id = give_task(conn)
    result = service.submit_answer(conn, "sasha", task_id, "?", False, PARAMS)

    assert (result["result"], result["correct"], result["chosen_option"], result["trap"]) == (
        "did not understand", None, None, None)  # fmt: skip
    assert history_row(conn, task_id) == (None, None, None, "didn't understand the question", False, "fast")
    (theta, _, failures), _, _ = ratings(conn, task_id)
    assert theta < 0 and failures == 1  # "?" counts as S = 0 and as a failure (SPEC 3, 5.6)


# Hint, pace and input


@pytest.mark.parametrize(("seconds", "pace"), [(10, "fast"), (100, "normal"), (200, "struggled")])
def test_pace_is_measured_from_issue_to_answer(conn, seconds, pace):
    seed(conn)
    task_id = give_task(conn)
    conn.execute("UPDATE student_tasks SET issued_at = now() - make_interval(secs => %s) WHERE task_id = %s",
                 (seconds, task_id))  # fmt: skip
    result = service.submit_answer(conn, "sasha", task_id, "C", True, PARAMS)
    assert (result["pace"], result["hint_used"]) == (pace, True)
    assert history_row(conn, task_id)[4:] == (True, pace)


def test_answer_letter_is_normalised(conn):
    seed(conn)
    assert service.submit_answer(conn, "sasha", give_task(conn), " c ", False, PARAMS)["correct"] is True


def test_answer_is_recorded_only_once(conn):
    seed(conn)
    task_id = give_task(conn)
    service.submit_answer(conn, "sasha", task_id, "C", False, PARAMS)
    with pytest.raises(service.InvalidRequest, match="already answered"):
        service.submit_answer(conn, "sasha", task_id, "A", False, PARAMS)


def test_only_tasks_given_to_the_student_can_be_answered(conn):
    seed(conn)
    seed(conn, "petya")
    task_id = give_task(conn, student="petya")
    with pytest.raises(service.InvalidRequest, match="was not given"):
        service.submit_answer(conn, "sasha", task_id, "C", False, PARAMS)
    with pytest.raises(service.StudentNotFound):
        service.submit_answer(conn, "nobody", task_id, "C", False, PARAMS)
    with pytest.raises(service.InvalidRequest, match="A-E"):
        service.submit_answer(conn, "petya", task_id, "F", False, PARAMS)


# The answer changes what comes next


def test_a_wrong_answer_turns_the_rule_to_reinforce(conn):
    seed(conn)
    before = service.student_profile(conn, "sasha", PARAMS)["recommendation"]
    assert (before["pedagogical_goal"], before["target_concept"]) == ("new_topic", "logic.ordering")
    service.submit_answer(conn, "sasha", give_task(conn), "A", False, PARAMS)
    after = service.student_profile(conn, "sasha", PARAMS)["recommendation"]
    assert (after["pedagogical_goal"], after["target_concept"]) == ("reinforce", "logic.ordering")
    assert after["traps_to_use"][0] == "reversed_relation"  # the fresh trap_hit leads the next brief
