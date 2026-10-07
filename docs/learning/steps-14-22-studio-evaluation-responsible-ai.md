# Steps 14-22 - Agent Studio, Prompt Management, Evaluation, and Responsible AI

Date completed: 2026-10-06

These steps extend the platform from runtime execution into design-time governance. The goal is to make agents easier to design, test, evaluate, and govern before and after deployment.

## Step 14 - Prompt and Template Management

File: `services/prompt_management/service.py`

Purpose:

Prompts are enterprise assets. They need owners, versions, publication status, validation, and safe rendering. This service creates the first prompt-management boundary.

### Classes

#### `PromptTemplateStatus`

Enum representing the lifecycle of a prompt asset.

Values:

- `DRAFT`: editable template or version.
- `PUBLISHED`: approved version that can be used by agents.
- `DEPRECATED`: old version that should no longer be selected for new work.

#### `PromptTemplate`

Metadata for a prompt family.

Important fields:

- `template_id`: unique prompt template identifier.
- `tenant_id`: tenant boundary.
- `name`: human-readable template name.
- `description`: optional explanation of the prompt purpose.
- `owner`: accountable owner.
- `status`: lifecycle state.
- `created_at`: creation timestamp.

#### `PromptVersion`

A concrete version of prompt text.

Important fields:

- `version_id`: unique version identifier.
- `template_id`: parent prompt template.
- `version`: version label such as `1.0.0`.
- `template_text`: format string containing variables.
- `variables`: extracted variable names.
- `status`: draft/published/deprecated.
- `created_at`: creation timestamp.

#### `PromptRenderResult`

Result returned after rendering a prompt version.

Fields:

- `template_id`: parent template.
- `version_id`: rendered version.
- `rendered_text`: final prompt text after variables are applied.
- `variables_used`: variable values used in the render.

#### `PromptTemplateNotFoundError`

Raised when the requested prompt template does not exist or belongs to another tenant.

#### `PromptVersionNotFoundError`

Raised when a prompt version cannot be found or its parent template is not tenant-visible.

#### `PromptValidationError`

Raised when required template variables are missing at render time.

#### `PromptManagementService`

Owns prompt template and version workflows.

Methods:

- `__init__()`: creates in-memory stores for templates and versions.
- `create_template(...)`: creates prompt metadata for a tenant and owner.
- `create_version(...)`: validates the parent template, extracts variables from prompt text, and stores a new version.
- `publish_version(...)`: marks a version as published and promotes the parent template to published.
- `render(...)`: validates all required variables and returns rendered prompt text.
- `get_template(...)`: loads a tenant-scoped template or raises `PromptTemplateNotFoundError`.
- `get_version(...)`: loads a version and verifies its parent template is visible to the tenant.
- `list_templates(...)`: returns all templates for one tenant ordered by creation time.
- `_extract_variables(...)`: uses Python's string `Formatter` parser to identify `{variable}` placeholders.
- `_parse_uuid(...)`: accepts UUID objects or UUID strings and normalizes them.

## Step 15 - Agent Studio Test Harness

File: `services/agent_studio/service.py`

Purpose:

Agent Studio should let builders test drafts before publishing. The test harness adds lightweight checks around design-time drafts.

### New Classes

#### `AgentTestStatus`

Enum for test run outcome.

Values:

- `PASSED`: validation and test cases passed.
- `FAILED`: validation failed or at least one case did not match expectations.

#### `AgentTestCase`

One test case for an Agent Studio draft.

Fields:

- `test_case_id`: unique test case identifier.
- `name`: case name.
- `input`: mock input payload.
- `expected_contains`: optional text that simulated output must contain.

#### `AgentTestRunResult`

Result of executing the test harness.

Fields:

- `test_run_id`: unique run identifier.
- `draft_id`: tested draft.
- `status`: passed or failed.
- `checked_cases`: number of cases executed.
- `failures`: validation or comparison failures.
- `created_at`: timestamp.

### New Methods

#### `run_test_harness(...)`

Loads the draft, validates it, normalizes incoming test cases, simulates output, and compares `expected_contains` against the simulated result.

Why it matters:

This is the starting point for a richer test harness. Later it can call the real runtime, capture traces, compare structured outputs, and attach evidence to deployment gates.

