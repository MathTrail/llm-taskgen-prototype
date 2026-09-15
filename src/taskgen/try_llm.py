"""Smoke test of llm.py (T18): one tiny call to the tutor's model (Claude Haiku 4.5) with a small JSON schema.

Prints the JSON answer, the model, tokens, cost and time. Costs well under $0.01.
Run: uv run python -m taskgen.try_llm
"""

import json

from taskgen import llm

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["answer", "explanation"],
    "properties": {
        "answer": {"type": "integer"},
        "explanation": {"type": "string"},
    },
}


def main() -> None:
    result = llm.call(
        "tutor",
        system="You are a patient maths coach for children in grades 1-4.",
        messages=[{"role": "user", "content": "A fence has 5 posts in a row, 2 metres apart. How long is the fence?"}],
        schema=SCHEMA,
    )
    call = result.call
    print(json.dumps(result.data, indent=2, ensure_ascii=False))
    print(
        f"model {call.model} (asked for {call.requested_model}), stop {call.stop_reason}, {call.duration_ms} ms\n"
        f"tokens: input {call.usage.input_tokens}, output {call.usage.output_tokens}, "
        f"cache write {call.usage.cache_write_tokens}, cache read {call.usage.cache_read_tokens}\n"
        f"cost ${call.cost_usd:.6f}"
    )


if __name__ == "__main__":
    main()
