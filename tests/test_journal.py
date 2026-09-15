"""journal.py (T23): the readiness check, the log and the review list, on the test database from conftest.py."""

import json

from taskgen import db, journal
from taskgen.rating import load_params
from taskgen.seed import SEED_DIR, seed_student

BRIEF = {
    "rationale": "Test.", "pedagogical_goal": "new_topic", "target_concept": "logic.ordering", "difficulty": 2,
    "setting": "music", "traps_to_use": ["reversed_relation"], "constraints": [], "excluded_skills": [],
    "profile_fields_used": ["history"],
}  # fmt: skip
TASK = {
    "core_idea": "Middle of five.", "design_thought_process": "Plot: a concert.",
    "question": "Пять детей стоят в ряд. Кто стоит в середине?",
    "options": {"A": "Аня", "B": "Боря", "C": "Катя", "D": "Дима", "E": "Ева"}, "correct_answer": "C",
    "solution": "Катя третья из пяти.", "hint": "Кто первый?",
    "distractors": {letter: {"trap": "off_by_one", "text": "Посчитай ещё раз."} for letter in "ABDE"},
}  # fmt: skip


def live_run(conn):
    """sasha: one generated task answered wrongly after a rejection, and one request the model abandoned."""
    seed_student(conn, json.loads((SEED_DIR / "sasha.json").read_text(encoding="utf-8")), load_params())
    request_id = db.create_request(conn, "sasha", "rule", BRIEF)
    db.record_attempt(conn, request_id, 1, "rejected", "p-1", reason="readability", generator=TASK)
    db.record_attempt(conn, request_id, 2, "accepted", "p-1", generator=TASK)
    task_id = db.save_task(conn, brief=BRIEF, task=TASK, analyst={}, skeptic={"issues": [
        {"type": "too_hard_for_grade", "severity": "minor", "comment": "Long names."}]},
        grade_level="3-4", attempt_count=2, rating=-1.0, language="ru")  # fmt: skip
    row_id = db.issue_task(conn, "sasha", task_id)
    db.close_request(conn, request_id, "generated", task_id, attempt_count=2, duration_ms=48000)
    db.save_answer(conn, row_id, correct=False, chosen_option="B", trap_hit="off_by_one", hint_used=True,
                   pace="normal")  # fmt: skip
    db.create_request(conn, "sasha", "llm", BRIEF)  # abandoned: never handed in
    return task_id


def test_log_tells_the_story_of_the_run(conn):
    task_id = live_run(conn)
    text = "\n".join(journal.log_lines(conn, hours=24))
    assert f"sasha [rule] logic.ordering d2 new_topic -> generated {task_id} in 2 attempt(s), 48 s" in text
    assert "attempt 1 rejected: readability" in text and "attempt 2 accepted" in text
    assert "answer: wrong (B, trap off_by_one), hint, pace normal" in text
    assert "abandoned: no task handed in" in text
    assert "requests: 2 (generated 1, bank 0, failed 1, of them abandoned 1)" in text
    assert "accepted on the first attempt: 0 of 1 generated" in text
    assert "rejections: readability 1" in text and "answers: wrong 1" in text


def test_log_accepts_a_fractional_window(conn):
    # make_interval takes whole hours: --hours 1.5 used to fail in Postgres, not in the tests.
    live_run(conn)
    assert any("sasha" in line for line in journal.log_lines(conn, hours=1.5))
    assert journal.tasks_lines(conn, hours=0.25)[0].startswith("t-")


def test_a_reset_student_does_not_borrow_the_repeat_answer(conn):
    # seed --student deletes the issued rows, then the bank gives the same task to a new request (T23 finding).
    task_id = live_run(conn)
    old = conn.execute("SELECT request_id FROM requests WHERE task_id = %s", (task_id,)).fetchone()[0]
    conn.execute("UPDATE requests SET created_at = created_at - interval '1 hour' WHERE student_id = 'sasha'")
    seed_student(conn, json.loads((SEED_DIR / "sasha.json").read_text(encoding="utf-8")), load_params())
    repeat = db.create_request(conn, "sasha", "rule", BRIEF)
    row_id = db.issue_task(conn, "sasha", task_id)
    db.close_request(conn, repeat, "bank", task_id)
    db.save_answer(conn, row_id, correct=True, chosen_option="C", pace="fast")
    answers = db.request_answers(conn, [old, repeat])
    assert old not in answers and answers[repeat]["correct"] is True
    text = "\n".join(journal.log_lines(conn, hours=24))
    assert f"from the bank: {task_id}" in text and "answer: not answered" in text


def test_log_filters_by_student(conn):
    live_run(conn)
    assert journal.log_lines(conn, student="masha", hours=24)[0] == ""  # nothing but the empty summary


def test_tasks_list_the_written_tasks_for_review(conn):
    task_id = live_run(conn)
    text = "\n".join(journal.tasks_lines(conn, hours=24))
    assert task_id in text and "logic.ordering d2  grades 3-4  ru  for sasha" in text
    assert "* C) Катя   <- correct" in text
    assert "B) Боря   [off_by_one: Посчитай ещё раз.]" in text
    assert "Self-check notes: Long names." in text


def test_tasks_list_says_when_there_is_nothing(conn):
    assert journal.tasks_lines(conn, hours=24) == ["no tasks written by the model in this window"]


def test_check_reports_every_part(conn):
    seed_student(conn, json.loads((SEED_DIR / "sasha.json").read_text(encoding="utf-8")), load_params())
    results = {name: (ok, detail) for name, ok, detail in journal.check(conn)}
    assert set(results) == {"schema", "students", "bank", "sandbox", "instructions"}
    assert results["schema"][0] is True
    assert results["students"] == (False, "sasha")  # a live run needs all five seed profiles
    assert results["instructions"][1].startswith("prompt_version ")
