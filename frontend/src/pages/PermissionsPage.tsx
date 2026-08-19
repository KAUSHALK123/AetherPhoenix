import React, { useEffect, useState } from 'react';
import { usePermissionStore } from '../store/permissionStore';

export const PermissionsPage: React.FC = () => {
  const pendingRequests = usePermissionStore((state) => state.pendingRequests);
  const approveRequest = usePermissionStore((state) => state.approveRequest);
  const rejectRequest = usePermissionStore((state) => state.rejectRequest);
  const fetchPending = usePermissionStore((state) => state.fetchPending);

  const [history, setHistory] = useState([
    { label: 'Network Access', agent: 'API-Fetcher', time: '2m ago', status: 'Approved' },
    { label: 'Read Downloads', agent: 'Worker-1', time: '15m ago', status: 'Approved' },
    { label: 'Write System32', agent: 'Worker-1', time: '1h ago', status: 'Denied' },
  ]);

  useEffect(() => {
    fetchPending();
  }, [fetchPending]);

  const handleApprove = async (id: string, capability: string, agent: string) => {
    await approveRequest(id);
    setHistory((prev) => [
      { label: capability, agent, time: 'Just now', status: 'Approved' },
      ...prev,
    ]);
  };

  const handleReject = async (id: string, capability: string, agent: string) => {
    await rejectRequest(id, 'User denied permission via Permission Center');
    setHistory((prev) => [
      { label: capability, agent, time: 'Just now', status: 'Denied' },
      ...prev,
    ]);
  };

  return (
    <div className="flex flex-col flex-1 min-h-[calc(100vh-4rem)]">
      <main className="p-6 md:p-10 max-w-6xl mx-auto w-full space-y-10 flex-1">
        <div className="flex justify-between items-end border-b border-outline-variant/30 pb-6">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold mb-2 text-white">Permission Center</h1>
            <p className="text-on-surface-muted text-sm md:text-base">
              Manage sensitive execution requests from active agents.
            </p>
          </div>
          <div className="hidden sm:flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/30 px-4 py-1.5 rounded-full">
            <span className="material-symbols-outlined text-emerald-400 text-sm icon-fill">gpp_good</span>
            <span className="text-xs font-bold text-emerald-400">System Shield Active</span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Active Requests Column */}
          <div className="lg:col-span-8 flex flex-col gap-6">
            <h2 className="text-xl font-bold flex items-center gap-2 text-white">
              <span className="material-symbols-outlined text-accent-electric">notifications_active</span>
              Active Requests
              {pendingRequests.length > 0 && (
                <span className="px-2 py-0.5 bg-accent-electric/20 text-accent-electric text-xs rounded-full">
                  {pendingRequests.length}
                </span>
              )}
            </h2>

            {pendingRequests.length === 0 ? (
              /* Fallback / Mock active card from Stitch design if queue empty */
              <div className="glass-panel rounded-xl p-6 md:p-8 relative overflow-hidden glow-active">
                <div className="flex justify-between items-start mb-6">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-full bg-surface-container flex items-center justify-center border border-outline-variant">
                      <span className="material-symbols-outlined text-primary text-2xl">smart_toy</span>
                    </div>
                    <div>
                      <h3 className="font-bold text-lg text-white">Worker-1</h3>
                      <p className="text-xs text-on-surface-muted">System Agent</p>
                    </div>
                  </div>
                  <div className="bg-amber-500/20 border border-amber-500/50 px-3 py-1 rounded-full flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-amber-500 text-sm">warning</span>
                    <span className="text-[10px] font-bold text-amber-500">MEDIUM RISK</span>
                  </div>
                </div>
                <div className="bg-surface-deep border border-outline-variant/50 rounded-lg p-5 mb-8">
                  <p className="font-bold text-white mb-2">
                    Action Requested: <code className="text-accent-electric">Write to /Downloads</code>
                  </p>
                  <p className="text-sm text-on-surface-muted italic">
                    "Move analyzed files into organized subfolders to declutter the directory."
                  </p>
                </div>
                <div className="flex gap-4">
                  <button
                    onClick={() =>
                      setHistory((prev) => [
                        { label: 'Write to /Downloads', agent: 'Worker-1', time: 'Just now', status: 'Approved' },
                        ...prev,
                      ])
                    }
                    className="flex-1 bg-primary text-white font-bold py-3 rounded-lg hover:bg-accent-electric transition-all shadow-lg flex items-center justify-center gap-2 cursor-pointer active:scale-95"
                  >
                    <span className="material-symbols-outlined text-lg">check_circle</span>
                    ALLOW
                  </button>
                  <button
                    onClick={() =>
                      setHistory((prev) => [
                        { label: 'Write to /Downloads', agent: 'Worker-1', time: 'Just now', status: 'Denied' },
                        ...prev,
                      ])
                    }
                    className="flex-1 border border-error text-error font-bold py-3 rounded-lg hover:bg-error/10 transition-all flex items-center justify-center gap-2 cursor-pointer active:scale-95"
                  >
                    <span className="material-symbols-outlined text-lg">block</span>
                    DENY
                  </button>
                </div>
              </div>
            ) : (
              pendingRequests.map((req) => {
                const capabilityName = req.permission_type || 'Execution Action';
                const agentName = `Task #${req.task_id || req.workflow_id}`;
                return (
                  <div
                    key={req.request_id}
                    className="glass-panel rounded-xl p-6 md:p-8 relative overflow-hidden glow-active"
                  >
                    <div className="flex justify-between items-start mb-6">
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-full bg-surface-container flex items-center justify-center border border-outline-variant">
                          <span className="material-symbols-outlined text-primary text-2xl">smart_toy</span>
                        </div>
                        <div>
                          <h3 className="font-bold text-lg text-white">{agentName}</h3>
                          <p className="text-xs text-on-surface-muted">Workflow #{req.workflow_id}</p>
                        </div>
                      </div>
                      <div className="bg-amber-500/20 border border-amber-500/50 px-3 py-1 rounded-full flex items-center gap-1.5">
                        <span className="material-symbols-outlined text-amber-500 text-sm">warning</span>
                        <span className="text-[10px] font-bold text-amber-500">
                          {req.risk_level?.toUpperCase() || 'MEDIUM RISK'}
                        </span>
                      </div>
                    </div>
                    <div className="bg-surface-deep border border-outline-variant/50 rounded-lg p-5 mb-8">
                      <p className="font-bold text-white mb-2">
                        Action Requested: <code className="text-accent-electric">{capabilityName}</code>
                      </p>
                      <p className="text-sm text-on-surface-muted italic">"{req.reason}"</p>
                    </div>
                    <div className="flex gap-4">
                      <button
                        onClick={() => handleApprove(req.request_id, capabilityName, agentName)}
                        className="flex-1 bg-primary text-white font-bold py-3 rounded-lg hover:bg-accent-electric transition-all shadow-lg flex items-center justify-center gap-2 cursor-pointer active:scale-95"
                      >
                        <span className="material-symbols-outlined text-lg">check_circle</span>
                        ALLOW
                      </button>
                      <button
                        onClick={() => handleReject(req.request_id, capabilityName, agentName)}
                        className="flex-1 border border-error text-error font-bold py-3 rounded-lg hover:bg-error/10 transition-all flex items-center justify-center gap-2 cursor-pointer active:scale-95"
                      >
                        <span className="material-symbols-outlined text-lg">block</span>
                        DENY
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* History Column */}
          <div className="lg:col-span-4 flex flex-col gap-6">
            <h2 className="text-xl font-bold flex items-center gap-2 text-white">
              <span className="material-symbols-outlined text-on-surface-muted">history</span>
              History
            </h2>
            <div className="glass-panel p-4 rounded-xl space-y-2">
              {history.map((h, i) => (
                <div
                  key={i}
                  className="flex items-center gap-4 p-3 rounded-lg hover:bg-surface-variant/30 transition-colors"
                >
                  <span
                    className={`material-symbols-outlined ${
                      h.status === 'Approved' ? 'text-emerald-400' : 'text-error'
                    } text-sm`}
                  >
                    {h.status === 'Approved' ? 'check_circle' : 'block'}
                  </span>
                  <div className="flex-1">
                    <p className="text-xs font-bold leading-none mb-1 text-white">{h.label}</p>
                    <p className="text-[10px] text-on-surface-muted uppercase tracking-tighter">
                      {h.agent}
                    </p>
                  </div>
                  <span className="text-[10px] font-bold text-on-surface-muted">{h.time}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};
