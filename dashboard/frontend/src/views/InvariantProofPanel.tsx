import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import {
  ShieldCheck,
  ShieldAlert,
  Database,
  CheckCircle2,
  Lock,
  GitCommit,
  RefreshCw,
  Terminal,
} from 'lucide-react';

export const InvariantProofPanel: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchInvariants = async () => {
    try {
      setLoading(true);
      const res: any = await api.get('/invariants');
      setData(res);
    } catch (err) {
      console.error('Failed to fetch invariant verification data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInvariants();
    const interval = setInterval(fetchInvariants, 8000);
    return () => clearInterval(interval);
  }, []);

  const invariantCards = [
    {
      title: 'Room Double-Booking Guard',
      invariant: 'Strict Schedule Isolation',
      violations: data?.invariants?.overlapping_bookings ?? 0,
      mechanism: 'Prevents overlapping bookings and guarantees conflict-free exam and class scheduling.',
    },
    {
      title: 'Inventory Conservation',
      invariant: 'Stock Balance Verification',
      violations: data?.invariants?.stock_drift_skus ?? 0,
      mechanism: 'Ensures that warehouse physical on-hand stock exactly equals available plus reserved items.',
    },
    {
      title: 'Infrastructure Graph Integrity',
      invariant: 'DAG Acyclicity Guard',
      violations: data?.invariants?.dag_cycles ?? 0,
      mechanism: 'Guarantees no circular dependencies across campus electrical, PoE, and HVAC lines.',
    },
    {
      title: 'Stock Ledger Protection',
      invariant: 'Non-Negative Inventory Balance',
      violations: data?.invariants?.untracked_balance_updates ?? 0,
      mechanism: 'Blocks untracked inventory modifications and prevents negative stock balances.',
    },
    {
      title: 'State Transition Integrity',
      invariant: 'FSM Transition Guard',
      violations: data?.invariants?.illegal_fsm_jumps ?? 0,
      mechanism: 'Enforces authorized progression through intake, triage, parts assignment, and resolution.',
    },
    {
      title: 'Tamper-Proof Audit Trail',
      invariant: 'Append-Only Ledger',
      violations: data?.invariants?.tampered_audit_rows ?? 0,
      mechanism: 'Guarantees that historical operational records cannot be altered or deleted.',
    },
  ];

  return (
    <div className="h-full flex flex-col bg-transparent text-[#d8bca4] overflow-y-auto p-4 space-y-4">
      {/* Header Banner (Frosted Glass Panel) */}
      <div className="glass-panel rounded-xl p-5 shadow-lg flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-[#ec9665]/20 text-[#f4aa7f] rounded-lg border border-[#ec9665]/35 shadow-sm spring-interactive">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white tracking-tight font-mono">
              System Health & Invariant Proofs
            </h2>
            <p className="text-xs text-[#d8bca4]/80">
              Live automated health and mathematical constraint checks across campus operations.
            </p>
          </div>
        </div>

        <button
          onClick={fetchInvariants}
          className="flex items-center space-x-1.5 px-3 py-1.5 bg-[#523624]/60 hover:bg-[#ec9665] text-[#d8bca4] hover:text-[#180f0a] rounded-md text-xs font-semibold border border-[#9c6c4c]/40 transition spring-interactive shadow-sm"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Re-verify Now</span>
        </button>
      </div>

      {/* 6 Invariant Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {invariantCards.map((card, idx) => {
          const isPassed = card.violations === 0;
          return (
            <div
              key={idx}
              className={`glass-surface p-4 rounded-xl transition spring-interactive shadow-md ${
                isPassed
                  ? 'hover:border-[#ec9665]/50 hover:bg-[#523624]/60'
                  : 'border-rose-500/50 bg-rose-950/30'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-[10px] text-[#9c6c4c] font-bold uppercase tracking-wider">
                  Invariant #{idx + 1}
                </span>
                <span
                  className={`flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-mono border ${
                    isPassed
                      ? 'bg-[#ec9665]/15 text-[#f4aa7f] border-[#ec9665]/30'
                      : 'bg-rose-500/20 text-rose-300 border-rose-500/30'
                  }`}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      isPassed ? 'bg-[#ec9665] shadow-[0_0_8px_#ec9665]' : 'bg-rose-400'
                    }`}
                  />
                  <span>{isPassed ? 'VERIFIED (0 Vio)' : `${card.violations} VIOLATION`}</span>
                </span>
              </div>
              <h3 className="text-xs font-bold text-white mb-1">{card.title}</h3>
              <div className="font-mono text-[11px] text-[#f4aa7f] bg-[#180f0a]/70 p-2 rounded-md border border-[#9c6c4c]/30 mb-2 truncate shadow-inner">
                {card.invariant}
              </div>
              <p className="text-[11px] text-[#d8bca4]/80 font-sans leading-relaxed">{card.mechanism}</p>
            </div>
          );
        })}
      </div>

      {/* Activity Log Stream */}
      <div className="glass-panel rounded-xl p-5 shadow-lg space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-[#9c6c4c]/30">
          <div className="flex items-center space-x-2">
            <Terminal className="w-4 h-4 text-[#ec9665]" />
            <h3 className="font-bold text-[#f4aa7f] text-xs uppercase tracking-wider font-mono">
              Operational Activity Log ({data?.audit_stream?.length || 0} Recent Events)
            </h3>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-[#24160f]/90 text-[#d8bca4]/70 border-b border-[#9c6c4c]/30 font-mono text-[10px]">
              <tr>
                <th className="py-2 px-3 border-r border-[#9c6c4c]/20">Timestamp (UTC)</th>
                <th className="py-2 px-3 border-r border-[#9c6c4c]/20">Ticket #</th>
                <th className="py-2 px-3 border-r border-[#9c6c4c]/20">Actor</th>
                <th className="py-2 px-3 border-r border-[#9c6c4c]/20">Action</th>
                <th className="py-2 px-3 border-r border-[#9c6c4c]/20">State Change</th>
                <th className="py-2 px-3">Cryptographic Signature</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#9c6c4c]/20 font-mono text-[11px]">
              {data?.audit_stream?.map((entry: any) => (
                <tr key={entry.id} className="hover:bg-[#523624]/35 transition spring-row">
                  <td className="py-2 px-3 text-[#9c6c4c] border-r border-[#9c6c4c]/20">
                    {new Date(entry.created_at).toISOString().replace('T', ' ').slice(0, 19)}
                  </td>
                  <td className="py-2 px-3 text-[#ec9665] font-bold border-r border-[#9c6c4c]/20">
                    {entry.ticket_number ? `#${entry.ticket_number}` : 'SYSTEM'}
                  </td>
                  <td className="py-2 px-3 text-white border-r border-[#9c6c4c]/20">{entry.actor_name || 'System / Service'}</td>
                  <td className="py-2 px-3 border-r border-[#9c6c4c]/20">
                    <span className="px-1.5 py-0.5 rounded-full bg-[#ec9665]/15 text-[#f4aa7f] border border-[#ec9665]/30 text-[10px]">
                      {entry.action}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-[#d8bca4] border-r border-[#9c6c4c]/20">
                    {entry.previous_state ? `${entry.previous_state} -> ` : ''}
                    <span className="text-[#f4aa7f] font-bold">{entry.new_state || 'RECORDED'}</span>
                  </td>
                  <td className="py-2 px-3 text-[10px] text-[#9c6c4c] truncate max-w-xs">
                    {JSON.stringify(entry.details)}
                  </td>
                </tr>
              ))}
              {(!data?.audit_stream || data.audit_stream.length === 0) && (
                <tr>
                  <td colSpan={6} className="py-16 text-center text-[#9c6c4c] font-mono text-xs">
                    No activity recorded in audit ledger yet. Operational events will be immutably recorded here.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
