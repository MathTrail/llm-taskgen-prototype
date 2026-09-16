"""submit_task (T21): every rejection reason, acceptance, the attempt limit. On the test database from conftest.py,
with the real sandbox (skipped without Docker)."""

import json
import shutil
import subprocess

import pytest

from taskgen import sandbox, service
from taskgen.filters import load_thresholds, readability
from taskgen.rating import load_params
from taskgen.seed import SEED_DIR, seed_student
from taskgen.validate_examples import load_examples


def docker_works() -> bool:
    return bool(shutil.which("docker")) and subprocess.run(["docker", "info"], capture_output=True).returncode == 0


pytestmark = pytest.mark.skipif(not docker_works(), reason="Docker is not available")

PARAMS = load_params()
CLIENT = {"name": "claude-code", "version": "2.1.270"}
QUESTION = "Ann, Ben and Kim ran a race. Ben finished before Kim. Ann finished after Kim. Who finished first?"
SOLVER = """
import itertools, json
first = set()
for order in itertools.permutations(["Ann", "Ben", "Kim"]):
    place = {name: i for i, name in enumerate(order)}
    if place["Ben"] < place["Kim"] and place["Ann"] > place["Kim"]:
        first.add(order[0])
options = {"A": "Ann", "B": "Kim", "C": "Ben", "D": "Nobody", "E": "All at once"}
print(json.dumps([letter for letter, name in options.items() if {name} == first]))
"""
LONG_QUESTION = (
    "Ann, Ben and Kim ran a long race around the old park near the river on a sunny Saturday morning while all "
    "their friends and parents were watching and cheering loudly. Ben finished before Kim. Ann finished after Kim. "
    "Who finished first?"
)


def seed(conn, name="sasha"):
    seed_student(conn, json.loads((SEED_DIR / f"{name}.json").read_text(encoding="utf-8")), PARAMS)


def open_request(conn, student="sasha", language="en"):
    package = service.next_task(conn, student, language, PARAMS)
    assert package["source"] == "generate"
    return package


def good_task(question=QUESTION):
    return {
        "core_idea": "Order three runners from two comparisons.",
        "design_thought_process": "Plot: a race. Traps: reversed comparisons, stopping early.",
        "question": question,
        "options": {"A": "Ann", "B": "Kim", "C": "Ben", "D": "Nobody", "E": "All at once"},
        "correct_answer": "C",
        "solution": "Ben is before Kim, and Kim is before Ann. So Ben is first.",
        "hint": "Who finished before Kim?",
        "distractors": {
            "A": {"trap": "reversed_relation", "text": "Ann finished after Kim, so she is last."},
            "B": {"trap": "stopped_early", "text": "Kim is in the middle: Ben beat her."},
            "D": {"trap": "ignored_condition", "text": "Someone always finishes first."},
            "E": {"trap": "answered_other_question", "text": "They finished one after another."},
        },
    }


def good_check(final="C", issues=()):
    return {
        "issues": list(issues),
        "option_check": {"A": "wrong because Ann is last", "B": "wrong because Kim is second", "C": "correct",
                         "D": "wrong because someone finished first", "E": "wrong because nobody tied"},
        "final_answer": final,
    }  # fmt: skip


def submit(conn, package, *, brief=None, task=None, solver=SOLVER, check=None, language="en", **options):
    return service.submit_task(conn, package["request_id"], brief or package["brief"], task or good_task(), solver,
                               check or good_check(), language, PARAMS, client=CLIENT, **options)  # fmt: skip


def codes(result):
    return [reason["code"] for reason in result["reasons"]]


def request_row(conn, request_id):
    return conn.execute(
        "SELECT source, task_id, attempt_count, tutor_mode FROM requests WHERE request_id = %s", (request_id,)
    ).fetchone()


def attempt_rows(conn, request_id):
    return conn.execute(
        "SELECT attempt_no, status, reason, models FROM attempts WHERE request_id = %s ORDER BY attempt_no",
        (request_id,),
    ).fetchall()


