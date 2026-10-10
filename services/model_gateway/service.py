import ast
from dataclasses import dataclass
from typing import Any, Protocol

import httpx


@dataclass
class ModelInvocationResult:
    output_text: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost: float = 0.0


class ModelGatewayError(Exception):
    """Raised when a configured model provider cannot complete a request."""


class LangChainChatModel(Protocol):
    async def ainvoke(self, messages: list[Any]) -> Any:
        """Invoke a LangChain chat model asynchronously."""


class ModelGatewayService:
    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
        langchain_chat_model: LangChainChatModel | None = None,
    ) -> None:
        self.http_client = http_client
        self.langchain_chat_model = langchain_chat_model

    async def chat(self, model_profile: dict, messages: list[dict]) -> ModelInvocationResult:
        provider = str(model_profile.get("provider", "mock")).strip()
        api_key = str(model_profile.get("api_key") or "").strip()
        if provider.lower() in {"openai", "openai-compatible"} and api_key:
            if self.http_client is None:
                langchain_result = await self._chat_with_langchain(model_profile, messages)
                if langchain_result is not None:
                    return langchain_result
            return await self._chat_openai_compatible(model_profile, messages)

        prompt_tokens = sum(len(str(message)) for message in messages)
        output_text = self._generate_response(messages)
        completion_tokens = max(5, len(output_text.split()))
        estimated_cost = round((prompt_tokens + completion_tokens) * 0.000001, 6)
        return ModelInvocationResult(
            output_text=output_text,
            provider=provider or "mock",
            model=model_profile.get("model", "mock-model"),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost=estimated_cost,
        )

    async def _chat_with_langchain(
        self,
        model_profile: dict,
        messages: list[dict],
    ) -> ModelInvocationResult | None:
        model = self.langchain_chat_model or self._build_langchain_chat_model(model_profile)
        if model is None:
            return None

        try:
            response = await model.ainvoke(self._to_langchain_messages(messages))
        except Exception as exc:
            raise ModelGatewayError(f"LangChain model invocation failed: {exc}") from exc

        output_text = str(getattr(response, "content", response)).strip()
        usage = self._langchain_usage(response)
        prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        estimated_cost = round((prompt_tokens + completion_tokens) * 0.000001, 6)
        return ModelInvocationResult(
            output_text=output_text or "Model completed without a text response.",
            provider=provider_name(model_profile),
            model=self._model_id(model_profile),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost=estimated_cost,
        )

    def _build_langchain_chat_model(self, model_profile: dict) -> LangChainChatModel | None:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            return None

        parameters = self._parameters(model_profile)
        kwargs: dict[str, Any] = {
            "model": self._model_id(model_profile),
            "api_key": model_profile["api_key"],
        }
        base_url = model_profile.get("base_url") or parameters.get("base_url")
        if base_url:
            kwargs["base_url"] = str(base_url).rstrip("/")
        for key in ("temperature", "max_tokens", "top_p", "presence_penalty", "frequency_penalty"):
            if key in parameters and parameters[key] is not None:
                kwargs[key] = parameters[key]
        return ChatOpenAI(**kwargs)

    async def _chat_openai_compatible(
        self,
        model_profile: dict,
        messages: list[dict],
    ) -> ModelInvocationResult:
        parameters = self._parameters(model_profile)
        endpoint = str(
            model_profile.get("base_url")
            or parameters.get("base_url")
            or "https://api.openai.com/v1"
        ).rstrip("/")
        model_id = self._model_id(model_profile)
        payload: dict[str, Any] = {
            "model": model_id,
            "messages": messages,
        }
        for key in ("temperature", "max_tokens", "top_p", "presence_penalty", "frequency_penalty"):
            if key in parameters and parameters[key] is not None:
                payload[key] = parameters[key]

        owns_client = self.http_client is None
        client = self.http_client or httpx.AsyncClient(timeout=60)
        try:
            response = await client.post(
                f"{endpoint}/chat/completions",
                headers={
                    "Authorization": f"Bearer {model_profile['api_key']}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            detail = self._provider_error_detail(exc.response)
            raise ModelGatewayError(f"Model provider request failed: {detail}") from exc
        except httpx.HTTPError as exc:
            raise ModelGatewayError(f"Model provider connection failed: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()

        try:
            output_text = str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelGatewayError("Model provider returned an unsupported response format") from exc

        usage = data.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        estimated_cost = round((prompt_tokens + completion_tokens) * 0.000001, 6)
        return ModelInvocationResult(
            output_text=output_text or "Model completed without a text response.",
            provider=provider_name(model_profile),
            model=model_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost=estimated_cost,
        )

    @staticmethod
    def _generate_response(messages: list[dict]) -> str:
        user_content = next(
            (str(message.get("content", "")) for message in reversed(messages) if message.get("role") == "user"),
            "",
        )
        query = user_content
        try:
            parsed = ast.literal_eval(user_content)
            if isinstance(parsed, dict):
                query = str(parsed.get("query") or parsed.get("message") or parsed.get("input") or user_content)
        except (SyntaxError, ValueError):
            pass

        cleaned_query = query.strip()
        if not cleaned_query:
            return "I need a user query before I can respond."
        return (
            "I ran this through the configured agent runtime. "
            f"User request: {cleaned_query}. "
            "A production model connector or approved knowledge source is required before I can provide "
            "specific product facts, rates, eligibility criteria, fees, or regulatory advice."
        )

    @staticmethod
    def _parameters(model_profile: dict) -> dict:
        parameters = model_profile.get("parameters")
        return parameters if isinstance(parameters, dict) else {}

    @staticmethod
    def _model_id(model_profile: dict) -> str:
        configured_model = str(model_profile.get("model", "gpt-4o-mini")).strip()
        if configured_model.lower().startswith("gpt ") or " " in configured_model:
            return configured_model.lower().replace(" ", "-")
        return configured_model

    @staticmethod
    def _to_langchain_messages(messages: list[dict]) -> list[Any]:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        converted_messages = []
        for message in messages:
            role = str(message.get("role", "user")).lower()
            content = str(message.get("content", ""))
            if role == "system":
                converted_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                converted_messages.append(AIMessage(content=content))
            else:
                converted_messages.append(HumanMessage(content=content))
        return converted_messages

    @staticmethod
    def _langchain_usage(response: Any) -> dict:
        usage = getattr(response, "usage_metadata", None)
        if isinstance(usage, dict):
            return usage
        response_metadata = getattr(response, "response_metadata", None)
        if isinstance(response_metadata, dict):
            token_usage = response_metadata.get("token_usage")
            if isinstance(token_usage, dict):
                return token_usage
        return {}

    @staticmethod
    def _provider_error_detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text or response.reason_phrase
        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict):
            return str(error.get("message") or error)
        return str(payload)


def provider_name(model_profile: dict) -> str:
    return str(model_profile.get("provider", "OpenAI"))