#### `_simulate_test_output(...)`

Creates deterministic output from the draft role, goal, and test input. This keeps tests stable while the real runtime path evolves.

## Steps 16-20 - Evaluation Architecture

File: `services/evaluation_service/service.py`

Purpose:

Evaluation turns subjective agent quality into repeatable evidence. These steps add offline, online, LLM-as-judge, and safety evaluation primitives.

### Classes

#### `EvaluationMode`

Enum describing the evaluation type.

Values:

- `OFFLINE`: golden dataset or prompt regression evaluation.
- `ONLINE`: user feedback or human scoring.
- `LLM_AS_JUDGE`: automated quality scoring by a judge model.
- `SAFETY`: safety and risk checks.

#### `EvaluationStatus`

Enum describing result outcome.

Values:

- `PASSED`: score met threshold.
- `FAILED`: score did not meet threshold.
- `COMPLETED`: run completed without a pass/fail judgement.

#### `SafetyMetric`

Enum for supported safety dimensions.

Values:

- `HALLUCINATION`
- `GROUNDEDNESS`
- `TOXICITY`
- `PII_LEAKAGE`
- `PROMPT_INJECTION_RESILIENCE`

#### `EvaluationCase`

One item in an evaluation suite.

Fields:

- `case_id`: unique case identifier.
- `input`: test input.
- `expected_output`: expected text.
- `expected_facts`: facts the output should include or preserve.

#### `EvaluationSuite`

Collection of evaluation cases.

Fields:

- `suite_id`: unique suite identifier.
- `tenant_id`: tenant boundary.
- `name`: suite name.
- `mode`: evaluation type.
- `cases`: evaluation cases.
- `created_at`: creation timestamp.

#### `EvaluationScore`

One scored metric.

Fields:

- `metric`: metric name.
- `score`: numeric score from 0 to 1.
- `passed`: boolean threshold outcome.
- `reason`: optional explanation.

#### `EvaluationResult`

Result of an evaluation run.

Fields:

- `result_id`: unique result identifier.
- `tenant_id`: tenant boundary.
- `suite_id`: optional suite reference.
- `agent_version_id`: evaluated agent version.
- `mode`: evaluation mode.
- `status`: passed, failed, or completed.
- `scores`: metric scores.
- `created_at`: timestamp.

#### `OnlineFeedback`

Feedback from a user or human scorer.

Fields:

- `feedback_id`: unique feedback identifier.
- `tenant_id`: tenant boundary.
- `run_id`: runtime run being judged.
- `user_id`: scorer identity.
- `rating`: 1-5 score.
- `comment`: optional explanation.
- `created_at`: timestamp.

#### `EvaluationService`

Owns evaluation suites, results, and feedback.

Methods:

- `__init__()`: creates in-memory suite, result, and feedback stores.
- `create_suite(...)`: creates an evaluation suite for a tenant and mode.
- `run_offline_evaluation(...)`: keeps the older simple offline evaluation contract while storing a structured result.
- `run_suite(...)`: runs a suite, averages case scores, and returns pass/fail status.
- `record_online_feedback(...)`: records user or human feedback for a runtime run.
- `score_with_llm_judge(...)`: simulates LLM-as-judge scoring using deterministic local logic.
- `run_safety_evaluation(...)`: checks output for toxicity, PII leakage, prompt injection pattern, groundedness, and hallucination placeholders.
- `_get_suite(...)`: loads a tenant-scoped suite.
- `_score_case(...)`: returns a deterministic score for one case.

## Steps 21-22 - Responsible AI Service and Runtime Hooks

Files:

- `services/responsible_ai/service.py`
- `services/runtime_execution/service.py`

Purpose:

Responsible AI tracks fairness, bias, explainability, model risk, and regulatory evidence. The runtime hook ensures every completed run can carry Responsible AI evidence.

### Classes

#### `ResponsibleAIStatus`

Enum for Responsible AI outcome.

Values:

- `PASSED`: no issue detected.
- `REVIEW_REQUIRED`: human or governance review needed.
- `FAILED`: failed Responsible AI check.
- `REGISTERED`: model risk record has been registered.

#### `FairnessTestResult`

