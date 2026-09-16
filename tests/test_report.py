"""report.py (T24): every SPEC 9 metric on a small run in the test database from conftest.py."""

import json

import pytest

from taskgen import db, report
from taskgen.rating import load_params
from taskgen.seed import SEED_DIR, seed_student

BRIEF = {
    "rationale": "Test.", "pedagogical_goal": "new_topic", "target_concept": "logic.ordering", "difficulty": 2,
    "setting": "music", "traps_to_use": ["reversed_relation"], "constraints": [], "excluded_skills": [],
    "profile_fields_used": ["history", "interests"],
}  # fmt: skip
QUESTION = ("Пять детей стоят в ряд на школьном концерте: Аня, Боря, Катя, Дима и Ева. "
            "Кто из них стоит в середине ряда?")  # fmt: skip
TASK = {
    "core_idea": "Middle of five.", "design_thought_process": "Plot: a concert.", "question": QUESTION,
    "options": {"A": "Аня", "B": "Боря", "C": "Катя", "D": "Дима", "E": "Ева"}, "correct_answer": "C",
    "solution": "Катя третья из пяти.", "hint": "Кто первый?",
    "distractors": {letter: {"trap": "off_by_one", "text": "Посчитай ещё раз."} for letter in "ABDE"},
}  # fmt: skip
CLIENT = {"name": "claude-code", "version": "2.1.270"}
OTHER = {"name": "other", "version": "1"}
MINOR = {"type": "too_hard_for_grade", "severity": "minor", "comment": "Long names."}


def generate(conn, student, mode, question, *, rejected=(), prompt="p-1", models=CLIENT, ms=60000, skeptic=None):
    """A request whose task was accepted after the rejected attempts; returns (task_id, issued row id)."""
    request_id = db.create_request(conn, student, mode, BRIEF)
    for number, reason in enumerate(rejected, 1):
        db.record_attempt(conn, request_id, number, "rejected", prompt, reason=reason, models=models)
    attempts = len(rejected) + 1
    db.record_attempt(conn, request_id, attempts, "accepted", prompt, models=models)
    task_id = db.save_task(conn, brief=BRIEF, task=dict(TASK, question=question), analyst={},
                           skeptic=skeptic or {"issues": []}, grade_level="3-4", attempt_count=attempts, rating=-1.0,
                           language="ru")  # fmt: skip
    row_id = db.issue_task(conn, student, task_id)
    db.close_request(conn, request_id, "generated", task_id, attempt_count=attempts, duration_ms=ms)
    return task_id, row_id


def small_run(conn):
    """sasha: accepted at once and solved; a near duplicate accepted on the 2nd attempt and missed; a failed request.
    masha: an abandoned request and the first task again from the bank."""
    for name in ("sasha", "masha"):
        seed_student(conn, json.loads((SEED_DIR / f"{name}.json").read_text(encoding="utf-8")), load_params())
    first, row = generate(conn, "sasha", "rule", QUESTION, skeptic={"issues": [MINOR]})
    db.save_answer(conn, row, correct=True, chosen_option="C", pace="normal")
    second, row = generate(conn, "sasha", "llm", QUESTION.replace("концерте", "празднике"),
                           rejected=["solver_disagrees"], prompt="p-2", models=OTHER, ms=120000)  # fmt: skip
    db.save_answer(conn, row, correct=False, chosen_option="B", trap_hit="off_by_one", pace="normal")
    reinforce = dict(BRIEF, pedagogical_goal="reinforce", traps_to_use=["off_by_one"])
    failed = db.create_request(conn, "sasha", "rule", reinforce)
    for number, reason in enumerate(["readability", "self_check_blocking", "near_duplicate"], 1):
        db.record_attempt(conn, failed, number, "rejected", "p-2", reason=reason, models=CLIENT)
    db.close_request(conn, failed, "failed", attempt_count=3)
    db.create_request(conn, "masha", "rule", BRIEF)  # abandoned: nothing handed in
    bank = db.create_request(conn, "masha", "rule", BRIEF)
    row = db.issue_task(conn, "masha", first)
    db.close_request(conn, bank, "bank", first)
    db.save_answer(conn, row, correct=True, chosen_option="C", pace="fast")
    return first, second


def line(lines, start):
    """The line that starts with this label."""
    return next(text for text in lines if text.startswith(start))


def section(lines, title):
    """The lines of a section, up to the next blank line."""
    start = lines.index(title) + 1
    end = lines.index("", start) if "" in lines[start:] else len(lines)
    return lines[start:end]


