"""Reference task checks for T10: the real file is valid and broken tasks are rejected."""

import copy

import pytest

from taskgen.validate_examples import examples_errors, load_example_files, load_examples, placement_errors

# A fixed valid task, so the tests do not depend on the reference tasks in data/examples/.
VALID = {
    "id": "gaps-posts-test",
    "topic": "counting.gaps",
    "grade_level": "1-2",
    "difficulty": 3,
    "question": "A fence has 4 posts in a row, 1 metre apart. How long is the fence?",
    "options": {"A": "1", "B": "3", "C": "4", "D": "5", "E": "8"},
    "correct_answer": "B",
    "solution": "4 posts have 3 gaps of 1 metre: 3 metres.",
    "distractors": {
        "A": {"trap": "answered_other_question", "text": "1 metre is one gap."},
        "C": {"trap": "off_by_one", "text": "4 posts have 3 gaps, not 4."},
        "D": {"trap": "off_by_one", "text": "4 posts have 3 gaps, not 5."},
        "E": {"trap": "double_count", "text": "Each gap counts once."},
    },
}


def errors_after(change):
    task = copy.deepcopy(VALID)
    change(task)
    return examples_errors([task])


def test_real_examples_are_valid():
    assert examples_errors(load_examples()) == []


def test_real_files_hold_their_topic():
    assert placement_errors(load_example_files()) == []


def test_task_in_wrong_file_is_rejected():
    errors = placement_errors({"time.clocks.json": [VALID]})
    assert any("expected 'time.clocks'" in error for error in errors)


def test_grade_level_outside_topic_levels_is_rejected():
    # logic.knights_liars is listed for grades 3-4 only; VALID is a 1-2 task.
    errors = errors_after(lambda task: task.update(topic="logic.knights_liars"))
    assert any("grade_level" in error for error in errors)


def test_valid_task_passes():
    assert examples_errors([VALID]) == []


def test_draft_flag_is_allowed():
    assert errors_after(lambda task: task.update(draft=True)) == []


def test_source_is_allowed():
    assert errors_after(lambda task: task.update(source="Author, Book title, 1950, problem 12")) == []


def test_empty_source_is_rejected():
    assert errors_after(lambda task: task.update(source=""))


def test_file_must_be_an_array():
    assert examples_errors(VALID) == ["the file must hold a JSON array of tasks"]


def test_same_options_are_rejected():
    errors = errors_after(lambda task: task["options"].update(E="3 "))
    assert any("5 different answers" in error for error in errors)


def test_missing_option_is_rejected():
    assert errors_after(lambda task: task["options"].pop("E"))


def test_distractor_on_correct_answer_is_rejected():
    def change(task):
        task["distractors"]["B"] = task["distractors"].pop("E")

    errors = errors_after(change)
    assert any("wrong options" in error for error in errors)


def test_three_distractors_are_rejected():
    assert errors_after(lambda task: task["distractors"].pop("E"))


def test_distractor_without_text_is_rejected():
    assert errors_after(lambda task: task["distractors"]["A"].pop("text"))


def test_unknown_trap_is_rejected():
    errors = errors_after(lambda task: task["distractors"]["A"].update(trap="forgot_a_case"))
    assert any("forgot_a_case" in error for error in errors)


def test_unknown_topic_is_rejected():
    errors = errors_after(lambda task: task.update(topic="patterns.sequences"))
    assert any("patterns.sequences" in error for error in errors)


@pytest.mark.parametrize(
    "field, value",
    [("grade_level", "5-6"), ("difficulty", 6), ("correct_answer", "F"), ("question", "")],
)
def test_bad_field_value_is_rejected(field, value):
    assert errors_after(lambda task: task.update({field: value}))


def test_extra_field_is_rejected():
    assert errors_after(lambda task: task.update(answer="B"))


def test_duplicate_id_is_rejected():
    errors = examples_errors([VALID, copy.deepcopy(VALID)])
    assert any("duplicate id" in error for error in errors)
