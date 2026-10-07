from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class KnowledgeBaseStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class IngestionJobStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class RetrievalSafetyStatus(StrEnum):
    PASSED = "passed"
    REVIEW_REQUIRED = "review_required"


class KnowledgeBase(BaseModel):
    knowledge_base_id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str | None = None
    source_type: str = "local"
    status: KnowledgeBaseStatus = KnowledgeBaseStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class KnowledgeDocument(BaseModel):
    document_id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(min_length=1)
    knowledge_base_id: UUID
    title: str = Field(min_length=1)
    source_uri: str | None = None
    content: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DocumentChunk(BaseModel):
    chunk_id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(min_length=1)
    document_id: UUID
    knowledge_base_id: UUID
    text: str = Field(min_length=1)
    chunk_index: int = Field(ge=0)


class IngestionJob(BaseModel):
    job_id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(min_length=1)
    knowledge_base_id: UUID
    document_id: UUID | None = None
    status: IngestionJobStatus
    chunks_created: int = 0
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Citation(BaseModel):
    document_id: UUID | str
    chunk_id: UUID | str
    source_uri: str | None = None
    title: str | None = None


class RetrievalResult(BaseModel):
    document_id: UUID | str
    chunk_id: UUID | str
    text: str
    score: float = Field(ge=0, le=1)
    citation: Citation
    safety_status: RetrievalSafetyStatus = RetrievalSafetyStatus.PASSED
    safety_findings: list[str] = Field(default_factory=list)


class RetrievalGovernanceReport(BaseModel):
    status: RetrievalSafetyStatus
    findings: list[str] = Field(default_factory=list)
    citation_count: int = 0


class KnowledgeBaseNotFoundError(Exception):
    """Raised when a knowledge base is not visible to the requested tenant."""


