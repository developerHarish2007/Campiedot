import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import {
  DoorOpen,
  Plus,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Building2,
  Users,
  Layers,
  Sparkles,
  Trash2,
  RefreshCw,
  X,
  Calendar,
  Clock,
  Wrench,
  BookOpen,
  AlertTriangle,
  ArrowRight,
} from 'lucide-react';

interface Room {
  id: string;
  node_code: string;
  name: string;
  building_code: string;
  floor_number: number;
  room_capacity: number;
  room_type: string;
  room_features: string[];
  is_operational: boolean;
  criticality_weight: number;
}

interface Booking {
  id: string;
  room_node_id: string;
  room_code?: string;
  room_name?: string;
  building_code?: string;
  booking_type: string;
  course_or_event_title: string;
  student_count: number;
  start_time: string;
  end_time: string;
  status: string;
  linked_work_order_id?: string;
  relocated_to_booking_id?: string;
  relocated_to_room_code?: string;
  relocated_to_room_name?: string;
  compromise_explanation?: string;
}

interface RoomAlternative {
  room_id: string;
  room_code: string;
  room_name: string;
  building_code: string;
  floor_number: number;
  room_capacity: number;
  room_features: string[];
  penalty_score: number;
  is_same_building: boolean;
  floor_delta: number;
  wasted_seats: number;
  explanation: string;
}

const AVAILABLE_BLOCKS = [
  { code: 'EEC-MAIN', name: 'Main Administrative Block' },
  { code: 'EEC-ACAD', name: 'Academic Tech Block (CSE/IT/AI&DS)' },
  { code: 'EEC-MECH-PG', name: 'Mechanical, Civil & Central PG Library' },
  { code: 'EEC-ROBOTICS', name: 'ABB Robotics Research & Automation' },
  { code: 'EEC-AUD-FC', name: 'TRP Auditorium & Food Court' },
];

