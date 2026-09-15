"""db.py on a real PostgreSQL (T12); the separate test database and its fixtures are in conftest.py."""

import psycopg
import pytest

from taskgen import db
from taskgen.seed import seed_student

TOPIC = "combinatorics.enumeration"


def add_student(conn, student_id="masha", grade=3, excluded_skills=("fractions",), consecutive_failures=0, history=()):
    profile = {
        "id": student_id,
        "grade": grade,
        "interests": ["space"],
        "cognitive_profile": ["off-by-one when counting gaps"],
        "mastered_topics": [],
        "excluded_skills": list(excluded_skills),
        "consecutive_failures": consecutive_failures,
        "history": list(history),
    }
    seed_student(conn, profile)
    return db.load_student(conn, student_id)


def make_brief(topic=TOPIC, difficulty=3, setting="space", excluded_skills=("fractions",)):
    return {
        "rationale": "Test brief.",
        "pedagogical_goal": "reinforce",
        "target_concept": topic,
        "difficulty": difficulty,
        "setting": setting,
        "traps_to_use": ["missed_case"],
        "constraints": [],
        "excluded_skills": list(excluded_skills),
        "profile_fields_used": ["history"],
    }


def make_task(question="Four spaceships dock in pairs. How many different pairs can they make?",
              traps=("missed_case", "double_count", "off_by_one", "number_from_text")):
    return {
        "core_idea": "Unordered pairs among 4 objects: 6.",
        "design_thought_process": "Plot: docking.",
        "question": question,
        "options": {"A": "4", "B": "5", "C": "6", "D": "8", "E": "12"},
        "correct_answer": "C",
        "solution": "List the pairs.",
        "hint": "How many ships can the first ship dock with?",
        "distractors": {letter: {"trap": trap, "text": "Explanation."} for letter, trap in zip("ABDE", traps)},
    }


def add_task(conn, rating=0.0, grade_level="3-4", **brief_fields):
    task_fields = {key: brief_fields.pop(key) for key in ("question", "traps") if key in brief_fields}
    return db.save_task(
        conn,
        brief=make_brief(**brief_fields),
        task=make_task(**task_fields),
        analyst={"solving_thought_process": "Six pairs.", "final_answer": "C", "solver_code": "print('[\"C\"]')"},
        skeptic={"issues": [], "option_check": {}, "final_answer": "C"},
        grade_level=grade_level,
        attempt_count=1,
        rating=rating,
    )


def test_tests_use_the_separate_database(conn):
    assert conn.info.dbname == "taskgen_test"


@pytest.mark.parametrize(("grade", "level"), [(1, "1-2"), (2, "1-2"), (3, "3-4"), (4, "3-4")])
def test_grade_level(grade, level):
    assert db.grade_level(grade) == level


def test_grade_level_outside_1_to_4_is_rejected():
    with pytest.raises(ValueError):
        db.grade_level(5)


# Students


def test_load_student_returns_profile_ratings_and_last_history(conn):
    history = [
        {"topic": TOPIC, "difficulty": level, "correct": True, "pace": "normal"} for level in (1, 2, 3, 4, 5)
    ] + [{"topic": "time.clocks", "difficulty": 2, "correct": False, "chosen_option": "B", "trap_hit": "off_by_one"}]
    add_student(conn, grade=3, consecutive_failures=1, history=history)
    db.save_student_rating(conn, "masha", 0.5, 6)
    db.save_topic_rating(conn, "masha", TOPIC, -0.25, 5)

    student = db.load_student(conn, "masha")

    assert student["grade"] == 3
    assert student["interests"] == ["space"]
    assert student["excluded_skills"] == ["fractions"]
    assert student["consecutive_failures"] == 1
    assert (student["rating"], student["answers_count"]) == (0.5, 6)
    assert student["topic_ratings"][TOPIC] == {"offset": -0.25, "answers_count": 5}
    assert student["topic_ratings"].keys() == {TOPIC, "time.clocks"}  # seed replays the history for both topics
    # The last 5 of 6 rows, oldest first.
    assert [(row["topic"], row["difficulty"]) for row in student["history"]] == [
        (TOPIC, 2), (TOPIC, 3), (TOPIC, 4), (TOPIC, 5), ("time.clocks", 2)
    ]
    assert student["history"][-1]["trap_hit"] == "off_by_one"
    assert all(row["task_id"] is None for row in student["history"])


