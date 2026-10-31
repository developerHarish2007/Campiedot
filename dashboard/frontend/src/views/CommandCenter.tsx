import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import {
  Activity,
  AlertTriangle,
  Clock,
  Wrench,
  CheckCircle,
  Send,
  Zap,
  Sparkles,
  Building,
  RefreshCw,
  TrendingUp,
  Cpu,
  Layers,
  ArrowUpRight,
} from 'lucide-react';

export const CommandCenter: React.FC = () => {
  const { currentUser } = useAuth();
  const [pulse, setPulse] = useState<any>(null);
  const [summary, setSummary] = useState<any>(null);
  const [activeTickets, setActiveTickets] = useState<any[]>([]);
  const [intakeText, setIntakeText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [intakeResult, setIntakeResult] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [pulseData, summaryData, ticketsData] = await Promise.all([
        api.get<any>('/pulse'),
        api.get<any>('/analytics/summary'),
        api.get<any[]>('/work-orders'),
      ]);
      setPulse(pulseData);
      setSummary(summaryData);
      setActiveTickets(ticketsData.slice(0, 10));
    } catch (err) {
      console.error('Error fetching command center data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [currentUser]);

  const handleIntakeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!intakeText.trim()) return;
    try {
      setIsSubmitting(true);
      const res: any = await api.post('/intake', {
        text: intakeText,
        channel: 'PORTAL_FORM',
      });
      setIntakeResult(res);
      setIntakeText('');
      fetchData();
    } catch (err: any) {
      alert(`Intake failed: ${err.message || 'Error'}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getVibeBadge = (vibe: string) => {
    switch (vibe) {
      case 'STABLE':
        return 'bg-[#ec9665]/20 text-[#f4aa7f] border-[#ec9665]/40';
      case 'ELEVATED_ATTENTION':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
      case 'SLA_WARNING':
        return 'bg-rose-500/20 text-rose-300 border-rose-500/40';
      default:
        return 'bg-[#9c6c4c]/30 text-[#d8bca4] border-[#9c6c4c]/40';
    }
  };

  return (
    <div className="h-full flex flex-col bg-transparent text-[#d8bca4] overflow-y-auto p-4 space-y-4">
      {/* Top Telemetry & Health Ribbon (Frosted Glass Cards) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 shrink-0">
        <div className="glass-surface rounded-lg p-3 flex items-center justify-between spring-interactive shadow-sm">
          <div>
            <span className="text-[10px] font-mono text-[#9c6c4c] uppercase tracking-wider block">
              Campus Status
            </span>
            <div className="text-sm font-bold text-white font-mono mt-0.5">
              {pulse?.status_vibe?.replace('_', ' ') || 'OPERATIONAL'}
            </div>
          </div>
          <span
            className={`text-[9px] px-2 py-0.5 rounded-full font-mono border ${getVibeBadge(
              pulse?.status_vibe || 'STABLE'
            )}`}
          >
            LIVE
          </span>
        </div>

        <div className="glass-surface rounded-lg p-3 flex items-center justify-between spring-interactive shadow-sm">
          <div>
            <span className="text-[10px] font-mono text-[#9c6c4c] uppercase tracking-wider block">
              Active Disruptions
            </span>
            <div className="text-sm font-bold text-rose-400 font-mono mt-0.5">
              {summary?.open_requests_count || pulse?.metrics?.open_requests || 0} Open
            </div>
          </div>
          <span className="text-[9px] px-2 py-0.5 rounded-full font-mono bg-rose-500/15 text-rose-300 border border-rose-500/30">
            P0/P1
          </span>
        </div>

        <div className="glass-surface rounded-lg p-3 flex items-center justify-between spring-interactive shadow-sm">
          <div>
            <span className="text-[10px] font-mono text-[#9c6c4c] uppercase tracking-wider block">
              Inventory Constrained
            </span>
            <div className="text-sm font-bold text-[#f4aa7f] font-mono mt-0.5">
              {summary?.blocked_by_parts_count || 0} Blocked
            </div>
          </div>
          <span className="text-[9px] px-2 py-0.5 rounded-full font-mono bg-[#ec9665]/15 text-[#f4aa7f] border border-[#ec9665]/30">
            Store Hold
          </span>
        </div>

        <div className="glass-surface rounded-lg p-3 flex items-center justify-between spring-interactive shadow-sm">
          <div>
            <span className="text-[10px] font-mono text-[#9c6c4c] uppercase tracking-wider block">
              SLA Compliance
            </span>
            <div className="text-sm font-bold text-[#ec9665] font-mono mt-0.5">
              {summary?.sla_compliance_percentage
                ? Number(summary.sla_compliance_percentage).toFixed(1)
                : 100.0}
              %
            </div>
          </div>
          <span className="text-[9px] px-2 py-0.5 rounded-full font-mono bg-[#ec9665]/20 text-[#f4aa7f] border border-[#ec9665]/40">
            Nominal
          </span>
        </div>
      </div>

      {/* Primary 60/40 Split */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1">
        {/* 60% Left Pane: Operational Briefing & Active Incident Stream (7 Cols) */}
        <div className="lg:col-span-7 space-y-4 flex flex-col">
          {/* Executive Pulse Briefing (Glass Panel) */}
          <div className="glass-panel rounded-xl p-4 space-y-2.5 shadow-lg">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[#f4aa7f] uppercase tracking-wider font-mono flex items-center space-x-1.5">
                <Sparkles className="w-3.5 h-3.5 text-[#ec9665]" />
                <span>Executive Operations Briefing</span>
              </span>
              <span className="text-[10px] text-[#9c6c4c] font-mono">SRM Easwari Digital Twin</span>
            </div>
            <div className="p-3 bg-[#180f0a]/80 border border-[#9c6c4c]/30 rounded-lg text-xs text-[#d8bca4] leading-relaxed font-mono shadow-inner">
              {pulse?.pulse_text || 'Campus facilities nominal across all operational sectors.'}
            </div>
          </div>

          {/* Real-time Work Order Feed (Glass Panel) */}
          <div className="glass-panel rounded-xl p-4 flex-1 flex flex-col space-y-2 overflow-hidden shadow-lg">
            <div className="flex items-center justify-between pb-2 border-b border-[#9c6c4c]/30">
              <span className="text-xs font-bold text-[#f4aa7f] uppercase tracking-wider font-mono flex items-center space-x-1.5">
                <Activity className="w-3.5 h-3.5 text-[#ec9665]" />
                <span>Live Operational Feed ({activeTickets.length} active)</span>
              </span>
              <button
                onClick={fetchData}
                className="text-[#9c6c4c] hover:text-[#ec9665] p-1 rounded transition spring-interactive"
                title="Refresh"
              >
                <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>

            <div className="overflow-auto flex-1">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-[#24160f]/90 text-[#d8bca4]/70 font-mono text-[10px] border-b border-[#9c6c4c]/30 sticky top-0 shadow-sm">
                  <tr>
                    <th className="py-2 px-2.5 w-16 border-r border-[#9c6c4c]/20">Ticket</th>
                    <th className="py-2 px-2.5 w-28 border-r border-[#9c6c4c]/20">Location</th>
                    <th className="py-2 px-2.5 w-32 border-r border-[#9c6c4c]/20">Category</th>
                    <th className="py-2 px-2.5 w-20 border-r border-[#9c6c4c]/20 text-right">Priority</th>
                    <th className="py-2 px-2.5 w-24 border-r border-[#9c6c4c]/20 text-right">State</th>
                    <th className="py-2 px-2.5 text-right">Assigned</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#9c6c4c]/20 font-sans">
                  {activeTickets.map((t) => (
                    <tr key={t.id} className="hover:bg-[#523624]/35 transition h-8 spring-row">
                      <td className="py-1 px-2.5 font-mono font-bold text-[#ec9665] border-r border-[#9c6c4c]/20">
                        #{t.ticket_number}
                      </td>
                      <td className="py-1 px-2.5 font-mono text-[#d8bca4] border-r border-[#9c6c4c]/20 truncate">
                        {t.node_code || 'General'}
                      </td>
                      <td className="py-1 px-2.5 font-mono text-[#f4aa7f] text-[11px] border-r border-[#9c6c4c]/20">
                        {t.category || 'TBD'}
                      </td>
                      <td className="py-1 px-2.5 font-mono text-right border-r border-[#9c6c4c]/20">
                        <span
                          className={`text-[9px] px-1.5 py-0.2 rounded font-mono border ${
                            t.calculated_priority === 'P0_CRITICAL'
                              ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                              : 'bg-[#523624]/50 text-[#d8bca4] border-[#9c6c4c]/30'
                          }`}
                        >
                          {t.calculated_priority || 'P2'}
                        </span>
                      </td>
                      <td className="py-1 px-2.5 font-mono text-right border-r border-[#9c6c4c]/20">
                        <span className="text-[10px] text-[#d8bca4]">{t.state}</span>
                      </td>
                      <td className="py-1 px-2.5 text-right font-mono text-[#f4aa7f] truncate">
                        {t.assigned_tech_name || (
                          <span className="text-[#9c6c4c] italic">Unassigned</span>
                        )}
                      </td>
                    </tr>
                  ))}
                  {activeTickets.length === 0 && (
                    <tr>
                      <td colSpan={6} className="py-6 px-4 text-center text-xs font-mono">
                        <div className="text-[#9c6c4c] mb-3">
                          No active work orders. Ready for real incident reports.
                        </div>
                        <div className="text-[10px] uppercase tracking-wider text-[#f4aa7f] mb-2 font-bold">
                          Quick Incident Templates (Click to fill & dispatch)
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-left">
                          <button
                            type="button"
                            onClick={() => setIntakeText('URGENT: Electrical short circuit sparks near switchboard in RM-ACAD-204!')}
                            className="p-2 bg-[#180f0a]/80 hover:bg-[#523624] border border-[#9c6c4c]/30 rounded text-[11px] text-[#f4aa7f] spring-interactive transition"
                          >
                            ⚡ Short circuit in RM-ACAD-204
                          </button>
                          <button
                            type="button"
                            onClick={() => setIntakeText('Water pipe leaking heavily and flooding corridor in EEC-MAIN')}
                            className="p-2 bg-[#180f0a]/80 hover:bg-[#523624] border border-[#9c6c4c]/30 rounded text-[11px] text-[#f4aa7f] spring-interactive transition"
                          >
                            🔧 Water leak in Main Block
                          </button>
                          <button
                            type="button"
                            onClick={() => setIntakeText('Central Air Handling Unit AHU-AUD-MAIN blowing hot air in Auditorium')}
                            className="p-2 bg-[#180f0a]/80 hover:bg-[#523624] border border-[#9c6c4c]/30 rounded text-[11px] text-[#f4aa7f] spring-interactive transition"
                          >
                            ❄️ AC failure in Auditorium
                          </button>
                          <button
                            type="button"
                            onClick={() => setIntakeText('EMERGENCY: Fire catching fast everywhere in Academic Tech Block near RM-ACAD-204!')}
                            className="p-2 bg-rose-950/40 hover:bg-rose-900/50 border border-rose-500/40 rounded text-[11px] text-rose-300 spring-interactive transition"
                          >
                            🚨 Fire hazard in Academic Block
                          </button>
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* 40% Right Pane: Incident Reporting & Emergency Protocols (5 Cols) */}
        <div className="lg:col-span-5 space-y-4 flex flex-col">
          {/* Incident Intake Terminal (Glass Panel) */}
          <div className="glass-panel rounded-xl p-4 space-y-3 shadow-lg">
            <div className="flex items-center space-x-2 pb-2 border-b border-[#9c6c4c]/30">
              <Zap className="w-3.5 h-3.5 text-[#ec9665]" />
              <h2 className="text-xs font-bold text-[#f4aa7f] uppercase tracking-wider font-mono">
                Rapid Incident Intake
              </h2>
            </div>

            <p className="text-[11px] text-[#d8bca4]/80 leading-relaxed font-mono">
              Describe room fault, fire hazard, or equipment breakdown. Multi-agent AI extracts entities
              and dispatches instructions.
            </p>

            <form onSubmit={handleIntakeSubmit} className="space-y-2.5">
              <textarea
                value={intakeText}
                onChange={(e) => setIntakeText(e.target.value)}
                rows={3}
                placeholder="e.g. URGENT: Electrical short circuit sparks near switchboard in RM-ACAD-204!"
                className="w-full glass-input rounded-md p-2.5 text-xs text-[#f4aa7f] font-mono focus:outline-none resize-none shadow-inner"
              />

              <button
                type="submit"
                disabled={isSubmitting || !intakeText.trim()}
                className="w-full py-2 bg-gradient-to-r from-[#ec9665] to-[#f4aa7f] hover:brightness-110 text-[#180f0a] rounded-md text-xs font-bold font-mono transition spring-interactive flex items-center justify-center space-x-1.5 shadow-[0_4px_16px_rgba(236,150,101,0.35)]"
              >
                <Send className="w-3 h-3" />
                <span>{isSubmitting ? 'Analyzing & Routing...' : 'Submit Incident Report'}</span>
              </button>
            </form>
          </div>

          {/* Real-time Emergency Protocol Output */}
          {intakeResult && (
            <div className="glass-panel rounded-xl p-4 space-y-2.5 shadow-lg">
              {intakeResult.emergency_instructions && (
                <div className="p-3 bg-rose-950/50 border border-rose-500/60 rounded-lg space-y-2 text-xs shadow-md">
                  <div className="flex items-center space-x-1.5 text-rose-300 font-bold">
                    <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                    <span>{intakeResult.emergency_instructions.headline}</span>
                  </div>
                  <div className="p-2 bg-rose-900/40 rounded border border-rose-500/40 text-[11px] text-rose-200 font-mono">
                    📍 Route: {intakeResult.emergency_instructions.evacuation_route}
                    <br />
                    🛡️ Assembly: {intakeResult.emergency_instructions.assembly_point}
                  </div>
                  <div className="text-[11px] text-[#d8bca4]">
                    <span className="font-bold text-rose-300 block mb-1">Immediate Safety Steps:</span>
                    <ul className="list-disc pl-4 space-y-0.5">
                      {intakeResult.emergency_instructions.immediate_actions?.map(
                        (act: string, idx: number) => (
                          <li key={idx}>{act}</li>
                        )
                      )}
                    </ul>
                  </div>
                </div>
              )}

              <div className="p-2.5 bg-[#180f0a]/80 border border-[#9c6c4c]/30 rounded-md text-xs font-mono space-y-1 shadow-inner">
                <div className="flex items-center justify-between text-[#ec9665] font-bold">
                  <span>Ticket #{intakeResult.ticket_number}</span>
                  <span>{intakeResult.state}</span>
                </div>
                <div className="text-[#d8bca4] text-[11px]">
                  Category: <span className="text-[#f4aa7f] font-semibold">{intakeResult.category || 'TBD'}</span>
                </div>
                <div className="text-[#9c6c4c] text-[10px]">
                  Summary: {intakeResult.concise_summary}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
