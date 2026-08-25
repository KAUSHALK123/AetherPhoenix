import React, { useState } from 'react';
import { KeyRound, Plus, Copy, Check } from 'lucide-react';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';

export const ApiTokensPage: React.FC = () => {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const tokens = [
    {
      id: 'tok-1',
      name: 'Default Desktop Agent Key',
      prefix: 'aeth_live_89f...28a',
      created: '2026-08-10',
      lastUsed: 'Just now',
      role: 'Admin',
    },
    {
      id: 'tok-2',
      name: 'CI/CD Automated Test Pipeline',
      prefix: 'aeth_test_41c...99e',
      created: '2026-08-15',
      lastUsed: '3 hours ago',
      role: 'Restricted',
    },
  ];

  const handleCopy = (prefix: string) => {
    navigator.clipboard?.writeText(prefix);
    setCopiedKey(prefix);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <KeyRound className="w-5 h-5 text-sky-400" />
            API Tokens & Key Management
          </h2>
          <p className="text-xs text-slate-400">
            Manage authentication credentials for external integrations and local CLI agents
          </p>
        </div>

        <Button variant="primary" size="sm" onClick={() => alert('Generating new API key...')}>
          <Plus className="w-4 h-4 mr-1" />
          Create New Token
        </Button>
      </div>

      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <div className="space-y-3">
          {tokens.map((tok) => (
            <div
              key={tok.id}
              className="glass-card rounded-xl p-4 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4 font-mono text-xs"
            >
              <div>
                <div className="font-sans text-sm font-bold text-slate-200">{tok.name}</div>
                <div className="text-slate-400 mt-1 flex items-center gap-2">
                  <span className="bg-slate-900 px-2 py-0.5 rounded border border-slate-800 text-sky-300">
                    {tok.prefix}
                  </span>
                  <span>Created: {tok.created}</span>
                  <span>• Last used: {tok.lastUsed}</span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Badge variant={tok.role === 'Admin' ? 'primary' : 'neutral'}>
                  {tok.role}
                </Badge>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleCopy(tok.prefix)}
                >
                  {copiedKey === tok.prefix ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400 mr-1" />
                  ) : (
                    <Copy className="w-3.5 h-3.5 mr-1" />
                  )}
                  {copiedKey === tok.prefix ? 'Copied' : 'Copy'}
                </Button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
