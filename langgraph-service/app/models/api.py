"""Pydantic models for API request/response payloads."""

from typing import Any, Optional

from pydantic import BaseModel


class ExecutionPayload(BaseModel):
    """Request body for the /execute endpoint."""

    workflow_id: str
    input: dict[str, Any]
    config: dict[str, Any]
    callback_url: Optional[str] = None
