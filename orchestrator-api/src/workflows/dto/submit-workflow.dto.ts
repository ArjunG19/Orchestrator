import {
  IsNotEmpty,
  IsNotEmptyObject,
  IsObject,
  IsOptional,
  IsString,
  ValidateNested,
} from 'class-validator';
import { Type } from 'class-transformer';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { WorkflowConfig } from './workflow-config.dto';

export class SubmitWorkflowDto {
  @ApiProperty({
    description:
      'The workflow input. Can be a plain text string or a JSON object.',
    oneOf: [{ type: 'string' }, { type: 'object' }],
    example: 'Analyze sales data and generate a report',
  })
  @IsNotEmpty()
  input: string | Record<string, unknown>;

  @ApiPropertyOptional({
    description: 'Optional workflow configuration overrides',
    type: () => WorkflowConfig,
  })
  @IsOptional()
  @ValidateNested()
  @Type(() => WorkflowConfig)
  config?: WorkflowConfig;
}
