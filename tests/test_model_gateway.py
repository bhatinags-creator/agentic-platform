import httpx
import pytest
from langchain_core.messages import AIMessage

from services.model_gateway.service import ModelGatewayError, ModelGatewayService


class FakeLangChainChatModel:
    def __init__(self) -> None:
        self.messages = []

    async def ainvoke(self, messages):
        self.messages = messages
        return AIMessage(
            content="LangChain provider response",
            usage_metadata={"input_tokens": 8, "output_tokens": 5, "total_tokens": 13},
        )


@pytest.mark.anyio
async def test_model_gateway_prefers_langchain_chat_model_for_openai_profiles() -> None:
    fake_model = FakeLangChainChatModel()
    service = ModelGatewayService(langchain_chat_model=fake_model)

    result = await service.chat(
        {"provider": "OpenAI", "model": "GPT Test", "api_key": "test-key"},
        [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "hello"},
        ],
    )

    assert result.output_text == "LangChain provider response"
    assert result.model == "gpt-test"
    assert result.prompt_tokens == 8
    assert result.completion_tokens == 5
    assert fake_model.messages[0].type == "system"
    assert fake_model.messages[1].type == "human"


@pytest.mark.anyio
async def test_model_gateway_calls_openai_compatible_chat_completion() -> None:
    captured_request = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured_request["url"] = str(request.url)
        captured_request["authorization"] = request.headers.get("Authorization")
        captured_request["payload"] = request.read().decode()
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Real provider response"}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 4},
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = ModelGatewayService(http_client=client)

    result = await service.chat(
        {
            "provider": "OpenAI",
            "model": "GPT Test",
            "api_key": "test-key",
            "parameters": {"base_url": "https://example.test/v1", "temperature": 0.2},
        },
        [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "hello"},
        ],
    )
    await client.aclose()

    assert result.output_text == "Real provider response"
    assert result.provider == "OpenAI"
    assert result.model == "gpt-test"
    assert result.prompt_tokens == 12
    assert result.completion_tokens == 4
    assert captured_request["url"] == "https://example.test/v1/chat/completions"
    assert captured_request["authorization"] == "Bearer test-key"
    assert '"model":"gpt-test"' in captured_request["payload"]
    assert '"temperature":0.2' in captured_request["payload"]


@pytest.mark.anyio
async def test_model_gateway_raises_clear_provider_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "bad api key"}}, request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = ModelGatewayService(http_client=client)

    with pytest.raises(ModelGatewayError, match="bad api key"):
        await service.chat(
            {"provider": "OpenAI", "model": "gpt-test", "api_key": "bad-key"},
            [{"role": "user", "content": "hello"}],
        )
    await client.aclose()
