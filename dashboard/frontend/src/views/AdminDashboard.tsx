import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import {
  Activity,
  AlertTriangle,
  DoorClosed,
  Clock,
  Layers,
  Search,
  Filter,
  RefreshCw,
  HelpCircle,
  X,
  MessageSquare,
  Send,
  User,
  ShieldAlert,
  ArrowRight,
  Calendar,
  CheckCircle2,
  AlertCircle,
  Briefcase,
  Sparkles,
  XCircle,
} from 'lucide-react';

export const AdminDashboard: React.FC = () => {
  const { currentUser } = useAuth();
  const [workOrders, setWorkOrders] = useState<any[]>([]);
  const [nodes, setNodes] = useState<any[]>([]);
  const [bookings, setBookings] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [filterState, setFilterState] = useState<string>('ALL');
  const [filterCategory, setFilterCategory] = useState<string>('ALL');

  // Direct Communication with Worker Modal State
  const [commTicket, setCommTicket] = useState<any | null>(null);
  const [comments, setComments] = useState<any[]>([]);
  const [newCommentText, setNewCommentText] = useState<string>('');
  const [loadingComments, setLoadingComments] = useState<boolean>(false);
  const [submittingComment, setSubmittingComment] = useState<boolean>(false);
  const [commError, setCommError] = useState<string | null>(null);

  // Clarification Modal State
  const [clarifyingTicket, setClarifyingTicket] = useState<any | null>(null);
  const [clarifyInput, setClarifyInput] = useState<string>('');
  const [submittingClarify, setSubmittingClarify] = useState<boolean>(false);

  // Urgent Action Needed Popup State
  const [urgentPopupDismissedId, setUrgentPopupDismissedId] = useState<string | null>(null);
  const [handledBookingIds, setHandledBookingIds] = useState<Set<string>>(new Set());
  const [alternativeRooms, setAlternativeRooms] = useState<Record<string, any[]>>({});
  const [relocatingId, setRelocatingId] = useState<string | null>(null);
  const [reschedulingBooking, setReschedulingBooking] = useState<any | null>(null);
  const [rescheduleData, setRescheduleData] = useState({
    target_room_id: '',
    start_time: '',
    end_time: '',
    reason: 'Rescheduled by Admin from Operations Control Center.',
  });
  const [resolvedToast, setResolvedToast] = useState<string | null>(null);

  const fetchDatabaseStatistics = async () => {
    try {
      setLoading(true);
      const results = await Promise.allSettled([
        api.get('/work-orders?limit=1000'),
        api.get('/campus/nodes'),
        api.get('/bookings'),
      ]);

      const [woRes, nodesRes, bookingsRes] = results;

      if (woRes.status === 'fulfilled' && Array.isArray(woRes.value)) {
        setWorkOrders(woRes.value);
      }
      if (nodesRes.status === 'fulfilled' && Array.isArray(nodesRes.value)) {
        setNodes(nodesRes.value);
      }
      if (bookingsRes.status === 'fulfilled' && Array.isArray(bookingsRes.value)) {
        setBookings(bookingsRes.value);
      }
    } catch (err) {
      console.error('Failed to load database stats', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDatabaseStatistics();
    const interval = setInterval(fetchDatabaseStatistics, 10000);
    return () => clearInterval(interval);
  }, []);

  // Compute metrics from actual database records
  const totalTickets = workOrders.length;
  const activeTickets = workOrders.filter(
    (w) => w.state !== 'RESOLVED' && w.state !== 'CLOSED' && w.state !== 'MERGED_DUPLICATE'
  );
  const activeTicketsCount = activeTickets.length;
  const resolvedTicketsCount = workOrders.filter(
    (w) => w.state === 'RESOLVED' || w.state === 'CLOSED'
  ).length;

  const criticalCount = activeTickets.filter(
    (w) => w.calculated_priority === 'P0_CRITICAL' || w.calculated_priority === 'P1_HIGH'
  ).length;

  const activeRoomNodeIds = new Set(activeTickets.map((w) => w.target_node_id).filter(Boolean));
  const activeRoomCodes = new Set(activeTickets.map((w) => w.node_code).filter(Boolean));

  const nonOperationalRooms = nodes.filter(
    (n) => n.node_type === 'ROOM' && (!n.is_operational || activeRoomNodeIds.has(n.id) || activeRoomCodes.has(n.node_code))
  ).length;

  const totalRooms = nodes.filter((n) => n.node_type === 'ROOM').length || 32;

  // Real category counts from actual database records
  const categoryCounts: Record<string, number> = {};
  workOrders.forEach((w) => {
    const cat = w.category || 'GENERAL';
    categoryCounts[cat] = (categoryCounts[cat] || 0) + 1;
  });

  // Real status counts from actual database records
  const statusCounts: Record<string, number> = {};
  workOrders.forEach((w) => {
    const st = w.state || 'UNKNOWN';
    statusCounts[st] = (statusCounts[st] || 0) + 1;
  });

  // Fetch comments when comm modal opens
  const openCommModal = async (ticket: any) => {
    setCommTicket(ticket);
    setCommError(null);
    setNewCommentText('');
    try {
      setLoadingComments(true);
      const res: any = await api.get(`/work-orders/${ticket.id}/comments`);
      setComments(Array.isArray(res) ? res : []);
    } catch (err: any) {
      console.error('Failed to load comments:', err);
      setComments([]);
    } finally {
      setLoadingComments(false);
    }
  };

  const handleSendComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCommentText.trim() || !commTicket) return;
    try {
      setSubmittingComment(true);
      setCommError(null);
      const res: any = await api.post(`/work-orders/${commTicket.id}/comments`, {
        message: newCommentText.trim(),
      });
      setComments((prev) => [...prev, res]);
      setNewCommentText('');
      await fetchDatabaseStatistics();
    } catch (err: any) {
      setCommError(err?.message || 'Failed to send comment to worker');
    } finally {
      setSubmittingComment(false);
    }
  };

  // Submit clarification
  const handleClarifySubmit = async (text: string) => {
    if (!clarifyingTicket) return;
    try {
      setSubmittingClarify(true);
      const threadId = clarifyingTicket.conversation_thread_id;
      await api.post(`/intake/${threadId}/clarify`, {
        reply_text: text,
      });
      setClarifyingTicket(null);
      await fetchDatabaseStatistics();
    } catch (err: any) {
      alert(`Clarification failed: ${err.message || 'Error'}`);
    } finally {
      setSubmittingClarify(false);
    }
  };

  // STRICT REQUIREMENT: Only show currently unresolved issues under the Live Database Stats page
  const unresolvedTickets = workOrders.filter(
    (w) => w.state !== 'RESOLVED' && w.state !== 'CLOSED' && w.state !== 'MERGED_DUPLICATE'
  );

  const filteredUnresolvedTickets = unresolvedTickets.filter((w) => {
    const matchesSearch =
      (w.node_code && w.node_code.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (w.raw_description && w.raw_description.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (w.ticket_number && w.ticket_number.toString().includes(searchQuery)) ||
      (w.assigned_tech_name && w.assigned_tech_name.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesState = filterState === 'ALL' || w.state === filterState;
    const matchesCategory = filterCategory === 'ALL' || w.category === filterCategory;
    return matchesSearch && matchesState && matchesCategory;
  });

  // Count unread / pending worker messages
  const newWorkerUpdatesCount = unresolvedTickets.filter(
    (w) => w.latest_comment_author_role === 'TECHNICIAN'
  ).length;

  // URGENT ACTION POPUP LOGIC:
  // Detects active disruptions in scheduled classes:
  // 1) Student reports a problem in a classroom with a class scheduled in the next 3 hours
  // 2) Impending class scheduled within the next 3 hours in a classroom where an unresolved report was raised earlier
  // Automatically clears when:
  // - Admin relocates the booking (by AI suggestion or manual room)
  // - Admin reschedules the booking
  // - Admin suspends the class
  // - Worker marks the work order RESOLVED or CLOSED
  const activeImpactedBookings = bookings.filter((b) => {
    // If already handled by admin in this session, do not show popup
    if (handledBookingIds.has(b.id)) {
      return false;
    }

    // If already moved, suspended, or cancelled, no action needed
    if (b.status === 'RELOCATED' || b.status === 'SUSPENDED' || b.status === 'CANCELLED') {
      return false;
    }

    // If this booking is the result of a successful relocation into a safe room, it's not disrupted
    if (b.compromise_explanation && b.compromise_explanation.startsWith('Relocated from')) {
      return false;
    }

    // Check if there is an unresolved work order in THIS classroom (physical location)
    const unresolvedWo = workOrders.find(
      (w) =>
        w.target_node_id === b.room_node_id &&
        w.state !== 'RESOLVED' &&
        w.state !== 'CLOSED' &&
        w.state !== 'MERGED_DUPLICATE'
    );

    if (!unresolvedWo) {
      return false; // Worker solved the issue or no issue in this room!
    }

    // If the work order records that this class disruption was already handled (relocated/suspended/rescheduled), skip
    const dcStatus = unresolvedWo.partial_slots?.disrupted_class?.status;
    if (dcStatus === 'RELOCATED' || dcStatus === 'SUSPENDED' || dcStatus === 'RESCHEDULED') {
      return false;
    }

    // Trigger 1: Explicitly marked IMPACTED_NEEDS_MOVE by intake or backend conflict check
    if (b.status === 'IMPACTED_NEEDS_MOVE') {
      return true;
    }

    // Trigger 2: Class scheduled within the next 3 hours (or active now) with an unresolved report in this room
    if (b.start_time && b.end_time) {
      const now = new Date();
      const inThreeHours = new Date(now.getTime() + 3 * 60 * 60 * 1000);
      const start = new Date(b.start_time);
      const end = new Date(b.end_time);

      if (start <= inThreeHours && end >= new Date(now.getTime() - 30 * 60 * 1000)) {
        return true;
      }
    }

    return false;
  });

  const urgentDisruptedBooking = activeImpactedBookings.length > 0 ? activeImpactedBookings[0] : null;
  const urgentLinkedWo = urgentDisruptedBooking
    ? workOrders.find(
        (w) =>
          w.id === urgentDisruptedBooking.linked_work_order_id ||
          w.target_node_id === urgentDisruptedBooking.room_node_id
      )
    : null;

  // Fetch AI recommended alternatives when an urgent disruption is active
  useEffect(() => {
    if (urgentDisruptedBooking && !alternativeRooms[urgentDisruptedBooking.id]) {
      api
        .get(
          `/rooms/alternatives?current_room_id=${urgentDisruptedBooking.room_node_id}&student_count=${urgentDisruptedBooking.student_count}&start_time=${urgentDisruptedBooking.start_time}&end_time=${urgentDisruptedBooking.end_time}`
        )
        .then((alts: any) => {
          if (Array.isArray(alts)) {
            setAlternativeRooms((prev) => ({ ...prev, [urgentDisruptedBooking.id]: alts }));
          }
        })
        .catch(console.error);
    }
  }, [urgentDisruptedBooking?.id]);

  const urgentAlternatives = urgentDisruptedBooking
    ? alternativeRooms[urgentDisruptedBooking.id] || []
    : [];
  const urgentBestAlt = urgentAlternatives.length > 0 ? urgentAlternatives[0] : null;

  // Urgent Actions:
  const handleUrgentRelocate = async (booking: any, targetRoomId: string) => {
    try {
      setRelocatingId(booking.id);
      // Immediately mark as handled and close popup to prevent repetitive/duplicate clicks
      setHandledBookingIds((prev) => new Set([...prev, booking.id]));
      setUrgentPopupDismissedId(booking.id);

      await api.post(`/bookings/${booking.id}/relocate`, {
        target_room_id: targetRoomId,
        reason: 'Urgent AI Relocation Approved by Admin from Live Stats Center.',
      });
      setResolvedToast(
        `Class relocated successfully to ${urgentBestAlt?.room_code || 'new room'}! Scheduled session protected.`
      );
      setTimeout(() => setResolvedToast(null), 6000);
      await fetchDatabaseStatistics();
    } catch (err: any) {
      alert(`Relocation failed: ${err.message || 'Error'}`);
    } finally {
      setRelocatingId(null);
    }
  };

  const handleUrgentSuspend = async (booking: any) => {
    if (!window.confirm(`Are you sure you want to suspend "${booking.course_or_event_title}"?`)) return;
    try {
      setRelocatingId(booking.id);
      // Immediately mark as handled and close popup
      setHandledBookingIds((prev) => new Set([...prev, booking.id]));
      setUrgentPopupDismissedId(booking.id);

      await api.post(`/bookings/${booking.id}/suspend`, {});
      setResolvedToast(`Class "${booking.course_or_event_title}" suspended due to room repairs.`);
      setTimeout(() => setResolvedToast(null), 6000);
      await fetchDatabaseStatistics();
    } catch (err: any) {
      alert(`Suspend failed: ${err.message || 'Error'}`);
    } finally {
      setRelocatingId(null);
    }
  };

  const handleOpenUrgentReschedule = (booking: any) => {
    setReschedulingBooking(booking);
    setRescheduleData({
      target_room_id: booking.room_node_id,
      start_time: new Date(booking.start_time).toISOString().slice(0, 16),
      end_time: new Date(booking.end_time).toISOString().slice(0, 16),
      reason: 'Rescheduled by Admin from Operations Control Center.',
    });
  };

  const handleUrgentRescheduleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reschedulingBooking) return;
    const bId = reschedulingBooking.id;
    try {
      // Immediately mark as handled and close popup
      setHandledBookingIds((prev) => new Set([...prev, bId]));
      setUrgentPopupDismissedId(bId);
      setReschedulingBooking(null);

      await api.post(`/bookings/${bId}/reschedule`, {
        target_room_id: rescheduleData.target_room_id,
        start_time: new Date(rescheduleData.start_time).toISOString(),
        end_time: new Date(rescheduleData.end_time).toISOString(),
        reason: rescheduleData.reason,
      });
      setResolvedToast('Class rescheduled successfully to new window.');
      setTimeout(() => setResolvedToast(null), 6000);
      await fetchDatabaseStatistics();
    } catch (err: any) {
      alert(`Reschedule failed: ${err.message || 'Error'}`);
    }
  };

  return (
    <div className="h-full w-full overflow-y-auto bg-slate-950 text-slate-100 p-6 space-y-6 pb-24">
      {/* Toast Notification Banner */}
      {resolvedToast && (
        <div className="p-4 rounded-xl bg-emerald-950/80 border border-emerald-500/50 text-emerald-200 text-xs font-mono flex items-center justify-between shadow-lg animate-in fade-in duration-200">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            <span>{resolvedToast}</span>
          </div>
          <button onClick={() => setResolvedToast(null)} className="text-emerald-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800 gap-4">
        <div>
          <div className="flex items-center space-x-2 text-indigo-400 text-xs font-semibold uppercase tracking-wider mb-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>Campus Operations Engine • Live Database Analytics</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Campus Operations Control Center
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real metrics computed directly from PostgreSQL tables and invariant kernels.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Notification Indicator: Worker Message Updates */}
          {newWorkerUpdatesCount > 0 && (
            <div className="flex items-center gap-2 bg-indigo-500/15 border border-indigo-500/40 px-3 py-1.5 rounded-lg text-xs font-mono text-indigo-300 font-semibold shadow-sm">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-indigo-500"></span>
              </span>
              <MessageSquare className="w-3.5 h-3.5 text-indigo-400" />
              <span>
                {newWorkerUpdatesCount} Worker Update{newWorkerUpdatesCount > 1 ? 's' : ''} Pending
              </span>
            </div>
          )}

          <span className="text-xs font-mono text-slate-400">
            Last Synced: {new Date().toLocaleTimeString()}
          </span>
          <button
            onClick={fetchDatabaseStatistics}
            className="p-2 rounded-lg bg-slate-900 border border-slate-700 hover:bg-slate-800 text-slate-200 transition"
            title="Refresh database records"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Minimized Urgent Alert Banner if dismissed */}
      {urgentDisruptedBooking && urgentPopupDismissedId === urgentDisruptedBooking.id && (
        <div className="p-3.5 rounded-xl bg-rose-500/15 border-2 border-rose-500/50 text-rose-200 text-xs flex items-center justify-between shadow-lg animate-pulse">
          <div className="flex items-center gap-2.5">
            <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0" />
            <div>
              <strong className="text-white font-bold">URGENT ACTION NEEDED:</strong> Scheduled Class{' '}
              <span className="text-rose-300 font-semibold">
                "{urgentDisruptedBooking.course_or_event_title}"
              </span>{' '}
              compromised in <strong className="text-amber-300">{urgentDisruptedBooking.room_code}</strong>.
            </div>
          </div>
          <button
            onClick={() => setUrgentPopupDismissedId(null)}
            className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs shadow transition"
          >
            Review & Resolve Disruption
          </button>
        </div>
      )}

      {/* Key Metric Indicators: High/Critical Alerts & Classrooms Down */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Critical / High Priority */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">High / Critical Alerts</span>
            <AlertTriangle className="w-4 h-4 text-rose-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span
              className={`text-2xl font-bold font-mono ${
                criticalCount > 0 ? 'text-rose-400' : 'text-slate-200'
              }`}
            >
              {criticalCount}
            </span>
            <span className="text-xs text-slate-500 font-mono">P0/P1 tier</span>
          </div>
          <div className="mt-1 text-[11px] text-slate-400">
            {criticalCount > 0 ? 'Requires immediate action' : 'Zero critical escalations'}
          </div>
        </div>

        {/* Out of Order Rooms */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-md">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Classrooms Down / Impacted</span>
            <DoorClosed className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span
              className={`text-2xl font-bold font-mono ${
                nonOperationalRooms > 0 ? 'text-amber-400' : 'text-slate-200'
              }`}
            >
              {nonOperationalRooms}
            </span>
            <span className="text-xs text-slate-500 font-mono">/ {totalRooms} rooms</span>
          </div>
          <div className="mt-1 text-[11px] text-slate-400">
            {totalRooms - nonOperationalRooms} operational rooms
          </div>
        </div>
      </div>

      {/* Real Problems Incident Table - STRICTLY UNRESOLVED TICKETS ONLY */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        {/* Table Filter Bar */}
        <div className="p-4 border-b border-slate-800 bg-slate-900/90 flex flex-col md:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-3 w-full md:w-auto">
            <div className="flex items-center gap-2 flex-1 md:w-72 bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 focus-within:border-indigo-500">
              <Search className="w-4 h-4 text-slate-400 shrink-0" />
              <input
                type="text"
                placeholder="Search ticket #, room, worker, description..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-transparent text-xs text-slate-100 placeholder-slate-500 w-full focus:outline-none"
              />
            </div>
            <span className="text-[11px] font-mono text-slate-400 bg-slate-950 px-2.5 py-1 rounded-md border border-slate-800 whitespace-nowrap">
              {filteredUnresolvedTickets.length} unresolved active issues
            </span>
          </div>

          <div className="flex items-center gap-2 w-full md:w-auto justify-end">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={filterState}
              onChange={(e) => setFilterState(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="ALL">All Active States</option>
              <option value="TRIAGED">TRIAGED</option>
              <option value="ASSIGNED">ASSIGNED</option>
              <option value="IN_PROGRESS">IN_PROGRESS</option>
              <option value="BLOCKED_PARTS">BLOCKED_PARTS</option>
              <option value="AWAITING_CLARIFICATION">AWAITING_CLARIFICATION</option>
            </select>

            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="ALL">All Categories</option>
              <option value="ELECTRICAL">ELECTRICAL</option>
              <option value="PLUMBING">PLUMBING</option>
              <option value="NETWORK">NETWORK</option>
              <option value="STRUCTURAL_SAFETY">STRUCTURAL_SAFETY</option>
              <option value="SOS">SOS (Medical & Emergency)</option>
              <option value="SWEEPER">SWEEPER (Cleaning & Sanitation)</option>
            </select>
          </div>
        </div>

        {/* Table - FSM Actions Removed, Direct Worker Communication Added */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 font-mono text-[11px] uppercase tracking-wider sticky top-0 z-10">
              <tr>
                <th className="py-3 px-4">Ticket</th>
                <th className="py-3 px-4">Location</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4">Priority</th>
                <th className="py-3 px-4">Assigned Worker</th>
                <th className="py-3 px-4">Current State</th>
                <th className="py-3 px-4">Description</th>
                <th className="py-3 px-4 text-right">Direct Worker Comm</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {filteredUnresolvedTickets.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-500 font-mono text-xs">
                    No active unresolved tickets match the current filter.
                  </td>
                </tr>
              ) : (
                filteredUnresolvedTickets.map((t) => {
                  const hasDisruptedClass = Boolean(t.partial_slots?.disrupted_class);
                  const hasWorkerUpdate = t.latest_comment_author_role === 'TECHNICIAN';

                  return (
                    <tr key={t.id} className="hover:bg-slate-800/40 transition">
                      <td className="py-3 px-4 font-mono font-bold text-indigo-400">
                        #{t.ticket_number}
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-200">
                        <div>{t.node_code || 'General'}</div>
                        {hasDisruptedClass && (
                          <span className="inline-block mt-0.5 text-[9px] font-mono px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 font-bold">
                            CLASS IMPACTED
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-slate-300 font-medium">
                        {t.category || 'TBD'}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono border ${
                            t.calculated_priority === 'P0_CRITICAL'
                              ? 'bg-rose-500/10 text-rose-400 border-rose-500/30 font-bold'
                              : t.calculated_priority === 'P1_HIGH'
                              ? 'bg-amber-500/10 text-amber-400 border-amber-500/30 font-bold'
                              : 'bg-slate-800 text-slate-300 border-slate-700'
                          }`}
                        >
                          {t.calculated_priority || 'P2'}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-300">
                        {t.assigned_tech_name ? (
                          <div className="flex items-center gap-1.5">
                            <Briefcase className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                            <span className="truncate max-w-[130px] font-semibold text-slate-200">
                              {t.assigned_tech_name}
                            </span>
                          </div>
                        ) : (
                          <span className="text-slate-500 italic">Auto-Dispatching...</span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-950 text-slate-200 border border-slate-800">
                          {t.state}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-400 max-w-xs">
                        <div className="truncate">{t.ai_summary || t.raw_description}</div>
                        {/* Worker Notification snippet if latest message from worker */}
                        {hasWorkerUpdate && t.latest_comment_message && (
                          <div className="mt-1 flex items-center gap-1.5 text-[10px] text-emerald-300 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/60 font-mono">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping shrink-0" />
                            <span className="font-bold text-emerald-200 shrink-0">Worker Update:</span>
                            <span className="truncate">"{t.latest_comment_message}"</span>
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {t.state === 'AWAITING_CLARIFICATION' && (
                            <button
                              onClick={() => {
                                setClarifyingTicket(t);
                                setClarifyInput('');
                              }}
                              className="px-2.5 py-1 rounded bg-amber-600/80 hover:bg-amber-600 text-white font-medium text-[11px] transition shadow-sm inline-flex items-center gap-1"
                            >
                              <HelpCircle className="w-3 h-3" />
                              <span>Clarify</span>
                            </button>
                          )}
                          <button
                            onClick={() => openCommModal(t)}
                            className={`px-2.5 py-1 rounded text-white font-semibold text-[11px] transition shadow-sm inline-flex items-center gap-1.5 ${
                              hasWorkerUpdate
                                ? 'bg-indigo-600 hover:bg-indigo-500 ring-2 ring-indigo-400/50'
                                : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700'
                            }`}
                            title="Communicate directly with the assigned worker"
                          >
                            <MessageSquare className="w-3.5 h-3.5 text-indigo-300" />
                            <span>Communicate {t.comments_count > 0 ? `(${t.comments_count})` : ''}</span>
                            {hasWorkerUpdate && (
                              <span className="px-1.5 py-0.2 rounded-full bg-emerald-400 text-slate-950 font-bold text-[9px] animate-pulse">
                                New
                              </span>
                            )}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        <div className="p-3 bg-slate-950/80 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400 font-mono">
          <span>Showing only active unresolved issues on Live Stats page. Complete incident history is available in Work Orders.</span>
          <span className="text-emerald-400 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Live Database Synced
          </span>
        </div>
      </div>

      {/* URGENT ACTION NEEDED POPUP MODAL (Automatically closes once resolved/relocated/suspended/fixed) */}
      {urgentDisruptedBooking && urgentPopupDismissedId !== urgentDisruptedBooking.id && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-slate-900 border-2 border-rose-500/70 rounded-2xl max-w-2xl w-full p-6 shadow-[0_0_50px_rgba(244,63,94,0.35)] space-y-5">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-rose-500/30 pb-3">
              <div className="flex items-center space-x-3">
                <div className="p-2.5 bg-rose-500/20 text-rose-400 rounded-xl border border-rose-500/40">
                  <ShieldAlert className="w-6 h-6 animate-pulse text-rose-400" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-bold text-white tracking-tight">
                      🚨 CRITICAL ACTION REQUIRED
                    </h3>
                    <span className="px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 text-[10px] font-mono border border-rose-500/40 font-bold">
                      Class Scheduled within 3 Hours
                    </span>
                  </div>
                  <p className="text-xs text-rose-200/80 mt-0.5">
                    Unresolved maintenance issue conflicts with an upcoming scheduled class. Admin decision required:
                  </p>
                </div>
              </div>

              <button
                onClick={() => {
                  setHandledBookingIds((prev) => new Set([...prev, urgentDisruptedBooking.id]));
                  setUrgentPopupDismissedId(urgentDisruptedBooking.id);
                }}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
                title="Dismiss popup"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Disrupted Class & Incident Info */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1">
                <span className="text-[10px] uppercase font-mono text-slate-400 font-bold">
                  Disrupted Academic Session
                </span>
                <div className="font-bold text-white text-sm">
                  {urgentDisruptedBooking.course_or_event_title}
                </div>
                <div className="text-slate-300">
                  Room: <strong className="text-amber-300">{urgentDisruptedBooking.room_code}</strong> •{' '}
                  <span className="font-semibold">{urgentDisruptedBooking.student_count} Students</span>
                </div>
                <div className="text-[11px] font-mono text-slate-400">
                  Window:{' '}
                  {new Date(urgentDisruptedBooking.start_time).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}{' '}
                  -{' '}
                  {new Date(urgentDisruptedBooking.end_time).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </div>
              </div>

              <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1">
                <span className="text-[10px] uppercase font-mono text-slate-400 font-bold">
                  Active Facility Incident
                </span>
                <div className="font-bold text-rose-400 truncate">
                  {urgentLinkedWo ? `Ticket #${urgentLinkedWo.ticket_number}` : 'Operational Breakdown'}
                </div>
                <p className="text-slate-300 truncate">
                  {urgentLinkedWo?.raw_description || 'Active power or facility interruption.'}
                </p>
                <div className="text-[11px] font-mono text-slate-400">
                  Assigned:{' '}
                  <strong className="text-slate-200">
                    {urgentLinkedWo?.assigned_tech_name || 'Technician Auto-Dispatched'}
                  </strong>{' '}
                  ({urgentLinkedWo?.state || 'ASSIGNED'})
                </div>
              </div>
            </div>

            {/* AI CSP Alternative Room Recommendation */}
            <div className="bg-slate-950 border border-indigo-500/40 rounded-xl p-3.5 text-xs space-y-1.5 shadow-inner">
              <div className="flex items-center space-x-2 text-indigo-400 font-mono font-semibold">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                <span>AI CSP Constraint Solver Optimization:</span>
              </div>
              {urgentBestAlt ? (
                <div className="text-slate-300 space-y-1">
                  <div className="flex flex-wrap items-center gap-2 font-mono">
                    <span className="text-emerald-400 font-bold text-sm">{urgentBestAlt.room_code}</span>
                    <span className="text-slate-400">({urgentBestAlt.room_name})</span>
                    <span className="text-slate-500">•</span>
                    <span>Cap: {urgentBestAlt.room_capacity} seats</span>
                    <span className="text-slate-500">•</span>
                    <span className="text-emerald-300 font-bold">0 Collisions</span>
                  </div>
                  <p className="text-[11px] text-slate-400">{urgentBestAlt.explanation}</p>
                </div>
              ) : (
                <p className="text-slate-400 italic">
                  Searching for available free rooms during this window...
                </p>
              )}
            </div>

            {/* 4 Action Buttons */}
            <div className="pt-2 flex flex-wrap items-center justify-between gap-2.5">
              <div className="flex items-center gap-2">
                {urgentLinkedWo && (
                  <button
                    onClick={() => {
                      setUrgentPopupDismissedId(urgentDisruptedBooking.id);
                      openCommModal(urgentLinkedWo);
                    }}
                    className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold border border-slate-700 transition flex items-center space-x-1.5"
                  >
                    <MessageSquare className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Communicate with Worker</span>
                  </button>
                )}
              </div>

              <div className="flex items-center gap-2">
                {urgentBestAlt && (
                  <button
                    disabled={relocatingId === urgentDisruptedBooking.id}
                    onClick={() => handleUrgentRelocate(urgentDisruptedBooking, urgentBestAlt.room_id)}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold font-mono transition flex items-center space-x-1.5 shadow-lg shadow-emerald-950/50 disabled:opacity-50"
                  >
                    <Sparkles className="w-4 h-4 text-emerald-200" />
                    <span>Approve AI Relocation ({urgentBestAlt.room_code})</span>
                  </button>
                )}
                <button
                  disabled={relocatingId === urgentDisruptedBooking.id}
                  onClick={() => handleOpenUrgentReschedule(urgentDisruptedBooking)}
                  className="px-3.5 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-bold font-mono transition flex items-center space-x-1.5 shadow disabled:opacity-50"
                >
                  <Calendar className="w-3.5 h-3.5 text-amber-200" />
                  <span>Reschedule</span>
                </button>
                <button
                  disabled={relocatingId === urgentDisruptedBooking.id}
                  onClick={() => handleUrgentSuspend(urgentDisruptedBooking)}
                  className="px-3.5 py-2 bg-rose-700 hover:bg-rose-600 text-white rounded-lg text-xs font-bold font-mono transition flex items-center space-x-1.5 shadow disabled:opacity-50"
                >
                  <XCircle className="w-3.5 h-3.5 text-rose-200" />
                  <span>Suspend Class</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: Reschedule Class */}
      {reschedulingBooking && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden animate-in fade-in duration-200">
            <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
              <div className="flex items-center space-x-2.5">
                <div className="p-2 bg-amber-500/20 text-amber-400 rounded-lg border border-amber-500/30">
                  <Calendar className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-white text-base">Reschedule Scheduled Class</h3>
                  <p className="text-xs text-slate-400">
                    {reschedulingBooking.course_or_event_title} ({reschedulingBooking.student_count} students)
                  </p>
                </div>
              </div>
              <button
                onClick={() => setReschedulingBooking(null)}
                className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUrgentRescheduleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">
                  Target Classroom *
                </label>
                <select
                  required
                  value={rescheduleData.target_room_id}
                  onChange={(e) => setRescheduleData({ ...rescheduleData, target_room_id: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                >
                  {nodes
                    .filter((n) => n.node_type === 'ROOM')
                    .map((r) => (
                      <option key={r.id} value={r.id} className="bg-slate-900 text-slate-200">
                        {r.node_code} - {r.name} (Cap: {r.room_capacity}, {r.building_code})
                      </option>
                    ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">
                    New Start Time *
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={rescheduleData.start_time}
                    onChange={(e) => setRescheduleData({ ...rescheduleData, start_time: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">
                    New End Time *
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={rescheduleData.end_time}
                    onChange={(e) => setRescheduleData({ ...rescheduleData, end_time: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">
                  Rescheduling Reason / Justification
                </label>
                <input
                  type="text"
                  value={rescheduleData.reason}
                  onChange={(e) => setRescheduleData({ ...rescheduleData, reason: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="pt-3 border-t border-slate-800 flex items-center justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setReschedulingBooking(null)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-amber-600 hover:bg-amber-500 text-white font-bold rounded-lg text-xs shadow-lg transition"
                >
                  Confirm Reschedule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Direct Worker Communication Slide-over / Modal */}
      {commTicket && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-xl w-full flex flex-col max-h-[85vh] shadow-2xl overflow-hidden animate-in fade-in duration-200">
            {/* Modal Header */}
            <div className="p-4 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-indigo-400 bg-indigo-950/80 px-2 py-0.5 rounded border border-indigo-800/60">
                    Ticket #{commTicket.ticket_number}
                  </span>
                  <span className="text-sm font-bold text-white">Direct Worker Communication</span>
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  Worker: <strong className="text-amber-300">{commTicket.assigned_tech_name || 'Assigned Technician'}</strong> • Room: <strong className="text-slate-200">{commTicket.node_code || 'Campus'}</strong>
                </p>
              </div>
              <button
                onClick={() => setCommTicket(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Scheduled Class Alert if present */}
            {commTicket.partial_slots?.disrupted_class && (
              <div className="p-3 bg-rose-500/15 border-b border-rose-500/30 text-xs text-rose-200 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0" />
                <span>
                  <strong>Urgent:</strong> Class <em>{commTicket.partial_slots.disrupted_class.course_title}</em> is impacted in this room. Prioritize repairs.
                </span>
              </div>
            )}

            {/* Comment Thread List */}
            <div className="p-4 overflow-y-auto flex-1 space-y-3 bg-slate-950/40 min-h-[220px]">
              {loadingComments ? (
                <div className="flex items-center justify-center py-12 text-xs text-slate-400 font-mono">
                  <RefreshCw className="w-4 h-4 animate-spin mr-2" />
                  Loading discussion thread...
                </div>
              ) : comments.length === 0 ? (
                <div className="text-center py-12 text-xs text-slate-500 font-mono">
                  No comments yet. Send a message to coordinate with {commTicket.assigned_tech_name || 'the worker'}.
                </div>
              ) : (
                comments.map((c: any) => {
                  const isTech = c.author_role === 'TECHNICIAN';
                  const isSys = c.author_role === 'SYS_ADMIN' || c.author_role === 'FACILITIES_ADMIN';
                  return (
                    <div
                      key={c.id}
                      className={`flex flex-col ${isTech ? 'items-start' : 'items-end'}`}
                    >
                      <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-400 mb-1">
                        <span className="font-semibold text-slate-300">{c.author_name}</span>
                        <span className="text-slate-500">({c.author_role})</span>
                        <span className="text-slate-600">•</span>
                        <span>{new Date(c.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                      <div
                        className={`p-3 rounded-2xl max-w-[85%] text-xs leading-relaxed ${
                          isTech
                            ? 'bg-amber-950/40 text-amber-100 border border-amber-800/40 rounded-tl-sm'
                            : 'bg-indigo-600 text-white rounded-tr-sm shadow-md'
                        }`}
                      >
                        {c.message}
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Send Comment Input */}
            <form onSubmit={handleSendComment} className="p-3 border-t border-slate-800 bg-slate-950 flex items-center gap-2">
              <input
                type="text"
                placeholder={`Message ${commTicket.assigned_tech_name || 'technician'} regarding this issue...`}
                value={newCommentText}
                onChange={(e) => setNewCommentText(e.target.value)}
                className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
              />
              <button
                type="submit"
                disabled={submittingComment || !newCommentText.trim()}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition shadow"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{submittingComment ? 'Sending...' : 'Send'}</span>
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Clarification Modal */}
      {clarifyingTicket && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <HelpCircle className="w-5 h-5 text-amber-400" />
                <h3 className="font-bold text-white text-base">
                  Clarify Ticket #{clarifyingTicket.ticket_number}
                </h3>
              </div>
              <button
                onClick={() => setClarifyingTicket(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3">
              <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-xs text-amber-300">
                <span className="font-bold">Pending Question: </span>
                {clarifyingTicket.clarification_question ||
                  'Please specify the exact room or location to proceed.'}
              </div>

              <p className="text-xs text-slate-400">
                Original report: "{clarifyingTicket.raw_description}"
              </p>

              <div>
                <label className="block text-xs font-mono text-slate-300 mb-1">
                  Clarification Reply (e.g. "RM-FC-101" or "Plumbing")
                </label>
                <input
                  type="text"
                  value={clarifyInput}
                  onChange={(e) => setClarifyInput(e.target.value)}
                  placeholder="e.g. RM-FC-101"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500"
                />
              </div>
            </div>

            <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setClarifyingTicket(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded-lg transition"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={submittingClarify || !clarifyInput.trim()}
                onClick={() => handleClarifySubmit(clarifyInput.trim())}
                className="px-4 py-2 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white font-bold text-xs rounded-lg transition"
              >
                {submittingClarify ? 'Resolving...' : 'Submit Clarification'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
