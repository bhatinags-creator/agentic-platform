from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID, uuid4

from platform_common.domain.models import AgentRun, AgentRunStatus, PolicyDecision
from platform_common.events.envelope import ActorType, EventEnvelope
from services.aisecops.service import AISecOpsMonitoringService, AISecOpsSignal
from services.audit_service.service import AuditService
from services.finops_service.service import AIFinOpsService, BudgetExceededError, CostEvent
from services.memory_governance.service import MemoryGovernanceService, MemoryRecord, MemoryType
from services.model_gateway.service import ModelGatewayService
from services.policy_engine.service import PolicyEngineService
from services.rag_platform.service import RAGPlatformService
from services.responsible_ai.service import ResponsibleAIService
from services.tool_gateway.service import ToolGatewayService, ToolInvocationDeniedError


class AgentRunNotFoundError(Exception):
    """Raised when an agent run cannot be found for a tenant."""


class RuntimePolicyDeniedError(Exception):
    """Raised when policy denies an agent run before model/tool execution."""

    def __init__(self, message: str, run: AgentRun, decision: PolicyDecision) -> None:
        super().__init__(message)
        self.run = run
        self.decision = decision


class RuntimeExecutionFailedError(Exception):
    """Raised when execution fails after the run has been created and persisted."""

    def __init__(self, message: str, run: AgentRun, error_code: str) -> None:
        super().__init__(message)
        self.run = run
        self.error_code = error_code


class AgentRunRepository(ABC):
    """Storage contract for runtime execution history."""

    @abstractmethod
    def save_run(self, run: AgentRun) -> AgentRun:
        raise NotImplementedError

    @abstractmethod
    def get_run(self, tenant_id: str, run_id: UUID) -> AgentRun | None:
        raise NotImplementedError

    @abstractmethod
    def list_runs(self, tenant_id: str) -> list[AgentRun]:
        raise NotImplementedError


class InMemoryAgentRunRepository(AgentRunRepository):
    """Development run store used before durable runtime history is introduced."""

    def __init__(self) -> None:
        self._runs: dict[UUID, AgentRun] = {}

    def save_run(self, run: AgentRun) -> AgentRun:
        self._runs[run.run_id] = run
        return run

    def get_run(self, tenant_id: str, run_id: UUID) -> AgentRun | None:
        run = self._runs.get(run_id)
        if run is None or run.tenant_id != tenant_id:
            return None
        return run

    def list_runs(self, tenant_id: str) -> list[AgentRun]:
        return sorted(
            [run for run in self._runs.values() if run.tenant_id == tenant_id],
            key=lambda run: run.created_at,
        )


