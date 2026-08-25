export interface SubsystemHealth {
  name: string;
  status: 'HEALTHY' | 'DEGRADED' | 'UNAVAILABLE' | 'NOT_EXPOSED';
  latency_ms?: number;
  message?: string;
  is_exposed: boolean;
}

export interface SystemHealthResponse {
  backend_status: 'ok' | 'degraded' | 'error';
  timestamp: string;
  subsystems: SubsystemHealth[];
}
