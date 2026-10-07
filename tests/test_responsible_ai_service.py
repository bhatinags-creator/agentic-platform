from services.responsible_ai.service import ResponsibleAIService


def test_responsible_ai_records_model_risk_and_evidence() -> None:
    service = ResponsibleAIService()

    risk = service.create_model_risk_record("mock-profile", "customer support", "medium")
    evidence = service.generate_regulatory_evidence(
        tenant_id="tenant-a",
        agent_id="agent.support",
        evidence_type="deployment_review",
        payload={"approved": True},
    )

    assert risk["status"] == "registered"
    assert evidence.payload == {"approved": True}


def test_responsible_ai_detects_bias_and_creates_explainability_report() -> None:
    service = ResponsibleAIService()

    bias = service.detect_bias(
        tenant_id="tenant-a",
        agent_id="agent.support",
        sensitive_attributes=["age"],
        output="The answer mentions age as a sensitive attribute.",
    )
    report = service.create_explainability_report(
        tenant_id="tenant-a",
        agent_id="agent.support",
        summary="Model used policy citations.",
    )

    assert bias.bias_detected is True
    assert bias.status == "review_required"
    assert report.summary == "Model used policy citations."


def test_responsible_ai_runtime_assessment_flags_review_findings() -> None:
    service = ResponsibleAIService()

    assessment = service.assess_runtime_output(
        tenant_id="tenant-a",
        agent_id="agent.support",
        run_id="run-1",
        output_text="This has a sensitive attribute and is unexplainable.",
    )

    assert assessment.status == "review_required"
    assert assessment.findings == [
        "sensitive attribute reference detected",
        "explainability review required",
    ]
