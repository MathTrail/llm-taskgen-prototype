"""Rule tutor (T17): expected topic and goal on the seed profiles, a valid and repeatable brief, trap and topic rules."""

import copy
import json

import pytest
from jsonschema import Draft202012Validator

from taskgen import ROOT
from taskgen.catalogs import load_catalog
from taskgen.db import load_student
from taskgen.rating import corridor, load_params, replay_history
from taskgen.seed import SEED_DIR, seed_student
from taskgen.tutor_rule import TRAP_COUNT, example_traps, make_brief

PARAMS = load_params()
BRIEF_SCHEMA = json.loads((ROOT / "schemas" / "brief.json").read_text(encoding="utf-8"))
TRAPS = {entry["id"] for entry in load_catalog("traps")}

# Topic catalog order: ordering, knights_liars (3-4 only), enumeration, gaps, clocks, calendar, pigeonhole, parity,
# tricks, weighing_pouring (3-4 only). Setting: interests[history rows % number of interests].
EXPECTED = {
    "dima": ("combinatorics.enumeration", "new_topic", "trains"),  # grade 1: knights_liars is skipped
    "masha": ("time.clocks", "reinforce", "robots"),  # two failures, the last one in clocks
    "olya": ("logic.ordering", "new_topic", "drawing"),
    "petya": ("time.clocks", "new_topic", "football"),  # the first never-given unmastered topic
    "sasha": ("logic.ordering", "new_topic", "music"),  # new student, empty history
}


def from_profile(profile):
    """The student as db.load_student(history_limit=None) returns it, built from a profile without the database."""
    ratings = replay_history(profile["history"], PARAMS)
    return {
        "student_id": profile["id"],
        "grade": profile["grade"],
        "interests": profile["interests"],
        "cognitive_profile": profile["cognitive_profile"],
        "mastered_topics": profile["mastered_topics"],
        "excluded_skills": profile["excluded_skills"],
        "consecutive_failures": profile["consecutive_failures"],
        "rating": ratings.theta,
        "answers_count": ratings.answers,
        "topic_ratings": {topic: {"offset": delta, "answers_count": n} for topic, (delta, n) in ratings.topics.items()},
        "history": [dict(row, trap_hit=row.get("trap_hit")) for row in profile["history"]],
    }


def seed(name):
    return from_profile(json.loads((SEED_DIR / f"{name}.json").read_text(encoding="utf-8")))


def student(grade=3, history=(), consecutive_failures=0, mastered=(), interests=("space", "robots")):
    return from_profile({
        "id": "test", "grade": grade, "interests": list(interests), "cognitive_profile": [],
        "mastered_topics": list(mastered), "excluded_skills": ["fractions"],
        "consecutive_failures": consecutive_failures, "history": list(history),
    })  # fmt: skip


def row(topic, correct=True, trap=None):
    return {"topic": topic, "difficulty": 2, "correct": correct} | ({"trap_hit": trap} if trap else {})


# Seed profiles


@pytest.mark.parametrize("name", EXPECTED)
def test_seed_profile_topic_goal_and_setting(name):
    brief = make_brief(seed(name), PARAMS)
    assert (brief["target_concept"], brief["pedagogical_goal"], brief["setting"]) == EXPECTED[name]


@pytest.mark.parametrize("name", EXPECTED)
def test_seed_brief_is_valid(name):
    profile = seed(name)
    brief = make_brief(profile, PARAMS)
    assert list(Draft202012Validator(BRIEF_SCHEMA).iter_errors(brief)) == []
    assert len(brief["traps_to_use"]) == TRAP_COUNT and set(brief["traps_to_use"]) <= TRAPS
    assert brief["excluded_skills"] == profile["excluded_skills"]
    level = profile["rating"] + profile["topic_ratings"].get(brief["target_concept"], {"offset": 0})["offset"]
    assert brief["difficulty"] == corridor(level, PARAMS.corridor).recommended


@pytest.mark.parametrize("name", EXPECTED)
def test_brief_is_repeatable(name):
    profile = seed(name)
    assert make_brief(profile, PARAMS) == make_brief(copy.deepcopy(profile), PARAMS)


def test_masha_gets_example_traps_for_clocks():
    # Her only trap_hit is in enumeration, so the clocks traps come from the grade 3-4 clocks examples.
    assert make_brief(seed("masha"), PARAMS)["traps_to_use"] == list(example_traps("time.clocks", "3-4")[:TRAP_COUNT])


# Goal and topic


def test_did_not_understand_is_a_failure_too():
    brief = make_brief(student(history=[row("time.clocks"), row("time.calendar", correct=None)],
                               consecutive_failures=1), PARAMS)
    assert (brief["pedagogical_goal"], brief["target_concept"]) == ("reinforce", "time.calendar")


def test_topic_given_longest_ago_when_all_were_given():
    topics = [entry["id"] for entry in load_catalog("topics")]
    order = topics[3:] + topics[:3]  # the first three catalog topics were given most recently
    brief = make_brief(student(history=[row(topic) for topic in order]), PARAMS)
    assert brief["target_concept"] == order[0]


def test_mastered_topics_are_skipped():
    brief = make_brief(student(mastered=["logic.ordering", "logic.knights_liars"]), PARAMS)
    assert brief["target_concept"] == "combinatorics.enumeration"
    assert "mastered_topics" in brief["profile_fields_used"]


def test_all_topics_mastered_falls_back_to_all():
    topics = [entry["id"] for entry in load_catalog("topics")]
    assert make_brief(student(mastered=topics), PARAMS)["target_concept"] == "logic.ordering"


# Traps and setting


def test_own_traps_come_first_by_frequency_then_recency():
    history = [
        row("counting.gaps", False, "missed_case"),
        row("counting.gaps", False, "off_by_one"),
        row("counting.gaps", False, "off_by_one"),
        row("counting.gaps", False, "double_count"),
    ]
    brief = make_brief(student(history=history, consecutive_failures=4), PARAMS)
    assert brief["traps_to_use"] == ["off_by_one", "double_count"]  # double_count is more recent than missed_case


def test_one_own_trap_is_topped_up_from_examples():
    brief = make_brief(student(history=[row("counting.gaps", False, "trusted_statement")], consecutive_failures=1),
                       PARAMS)
    top_up = next(trap for trap in example_traps("counting.gaps", "3-4") if trap != "trusted_statement")
    assert brief["traps_to_use"] == ["trusted_statement", top_up]


def test_setting_goes_round_the_interests():
    settings = [make_brief(student(history=[row("logic.ordering")] * n, interests=("a", "b", "c")), PARAMS)["setting"]
                for n in range(4)]
    assert settings == ["a", "b", "c", "a"]


def test_student_without_interests_is_reported():
    with pytest.raises(ValueError):
        make_brief(student(interests=()), PARAMS)


# From the database


def test_brief_from_the_database_matches(conn):
    profile = json.loads((SEED_DIR / "petya.json").read_text(encoding="utf-8"))
    seed_student(conn, profile, PARAMS)
    from_db = make_brief(load_student(conn, "petya", history_limit=None), PARAMS)
    assert from_db == make_brief(from_profile(profile), PARAMS)
