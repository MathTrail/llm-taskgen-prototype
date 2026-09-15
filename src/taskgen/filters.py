"""Cheap checks of a generated task without an LLM (SPEC 6, conditions 1, 5 and 6; D38).

- structure_errors: five different options, distractors for exactly the four wrong options, a hint, known trap ids;
- readability: Flesch-Kincaid grade and the longest sentence of the question against the student's grade;
- near_duplicate: pg_trgm similarity of the question to the bank tasks and to the reference examples.
Thresholds are in config.yaml.
"""

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import psycopg
import textstat
import yaml

from taskgen import ROOT
from taskgen.catalogs import load_catalog
from taskgen.db import grade_level, similar_tasks, similarities
from taskgen.validate_examples import load_examples

OPTIONS = ("A", "B", "C", "D", "E")


@dataclass(frozen=True)
class Thresholds:
    max_grade_margin: float  # Flesch-Kincaid grade at most the student's grade plus this
    max_sentence_words: dict[str, int]  # longest sentence of the question, by grade level
    max_similarity: float  # pg_trgm similarity at or above this is a near duplicate


def load_thresholds(path: Path = ROOT / "config.yaml") -> Thresholds:
    """The readability and near_duplicate sections of config.yaml."""
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    readability = config["readability"]
    return Thresholds(
        readability["max_grade_margin"],
        dict(readability["max_sentence_words"]),
        config["near_duplicate"]["max_similarity"],
    )


# Structure (condition 1)


@lru_cache(maxsize=None)
def trap_ids() -> frozenset[str]:
    return frozenset(entry["id"] for entry in load_catalog("traps"))


def structure_errors(task: dict) -> list[str]:
    """What breaks the rules of SPEC 6, condition 1, that a JSON schema cannot express; an empty list means fine."""
    errors = []
    options = task.get("options") or {}
    if sorted(options) != list(OPTIONS):
        errors.append(f"options must be exactly A-E, got {sorted(options)}")
    values = [str(value).strip().lower() for value in options.values()]
    if any(not value for value in values):
        errors.append("an option is empty")
    elif len(set(values)) != len(values):
        repeated = sorted({value for value in values if values.count(value) > 1})
        errors.append(f"options must all differ, repeated: {repeated}")

    correct = task.get("correct_answer")
    if correct not in OPTIONS:
        errors.append(f"correct_answer must be one of A-E, got {correct!r}")
    distractors = task.get("distractors") or {}
    wrong = sorted(set(OPTIONS) - {correct})
    if sorted(distractors) != wrong:
        errors.append(f"distractors must cover exactly the wrong options {wrong}, got {sorted(distractors)}")
    for letter, distractor in sorted(distractors.items()):
        if not str(distractor.get("text", "")).strip():
            errors.append(f"distractor {letter} has no text")
        if distractor.get("trap") not in trap_ids():
            errors.append(f"distractor {letter}: trap {distractor.get('trap')!r} is not in data/catalogs/traps.json")

    if not str(task.get("hint") or "").strip():
        errors.append("hint is empty")
    return errors


# Readability (condition 5)


def sentences(text: str) -> list[str]:
    return [sentence for sentence in re.split(r"(?<=[.!?])\s+", text.strip()) if sentence]


@dataclass(frozen=True)
class Readability:
    fk_grade: float
    longest_sentence: str
    longest_sentence_words: int
    max_fk_grade: float
    max_sentence_words: int
    problems: list[str] = field(default_factory=list)  # for the log and the Generator's retry prompt

    @property
    def ok(self) -> bool:
        return not self.problems


def readability(question: str, grade: int, thresholds: Thresholds) -> Readability:
    """Flesch-Kincaid grade and the longest sentence of the question against a student of this grade."""
    fk_grade = textstat.flesch_kincaid_grade(question)
    longest = max(sentences(question), key=lambda sentence: len(sentence.split()), default="")
    words = len(longest.split())
    max_fk_grade = grade + thresholds.max_grade_margin
    max_words = thresholds.max_sentence_words[grade_level(grade)]
    problems = []
    if fk_grade > max_fk_grade:
        problems.append(f"Flesch-Kincaid grade {fk_grade:.1f} is above {max_fk_grade} for grade {grade}")
    if words > max_words:
        problems.append(f"the longest sentence has {words} words, more than {max_words}: {longest!r}")
    return Readability(fk_grade, longest, words, max_fk_grade, max_words, problems)


# Near duplicates (condition 6)


@dataclass(frozen=True)
class Duplicate:
    source: str  # "bank" or "example"
    id: str  # task_id or example id
    question: str
    similarity: float


@lru_cache(maxsize=None)
def example_questions() -> tuple[tuple[str, str], ...]:
    """(id, question) of every reference example in data/examples/."""
    return tuple((task["id"], task["question"]) for task in load_examples())


def near_duplicate(
    conn: psycopg.Connection, question: str, max_similarity: float, examples: tuple[tuple[str, str], ...] | None = None
) -> Duplicate | None:
    """The most similar bank task or reference example with similarity >= max_similarity, or None.

    The examples are not in the database: their texts go into the same pg_trgm similarity() call.
    """
    found = []
    bank = similar_tasks(conn, question, max_similarity, limit=1)
    if bank:
        found.append(Duplicate("bank", bank[0]["task_id"], bank[0]["question"], bank[0]["similarity"]))
    examples = example_questions() if examples is None else examples
    scores = similarities(conn, question, [text for _, text in examples])
    if scores:
        best = max(range(len(scores)), key=scores.__getitem__)
        if scores[best] >= max_similarity:
            found.append(Duplicate("example", examples[best][0], examples[best][1], scores[best]))
    return max(found, key=lambda duplicate: duplicate.similarity, default=None)
