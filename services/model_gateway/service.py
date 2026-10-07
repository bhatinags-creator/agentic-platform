from dataclasses import dataclass


@dataclass
class ModelInvocationResult:
    output_text: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost: float = 0.0

class ModelGatewayService:
    async def chat(self, model_profile: dict, messages: list[dict]) -> ModelInvocationResult:
        return ModelInvocationResult(
            output_text="MVP model gateway response",
            provider=model_profile.get("provider", "mock"),
            model=model_profile.get("model", "mock-model"),
            prompt_tokens=sum(len(str(m)) for m in messages),
            completion_tokens=5,
        )
