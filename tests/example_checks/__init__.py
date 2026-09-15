"""Brute-force answer checks for the reference tasks in data/examples/ (T11).

Each module holds the checks of one topic. A check is registered for one task id and returns the correct answer,
computed by counting, simulation or search rather than copied from the task; tests/test_example_answers.py then
requires that exactly one option matches it and that this option is the task's correct_answer.
"""

import importlib
import pkgutil
from collections.abc import Callable

CHECKS: dict[str, Callable[[], object]] = {}


def check(task_id: str):
    """Register the decorated function as the answer check of one task."""

    def register(function: Callable[[], object]) -> Callable[[], object]:
        if task_id in CHECKS:
            raise ValueError(f"duplicate check for {task_id}")
        CHECKS[task_id] = function
        return function

    return register


def load_checks() -> dict[str, Callable[[], object]]:
    """Import every check module and return all registered checks."""
    for module in pkgutil.iter_modules(__path__):
        importlib.import_module(f"{__name__}.{module.name}")
    return CHECKS
