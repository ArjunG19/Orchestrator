import { IsEnum, IsObject, IsOptional, IsString } from 'class-validator';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

export class WorkflowCallbackDto {
  @ApiProperty({
    description: 'Final status of the workflow execution',
    enum: ['COMPLETED', 'FAILED'],
    example: 'COMPLETED',
  })
  @IsEnum(['COMPLETED', 'FAILED'])
  status: 'COMPLETED' | 'FAILED';

  @ApiPropertyOptional({
    description: 'Workflow execution result containing plan, validation, execution output, and evaluation',
    type: 'object',
    nullable: true,
    example: { plan: 'Step 1: ...', execution: 'Done', evaluation: 'Success' },
  })
  @IsOptional()
  @IsObject()
  result: Record<string, unknown> | null;

  @ApiPropertyOptional({
    description: 'Error message when the workflow status is FAILED',
    type: 'string',
    example: 'Agent execution timed out after 300 seconds',
  })
  @IsOptional()
  @IsString()
  error?: string;
}
