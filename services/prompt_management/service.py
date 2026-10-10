from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from contextlib import closing
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
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


class PromptRepository(ABC):
    @abstractmethod
    def save_template(self, template: PromptTemplate) -> PromptTemplate:
        raise NotImplementedError

    @abstractmethod
    def get_template(self, tenant_id: str, template_id: UUID) -> PromptTemplate | None:
        raise NotImplementedError

    @abstractmethod
    def list_templates(self, tenant_id: str) -> list[PromptTemplate]:
        raise NotImplementedError

    @abstractmethod
    def save_version(self, version: PromptVersion, tenant_id: str) -> PromptVersion:
        raise NotImplementedError

    @abstractmethod
    def get_version(self, tenant_id: str, version_id: UUID) -> PromptVersion | None:
        raise NotImplementedError

    @abstractmethod
    def list_versions(self, tenant_id: str, template_id: UUID | None = None) -> list[PromptVersion]:
        raise NotImplementedError


class InMemoryPromptRepository(PromptRepository):
    def __init__(self) -> None:
        self._templates: dict[UUID, PromptTemplate] = {}
        self._versions: dict[UUID, PromptVersion] = {}

    def save_template(self, template: PromptTemplate) -> PromptTemplate:
        self._templates[template.template_id] = template
        return template

    def get_template(self, tenant_id: str, template_id: UUID) -> PromptTemplate | None:
        template = self._templates.get(template_id)
        if template is None or template.tenant_id != tenant_id:
            return None
        return template

    def list_templates(self, tenant_id: str) -> list[PromptTemplate]:
        return sorted(
            [template for template in self._templates.values() if template.tenant_id == tenant_id],
            key=lambda template: template.created_at,
        )

    def save_version(self, version: PromptVersion, tenant_id: str) -> PromptVersion:
        self._versions[version.version_id] = version
        return version

    def get_version(self, tenant_id: str, version_id: UUID) -> PromptVersion | None:
        prompt_version = self._versions.get(version_id)
        if prompt_version is None:
            return None
        if self.get_template(tenant_id, prompt_version.template_id) is None:
            return None
        return prompt_version

    def list_versions(self, tenant_id: str, template_id: UUID | None = None) -> list[PromptVersion]:
        visible_template_ids = {template.template_id for template in self.list_templates(tenant_id)}
        if template_id is not None:
            visible_template_ids = {template_id}
        return sorted(
            [version for version in self._versions.values() if version.template_id in visible_template_ids],
            key=lambda version: version.created_at,
        )


class SQLitePromptRepository(PromptRepository):
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def save_template(self, template: PromptTemplate) -> PromptTemplate:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO prompt_templates (
                    template_id, tenant_id, name, owner, status, created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(template_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    name = excluded.name,
                    owner = excluded.owner,
                    status = excluded.status,
                    payload_json = excluded.payload_json
                """,
                (
                    str(template.template_id),
                    template.tenant_id,
                    template.name,
                    template.owner,
                    template.status.value,
                    template.created_at.isoformat(),
                    template.model_dump_json(),
                ),
            )
        return template

    def get_template(self, tenant_id: str, template_id: UUID) -> PromptTemplate | None:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                "SELECT payload_json FROM prompt_templates WHERE tenant_id = ? AND template_id = ?",
                (tenant_id, str(template_id)),
            ).fetchone()
        return self._template_from_row(row)

    def list_templates(self, tenant_id: str) -> list[PromptTemplate]:
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                "SELECT payload_json FROM prompt_templates WHERE tenant_id = ? ORDER BY created_at ASC",
                (tenant_id,),
            ).fetchall()
        return [PromptTemplate.model_validate_json(row["payload_json"]) for row in rows]

    def save_version(self, version: PromptVersion, tenant_id: str) -> PromptVersion:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO prompt_versions (
                    version_id, tenant_id, template_id, version, status, created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(version_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    template_id = excluded.template_id,
                    version = excluded.version,
                    status = excluded.status,
                    payload_json = excluded.payload_json
                """,
                (
                    str(version.version_id),
                    tenant_id,
                    str(version.template_id),
                    version.version,
                    version.status.value,
                    version.created_at.isoformat(),
                    version.model_dump_json(),
                ),
            )
        return version

    def get_version(self, tenant_id: str, version_id: UUID) -> PromptVersion | None:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                "SELECT payload_json FROM prompt_versions WHERE tenant_id = ? AND version_id = ?",
                (tenant_id, str(version_id)),
            ).fetchone()
        return self._version_from_row(row)

    def list_versions(self, tenant_id: str, template_id: UUID | None = None) -> list[PromptVersion]:
        query = "SELECT payload_json FROM prompt_versions WHERE tenant_id = ?"
        params: list[str] = [tenant_id]
        if template_id is not None:
            query += " AND template_id = ?"
            params.append(str(template_id))
        query += " ORDER BY created_at ASC"
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(query, params).fetchall()
        return [PromptVersion.model_validate_json(row["payload_json"]) for row in rows]

    def _initialize_schema(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS prompt_templates (
                    template_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_prompt_templates_tenant_created
                    ON prompt_templates (tenant_id, created_at);

                CREATE TABLE IF NOT EXISTS prompt_versions (
                    version_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    template_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_prompt_versions_template_created
                    ON prompt_versions (tenant_id, template_id, created_at);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _template_from_row(row: sqlite3.Row | None) -> PromptTemplate | None:
        if row is None:
            return None
        return PromptTemplate.model_validate_json(row["payload_json"])

    @staticmethod
    def _version_from_row(row: sqlite3.Row | None) -> PromptVersion | None:
        if row is None:
            return None
        return PromptVersion.model_validate_json(row["payload_json"])


class PromptManagementService:
    def __init__(self, repository: PromptRepository | None = None) -> None:
        self.repository = repository or InMemoryPromptRepository()

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
        return self.repository.save_template(template)

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
        return self.repository.save_version(prompt_version, tenant_id)

    def publish_version(self, tenant_id: str, version_id: UUID | str) -> PromptVersion:
        prompt_version = self.get_version(tenant_id, version_id)
        published = prompt_version.model_copy(update={"status": PromptTemplateStatus.PUBLISHED})
        self.repository.save_version(published, tenant_id)
        template = self.get_template(tenant_id, published.template_id)
        self.repository.save_template(template.model_copy(update={"status": PromptTemplateStatus.PUBLISHED}))
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
        template = self.repository.get_template(tenant_id, template_uuid)
        if template is None:
            raise PromptTemplateNotFoundError(f"Prompt template not found: {template_id}")
        return template

    def get_version(self, tenant_id: str, version_id: UUID | str) -> PromptVersion:
        version_uuid = self._parse_uuid(version_id)
        prompt_version = self.repository.get_version(tenant_id, version_uuid)
        if prompt_version is None:
            raise PromptVersionNotFoundError(f"Prompt version not found: {version_id}")
        return prompt_version

    def list_templates(self, tenant_id: str) -> list[PromptTemplate]:
        return self.repository.list_templates(tenant_id)

    def list_versions(
        self,
        tenant_id: str,
        template_id: UUID | str | None = None,
    ) -> list[PromptVersion]:
        if template_id is not None:
            template = self.get_template(tenant_id, template_id)
            return self.repository.list_versions(tenant_id, template.template_id)
        return self.repository.list_versions(tenant_id)

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
