"""EvaluatorAgent — validates the final outcome against success criteria."""

import logging
from typing import TYPE_CHECKING, Optional

from app.agents.base import BaseAgent
from app.config import EVALUATOR_MODEL, EVALUATOR_TEMPERATURE
from app.models.state import EvaluationResult, WorkflowState
from app.workflow.llm_client import LLMClient

if TYPE_CHECKING:
    from app.prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)


class EvaluatorAgent(BaseAgent):
    """Evaluates execution output and produces an EvaluationResult."""

    def __init__(
        self,
        config: dict,
        llm_client: Optional[LLMClient] = None,
        prompt_registry: Optional["PromptRegistry"] = None,
    ):
        super().__init__(
            config,
            llm_client,
            model=EVALUATOR_MODEL,
            temperature=EVALUATOR_TEMPERATURE,
            prompt_registry=prompt_registry,
        )

    def run(self, state: WorkflowState) -> WorkflowState:
        """Evaluate the execution output."""
        prompt = self._build_prompt(state)
        response = self._call_llm(state, prompt)

        if response is None:
            return self._fail(state, "Evaluator LLM call failed: no response")

        evaluation = self._parse_evaluation(response)
        if evaluation is None:
            return self._fail(state, "Evaluator failed to parse evaluation from LLM response")

        return {**state, "evaluation": evaluation, "status": "evaluation_complete"}

    # ------------------------------------------------------------------
    # Prompt
    # ------------------------------------------------------------------

    def _build_prompt(self, state: WorkflowState) -> str:
        if self.prompt_registry is not None:
            return self.prompt_registry.render("evaluator", {
                "input": str(state["input"]),
                "plan": str(state.get("plan", [])),
                "execution": str(state.get("execution", {})),
            })

        parts: list[str] = [
            "You are an evaluation agent. Assess the execution results against the original workflow input and plan.",
            "",
            "## Workflow Input",
            str(state["input"]),
            "",
            "## Plan",
            str(state.get("plan", [])),
            "",
            "## Execution Output",
            str(state.get("execution", {})),
            "",
            "Respond with ONLY a JSON object with the following fields:",
            '  "passed": true/false (whether the execution meets success criteria),',
            '  "score": <0.0 to 1.0> (quality score),',
            '  "feedback": "<detailed feedback explaining the evaluation>"',
            "",
            "Example:",
            '{"passed": true, "score": 0.92, "feedback": "All steps completed successfully with high quality output."}',
        ]
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_evaluation(self, response: str) -> Optional[EvaluationResult]:
        parsed = self._parse_json(response)
        if not isinstance(parsed, dict):
            return None

        passed = parsed.get("passed")
        score = parsed.get("score")
        feedback = parsed.get("feedback")

        if passed is None or score is None or feedback is None:
            return None

        try:
            score_val = float(score)
        except (ValueError, TypeError):
            return None

        return EvaluationResult(
            passed=bool(passed),
            score=max(0.0, min(1.0, score_val)),
            feedback=str(feedback),
        )