def test_history_limit_is_a_parameter(conn):
    history = [{"topic": TOPIC, "difficulty": level, "correct": True} for level in (1, 2, 3)]
    add_student(conn, history=history)
    assert [row["difficulty"] for row in db.load_student(conn, "masha", history_limit=2)["history"]] == [2, 3]


def test_whole_history_and_student_list(conn):
    history = [{"topic": TOPIC, "difficulty": level, "correct": True} for level in (1, 2, 3, 4, 5, 1, 2)]
    add_student(conn, "petya", history=history)
    add_student(conn, "masha")
    assert len(db.load_student(conn, "petya", history_limit=None)["history"]) == 7
    assert db.list_students(conn) == ["masha", "petya"]


def test_unknown_student_is_none(conn):
    assert db.load_student(conn, "nobody") is None


def test_consecutive_failures(conn):
    add_student(conn, consecutive_failures=2, history=[{"topic": TOPIC, "difficulty": 3, "correct": False,
                                                        "chosen_option": "A"}] * 2)
    assert db.update_consecutive_failures(conn, "masha", False) == 3
    assert db.update_consecutive_failures(conn, "masha", None) == 4  # "?" is a failure too
    assert db.update_consecutive_failures(conn, "masha", True) == 0
    assert db.load_student(conn, "masha")["consecutive_failures"] == 0


def test_consecutive_failures_of_unknown_student(conn):
    with pytest.raises(LookupError):
        db.update_consecutive_failures(conn, "nobody", True)


def test_save_ratings(conn):
    add_student(conn)
    db.save_topic_rating(conn, "masha", TOPIC, 0.5, 1)
    db.save_topic_rating(conn, "masha", TOPIC, 0.25, 2)  # a later answer updates the same row
    db.save_student_rating(conn, "masha", -0.75, 2)
    student = db.load_student(conn, "masha")
    assert (student["rating"], student["answers_count"]) == (-0.75, 2)
    assert student["topic_ratings"] == {TOPIC: {"offset": 0.25, "answers_count": 2}}

    task_id = add_task(conn, rating=0.0)
    db.save_task_rating(conn, task_id, 0.5, 1)
    assert conn.execute("SELECT rating, rating_count FROM tasks WHERE task_id = %s", (task_id,)).fetchone() == (0.5, 1)


def test_save_ratings_of_unknown_rows(conn):
    with pytest.raises(LookupError):
        db.save_student_rating(conn, "nobody", 0.0, 0)
    with pytest.raises(LookupError):
        db.save_task_rating(conn, "t-missing", 0.0, 0)


# Requests and attempts


def test_request_with_attempts(conn):
    add_student(conn)
    request_id = db.create_request(conn, "masha", "llm", make_brief())
    assert conn.execute("SELECT source, task_id FROM requests WHERE request_id = %s", (request_id,)).fetchone() == (
        "failed", None
    )

    client = {"name": "claude-code", "version": "2.1.270"}  # clientInfo of the MCP client (SPEC 7)
    db.record_attempt(conn, request_id, 1, "rejected", "p-1", reason="solver_disagrees",
                      generator=make_task(), analyst={"solver_code": "print('[\"B\"]')"},
                      skeptic={"final_answer": "C"}, solver_result=["B"], models=client, duration_ms=9000)
    db.record_attempt(conn, request_id, 2, "accepted", "p-1", generator=make_task(), models=client)
    task_id = add_task(conn)
    db.close_request(conn, request_id, "generated", task_id, attempt_count=2, duration_ms=20000)

    request = conn.execute(
        "SELECT source, task_id, attempt_count, tokens, cost_usd, duration_ms FROM requests WHERE request_id = %s",
        (request_id,),
    ).fetchone()
    assert request == ("generated", task_id, 2, None, None, 20000)  # no LLM calls of our own (D42)
    attempts = conn.execute(
        "SELECT attempt_no, status, reason, solver_result, models FROM attempts WHERE request_id = %s "
        "ORDER BY attempt_no",
        (request_id,),
    ).fetchall()
    assert attempts == [
        (1, "rejected", "solver_disagrees", ["B"], client),
        (2, "accepted", None, None, client),
    ]


