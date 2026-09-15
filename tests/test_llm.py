"""llm.py (T18) without the network: request parameters per agent, cost accounting, errors, prompt_version."""

from pathlib import Path
from types import SimpleNamespace

import anthropic
import pytest

from taskgen import llm

CONFIG = llm.load_config()
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["answer"],
          "properties": {"answer": {"type": "integer"}}}  # fmt: skip


def message(text='{"answer": 42}', model="claude-haiku-4-5", stop_reason="end_turn", input_tokens=100,
            output_tokens=20, cache_write=1000, cache_read=0):
    return SimpleNamespace(
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
        model=model,
        stop_reason=stop_reason,
        stop_details=SimpleNamespace(category="cyber") if stop_reason == "refusal" else None,
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens,
                              cache_creation_input_tokens=cache_write, cache_read_input_tokens=cache_read),
    )  # fmt: skip


class FakeStream:
    def __init__(self, reply):
        self.reply = reply

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self.reply


class FakeMessages:
    def __init__(self, reply):
        self.reply, self.calls = reply, []

    def stream(self, **params):
        self.calls.append(params)
        return FakeStream(self.reply)


class FakeClient:
    """Records the parameters of messages.stream() and beta.messages.stream() and returns a canned message."""

    def __init__(self, reply=None):
        reply = reply or message()
        self.messages = FakeMessages(reply)
        self.beta = SimpleNamespace(messages=FakeMessages(reply))


def ask(agent="tutor", reply=None, system="System prompt."):
    client = FakeClient(reply)
    result = llm.call(agent, system, [{"role": "user", "content": "Hi"}], SCHEMA, config=CONFIG, client=client)
    return result, client


# Request parameters


def test_tutor_request():
    result, client = ask("tutor")
    (params,) = client.messages.calls
    assert params["model"] == "claude-haiku-4-5" and params["max_tokens"] == 4096
    assert params["output_config"] == {"format": {"type": "json_schema", "schema": SCHEMA}}  # Haiku 4.5: no effort
    assert "thinking" not in params
    assert params["system"] == [{"type": "text", "text": "System prompt.", "cache_control": {"type": "ephemeral"}}]
    assert client.beta.messages.calls == []
    assert result.data == {"answer": 42}


def test_generator_request_uses_effort_thinking_and_fallbacks():
    _, client = ask("generator", message(model="claude-opus-5"))
    (params,) = client.beta.messages.calls
    assert params["model"] == "claude-opus-5" and params["max_tokens"] == 32000
    assert params["output_config"]["effort"] == "high"
    assert params["thinking"] == {"type": "adaptive"}
    assert params["fallbacks"] == "default" and params["betas"] == [llm.FALLBACKS_BETA]
    assert client.messages.calls == []


@pytest.mark.parametrize("agent", ["analyst", "skeptic"])
def test_verifier_request(agent):
    _, client = ask(agent, message(model="claude-sonnet-5"))
    (params,) = client.messages.calls
    assert (params["model"], params["output_config"]["effort"], params["thinking"]) == (
        "claude-sonnet-5", "medium", {"type": "adaptive"}
    )


def test_only_the_last_system_block_is_the_cache_breakpoint():
    _, client = ask(system=["Instructions.", "Few-shot examples."])
    blocks = client.messages.calls[0]["system"]
    assert [block.get("cache_control") for block in blocks] == [None, {"type": "ephemeral"}]


# Cost


def test_cost_of_a_call():
    result, _ = ask(reply=message(input_tokens=100, output_tokens=20, cache_write=1000, cache_read=0))
    # Haiku 4.5: 100 * $1 + 1000 * $1.25 + 20 * $5 per million tokens
    assert result.call.cost_usd == pytest.approx(1450 / 1_000_000)
    assert result.call.usage.total == 1120


def test_cache_read_is_cheap():
    usage = llm.Usage(input_tokens=0, output_tokens=0, cache_write_tokens=0, cache_read_tokens=1_000_000)
    assert llm.cost_usd(usage, CONFIG["prices"]["claude-opus-5"]) == pytest.approx(0.50)


def test_fallback_is_priced_by_the_model_that_answered():
    result, _ = ask("generator", message(model="claude-opus-4-8", input_tokens=1_000_000, output_tokens=0,
                                         cache_write=0))
    assert (result.call.requested_model, result.call.model) == ("claude-opus-5", "claude-opus-4-8")
    assert result.call.cost_usd == pytest.approx(5.0)


def test_every_configured_model_has_a_price():
    for settings in CONFIG["agents"].values():
        assert set(CONFIG["prices"][settings["model"]]) == {"input", "cache_write", "cache_read", "output"}


# Errors


@pytest.mark.parametrize(
    ("reply", "fragment"),
    [
        (message(stop_reason="refusal"), "refused"),
        (message(stop_reason="max_tokens"), "cut off"),
        (message(text="The answer is 42."), "not JSON"),
    ],
)
def test_unusable_answer_raises_with_its_cost(reply, fragment):
    with pytest.raises(llm.LLMError, match=fragment) as error:
        ask(reply=reply)
    assert error.value.call.cost_usd > 0  # the paid call is still accounted for


# Client and prompt version


def test_client_takes_retries_and_timeout_from_config(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    client = llm.make_client(CONFIG)
    assert isinstance(client, anthropic.Anthropic)
    assert client.max_retries == CONFIG["llm"]["max_retries"] == 4
    assert client.timeout == CONFIG["llm"]["timeout_sec"] == 600


def test_api_key_from_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("# comment\nANTHROPIC_API_KEY='sk-test'\nDATABASE_URL=x\n", encoding="utf-8")
    assert llm.api_key(env_file) == "sk-test"
    env_file.write_text("ANTHROPIC_API_KEY=\n", encoding="utf-8")
    assert llm.api_key(env_file) is None


def test_prompt_version(tmp_path):
    prompt, schema = tmp_path / "tutor.md", tmp_path / "brief.json"
    prompt.write_text("Pick a task.", encoding="utf-8")
    schema.write_text("{}", encoding="utf-8")
    version = llm.prompt_version(prompt, schema)
    assert len(version) == 12 and int(version, 16) >= 0
    assert llm.prompt_version(schema, prompt) == version  # order does not matter
    prompt.write_text("Pick a task!", encoding="utf-8")
    assert llm.prompt_version(prompt, schema) != version


def test_prompt_version_of_real_files():
    assert llm.prompt_version(Path("schemas/brief.json")) == llm.prompt_version(Path("schemas/brief.json"))
