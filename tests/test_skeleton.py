"""Skeleton checks for T06: package modules import and config.yaml has every key from SPEC 8."""

import importlib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
MODULES = ["main", "agents", "tutor_rule", "rating", "sandbox", "llm", "db", "seed", "catalogs", "apply_schema", "validate_examples"]


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name):
    module = importlib.import_module(f"taskgen.{name}")
    assert module.__doc__


def test_config_has_spec_keys():
    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))

    assert set(config["agents"]) == {"tutor", "generator", "analyst", "skeptic"}
    for agent in config["agents"].values():
        assert agent["provider"] == "anthropic"
        assert "temperature" not in agent  # rejected by Opus 5 / Sonnet 5, SPEC 5.3

    assert config["max_attempts"] == 3
    assert {"fast_below_sec", "struggled_above_sec"} <= set(config["pace"])
    assert {"k0_student", "k0_topic", "k0_task", "decay", "corridor"} <= set(config["rating"])
    assert {"image", "timeout_sec", "memory_mb", "cpus"} <= set(config["sandbox"])
    assert "max_grade_margin" in config["readability"]
    assert "max_similarity" in config["near_duplicate"]
