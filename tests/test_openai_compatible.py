"""Offline request-shape tests for the OpenAI-compatible adapter."""

import json
from unittest.mock import patch

from app.llm.openai_compatible import OpenAICompatibleChat


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self) -> bytes:
        return b'{"choices":[{"message":{"content":"{\\"tool\\":\\"search_products\\"}"}}]}'


def test_request_does_not_force_temperature_zero() -> None:
    client = OpenAICompatibleChat(
        api_key="test-key",
        base_url="https://example.test/v1",
        model="test-model",
    )

    with patch("app.llm.openai_compatible.urlopen", return_value=_Response()) as mocked:
        client("route this")

    request = mocked.call_args.args[0]
    payload = json.loads(request.data.decode("utf-8"))
    assert payload == {
        "model": "test-model",
        "messages": [{"role": "user", "content": "route this"}],
    }
    assert "temperature" not in payload
