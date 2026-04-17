"""ValidatorAgent — checks plan feasibility and constraint satisfaction."""

import logging
from typing import TYPE_CHECKING, Optional

from app.agents.base import BaseAgent
from app.config import VALIDATOR_MODEL, VALIDATOR_TEMPERATURE
from app.models.state import ValidationResult, WorkflowState
from app.workflow.llm_client import LLMClient

if TYPE_CHECKING:
    from app.prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)


class ValidatorAgent(BaseAgent):
    """Validates the current plan and produces a ValidationResult."""

    def __init__(
        self,
        config: dict,
        llm_client: Optional[LLMClient] = None,
        prompt_registry: Optional["PromptRegistry"] = None,
    ):
        super().__init__(
            config,
            llm_client,
            model=VALIDATOR_MODEL,
            temperature=VALIDATOR_TEMPERATURE,
            prompt_registry=prompt_registry,
        )

    def run(self, state: WorkflowState) -> WorkflowState:
        """Validate the plan in the current state."""
        prompt = self._build_prompt(state)
        response = self._call_llm(state, prompt)

        if response is None:
            return self._fail(state, "Validator LLM call failed: no response")

        validation = self._parse_validation(response)
        if validation is None:
            return self._fail(state, "Validator failed to parse validation from LLM response")

        return {**state, "validation": validation, "status": "validation_complete"}

    # ------------------------------------------------------------------
    # Prompt
    # ------------------------------------------------------------------

    def _build_prompt(self, state: WorkflowState) -> str:
        if self.prompt_registry is not None:
            return self.prompt_registry.render("validator", {
                "input": str(state["input"]),
                "plan": str(state.get("plan", [])),
            })

        parts: list[str] = [
            "You are a validation agent. Review the following execution plan and determine if it is valid and feasible.",
            "",
            "## Workflow Input",
            str(state["input"]),
            "",
            "## Plan to Validate",
            str(state.get("plan", [])),
            "",
            "Respond with ONLY a JSON object with the following fields:",
            '  "is_valid": true/false,',
            '  "issues": ["list of issues found, empty if valid"]',
            "",
            "Example:",
            '{"is_valid": true, "issues": []}',
        ]
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_validation(self, response: str) -> Optional[ValidationResult]:
        parsed = self._parse_json(response)
        if not isinstance(parsed, dict):
            return None

        is_valid = parsed.get("is_valid")
        if is_valid is None:
            return None

        issues = parsed.get("issues", [])
        if not isinstance(issues, list):
            issues = []

        return ValidationResult(
            is_valid=bool(is_valid),
            issues=[str(i) for i in issues],
        )
