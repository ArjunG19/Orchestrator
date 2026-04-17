import {
  Injectable,
  Logger,
  NotFoundException,
  ConflictException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Workflow } from './entities/workflow.entity';
import { WorkflowConfig } from './dto/workflow-config.dto';
import {
  WorkflowStatus,
  WorkflowResult,
} from './interfaces/workflow.interfaces';
import { LangGraphClient } from './langgraph.client';

const VALID_TRANSITIONS: Record<string, WorkflowStatus[]> = {
  PENDING: ['RUNNING'],
  RUNNING: ['COMPLETED', 'FAILED'],
};

@Injectable()
export class WorkflowService {
  private readonly logger = new Logger(WorkflowService.name);
  private readonly defaultConfig: WorkflowConfig;

  constructor(
    @InjectRepository(Workflow)
    private readonly workflowRepository: Repository<Workflow>,
    private readonly langGraphClient: LangGraphClient,
    private readonly configService: ConfigService,
  ) {
    this.defaultConfig = {
      maxRetries: this.configService.get<number>('DEFAULT_MAX_RETRIES', 3),
      maxIterations: this.configService.get<number>('DEFAULT_MAX_ITERATIONS', 15),
      timeoutSeconds: this.configService.get<number>('DEFAULT_TIMEOUT_SECONDS', 300),
    };
  }

  async createWorkflow(
    input: string | Record<string, unknown>,
    config?: Partial<WorkflowConfig>,
  ): Promise<Workflow> {
    // Normalize plain text input into an object for the agents
    const normalizedInput: Record<string, unknown> =
      typeof input === 'string' ? { task: input } : input;
    const mergedConfig: WorkflowConfig = {
      ...this.defaultConfig,
      ...config,
    };

    const workflow = this.workflowRepository.create({
      status: 'PENDING' as WorkflowStatus,
      input: normalizedInput,
      config: mergedConfig,
      result: null,
    });

    return this.workflowRepository.save(workflow);
  }

  async getWorkflow(workflowId: string): Promise<Workflow> {
    const workflow = await this.workflowRepository.findOne({
      where: { id: workflowId },
    });

    if (!workflow) {
      throw new NotFoundException(`Workflow with ID "${workflowId}" not found`);
    }

    return workflow;
  }

  async updateWorkflowStatus(
    workflowId: string,
    newStatus: WorkflowStatus,
  ): Promise<Workflow> {
    const workflow = await this.getWorkflow(workflowId);

    this.validateTransition(workflow.status, newStatus);

    workflow.status = newStatus;
    return this.workflowRepository.save(workflow);
  }

  async updateWorkflowResult(
    workflowId: string,
    status: 'COMPLETED' | 'FAILED',
    result: WorkflowResult | null,
  ): Promise<Workflow> {
    const workflow = await this.getWorkflow(workflowId);

    this.validateTransition(workflow.status, status);

    workflow.status = status;
    workflow.result = result;
    return this.workflowRepository.save(workflow);
  }

  async triggerExecution(workflowId: string): Promise<void> {
    const workflow = await this.getWorkflow(workflowId);

    this.validateTransition(workflow.status, 'RUNNING');
    workflow.status = 'RUNNING';
    await this.workflowRepository.save(workflow);

    try {
      await this.langGraphClient.executeWorkflow(
        workflowId,
        workflow.input,
        workflow.config as unknown as Record<string, unknown>,
      );
    } catch {
      workflow.status = 'FAILED';
      workflow.result = { error: 'LangGraph service unreachable' } as any;
      await this.workflowRepository.save(workflow);
      this.logger.error(
        `Workflow ${workflowId} failed: LangGraph service unreachable`,
      );
    }
  }

  private validateTransition(
    currentStatus: WorkflowStatus,
    newStatus: WorkflowStatus,
  ): void {
    const allowed = VALID_TRANSITIONS[currentStatus];

    if (!allowed || !allowed.includes(newStatus)) {
      throw new ConflictException(
        `Invalid status transition from "${currentStatus}" to "${newStatus}"`,
      );
    }
  }
}