Result of a fairness test.

Fields:

- `test_id`: unique test identifier.
- `tenant_id`: tenant boundary.
- `agent_id`: tested agent.
- `metric`: fairness metric name.
- `score`: numeric score from 0 to 1.
- `status`: pass or review required.
- `created_at`: timestamp.

#### `BiasDetectionResult`

Bias detection result.

Fields:

- `detection_id`: unique detection identifier.
- `tenant_id`: tenant boundary.
- `agent_id`: tested agent.
- `sensitive_attributes`: monitored attributes.
- `bias_detected`: boolean flag.
- `status`: pass or review required.
- `created_at`: timestamp.

#### `ExplainabilityReport`

Human-readable and machine-readable explanation record.

Fields:

- `report_id`: unique report identifier.
- `tenant_id`: tenant boundary.
- `agent_id`: explained agent.
- `summary`: explanation summary.
- `evidence`: supporting data.
- `created_at`: timestamp.

#### `ModelRiskRecord`

Tracks model risk for a model profile and use case.

Fields:

- `record_id`: unique risk record identifier.
- `model_profile_id`: model profile reference.
- `use_case`: model use case.
- `risk_class`: model risk category.
- `status`: record status.
- `created_at`: timestamp.

#### `RegulatoryEvidenceRecord`

Stores evidence for compliance and audit.

Fields:

- `evidence_id`: unique evidence identifier.
- `tenant_id`: tenant boundary.
- `agent_id`: related agent.
- `evidence_type`: evidence category.
- `payload`: evidence details.
- `created_at`: timestamp.

#### `ResponsibleAIAssessment`

Runtime assessment attached to an agent run.

Fields:

- `assessment_id`: unique assessment identifier.
- `tenant_id`: tenant boundary.
- `agent_id`: assessed agent.
- `run_id`: runtime run identifier.
- `status`: pass or review required.
- `findings`: detected issues.
- `created_at`: timestamp.

#### `ResponsibleAIService`

Owns Responsible AI governance operations.

Methods:

- `__init__()`: creates in-memory stores for risk records, fairness results, bias results, explainability reports, evidence, and runtime assessments.
- `create_model_risk_record(...)`: registers model profile risk for a use case.
- `run_fairness_test(...)`: stores a fairness result and marks low scores for review.
- `detect_bias(...)`: checks whether output references sensitive attributes and records the result.
- `create_explainability_report(...)`: creates an explanation report with optional supporting evidence.
- `generate_regulatory_evidence(...)`: stores compliance evidence for a tenant and agent.
- `assess_runtime_output(...)`: checks runtime output for simple Responsible AI signals and returns an assessment.

### Runtime Integration

`RuntimeExecutionService` now accepts a `ResponsibleAIService` dependency and creates a default one when none is injected.

During a completed run it now:

1. Calls RAG, tool, and model gateway stubs.
2. Records FinOps cost.
3. Runs `assess_runtime_output(...)`.
4. Writes `agent_run.responsible_ai_checked` to the audit trail.
5. Records governed memory.
6. Stores a `responsible_ai` section in the run output.

Current completed-run audit event order:

```text
agent_run.started
agent_run.policy_evaluated
agent_run.cost_recorded
agent_run.responsible_ai_checked
agent_run.memory_recorded
agent_run.completed
```

## Tests Added or Updated

- `tests/test_prompt_management.py`
- `tests/test_agent_studio.py`
- `tests/test_evaluation_service.py`
- `tests/test_responsible_ai_service.py`
- `tests/test_runtime_execution.py`
- `tests/test_runtime_persistence.py`

## Verification

```text
python -m ruff check .
All checks passed!

python -m pytest
58 passed, 1 warning
```

## Learning Summary

These steps introduce three important enterprise ideas:

1. Design-time governance: Agent Studio, prompts, and test harnesses help builders improve agents before publishing.
2. Quality evidence: Evaluation suites and scores make quality measurable instead of anecdotal.
3. Responsible AI evidence: fairness, bias, explainability, risk, and regulatory records create an audit-ready governance trail.

The platform now has the first version of an enterprise loop:

```text
Design -> Test -> Evaluate -> Govern -> Run -> Audit -> Improve
```
