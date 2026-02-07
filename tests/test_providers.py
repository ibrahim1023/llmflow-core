import pytest
from pydantic import ValidationError

from llmflow.errors import ProviderError
from llmflow.providers import MockProvider, ProviderMessage, ProviderRequest


def test_provider_request_requires_prompt_or_messages() -> None:
    with pytest.raises(ValidationError):
        ProviderRequest(model="mock")


def test_provider_request_disallows_prompt_and_messages() -> None:
    with pytest.raises(ValidationError):
        ProviderRequest(
            model="mock",
            prompt="hello",
            messages=[ProviderMessage(role="user", content="hi")],
        )


def test_mock_provider_prompt_mapping() -> None:
    provider = MockProvider(responses={"prompt:hello": "ok"})
    request = ProviderRequest(model="mock", prompt="hello")
    response = provider.call(request)
    assert response.output_text == "ok"
    assert response.raw["mock_key"] == "prompt:hello"


def test_mock_provider_messages_mapping() -> None:
    provider = MockProvider(responses={"messages:user|hi": "ok"})
    request = ProviderRequest(
        model="mock",
        messages=[ProviderMessage(role="user", content="hi")],
    )
    response = provider.call(request)
    assert response.output_text == "ok"
    assert response.raw["mock_key"] == "messages:user|hi"


def test_mock_provider_strict_missing_mapping_raises() -> None:
    provider = MockProvider()
    request = ProviderRequest(model="mock", prompt="missing")
    with pytest.raises(ProviderError):
        provider.call(request)
