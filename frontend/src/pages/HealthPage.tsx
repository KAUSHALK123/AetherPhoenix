import React, { useState, useEffect } from 'react';
import { HeartPulse, CheckCircle2, AlertCircle, RefreshCw, Server, Database } from 'lucide-react';
import { healthService } from '../services/healthService';
import type { SystemHealthResponse } from '../types/health';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';

export const HealthPage: React.FC = () => {
  const [healthData, setHealthData] = useState<SystemHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchHealth = async () => {
    setLoading(true);
    try {
      const data = await healthService.getHealth();
      setHealthData(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <HeartPulse className="w-5 h-5 text-emerald-400" />
            System Health & Telemetry
          </h2>
          <p className="text-xs text-slate-400">
            Live diagnostic health statuses for API server, agents, database & tool engines
          </p>
        </div>

        <Button variant="secondary" size="sm" onClick={fetchHealth} isLoading={loading}>
          <RefreshCw className="w-3.5 h-3.5 mr-1" />
          Check Health
        </Button>
      </div>

      {/* Main Status Overview Card */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-emerald-950/80 border border-emerald-500/40 text-emerald-400 flex items-center justify-center shadow-lg shadow-emerald-950/40">
            <Server className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-mono text-slate-500 uppercase tracking-wider">
              FastAPI Core Endpoint (GET /health)
            </div>
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2 mt-0.5">
              System State:{' '}
              <span
                className={
                  healthData?.backend_status === 'ok'
                    ? 'text-emerald-400'
                    : 'text-rose-400'
                }
              >
                {healthData?.backend_status === 'ok' ? 'OPERATIONAL' : 'DEGRADED / OFFLINE'}
              </span>
            </h3>
          </div>
        </div>

        <div className="text-xs font-mono text-slate-400">
          Last Checked:{' '}
          <span className="text-slate-200">
            {healthData ? new Date(healthData.timestamp).toLocaleTimeString() : '—'}
          </span>
        </div>
      </div>

      {/* Subsystems Breakdown Grid */}
      <div className="space-y-3">
        <div className="text-xs font-mono uppercase text-slate-400 font-semibold">
          Subsystem Diagnostics
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {healthData?.subsystems.map((sub, idx) => (
            <div
              key={idx}
              className="glass-card rounded-xl p-4 border border-slate-800 flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                {sub.status === 'HEALTHY' ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                ) : sub.status === 'NOT_EXPOSED' ? (
                  <Database className="w-5 h-5 text-slate-500 shrink-0" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
                )}

                <div>
                  <div className="text-sm font-semibold text-slate-200">{sub.name}</div>
                  <div className="text-xs text-slate-500 font-mono">
                    {sub.message || (sub.is_exposed ? 'Live probe active' : 'Not directly exposed')}
                  </div>
                </div>
              </div>

              <Badge
                variant={
                  sub.status === 'HEALTHY'
                    ? 'success'
                    : sub.status === 'NOT_EXPOSED'
                    ? 'neutral'
                    : 'danger'
                }
              >
                {sub.status}
              </Badge>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
