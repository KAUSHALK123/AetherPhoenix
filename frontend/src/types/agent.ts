export type AgentStatus = 'ONLINE' | 'STANDBY' | 'BUSY' | 'OFFLINE' | 'DEGRADED';

export interface AgentInfo {
  id: string;
  name: string;
  role: 'Planner' | 'Worker' | 'Supervisor' | 'Healing' | string;
  status: AgentStatus;
  version: string;
  description: string;
  capabilities: string[];
  assigned_tasks_count?: number;
  last_active?: string;
}
