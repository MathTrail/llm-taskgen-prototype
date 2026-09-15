"""Claude API calls for all agents (SPEC 8, D41).

- model, effort, thinking and max_tokens come from the agent's entry in config.yaml;
- the answer is constrained by a JSON schema through structured outputs (output_config.format);
- the system prompt is the cached prefix: its last block gets cache_control, so few-shot examples go there too;
- tokens and cost are counted with the prices in config.yaml, by the model that actually answered;
- prompt_version is a hash of the prompt and schema files, so metrics of different prompt versions never mix.

Every call streams and reads the final message, so a long answer never hits the HTTP timeout. The SDK retries
connection errors, 408, 409, 429 and 5xx with backoff (llm.max_retries in config.yaml). A refusal, a cut-off answer
or an answer that is not JSON raises LLMError, which still carries the tokens and cost of the paid call.
"""

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

import anthropic
import yaml

from taskgen import ROOT

FALLBACKS_BETA = "server-side-fallback-2026-07-01"  # the header for fallbacks: "default"


@dataclass(frozen=True)
class Usage:
    input_tokens: int  # uncached input
    output_tokens: int  # thinking included
    cache_write_tokens: int
    cache_read_tokens: int

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens + self.cache_write_tokens + self.cache_read_tokens


@dataclass(frozen=True)
class Call:
    """What one API call cost and how long it took."""

    agent: str
    requested_model: str
    model: str  # the model that answered: another one after a server-side fallback
    stop_reason: str
    usage: Usage
    cost_usd: float
    duration_ms: int


@dataclass(frozen=True)
class Result:
    data: dict  # the answer, valid against the schema
    call: Call


class LLMError(RuntimeError):
    """The model gave no usable answer: a refusal, a cut-off answer, or text that is not JSON."""

    def __init__(self, message: str, call: Call):
        super().__init__(message)
        self.call = call


def load_config(path: Path = ROOT / "config.yaml") -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def api_key(env_file: Path = ROOT / ".env") -> str | None:
    """ANTHROPIC_API_KEY from the environment, otherwise from .env; None lets the SDK find other credentials."""
    if key := os.environ.get("ANTHROPIC_API_KEY"):
        return key
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip() == "ANTHROPIC_API_KEY" and value.strip():
                return value.strip().strip("\"'")
    return None


def make_client(config: dict) -> anthropic.Anthropic:
    return anthropic.Anthropic(
        api_key=api_key(), max_retries=config["llm"]["max_retries"], timeout=config["llm"]["timeout_sec"]
    )


def prompt_version(*paths: Path) -> str:
    """12 hex digits of SHA-256 over the names and contents of the files; the order of the arguments does not matter."""
    digest = hashlib.sha256()
    for path in sorted(Path(path) for path in paths):
        digest.update(path.name.encode("utf-8") + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()[:12]


def cost_usd(usage: Usage, price: dict) -> float:
    """Cost of the tokens at the prices of one model, in USD per million tokens."""
    return (
        usage.input_tokens * price["input"]
        + usage.cache_write_tokens * price["cache_write"]
        + usage.cache_read_tokens * price["cache_read"]
        + usage.output_tokens * price["output"]
    ) / 1_000_000


def request_params(settings: dict, system: str | list[str], messages: list[dict], schema: dict) -> dict:
    """Keyword arguments for messages.stream() from the agent's settings."""
    blocks = [{"type": "text", "text": text} for text in ([system] if isinstance(system, str) else system)]
    blocks[-1]["cache_control"] = {"type": "ephemeral"}  # everything up to here is the stable, cached prefix
    output_config = {"format": {"type": "json_schema", "schema": schema}}
    if "effort" in settings:
        output_config["effort"] = settings["effort"]
    params = {
        "model": settings["model"],
        "max_tokens": settings["max_tokens"],
        "system": blocks,
        "messages": messages,
        "output_config": output_config,
    }
    if "thinking" in settings:
        params["thinking"] = {"type": settings["thinking"]}
    return params


def call(
    agent: str,
    system: str | list[str],
    messages: list[dict],
    schema: dict,
    *,
    config: dict | None = None,
    client: anthropic.Anthropic | None = None,
) -> Result:
    """Ask the agent's model and return its JSON answer with the tokens, cost and time of the call."""
    config = load_config() if config is None else config
    settings = config["agents"][agent]
    params = request_params(settings, system, messages, schema)
    client = make_client(config) if client is None else client

    started = time.monotonic()
    if settings.get("fallbacks"):
        stream = client.beta.messages.stream(**params, fallbacks=settings["fallbacks"], betas=[FALLBACKS_BETA])
    else:
        stream = client.messages.stream(**params)
    with stream as events:
        message = events.get_final_message()
    duration_ms = round((time.monotonic() - started) * 1000)

    usage = Usage(
        input_tokens=message.usage.input_tokens,
        output_tokens=message.usage.output_tokens,
        cache_write_tokens=message.usage.cache_creation_input_tokens or 0,
        cache_read_tokens=message.usage.cache_read_input_tokens or 0,
    )
    prices = config["prices"]
    price = prices.get(message.model, prices[settings["model"]])  # an unlisted fallback model: the requested price
    record = Call(agent, settings["model"], message.model, message.stop_reason, usage, cost_usd(usage, price), duration_ms)

    if message.stop_reason == "refusal":
        details = getattr(message, "stop_details", None)
        raise LLMError(f"{message.model} refused to answer: {getattr(details, 'category', None)}", record)
    if message.stop_reason == "max_tokens":
        raise LLMError(f"the answer was cut off at max_tokens = {settings['max_tokens']}", record)
    text = "".join(block.text for block in message.content if block.type == "text")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise LLMError(f"the answer is not JSON: {error}: {text[:200]!r}", record) from error
    return Result(data, record)
