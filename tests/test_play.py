"""play.py (T23): the Claude Code command for a student chat allows exactly the taskgen tools."""

import json

import pytest
from mcp import Client

from taskgen import ROOT, mcp_server, play


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_claude_command():
    args = play.claude_args(["--model", "opus"])
    assert args[:2] == ["claude", "--strict-mcp-config"]
    config = json.loads(args[args.index("--mcp-config") + 1])["mcpServers"]["taskgen"]
    assert config["command"] == "uv" and str(ROOT) in config["args"]  # the server starts from any folder
    assert args[args.index("--allowedTools") + 1].split() == [f"mcp__taskgen__{tool}" for tool in play.TOOLS]
    assert "Bash" in args[args.index("--disallowedTools") + 1].split()
    assert "coach" in args[args.index("--append-system-prompt") + 1]
    assert args[-2:] == ["--model", "opus"]


@pytest.mark.anyio
async def test_allowed_tools_are_the_server_tools():
    async with Client(mcp_server.server) as client:
        names = {tool.name for tool in (await client.list_tools()).tools}
    assert set(play.TOOLS) == names
