from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from platform_common.domain.models import AgentRun


class StartRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    agent_version: str = Field(min_length=1)
    input: dict[str, Any] = Field(default_factory=dict)


class AgentRunResponse(BaseModel):
    run: AgentRun


class AgentRunListResponse(BaseModel):
    runs: list[AgentRun]
