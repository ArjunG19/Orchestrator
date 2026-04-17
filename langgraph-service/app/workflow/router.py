"""Orchestrator Router — central decision-making node for the agentic workflow."""

import json
import logging
from typing import TYPE_CHECKING, Optional

from app.config import DEFAULT_MODEL, DEFAULT_TEMPERATURE, ROUTER_MODEL, ROUTER_TEMPERATURE
from app.models.state import RoutingDecision, WorkflowState
from app.workflow.llm_client import LLMClient

if TYPE_CHECKING:
    from app.prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)

VALID_AGENTS = {"planner", "validator", "executor", "evaluator", "done"}


class OrchestratorRouter:
    """Analyses current WorkflowState and decides which sub-agent to invoke next."""

    def __init__(
        self,
        config: dict,
        llm_client: Optional[LLMClient] = None,
        prompt_registry: Optional["PromptRegistry"] = None,
    ):
        self.config = config
        self.model = ROUTER_MODEL or DEFAULT_MODEL
        self.temperature = ROUTER_TEMPERATURE
        self.prompt_registry = prompt_registry
        self.llm_client = llm_client or LLMClient(
            model=self.model,
        )

    # ------------------------------------------------------------------
    # Public entry point (used as a LangGraph node function)
    # ------------------------------------------------------------------

    def route(self, state: WorkflowState) -> WorkflowState:
        """Analyse *state* and return an updated copy with ``next_agent`` set."""
        new_state: dict = {**state}
        new_state["current_iteration"] = state["current_iteration"] + 1

        # --- Hard termination: max iterations reached ---
        if new_state["current_iteration"] >= state["max_iterations"]:
            return self._exit(
                new_state,
                state,
                next_agent="done",
                status="max_iterations_reached",
                reasoning="Max iterations reached, forcing exit",
            )

        # --- Success termination: evaluation passed ---
        evaluation = state.get("evaluation")
        if evaluation and evaluation.get("passed"):
            return self._exit(
                new_state,
                state,
                next_agent="done",
                status="COMPLETED",
                reasoning="Evaluation passed, workflow complete",
            )

        try:
            # --- LLM-based routing decision ---
            prompt = self._build_routing_prompt(state)
            workflow_model = state.get("config", {}).get("model")
            response = self.llm_client.generate(
                prompt=prompt,
                model=workflow_model or self.model,
                max_tokens=512,
                temperature=self.temperature,
            )

            decision: Optional[RoutingDecision] = None
            if response is not None:
                decision = self._parse_routing_decision(response)

            # Apply routing constraints — override invalid LLM choices
            if decision is not None:
                decision = self._enforce_constraints(decision, state)

            # Deterministic fallback when LLM failed or returned garbage
            if decision is None:
                decision = self._deterministic_fallback(state)

        except Exception as exc:
            # If both LLM and deterministic fallback fail, route to failure exit
            logger.exception("Router encountered unexpected error: %s", exc)
            new_state["next_agent"] = "done"
            new_state["status"] = "FAILED"
            new_state["error"] = f"Router error: {exc}"
            decision = RoutingDecision(
                next_agent="done",
                reasoning=f"Router failure: {exc}",
                confidence=1.0,
            )
            new_state["routing_history"] = list(state["routing_history"]) + [decision]
            return new_state

        new_state["next_agent"] = decision["next_agent"]
        new_state["routing_history"] = list(state["routing_history"]) + [decision]
        return new_state

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def _build_routing_prompt(self, state: WorkflowState) -> str:
        """Build a concise prompt summarising the current state for the LLM."""
        # Compute summary strings for template variables
        plan_summary = (
            f"present ({len(state['plan'])} steps)" if state.get("plan") else "None"
        )

        if state.get("validation"):
            v = state["validation"]
            validation_summary = f"is_valid={v.get('is_valid')}, issues={v.get('issues', [])}"
        else:
            validation_summary = "None"

        if state.get("execution"):
            e = state["execution"]
            execution_summary = f"success={e.get('success')}, steps={len(e.get('step_results', []))}"
        else:
            execution_summary = "None"

        if state.get("evaluation"):
            ev = state["evaluation"]
            evaluation_summary = f"passed={ev.get('passed')}, score={ev.get('score')}"
        else:
            evaluation_summary = "None"

        if self.prompt_registry is not None:
            return self.prompt_registry.render("router", {
                "workflow_id": str(state["workflow_id"]),
                "current_iteration": str(state["current_iteration"]),
                "max_iterations": str(state["max_iterations"]),
                "plan_summary": plan_summary,
                "validation_summary": validation_summary,
                "execution_summary": execution_summary,
                "evaluation_summary": evaluation_summary,
                "status": str(state.get("status")),
                "error": str(state.get("error")),
            })

        parts: list[str] = [
            "You are an orchestrator router for a multi-step workflow.",
            "Analyse the current workflow state and decide which agent to invoke next.",
            "",
            "## Current State",
            f"- workflow_id: {state['workflow_id']}",
            f"- current_iteration: {state['current_iteration']} / {state['max_iterations']}",
            f"- plan: {plan_summary}",
            f"- validation: {validation_summary}",
            f"- execution: {execution_summary}",
            f"- evaluation: {evaluation_summary}",
            f"- status: {state.get('status')}",
            f"- error: {state.get('error')}",
            "",
            "## Available Agents",
            "planner  — creates or revises the execution plan",
            "validator — validates the current plan",
            "executor — executes the validated plan",
            "evaluator — evaluates execution results",
            "done — exit the workflow (success or no more work)",
            "",
            "## Constraints",
            "- Do NOT choose 'validator' if there is no plan.",
            "- Do NOT choose 'executor' if validation is missing or invalid.",
            "- Do NOT choose 'evaluator' if there is no execution output.",
            "",
            "Respond with ONLY a JSON object:",
            '{"next_agent": "<agent>", "reasoning": "<why>", "confidence": <0.0-1.0>}',
        ]

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_routing_decision(self, response: str) -> Optional[RoutingDecision]:
        """Try to extract a RoutingDecision from the raw LLM text."""
        try:
            # The LLM may wrap JSON in markdown fences or extra text.
            text = response.strip()
            # Try to find a JSON object in the response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start == -1 or end == 0:
                return None
            candidate = text[start:end]
            data = json.loads(candidate)

            next_agent = str(data.get("next_agent", "")).strip().lower()
            if next_agent not in VALID_AGENTS:
                return None

            return RoutingDecision(
                next_agent=next_agent,
                reasoning=str(data.get("reasoning", "")),
                confidence=float(data.get("confidence", 0.5)),
            )
        except (json.JSONDecodeError, ValueError, TypeError):
            logger.warning("Failed to parse routing decision from LLM response")
            return None

    # ------------------------------------------------------------------
    # Routing constraints
    # ------------------------------------------------------------------

    def _enforce_constraints(
        self, decision: RoutingDecision, state: WorkflowState
    ) -> Optional[RoutingDecision]:
        """Return *decision* if it respects state constraints, else None (triggers fallback)."""
        agent = decision["next_agent"]

        if agent == "validator" and not state.get("plan"):
            logger.info("Constraint violation: no plan for validator — falling back")
            return None

        if agent == "executor":
            validation = state.get("validation")
            if not validation or not validation.get("is_valid"):
                logger.info("Constraint violation: no valid validation for executor — falling back")
                return None

        if agent == "evaluator" and not state.get("execution"):
            logger.info("Constraint violation: no execution for evaluator — falling back")
            return None

        # Prevent redundant re-planning when validation passed and execution hasn't run yet
        if agent == "planner":
            validation = state.get("validation")
            if validation and validation.get("is_valid") and not state.get("execution"):
                logger.info("Constraint violation: plan already validated, should execute — falling back")
                return None

        return decision

    # ------------------------------------------------------------------
    # Deterministic fallback
    # ------------------------------------------------------------------

    def _deterministic_fallback(self, state: WorkflowState) -> RoutingDecision:
        """Choose the next agent based purely on which state fields are populated."""
        if not state.get("plan"):
            return RoutingDecision(
                next_agent="planner",
                reasoning="Deterministic fallback: no plan exists",
                confidence=1.0,
            )

        validation = state.get("validation")
        if not validation:
            return RoutingDecision(
                next_agent="validator",
                reasoning="Deterministic fallback: plan exists but no validation",
                confidence=1.0,
            )

        if not validation.get("is_valid"):
            # Plan was invalidated — re-plan
            return RoutingDecision(
                next_agent="planner",
                reasoning="Deterministic fallback: validation failed, re-planning",
                confidence=1.0,
            )

        if not state.get("execution"):
            return RoutingDecision(
                next_agent="executor",
                reasoning="Deterministic fallback: validated but not executed",
                confidence=1.0,
            )

        if not state.get("evaluation"):
            return RoutingDecision(
                next_agent="evaluator",
                reasoning="Deterministic fallback: executed but not evaluated",
                confidence=1.0,
            )

        # Everything populated — nothing left to do
        return RoutingDecision(
            next_agent="done",
            reasoning="Deterministic fallback: all stages complete",
            confidence=1.0,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _exit(
        new_state: dict,
        old_state: WorkflowState,
        *,
        next_agent: str,
        status: str,
        reasoning: str,
    ) -> dict:
        """Populate *new_state* for an exit routing decision."""
        new_state["next_agent"] = next_agent
        new_state["status"] = status
        decision = RoutingDecision(
            next_agent=next_agent,
            reasoning=reasoning,
            confidence=1.0,
        )
        new_state["routing_history"] = list(old_state["routing_history"]) + [decision]
        return new_state
