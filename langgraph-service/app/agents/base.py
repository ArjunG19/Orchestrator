"""Base agent abstract class for the agentic workflow sub-agents."""

import json
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Union

from app.config import DEFAULT_MODEL, DEFAULT_TEMPERATURE
from app.models.state import WorkflowState
from app.workflow.llm_client import LLMClient

if TYPE_CHECKING:
    from app.prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all workflow sub-agents.

    Each agent receives a WorkflowState, calls the LLM, parses the response,
    and returns a NEW state dict (never mutates the input).
    """

    def __init__(
        self,
        config: dict,
        llm_client: Optional[LLMClient] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        prompt_registry: Optional["PromptRegistry"] = None,
    ):
        self.config = config
        self.model = model or DEFAULT_MODEL
        self.temperature = temperature if temperature is not None else DEFAULT_TEMPERATURE
        self.prompt_registry = prompt_registry
        self.llm_client = llm_client or LLMClient(
            model=self.model,
        )

    @abstractmethod
    def run(self, state: WorkflowState) -> WorkflowState:
        """Execute agent logic and return a new WorkflowState."""
        ...

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _call_llm(self, state: WorkflowState, prompt: str, max_tokens: int = 2048) -> Optional[str]:
        """Call the LLM and return the raw response text, or None on failure.

        Model resolution precedence:
          workflow config model > self.model (per-agent env var) > DEFAULT_MODEL > hardcoded fallback
        """
        workflow_model = state.get("config", {}).get("model")
        return self.llm_client.generate(
            prompt=prompt,
            model=workflow_model or self.model,
            max_tokens=max_tokens,
            temperature=self.temperature,
        )

    def _fail(self, state: WorkflowState, error: str) -> WorkflowState:
        """Return a new state with error details and FAILED status."""
        return {**state, "error": error, "status": "FAILED"}

    @staticmethod
    def _parse_json(text: str) -> Optional[Union[dict, list]]:
        """Try to extract a JSON object or array from raw LLM text.

        Handles markdown fences and surrounding prose.
        """
        if text is None:
            return None
        stripped = text.strip()
        # Try to find a JSON object
        obj_start = stripped.find("{")
        arr_start = stripped.find("[")

        # Pick whichever comes first
        if obj_start == -1 and arr_start == -1:
            return None

        if arr_start != -1 and (obj_start == -1 or arr_start < obj_start):
            end = stripped.rfind("]") + 1
            if end == 0:
                return None
            candidate = stripped[arr_start:end]
        else:
            end = stripped.rfind("}") + 1
            if end == 0:
                return None
            candidate = stripped[obj_start:end]

        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            return None
