"""LangGraph state-graph construction for the agentic workflow."""

from langgraph.graph import END, StateGraph

from app.agents.evaluator import EvaluatorAgent
from app.agents.executor import ExecutorAgent
from app.agents.planner import PlannerAgent
from app.agents.validator import ValidatorAgent
from app.models.state import WorkflowState
from app.prompt_registry import PromptRegistry
from app.workflow.router import OrchestratorRouter


# ------------------------------------------------------------------
# Conditional edge function (Task 6.6)
# ------------------------------------------------------------------

def route_from_router(state: WorkflowState) -> str:
    """Conditional edge: return 'fail' on FAILED status, else the router's decision."""
    if state.get("status") == "FAILED":
        return "fail"
    return state["next_agent"]


# ------------------------------------------------------------------
# Graph builder (Task 6.1)
# ------------------------------------------------------------------

class AgenticGraphBuilder:
    """Builds and compiles the LangGraph StateGraph for the agentic workflow."""

    def build(self, config: dict):
        """Construct the five-node hub-and-spoke graph and return the compiled graph.

        Nodes: router, planner, validator, executor, evaluator
        Topology:
          - Entry → router
          - router →(conditional)→ planner | validator | executor | evaluator | END(done) | END(fail)
          - planner / validator / executor / evaluator → router
        """
        prompt_registry = PromptRegistry()

        router = OrchestratorRouter(config, prompt_registry=prompt_registry)
        planner = PlannerAgent(config, prompt_registry=prompt_registry)
        validator = ValidatorAgent(config, prompt_registry=prompt_registry)
        executor = ExecutorAgent(config, prompt_registry=prompt_registry)
        evaluator = EvaluatorAgent(config, prompt_registry=prompt_registry)

        graph = StateGraph(WorkflowState)

        # --- Nodes ---
        graph.add_node("router", router.route)
        graph.add_node("planner", planner.run)
        graph.add_node("validator", validator.run)
        graph.add_node("executor", executor.run)
        graph.add_node("evaluator", evaluator.run)

        # --- Entry point ---
        graph.set_entry_point("router")

        # --- Conditional edges from router ---
        graph.add_conditional_edges(
            "router",
            route_from_router,
            {
                "planner": "planner",
                "validator": "validator",
                "executor": "executor",
                "evaluator": "evaluator",
                "done": END,
                "fail": END,
            },
        )

        # --- Every agent routes back to router ---
        graph.add_edge("planner", "router")
        graph.add_edge("validator", "router")
        graph.add_edge("executor", "router")
        graph.add_edge("evaluator", "router")

        return graph.compile()