# Acceptance


def test_good_task_is_accepted_into_the_bank_and_issued(conn):
    seed(conn)
    package = open_request(conn)
    result = submit(conn, package)

    assert (result["status"], result["attempt"], result["minor_issues"]) == ("accepted", 1, [])
    task_id = result["task_id"]
    source, stored_id, attempts, tutor_mode = request_row(conn, package["request_id"])
    assert (source, stored_id, attempts, tutor_mode) == ("generated", task_id, 1, "rule")
    row = conn.execute(
        "SELECT topic, difficulty, language, rating, attempt_count, analyst -> 'solver_result' -> 'options' "
        "FROM tasks WHERE task_id = %s", (task_id,),
    ).fetchone()
    assert row == ("logic.ordering", 2, "en", -1.0, 1, ["C"])  # beta starts at difficulty - 3
    assert conn.execute("SELECT count(*) FROM student_tasks WHERE student_id = 'sasha' AND task_id = %s",
                        (task_id,)).fetchone()[0] == 1  # fmt: skip
    assert attempt_rows(conn, package["request_id"]) == [(1, "accepted", None, CLIENT)]
    version = conn.execute("SELECT prompt_version FROM attempts WHERE request_id = %s",
                           (package["request_id"],)).fetchone()[0]  # fmt: skip
    assert version == service.prompt_version()


def test_accepted_after_a_rejection(conn):
    seed(conn)
    package = open_request(conn)
    assert submit(conn, package, solver="raise ValueError('oops')")["status"] == "rejected"
    result = submit(conn, package)
    assert (result["status"], result["attempt"]) == ("accepted", 2)
    assert request_row(conn, package["request_id"])[2] == 2
    assert conn.execute("SELECT attempt_count FROM tasks WHERE task_id = %s", (result["task_id"],)).fetchone()[0] == 2


def test_task_in_russian_skips_flesch_kincaid(conn):
    seed(conn)
    package = open_request(conn, language="ru")
    task = good_task("Аня, Боря и Катя бежали наперегонки. Боря прибежал раньше Кати. Аня прибежала позже Кати. "
                     "Кто прибежал первым?")  # fmt: skip
    task["options"] = {"A": "Аня", "B": "Катя", "C": "Боря", "D": "Никто", "E": "Все сразу"}
    solver = SOLVER.replace('"Ann"', '"Аня"').replace('"Ben"', '"Боря"').replace('"Kim"', '"Катя"')
    solver = solver.replace('"Nobody"', '"Никто"').replace('"All at once"', '"Все сразу"')
    result = submit(conn, package, task=task, solver=solver, language="ru")
    assert result["status"] == "accepted", result
    assert conn.execute("SELECT language FROM tasks WHERE task_id = %s", (result["task_id"],)).fetchone()[0] == "ru"


# Rejections, one reason each


def test_bad_structure_stops_before_the_other_checks(conn):
    seed(conn)
    package = open_request(conn)
    task = good_task()
    task["options"].pop("E")
    result = submit(conn, package, task=task, solver="raise ValueError('never run')")
    assert (result["status"], codes(result), result["attempts_left"]) == ("rejected", ["bad_structure"], 2)
    assert request_row(conn, package["request_id"])[:3] == ("failed", None, 1)  # still open
    assert attempt_rows(conn, package["request_id"]) == [(1, "rejected", "bad_structure", CLIENT)]


def test_topic_and_difficulty_are_fixed_by_the_request(conn):
    seed(conn)
    package = open_request(conn)
    result = submit(conn, package, brief=dict(package["brief"], target_concept="time.clocks"))
    assert codes(result) == ["bad_structure"]
    assert any("get_next_task" in detail for detail in result["reasons"][0]["details"])


def test_student_restrictions_must_stay_in_the_brief(conn):
    seed(conn, "masha")  # masha may not use division_with_remainder and fractions
    package = open_request(conn, "masha")
    result = submit(conn, package, brief=dict(package["brief"], excluded_skills=[]))
    assert codes(result) == ["bad_structure"]
    assert any("missing" in detail for detail in result["reasons"][0]["details"])


