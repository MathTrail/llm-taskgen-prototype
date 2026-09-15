"""Start a student chat for a live run (T23): Claude Code in an empty folder with only the taskgen MCP server.

The folder has no CLAUDE.md and no project files, so the model acts as the coach from prompts/, not as a coding
assistant, and cannot open the reference answers. The taskgen tools run without permission prompts; file, shell and
web tools are off.

Run: uv run python -m taskgen.play [--dir ~/taskgen-play] [-- more claude arguments, e.g. --model opus]
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from taskgen import ROOT

TOOLS = ("get_student_profile", "get_progress", "get_next_task", "submit_task", "submit_answer")
DENIED = ("Bash", "Edit", "Write", "NotebookEdit", "Read", "Glob", "Grep", "WebFetch", "WebSearch")
SESSION_PROMPT = ROOT / "prompts" / "play_session.md"


def mcp_config() -> str:
    """The taskgen server as Claude Code should start it from any folder."""
    command = ["run", "--project", str(ROOT), "python", "-m", "taskgen.mcp_server"]
    return json.dumps({"mcpServers": {"taskgen": {"type": "stdio", "command": "uv", "args": command}}})


def claude_args(extra: list[str]) -> list[str]:
    return [
        "claude",
        "--strict-mcp-config",
        "--mcp-config", mcp_config(),
        "--allowedTools", " ".join(f"mcp__taskgen__{tool}" for tool in TOOLS),
        "--disallowedTools", " ".join(DENIED),
        "--append-system-prompt", SESSION_PROMPT.read_text(encoding="utf-8"),
        *extra,
    ]  # fmt: skip


def main() -> None:
    parser = argparse.ArgumentParser(description="Start Claude Code as the student's chat with the taskgen server.")
    parser.add_argument("--dir", type=Path, default=Path.home() / "taskgen-play", help="an empty folder to run in")
    parser.add_argument("extra", nargs=argparse.REMAINDER, help="more claude arguments after --")
    args = parser.parse_args()
    if shutil.which("claude") is None:
        sys.exit("the claude command is not installed")
    args.dir.mkdir(parents=True, exist_ok=True)
    os.chdir(args.dir)
    extra = args.extra[1:] if args.extra[:1] == ["--"] else args.extra
    os.execvp("claude", claude_args(extra))


if __name__ == "__main__":
    main()
