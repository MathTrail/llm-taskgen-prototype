"""filters.py (T15): structure of the Generator's JSON, readability for grades 1 and 4, near duplicates via pg_trgm."""

import pytest

from taskgen import db, filters

THRESHOLDS = filters.Thresholds(max_grade_margin=3, max_sentence_words={"1-2": 20, "3-4": 25}, max_similarity=0.6)

SIMPLE = "Masha has 3 red balls and 2 blue balls. How many balls does she have?"  # FK -0.1, longest 9 words
HARDER_WORDS = (  # FK 5.4, longest 14 words
    "A caterpillar crawls along a wooden fence. Every morning it climbs three metres, and every evening "
    "it slides down one metre. When does it reach the top?"
)
LONG_SENTENCE = (  # FK 3.5, longest 23 words
    "Tom and his little sister Ann walk to the big park by the river and see a lot of ducks and geese there. "
    "How many birds do they see?"
)
VERY_LONG_SENTENCE = (  # FK 4.1, longest 27 words
    "Tom and his little sister Ann walk to the big park by the river and they see a lot of ducks and a lot of "
    "geese there. How many birds do they see?"
)
HARD = (  # FK 11.5
    "Every afternoon seven classmates exchange colourful postcards. Each classmate sends exactly one postcard to "
    "every other classmate. How many postcards are delivered altogether?"
)
SPACESHIPS = "Four spaceships dock in pairs. How many different pairs can they make?"
SPACESHIPS_AGAIN = "Four spaceships dock in pairs. How many different pairs can the ships make?"
CLOCK = "A clock strikes 3 times at three o'clock. How long does it strike at six o'clock?"


def generated():
    return {
        "core_idea": "Unordered pairs among 4 objects: 6.",
        "design_thought_process": "Plot: docking.",
        "question": SPACESHIPS,
        "options": {"A": "4", "B": "5", "C": "6", "D": "8", "E": "12"},
        "correct_answer": "C",
        "solution": "List the pairs: 6.",
        "hint": "How many ships can the first ship dock with?",
        "distractors": {
            "A": {"trap": "number_from_text", "text": "4 is the number of ships."},
            "B": {"trap": "missed_case", "text": "You missed one pair."},
            "D": {"trap": "wrong_operation", "text": "You doubled the number of ships."},
            "E": {"trap": "double_count", "text": "You counted every pair twice."},
        },
    }


# Structure (SPEC 6, condition 1)


def test_valid_task_has_no_structure_errors():
    assert filters.structure_errors(generated()) == []


def set_options(task, **values):
    task["options"].update(values)


@pytest.mark.parametrize(
    ("change", "fragment"),
    [
        (lambda task: set_options(task, B=" 6 "), "repeated"),
        (lambda task: task.update(options={"A": "four", "B": "Four", "C": "6", "D": "8", "E": "12"}), "repeated"),
        (lambda task: set_options(task, E="  "), "empty"),
        (lambda task: task["options"].pop("E"), "exactly A-E"),
        (lambda task: task.update(correct_answer="F"), "correct_answer"),
        (lambda task: task["distractors"].pop("A"), "wrong options"),
        (lambda task: task["distractors"].update(C={"trap": "off_by_one", "text": "Right answer."}), "wrong options"),
        (lambda task: task.update(correct_answer="B"), "wrong options"),  # B has a distractor, C has none
        (lambda task: task.update(hint="   "), "hint"),
        (lambda task: task.pop("hint"), "hint"),
        (lambda task: task["distractors"]["B"].update(trap="forgot_a_case"), "forgot_a_case"),
        (lambda task: task["distractors"]["D"].update(text=""), "no text"),
    ],
    ids=[
        "same after strip", "same ignoring case", "empty option", "four options", "unknown correct letter",
        "missing distractor", "distractor for the correct option", "correct option has a distractor",
        "blank hint", "no hint", "unknown trap", "empty distractor text",
    ],
)
def test_broken_structure_is_reported(change, fragment):
    task = generated()
    change(task)
    errors = filters.structure_errors(task)
    assert errors and any(fragment in error for error in errors), errors