def test_metrics(conn):
    first, second = small_run(conn)
    reviews = {first: {"verdict": "ok"}, second: {"verdict": "false_accept", "issues": ["ambiguous"]},
               "t-gone": {"verdict": "ok"}}  # fmt: skip
    lines = report.report_lines(conn, hours=1, reviews=reviews)
    assert lines[0].startswith("SPEC 9 metrics: 5 requests")
    expected = {
        "accepted on the 1st attempt": "1 of 3  33%",  # the abandoned request is not in the three
        "accepted on the 2nd / 3rd attempt": "1 / 0",
        "accepted within 3 attempts": "2 of 3  67%",
        "abandoned: nothing handed in": "1",
        "manual review: good": "1 of 2  50%",
        "false accepts": "1 of 2  50%",
        "solver disagreed, of attempts": "1 of 6  17%",
        "blocking self-check, of attempts": "1 of 6  17%",
        "minor self-check notes, of accepted": "1 of 2  50%",
        "from the bank, of requests": "1 of 5  20%",
        "unique plots within a topic": "1 of 2  50%",  # the second task nearly repeats the first
        "time of a generated task, median": "90 s (p90 120 s; under 90 s: 1 of 2)",
    }
    for label, value in expected.items():
        assert value in line(lines, label), label
    reasons = line(lines, "rejection reasons: ").removeprefix("rejection reasons: ").split(", ")
    assert sorted(reasons) == ["near_duplicate 1", "readability 1", "self_check_blocking 1", "solver_disagrees 1"]
    assert "history 5, interests 5" in line(lines, "profile fields used in 5 briefs")
    assert line(lines, "manual review: 2 of 2").endswith("issues: ambiguous 1")
    assert "  1 reviews are for tasks outside this report" in lines


def test_tutor_modes_and_failures(conn):
    small_run(conn)
    lines = report.report_lines(conn, hours=1, reviews={})
    modes = section(lines, "tutor modes (rule: the rule's brief; llm: changed by the model)")
    assert line(modes, "rule ").split() == ["rule", "4", "2", "2", "of", "2", "100%", "above"]
    assert line(modes, "llm ").split() == ["llm", "1", "1", "0", "of", "1", "0%", "below"]
    # the failed rule request right after the wrong answer reinforces and uses its trap
    assert "  rule: goals reinforce 1; fresh trap in the brief 1 of 1  100%" in modes
    assert "blind comparison of rule and model briefs: deferred (D45)" in lines


def test_breakdowns(conn):
    small_run(conn)
    lines = report.report_lines(conn, hours=1, reviews={})
    clients = section(lines, "by client")
    # the first task and the failed request: 1 of 2 accepted, at once, in 60 s
    row = line(clients, "claude-code 2.1.270").split()[2:]
    assert row == ["2", "1", "of", "2", "50%", "1", "of", "2", "50%", "0", "0", "60", "s"]
    assert line(clients, "- ").split()[1] == "2"  # bank and abandoned requests report no client
    versions = section(lines, "by prompt_version")
    assert [text.split()[0] for text in versions[1:]] == ["-", "p-1", "p-2"]
    topics = section(lines, "diversity by topic (a near duplicate from similarity 0.6)")
    assert line(topics, "logic.ordering").split() == ["logic.ordering", "2", "1", "of", "2", "50%"]


def test_empty_window(conn):
    assert report.report_lines(conn, hours=1, reviews={}) == ["no requests in this window"]


@pytest.mark.parametrize("reviews, error", [
    ([], "must hold an object"),
    ({"t-1": "ok"}, "must be an object"),
    ({"t-1": {"verdict": "great"}}, "verdict must be one of"),
    ({"t-1": {"verdict": "ok", "score": 5}}, "unknown fields score"),
    ({"t-1": {"verdict": "bad", "issues": ["boring"]}}, "issues must be a list"),
    ({"t-1": {"verdict": "bad", "note": 3}}, "note must be text"),
])  # fmt: skip
def test_review_errors(reviews, error):
    assert error in "; ".join(report.review_errors(reviews))


def test_reviews_file(tmp_path):
    assert report.load_reviews(tmp_path / "missing.json") == {}
    assert report.review_errors(report.load_reviews()) == []  # the file in data/eval is valid
    bad = tmp_path / "reviews.json"
    bad.write_text('{"t-1": {"verdict": "great"}}', encoding="utf-8")
    with pytest.raises(ValueError, match="verdict"):
        report.load_reviews(bad)