def test_failed_request_has_no_task(conn):
    add_student(conn)
    request_id = db.create_request(conn, "masha", "rule", make_brief())
    task_id = add_task(conn)
    with pytest.raises(ValueError):
        db.close_request(conn, request_id, "failed", task_id)
    with pytest.raises(ValueError):
        db.close_request(conn, request_id, "bank")
    with pytest.raises(ValueError):
        db.close_request(conn, request_id, "cached", task_id)
    db.close_request(conn, request_id, "failed", attempt_count=3)


def test_unknown_tutor_mode_and_status_are_rejected(conn):
    add_student(conn)
    with pytest.raises(ValueError):
        db.create_request(conn, "masha", "human", make_brief())
    request_id = db.create_request(conn, "masha", "llm", make_brief())
    with pytest.raises(ValueError):
        db.record_attempt(conn, request_id, 1, "skipped", "p-1")
    with pytest.raises(ValueError):
        db.record_attempt(conn, request_id, 1, "accepted", "p-1", reason="readability")


# Task bank


def test_save_task_takes_fields_from_brief_and_task(conn):
    task_id = add_task(conn, rating=-1.0, grade_level="1-2", topic="time.clocks", difficulty=2, setting="robots",
                       excluded_skills=("fractions", "division_with_remainder"),
                       traps=("off_by_one", "off_by_one", "time_unit_mixup", "number_from_text"))
    row = conn.execute(
        "SELECT topic, difficulty, grade_level, setting, excluded_skills, traps, attempt_count, rating, rating_count, "
        "task ->> 'correct_answer' FROM tasks WHERE task_id = %s",
        (task_id,),
    ).fetchone()
    assert task_id.startswith("t-")
    assert row == ("time.clocks", 2, "1-2", "robots", ["fractions", "division_with_remainder"],
                   ["number_from_text", "off_by_one", "time_unit_mixup"], 1, -1.0, 0, "C")
    # Accepted tasks show up in the dataset views.
    assert conn.execute("SELECT count(*) FROM finetune_solver WHERE task_id = %s", (task_id,)).fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM finetune_generator WHERE task_id = %s", (task_id,)).fetchone()[0] == 1


def test_bank_candidates_apply_every_condition(conn):
    student = add_student(conn, grade=3, excluded_skills=("fractions",))
    fits = add_task(conn, rating=0.0, excluded_skills=("fractions", "division_with_remainder"))
    low_edge = add_task(conn, rating=-0.5)
    high_edge = add_task(conn, rating=0.5)
    add_task(conn, rating=0.0, topic="time.clocks")  # other topic
    add_task(conn, rating=1.5)  # above the corridor
    add_task(conn, rating=-1.0)  # below the corridor
    add_task(conn, rating=0.0, grade_level="1-2")  # other grade level
    add_task(conn, rating=0.0, excluded_skills=())  # generated without the student's restriction
    issued = add_task(conn, rating=0.0)
    db.issue_task(conn, "masha", issued)  # already given to this student

    found = db.bank_candidates(conn, student, TOPIC, (-0.5, 0.5))

    assert {row["task_id"] for row in found} == {fits, low_edge, high_edge}


def test_issued_task_stays_available_to_other_students(conn):
    add_student(conn, "masha")
    petya = add_student(conn, "petya")
    task_id = add_task(conn)
    db.issue_task(conn, "masha", task_id)
    assert [row["task_id"] for row in db.bank_candidates(conn, petya, TOPIC, (-1, 1))] == [task_id]


def test_student_without_restrictions_gets_any_task(conn):
    student = add_student(conn, excluded_skills=())
    task_id = add_task(conn, excluded_skills=())
    assert [row["task_id"] for row in db.bank_candidates(conn, student, TOPIC, (-1, 1))] == [task_id]