class RAGPlatformService:
    POISONING_TERMS: ClassVar[list[str]] = ["ignore previous", "jailbreak", "exfiltrate", "reveal system prompt"]

    def __init__(self) -> None:
        self._knowledge_bases: dict[UUID, KnowledgeBase] = {}
        self._documents: dict[UUID, KnowledgeDocument] = {}
        self._chunks: dict[UUID, DocumentChunk] = {}
        self._jobs: dict[UUID, IngestionJob] = {}
        self._ensure_default_content()

    def create_knowledge_base(
        self,
        *,
        tenant_id: str,
        name: str,
        description: str | None = None,
        source_type: str = "local",
    ) -> KnowledgeBase:
        knowledge_base = KnowledgeBase(
            tenant_id=tenant_id,
            name=name,
            description=description,
            source_type=source_type,
        )
        self._knowledge_bases[knowledge_base.knowledge_base_id] = knowledge_base
        return knowledge_base

    def get_knowledge_base(self, tenant_id: str, knowledge_base_id: UUID | str) -> KnowledgeBase:
        kb_uuid = knowledge_base_id if isinstance(knowledge_base_id, UUID) else UUID(knowledge_base_id)
        knowledge_base = self._knowledge_bases.get(kb_uuid)
        if knowledge_base is None or knowledge_base.tenant_id != tenant_id:
            raise KnowledgeBaseNotFoundError(f"Knowledge base not found: {knowledge_base_id}")
        return knowledge_base

    def list_knowledge_bases(self, tenant_id: str) -> list[KnowledgeBase]:
        return sorted(
            [kb for kb in self._knowledge_bases.values() if kb.tenant_id == tenant_id],
            key=lambda kb: kb.created_at,
        )

    def ingest_document(
        self,
        *,
        tenant_id: str,
        knowledge_base_id: UUID | str,
        title: str,
        content: str,
        source_uri: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> IngestionJob:
        knowledge_base = self.get_knowledge_base(tenant_id, knowledge_base_id)
        document = KnowledgeDocument(
            tenant_id=tenant_id,
            knowledge_base_id=knowledge_base.knowledge_base_id,
            title=title,
            source_uri=source_uri,
            content=content,
            metadata=metadata or {},
        )
        self._documents[document.document_id] = document
        chunks = self._chunk_document(document)
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk
        job = IngestionJob(
            tenant_id=tenant_id,
            knowledge_base_id=knowledge_base.knowledge_base_id,
            document_id=document.document_id,
            status=IngestionJobStatus.COMPLETED,
            chunks_created=len(chunks),
        )
        self._jobs[job.job_id] = job
        return job

    async def retrieve(self, query: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        tenant_id = context.get("tenant_id", "default")
        knowledge_base_id = context.get("knowledge_base_id")
        results = self.search(
            tenant_id=tenant_id,
            query=query,
            knowledge_base_id=knowledge_base_id,
        )
        if not results and tenant_id != "default":
            results = self.search(tenant_id="default", query=query)
        return [self._result_to_runtime_dict(result) for result in results]

    def search(
        self,
        *,
        tenant_id: str,
        query: str,
        knowledge_base_id: UUID | str | None = None,
        limit: int = 5,
    ) -> list[RetrievalResult]:
        terms = {term.lower() for term in query.split() if term.strip()}
        kb_uuid = UUID(str(knowledge_base_id)) if knowledge_base_id else None
        scored: list[tuple[float, DocumentChunk]] = []
        for chunk in self._chunks.values():
            if chunk.tenant_id != tenant_id:
                continue
            if kb_uuid and chunk.knowledge_base_id != kb_uuid:
                continue
            chunk_terms = set(chunk.text.lower().split())
            score = len(terms & chunk_terms) / max(len(terms), 1)
            if score > 0 or not terms:
                scored.append((max(score, 0.01), chunk))
        if not scored:
            scored = [
                (0.01, chunk)
                for chunk in self._chunks.values()
                if chunk.tenant_id == tenant_id
                and (kb_uuid is None or chunk.knowledge_base_id == kb_uuid)
            ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [self._chunk_to_result(chunk, min(score, 1.0)) for score, chunk in scored[:limit]]

    def govern_retrievals(self, results: list[RetrievalResult]) -> RetrievalGovernanceReport:
        findings: list[str] = []
        for result in results:
            findings.extend(result.safety_findings)
            if not result.citation:
                findings.append("missing citation")
        return RetrievalGovernanceReport(
            status=RetrievalSafetyStatus.REVIEW_REQUIRED if findings else RetrievalSafetyStatus.PASSED,
            findings=findings,
            citation_count=len([result for result in results if result.citation]),
        )

    def list_ingestion_jobs(self, tenant_id: str) -> list[IngestionJob]:
        return sorted(
            [job for job in self._jobs.values() if job.tenant_id == tenant_id],
            key=lambda job: job.created_at,
        )

    def _chunk_document(self, document: KnowledgeDocument, chunk_size: int = 400) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        content = document.content.strip()
        for index, start in enumerate(range(0, len(content), chunk_size)):
            text = content[start : start + chunk_size].strip()
            if text:
                chunks.append(
                    DocumentChunk(
                        tenant_id=document.tenant_id,
                        document_id=document.document_id,
                        knowledge_base_id=document.knowledge_base_id,
                        text=text,
                        chunk_index=index,
                    )
                )
        return chunks

    def _chunk_to_result(self, chunk: DocumentChunk, score: float) -> RetrievalResult:
        document = self._documents[chunk.document_id]
        findings = [term for term in self.POISONING_TERMS if term in chunk.text.lower()]
        return RetrievalResult(
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            text=chunk.text,
            score=score,
            citation=Citation(
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                source_uri=document.source_uri,
                title=document.title,
            ),
            safety_status=RetrievalSafetyStatus.REVIEW_REQUIRED
            if findings
            else RetrievalSafetyStatus.PASSED,
            safety_findings=[f"potential RAG poisoning term: {term}" for term in findings],
        )

    @staticmethod
    def _result_to_runtime_dict(result: RetrievalResult) -> dict[str, Any]:
        return {
            "document_id": str(result.document_id),
            "chunk_id": str(result.chunk_id),
            "text": result.text,
            "score": result.score,
            "citation": result.citation.title or result.citation.source_uri or str(result.document_id),
            "safety_status": result.safety_status,
            "safety_findings": result.safety_findings,
        }

    def _ensure_default_content(self) -> None:
        if self._knowledge_bases:
            return
        kb = self.create_knowledge_base(
            tenant_id="default",
            name="mvp-default-knowledge",
            description="Default local knowledge base for the runtime MVP path.",
        )
        self.ingest_document(
            tenant_id="default",
            knowledge_base_id=kb.knowledge_base_id,
            title="MVP source section 1",
            content="MVP retrieved context for customer support and enterprise agent testing.",
            source_uri="mvp://source/section-1",
        )