class RuntimeExecutionService:
    """Orchestrates one minimal agent execution through platform gateways."""

    def __init__(
        self,
        repository: AgentRunRepository | None = None,
        model_gateway: ModelGatewayService | None = None,
        tool_gateway: ToolGatewayService | None = None,
        rag_platform: RAGPlatformService | None = None,
        policy_engine: PolicyEngineService | None = None,
        audit_service: AuditService | None = None,
        finops_service: AIFinOpsService | None = None,
        memory_governance: MemoryGovernanceService | None = None,
        responsible_ai_service: ResponsibleAIService | None = None,
        aisecops_service: AISecOpsMonitoringService | None = None,
    ) -> None:
        self.repository = repository or InMemoryAgentRunRepository()
        self.model_gateway = model_gateway or ModelGatewayService()
        self.tool_gateway = tool_gateway or ToolGatewayService()
        self.rag_platform = rag_platform or RAGPlatformService()
        self.policy_engine = policy_engine or PolicyEngineService()
        self.audit_service = audit_service or AuditService()
        self.finops_service = finops_service or AIFinOpsService()
        self.memory_governance = memory_governance or MemoryGovernanceService()
        self.responsible_ai_service = responsible_ai_service or ResponsibleAIService()
        self.aisecops_service = aisecops_service or AISecOpsMonitoringService()

    async def start_run(
        self,
        tenant_id: str,
        user_id: str,
        agent_id: str,
        agent_version: str,
        input_payload: dict,
    ) -> AgentRun:
        trace_id = str(uuid4())
        running_run = AgentRun(
            tenant_id=tenant_id,
            agent_id=agent_id,
            agent_version=agent_version,
            user_id=user_id,
            trace_id=trace_id,
            input=input_payload,
            status=AgentRunStatus.RUNNING,
        )
        self.repository.save_run(running_run)
        self._write_audit_event("agent_run.started", running_run, {})

        policy_decision = await self.policy_engine.evaluate(
            action="agent_run.start",
            subject={"type": "user", "id": user_id, "tenant_id": tenant_id},
            resource={
                "type": "agent_run",
                "agent_id": agent_id,
                "agent_version": agent_version,
                "input": input_payload,
            },
        )
        self._write_audit_event(
            "agent_run.policy_evaluated",
            running_run,
            {
                "decision_id": str(policy_decision.decision_id),
                "decision": policy_decision.decision,
                "reason": policy_decision.reason,
                "constraints": policy_decision.constraints,
            },
        )

        if policy_decision.decision == "deny":
            denied_run = running_run.model_copy(
                update={
                    "status": AgentRunStatus.FAILED,
                    "output": {
                        "error": "policy_denied",
                        "policy_decision_id": str(policy_decision.decision_id),
                        "reason": policy_decision.reason,
                    },
                }
            )
            self.repository.save_run(denied_run)
            self._write_audit_event(
                "agent_run.denied",
                denied_run,
                {"policy_decision_id": str(policy_decision.decision_id)},
            )
            raise RuntimePolicyDeniedError("Policy denied agent run", denied_run, policy_decision)

        try:
            aisecops_signals: list[AISecOpsSignal] = []
            prompt_signal = self.aisecops_service.inspect_prompt(
                str(input_payload),
                tenant_id=tenant_id,
                agent_id=agent_id,
                run_id=str(running_run.run_id),
                trace_id=trace_id,
            )
            if prompt_signal["signal"] != "none":
                self._write_audit_event(
                    "agent_run.aisecops_signal_recorded",
                    running_run,
                    {
                        "signal_id": prompt_signal["signal_id"],
                        "signal": prompt_signal["signal"],
                        "severity": prompt_signal["severity"],
                    },
                )

            retrievals = await self.rag_platform.retrieve(str(input_payload), {"tenant_id": tenant_id})
            for retrieval in retrievals:
                safety_findings = retrieval.get("safety_findings") or []
                if safety_findings:
                    aisecops_signals.append(
                        self.aisecops_service.record_rag_poisoning(
                            tenant_id=tenant_id,
                            agent_id=agent_id,
                            knowledge_source=str(retrieval.get("citation", "unknown")),
                            evidence={"findings": safety_findings},
                            run_id=str(running_run.run_id),
                            trace_id=trace_id,
                        )
                    )
            tool_result = await self.tool_gateway.invoke(
                "mvp.echo",
                input_payload,
                {
                    "tenant_id": tenant_id,
                    "trace_id": trace_id,
                    "run_id": str(running_run.run_id),
                    "agent_id": agent_id,
                },
            )
            model_result = await self.model_gateway.chat(
                {"provider": "mock", "model": "mock-model"},
                [{"role": "user", "content": str(input_payload)}],
            )
            cost_event = self.finops_service.record_model_usage(
                tenant_id=tenant_id,
                agent_id=agent_id,
                run_id=str(running_run.run_id),
                trace_id=trace_id,
                provider=model_result.provider,
                model=model_result.model,
                prompt_tokens=model_result.prompt_tokens,
                completion_tokens=model_result.completion_tokens,
                estimated_cost=model_result.estimated_cost,
                workflow_id=input_payload.get("workflow_id"),
                department=input_payload.get("department"),
            )
            self._write_audit_event(
                "agent_run.cost_recorded",
                running_run,
                {
                    "cost_event_id": str(cost_event.event_id),
                    "total_tokens": cost_event.total_tokens,
                    "estimated_cost": cost_event.estimated_cost,
                },
            )
            memory_record = self.memory_governance.create_record(
                tenant_id=tenant_id,
                agent_id=agent_id,
                run_id=str(running_run.run_id),
                trace_id=trace_id,
                memory_type=MemoryType.CONVERSATION,
                content={
                    "input": input_payload,
                    "model_output": model_result.output_text,
                    "retrieval_count": len(retrievals),
                    "tool_status": tool_result.get("status"),
                },
            )
            responsible_ai_assessment = self.responsible_ai_service.assess_runtime_output(
                tenant_id=tenant_id,
                agent_id=agent_id,
                run_id=str(running_run.run_id),
                output_text=model_result.output_text,
            )
            self._write_audit_event(
                "agent_run.responsible_ai_checked",
                running_run,
                {
                    "assessment_id": str(responsible_ai_assessment.assessment_id),
                    "status": responsible_ai_assessment.status,
                    "findings": responsible_ai_assessment.findings,
                },
            )
            self._write_audit_event(
                "agent_run.aisecops_checked",
                running_run,
                {
                    "signals": [str(signal.signal_id) for signal in aisecops_signals],
                    "signal_count": len(aisecops_signals) + (1 if prompt_signal["signal"] != "none" else 0),
                },
            )
            self._write_audit_event(
                "agent_run.memory_recorded",
                running_run,
                {
                    "memory_id": str(memory_record.memory_id),
                    "memory_type": memory_record.memory_type,
                    "retention": memory_record.retention,
                    "expires_at": memory_record.expires_at.isoformat()
                    if memory_record.expires_at
                    else None,
                },
            )

            completed_run = running_run.model_copy(
                update={
                    "status": AgentRunStatus.COMPLETED,
                    "output": {
                        "policy": {
                            "decision_id": str(policy_decision.decision_id),
                            "decision": policy_decision.decision,
                            "reason": policy_decision.reason,
                        },
                        "finops": self._cost_event_output(cost_event),
                        "memory": self._memory_record_output(memory_record),
                        "responsible_ai": {
                            "assessment_id": str(responsible_ai_assessment.assessment_id),
                            "status": responsible_ai_assessment.status,
                            "findings": responsible_ai_assessment.findings,
                        },
                        "aisecops": {
                            "prompt_signal": prompt_signal,
                            "signals": [
                                {
                                    "signal_id": str(signal.signal_id),
                                    "signal_type": signal.signal_type,
                                    "severity": signal.severity,
                                    "status": signal.status,
                                }
                                for signal in aisecops_signals
                            ],
                        },
                        "model": {
                            "output_text": model_result.output_text,
                            "provider": model_result.provider,
                            "model": model_result.model,
                            "prompt_tokens": model_result.prompt_tokens,
                            "completion_tokens": model_result.completion_tokens,
                            "estimated_cost": model_result.estimated_cost,
                        },
                        "tool": tool_result,
                        "retrievals": retrievals,
                    },
                }
            )
            saved_run = self.repository.save_run(completed_run)
            self._write_audit_event("agent_run.completed", saved_run, {})
            return saved_run
        except ToolInvocationDeniedError as exc:
            self.aisecops_service.record_tool_abuse(
                tenant_id=tenant_id,
                agent_id=agent_id,
                tool_name=exc.record.tool_name,
                evidence={"reason": exc.record.decision.reason},
                run_id=str(running_run.run_id),
                trace_id=trace_id,
            )
            failed_run = self._record_failed_run(running_run, "tool_invocation_denied", str(exc))
            raise RuntimeExecutionFailedError(str(exc), failed_run, "tool_invocation_denied") from exc
        except BudgetExceededError as exc:
            failed_run = self._record_failed_run(running_run, "budget_exceeded", str(exc))
            raise RuntimeExecutionFailedError(str(exc), failed_run, "budget_exceeded") from exc
        except Exception as exc:
            failed_run = self._record_failed_run(running_run, "execution_failed", str(exc))
            raise RuntimeExecutionFailedError(str(exc), failed_run, "execution_failed") from exc

    def get_run(self, tenant_id: str, run_id: UUID | str) -> AgentRun:
        run_uuid = self._parse_uuid(run_id)
        run = self.repository.get_run(tenant_id, run_uuid)
        if run is None:
            raise AgentRunNotFoundError(f"Agent run not found: {run_id}")
        return run

    def list_runs(self, tenant_id: str) -> list[AgentRun]:
        return self.repository.list_runs(tenant_id)

    def list_audit_events(self, tenant_id: str, trace_id: str | None = None) -> list[EventEnvelope]:
        return self.audit_service.list_events(tenant_id=tenant_id, trace_id=trace_id)

    def list_memory_records(
        self,
        tenant_id: str,
        agent_id: str | None = None,
        run_id: str | None = None,
    ) -> list[MemoryRecord]:
        return self.memory_governance.list_records(
            tenant_id=tenant_id,
            agent_id=agent_id,
            run_id=run_id,
        )

    def _record_failed_run(
        self,
        running_run: AgentRun,
        error_code: str,
        message: str,
    ) -> AgentRun:
        failed_run = running_run.model_copy(
            update={
                "status": AgentRunStatus.FAILED,
                "output": {"error": error_code, "message": message},
            }
        )
        self.repository.save_run(failed_run)
        self._write_audit_event(
            "agent_run.failed",
            failed_run,
            {"error": error_code, "message": message},
        )
        return failed_run

    def _write_audit_event(
        self,
        event_type: str,
        run: AgentRun,
        payload: dict,
    ) -> EventEnvelope:
        event = EventEnvelope.create(
            event_type=event_type,
            tenant_id=run.tenant_id,
            trace_id=run.trace_id,
            correlation_id=str(run.run_id),
            actor_type=ActorType.USER,
            actor_id=run.user_id,
            subject_type="agent_run",
            subject_id=str(run.run_id),
            payload={
                "agent_id": run.agent_id,
                "agent_version": run.agent_version,
                "status": run.status,
                **payload,
            },
            idempotency_key=f"{run.run_id}:{event_type}",
        )
        return self.audit_service.write(event)

    @staticmethod
    def _cost_event_output(cost_event: CostEvent) -> dict:
        return {
            "cost_event_id": str(cost_event.event_id),
            "prompt_tokens": cost_event.prompt_tokens,
            "completion_tokens": cost_event.completion_tokens,
            "total_tokens": cost_event.total_tokens,
            "estimated_cost": cost_event.estimated_cost,
            "department": cost_event.department,
            "workflow_id": cost_event.workflow_id,
        }

    @staticmethod
    def _memory_record_output(memory_record: MemoryRecord) -> dict:
        return {
            "memory_id": str(memory_record.memory_id),
            "memory_type": memory_record.memory_type,
            "retention": memory_record.retention,
            "expires_at": memory_record.expires_at.isoformat() if memory_record.expires_at else None,
        }

    @staticmethod
    def _parse_uuid(value: UUID | str) -> UUID:
        if isinstance(value, UUID):
            return value
        return UUID(value)


