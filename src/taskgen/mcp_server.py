"""MCP server of the prototype (SPEC 5.8): a thin adapter over taskgen.service, run over stdio.

Claude Code starts it from .mcp.json in the repository root: uv run python -m taskgen.mcp_server
Nothing may be printed to stdout: over stdio it carries the protocol.
"""

from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from taskgen import service
from taskgen.rating import load_params

server = MCPServer("taskgen", instructions=service.instructions())


def profile_or_error(read, student_id: str) -> dict[str, Any]:
    """Run a read of one student's data; an unknown student becomes a tool error the model can act on."""
    with service.connect() as conn:
        try:
            return read(conn, student_id, load_params())
        except service.StudentNotFound as error:
            raise ToolError(str(error)) from error


@server.tool(title="Student profile")
def get_student_profile(student_id: str) -> dict[str, Any]:
    """For the coach, not for reading out: the student's profile, last answers and, for every topic of their
    grade level, the level, a chess-style rating, the recommended difficulty 1-5 and its fit to the 70-85% success
    corridor. Contains sensitive notes (cognitive_profile): adapt to them, never quote them to the child."""
    return profile_or_error(service.student_profile, student_id)


@server.tool(title="Progress")
def get_progress(student_id: str) -> dict[str, Any]:
    """A summary to share with the child: ratings by topic on a chess-like scale (1500 is the start), mastered
    topics and the last answers."""
    return profile_or_error(service.progress, student_id)


def main() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main()
