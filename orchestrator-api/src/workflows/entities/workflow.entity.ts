import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  CreateDateColumn,
  UpdateDateColumn,
} from 'typeorm';
import { WorkflowStatus, WorkflowResult } from '../interfaces/workflow.interfaces';
import { WorkflowConfig } from '../dto/workflow-config.dto';

@Entity('workflows')
export class Workflow {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ type: 'varchar', default: 'PENDING' })
  status: WorkflowStatus;

  @Column({ type: 'jsonb' })
  input: Record<string, unknown>;

  @Column({ type: 'jsonb' })
  config: WorkflowConfig;

  @Column({ type: 'jsonb', nullable: true })
  result: WorkflowResult | null;

  @CreateDateColumn()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;
}
