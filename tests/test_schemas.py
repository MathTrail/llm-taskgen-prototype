"""Agent JSON schemas (T16): the examples from SPEC 5.1-5.4 pass, broken answers fail, and every schema uses only
keywords that Claude structured outputs support, so the SDK sends it unchanged (D39)."""

import copy
import json
import re

import pytest
from anthropic import transform_schema
from jsonschema import Draft202012Validator

from taskgen import ROOT

SCHEMAS = {"brief": "5.1", "generator": "5.2", "analyst": "5.3", "skeptic": "5.4"}

# Not supported by structured outputs (platform docs, "JSON Schema limitations").
UNSUPPORTED = {
    "minLength", "maxLength", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
    "maxItems", "uniqueItems", "minProperties", "maxProperties", "propertyNames", "patternProperties", "oneOf",
    "not", "if", "then", "else", "nullable", "$schema",
}  # fmt: skip


def load(name):
    return json.loads((ROOT / "schemas" / f"{name}.json").read_text(encoding="utf-8"))


def spec_example(section):
    """The first JSON block after the SPEC heading, e.g. the brief example in 5.1."""
    text = (ROOT / "SPEC.md").read_text(encoding="utf-8")
    start = text.index(f"### {section} ")
    return json.loads(re.search(r"```json\n(.*?)```", text[start:], re.S).group(1))


def errors(name, answer):
    return list(Draft202012Validator(load(name)).iter_errors(answer))


def nodes(schema):
    """Every subschema, the root included."""
    yield schema
    for key, value in schema.items():
        if key in ("properties", "$defs"):
            for child in value.values():
                yield from nodes(child)
        elif key == "items":
            yield from nodes(value)
        elif key in ("anyOf", "allOf"):
            for child in value:
                yield from nodes(child)


# Structured outputs compatibility


@pytest.mark.parametrize("name", SCHEMAS)
def test_schema_is_valid_json_schema(name):
    Draft202012Validator.check_schema(load(name))


@pytest.mark.parametrize("name", SCHEMAS)
def test_schema_uses_only_supported_keywords(name):
    for node in nodes(load(name)):
        assert not UNSUPPORTED & set(node), node
        if node.get("type") == "object":
            assert node.get("additionalProperties") is False, node
        if "minItems" in node:
            assert node["minItems"] in (0, 1), node
        if "$ref" in node:
            assert set(node) == {"$ref"}, node  # siblings of $ref would be dropped
        if "enum" in node:
            assert "type" in node, node


@pytest.mark.parametrize("name", SCHEMAS)
def test_sdk_sends_schema_unchanged(name):
    # transform_schema moves unsupported constraints into descriptions; a compatible schema comes back equal.
    assert transform_schema(load(name)) == load(name)


# Examples from SPEC


@pytest.mark.parametrize(("name", "section"), SCHEMAS.items())
def test_spec_example_passes(name, section):
    assert errors(name, spec_example(section)) == []


@pytest.mark.parametrize(("name", "section"), SCHEMAS.items())
def test_fields_follow_the_spec_order(name, section):
    # The model writes fields in schema order: reasoning comes before the answer, as in SPEC.
    assert list(load(name)["properties"]) == list(spec_example(section))


# Broken answers

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
    "analyst": [
        ("answer F", lambda a: a.update(final_answer="F")),
        ("unsolvable is for the Skeptic", lambda a: a.update(final_answer="UNSOLVABLE")),
        ("no code", lambda a: a.pop("solver_code")),
        ("extra field", lambda a: a.update(confidence=0.9)),
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


def test_skeptic_may_find_the_task_unsolvable_with_no_issues():
    answer = spec_example("5.4") | {"issues": [], "final_answer": "UNSOLVABLE"}
    assert errors("skeptic", answer) == []


def test_generator_distractor_count_is_left_to_the_code():
    # Structured outputs cannot require exactly four keys: the schema accepts five, filters.structure_errors does not.
    answer = spec_example("5.2")
    answer["distractors"]["C"] = {"trap": "off_by_one", "text": "No."}
    assert errors("generator", answer) == []
