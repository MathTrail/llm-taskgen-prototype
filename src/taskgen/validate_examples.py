"""Validate the reference tasks in data/examples/<topic>.json against schemas/example_task.json (T10, T11, SPEC 4.3).

Run: uv run python -m taskgen.validate_examples. Exit code 1 if any task is invalid.
On success it prints, per topic and grade level, how many tasks each difficulty 1-5 has (target: 5 per cell, T11).
"""

import json
import sys
from collections import Counter

from jsonschema import Draft202012Validator

from taskgen import ROOT
from taskgen.catalogs import load_catalog

EXAMPLES_DIR = ROOT / "data" / "examples"
TASK_SCHEMA = json.loads((ROOT / "schemas" / "example_task.json").read_text(encoding="utf-8"))
LETTERS = {"A", "B", "C", "D", "E"}
DIFFICULTIES = range(1, 6)
TASKS_PER_CELL = 5


def load_example_files() -> dict[str, object]:
    """Parsed content of every file in data/examples/, keyed by file name; one file per topic."""
    files = {}
    for path in sorted(EXAMPLES_DIR.glob("*.json")):
        try:
            files[path.name] = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"{path.name}: invalid JSON: {error}") from error
    return files


def load_examples() -> list[dict]:
    """All reference tasks from data/examples/, in file order."""
    tasks = []
    for content in load_example_files().values():
        tasks += content if isinstance(content, list) else [content]
    return tasks


def task_errors(task: object, topic_levels: dict[str, list[str]], trap_ids: set[str]) -> list[str]:
    """Schema violations and broken option rules of one task; an empty list means the task is valid."""
    errors = [
        f"{'/'.join(map(str, error.absolute_path)) or '(root)'}: {error.message}"
        for error in Draft202012Validator(TASK_SCHEMA).iter_errors(task)
    ]
    if errors:
        return errors

    if task["topic"] not in topic_levels:
        errors.append(f"topic {task['topic']!r} is not in data/catalogs/topics.json")
    elif task["grade_level"] not in topic_levels[task["topic"]]:
        errors.append(
            f"grade_level {task['grade_level']!r} is not listed for topic {task['topic']!r} in data/catalogs/topics.json"
        )

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
    """Errors of all tasks, each prefixed with the task id or its position."""
    if not isinstance(tasks, list):
        return ["the file must hold a JSON array of tasks"]

    topic_levels = {entry["id"]: entry["grade_levels"] for entry in load_catalog("topics")}
    trap_ids = {entry["id"] for entry in load_catalog("traps")}
    errors, seen = [], set()
    for index, task in enumerate(tasks):
        task_id = task.get("id") if isinstance(task, dict) else None
        name = task_id if isinstance(task_id, str) else f"#{index}"
        errors += [f"{name}: {error}" for error in task_errors(task, topic_levels, trap_ids)]
        if isinstance(task_id, str):
            if task_id in seen:
                errors.append(f"{name}: duplicate id")
            seen.add(task_id)
    return errors


def placement_errors(files: dict[str, object]) -> list[str]:
    """Every file holds an array of tasks of the topic it is named after, e.g. counting.gaps.json."""
    errors = []
    for name, content in files.items():
        if not isinstance(content, list):
            errors.append(f"{name}: the file must hold a JSON array of tasks")
            continue
        topic = name.removesuffix(".json")
        for task in content:
            if isinstance(task, dict) and task.get("topic") != topic:
                errors.append(f"{name}: task {task.get('id')!r} has topic {task.get('topic')!r}, expected {topic!r}")
    return errors


def main() -> None:
    try:
        files = load_example_files()
    except ValueError as error:
        sys.exit(str(error))

    tasks = load_examples()
    errors = placement_errors(files) + examples_errors(tasks)
    for error in errors:
        print(error)
    if errors:
        sys.exit(1)

    cells = Counter((task["topic"], task["grade_level"], task["difficulty"]) for task in tasks)
    print(f"tasks per difficulty {DIFFICULTIES.start}-{DIFFICULTIES.stop - 1}, target {TASKS_PER_CELL} each:")
    for topic in load_catalog("topics"):
        levels = [
            f"{level}: " + " ".join(str(cells[(topic["id"], level, difficulty)]) for difficulty in DIFFICULTIES)
            for level in topic["grade_levels"]
        ]
        print(f"  {topic['id']}  " + "  |  ".join(levels))
    print(f"{len(tasks)} tasks OK in {len(files)} files")


if __name__ == "__main__":
    main()
