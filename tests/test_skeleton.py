"""Skeleton checks: package modules import and config.yaml has the keys from SPEC 8."""

import importlib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
MODULES = ["tutor_rule", "rating", "sandbox", "db", "seed", "catalogs", "apply_schema", "validate_examples", "filters",
           "service", "mcp_server", "journal", "play"]


def load_config():
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name):
    module = importlib.import_module(f"taskgen.{name}")
    assert module.__doc__


def test_config_has_spec_keys():
    config = load_config()
    assert config["max_attempts"] == 3
    assert {"fast_below_sec", "struggled_above_sec"} <= set(config["pace"])
    assert {"k0_student", "k0_topic", "k0_task", "decay", "corridor"} <= set(config["rating"])
    assert {"image", "timeout_sec", "memory_mb", "cpus"} <= set(config["sandbox"])
    assert {"max_grade_margin", "max_sentence_words"} <= set(config["readability"])
    assert "max_similarity" in config["near_duplicate"]


def test_no_llm_api_settings():
    # The client's model writes the tasks; the prototype makes no LLM API calls of its own (D42).
    assert not {"agents", "llm", "prices"} & set(load_config())
