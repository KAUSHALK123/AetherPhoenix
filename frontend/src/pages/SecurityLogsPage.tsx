import React from 'react';
import { ShieldAlert } from 'lucide-react';
import { Badge } from '../components/common/Badge';

export const SecurityLogsPage: React.FC = () => {
  const logs = [
    {
      timestamp: '19:28:12',
      event: 'PERMISSION_PRE_AUTHORIZED',
      severity: 'INFO',
      details: 'Workflow wf-8f4008 granted BROWSER_ACCESS in ASSISTED mode',
    },
    {
      timestamp: '19:28:14',
      event: 'SANDBOX_BOUNDARY_CHECK',
      severity: 'SUCCESS',
      details: 'Playwright navigation restricted to approved domains whitelist',
    },
    {
      timestamp: '19:28:20',
      event: 'SECURITY_AUDIT_PASSED',
      severity: 'SUCCESS',
      details: 'No unsafe shell command injection or local file exfiltration detected',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-amber-400" />
            Security & Audit Logs
          </h2>
          <p className="text-xs text-slate-400">
            Immutable audit log for tool sandboxing, permission evaluations and system events
          </p>
        </div>

        <Badge variant="warning">AUDIT LOGGING ON</Badge>
      </div>

      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <div className="space-y-2 font-mono text-xs">
          {logs.map((log, idx) => (
            <div
              key={idx}
              className="p-3.5 bg-slate-950/70 rounded-xl border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3"
            >
              <div className="flex items-center gap-3">
                <span className="text-slate-500">[{log.timestamp}]</span>
                <span className="text-sky-300 font-bold">{log.event}</span>
                <span className="text-slate-300 font-sans text-xs">{log.details}</span>
              </div>
              <Badge variant={log.severity === 'SUCCESS' ? 'success' : 'primary'}>
                {log.severity}
              </Badge>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
