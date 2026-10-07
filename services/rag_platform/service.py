from typing import Any


class RAGPlatformService:
    async def retrieve(self, query: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        return [{"document_id": "doc-mvp-001", "chunk_id": "chunk-001", "text": "MVP retrieved context.", "score": 0.99, "citation": "MVP source section 1"}]
