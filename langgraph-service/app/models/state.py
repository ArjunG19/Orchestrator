"""WorkflowState and sub-type TypedDict models for the LangGraph agentic workflow."""

from typing import Dict, List, Optional, TypedDict


class PlanStep(TypedDict):
    step_id: str
    description: str
    expected_output: str


class ValidationResult(TypedDict):
    is_valid: bool
    issues: List[str]


class ExecutionOutput(TypedDict):
    step_results: List[dict]
    success: bool


class EvaluationResult(TypedDict):
    passed: bool
    score: float
    feedback: str


class RoutingDecision(TypedDict):
    next_agent: str
    reasoning: str
    confidence: float


class WorkflowState(TypedDict):
    workflow_id: str
    input: dict
    config: dict
    plan: Optional[List[PlanStep]]
    validation: Optional[ValidationResult]
    execution: Optional[ExecutionOutput]
    evaluation: Optional[EvaluationResult]
    routing_history: List[RoutingDecision]
    current_iteration: int
    max_iterations: int
    next_agent: Optional[str]
    retry_count: int
    max_retries: int
    status: str
    error: Optional[str]
