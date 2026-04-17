import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Workflow } from './entities/workflow.entity';
import { WorkflowService } from './workflows.service';
import { WorkflowController } from './workflows.controller';
import { LangGraphClient } from './langgraph.client';

@Module({
  imports: [TypeOrmModule.forFeature([Workflow])],
  controllers: [WorkflowController],
  providers: [WorkflowService, LangGraphClient],
  exports: [WorkflowService],
})
export class WorkflowsModule {}
