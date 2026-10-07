from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from platform_common.domain.models import AgentManifest, AgentVersion, RiskClass
from services.agent_registry.service import AgentRegistryService


class AgentDraftStatus(StrEnum):
    DRAFT = "draft"
    VALIDATED = "validated"
    PUBLISHED = "published"


class AgentTestStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"


class AgentDraft(BaseModel):
    draft_id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    manifest: AgentManifest
    risk_class: RiskClass = RiskClass.MEDIUM
    status: AgentDraftStatus = AgentDraftStatus.DRAFT
    agent_id: UUID | None = None
    published_version_id: UUID | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentDraftValidationResult(BaseModel):
    draft_id: UUID
    valid: bool
    errors: list[str] = Field(default_factory=list)


class AgentTestCase(BaseModel):
    test_case_id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1)
    input: dict = Field(default_factory=dict)
    expected_contains: str | None = None


class AgentTestRunResult(BaseModel):
    test_run_id: UUID = Field(default_factory=uuid4)
    draft_id: UUID
    status: AgentTestStatus
    checked_cases: int
    failures: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentDraftNotFoundError(Exception):
    """Raised when an Agent Studio draft is not visible to the requested tenant."""


class AgentDraftAlreadyPublishedError(Exception):
    """Raised when a caller tries to modify or republish an already published draft."""


class AgentStudioService:
    """Manages Agent Studio draft design, validation, publish, and test workflows."""

    def __init__(self, registry: AgentRegistryService) -> None:
        self.registry = registry
        self._drafts: dict[UUID, AgentDraft] = {}
        self._test_runs: dict[UUID, AgentTestRunResult] = {}

    def create_draft(
        self,
        *,
        tenant_id: str,
        name: str,
        owner: str,
        manifest: AgentManifest,
        risk_class: RiskClass = RiskClass.MEDIUM,
    ) -> AgentDraft:
        draft = AgentDraft(
            tenant_id=tenant_id,
            name=name,
            owner=owner,
            manifest=manifest,
            risk_class=risk_class,
        )
        self._drafts[draft.draft_id] = draft
        return draft

    def get_draft(self, tenant_id: str, draft_id: UUID | str) -> AgentDraft:
        draft_uuid = self._parse_uuid(draft_id)
        draft = self._drafts.get(draft_uuid)
        if draft is None or draft.tenant_id != tenant_id:
            raise AgentDraftNotFoundError(f"Agent Studio draft not found: {draft_id}")
        return draft

    def list_drafts(self, tenant_id: str) -> list[AgentDraft]:
        return sorted(
            [draft for draft in self._drafts.values() if draft.tenant_id == tenant_id],
            key=lambda draft: draft.created_at,
        )

    def update_draft(
        self,
        *,
        tenant_id: str,
        draft_id: UUID | str,
        name: str | None = None,
        owner: str | None = None,
        manifest: AgentManifest | None = None,
        risk_class: RiskClass | None = None,
    ) -> AgentDraft:
        draft = self.get_draft(tenant_id, draft_id)
        if draft.status == AgentDraftStatus.PUBLISHED:
            raise AgentDraftAlreadyPublishedError(f"Published draft cannot be updated: {draft_id}")

        updated_draft = draft.model_copy(
            update={
                "name": name or draft.name,
                "owner": owner or draft.owner,
                "manifest": manifest or draft.manifest,
                "risk_class": risk_class or draft.risk_class,
                "status": AgentDraftStatus.DRAFT,
                "updated_at": datetime.now(UTC),
            }
        )
        self._drafts[updated_draft.draft_id] = updated_draft
        return updated_draft

    def validate_draft(self, tenant_id: str, draft_id: UUID | str) -> AgentDraftValidationResult:
        draft = self.get_draft(tenant_id, draft_id)
        errors = self._validate_manifest_alignment(draft)
        if not errors and draft.status != AgentDraftStatus.PUBLISHED:
            self._drafts[draft.draft_id] = draft.model_copy(
                update={"status": AgentDraftStatus.VALIDATED, "updated_at": datetime.now(UTC)}
            )
        return AgentDraftValidationResult(
            draft_id=draft.draft_id,
            valid=not errors,
            errors=errors,
        )

    def run_test_harness(
        self,
        *,
        tenant_id: str,
        draft_id: UUID | str,
        test_cases: list[AgentTestCase],
    ) -> AgentTestRunResult:
        draft = self.get_draft(tenant_id, draft_id)
        validation = self.validate_draft(tenant_id, draft.draft_id)
        failures = [f"validation: {error}" for error in validation.errors]
        normalized_cases = [case if isinstance(case, AgentTestCase) else AgentTestCase.model_validate(case) for case in test_cases]
        for test_case in normalized_cases:
            simulated_output = self._simulate_test_output(draft, test_case)
            if test_case.expected_contains and test_case.expected_contains not in simulated_output:
                failures.append(
                    f"{test_case.name}: expected output to contain {test_case.expected_contains!r}"
                )
        result = AgentTestRunResult(
            draft_id=draft.draft_id,
            status=AgentTestStatus.FAILED if failures else AgentTestStatus.PASSED,
            checked_cases=len(normalized_cases),
            failures=failures,
        )
        self._test_runs[result.test_run_id] = result
        return result

    def publish_draft(self, tenant_id: str, draft_id: UUID | str) -> AgentVersion:
        draft = self.get_draft(tenant_id, draft_id)
        if draft.status == AgentDraftStatus.PUBLISHED:
            raise AgentDraftAlreadyPublishedError(f"Draft already published: {draft_id}")

        validation = self.validate_draft(tenant_id, draft.draft_id)
        if not validation.valid:
            raise ValueError("Agent Studio draft is not valid: " + "; ".join(validation.errors))

        agent = self.registry.create_agent(
            tenant_id=tenant_id,
            name=draft.name,
            owner=draft.owner,
            risk_class=draft.risk_class,
        )
        version = self.registry.publish_version(
            tenant_id=tenant_id,
            agent_id=agent.agent_id,
            manifest=draft.manifest,
        )
        self._drafts[draft.draft_id] = draft.model_copy(
            update={
                "status": AgentDraftStatus.PUBLISHED,
                "agent_id": agent.agent_id,
                "published_version_id": version.version_id,
                "updated_at": datetime.now(UTC),
            }
        )
        return version

    @staticmethod
    def _validate_manifest_alignment(draft: AgentDraft) -> list[str]:
        errors: list[str] = []
        if draft.manifest.name != draft.name:
            errors.append("draft name must match manifest name")
        if draft.manifest.version.strip() == "":
            errors.append("manifest version is required")
        if draft.manifest.model.provider.strip() == "":
            errors.append("manifest model provider is required")
        if draft.manifest.model.model.strip() == "":
            errors.append("manifest model name is required")
        return errors

    @staticmethod
    def _simulate_test_output(draft: AgentDraft, test_case: AgentTestCase) -> str:
        return f"{draft.manifest.role}: {draft.manifest.goal}; input={test_case.input}"

    @staticmethod
    def _parse_uuid(value: UUID | str) -> UUID:
        if isinstance(value, UUID):
            return value
        return UUID(value)

