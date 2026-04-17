import { IsInt, IsOptional, IsString, Max, Min } from 'class-validator';
import { ApiPropertyOptional } from '@nestjs/swagger';

export class WorkflowConfig {
  @ApiPropertyOptional({
    description: 'Maximum number of retries on agent failure',
    type: 'integer',
    minimum: 0,
    maximum: 10,
    default: 3,
    example: 3,
  })
  @IsOptional()
  @IsInt()
  @Min(0)
  @Max(10)
  maxRetries: number = 3;

  @ApiPropertyOptional({
    description: 'Maximum number of agent routing iterations',
    type: 'integer',
    minimum: 1,
    maximum: 50,
    default: 15,
    example: 15,
  })
  @IsOptional()
  @IsInt()
  @Min(1)
  @Max(50)
  maxIterations: number = 15;

  @ApiPropertyOptional({
    description: 'Workflow execution timeout in seconds',
    type: 'integer',
    minimum: 1,
    maximum: 600,
    default: 300,
    example: 300,
  })
  @IsOptional()
  @IsInt()
  @Min(1)
  @Max(600)
  timeoutSeconds: number = 300;

  @ApiPropertyOptional({
    description: 'LLM model name override for all agents in this workflow',
    type: 'string',
    example: 'llama-3.3-70b-versatile',
  })
  @IsOptional()
  @IsString()
  model?: string;
}
