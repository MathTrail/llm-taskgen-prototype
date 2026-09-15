"""JSON schemas of the brief, the task and the self-check (T16, D42): the examples from SPEC 5.1, 5.2 and 5.4 pass,
broken answers fail. The MCP server checks what the client's model hands in against these schemas."""

import copy
import json
import re

import pytest
from jsonschema import Draft202012Validator

from taskgen import ROOT

SCHEMAS = {"brief": "5.1", "generator": "5.2", "skeptic": "5.4"}


def load(name):
    return json.loads((ROOT / "schemas" / f"{name}.json").read_text(encoding="utf-8"))


def spec_example(section):
    """The first JSON block after the SPEC heading, e.g. the brief example in 5.1."""
    text = (ROOT / "SPEC.md").read_text(encoding="utf-8")
    start = text.index(f"### {section} ")
    return json.loads(re.search(r"```json\n(.*?)```", text[start:], re.S).group(1))


def errors(name, answer):
    return list(Draft202012Validator(load(name)).iter_errors(answer))


@pytest.mark.parametrize("name", SCHEMAS)
def test_schema_is_valid_json_schema(name):
    Draft202012Validator.check_schema(load(name))


@pytest.mark.parametrize(("name", "section"), SCHEMAS.items())
def test_spec_example_passes(name, section):
    assert errors(name, spec_example(section)) == []


@pytest.mark.parametrize(("name", "section"), SCHEMAS.items())
def test_fields_follow_the_spec_order(name, section):
    # Reasoning comes before the answer, as in SPEC.
    assert list(load(name)["properties"]) == list(spec_example(section))


BROKEN = {
    "brief": [
        ("unknown goal", lambda a: a.update(pedagogical_goal="teach")),
        ("difficulty 6", lambda a: a.update(difficulty=6)),
        ("difficulty as text", lambda a: a.update(difficulty="2")),
        ("no rationale", lambda a: a.pop("rationale")),
        ("extra field", lambda a: a.update(topic="combinatorics.enumeration")),
        ("no traps", lambda a: a.update(traps_to_use=[])),
        ("unknown profile field", lambda a: a["profile_fields_used"].append("age")),
    ],
    "generator": [
        ("no hint", lambda a: a.pop("hint")),
        ("four options", lambda a: a["options"].pop("E")),
        ("sixth option", lambda a: a["options"].update(F="16")),
        ("answer F", lambda a: a.update(correct_answer="F")),
        ("distractor without text", lambda a: a["distractors"]["B"].pop("text")),
        ("distractor for F", lambda a: a["distractors"].update(F={"trap": "off_by_one", "text": "No."})),
        ("option as number", lambda a: a["options"].update(A=4)),
    ],
    "skeptic": [
        ("unknown issue type", lambda a: a["issues"][0].update(type="typo")),
        ("unknown severity", lambda a: a["issues"][0].update(severity="major")),
        ("issue without comment", lambda a: a["issues"][0].pop("comment")),
        ("option check without E", lambda a: a["option_check"].pop("E")),
        ("answer maybe", lambda a: a.update(final_answer="maybe")),
        ("no issues list", lambda a: a.pop("issues")),
    ],
}


@pytest.mark.parametrize(
    ("name", "change"),
    [(name, change) for name, cases in BROKEN.items() for _, change in cases],
    ids=[f"{name}: {label}" for name, cases in BROKEN.items() for label, _ in cases],
)
def test_broken_answer_fails(name, change):
    answer = copy.deepcopy(spec_example(SCHEMAS[name]))
    change(answer)
    assert errors(name, answer)


def test_self_check_may_find_the_task_unsolvable_with_no_issues():
    answer = spec_example("5.4") | {"issues": [], "final_answer": "UNSOLVABLE"}
    assert errors("skeptic", answer) == []


def test_generator_distractor_count_is_left_to_the_code():
    # A schema cannot require exactly four keys: it accepts five, filters.structure_errors does not.
    answer = spec_example("5.2")
    answer["distractors"]["C"] = {"trap": "off_by_one", "text": "No."}
    assert errors("generator", answer) == []
