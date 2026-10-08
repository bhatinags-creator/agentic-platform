# Steps 31-35 - Deployment Service, Gates, Local Scripts, and Human Approval

Date completed: 2026-10-08

## Purpose

These steps add the first deployment-management layer and human-in-the-loop runtime checkpoints. The platform can now create deployment targets, evaluate deployment gates, deploy, roll back, create human approval tasks, pause runtime execution, and resume based on approval decisions.

## Step 31 - Deployment Service MVP

File:

- `services/deployment_service/service.py`

Implemented:

- deployment target registration
- deployment record creation
- deployment listing and lookup
- deploy operation
- rollback operation

Key classes:

- `DeploymentEnvironment`: local, dev, test, prod.
- `DeploymentStatus`: created, blocked, deployed, rolled back.
- `DeploymentTarget`: tenant-scoped runtime deployment target.
- `DeploymentRecord`: one deployment of an agent version to a target.
- `DeploymentService`: manages targets and deployments.

## Step 32 - Deployment Gates

File:

- `services/deployment_service/service.py`

Implemented gate types:

- policy
- evaluation
- Responsible AI
- AISecOps

Key classes:

- `DeploymentGateType`
- `DeploymentGateStatus`
- `DeploymentGateResult`
- `DeploymentBlockedError`

Learning point:

Deployment gates are the bridge between design-time evidence and runtime promotion. A deployment should not become active unless the required controls have passed.

## Step 33 - Local Laptop Deployment Scripts

Files:

- `scripts/start-local.ps1`
- `scripts/smoke-test.ps1`

Implemented:

- virtual environment bootstrap
- editable install with dev dependencies
- local data directory creation
- Control Plane API startup
- Runtime API startup
- health-check smoke test

## Step 34 - Human Task Service MVP

File:

- `services/human_task_service/service.py`

Implemented:

- approval task creation
- task decision handling
- tenant-scoped task lookup
- task listing by status
- duplicate decision protection

Key classes:

- `HumanTaskStatus`: pending, approved, rejected, cancelled.
- `HumanTask`: approval task record.
- `HumanApprovalDecision`: approval decision model.
- `HumanTaskService`: manages approval tasks.

## Step 35 - Runtime Human Approval Checkpoints

File:

- `services/runtime_execution/service.py`

Implemented:

- runtime pauses when `input_payload.requires_human_approval` is `True`
- creates a human approval task
- saves run as `WAITING_FOR_HUMAN`
- writes `agent_run.waiting_for_human` audit event
- `resume_after_human_approval(...)` approves or rejects the paused run
- writes `agent_run.human_approval_decided` audit event

Learning point:

Human approval is a runtime checkpoint, not just a UI action. It must be represented in run state, task state, and audit evidence.

## Tests

Added or updated:

- `tests/test_deployment_service.py`
- `tests/test_human_task_service.py`
- `tests/test_runtime_execution.py`

## Verification

```text
python -m ruff check .
All checks passed!

python -m pytest
82 passed, 1 warning
```

## Learning Summary

The platform now supports this deployment and approval lifecycle:

```text
Create Target -> Create Deployment -> Evaluate Gates -> Deploy -> Roll Back
```

And this human approval lifecycle:

```text
Run Starts -> Policy Passes -> Human Task Created -> Run Waits -> Human Decides -> Run Completes or Fails
```