const ROOM_TYPES = [
  { value: 'CLASSROOM', label: 'Classroom / Lecture Hall', color: 'bg-[#ec9665]/20 text-[#f4aa7f] border-[#ec9665]/40' },
  { value: 'LAB', label: 'Laboratory / Research Facility', color: 'bg-[#9c6c4c]/30 text-[#d8bca4] border-[#9c6c4c]/50' },
  { value: 'ADMINISTRATIVE', label: 'Administrative Office / Block', color: 'bg-purple-500/20 text-purple-300 border-purple-500/40' },
  { value: 'AUDITORIUM', label: 'Auditorium / Amphitheatre', color: 'bg-blue-500/20 text-blue-300 border-blue-500/40' },
  { value: 'FOOD_COURT', label: 'Food Court & Dining', color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' },
  { value: 'SEMINAR_HALL', label: 'Seminar Hall / Boardroom', color: 'bg-[#523624]/60 text-[#d8bca4] border-[#9c6c4c]/40' },
  { value: 'WORKSHOP', label: 'Workshop / Fabrication Bay', color: 'bg-[#f4aa7f]/20 text-[#f4aa7f] border-[#f4aa7f]/40' },
];

const FEATURE_OPTIONS = [
  'PROJECTOR',
  'AC',
  'COMPUTERS',
  'AUDIO_SYSTEM',
  'SMART_BOARD',
  'WIFI_AP',
  'RAMP_ACCESS',
  '3_PHASE_POWER',
];

const getNowPlusHours = (hours: number) => {
  const d = new Date();
  d.setHours(d.getHours() + hours);
  d.setMinutes(0);
  d.setSeconds(0);
  const offset = d.getTimezoneOffset() * 60000;
  return new Date(d.getTime() - offset).toISOString().slice(0, 16);
};

export const RoomManagementView: React.FC = () => {
  const { currentUser } = useAuth();
  const isAdmin = currentUser.role === 'SYS_ADMIN' || currentUser.role === 'FACILITIES_ADMIN';
  const [rooms, setRooms] = useState<Room[]>([]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedBlock, setSelectedBlock] = useState<string>('ALL');
  const [selectedType, setSelectedType] = useState<string>('ALL');

  // AI Disrupted Classes & Alternatives State
  const [alternativeRecommendations, setAlternativeRecommendations] = useState<Record<string, RoomAlternative[]>>({});
  const [relocatingId, setRelocatingId] = useState<string | null>(null);

  // Reschedule Modal State
  const [reschedulingBooking, setReschedulingBooking] = useState<Booking | null>(null);
  const [rescheduleFormData, setRescheduleFormData] = useState({
    target_room_id: '',
    start_time: '',
    end_time: '',
    reason: 'Class rescheduled by Admin due to facility operational requirements.',
  });
  const [submittingReschedule, setSubmittingReschedule] = useState<boolean>(false);

  // Modals state
  const [isRoomModalOpen, setIsRoomModalOpen] = useState<boolean>(false);
  const [isScheduleModalOpen, setIsScheduleModalOpen] = useState<boolean>(false);
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Form State for Registering a New Room
  const [roomFormData, setRoomFormData] = useState({
    node_code: '',
    name: '',
    room_capacity: 60,
    room_type: 'CLASSROOM',
    building_code: 'EEC-ACAD',
    floor_number: 1,
    room_features: ['AC', 'PROJECTOR'] as string[],
    is_operational: true,
  });

  // Form State for Scheduling Timing (Class or Under Work Maintenance Block)
  const [scheduleFormData, setScheduleFormData] = useState({
    room_node_id: '',
    booking_type: 'MAINTENANCE_BLOCK',
    course_or_event_title: 'Room Under Maintenance & Electrical Repairs',
    student_count: 30,
    start_time: getNowPlusHours(1),
    end_time: getNowPlusHours(3),
  });

  const fetchData = async () => {
    try {
      setLoading(true);
      const [roomsData, bookingsData] = await Promise.all([
        api.get<Room[]>('/campus/rooms'),
        api.get<Booking[]>('/bookings'),
      ]);
      setRooms(roomsData);
      setBookings(bookingsData);

      // Identify disrupted classes needing move and fetch AI recommendations
      const impacted = bookingsData.filter((b) => b.status === 'IMPACTED_NEEDS_MOVE');
      impacted.forEach(async (b) => {
        try {
          const alts = await api.get<RoomAlternative[]>(
            `/rooms/alternatives?current_room_id=${b.room_node_id}&student_count=${b.student_count}&start_time=${b.start_time}&end_time=${b.end_time}`
          );
          if (Array.isArray(alts)) {
            setAlternativeRecommendations((prev) => ({ ...prev, [b.id]: alts }));
          }
        } catch (e) {
          console.error('Failed to fetch alternatives for', b.id, e);
        }
      });
    } catch (err: any) {
      console.error('Failed to load rooms or bookings:', err);
      setActionMessage({ type: 'error', text: err.message || 'Failed to fetch data.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [currentUser]);

  const handleToggleFeature = (feature: string) => {
    setRoomFormData((prev) => {
      const exists = prev.room_features.includes(feature);
      return {
        ...prev,
        room_features: exists
          ? prev.room_features.filter((f) => f !== feature)
          : [...prev.room_features, feature],
      };
    });
  };

  const handleRegisterRoom = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionMessage(null);
    if (!roomFormData.node_code.trim()) {
      setActionMessage({ type: 'error', text: 'Room Code is required (e.g. RM-ACAD-305).' });
      return;
    }
    if (!roomFormData.name.trim()) {
      setActionMessage({ type: 'error', text: 'Room Name is required.' });
      return;
    }
    try {
      await api.post('/campus/rooms', {
        node_code: roomFormData.node_code.trim().toUpperCase(),
        name: roomFormData.name.trim(),
        room_capacity: Number(roomFormData.room_capacity),
        room_type: roomFormData.room_type,
        building_code: roomFormData.building_code,
        floor_number: Number(roomFormData.floor_number),
        room_features: roomFormData.room_features,
        is_operational: roomFormData.is_operational,
      });
      setActionMessage({
        type: 'success',
        text: `Room ${roomFormData.node_code.toUpperCase()} registered successfully!`,
      });
      setIsRoomModalOpen(false);
      setRoomFormData({
        node_code: '',
        name: '',
        room_capacity: 60,
        room_type: 'CLASSROOM',
        building_code: 'EEC-ACAD',
        floor_number: 1,
        room_features: ['AC', 'PROJECTOR'],
        is_operational: true,
      });
      fetchData();
    } catch (err: any) {
      setActionMessage({
        type: 'error',
        text: err.message || 'Failed to register room. Ensure room code is unique.',
      });
    }
  };

  const handleCreateSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionMessage(null);
    if (!scheduleFormData.room_node_id) {
      setActionMessage({ type: 'error', text: 'Please select a room to schedule.' });
      return;
    }
    if (!scheduleFormData.course_or_event_title.trim()) {
      setActionMessage({ type: 'error', text: 'Title or maintenance description is required.' });
      return;
    }
    try {
      const startIso = new Date(scheduleFormData.start_time).toISOString();
      const endIso = new Date(scheduleFormData.end_time).toISOString();
      if (new Date(endIso) <= new Date(startIso)) {
        setActionMessage({ type: 'error', text: 'End timing must be later than start timing.' });
        return;
      }
      await api.post('/bookings', {
        room_node_id: scheduleFormData.room_node_id,
        booking_type: scheduleFormData.booking_type,
        course_or_event_title: scheduleFormData.course_or_event_title.trim(),
        student_count: Number(scheduleFormData.student_count),
        start_time: startIso,
        end_time: endIso,
        required_features: [],
      });
      setActionMessage({
        type: 'success',
        text: scheduleFormData.booking_type === 'MAINTENANCE_BLOCK'
          ? 'Room maintenance schedule successfully created! Room locked during this window.'
          : 'Class timing scheduled successfully!',
      });
      setIsScheduleModalOpen(false);
      fetchData();
    } catch (err: any) {
      setActionMessage({
        type: 'error',
        text: err.message || 'Scheduling conflict: Room is already booked or under work during this window.',
      });
    }
  };

  const handleCancelBooking = async (bookingId: string) => {
    if (!window.confirm('Cancel and release this room schedule window?')) return;
    try {
      await api.delete(`/bookings/${bookingId}`);
      setActionMessage({ type: 'success', text: 'Room timing released successfully.' });
      fetchData();
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'Failed to release booking.' });
    }
  };

  // ADMIN ACTION 1: Approve AI Relocation
  const handleApproveRelocation = async (booking: Booking, targetRoomId: string) => {
    try {
      setRelocatingId(booking.id);
      await api.post(`/bookings/${booking.id}/relocate`, {
        target_room_id: targetRoomId,
        reason: 'AI Relocation Approved by Admin due to room operational disruption.',
      });
      setActionMessage({ type: 'success', text: `Class relocated successfully to new classroom!` });
      await fetchData();
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'Relocation failed.' });
    } finally {
      setRelocatingId(null);
    }
  };

  // ADMIN ACTION 2: Suspend Class
  const handleSuspendClass = async (booking: Booking) => {
    if (!window.confirm(`Are you sure you want to suspend "${booking.course_or_event_title}"?`)) return;
    try {
      setRelocatingId(booking.id);
      await api.post(`/bookings/${booking.id}/suspend`, {});
      setActionMessage({ type: 'success', text: `Class "${booking.course_or_event_title}" has been suspended.` });
      await fetchData();
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'Failed to suspend class.' });
    } finally {
      setRelocatingId(null);
    }
  };

  // ADMIN ACTION 3: Reschedule Class (modal open & submit)
  const handleOpenReschedule = (booking: Booking) => {
    setReschedulingBooking(booking);
    setRescheduleFormData({
      target_room_id: booking.room_node_id,
      start_time: new Date(booking.start_time).toISOString().slice(0, 16),
      end_time: new Date(booking.end_time).toISOString().slice(0, 16),
      reason: 'Rescheduled by Admin due to room operational requirements.',
    });
  };

  const handleRescheduleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reschedulingBooking) return;
    try {
      setSubmittingReschedule(true);
      await api.post(`/bookings/${reschedulingBooking.id}/reschedule`, {
        target_room_id: rescheduleFormData.target_room_id,
        start_time: new Date(rescheduleFormData.start_time).toISOString(),
        end_time: new Date(rescheduleFormData.end_time).toISOString(),
        reason: rescheduleFormData.reason,
      });
      setActionMessage({ type: 'success', text: 'Class rescheduled successfully.' });
      setReschedulingBooking(null);
      await fetchData();
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'Reschedule failed.' });
    } finally {
      setSubmittingReschedule(false);
    }
  };

  const handleOpenScheduleForRoom = (room: Room) => {
    setScheduleFormData((prev) => ({
      ...prev,
      room_node_id: room.id,
      booking_type: 'MAINTENANCE_BLOCK',
      course_or_event_title: `Maintenance & Repairs in ${room.node_code}`,
      start_time: getNowPlusHours(1),
      end_time: getNowPlusHours(3),
    }));
    setIsScheduleModalOpen(true);
  };

  const handleToggleOperational = async (room: Room) => {
    try {
      await api.patch(`/campus/rooms/${room.id}`, {
        is_operational: !room.is_operational,
      });
      setRooms((prev) =>
        prev.map((r) => (r.id === room.id ? { ...r, is_operational: !r.is_operational } : r))
      );
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'Failed to update room status.' });
    }
  };

  const handleDeleteRoom = async (room: Room) => {
    if (!window.confirm(`Are you sure you want to delete room ${room.node_code} (${room.name})?`)) {
      return;
    }
    try {
      await api.delete(`/campus/rooms/${room.id}`);
      setActionMessage({ type: 'success', text: `Room ${room.node_code} deleted successfully.` });
      setRooms((prev) => prev.filter((r) => r.id !== room.id));
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'Failed to delete room.' });
    }
  };

  // Filtered rooms
  const filteredRooms = rooms.filter((room) => {
    const matchesSearch =
      room.node_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      room.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      room.building_code.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesBlock = selectedBlock === 'ALL' || room.building_code === selectedBlock;
    const matchesType = selectedType === 'ALL' || room.room_type === selectedType;
    return matchesSearch && matchesBlock && matchesType;
  });

  // Aggregated Stats
  const totalCapacity = rooms.filter((r) => r.room_type !== 'ADMINISTRATIVE').reduce((acc, r) => acc + (r.room_capacity || 0), 0);
  const maintenanceCount = bookings.filter((b) => b.booking_type === 'MAINTENANCE_BLOCK').length;
  const activeClassesCount = bookings.filter((b) => b.booking_type === 'CLASS' || b.booking_type === 'EXAM').length;
  const impactedBookings = bookings.filter((b) => b.status === 'IMPACTED_NEEDS_MOVE');

  return (
    <div className="h-full flex flex-col bg-transparent text-[#d8bca4] overflow-y-auto p-4 space-y-4">
      {/* Top Banner (Frosted Glass) */}
      <div className="glass-panel rounded-xl p-5 shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-lg bg-[#ec9665]/20 text-[#f4aa7f] border border-[#ec9665]/35 shadow-sm spring-interactive">
            <DoorOpen className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight flex items-center space-x-2 font-mono">
              <span>Rooms & Facility Scheduling</span>
              <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-[#ec9665]/15 text-[#f4aa7f] border border-[#ec9665]/30">
                SRM Easwari
              </span>
            </h2>
            <p className="text-xs text-[#d8bca4]/80">
              Manage physical rooms, schedule class lectures, and lock rooms under maintenance work.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2.5">
          <button
            onClick={fetchData}
            className="flex items-center space-x-1.5 px-3 py-2 bg-[#523624]/60 hover:bg-[#ec9665] text-[#d8bca4] hover:text-[#180f0a] rounded-md text-xs font-semibold border border-[#9c6c4c]/40 transition spring-interactive shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          {/* Schedule Timing Button */}
          <button
            onClick={() => {
              if (rooms.length > 0) {
                setScheduleFormData((prev) => ({
                  ...prev,
                  room_node_id: rooms[0].id,
                }));
              }
              setIsScheduleModalOpen(true);
            }}
            className="flex items-center space-x-1.5 px-3.5 py-2 bg-[#9c6c4c] hover:bg-[#9c6c4c]/90 text-white rounded-md text-xs font-bold shadow-md transition spring-interactive"
          >
            <Calendar className="w-4 h-4" />
            <span>Schedule Class / Work</span>
          </button>

          {/* Add Room Button */}
          <button
            onClick={() => setIsRoomModalOpen(true)}
            className="flex items-center space-x-1.5 px-4 py-2 bg-gradient-to-r from-[#ec9665] to-[#f4aa7f] hover:brightness-110 text-[#180f0a] rounded-md text-xs font-bold shadow-[0_4px_16px_rgba(236,150,101,0.35)] transition spring-interactive"
          >
            <Plus className="w-4 h-4" />
            <span>Add Room</span>
          </button>
        </div>
      </div>

      {/* Action Notification Alert */}
      {actionMessage && (
        <div
          className={`p-4 rounded-xl text-xs font-mono border flex items-center justify-between ${
            actionMessage.type === 'error'
              ? 'bg-rose-950/40 border-rose-500/50 text-rose-300'
              : 'bg-emerald-950/40 border-emerald-500/50 text-emerald-300'
          }`}
        >
          <div className="flex items-center space-x-2">
            {actionMessage.type === 'error' ? (
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            ) : (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            )}
            <span>{actionMessage.text}</span>
          </div>
          <button onClick={() => setActionMessage(null)} className="text-slate-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* KPI Metrics Strip (Frosted Glass Cards) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="glass-surface p-3.5 rounded-xl shadow spring-interactive">
          <div className="flex items-center justify-between">
            <span className="text-xs text-[#9c6c4c] font-mono">Total Rooms</span>
            <DoorOpen className="w-4 h-4 text-[#ec9665]" />
          </div>
          <div className="text-xl font-bold text-white mt-1 font-mono">{rooms.length}</div>
          <span className="text-[10px] text-[#9c6c4c]">Across 5 campus blocks</span>
        </div>

        <div className="glass-surface p-3.5 rounded-xl shadow spring-interactive">
          <div className="flex items-center justify-between">
            <span className="text-xs text-[#9c6c4c] font-mono">Campus Capacity</span>
            <Users className="w-4 h-4 text-[#f4aa7f]" />
          </div>
          <div className="text-xl font-bold text-[#f4aa7f] mt-1 font-mono">{totalCapacity.toLocaleString()}</div>
          <span className="text-[10px] text-[#9c6c4c]">Total seating capacity</span>
        </div>

        <div className="glass-surface p-3.5 rounded-xl shadow spring-interactive">
          <div className="flex items-center justify-between">
            <span className="text-xs text-[#9c6c4c] font-mono">Under Work / Maintenance</span>
            <Wrench className="w-4 h-4 text-[#ec9665]" />
          </div>
          <div className="text-xl font-bold text-[#ec9665] mt-1 font-mono">{maintenanceCount}</div>
          <span className="text-[10px] text-[#9c6c4c]">Scheduled maintenance windows</span>
        </div>

        <div className="glass-surface p-3.5 rounded-xl shadow spring-interactive">
          <div className="flex items-center justify-between">
            <span className="text-xs text-[#9c6c4c] font-mono">Scheduled Classes</span>
            <BookOpen className="w-4 h-4 text-[#d8bca4]" />
          </div>
          <div className="text-xl font-bold text-white mt-1 font-mono">{activeClassesCount}</div>
          <span className="text-[10px] text-[#9c6c4c]">
            {impactedBookings.length > 0 ? `${impactedBookings.length} impacted by issues` : 'Active class lectures'}
          </span>
        </div>
      </div>

      {/* DYNAMIC DISRUPTED CLASSES & AI RE-ASSIGNMENT PANEL */}
      {impactedBookings.length > 0 && (
        <div className="border-2 border-rose-500/60 bg-rose-950/20 backdrop-blur-md rounded-xl p-4 shadow-2xl space-y-3 animate-in fade-in duration-300">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-rose-500/30 pb-3">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 bg-rose-500/20 text-rose-400 rounded-lg border border-rose-500/40">
                <AlertTriangle className="w-5 h-5 animate-pulse text-rose-400" />
              </div>
              <div>
                <h3 className="font-bold text-white text-sm flex items-center gap-2">
                  <span>Scheduled Class Operational Disruptions</span>
                  <span className="px-2 py-0.5 rounded-full bg-rose-500/30 text-rose-300 text-[10px] font-mono border border-rose-500/50">
                    {impactedBookings.length} Urgent Action Needed
                  </span>
                </h3>
                <p className="text-xs text-rose-200/80">
                  Issues reported in active classrooms. Review AI-recommended free alternatives, suspend, or reschedule.
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            {impactedBookings.map((b) => {
              const alts = alternativeRecommendations[b.id] || [];
              const bestAlt = alts.length > 0 ? alts[0] : null;
              const isProcessing = relocatingId === b.id;

              return (
                <div key={b.id} className="bg-slate-900/90 border border-rose-500/40 rounded-xl p-4 space-y-3 shadow-lg">
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40">
                          {b.room_code || 'ROOM'} DISRUPTED
                        </span>
                        <h4 className="text-white font-bold text-sm">{b.course_or_event_title}</h4>
                      </div>
                      <p className="text-xs text-slate-300">
                        <span className="font-semibold text-rose-300">{b.student_count} Students</span> • Time Window:{' '}
                        <span className="font-mono text-amber-300">
                          {new Date(b.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} -{' '}
                          {new Date(b.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>{' '}
                        • Block: <span className="font-mono text-slate-400">{b.building_code}</span>
                      </p>
                    </div>

                    {/* 3 Admin Action Buttons */}
                    <div className="flex flex-wrap items-center gap-2">
                      {bestAlt && (
                        <button
                          disabled={isProcessing}
                          onClick={() => handleApproveRelocation(b, bestAlt.room_id)}
                          className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold font-mono transition flex items-center space-x-1.5 shadow-md disabled:opacity-50"
                        >
                          <Sparkles className="w-3.5 h-3.5 text-emerald-200" />
                          <span>Approve AI Relocation ({bestAlt.room_code})</span>
                        </button>
                      )}
                      <button
                        disabled={isProcessing}
                        onClick={() => handleOpenReschedule(b)}
                        className="px-3.5 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-bold font-mono transition flex items-center space-x-1.5 shadow-md disabled:opacity-50"
                      >
                        <Calendar className="w-3.5 h-3.5 text-amber-200" />
                        <span>Reschedule</span>
                      </button>
                      <button
                        disabled={isProcessing}
                        onClick={() => handleSuspendClass(b)}
                        className="px-3.5 py-2 bg-rose-700 hover:bg-rose-600 text-white rounded-lg text-xs font-bold font-mono transition flex items-center space-x-1.5 shadow-md disabled:opacity-50"
                      >
                        <XCircle className="w-3.5 h-3.5 text-rose-200" />
                        <span>Suspend Class</span>
                      </button>
                    </div>
                  </div>

                  {/* AI Prediction Recommendation Card */}
                  <div className="bg-slate-950/80 border border-indigo-500/30 rounded-lg p-3 text-xs">
                    <div className="flex items-center space-x-2 text-indigo-400 font-mono font-semibold mb-1">
                      <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                      <span>AI / CSP Constraint Optimization Prediction:</span>
                    </div>
                    {bestAlt ? (
                      <div className="text-slate-300 space-y-1">
                        <div className="flex flex-wrap items-center gap-2 font-mono">
                          <span className="text-emerald-400 font-bold">{bestAlt.room_code}</span>
                          <span className="text-slate-400">({bestAlt.room_name})</span>
                          <span className="text-slate-500">•</span>
                          <span>Capacity: {bestAlt.room_capacity} seats</span>
                          <span className="text-slate-500">•</span>
                          <span className="text-indigo-300">0 Schedule Collisions</span>
                          <span className="text-slate-500">•</span>
                          <span className="text-amber-300/80">Wasted Seats: {bestAlt.wasted_seats}</span>
                        </div>
                        <p className="text-[11px] text-slate-400">{bestAlt.explanation}</p>
                      </div>
                    ) : (
                      <p className="text-slate-400 italic">
                        Searching for free rooms during this time slot... If none available, consider rescheduling or suspending.
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Search & Filters */}
      <div className="glass-panel rounded-xl p-3 shadow flex flex-col md:flex-row items-center justify-between gap-3">
        <div className="relative w-full md:w-80">
          <Search className="w-3.5 h-3.5 text-[#9c6c4c] absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search room code, name, or block..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full glass-input rounded-md pl-9 pr-3 py-1.5 text-xs text-[#f4aa7f] placeholder-[#9c6c4c] focus:outline-none"
          />
        </div>

        <div className="flex items-center space-x-2 w-full md:w-auto overflow-x-auto pb-1 md:pb-0">
          <div className="flex items-center space-x-1 bg-[#24160f]/60 p-1 rounded-md border border-[#9c6c4c]/30">
            <Building2 className="w-3.5 h-3.5 text-[#9c6c4c] ml-1" />
            <select
              value={selectedBlock}
              onChange={(e) => setSelectedBlock(e.target.value)}
              className="bg-transparent text-xs text-[#d8bca4] font-mono border-none focus:outline-none pr-2 py-0.5"
            >
              <option value="ALL" className="bg-[#180f0a]">All Blocks</option>
              {AVAILABLE_BLOCKS.map((b) => (
                <option key={b.code} value={b.code} className="bg-[#180f0a]">
                  {b.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center space-x-1 bg-[#24160f]/60 p-1 rounded-md border border-[#9c6c4c]/30">
            <Layers className="w-3.5 h-3.5 text-[#9c6c4c] ml-1" />
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="bg-transparent text-xs text-[#d8bca4] font-mono border-none focus:outline-none pr-2 py-0.5"
            >
              <option value="ALL" className="bg-[#180f0a]">All Types</option>
              {ROOM_TYPES.map((t) => (
                <option key={t.value} value={t.value} className="bg-[#180f0a]">
                  {t.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Main Split Layout: Left Rooms Table, Right Schedules & Maintenance */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4 flex-1">
        {/* Left: Rooms Table */}
        <div className="xl:col-span-7 glass-panel rounded-xl flex flex-col overflow-hidden shadow-lg">
          <div className="p-3 border-b border-[#9c6c4c]/30 flex items-center justify-between shrink-0">
            <div className="flex items-center space-x-2">
              <DoorOpen className="w-4 h-4 text-[#ec9665]" />
              <h3 className="font-bold text-[#f4aa7f] text-xs uppercase tracking-wider font-mono">
                Campus Spaces ({filteredRooms.length})
              </h3>
            </div>
            {isAdmin && (
              <button
                onClick={() => setIsRoomModalOpen(true)}
                className="px-2.5 py-1 bg-gradient-to-r from-[#ec9665] to-[#f4aa7f] text-[#180f0a] font-bold text-[11px] rounded font-mono spring-interactive shadow"
              >
                + Add Room
              </button>
            )}
          </div>

          <div className="overflow-auto flex-1">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-[#24160f]/90 text-[#d8bca4]/70 border-b border-[#9c6c4c]/30 font-mono text-[10px] sticky top-0 z-10 shadow-sm">
                <tr>
                  <th className="py-2 px-2.5 w-24 border-r border-[#9c6c4c]/20">Room Code</th>
                  <th className="py-2 px-2.5 border-r border-[#9c6c4c]/20">Room Name</th>
                  <th className="py-2 px-2.5 w-16 border-r border-[#9c6c4c]/20">Block</th>
                  <th className="py-2 px-2.5 w-24 border-r border-[#9c6c4c]/20">Type</th>
                  <th className="py-2 px-2.5 w-16 border-r border-[#9c6c4c]/20">Cap</th>
                  <th className="py-2 px-2.5 w-24 border-r border-[#9c6c4c]/20">Status</th>
                  <th className="py-2 px-2.5 w-20 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#9c6c4c]/20 font-sans">
                {filteredRooms.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-16 text-center text-[#9c6c4c] font-mono text-xs">
                      No registered rooms found. Click "+ Add Room" to register spaces.
                    </td>
                  </tr>
                ) : (
                  filteredRooms.map((room) => {
                    const typeObj = ROOM_TYPES.find((t) => t.value === room.room_type) || {
                      color: 'bg-[#523624]/60 text-[#d8bca4] border-[#9c6c4c]/40',
                      label: room.room_type,
                    };

                    const hasMaintenance = bookings.some(
                      (b) => b.room_node_id === room.id && b.booking_type === 'MAINTENANCE_BLOCK'
                    );

                    const hasImpact = bookings.some(
                      (b) => b.room_node_id === room.id && b.status === 'IMPACTED_NEEDS_MOVE'
                    );

                    return (
                      <tr key={room.id} className="hover:bg-[#523624]/35 transition spring-row h-8">
                        <td className="py-1 px-2.5 font-mono font-bold text-[#ec9665] border-r border-[#9c6c4c]/20 truncate">
                          {room.node_code}
                        </td>
                        <td className="py-1 px-2.5 font-semibold text-white border-r border-[#9c6c4c]/20 truncate">
                          {room.name}
                        </td>
                        <td className="py-1 px-2.5 font-mono text-[#d8bca4] border-r border-[#9c6c4c]/20">
                          {room.building_code}
                        </td>
                        <td className="py-1 px-2.5 border-r border-[#9c6c4c]/20">
                          <span className={`text-[9px] px-1.5 py-0.2 rounded font-mono border ${typeObj.color}`}>
                            {room.room_type}
                          </span>
                        </td>
                        <td className="py-1 px-2.5 font-mono font-bold text-[#f4aa7f] border-r border-[#9c6c4c]/20">
                          {room.room_type === 'ADMINISTRATIVE' ? (
                            <span className="text-slate-500 font-mono font-normal text-[11px]">—</span>
                          ) : (
                            room.room_capacity
                          )}
                        </td>
                        <td className="py-1 px-2.5 border-r border-[#9c6c4c]/20">
                          {hasImpact ? (
                            <span className="inline-flex items-center space-x-1 text-[9px] px-1.5 py-0.2 rounded font-mono bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse font-bold">
                              <AlertTriangle className="w-2.5 h-2.5 text-rose-400" />
                              <span>IMPACTED</span>
                            </span>
                          ) : hasMaintenance ? (
                            <span className="inline-flex items-center space-x-1 text-[9px] px-1.5 py-0.2 rounded font-mono bg-[#ec9665]/20 text-[#f4aa7f] border border-[#ec9665]/40">
                              <Wrench className="w-2.5 h-2.5 text-[#ec9665]" />
                              <span>WORK</span>
                            </span>
                          ) : (
                            <button
                              onClick={() => handleToggleOperational(room)}
                              className={`inline-flex items-center space-x-1 text-[9px] px-1.5 py-0.2 rounded font-mono border transition spring-interactive ${
                                room.is_operational
                                  ? 'bg-[#ec9665]/15 text-[#f4aa7f] border-[#ec9665]/35 hover:bg-[#ec9665]/25'
                                  : 'bg-rose-500/15 text-rose-300 border-rose-500/35 hover:bg-rose-500/25'
                              }`}
                            >
                              <span>{room.is_operational ? 'OK' : 'OFFLINE'}</span>
                            </button>
                          )}
                        </td>
                        <td className="py-1 px-2.5 text-right">
                          <div className="flex items-center justify-end space-x-1">
                            <button
                              onClick={() => handleOpenScheduleForRoom(room)}
                              className="p-1 hover:bg-[#ec9665]/20 text-[#f4aa7f] rounded transition spring-interactive"
                              title="Schedule Work / Class"
                            >
                              <Clock className="w-3 h-3" />
                            </button>
                            <button
                              onClick={() => handleDeleteRoom(room)}
                              className="p-1 hover:bg-rose-500/25 text-[#9c6c4c] hover:text-rose-300 rounded transition spring-interactive"
                              title="Delete Room"
                            >
                              <Trash2 className="w-3 h-3" />
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
        </div>

        {/* Right: Active Schedules & Under Work Windows */}
        <div className="xl:col-span-5 glass-panel rounded-xl flex flex-col overflow-hidden shadow-lg">
          <div className="p-3 border-b border-[#9c6c4c]/30 flex items-center justify-between shrink-0">
            <div className="flex items-center space-x-2">
              <Calendar className="w-4 h-4 text-[#ec9665]" />
              <h3 className="font-bold text-[#f4aa7f] text-xs uppercase tracking-wider font-mono">
                Schedules & Maintenance ({bookings.length})
              </h3>
            </div>
            {isAdmin && (
              <button
                onClick={() => setIsScheduleModalOpen(true)}
                className="px-2.5 py-1 bg-[#523624]/60 hover:bg-[#523624] text-[#f4aa7f] border border-[#9c6c4c]/40 font-bold text-[11px] rounded font-mono spring-interactive shadow"
              >
                + Schedule Work/Class
              </button>
            )}
          </div>

          <div className="overflow-auto flex-1">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-[#24160f]/90 text-[#d8bca4]/70 border-b border-[#9c6c4c]/30 font-mono text-[10px] sticky top-0 z-10 shadow-sm">
                <tr>
                  <th className="py-2 px-2.5 w-20 border-r border-[#9c6c4c]/20">Room</th>
                  <th className="py-2 px-2.5 w-20 border-r border-[#9c6c4c]/20">Status</th>
                  <th className="py-2 px-2.5 border-r border-[#9c6c4c]/20">Activity / Work Title</th>
                  <th className="py-2 px-2.5 w-24 border-r border-[#9c6c4c]/20">Window</th>
                  <th className="py-2 px-2.5 w-16 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#9c6c4c]/20 font-sans">
                {bookings.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-16 text-center text-[#9c6c4c] font-mono text-xs">
                      No active bookings or maintenance lockouts. Click "+ Schedule Work/Class" to book.
                    </td>
                  </tr>
                ) : (
                  bookings.map((b) => {
                    const isMaintenance = b.booking_type === 'MAINTENANCE_BLOCK';
                    const isImpacted = b.status === 'IMPACTED_NEEDS_MOVE';
                    const isRelocated = b.status === 'RELOCATED';
                    const isSuspended = b.status === 'SUSPENDED';

                    return (
                      <tr key={b.id} className="hover:bg-[#523624]/35 transition spring-row h-8">
                        <td className="py-1.5 px-2.5 font-mono font-bold text-[#ec9665] border-r border-[#9c6c4c]/20">
                          <div className="truncate">{b.room_code || 'Room'}</div>
                          {isRelocated && b.relocated_to_room_code && (
                            <div className="text-[10px] text-purple-400 font-mono flex items-center gap-1 font-bold mt-0.5">
                              <span>➜</span>
                              <span>{b.relocated_to_room_code}</span>
                            </div>
                          )}
                        </td>
                        <td className="py-1 px-2.5 border-r border-[#9c6c4c]/20">
                          {isImpacted ? (
                            <span className="text-[9px] px-1.5 py-0.2 rounded font-mono bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse font-bold">
                              IMPACTED
                            </span>
                          ) : isRelocated ? (
                            <span className="text-[9px] px-1.5 py-0.2 rounded font-mono bg-purple-500/20 text-purple-300 border border-purple-500/40 font-bold">
                              RELOCATED
                            </span>
                          ) : isSuspended ? (
                            <span className="text-[9px] px-1.5 py-0.2 rounded font-mono bg-slate-800 text-slate-400 border border-slate-700 font-bold">
                              SUSPENDED
                            </span>
                          ) : isMaintenance ? (
                            <span className="text-[9px] px-1.5 py-0.2 rounded font-mono bg-[#ec9665]/20 text-[#f4aa7f] border border-[#ec9665]/40 font-bold">
                              WORK
                            </span>
                          ) : (
                            <span className="text-[9px] px-1.5 py-0.2 rounded font-mono bg-[#9c6c4c]/25 text-[#d8bca4] border-[#9c6c4c]/40 font-bold">
                              CLASS
                            </span>
                          )}
                        </td>
                        <td className="py-1.5 px-2.5 font-semibold text-white border-r border-[#9c6c4c]/20">
                          <div className="truncate">{b.course_or_event_title}</div>
                          {isRelocated && (
                            <div className="mt-1 flex items-center flex-wrap gap-1">
                              <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-purple-950/80 border border-purple-500/40 text-purple-300 inline-flex items-center gap-1 shadow-sm">
                                <span className="text-purple-400 font-bold">➜ Relocated to:</span>
                                <strong className="text-white underline decoration-purple-400">
                                  {b.relocated_to_room_code || 'Alternative Classroom'}
                                </strong>
                                {b.relocated_to_room_name && (
                                  <span className="text-purple-300/80 font-normal truncate max-w-[140px]">
                                    ({b.relocated_to_room_name})
                                  </span>
                                )}
                              </span>
                            </div>
                          )}
                        </td>
                        <td className="py-1 px-2.5 font-mono text-[10px] text-[#f4aa7f] border-r border-[#9c6c4c]/20 truncate">
                          {new Date(b.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} -{' '}
                          {new Date(b.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </td>
                        <td className="py-1 px-2.5 text-right">
                          <button
                            onClick={() => handleCancelBooking(b.id)}
                            className="px-2 py-0.5 bg-[#523624]/60 hover:bg-rose-950/60 text-[#d8bca4] hover:text-rose-300 rounded text-[10px] font-semibold border border-[#9c6c4c]/40 transition spring-interactive"
                          >
                            Cancel
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* MODAL: Reschedule Class */}
      {reschedulingBooking && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="glass-panel bg-[#24160f]/95 border border-[#9c6c4c]/40 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden animate-in fade-in duration-200">
            <div className="p-5 border-b border-[#9c6c4c]/30 flex items-center justify-between bg-[#180f0a]/60">
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
                className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-[#523624]/40 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleRescheduleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-mono text-[#d8bca4]/70 mb-1">
                  Target Classroom *
                </label>
                <select
                  required
                  value={rescheduleFormData.target_room_id}
                  onChange={(e) => setRescheduleFormData({ ...rescheduleFormData, target_room_id: e.target.value })}
                  className="w-full glass-input bg-[#180f0a]/70 border border-[#9c6c4c]/40 rounded-lg px-3 py-2 text-xs text-[#d8bca4] font-mono focus:outline-none focus:border-[#ec9665]"
                >
                  {rooms.map((r) => (
                    <option key={r.id} value={r.id} className="bg-[#180f0a] text-[#d8bca4]">
                      {r.node_code} - {r.name} (Cap: {r.room_capacity}, {r.building_code})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-mono text-[#d8bca4]/70 mb-1">
                    New Start Time *
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={rescheduleFormData.start_time}
                    onChange={(e) => setRescheduleFormData({ ...rescheduleFormData, start_time: e.target.value })}
                    className="w-full glass-input bg-[#180f0a]/70 border border-[#9c6c4c]/40 rounded-lg px-3 py-2 text-xs text-[#d8bca4] font-mono focus:outline-none focus:border-[#ec9665]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-mono text-[#d8bca4]/70 mb-1">
                    New End Time *
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={rescheduleFormData.end_time}
                    onChange={(e) => setRescheduleFormData({ ...rescheduleFormData, end_time: e.target.value })}
                    className="w-full glass-input bg-[#180f0a]/70 border border-[#9c6c4c]/40 rounded-lg px-3 py-2 text-xs text-[#d8bca4] font-mono focus:outline-none focus:border-[#ec9665]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono text-[#d8bca4]/70 mb-1">
                  Rescheduling Reason / Justification
                </label>
                <input
                  type="text"
                  value={rescheduleFormData.reason}
                  onChange={(e) => setRescheduleFormData({ ...rescheduleFormData, reason: e.target.value })}
                  className="w-full glass-input bg-[#180f0a]/70 border border-[#9c6c4c]/40 rounded-lg px-3 py-2 text-xs text-[#d8bca4] font-mono focus:outline-none focus:border-[#ec9665]"
                />
              </div>

              <div className="pt-3 border-t border-[#9c6c4c]/30 flex items-center justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setReschedulingBooking(null)}
                  className="px-4 py-2 bg-[#523624]/60 hover:bg-[#523624] text-[#d8bca4] rounded-lg text-xs font-semibold border border-[#9c6c4c]/30 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingReschedule}
                  className="px-5 py-2 bg-gradient-to-r from-amber-600 to-amber-500 text-white font-bold rounded-lg text-xs shadow-lg transition disabled:opacity-50"
                >
                  {submittingReschedule ? 'Rescheduling...' : 'Confirm Reschedule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: Schedule Class or Maintenance Work */}
      {isScheduleModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="glass-panel bg-[#24160f]/95 border border-[#9c6c4c]/40 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden animate-in fade-in duration-200">
            <div className="p-5 border-b border-[#9c6c4c]/30 flex items-center justify-between bg-[#180f0a]/60">
              <div className="flex items-center space-x-2.5">
                <div className="p-2 bg-[#ec9665]/20 text-[#ec9665] rounded-lg border border-[#ec9665]/30">
                  <Calendar className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-[#d8bca4] text-base">Schedule Class or Work Timing</h3>
                  <p className="text-xs text-[#d8bca4]/60">
                    Schedule lectures or lock a room for maintenance & repair work.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsScheduleModalOpen(false)}
                className="text-[#d8bca4]/60 hover:text-[#d8bca4] p-1.5 rounded-lg hover:bg-[#523624]/40 spring-interactive transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateSchedule} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-mono text-[#d8bca4]/70 mb-1">
                  Select Room *
                </label>
                {rooms.length === 0 ? (
                  <div className="p-3 bg-rose-950/40 border border-rose-500/30 rounded-lg text-xs text-rose-300">
                    No rooms registered yet! Please add a room first before scheduling.
                  </div>
                ) : (
                  <select
                    required
                    value={scheduleFormData.room_node_id}
                    onChange={(e) => setScheduleFormData({ ...scheduleFormData, room_node_id: e.target.value })}
                    className="w-full glass-input bg-[#180f0a]/70 border border-[#9c6c4c]/40 rounded-lg px-3 py-2 text-xs text-[#d8bca4] font-mono focus:outline-none focus:border-[#ec9665]"
                  >
                    <option value="" className="bg-[#180f0a] text-[#d8bca4]">-- Choose Room --</option>
                    {rooms.map((r) => (
                      <option key={r.id} value={r.id} className="bg-[#180f0a] text-[#d8bca4]">
                        {r.node_code} - {r.name} ({r.building_code}, Cap: {r.room_capacity})
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div>
                <label className="block text-xs font-mono text-[#d8bca4]/70 mb-1">
                  Schedule Type *
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setScheduleFormData({
                      ...scheduleFormData,
                      booking_type: 'MAINTENANCE_BLOCK',
                      course_or_event_title: 'Room Under Maintenance & Work',
                    })}
                    className={`flex items-center space-x-2 p-2.5 rounded-lg border text-xs font-semibold spring-interactive transition ${
                      scheduleFormData.booking_type === 'MAINTENANCE_BLOCK'
                        ? 'bg-[#ec9665]/20 border-[#ec9665] text-[#f4aa7f]'
                        : 'bg-[#180f0a]/60 border-[#9c6c4c]/30 text-[#d8bca4]/70 hover:border-[#9c6c4c]/60'
                    }`}
                  >
                    <Wrench className="w-4 h-4 text-[#ec9665]" />
                    <span>Maintenance Work</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setScheduleFormData({
                      ...scheduleFormData,
                      booking_type: 'CLASS',
                      course_or_event_title: 'Class Lecture Session',
                    })}
                    className={`flex items-center space-x-2 p-2.5 rounded-lg border text-xs font-semibold spring-interactive transition ${
                      scheduleFormData.booking_type === 'CLASS'
                        ? 'bg-[#ec9665]/20 border-[#ec9665] text-[#f4aa7f]'
                        : 'bg-[#180f0a]/60 border-[#9c6c4c]/30 text-[#d8bca4]/70 hover:border-[#9c6c4c]/60'
                    }`}
                  >
                    <BookOpen className="w-4 h-4 text-[#ec9665]" />
                    <span>Academic Class</span>
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono text-[#d8bca4]/70 mb-1">
                  Activity / Course Title *
                </label>
                <input
                  type="text"
                  required
                  value={scheduleFormData.course_or_event_title}
                  onChange={(e) => setScheduleFormData({ ...scheduleFormData, course_or_event_title: e.target.value })}
                  placeholder="e.g. CS602 Data Structures or HVAC Overhaul"
                  className="w-full glass-input bg-[#180f0a]/70 border border-[#9c6c4c]/40 rounded-lg px-3 py-2 text-xs text-[#d8bca4] font-mono focus:outline-none focus:border-[#ec9665]"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-mono text-[#d8bca4]/70 mb-1">
                    Start Timing *
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={scheduleFormData.start_time}
                    onChange={(e) => setScheduleFormData({ ...scheduleFormData, start_time: e.target.value })}
                    className="w-full glass-input bg-[#180f0a]/70 border border-[#9c6c4c]/40 rounded-lg px-3 py-2 text-xs text-[#d8bca4] font-mono focus:outline-none focus:border-[#ec9665]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono text-[#d8bca4]/70 mb-1">
                    End Timing *
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={scheduleFormData.end_time}
                    onChange={(e) => setScheduleFormData({ ...scheduleFormData, end_time: e.target.value })}
                    className="w-full glass-input bg-[#180f0a]/70 border border-[#9c6c4c]/40 rounded-lg px-3 py-2 text-xs text-[#d8bca4] font-mono focus:outline-none focus:border-[#ec9665]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono text-[#d8bca4]/70 mb-1">
                  Expected Attendees / Student Count
                </label>
                <input
                  type="number"
                  min={1}
                  max={500}
                  value={scheduleFormData.student_count}
                  onChange={(e) => setScheduleFormData({ ...scheduleFormData, student_count: parseInt(e.target.value) || 0 })}
                  className="w-full glass-input bg-[#180f0a]/70 border border-[#9c6c4c]/40 rounded-lg px-3 py-2 text-xs text-[#d8bca4] font-mono focus:outline-none focus:border-[#ec9665]"
                />
              </div>

              <div className="pt-3 border-t border-[#9c6c4c]/30 flex items-center justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsScheduleModalOpen(false)}
                  className="px-4 py-2 bg-[#523624]/60 hover:bg-[#523624] text-[#d8bca4] rounded-lg text-xs font-semibold border border-[#9c6c4c]/30 spring-interactive transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-gradient-to-r from-[#ec9665] to-[#f4aa7f] text-[#180f0a] font-bold rounded-lg text-xs shadow-lg shadow-[#ec9665]/20 spring-interactive transition"
                >
                  Schedule Timing
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: Register Room */}
      {isRoomModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="glass-panel bg-[#24160f]/95 border border-[#9c6c4c]/40 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden animate-in fade-in duration-200">
            <div className="p-5 border-b border-[#9c6c4c]/30 flex items-center justify-between bg-[#180f0a]/60">
              <div className="flex items-center space-x-2.5">
                <div className="p-2 bg-[#ec9665]/20 text-[#ec9665] rounded-lg border border-[#ec9665]/30">
                  <DoorOpen className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-[#d8bca4] text-base">Register New Room</h3>
                  <p className="text-xs text-[#d8bca4]/60">Add a physical space to the campus topology.</p>
                </div>
              </div>
              <button
                onClick={() => setIsRoomModalOpen(false)}
                className="text-[#d8bca4]/60 hover:text-[#d8bca4] p-1.5 rounded-lg hover:bg-[#523624]/40 spring-interactive transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleRegisterRoom} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-mono text-[#d8bca4]/70 mb-1">
                    Room Code *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. RM-ACAD-305"
                    value={roomFormData.node_code}
                    onChange={(e) => setRoomFormData({ ...roomFormData, node_code: e.target.value })}
                    className="w-full glass-input bg-[#180f0a]/70 border border-[#9c6c4c]/40 rounded-lg px-3 py-2 text-xs text-[#d8bca4] font-mono focus:outline-none focus:border-[#ec9665]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono text-[#d8bca4]/70 mb-1">
                    Room Name *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. AI Research Lab"
                    value={roomFormData.name}
                    onChange={(e) => setRoomFormData({ ...roomFormData, name: e.target.value })}
                    className="w-full glass-input bg-[#180f0a]/70 border border-[#9c6c4c]/40 rounded-lg px-3 py-2 text-xs text-[#d8bca4] font-mono focus:outline-none focus:border-[#ec9665]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-mono text-[#d8bca4]/70 mb-1">
                    Room Type *
                  </label>
                  <select
                    value={roomFormData.room_type}
                    onChange={(e) => {
                      const newType = e.target.value;
                      setRoomFormData({
                        ...roomFormData,
                        room_type: newType,
                        room_capacity: newType === 'ADMINISTRATIVE' ? 0 : (roomFormData.room_capacity || 60),
                      });
                    }}
                    className="w-full glass-input bg-[#180f0a]/70 border border-[#9c6c4c]/40 rounded-lg px-3 py-2 text-xs text-[#d8bca4] font-mono focus:outline-none focus:border-[#ec9665]"
                  >
                    {ROOM_TYPES.map((t) => (
                      <option key={t.value} value={t.value} className="bg-[#180f0a] text-[#d8bca4]">
                        {t.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-mono text-[#d8bca4]/70 mb-1">
                    {roomFormData.room_type === 'ADMINISTRATIVE' ? 'Capacity (Not Applicable)' : 'Capacity (Seats) *'}
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={1000}
                    disabled={roomFormData.room_type === 'ADMINISTRATIVE'}
                    required={roomFormData.room_type !== 'ADMINISTRATIVE'}
                    value={roomFormData.room_type === 'ADMINISTRATIVE' ? '' : roomFormData.room_capacity}
                    onChange={(e) => setRoomFormData({ ...roomFormData, room_capacity: parseInt(e.target.value) || 0 })}
                    placeholder={roomFormData.room_type === 'ADMINISTRATIVE' ? '— Not applicable for Admin Blocks —' : 'e.g. 60'}
                    className="w-full glass-input bg-[#180f0a]/70 border border-[#9c6c4c]/40 rounded-lg px-3 py-2 text-xs text-[#d8bca4] font-mono focus:outline-none focus:border-[#ec9665] disabled:opacity-50 disabled:cursor-not-allowed"
                  />
              </div>
              </div>

              <div>
                <label className="block text-xs font-mono text-[#d8bca4]/70 mb-1">
                  Building Block *
                </label>
                <select
                  value={roomFormData.building_code}
                  onChange={(e) => setRoomFormData({ ...roomFormData, building_code: e.target.value })}
                  className="w-full glass-input bg-[#180f0a]/70 border border-[#9c6c4c]/40 rounded-lg px-3 py-2 text-xs text-[#d8bca4] font-mono focus:outline-none focus:border-[#ec9665]"
                >
                  {AVAILABLE_BLOCKS.map((b) => (
                    <option key={b.code} value={b.code} className="bg-[#180f0a] text-[#d8bca4]">
                      {b.code} - {b.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-mono text-[#d8bca4]/70 mb-1">
                    Floor Number
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={6}
                    value={roomFormData.floor_number}
                    onChange={(e) => setRoomFormData({ ...roomFormData, floor_number: parseInt(e.target.value) || 1 })}
                    className="w-full glass-input bg-[#180f0a]/70 border border-[#9c6c4c]/40 rounded-lg px-3 py-2 text-xs text-[#d8bca4] font-mono focus:outline-none focus:border-[#ec9665]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono text-[#d8bca4]/70 mb-1">
                    Initial Status
                  </label>
                  <select
                    value={roomFormData.is_operational ? 'true' : 'false'}
                    onChange={(e) => setRoomFormData({ ...roomFormData, is_operational: e.target.value === 'true' })}
                    className="w-full glass-input bg-[#180f0a]/70 border border-[#9c6c4c]/40 rounded-lg px-3 py-2 text-xs text-[#d8bca4] font-mono focus:outline-none focus:border-[#ec9665]"
                  >
                    <option value="true" className="bg-[#180f0a] text-[#d8bca4]">Operational</option>
                    <option value="false" className="bg-[#180f0a] text-[#d8bca4]">Under Maintenance</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono text-[#d8bca4]/70 mb-2">
                  Room Features & Amenities
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {FEATURE_OPTIONS.map((feat) => {
                    const isSelected = roomFormData.room_features.includes(feat);
                    return (
                      <button
                        type="button"
                        key={feat}
                        onClick={() => handleToggleFeature(feat)}
                        className={`text-left px-2.5 py-1.5 rounded-lg border text-xs font-mono transition flex items-center justify-between spring-interactive ${
                          isSelected
                            ? 'bg-[#ec9665]/20 border-[#ec9665] text-[#f4aa7f]'
                            : 'bg-[#180f0a]/60 border-[#9c6c4c]/30 text-[#d8bca4]/70 hover:border-[#9c6c4c]/60'
                        }`}
                      >
                        <span>{feat}</span>
                        {isSelected && <CheckCircle2 className="w-3.5 h-3.5 text-[#ec9665]" />}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="pt-3 border-t border-[#9c6c4c]/30 flex items-center justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsRoomModalOpen(false)}
                  className="px-4 py-2 bg-[#523624]/60 hover:bg-[#523624] text-[#d8bca4] rounded-lg text-xs font-semibold border border-[#9c6c4c]/30 spring-interactive transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-gradient-to-r from-[#ec9665] to-[#f4aa7f] text-[#180f0a] font-bold rounded-lg text-xs shadow-lg shadow-[#ec9665]/20 spring-interactive transition"
                >
                  Register Room
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
