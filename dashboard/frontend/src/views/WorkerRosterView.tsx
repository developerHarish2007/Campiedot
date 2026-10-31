import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import {
  Users,
  UserPlus,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Mail,
  Shield,
  Briefcase,
  X,
  Search,
} from 'lucide-react';

interface Worker {
  id: string;
  full_name: string;
  email: string;
  role: string;
  skills: string[];
  is_available: boolean;
  active_workload_count: number;
  max_concurrent_workload: number;
}

const TRADE_ROLES = [
  { value: 'ELECTRICAL', label: 'Electrician (Electrical & Power Systems)', icon: '⚡' },
  { value: 'PLUMBING', label: 'Plumber (Water & Drainage Systems)', icon: '🔧' },
  { value: 'NETWORK', label: 'Network Engineer (LAN, Switches & WiFi)', icon: '🌐' },
  { value: 'STRUCTURAL_SAFETY', label: 'Structural & Safety Specialist', icon: '🔨' },
  { value: 'SOS', label: 'SOS Medical & Emergency Care Officer', icon: '🚨' },
  { value: 'SWEEPER', label: 'Campus Sweeper & Housekeeping', icon: '🧹' },
];

export const WorkerRosterView: React.FC = () => {
  const { currentUser } = useAuth();
  const isAdmin = currentUser.role === 'SYS_ADMIN' || currentUser.role === 'FACILITIES_ADMIN';

  const [workers, setWorkers] = useState<Worker[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusMessage, setStatusMessage] = useState<{ text: string; isError: boolean } | null>(null);

  // Registration Drawer Form State
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [formName, setFormName] = useState('');
  const [formEmail, setFormEmail] = useState('');
  const [formRole, setFormRole] = useState('ELECTRICAL');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchWorkers = async () => {
    try {
      setLoading(true);
      const res = await api.get<Worker[]>('/staff/workers');
      setWorkers(res);
    } catch (err: any) {
      console.error('Failed to load workers:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkers();
  }, [currentUser]);

  const handleRegisterWorker = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAdmin) {
      setStatusMessage({ text: 'Only System Administrators can register workers.', isError: true });
      return;
    }
    if (!formName.trim() || !formEmail.trim()) {
      setStatusMessage({ text: 'Full Name and Email Address are required.', isError: true });
      return;
    }

    try {
      setIsSubmitting(true);
      setStatusMessage(null);
      await api.post('/staff/workers', {
        full_name: formName.trim(),
        email: formEmail.trim().toLowerCase(),
        role: formRole,
      });

      setStatusMessage({ text: `Worker "${formName}" registered successfully!`, isError: false });
      setFormName('');
      setFormEmail('');
      setIsDrawerOpen(false);
      fetchWorkers();
    } catch (err: any) {
      setStatusMessage({ text: err.message || 'Failed to register worker.', isError: true });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteWorker = async (workerId: string, name: string) => {
    if (!isAdmin) return;
    if (!confirm(`Are you sure you want to deregister worker "${name}"?`)) return;

    try {
      await api.delete(`/staff/workers/${workerId}`);
      setStatusMessage({ text: `Worker "${name}" deregistered.`, isError: false });
      fetchWorkers();
    } catch (err: any) {
      setStatusMessage({ text: err.message || 'Failed to deregister worker.', isError: true });
    }
  };

  const filteredWorkers = workers.filter((w) => {
    const q = searchQuery.toLowerCase();
    return (
      w.full_name.toLowerCase().includes(q) ||
      w.email.toLowerCase().includes(q) ||
      w.role.toLowerCase().includes(q)
    );
  });

  return (
    <div className="h-full flex flex-col bg-transparent text-[#d8bca4] overflow-hidden">
      {/* Top Action Bar (Glassmorphic) */}
      <div className="h-12 border-b border-[#9c6c4c]/30 bg-[#24160f]/75 backdrop-blur-md px-4 flex items-center justify-between shrink-0 shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            <Users className="w-4 h-4 text-[#ec9665]" />
            <h1 className="text-xs font-bold uppercase tracking-wider text-[#f4aa7f] font-mono">
              Maintenance Personnel & Trade Roster
            </h1>
          </div>
          <span className="text-[11px] px-2 py-0.5 rounded-full font-mono bg-[#ec9665]/15 text-[#f4aa7f] border border-[#ec9665]/30">
            {workers.length} Registered Personnel
          </span>
          {!isAdmin && (
            <span className="text-[10px] px-2 py-0.5 rounded-full font-mono bg-amber-500/10 text-amber-300 border border-amber-500/25">
              Read-Only View (Admin required for registration)
            </span>
          )}
        </div>

        <div className="flex items-center space-x-3">
          {/* Search Input with Spring */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-[#9c6c4c] absolute left-2.5 top-2" />
            <input
              type="text"
              placeholder="Filter by name, email, trade..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="glass-input rounded-md px-2.5 pl-8 py-1 text-xs placeholder-[#9c6c4c] focus:outline-none font-mono w-56 shadow-inner"
            />
          </div>

          <button
            onClick={fetchWorkers}
            className="p-1.5 bg-[#523624]/60 hover:bg-[#ec9665] text-[#d8bca4] hover:text-[#180f0a] rounded-md border border-[#9c6c4c]/40 text-xs transition spring-interactive shadow-sm"
            title="Refresh Roster"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>

          {isAdmin && (
            <button
              onClick={() => setIsDrawerOpen(true)}
              className="flex items-center space-x-1.5 px-3 py-1 bg-gradient-to-r from-[#ec9665] to-[#f4aa7f] hover:brightness-110 text-[#180f0a] rounded-md text-xs font-bold shadow-[0_2px_12px_rgba(236,150,101,0.35)] transition spring-interactive"
            >
              <UserPlus className="w-3.5 h-3.5" />
              <span>+ Register Worker</span>
            </button>
          )}
        </div>
      </div>

      {/* Feedback Alert Strip */}
      {statusMessage && (
        <div
          className={`px-4 py-2 text-xs flex items-center justify-between border-b ${
            statusMessage.isError
              ? 'bg-rose-950/60 text-rose-300 border-rose-500/30'
              : 'bg-[#ec9665]/20 text-[#f4aa7f] border-[#ec9665]/40'
          }`}
        >
          <div className="flex items-center space-x-2">
            {statusMessage.isError ? (
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            ) : (
              <CheckCircle2 className="w-4 h-4 text-[#ec9665] shrink-0" />
            )}
            <span>{statusMessage.text}</span>
          </div>
          <button onClick={() => setStatusMessage(null)} className="text-[#9c6c4c] hover:text-[#d8bca4] spring-interactive">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Main Workspace Split: Roster Ledger (60/40 Asymmetric Split) */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Pane: Ledger Table */}
        <div className="flex-1 border-r border-[#9c6c4c]/30 overflow-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-[#24160f]/90 backdrop-blur-md text-[#d8bca4]/70 border-b border-[#9c6c4c]/30 font-mono sticky top-0 z-10 shadow-sm">
              <tr>
                <th className="py-2.5 px-3 w-8 border-r border-[#9c6c4c]/20 text-center">●</th>
                <th className="py-2.5 px-3 w-40 border-r border-[#9c6c4c]/20">Worker Name</th>
                <th className="py-2.5 px-3 w-56 border-r border-[#9c6c4c]/20">Email (Dispatch)</th>
                <th className="py-2.5 px-3 w-36 border-r border-[#9c6c4c]/20">Trade Role</th>
                <th className="py-2.5 px-3 w-28 border-r border-[#9c6c4c]/20 text-right">Workload</th>
                <th className="py-2.5 px-3 w-24 border-r border-[#9c6c4c]/20 text-right">Status</th>
                {isAdmin && <th className="py-2.5 px-3 w-16 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#9c6c4c]/20 font-sans">
              {filteredWorkers.map((w) => {
                const trade = TRADE_ROLES.find((t) => t.value === w.role);
                return (
                  <tr key={w.id} className="hover:bg-[#523624]/35 transition h-9 spring-row">
                    <td className="py-2 px-3 border-r border-[#9c6c4c]/20 text-center">
                      <span
                        className={`inline-block w-1.5 h-1.5 rounded-full ${
                          w.is_available ? 'bg-[#ec9665] shadow-[0_0_8px_#ec9665]' : 'bg-[#5f493b]'
                        }`}
                        title={w.is_available ? 'Active on duty' : 'Off duty'}
                      />
                    </td>
                    <td className="py-2 px-3 font-semibold text-white border-r border-[#9c6c4c]/20 truncate">
                      {w.full_name}
                    </td>
                    <td className="py-2 px-3 font-mono text-[#f4aa7f] border-r border-[#9c6c4c]/20 truncate">
                      {w.email}
                    </td>
                    <td className="py-2 px-3 border-r border-[#9c6c4c]/20">
                      <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded-md text-[10px] font-mono bg-[#ec9665]/15 text-[#f4aa7f] border border-[#ec9665]/30">
                        <span>{trade?.icon || '🛠️'}</span>
                        <span>{trade?.label.split(' (')[0] || w.role}</span>
                      </span>
                    </td>
                    <td className="py-2 px-3 font-mono text-right border-r border-[#9c6c4c]/20 text-[#d8bca4]">
                      {w.active_workload_count}/{w.max_concurrent_workload}
                    </td>
                    <td className="py-2 px-3 text-right border-r border-[#9c6c4c]/20">
                      <span
                        className={`text-[9px] px-1.5 py-0.2 rounded font-mono border ${
                          w.is_available
                            ? 'bg-[#ec9665]/20 text-[#f4aa7f] border-[#ec9665]/40'
                            : 'bg-[#523624]/50 text-[#9c6c4c] border-[#9c6c4c]/30'
                        }`}
                      >
                        {w.is_available ? 'ACTIVE' : 'OFF'}
                      </span>
                    </td>
                    {isAdmin && (
                      <td className="py-2 px-3 text-right">
                        <button
                          onClick={() => handleDeleteWorker(w.id, w.full_name)}
                          className="p-1 hover:bg-rose-500/25 text-[#9c6c4c] hover:text-rose-300 rounded transition spring-interactive"
                          title="Deregister worker"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    )}
                  </tr>
                );
              })}
              {filteredWorkers.length === 0 && (
                <tr>
                  <td
                    colSpan={isAdmin ? 7 : 6}
                    className="py-16 text-center text-[#9c6c4c] text-xs font-mono"
                  >
                    {workers.length === 0
                      ? 'No maintenance workers registered yet. Use the registration panel on the right to add technicians.'
                      : 'No workers match the search query.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Right Pane: Persistent Worker Operations & Registration Command Station */}
        <div className="w-[430px] glass-drawer p-4 flex flex-col justify-between shrink-0 shadow-2xl z-10 overflow-y-auto space-y-4">
          <div className="space-y-4">
            {isAdmin ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-[#9c6c4c]/30">
                  <div className="flex items-center space-x-2">
                    <UserPlus className="w-4 h-4 text-[#ec9665]" />
                    <h2 className="text-xs font-bold text-[#f4aa7f] uppercase tracking-wider font-mono">
                      Register Maintenance Worker
                    </h2>
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded font-mono bg-[#ec9665]/15 text-[#f4aa7f] border border-[#ec9665]/30">
                    Admin Only
                  </span>
                </div>

                <form onSubmit={handleRegisterWorker} className="space-y-2.5">
                  <div>
                    <label className="block text-[11px] font-mono text-[#9c6c4c] mb-1">
                      Worker Full Name *
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Murugan P"
                      value={formName}
                      onChange={(e) => setFormName(e.target.value)}
                      className="w-full glass-input rounded-md px-2.5 py-1.5 text-xs text-[#f4aa7f] focus:outline-none font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-mono text-[#9c6c4c] mb-1">
                      Notification Email Address (Resend API) *
                    </label>
                    <input
                      type="email"
                      required
                      placeholder="e.g. murugan.plumber@easwari.edu"
                      value={formEmail}
                      onChange={(e) => setFormEmail(e.target.value)}
                      className="w-full glass-input rounded-md px-2.5 py-1.5 text-xs text-[#f4aa7f] focus:outline-none font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-mono text-[#9c6c4c] mb-1">
                      Primary Trade / Specialty *
                    </label>
                    <select
                      value={formRole}
                      onChange={(e) => setFormRole(e.target.value)}
                      className="w-full glass-input rounded-md px-2.5 py-1.5 text-xs text-[#d8bca4] focus:outline-none font-mono cursor-pointer"
                    >
                      {TRADE_ROLES.map((t) => (
                        <option key={t.value} value={t.value} className="bg-[#180f0a] text-[#d8bca4]">
                          {t.icon} {t.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="pt-1">
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="w-full py-2 bg-gradient-to-r from-[#ec9665] to-[#f4aa7f] text-[#180f0a] disabled:opacity-50 rounded-md text-xs font-bold transition spring-interactive shadow-[0_4px_16px_rgba(236,150,101,0.35)] flex items-center justify-center space-x-1.5"
                    >
                      <UserPlus className="w-3.5 h-3.5" />
                      <span>{isSubmitting ? 'Registering Worker...' : 'Register Worker'}</span>
                    </button>
                  </div>
                </form>
              </div>
            ) : (
              <div className="p-3 bg-[#180f0a]/60 rounded-lg border border-[#9c6c4c]/30 text-xs font-mono text-[#9c6c4c]">
                Viewing Worker Roster in Student/Staff read-only mode.
              </div>
            )}

            {/* Trade Specialty Readiness & Distribution Grid */}
            <div className="space-y-2">
              <span className="text-[10px] font-mono uppercase text-[#9c6c4c] tracking-wider block">
                Trade Specialty Fleet Coverage
              </span>
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                {TRADE_ROLES.map((t) => {
                  const count = workers.filter((w) => w.role === t.value).length;
                  return (
                    <div
                      key={t.value}
                      className="p-2 bg-[#180f0a]/60 rounded-lg border border-[#9c6c4c]/25 flex items-center justify-between"
                    >
                      <div className="flex items-center space-x-1.5 truncate">
                        <span>{t.icon}</span>
                        <span className="text-[11px] text-[#d8bca4] truncate">{t.value}</span>
                      </div>
                      <span className={`font-bold text-xs ${count > 0 ? 'text-[#ec9665]' : 'text-[#9c6c4c]'}`}>
                        {count} active
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Invariant Policy Notice */}
            <div className="p-2.5 bg-[#180f0a]/60 rounded-lg border border-[#9c6c4c]/25 text-[10px] font-mono text-[#d8bca4]/75 space-y-1">
              <div className="flex items-center space-x-1 text-[#f4aa7f] font-bold">
                <Shield className="w-3 h-3" />
                <span>Automated Dispatch Rules</span>
              </div>
              <div>• Groq AI multi-agent extracts trade skill</div>
              <div>• Resend API emails worker on P0/P1 emergency</div>
              <div>• Capacity invariant: max 5 active tickets / technician</div>
            </div>
          </div>

          <div className="pt-2 border-t border-[#9c6c4c]/30 text-[10px] text-[#9c6c4c] font-mono">
            Roster: {workers.length} Total Workers Registered
          </div>
        </div>
      </div>
    </div>
  );
};
