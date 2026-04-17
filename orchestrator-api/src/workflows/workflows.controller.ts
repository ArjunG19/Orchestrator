import {
  Controller,
  Post,
  Get,
  Param,
  Body,
  HttpCode,
  HttpStatus,
  ParseUUIDPipe,
} from '@nestjs/common';
import {
  ApiTags,
  ApiOperation,
  ApiResponse,
  ApiParam,
  ApiBody,
} from '@nestjs/swagger';
import { WorkflowService } from './workflows.service';
import { SubmitWorkflowDto } from './dto/submit-workflow.dto';
import { WorkflowCallbackDto } from './dto/workflow-callback.dto';
import {
  WorkflowResponse,
  WorkflowStatusResponse,
  WorkflowResult,
} from './interfaces/workflow.interfaces';

@ApiTags('Workflows')
@Controller()
export class WorkflowController {
  constructor(private readonly workflowService: WorkflowService) {}

  @Post('workflows')
  @HttpCode(HttpStatus.ACCEPTED)
  @ApiOperation({
    summary: 'Submit a new workflow',
    description:
      'Accepts workflow input and optional configuration, creates a new workflow, and triggers asynchronous execution via the LangGraph Service. Returns immediately with the workflow ID and PENDING status.',
  })
  @ApiBody({ type: SubmitWorkflowDto })
  @ApiResponse({
    status: 202,
    description: 'Workflow accepted and queued for execution.',
    schema: {
      type: 'object',
      properties: {
        workflowId: { type: 'string', format: 'uuid' },
        status: { type: 'string', example: 'PENDING' },
      },
    },
  })
  @ApiResponse({ status: 400, description: 'Invalid request body.' })
  @ApiResponse({ status: 401, description: 'Missing or invalid API key.' })
  async submitWorkflow(
    @Body() dto: SubmitWorkflowDto,
  ): Promise<WorkflowResponse> {
    const workflow = await this.workflowService.createWorkflow(
      dto.input,
      dto.config,
    );

    // Fire-and-forget: trigger LangGraph execution asynchronously
    this.workflowService.triggerExecution(workflow.id).catch(() => {
      // Error handling is done inside triggerExecution
    });

    return {
      workflowId: workflow.id,
      status: workflow.status,
    };
  }

  @Get('workflows/:id')
  @ApiOperation({
    summary: 'Get workflow status',
    description:
      'Retrieves the current status and result of a workflow by its ID. When the workflow is COMPLETED or FAILED, the result field contains the full execution output.',
  })
  @ApiParam({
    name: 'id',
    description: 'UUID of the workflow',
    type: 'string',
    format: 'uuid',
  })
  @ApiResponse({
    status: 200,
    description: 'Workflow status retrieved successfully.',
    schema: {
      type: 'object',
      properties: {
        workflowId: { type: 'string', format: 'uuid' },
        status: {
          type: 'string',
          enum: ['PENDING', 'RUNNING', 'COMPLETED', 'FAILED'],
        },
        result: {
          type: 'object',
          nullable: true,
          description:
            'Full workflow result when status is COMPLETED or FAILED, null otherwise.',
        },
      },
    },
  })
  @ApiResponse({ status: 401, description: 'Missing or invalid API key.' })
  @ApiResponse({ status: 404, description: 'Workflow not found.' })
  async getWorkflowStatus(
    @Param('id', new ParseUUIDPipe()) id: string,
  ): Promise<WorkflowStatusResponse> {
    const workflow = await this.workflowService.getWorkflow(id);

    return {
      workflowId: workflow.id,
      status: workflow.status,
      result: workflow.result,
    };
  }

  @Post('callbacks/:workflowId')
  @HttpCode(HttpStatus.OK)
  @ApiOperation({
    summary: 'Handle workflow callback',
    description:
      'Receives a callback from the LangGraph Service with the final workflow status and result. Used internally for asynchronous workflow completion.',
  })
  @ApiParam({
    name: 'workflowId',
    description: 'UUID of the workflow to update',
    type: 'string',
    format: 'uuid',
  })
  @ApiBody({ type: WorkflowCallbackDto })
  @ApiResponse({
    status: 200,
    description: 'Callback received and processed.',
    schema: {
      type: 'object',
      properties: {
        received: { type: 'boolean', example: true },
      },
    },
  })
  @ApiResponse({ status: 400, description: 'Invalid callback payload.' })
  async handleCallback(
    @Param('workflowId', new ParseUUIDPipe()) workflowId: string,
    @Body() dto: WorkflowCallbackDto,
  ): Promise<{ received: boolean }> {
    await this.workflowService.updateWorkflowResult(
      workflowId,
      dto.status,
      ((dto.result as unknown) as WorkflowResult) ?? null,
    );

    return { received: true };
  }
}
