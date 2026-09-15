"""Runs the Analyst's solver_code in a Docker container without network, with memory, CPU and time limits (SPEC 5.3, 6).

The code goes in through stdin and must print a JSON list of the correct options, e.g. ["C"], as its last line;
lines before it are ignored. The container runs as nobody on a read-only file system and is removed after the run;
one that outlives the time limit is killed by name. The limit counts from the start of `docker run`.
"""

import json
import subprocess
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from taskgen import ROOT

OPTIONS = ("A", "B", "C", "D", "E")
OUTPUT_LIMIT = 64 * 1024  # bytes kept from stdout and from stderr; longer stdout is a bad output
STATUSES = ("ok", "error", "timeout", "bad_output")
OOM_EXIT = 137  # killed by SIGKILL: the memory limit


class SandboxUnavailable(RuntimeError):
    """Docker or the image cannot be used: a problem of the machine, not of the solver code."""


@dataclass(frozen=True)
class Limits:
    image: str
    timeout_sec: float
    memory_mb: int
    cpus: float


def load_limits(path: Path = ROOT / "config.yaml") -> Limits:
    """The sandbox section of config.yaml."""
    sandbox = yaml.safe_load(path.read_text(encoding="utf-8"))["sandbox"]
    return Limits(sandbox["image"], sandbox["timeout_sec"], sandbox["memory_mb"], sandbox["cpus"])


@dataclass(frozen=True)
class Result:
    status: str  # "ok", "error" (the code failed), "timeout" or "bad_output"
    options: list[str] | None  # the printed correct options, sorted; None unless status is "ok"
    message: str  # what went wrong, for the log and the retry prompt; empty when status is "ok"
    exit_code: int | None  # None after a timeout
    stdout: str
    stderr: str
    duration_ms: int

    def to_json(self) -> dict:
        """The result as stored in attempts.solver_result."""
        return asdict(self)


def parse_options(stdout: str) -> tuple[list[str] | None, str]:
    """Options from the last non-empty line of stdout and an empty message, or None and what is wrong."""
    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines:
        return None, "the program printed nothing"
    last = lines[-1].strip()
    try:
        value = json.loads(last)
    except json.JSONDecodeError:
        return None, f"the last line is not JSON: {last[:200]!r}"
    if not isinstance(value, list) or not all(isinstance(item, str) and item in OPTIONS for item in value):
        return None, f"the last line must be a JSON list of letters A-E, got {last[:200]}"
    if len(set(value)) != len(value):
        return None, f"an option is repeated: {last[:200]}"
    return sorted(value), ""


def docker_command(name: str, limits: Limits) -> list[str]:
    return [
        "docker", "run", "--rm", "--interactive", "--name", name,
        "--network", "none",
        "--memory", f"{limits.memory_mb}m", "--memory-swap", f"{limits.memory_mb}m",  # no swap on top
        "--cpus", str(limits.cpus),
        "--pids-limit", "64",
        "--read-only", "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--user", "65534:65534",  # nobody
        limits.image,
        "python", "-I", "-B", "-",  # isolated mode, no .pyc files, program from stdin
    ]  # fmt: skip


@lru_cache(maxsize=None)
def ensure_image(image: str) -> None:
    """Pull the image once if it is not on the machine, so a pull never eats into the time limit."""
    try:
        if subprocess.run(["docker", "image", "inspect", image], capture_output=True).returncode == 0:
            return
        pulled = subprocess.run(["docker", "pull", "--quiet", image], capture_output=True, text=True)
    except FileNotFoundError as error:
        raise SandboxUnavailable("the docker command is not installed") from error
    if pulled.returncode != 0:
        raise SandboxUnavailable(f"cannot pull {image}: {pulled.stderr.strip()}")


def read_capped(stream, sink: list[bytes]) -> None:
    """Keep the first OUTPUT_LIMIT + 1 bytes and drain the rest, so the container never blocks on a full pipe."""
    sink.append(stream.read(OUTPUT_LIMIT + 1))
    while stream.read(65536):
        pass


def run(code: str, limits: Limits | None = None) -> Result:
    """Run solver code in a fresh container and check what it printed."""
    limits = limits or load_limits()
    ensure_image(limits.image)
    name = f"taskgen-sandbox-{uuid.uuid4().hex[:12]}"
    started = time.monotonic()
    process = subprocess.Popen(
        docker_command(name, limits), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = [], []
    readers = [
        threading.Thread(target=read_capped, args=(process.stdout, stdout)),
        threading.Thread(target=read_capped, args=(process.stderr, stderr)),
    ]
    for reader in readers:
        reader.start()
    try:
        process.stdin.write(code.encode("utf-8"))
        process.stdin.close()
    except BrokenPipeError:
        pass  # the container ended before reading the code; its exit code and stderr say why

    try:
        exit_code = process.wait(timeout=limits.timeout_sec)
    except subprocess.TimeoutExpired:
        exit_code = None
        subprocess.run(["docker", "kill", name], capture_output=True)
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    for reader in readers:
        reader.join()
    duration_ms = round((time.monotonic() - started) * 1000)

    out_bytes, err_bytes = stdout[0], stderr[0]
    out = out_bytes[:OUTPUT_LIMIT].decode("utf-8", errors="replace")
    err = err_bytes[:OUTPUT_LIMIT].decode("utf-8", errors="replace")

    def result(status, options=None, message=""):
        return Result(status, options, message, exit_code, out, err, duration_ms)

    if exit_code is None:
        return result("timeout", message=f"no result within {limits.timeout_sec} s")
    if exit_code == 125 and err.startswith("docker:"):
        raise SandboxUnavailable(f"docker run failed: {err.strip()}")
    if exit_code == OOM_EXIT:
        return result("error", message=f"killed, most likely over the {limits.memory_mb} MB memory limit")
    if exit_code != 0:
        last_line = err.strip().splitlines()[-1] if err.strip() else "no error text"
        return result("error", message=f"exit code {exit_code}: {last_line}")
    if len(out_bytes) > OUTPUT_LIMIT:
        return result("bad_output", message=f"the program printed more than {OUTPUT_LIMIT // 1024} KB")
    options, problem = parse_options(out)
    if options is None:
        return result("bad_output", message=problem)
    return result("ok", options)