def test_bank_ranking_setting_then_shared_traps(conn):
    student = add_student(conn)
    other_setting_all_traps = add_task(conn, setting="robots",
                                       traps=("missed_case", "double_count", "off_by_one", "number_from_text"))
    same_setting_one_trap = add_task(conn, setting="space",
                                     traps=("missed_case", "wrong_operation", "off_by_one", "number_from_text"))
    same_setting_two_traps = add_task(conn, setting="space",
                                      traps=("missed_case", "double_count", "off_by_one", "number_from_text"))

    found = db.bank_candidates(conn, student, TOPIC, (-1, 1), setting="space",
                               traps_to_use=["missed_case", "double_count"])

    assert [row["task_id"] for row in found] == [same_setting_two_traps, same_setting_one_trap,
                                                 other_setting_all_traps]


def test_empty_bank_means_generate(conn):
    student = add_student(conn)
    assert db.bank_candidates(conn, student, TOPIC, (-1, 1)) == []


# Issued tasks and answers


def test_issue_task_and_save_answer(conn):
    add_student(conn)
    task_id = add_task(conn, difficulty=4, rating=1.0)
    row_id = db.issue_task(conn, "masha", task_id)
    db.save_answer(conn, row_id, correct=False, chosen_option="E", trap_hit="number_from_text", hint_used=True,
                   pace="struggled")

    last = db.load_student(conn, "masha")["history"][-1]
    assert (last["task_id"], last["topic"], last["difficulty"]) == (task_id, TOPIC, 4)
    assert (last["correct"], last["chosen_option"], last["trap_hit"], last["hint_used"], last["pace"]) == (
        False, "E", "number_from_text", True, "struggled"
    )


def test_did_not_understand_answer(conn):
    add_student(conn)
    row_id = db.issue_task(conn, "masha", add_task(conn))
    db.save_answer(conn, row_id, correct=None, feedback="didn't understand the question", pace="normal")
    last = db.load_student(conn, "masha")["history"][-1]
    assert last["correct"] is None and last["feedback"] == "didn't understand the question"


def test_task_is_never_issued_twice(conn):
    add_student(conn)
    task_id = add_task(conn)
    db.issue_task(conn, "masha", task_id)
    with pytest.raises(psycopg.errors.UniqueViolation):
        db.issue_task(conn, "masha", task_id)


def test_unknown_task_and_bad_answer_values_are_rejected(conn):
    add_student(conn)
    with pytest.raises(LookupError):
        db.issue_task(conn, "masha", "t-missing")
    row_id = db.issue_task(conn, "masha", add_task(conn))
    with pytest.raises(ValueError):
        db.save_answer(conn, row_id, correct=False, chosen_option="F")
    with pytest.raises(ValueError):
        db.save_answer(conn, row_id, correct=True, pace="slow")
    with pytest.raises(LookupError):
        db.save_answer(conn, row_id + 1000, correct=True)


# Text similarity


def test_similar_tasks_finds_near_duplicates(conn):
    near = add_task(conn, question="Four spaceships dock in pairs. How many different pairs can they make?")
    add_task(conn, question="A clock strikes 3 times at three o'clock. How long does it strike at six o'clock?")

    found = db.similar_tasks(conn, "Four spaceships dock in pairs. How many different pairs can the ships make?", 0.6)

    assert [row["task_id"] for row in found] == [near]
    assert 0.6 <= found[0]["similarity"] < 1


def test_similar_tasks_respects_the_threshold(conn):
    add_task(conn, question="Four spaceships dock in pairs. How many different pairs can they make?")
    assert db.similar_tasks(conn, "Five robots shake hands in pairs. How many handshakes are there?", 0.6) == []


def test_similarities_to_outside_texts(conn):
    question = "Four spaceships dock in pairs. How many different pairs can they make?"
    scores = db.similarities(conn, question, [question, "A clock strikes 3 times at three o'clock.", ""])
    assert scores[0] == pytest.approx(1.0)
    assert scores[1] < 0.3
    assert scores[2] == 0
