"""API route definitions for the LangGraph service."""

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, BackgroundTasks

from app.config import DEFAULT_MAX_ITERATIONS, DEFAULT_MAX_RETRIES
from app.models.api import ExecutionPayload
from app.models.state import WorkflowState
from app.workflow.graph import AgenticGraphBuilder

logger = logging.getLogger(__name__)

router = APIRouter()


async def _run_workflow(payload: ExecutionPayload) -> None:
    """Execute the workflow graph and send exactly one callback with the result."""
    callback_url = payload.callback_url
    status = "FAILED"
    result: Optional[dict] = None
    error: Optional[str] = None
    final_state: Optional[dict] = None

    try:
        config = payload.config
        builder = AgenticGraphBuilder()
        graph = builder.build(config)

        initial_state: WorkflowState = {
            "workflow_id": payload.workflow_id,
            "input": payload.input,
            "config": config,
            "plan": None,
            "validation": None,
            "execution": None,
            "evaluation": None,
            "routing_history": [],
            "current_iteration": 0,
            "max_iterations": int(config.get("maxIterations", DEFAULT_MAX_ITERATIONS)),
            "next_agent": None,
            "retry_count": 0,
            "max_retries": int(config.get("maxRetries", DEFAULT_MAX_RETRIES)),
            "status": "initialized",
            "error": None,
        }

        final_state = graph.invoke(initial_state)

        if final_state.get("status") == "COMPLETED" or (
            final_state.get("evaluation") and final_state["evaluation"].get("passed")
        ):
            status = "COMPLETED"
        else:
            status = "FAILED"
            error = final_state.get("error")

        result = {
            "plan": final_state.get("plan"),
            "validationResult": final_state.get("validation"),
            "executionOutput": final_state.get("execution"),
            "evaluation": final_state.get("evaluation"),
            "routingHistory": final_state.get("routing_history", []),
            "totalIterations": final_state.get("current_iteration", 0),
            "finalOutput": final_state.get("execution", {}) or {},
        }

    except Exception as exc:
        logger.exception("Workflow execution failed for %s", payload.workflow_id)
        status = "FAILED"
        error = str(exc)
        # Preserve any intermediate results accumulated before the exception
        if final_state is not None:
            result = {
                "plan": final_state.get("plan"),
                "validationResult": final_state.get("validation"),
                "executionOutput": final_state.get("execution"),
                "evaluation": final_state.get("evaluation"),
                "routingHistory": final_state.get("routing_history", []),
                "totalIterations": final_state.get("current_iteration", 0),
                "finalOutput": final_state.get("execution", {}) or {},
            }

    finally:
        # Ensure exactly one callback per execution
        if callback_url:
            callback_body: dict = {"status": status, "result": result}
            if error:
                callback_body["error"] = error

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    await client.post(
                        callback_url,
                        json=callback_body,
                        headers={
                            "Content-Type": "application/json",
                        },
                    )
            except Exception as cb_exc:
                logger.error(
                    "Failed to send callback for workflow %s: %s",
                    payload.workflow_id,
                    cb_exc,
                )


@router.post("/execute")
async def execute(
    payload: ExecutionPayload,
    background_tasks: BackgroundTasks,
):
    """Accept an execution request and run the graph in the background."""
    background_tasks.add_task(_run_workflow, payload)

    return {
        "workflow_id": payload.workflow_id,
        "status": "accepted",
        "message": "Workflow execution started",
    }
