from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from string import Formatter
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class PromptTemplateStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


class PromptTemplate(BaseModel):
    template_id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str | None = None
    owner: str = Field(min_length=1)
    status: PromptTemplateStatus = PromptTemplateStatus.DRAFT
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PromptVersion(BaseModel):
    version_id: UUID = Field(default_factory=uuid4)
    template_id: UUID
    version: str = Field(min_length=1)
    template_text: str = Field(min_length=1)
    variables: list[str] = Field(default_factory=list)
    status: PromptTemplateStatus = PromptTemplateStatus.DRAFT
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PromptRenderResult(BaseModel):
    template_id: UUID
    version_id: UUID
    rendered_text: str
    variables_used: dict[str, str]


class PromptTemplateNotFoundError(Exception):
    """Raised when a prompt template is not visible to the requested tenant."""


class PromptVersionNotFoundError(Exception):
    """Raised when a prompt version does not exist for a tenant-visible template."""


class PromptValidationError(Exception):
    """Raised when prompt variables and supplied values do not match."""


class PromptManagementService:
    def __init__(self) -> None:
        self._templates: dict[UUID, PromptTemplate] = {}
        self._versions: dict[UUID, PromptVersion] = {}

    def create_template(
        self,
        *,
        tenant_id: str,
        name: str,
        owner: str,
        description: str | None = None,
    ) -> PromptTemplate:
        template = PromptTemplate(
            tenant_id=tenant_id,
            name=name,
            owner=owner,
            description=description,
        )
        self._templates[template.template_id] = template
        return template

    def create_version(
        self,
        *,
        tenant_id: str,
        template_id: UUID | str,
        version: str,
        template_text: str,
    ) -> PromptVersion:
        template = self.get_template(tenant_id, template_id)
        variables = self._extract_variables(template_text)
        prompt_version = PromptVersion(
            template_id=template.template_id,
            version=version,
            template_text=template_text,
            variables=variables,
        )
        self._versions[prompt_version.version_id] = prompt_version
        return prompt_version

    def publish_version(self, tenant_id: str, version_id: UUID | str) -> PromptVersion:
        prompt_version = self.get_version(tenant_id, version_id)
        published = prompt_version.model_copy(update={"status": PromptTemplateStatus.PUBLISHED})
        self._versions[published.version_id] = published
        template = self.get_template(tenant_id, published.template_id)
        self._templates[template.template_id] = template.model_copy(
            update={"status": PromptTemplateStatus.PUBLISHED}
        )
        return published

    def render(
        self,
        *,
        tenant_id: str,
        version_id: UUID | str,
        variables: dict[str, str],
    ) -> PromptRenderResult:
        prompt_version = self.get_version(tenant_id, version_id)
        missing_variables = [name for name in prompt_version.variables if name not in variables]
        if missing_variables:
            raise PromptValidationError("Missing prompt variables: " + ", ".join(missing_variables))
        rendered_text = prompt_version.template_text.format(**variables)
        return PromptRenderResult(
            template_id=prompt_version.template_id,
            version_id=prompt_version.version_id,
            rendered_text=rendered_text,
            variables_used={name: variables[name] for name in prompt_version.variables},
        )

    def get_template(self, tenant_id: str, template_id: UUID | str) -> PromptTemplate:
        template_uuid = self._parse_uuid(template_id)
        template = self._templates.get(template_uuid)
        if template is None or template.tenant_id != tenant_id:
            raise PromptTemplateNotFoundError(f"Prompt template not found: {template_id}")
        return template

    def get_version(self, tenant_id: str, version_id: UUID | str) -> PromptVersion:
        version_uuid = self._parse_uuid(version_id)
        prompt_version = self._versions.get(version_uuid)
        if prompt_version is None:
            raise PromptVersionNotFoundError(f"Prompt version not found: {version_id}")
        self.get_template(tenant_id, prompt_version.template_id)
        return prompt_version

    def list_templates(self, tenant_id: str) -> list[PromptTemplate]:
        return sorted(
            [template for template in self._templates.values() if template.tenant_id == tenant_id],
            key=lambda template: template.created_at,
        )

    @staticmethod
    def _extract_variables(template_text: str) -> list[str]:
        return sorted(
            {
                field_name
                for _, field_name, _, _ in Formatter().parse(template_text)
                if field_name
            }
        )

    @staticmethod
    def _parse_uuid(value: UUID | str) -> UUID:
        if isinstance(value, UUID):
            return value
        return UUID(value)
