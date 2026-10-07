from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ResponsibleAIStatus(StrEnum):
    PASSED = "passed"
    REVIEW_REQUIRED = "review_required"
    FAILED = "failed"
    REGISTERED = "registered"


class FairnessTestResult(BaseModel):
    test_id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    agent_id: str
    metric: str
    score: float = Field(ge=0, le=1)
    status: ResponsibleAIStatus
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BiasDetectionResult(BaseModel):
    detection_id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    agent_id: str
    sensitive_attributes: list[str]
    bias_detected: bool
    status: ResponsibleAIStatus
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ExplainabilityReport(BaseModel):
    report_id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    agent_id: str
    summary: str
    evidence: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ModelRiskRecord(BaseModel):
    record_id: UUID = Field(default_factory=uuid4)
    model_profile_id: str
    use_case: str
    risk_class: str
    status: ResponsibleAIStatus = ResponsibleAIStatus.REGISTERED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RegulatoryEvidenceRecord(BaseModel):
    evidence_id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    agent_id: str
    evidence_type: str
    payload: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ResponsibleAIAssessment(BaseModel):
    assessment_id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    agent_id: str
    run_id: str
    status: ResponsibleAIStatus
    findings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ResponsibleAIService:
    def __init__(self) -> None:
        self.model_risk_records: list[ModelRiskRecord] = []
        self.fairness_results: list[FairnessTestResult] = []
        self.bias_results: list[BiasDetectionResult] = []
        self.explainability_reports: list[ExplainabilityReport] = []
        self.regulatory_evidence: list[RegulatoryEvidenceRecord] = []
        self.assessments: list[ResponsibleAIAssessment] = []

    def create_model_risk_record(
        self, model_profile_id: str, use_case: str, risk_class: str
    ) -> dict:
        record = ModelRiskRecord(
            model_profile_id=model_profile_id,
            use_case=use_case,
            risk_class=risk_class,
        )
        self.model_risk_records.append(record)
        return {
            "model_profile_id": model_profile_id,
            "use_case": use_case,
            "risk_class": risk_class,
            "status": record.status,
        }

    def run_fairness_test(
        self,
        *,
        tenant_id: str,
        agent_id: str,
        metric: str,
        score: float,
    ) -> FairnessTestResult:
        result = FairnessTestResult(
            tenant_id=tenant_id,
            agent_id=agent_id,
            metric=metric,
            score=score,
            status=ResponsibleAIStatus.PASSED if score >= 0.8 else ResponsibleAIStatus.REVIEW_REQUIRED,
        )
        self.fairness_results.append(result)
        return result

    def detect_bias(
        self,
        *,
        tenant_id: str,
        agent_id: str,
        sensitive_attributes: list[str],
        output: str,
    ) -> BiasDetectionResult:
        lowered_output = output.lower()
        bias_detected = any(attribute.lower() in lowered_output for attribute in sensitive_attributes)
        result = BiasDetectionResult(
            tenant_id=tenant_id,
            agent_id=agent_id,
            sensitive_attributes=sensitive_attributes,
            bias_detected=bias_detected,
            status=ResponsibleAIStatus.REVIEW_REQUIRED if bias_detected else ResponsibleAIStatus.PASSED,
        )
        self.bias_results.append(result)
        return result

    def create_explainability_report(
        self,
        *,
        tenant_id: str,
        agent_id: str,
        summary: str,
        evidence: dict | None = None,
    ) -> ExplainabilityReport:
        report = ExplainabilityReport(
            tenant_id=tenant_id,
            agent_id=agent_id,
            summary=summary,
            evidence=evidence or {},
        )
        self.explainability_reports.append(report)
        return report

    def generate_regulatory_evidence(
        self,
        *,
        tenant_id: str,
        agent_id: str,
        evidence_type: str,
        payload: dict,
    ) -> RegulatoryEvidenceRecord:
        record = RegulatoryEvidenceRecord(
            tenant_id=tenant_id,
            agent_id=agent_id,
            evidence_type=evidence_type,
            payload=payload,
        )
        self.regulatory_evidence.append(record)
        return record

    def assess_runtime_output(
        self,
        *,
        tenant_id: str,
        agent_id: str,
        run_id: str,
        output_text: str,
    ) -> ResponsibleAIAssessment:
        findings: list[str] = []
        lowered_output = output_text.lower()
        if "sensitive attribute" in lowered_output:
            findings.append("sensitive attribute reference detected")
        if "unexplainable" in lowered_output:
            findings.append("explainability review required")
        assessment = ResponsibleAIAssessment(
            tenant_id=tenant_id,
            agent_id=agent_id,
            run_id=run_id,
            status=ResponsibleAIStatus.REVIEW_REQUIRED if findings else ResponsibleAIStatus.PASSED,
            findings=findings,
        )
        self.assessments.append(assessment)
        return assessment
