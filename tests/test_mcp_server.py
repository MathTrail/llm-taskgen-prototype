"""mcp_server.py (T19–T21) through a real MCP client: in process, and over stdio as Claude Code starts it."""

import json
import sys

import psycopg
import pytest
from mcp import Client, StdioServerParameters

from taskgen import mcp_server, service
from taskgen.seed import SEED_DIR, seed_student

STUDENT = "mcpprobe"  # a committed student only these tests use; removed afterwards


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def probe_student(test_url, monkeypatch):
    """A student committed to the test database, since the server opens its own connection."""
    monkeypatch.setenv("DATABASE_URL", test_url)
    profile = json.loads((SEED_DIR / "masha.json").read_text(encoding="utf-8")) | {"id": STUDENT}
    with psycopg.connect(test_url) as conn:
        seed_student(conn, profile)
    yield STUDENT
    with psycopg.connect(test_url) as conn:
        tasks = [row[0] for row in conn.execute(
            "SELECT task_id FROM requests WHERE student_id = %s AND task_id IS NOT NULL", (STUDENT,))]  # fmt: skip
        conn.execute("DELETE FROM attempts WHERE request_id IN (SELECT request_id FROM requests WHERE student_id = %s)",
                     (STUDENT,))  # fmt: skip
        for table in ("requests", "student_tasks", "student_topic_ratings", "students"):
            conn.execute(f"DELETE FROM {table} WHERE student_id = %s", (STUDENT,))
        conn.execute("DELETE FROM tasks WHERE task_id = ANY(%s)", (tasks,))


@pytest.mark.anyio
async def test_tools_are_registered():
    async with Client(mcp_server.server) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
    assert {"get_student_profile", "get_progress", "get_next_task", "submit_task"} <= set(tools)
    assert "student_id" in json.dumps(tools["get_student_profile"].input_schema)
    assert {"language", "topic", "difficulty", "reason"} <= set(tools["get_next_task"].input_schema["properties"])
    submit = tools["submit_task"].input_schema["properties"]
    assert {"request_id", "brief", "task", "solver_code", "self_check", "language"} <= set(submit)
    assert "ctx" not in submit  # the context is injected by the server, not passed by the model


@pytest.mark.anyio
async def test_profile_through_mcp(probe_student):
    async with Client(mcp_server.server) as client:
        result = await client.call_tool("get_student_profile", {"student_id": probe_student})
    assert not result.is_error
    assert result.structured_content["student_id"] == probe_student
    assert len(result.structured_content["topics"]) == 10


@pytest.mark.anyio
async def test_progress_through_mcp(probe_student):
    async with Client(mcp_server.server) as client:
        result = await client.call_tool("get_progress", {"student_id": probe_student})
    assert not result.is_error
    assert "cognitive_profile" not in result.structured_content


@pytest.mark.anyio
async def test_next_task_through_mcp(probe_student):
    async with Client(mcp_server.server) as client:
        result = await client.call_tool("get_next_task", {"student_id": probe_student, "language": "en"})
    assert not result.is_error
    assert result.structured_content["source"] == "generate"  # no bank tasks in the test database
    assert result.structured_content["brief"]["target_concept"] == "time.clocks"


@pytest.mark.anyio
async def test_submit_task_records_the_client(probe_student, test_url):
    # A deliberately broken hand-in: this checks the plumbing and the client info, not the task checks.
    async with Client(mcp_server.server) as client:
        package = (await client.call_tool("get_next_task", {"student_id": probe_student, "language": "en"}))
        request_id = package.structured_content["request_id"]
        result = await client.call_tool("submit_task", {
            "request_id": request_id, "brief": package.structured_content["brief"], "task": {"question": "?"},
            "solver_code": "print('[]')", "self_check": {}, "language": "en",
        })  # fmt: skip
    assert not result.is_error
    assert result.structured_content["status"] == "rejected"
    assert result.structured_content["reasons"][0]["code"] == "bad_structure"
    with psycopg.connect(test_url) as conn:
        models = conn.execute("SELECT models FROM attempts WHERE request_id = %s", (request_id,)).fetchone()[0]
    assert models and models["name"]  # clientInfo of the in-process client


@pytest.mark.anyio
async def test_unknown_student_is_a_tool_error(probe_student):
    async with Client(mcp_server.server) as client:
        result = await client.call_tool("get_progress", {"student_id": "nobody"})
    assert result.is_error
    assert "nobody" in result.content[0].text and probe_student in result.content[0].text


@pytest.mark.anyio
async def test_bad_arguments_are_a_tool_error(probe_student):
    async with Client(mcp_server.server) as client:
        result = await client.call_tool("get_next_task", {"student_id": probe_student, "language": "english"})
    assert result.is_error and "ISO 639-1" in result.content[0].text


@pytest.mark.anyio
async def test_server_runs_over_stdio(probe_student, test_url):
    # The same way .mcp.json starts it; a stray print to stdout would break this.
    params = StdioServerParameters(command=sys.executable, args=["-m", "taskgen.mcp_server"],
                                   env={"DATABASE_URL": test_url})
    async with Client(params) as client:
        result = await client.call_tool("get_student_profile", {"student_id": probe_student})
    assert not result.is_error and result.structured_content["grade"] == 3


def test_instructions_reach_the_server():
    assert mcp_server.server.instructions == service.instructions()
