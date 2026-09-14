"""Validate the reference tasks in data/examples/tasks.json against schemas/example_task.json (T10, SPEC 4.3).

Run: uv run python -m taskgen.validate_examples. Exit code 1 if any task is invalid.
On success it prints how many tasks each topic has, towards the goal of 3 per topic (T11).
"""

import json
import sys
from collections import Counter

from jsonschema import Draft202012Validator

from taskgen import ROOT
from taskgen.catalogs import load_catalog

EXAMPLES = ROOT / "data" / "examples" / "tasks.json"
TASK_SCHEMA = json.loads((ROOT / "schemas" / "example_task.json").read_text(encoding="utf-8"))
LETTERS = {"A", "B", "C", "D", "E"}
TASKS_PER_TOPIC = 3


def load_examples() -> list[dict]:
    return json.loads(EXAMPLES.read_text(encoding="utf-8"))


def task_errors(task: object, topic_ids: set[str], trap_ids: set[str]) -> list[str]:
    """Schema violations and broken option rules of one task; an empty list means the task is valid."""
    errors = [
        f"{'/'.join(map(str, error.absolute_path)) or '(root)'}: {error.message}"
        for error in Draft202012Validator(TASK_SCHEMA).iter_errors(task)
    ]
    if errors:
        return errors

    if task["topic"] not in topic_ids:
        errors.append(f"topic {task['topic']!r} is not in data/catalogs/topics.json")

    options = [text.strip().lower() for text in task["options"].values()]
    if len(set(options)) != len(options):
        errors.append("options must be 5 different answers")

    wrong = LETTERS - {task["correct_answer"]}
    if set(task["distractors"]) != wrong:
        errors.append(
            f"distractors must cover exactly the wrong options {sorted(wrong)}, got {sorted(task['distractors'])}"
        )
    for letter, distractor in sorted(task["distractors"].items()):
        if distractor["trap"] not in trap_ids:
            errors.append(f"distractors/{letter}: trap {distractor['trap']!r} is not in data/catalogs/traps.json")
    return errors


def examples_errors(tasks: object) -> list[str]:
    """Errors of the whole file, each prefixed with the task id or its position."""
    if not isinstance(tasks, list):
        return ["the file must hold a JSON array of tasks"]

    topic_ids = {entry["id"] for entry in load_catalog("topics")}
    trap_ids = {entry["id"] for entry in load_catalog("traps")}
    errors, seen = [], set()
    for index, task in enumerate(tasks):
        task_id = task.get("id") if isinstance(task, dict) else None
        name = task_id if isinstance(task_id, str) else f"#{index}"
        errors += [f"{name}: {error}" for error in task_errors(task, topic_ids, trap_ids)]
        if isinstance(task_id, str):
            if task_id in seen:
                errors.append(f"{name}: duplicate id")
            seen.add(task_id)
    return errors


def main() -> None:
    try:
        tasks = load_examples()
    except json.JSONDecodeError as error:
        sys.exit(f"{EXAMPLES.relative_to(ROOT)}: invalid JSON: {error}")

    errors = examples_errors(tasks)
    for error in errors:
        print(error)
    if errors:
        sys.exit(1)

    counts = Counter(task["topic"] for task in tasks)
    drafts = Counter(task["topic"] for task in tasks if task.get("draft"))
    for topic in (entry["id"] for entry in load_catalog("topics")):
        note = f" ({drafts[topic]} draft)" if drafts[topic] else ""
        print(f"{topic}: {counts[topic]}/{TASKS_PER_TOPIC}{note}")
    print(f"{len(tasks)} tasks OK, {sum(drafts.values())} of them drafts")


if __name__ == "__main__":
    main()
