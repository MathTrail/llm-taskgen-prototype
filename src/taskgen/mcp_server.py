"""MCP server of the prototype (SPEC 5.8): a thin adapter over taskgen.service, run over stdio.

Claude Code starts it from .mcp.json in the repository root: uv run python -m taskgen.mcp_server
Nothing may be printed to stdout: over stdio it carries the protocol.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError

from taskgen import sandbox, service
from taskgen.rating import load_params

server = MCPServer("taskgen", instructions=service.instructions())


@contextmanager
def tool_errors() -> Iterator[None]:
    """Mistakes the model can fix become tool errors with a message for it; the transaction is rolled back."""
    try:
        yield
    except (service.StudentNotFound, service.InvalidRequest) as error:
        raise ToolError(str(error)) from error
    except sandbox.SandboxUnavailable as error:
        raise ToolError(f"the server cannot run the solver program right now ({error}); the attempt was not "
                        "counted, try submit_task again later") from error  # fmt: skip


def client_info(ctx: Context) -> dict[str, str] | None:
    """Name and version the MCP client declared (SPEC 7: attempts.models); the model itself is not disclosed."""
    params = ctx.session.client_params
    if params is None:
        return None
    return {"name": params.client_info.name, "version": params.client_info.version}


@server.tool(title="Student profile")
def get_student_profile(student_id: str) -> dict[str, Any]:
    """For the coach, not for reading out: the student's profile, last answers, the rule's recommended brief for the
    next task and, for every topic of their grade level, the level, a chess-style rating, the recommended difficulty
    1-5 and its fit to the 70-85% success corridor. Contains sensitive notes (cognitive_profile): adapt to them,
    never quote them to the child."""
    with tool_errors(), service.connect() as conn:
        return service.student_profile(conn, student_id, load_params())


@server.tool(title="Progress")
def get_progress(student_id: str) -> dict[str, Any]:
    """A summary to share with the child: ratings by topic on a chess-like scale (1500 is the start), mastered
    topics and the last answers."""
    with tool_errors(), service.connect() as conn:
        return service.progress(conn, student_id, load_params())


@server.tool(title="Next task")
def get_next_task(
    student_id: str,
    language: str,
    topic: str | None = None,
    difficulty: int | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """The next task for the student. language is the two-letter code of the chat language, such as en or ru.
    By default the task follows the rule's recommendation from get_student_profile; to choose another topic id or
    difficulty 1-5, pass them with a short reason.
    source "bank": a checked task is issued to the student; show the question and options, give the hint only on
    request; the answer is not included. source "generate": nothing fitting in the bank; write a task by the
    returned guide, brief, examples and formats and hand it in with submit_task."""
    with tool_errors(), service.connect() as conn:
        return service.next_task(conn, student_id, language, load_params(), topic=topic, difficulty=difficulty,
                                 reason=reason)  # fmt: skip


@server.tool(title="Hand in a task")
def submit_task(
    request_id: int,
    brief: dict[str, Any],
    task: dict[str, Any],
    solver_code: str,
    self_check: dict[str, Any],
    language: str,
    ctx: Context,
) -> dict[str, Any]:
    """Hand in the task you wrote for a get_next_task request with source "generate". brief, task and self_check
    follow the formats returned by get_next_task; solver_code prints the JSON list of correct options as its last
    line; language is the task's two-letter code. The server checks structure, runs the program, reads the
    self-check, readability and near duplicates. status "accepted": the task is in the bank and issued to the
    student; show it. status "rejected": fix every reason and call again with the same request_id while
    attempts_left > 0."""
    client = client_info(ctx)
    with tool_errors(), service.connect() as conn:
        return service.submit_task(conn, request_id, brief, task, solver_code, self_check, language, load_params(),
                                   client=client)  # fmt: skip


@server.tool(title="Record an answer")
def submit_answer(student_id: str, task_id: str, answer: str, hint_used: bool = False) -> dict[str, Any]:
    """Record the child's answer to a task they were given: answer is the letter A-E, or "?" when the child says
    they do not understand the task; hint_used is true if you gave them the hint. Returns whether it is correct,
    the correct answer, the trap text of a wrong option and the solution, so you can explain; also updates the
    child's history and ratings."""
    with tool_errors(), service.connect() as conn:
        return service.submit_answer(conn, student_id, task_id, answer, hint_used, load_params())


def main() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main()
