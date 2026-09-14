"""Catalog checks for T08: the real catalogs are valid and match SPEC; broken catalogs are rejected."""

import copy

import pytest

from scripts.validate_catalogs import CATALOGS, catalog_errors, load_catalog

# Topics are a closed list fixed by SPEC 4.2: adding one is a SPEC change.
SPEC_TOPICS = {
    "logic.ordering",
    "logic.knights_liars",
    "combinatorics.enumeration",
    "counting.gaps",
    "time.clocks",
    "time.calendar",
    "pigeonhole.basic",
    "parity.alternation",
    "arithmetic.tricks",
    "algorithms.weighing_pouring",
}
# Traps and skills are starting sets the author extends, so only the SPEC ids are required.
SPEC_TRAPS = {"off_by_one", "missed_case", "double_count", "ignored_not", "answered_other_question", "stopped_early"}
SPEC_SKILLS = {"multiplication", "division_with_remainder", "fractions"}  # used in SPEC 4.1 and 4.4


def ids(name):
    return {entry["id"] for entry in load_catalog(name)}


@pytest.mark.parametrize("name", CATALOGS)
def test_catalog_is_valid(name):
    assert catalog_errors(name, load_catalog(name)) == []


def test_topics_match_spec():
    assert ids("topics") == SPEC_TOPICS


def test_excluded_topic_is_absent():
    assert "patterns.sequences" not in ids("topics")  # SPEC 4.2, decision D05


def test_traps_include_spec():
    assert ids("traps") >= SPEC_TRAPS


def test_skills_include_spec():
    assert ids("skills") >= SPEC_SKILLS


def broken(name, change):
    entries = copy.deepcopy(load_catalog(name))
    change(entries)
    return catalog_errors(name, entries)


def test_duplicate_id_is_rejected():
    errors = broken("traps", lambda entries: entries.append(dict(entries[0])))
    assert any("duplicate id 'off_by_one'" in error for error in errors)


def test_unknown_grade_level_is_rejected():
    assert broken("topics", lambda entries: entries[0].update(grade_levels=["5-6"]))


def test_empty_grade_levels_are_rejected():
    assert broken("topics", lambda entries: entries[0].update(grade_levels=[]))


def test_missing_description_is_rejected():
    assert broken("skills", lambda entries: entries[0].pop("description"))


def test_extra_field_is_rejected():
    assert broken("traps", lambda entries: entries[0].update(text="free text"))


def test_topic_id_without_area_is_rejected():
    assert broken("topics", lambda entries: entries[0].update(id="ordering"))


def test_id_with_spaces_is_rejected():
    assert broken("skills", lambda entries: entries[0].update(id="simple fractions"))
