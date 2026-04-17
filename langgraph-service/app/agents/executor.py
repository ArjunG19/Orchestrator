"""ExecutorAgent — simulates execution of the validated plan steps."""

import logging
from typing import TYPE_CHECKING, Optional

from app.agents.base import BaseAgent
from app.config import EXECUTOR_MODEL, EXECUTOR_TEMPERATURE
from app.models.state import ExecutionOutput, WorkflowState
from app.workflow.llm_client import LLMClient

if TYPE_CHECKING:
    from app.prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)


class ExecutorAgent(BaseAgent):
    """Executes the validated plan and produces an ExecutionOutput."""

    def __init__(
        self,
        config: dict,
        llm_client: Optional[LLMClient] = None,
        prompt_registry: Optional["PromptRegistry"] = None,
    ):
        super().__init__(
            config,
            llm_client,
            model=EXECUTOR_MODEL,
            temperature=EXECUTOR_TEMPERATURE,
            prompt_registry=prompt_registry,
        )

    def run(self, state: WorkflowState) -> WorkflowState:
        """Execute the validated plan."""
        prompt = self._build_prompt(state)
        response = self._call_llm(state, prompt)

        if response is None:
            return self._fail(state, "Executor LLM call failed: no response")

        execution = self._parse_execution(response)
        if execution is None:
            return self._fail(state, "Executor failed to parse execution output from LLM response")

        return {**state, "execution": execution, "status": "execution_complete"}

    # ------------------------------------------------------------------
    # Prompt
    # ------------------------------------------------------------------

    def _build_prompt(self, state: WorkflowState) -> str:
        if self.prompt_registry is not None:
            return self.prompt_registry.render("executor", {
                "input": str(state["input"]),
                "plan": str(state.get("plan", [])),
            })

        parts: list[str] = [
            "You are an execution agent. Execute each step of the validated plan and produce results.",
            "",
            "## Workflow Input",
            str(state["input"]),
            "",
            "## Validated Plan",
            str(state.get("plan", [])),
            "",
            "Respond with ONLY a JSON object with the following fields:",
            '  "step_results": [{"step_id": "<id>", "output": "<result>", "status": "success|failure"}],',
            '  "success": true/false (true if all steps succeeded)',
            "",
            "Example:",
            '{"step_results": [{"step_id": "1", "output": "Completed analysis", "status": "success"}], "success": true}',
        ]
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_execution(self, response: str) -> Optional[ExecutionOutput]:
        parsed = self._parse_json(response)
        if not isinstance(parsed, dict):
            return None

        step_results = parsed.get("step_results")
        if not isinstance(step_results, list):
            return None

        success = parsed.get("success")
        if success is None:
            return None

        return ExecutionOutput(
            step_results=[dict(r) if isinstance(r, dict) else {"output": str(r)} for r in step_results],
            success=bool(success),
        )
