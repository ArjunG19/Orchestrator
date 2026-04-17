import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import axios from 'axios';

export interface ExecutionPayload {
  workflow_id: string;
  input: Record<string, unknown>;
  config: Record<string, unknown>;
  callback_url: string;
}

@Injectable()
export class LangGraphClient {
  private readonly logger = new Logger(LangGraphClient.name);
  private readonly langGraphUrl: string;
  private readonly orchestratorBaseUrl: string;

  constructor(private readonly configService: ConfigService) {
    this.langGraphUrl = this.configService.get<string>(
      'LANGGRAPH_SERVICE_URL',
      'http://localhost:8000',
    );
    this.orchestratorBaseUrl = this.configService.get<string>(
      'ORCHESTRATOR_BASE_URL',
      'http://localhost:3000',
    );
  }

  async executeWorkflow(
    workflowId: string,
    input: Record<string, unknown>,
    config: Record<string, unknown>,
  ): Promise<void> {
    const callbackUrl = `${this.orchestratorBaseUrl}/callbacks/${workflowId}`;

    const payload: ExecutionPayload = {
      workflow_id: workflowId,
      input,
      config,
      callback_url: callbackUrl,
    };

    try {
      await axios.post(`${this.langGraphUrl}/execute`, payload, {
        headers: {
          'Content-Type': 'application/json',
        },
        timeout: 10000,
      });
    } catch (error) {
      this.logger.error(
        `Failed to reach LangGraph service: ${error.message}`,
      );
      throw new Error('LangGraph service unreachable');
    }
  }
}