# Readability (SPEC 6, condition 5)


def test_config_thresholds():
    assert filters.load_thresholds() == THRESHOLDS


def test_sentences():
    assert filters.sentences("One two. Three? Four!  Five") == ["One two.", "Three?", "Four!", "Five"]


@pytest.mark.parametrize("grade", [1, 2, 3, 4])
def test_simple_text_fits_every_grade(grade):
    result = filters.readability(SIMPLE, grade, THRESHOLDS)
    assert result.ok and result.problems == []
    assert result.max_fk_grade == grade + 3


def test_harder_words_fit_grade_4_but_not_grade_1():
    first = filters.readability(HARDER_WORDS, 1, THRESHOLDS)
    assert not first.ok and "Flesch-Kincaid" in first.problems[0]
    assert 4 < first.fk_grade <= 7
    assert filters.readability(HARDER_WORDS, 4, THRESHOLDS).ok


def test_long_sentence_fits_grade_4_but_not_grade_1():
    first = filters.readability(LONG_SENTENCE, 1, THRESHOLDS)
    assert (first.longest_sentence_words, first.max_sentence_words) == (23, 20)
    assert first.problems == [f"the longest sentence has 23 words, more than 20: {first.longest_sentence!r}"]
    fourth = filters.readability(LONG_SENTENCE, 4, THRESHOLDS)
    assert fourth.ok and fourth.max_sentence_words == 25


def test_very_long_sentence_fails_grade_4():
    result = filters.readability(VERY_LONG_SENTENCE, 4, THRESHOLDS)
    assert result.longest_sentence_words == 27
    assert not result.ok and "27 words" in result.problems[0]


def test_hard_text_fails_grade_4():
    result = filters.readability(HARD, 4, THRESHOLDS)
    assert result.fk_grade > 7 and not result.ok


# Near duplicates (SPEC 6, condition 6), on the test database from conftest.py


def bank_task(conn, question):
    task = generated()
    task["question"] = question
    brief = {
        "rationale": "Test.", "pedagogical_goal": "reinforce", "target_concept": "combinatorics.enumeration",
        "difficulty": 3, "setting": "space", "traps_to_use": [], "constraints": [], "excluded_skills": [],
        "profile_fields_used": [],
    }  # fmt: skip
    return db.save_task(conn, brief=brief, task=task, analyst={"final_answer": "C"}, skeptic={"final_answer": "C"},
                        grade_level="3-4", attempt_count=1, rating=0.0)


def test_near_duplicate_in_the_bank(conn):
    task_id = bank_task(conn, SPACESHIPS)
    bank_task(conn, CLOCK)
    found = filters.near_duplicate(conn, SPACESHIPS_AGAIN, 0.6, examples=())
    assert (found.source, found.id, found.question) == ("bank", task_id, SPACESHIPS)
    assert 0.6 <= found.similarity < 1


def test_near_duplicate_among_examples(conn):
    examples = (("ex-1", CLOCK), ("ex-2", SPACESHIPS))
    found = filters.near_duplicate(conn, SPACESHIPS_AGAIN, 0.6, examples=examples)
    assert (found.source, found.id) == ("example", "ex-2")


def test_different_text_is_no_duplicate(conn):
    bank_task(conn, SPACESHIPS)
    examples = (("ex-1", CLOCK),)
    assert filters.near_duplicate(conn, "Five robots shake hands in pairs. How many handshakes are there?", 0.6,
                                  examples=examples) is None


def test_the_closest_of_bank_and_examples_wins(conn):
    bank_task(conn, SPACESHIPS_AGAIN)  # identical to the question
    found = filters.near_duplicate(conn, SPACESHIPS_AGAIN, 0.6, examples=(("ex-2", SPACESHIPS),))
    assert found.source == "bank" and found.similarity == pytest.approx(1.0)


def test_reference_examples_are_checked_by_default(conn):
    assert len(filters.example_questions()) == 450
    example_id, question = filters.example_questions()[0]
    found = filters.near_duplicate(conn, question.replace("?", " now?"), 0.6)
    assert (found.source, found.id) == ("example", example_id)