def test_crashing_program_is_a_solver_error(conn):
    seed(conn)
    result = submit(conn, open_request(conn), solver="raise ValueError('oops')")
    assert codes(result) == ["solver_error"]
    assert "ValueError: oops" in result["reasons"][0]["details"][0]


def test_blocking_self_check_rejects(conn):
    seed(conn)
    issue = {"type": "ambiguous", "severity": "blocking", "comment": "Two readings of 'after'."}
    result = submit(conn, open_request(conn), check=good_check(issues=[issue]))
    assert codes(result) == ["self_check_blocking"]


def test_minor_self_check_issue_is_kept(conn):
    seed(conn)
    issue = {"type": "too_hard_for_grade", "severity": "minor", "comment": "Maybe long for grade 3."}
    result = submit(conn, open_request(conn), check=good_check(issues=[issue]))
    assert result["status"] == "accepted" and result["minor_issues"] == [issue]


def test_long_sentence_fails_readability(conn):
    seed(conn)
    result = submit(conn, open_request(conn), task=good_task(LONG_QUESTION))
    assert codes(result) == ["readability"]


def test_copy_of_a_reference_example_is_a_near_duplicate(conn):
    seed(conn)
    thresholds = load_thresholds()
    example = next(task["question"] for task in load_examples()
                   if task["topic"] == "logic.ordering" and readability(task["question"], 4, thresholds).ok)
    result = submit(conn, open_request(conn), task=good_task(example))
    assert codes(result) == ["near_duplicate"]


def test_program_that_finds_another_answer_disagrees(conn):
    seed(conn)
    result = submit(conn, open_request(conn), solver='print(\'["A"]\')')
    assert codes(result) == ["solver_disagrees"]
    assert "['A']" in result["reasons"][0]["details"][0]


def test_self_check_with_another_answer_disagrees(conn):
    seed(conn)
    result = submit(conn, open_request(conn), check=good_check(final="B"))
    assert codes(result) == ["solver_disagrees"]
    assert "self_check" in result["reasons"][0]["details"][0]


def test_every_failed_check_is_reported_and_the_first_is_logged(conn):
    seed(conn)
    package = open_request(conn)
    issue = {"type": "ambiguous", "severity": "blocking", "comment": "Unclear."}
    result = submit(conn, package, task=good_task(LONG_QUESTION), check=good_check(issues=[issue]))
    assert codes(result) == ["self_check_blocking", "readability"]
    assert attempt_rows(conn, package["request_id"])[0][2] == "self_check_blocking"


# Attempts and requests


def test_three_rejections_close_the_request(conn):
    seed(conn)
    package = open_request(conn)
    results = [submit(conn, package, solver="raise ValueError('oops')") for _ in range(3)]
    assert [result["attempts_left"] for result in results] == [2, 1, 0]
    assert "get_next_task" in results[-1]["next"]
    assert request_row(conn, package["request_id"])[:3] == ("failed", None, 3)
    with pytest.raises(service.InvalidRequest, match="used all 3 attempts"):
        submit(conn, package)


def test_closed_and_unknown_requests_are_refused(conn):
    seed(conn)
    package = open_request(conn)
    submit(conn, package)  # accepted: the request is closed
    with pytest.raises(service.InvalidRequest, match="already closed"):
        submit(conn, package)
    with pytest.raises(service.InvalidRequest, match="no request"):
        submit(conn, dict(package, request_id=10**9))


def test_sandbox_outage_counts_no_attempt(conn):
    seed(conn)
    package = open_request(conn)

    def broken(code):
        raise sandbox.SandboxUnavailable("docker is down")

    with pytest.raises(sandbox.SandboxUnavailable):
        submit(conn, package, run_solver=broken)
    assert attempt_rows(conn, package["request_id"]) == []
