export type WorkflowStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';

export interface RoutingDecision {
  next_agent: 'planner' | 'validator' | 'executor' | 'evaluator' | 'done';
  reasoning: string;
  confidence: number;
}

export interface PlanStep {
  step_id: string;
  description: string;
  expected_output: string;
}

export interface ValidationResult {
  is_valid: boolean;
  issues: string[];
}

export interface ExecutionOutput {
  step_results: Record<string, unknown>[];
  success: boolean;
}

export interface EvaluationResult {
  passed: boolean;
  score: number;
  feedback: string;
}

export interface WorkflowResult {
  plan: PlanStep[];
  validationResult: ValidationResult;
  executionOutput: ExecutionOutput;
  evaluation: EvaluationResult;
  routingHistory: RoutingDecision[];
  totalIterations: number;
  finalOutput: Record<string, unknown>;
}

export interface WorkflowResponse {
  workflowId: string;
  status: WorkflowStatus;
}

export interface WorkflowStatusResponse {
  workflowId: string;
  status: WorkflowStatus;
  result: WorkflowResult | null;
}
