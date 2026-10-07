from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AISecOpsSignalType(StrEnum):
    PROMPT_ATTACK = "prompt_attack"
    AGENT_BEHAVIOR = "agent_behavior"
    RAG_POISONING = "rag_poisoning"
    MODEL_DRIFT = "model_drift"
    TOOL_ABUSE = "tool_abuse"
    ANOMALY = "anomaly"


class AISecOpsSeverity(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AISecOpsStatus(StrEnum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    MITIGATED = "mitigated"
    FALSE_POSITIVE = "false_positive"


class AISecOpsSignal(BaseModel):
    signal_id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    signal_type: AISecOpsSignalType
    severity: AISecOpsSeverity
    description: str = Field(min_length=1)
    evidence: dict = Field(default_factory=dict)
    run_id: str | None = None
    trace_id: str | None = None
    status: AISecOpsStatus = AISecOpsStatus.OPEN
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PromptAttackMonitoringRecord(AISecOpsSignal):
    signal_type: AISecOpsSignalType = AISecOpsSignalType.PROMPT_ATTACK
    attack_terms: list[str] = Field(default_factory=list)


class AgentBehaviorMonitoringRecord(AISecOpsSignal):
    signal_type: AISecOpsSignalType = AISecOpsSignalType.AGENT_BEHAVIOR
    behavior: str = Field(min_length=1)


class RAGPoisoningMonitoringRecord(AISecOpsSignal):
    signal_type: AISecOpsSignalType = AISecOpsSignalType.RAG_POISONING
    knowledge_source: str = Field(min_length=1)


class ModelDriftMonitoringRecord(AISecOpsSignal):
    signal_type: AISecOpsSignalType = AISecOpsSignalType.MODEL_DRIFT
    drift_score: float = Field(ge=0, le=1)


class ToolAbuseMonitoringRecord(AISecOpsSignal):
    signal_type: AISecOpsSignalType = AISecOpsSignalType.TOOL_ABUSE
    tool_name: str = Field(min_length=1)


class AnomalyDetectionRecord(AISecOpsSignal):
    signal_type: AISecOpsSignalType = AISecOpsSignalType.ANOMALY
    anomaly_score: float = Field(ge=0, le=1)


class AISecOpsSummary(BaseModel):
    tenant_id: str
    total_signals: int
    open_signals: int
    critical_signals: int
    high_signals: int
    by_type: dict[AISecOpsSignalType, int]


class AISecOpsSignalNotFoundError(Exception):
    """Raised when an AISecOps signal cannot be found for the requested tenant."""


class AISecOpsMonitoringService:
    PROMPT_ATTACK_TERMS: ClassVar[list[str]] = [
        "ignore instructions",
        "ignore previous",
        "jailbreak",
        "exfiltrate",
        "reveal system prompt",
        "developer message",
    ]

    def __init__(self) -> None:
        self._signals: dict[UUID, AISecOpsSignal] = {}

    def inspect_prompt(
        self,
        prompt: str,
        *,
        tenant_id: str = "default",
        agent_id: str = "unknown",
        run_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict:
        lowered_prompt = prompt.lower()
        matched_terms = [term for term in self.PROMPT_ATTACK_TERMS if term in lowered_prompt]
        if not matched_terms:
            return {"signal": "none", "severity": AISecOpsSeverity.NONE}

        record = self.record_prompt_attack(
            tenant_id=tenant_id,
            agent_id=agent_id,
            prompt=prompt,
            attack_terms=matched_terms,
            run_id=run_id,
            trace_id=trace_id,
        )
        return {
            "signal": record.signal_type,
            "severity": record.severity,
            "signal_id": str(record.signal_id),
        }

    def record_prompt_attack(
        self,
        *,
        tenant_id: str,
        agent_id: str,
        prompt: str,
        attack_terms: list[str] | None = None,
        run_id: str | None = None,
        trace_id: str | None = None,
    ) -> PromptAttackMonitoringRecord:
        terms = attack_terms or [
            term for term in self.PROMPT_ATTACK_TERMS if term in prompt.lower()
        ]
        record = PromptAttackMonitoringRecord(
            tenant_id=tenant_id,
            agent_id=agent_id,
            severity=AISecOpsSeverity.HIGH if terms else AISecOpsSeverity.LOW,
            description="Potential prompt attack detected",
            evidence={"prompt_excerpt": prompt[:250]},
            attack_terms=terms,
            run_id=run_id,
            trace_id=trace_id,
        )
        return self._save(record)

    def record_agent_behavior(
        self,
        *,
        tenant_id: str,
        agent_id: str,
        behavior: str,
        severity: AISecOpsSeverity = AISecOpsSeverity.MEDIUM,
        evidence: dict | None = None,
        run_id: str | None = None,
        trace_id: str | None = None,
    ) -> AgentBehaviorMonitoringRecord:
        record = AgentBehaviorMonitoringRecord(
            tenant_id=tenant_id,
            agent_id=agent_id,
            severity=severity,
            description="Suspicious agent behavior detected",
            evidence=evidence or {},
            behavior=behavior,
            run_id=run_id,
            trace_id=trace_id,
        )
        return self._save(record)

    def record_rag_poisoning(
        self,
        *,
        tenant_id: str,
        agent_id: str,
        knowledge_source: str,
        evidence: dict,
        severity: AISecOpsSeverity = AISecOpsSeverity.HIGH,
        run_id: str | None = None,
        trace_id: str | None = None,
    ) -> RAGPoisoningMonitoringRecord:
        record = RAGPoisoningMonitoringRecord(
            tenant_id=tenant_id,
            agent_id=agent_id,
            severity=severity,
            description="Potential RAG poisoning detected",
            evidence=evidence,
            knowledge_source=knowledge_source,
            run_id=run_id,
            trace_id=trace_id,
        )
        return self._save(record)

    def record_model_drift(
        self,
        *,
        tenant_id: str,
        agent_id: str,
        drift_score: float,
        baseline_ref: str,
        run_id: str | None = None,
        trace_id: str | None = None,
    ) -> ModelDriftMonitoringRecord:
        record = ModelDriftMonitoringRecord(
            tenant_id=tenant_id,
            agent_id=agent_id,
            severity=self._severity_from_score(drift_score),
            description="Model drift threshold signal recorded",
            evidence={"baseline_ref": baseline_ref},
            drift_score=drift_score,
            run_id=run_id,
            trace_id=trace_id,
        )
        return self._save(record)

    def record_tool_abuse(
        self,
        *,
        tenant_id: str,
        agent_id: str,
        tool_name: str,
        evidence: dict,
        severity: AISecOpsSeverity = AISecOpsSeverity.HIGH,
        run_id: str | None = None,
        trace_id: str | None = None,
    ) -> ToolAbuseMonitoringRecord:
        record = ToolAbuseMonitoringRecord(
            tenant_id=tenant_id,
            agent_id=agent_id,
            severity=severity,
            description="Suspicious tool usage detected",
            evidence=evidence,
            tool_name=tool_name,
            run_id=run_id,
            trace_id=trace_id,
        )
        return self._save(record)

    def record_anomaly(
        self,
        *,
        tenant_id: str,
        agent_id: str,
        anomaly_score: float,
        evidence: dict,
        run_id: str | None = None,
        trace_id: str | None = None,
    ) -> AnomalyDetectionRecord:
        record = AnomalyDetectionRecord(
            tenant_id=tenant_id,
            agent_id=agent_id,
            severity=self._severity_from_score(anomaly_score),
            description="Runtime anomaly detected",
            evidence=evidence,
            anomaly_score=anomaly_score,
            run_id=run_id,
            trace_id=trace_id,
        )
        return self._save(record)

    def list_signals(
        self,
        tenant_id: str,
        *,
        signal_type: AISecOpsSignalType | str | None = None,
        severity: AISecOpsSeverity | str | None = None,
        status: AISecOpsStatus | str | None = None,
    ) -> list[AISecOpsSignal]:
        resolved_type = AISecOpsSignalType(signal_type) if signal_type else None
        resolved_severity = AISecOpsSeverity(severity) if severity else None
        resolved_status = AISecOpsStatus(status) if status else None
        return sorted(
            [
                signal
                for signal in self._signals.values()
                if signal.tenant_id == tenant_id
                and (resolved_type is None or signal.signal_type == resolved_type)
                and (resolved_severity is None or signal.severity == resolved_severity)
                and (resolved_status is None or signal.status == resolved_status)
            ],
            key=lambda signal: signal.created_at,
        )

    def update_signal_status(
        self,
        tenant_id: str,
        signal_id: UUID | str,
        status: AISecOpsStatus | str,
    ) -> AISecOpsSignal:
        signal_uuid = self._parse_uuid(signal_id)
        signal = self._signals.get(signal_uuid)
        if signal is None or signal.tenant_id != tenant_id:
            raise AISecOpsSignalNotFoundError(f"AISecOps signal not found: {signal_id}")
        updated = signal.model_copy(update={"status": AISecOpsStatus(status)})
        self._signals[updated.signal_id] = updated
        return updated

    def summarize_tenant(self, tenant_id: str) -> AISecOpsSummary:
        signals = self.list_signals(tenant_id)
        return AISecOpsSummary(
            tenant_id=tenant_id,
            total_signals=len(signals),
            open_signals=sum(signal.status == AISecOpsStatus.OPEN for signal in signals),
            critical_signals=sum(
                signal.severity == AISecOpsSeverity.CRITICAL for signal in signals
            ),
            high_signals=sum(signal.severity == AISecOpsSeverity.HIGH for signal in signals),
            by_type={
                signal_type: sum(signal.signal_type == signal_type for signal in signals)
                for signal_type in AISecOpsSignalType
            },
        )

    def _save(self, signal: AISecOpsSignal) -> AISecOpsSignal:
        self._signals[signal.signal_id] = signal
        return signal

    @staticmethod
    def _severity_from_score(score: float) -> AISecOpsSeverity:
        if score >= 0.9:
            return AISecOpsSeverity.CRITICAL
        if score >= 0.7:
            return AISecOpsSeverity.HIGH
        if score >= 0.4:
            return AISecOpsSeverity.MEDIUM
        return AISecOpsSeverity.LOW

    @staticmethod
    def _parse_uuid(value: UUID | str) -> UUID:
        if isinstance(value, UUID):
            return value
        return UUID(value)

