"""Centralized environment-based configuration for the LangGraph Service.

All settings are read from environment variables at import time with sensible
defaults.  Invalid values (e.g. non-numeric strings for int/float fields) will
raise ValueError immediately so misconfigurations are caught at startup.
"""

import os
from typing import Optional

# ---------------------------------------------------------------------------
# Global defaults
# ---------------------------------------------------------------------------

DEFAULT_MODEL: str = os.environ.get("DEFAULT_MODEL", "llama-3.3-70b-versatile")
DEFAULT_MAX_RETRIES: int = int(os.environ.get("DEFAULT_MAX_RETRIES", "3"))
DEFAULT_MAX_ITERATIONS: int = int(os.environ.get("DEFAULT_MAX_ITERATIONS", "15"))
DEFAULT_TEMPERATURE: float = float(os.environ.get("DEFAULT_TEMPERATURE", "0.2"))

# ---------------------------------------------------------------------------
# Per-agent model overrides (None means fall back to DEFAULT_MODEL)
# ---------------------------------------------------------------------------

PLANNER_MODEL: Optional[str] = os.environ.get("PLANNER_MODEL")
VALIDATOR_MODEL: Optional[str] = os.environ.get("VALIDATOR_MODEL")
EXECUTOR_MODEL: Optional[str] = os.environ.get("EXECUTOR_MODEL")
EVALUATOR_MODEL: Optional[str] = os.environ.get("EVALUATOR_MODEL")
ROUTER_MODEL: Optional[str] = os.environ.get("ROUTER_MODEL")

# ---------------------------------------------------------------------------
# Per-agent temperature overrides (default to DEFAULT_TEMPERATURE)
# ---------------------------------------------------------------------------

PLANNER_TEMPERATURE: float = float(os.environ.get("PLANNER_TEMPERATURE", str(DEFAULT_TEMPERATURE)))
VALIDATOR_TEMPERATURE: float = float(os.environ.get("VALIDATOR_TEMPERATURE", str(DEFAULT_TEMPERATURE)))
EXECUTOR_TEMPERATURE: float = float(os.environ.get("EXECUTOR_TEMPERATURE", str(DEFAULT_TEMPERATURE)))
EVALUATOR_TEMPERATURE: float = float(os.environ.get("EVALUATOR_TEMPERATURE", str(DEFAULT_TEMPERATURE)))
ROUTER_TEMPERATURE: float = float(os.environ.get("ROUTER_TEMPERATURE", str(DEFAULT_TEMPERATURE)))
