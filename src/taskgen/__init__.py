"""Prototype package: an MCP server lets the chat client's model generate olympiad-style math tasks for grades 1-4
(see SPEC.md)."""

from pathlib import Path

# Repository root: data/, schemas/, prompts/, db/ and config.yaml live there, not in the package.
ROOT = Path(__file__).resolve().parents[2]
