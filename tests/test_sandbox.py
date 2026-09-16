"""sandbox.py (T14): output parsing without Docker, then real runs in the container (skipped without Docker)."""

import dataclasses
import json
import shutil
import subprocess

import pytest

from taskgen import sandbox


def docker_works() -> bool:
    return bool(shutil.which("docker")) and subprocess.run(["docker", "info"], capture_output=True).returncode == 0


needs_docker = pytest.mark.skipif(not docker_works(), reason="Docker is not available")


@pytest.fixture(scope="module")
def limits():
    return sandbox.load_limits()


def leftover_containers() -> str:
    return subprocess.run(
        ["docker", "ps", "--all", "--quiet", "--filter", "name=taskgen-sandbox-"], capture_output=True, text=True
    ).stdout.strip()


# Parsing


@pytest.mark.parametrize(
    ("stdout", "options"),
    [
        ('["C"]\n', ["C"]),
        ('checking pairs\n6 pairs\n["C"]\n\n', ["C"]),  # earlier lines are ignored
        ('["E", "A"]', ["A", "E"]),  # several correct options are reported, sorted
        ("[]", []),  # no correct option is a valid answer; the consensus check rejects it later
    ],
)
def test_parse_valid_output(stdout, options):
    assert sandbox.parse_options(stdout) == (options, "")


@pytest.mark.parametrize(
    "stdout",
    ["", "\n\n", "C", '"C"', '["F"]', '["c"]', '["C", "C"]', '{"answer": "C"}', "[3]", '["C"] done'],
)
def test_parse_bad_output(stdout):
    options, message = sandbox.parse_options(stdout)
    assert options is None and message


def test_config_limits(limits):
    assert limits.timeout_sec == 10 and limits.memory_mb == 256 and limits.cpus == 1
    assert "@sha256:" in limits.image  # exact versions only: the image is pinned by digest


# Runs in Docker


@needs_docker
def test_correct_code(limits):
    code = """
import itertools, json
pairs = len(list(itertools.combinations(range(4), 2)))
options = {"A": 4, "B": 5, "C": 6, "D": 8, "E": 12}
print(json.dumps([letter for letter, value in options.items() if value == pairs]))
"""
    result = sandbox.run(code, limits)
    assert (result.status, result.options, result.exit_code, result.message) == ("ok", ["C"], 0, "")
    assert json.loads(json.dumps(result.to_json()))["options"] == ["C"]  # fits attempts.solver_result


@needs_docker
def test_code_with_exception(limits):
    result = sandbox.run('raise ValueError("no such option")', limits)
    assert (result.status, result.options, result.exit_code) == ("error", None, 1)
    assert "ValueError: no such option" in result.message
    assert "Traceback" in result.stderr


@needs_docker
def test_infinite_loop_hits_the_time_limit(limits):
    short = dataclasses.replace(limits, timeout_sec=3)
    result = sandbox.run("while True:\n    pass\n", short)
    assert (result.status, result.options, result.exit_code) == ("timeout", None, None)
    assert 3000 <= result.duration_ms < 15000
    assert leftover_containers() == ""  # the killed container is gone


@needs_docker
def test_network_is_blocked(limits):
    code = """
import json, socket
reached = []
try:
    socket.create_connection(("1.1.1.1", 53), timeout=3)
    reached.append("ip")
except OSError:
    pass
try:
    socket.getaddrinfo("example.com", 443)
    reached.append("dns")
except OSError:
    pass
print(json.dumps(["B"] if reached else ["A"]))
"""
    assert sandbox.run(code, limits).options == ["A"]


@needs_docker
def test_output_in_the_wrong_format(limits):
    result = sandbox.run('print("The answer is C")', limits)
    assert (result.status, result.options, result.exit_code) == ("bad_output", None, 0)
    assert "not JSON" in result.message


@needs_docker
def test_memory_limit(limits):
    result = sandbox.run("data = bytearray(1024 * 1024 * 1024)\nprint('[\"A\"]')", limits)
    assert result.status == "error"


@needs_docker
def test_too_much_output(limits):
    result = sandbox.run("print('x' * 200_000)\nprint('[\"C\"]')", limits)
    assert result.status == "bad_output"
    assert len(result.stdout.encode()) <= sandbox.OUTPUT_LIMIT


@needs_docker
def test_file_system_is_read_only_and_user_is_nobody(limits):
    code = """
import json, os
try:
    open("/usr/local/lib/planted.py", "w")
    writable = True
except OSError:
    writable = False
print(json.dumps(["A"] if not writable and os.getuid() == 65534 else ["B"]))
"""
    assert sandbox.run(code, limits).options == ["A"]


@needs_docker
def test_missing_image_is_a_machine_problem(limits):
    missing = dataclasses.replace(limits, image="taskgen-no-such-image:0.0.0")
    with pytest.raises(sandbox.SandboxUnavailable):
        sandbox.run('print(["A"])', missing)
