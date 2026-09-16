"""Answer checks for T11: every reference task has a brute-force check that matches exactly its correct option."""

import pytest

from example_checks import load_checks
from taskgen.validate_examples import load_examples

TASKS = load_examples()
CHECKS = load_checks()


def normalize(value: object) -> str:
    return str(value).strip().lower()


def test_every_task_has_a_check():
    assert sorted({task["id"] for task in TASKS} - set(CHECKS)) == []


def test_every_check_has_a_task():
    assert sorted(set(CHECKS) - {task["id"] for task in TASKS}) == []


@pytest.mark.parametrize("task", TASKS, ids=lambda task: task["id"])
def test_check_matches_exactly_the_correct_option(task):
    expected = normalize(CHECKS[task["id"]]())
    matching = [letter for letter, text in sorted(task["options"].items()) if normalize(text) == expected]
    assert matching == [task["correct_answer"]], f"check gives {expected!r}"
