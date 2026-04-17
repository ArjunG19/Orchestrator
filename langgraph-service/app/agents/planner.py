"""PlannerAgent — breaks workflow input into discrete execution steps."""

import logging
from typing import TYPE_CHECKING, List, Optional

from app.agents.base import BaseAgent
from app.config import PLANNER_MODEL, PLANNER_TEMPERATURE
from app.models.state import PlanStep, WorkflowState
from app.workflow.llm_client import LLMClient

if TYPE_CHECKING:
    from app.prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """Generates a list of PlanStep objects from the workflow input."""

    def __init__(
        self,
        config: dict,
        llm_client: Optional[LLMClient] = None,
        prompt_registry: Optional["PromptRegistry"] = None,
    ):
        super().__init__(
            config,
            llm_client,
            model=PLANNER_MODEL,
            temperature=PLANNER_TEMPERATURE,
            prompt_registry=prompt_registry,
        )

    def run(self, state: WorkflowState) -> WorkflowState:
        """Build a plan from the workflow input (and previous feedback if retrying)."""
        prompt = self._build_prompt(state)
        response = self._call_llm(state, prompt)

        if response is None:
            return self._fail(state, "Planner LLM call failed: no response")

        plan = self._parse_plan(response)
        if plan is None:
            return self._fail(state, "Planner failed to parse plan from LLM response")

        return {**state, "plan": plan, "status": "planning_complete"}

    # ------------------------------------------------------------------
    # Prompt
    # ------------------------------------------------------------------

    def _build_prompt(self, state: WorkflowState) -> str:
        evaluation = state.get("evaluation")
        if evaluation and not evaluation.get("passed"):
            evaluation_section = (
                "\n## Previous Evaluation Feedback\n"
                + str(evaluation.get("feedback", ""))
                + "\nPlease revise the plan to address the feedback above.\n"
            )
        else:
            evaluation_section = ""

        if self.prompt_registry is not None:
            return self.prompt_registry.render("planner", {
                "input": str(state["input"]),
                "evaluation_section": evaluation_section,
            })

        parts: list[str] = [
            "You are a planning agent. Break the following workflow input into discrete execution steps.",
            "",
            "## Workflow Input",
            str(state["input"]),
        ]

        if evaluation_section:
            parts.append(evaluation_section)

        parts.append("")
        parts.append("Respond with ONLY a JSON array of plan steps. Each step must have:")
        parts.append('  "step_id": "<unique id>",')
        parts.append('  "description": "<what to do>",')
        parts.append('  "expected_output": "<what the step should produce>"')
        parts.append("")
        parts.append("Example:")
        parts.append('[{"step_id": "1", "description": "Analyse input data", "expected_output": "Summary of key findings"}]')

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_plan(self, response: str) -> Optional[List[PlanStep]]:
        parsed = self._parse_json(response)
        if parsed is None:
            return None

        # Accept a top-level array or an object with a "steps"/"plan" key
        steps_raw: list | None = None
        if isinstance(parsed, list):
            steps_raw = parsed
        elif isinstance(parsed, dict):
            steps_raw = parsed.get("steps") or parsed.get("plan")
            if isinstance(steps_raw, list) is False:
                return None

        if not steps_raw:
            return None

        plan: list[PlanStep] = []
        for idx, item in enumerate(steps_raw):
            if not isinstance(item, dict):
                continue
            plan.append(PlanStep(
                step_id=str(item.get("step_id", idx + 1)),
                description=str(item.get("description", "")),
                expected_output=str(item.get("expected_output", "")),
            ))

        return plan if plan else None
