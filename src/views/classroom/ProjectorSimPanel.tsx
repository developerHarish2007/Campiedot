import React, { useState, useEffect, useMemo } from 'react';
import {
  PG_PROJECTOR_IDS,
  FaultType,
  RATED_LAMP_HOURS,
  FILTER_SERVICE_INTERVAL,
  DAILY_LAMP_HOURS,
  BASE_SIM_DATE,
  projectorSim
} from '../../sim/projectorSim';
import { DevicePrediction, projectorPredictor } from '../../sim/projectorPredictor';
import { dashboardBridge } from '../../services/dashboardBridge';

interface SimPanelProps {
  currentDay: number;
  onDayChange: (day: number) => void;
  predictions: Record<string, DevicePrediction>;
  faults: Record<string, FaultType>;
  onSetFault: (deviceId: string, fault: FaultType) => void;
  onReset: () => void;
  activeTab?: 'status' | 'connection';
  onTabChange?: (tab: 'status' | 'connection') => void;
  selectedDeviceId?: string;
  onSelectDevice?: (deviceId: string) => void;
  noiseEnabled?: boolean;
  onToggleNoise?: (enabled: boolean) => void;
  onClose?: () => void;
}

export function ProjectorSimPanel({
  currentDay,
  onDayChange,
  predictions,
  faults,
  onSetFault,
  onReset,
  activeTab = 'status',
  onTabChange,
  selectedDeviceId = 'PG-201-PROJ',
  onSelectDevice,
  noiseEnabled = false,
  onToggleNoise,
  onClose
}: SimPanelProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [localTab, setLocalTab] = useState<'status' | 'connection'>(activeTab);
  const [localSelectedDev, setLocalSelectedDev] = useState<string>(selectedDeviceId);
  const [, setBridgeTick] = useState(0);
  const [copiedWarning, setCopiedWarning] = useState(false);

  useEffect(() => {
    return dashboardBridge.subscribe(() => setBridgeTick(t => t + 1));
  }, []);

  // Sync props to state if provided externally
  useEffect(() => {
    if (activeTab) setLocalTab(activeTab);
  }, [activeTab]);

  useEffect(() => {
    if (selectedDeviceId) setLocalSelectedDev(selectedDeviceId);
  }, [selectedDeviceId]);

  const handleTabClick = (tab: 'status' | 'connection') => {
    setLocalTab(tab);
    onTabChange?.(tab);
  };

  const handleDevicePick = (devId: string) => {
    setLocalSelectedDev(devId);
    onSelectDevice?.(devId);
  };

  // Play/Pause simulation timer: advances 1 day every 0.5s, stops at 30
  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      onDayChange(Math.min(30, currentDay + 1));
      if (currentDay >= 29) {
        setIsPlaying(false);
      }
    }, 500);
    return () => clearInterval(interval);
  }, [isPlaying, currentDay, onDayChange]);

  const simCalendarDate = useMemo(() => {
    const d = new Date(BASE_SIM_DATE + 'T00:00:00Z');
    d.setDate(d.getDate() + currentDay);
    return d.toISOString().split('T')[0];
  }, [currentDay]);

  const stateColors: Record<string, { bg: string; text: string; border: string; label: string }> = {
    healthy: { bg: '#064e3b', text: '#34d399', border: '#059669', label: 'HEALTHY' },
    degrading: { bg: '#78350f', text: '#fbbf24', border: '#d97706', label: 'DEGRADING' },
    imminent: { bg: '#881337', text: '#f43f5e', border: '#e11d48', label: 'IMMINENT FAILURE' },
    failed: { bg: '#450a0a', text: '#fda4af', border: '#991b1b', label: 'FAILED / OFFLINE' }
  };

  // Precompute 31-day sparkline history for all devices
  const sparklineData = useMemo(() => {
    const data: Record<string, number[]> = {};
    for (const p of PG_PROJECTOR_IDS) {
      const scores: number[] = [];
      for (let d = 0; d <= 30; d++) {
        const r = projectorSim.getReadingsUpToDay(p.deviceId, d);
        const pred = projectorPredictor.predict(p.deviceId, r);
        scores.push(pred.healthScore);
      }
      data[p.deviceId] = scores;
    }
    return data;
  }, [faults, noiseEnabled]);

  const selectedPred = predictions[localSelectedDev] ?? predictions['PG-201-PROJ'];
  const selectedConfig = PG_PROJECTOR_IDS.find(p => p.deviceId === localSelectedDev) ?? PG_PROJECTOR_IDS[2];
  const pjlinkData = useMemo(() => {
    if (!selectedPred) return null;
    return projectorSim.getPJLinkExchanges(localSelectedDev, selectedPred.lastReading);
  }, [localSelectedDev, selectedPred]);

  return (
    <div
      className="projector-sim-panel"
      style={{
        position: 'absolute',
        top: 60,
        right: 18,
        width: 410,
        maxHeight: 'calc(100vh - 120px)',
        background: 'rgba(15, 23, 42, 0.96)',
        backdropFilter: 'blur(16px)',
        border: '1px solid #334155',
        borderRadius: 14,
        boxShadow: '0 16px 40px rgba(0, 0, 0, 0.65)',
        color: '#f8fafc',
        zIndex: 130,
        display: 'flex',
        flexDirection: 'column',
        fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
        overflow: 'hidden',
        pointerEvents: 'auto'
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '12px 14px',
          borderBottom: '1px solid #334155',
          background: 'rgba(30, 41, 59, 0.85)',
          display: 'flex',
          flexDirection: 'column',
          gap: 8
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
              <span>📽️</span> PG Smart Labs Projector Maintenance
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>
              Deterministic PJLink Predictive Twin (5 Floors)
            </div>
          </div>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <button
              onClick={() => {
                setIsPlaying(false);
                onReset();
              }}
              title="Reset all projectors to scripted pilot demo scenario"
              style={{
                padding: '4px 8px',
                fontSize: 10,
                fontWeight: 600,
                background: '#334155',
                color: '#38bdf8',
                border: '1px solid #0284c7',
                borderRadius: 4,
                cursor: 'pointer'
              }}
            >
              Reset Pilot
            </button>
            <button
              onClick={() => setCollapsed(v => !v)}
              title={collapsed ? "Expand Panel" : "Collapse Panel"}
              style={{
                padding: '4px 7px',
                fontSize: 11,
                background: 'transparent',
                color: '#94a3b8',
                border: '1px solid #475569',
                borderRadius: 4,
                cursor: 'pointer'
              }}
            >
              {collapsed ? '▼' : '▲'}
            </button>
            {onClose && (
              <button
                onClick={onClose}
                title="Close Sim Panel (Esc)"
                style={{
                  padding: '4px 7px',
                  fontSize: 11,
                  background: 'rgba(239, 68, 68, 0.15)',
                  color: '#f87171',
                  border: '1px solid #dc2626',
                  borderRadius: 4,
                  cursor: 'pointer',
                  fontWeight: 700
                }}
              >
                ✕
              </button>
            )}
          </div>
        </div>

        {!collapsed && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(15, 23, 42, 0.6)', padding: '6px 10px', borderRadius: 8, border: '1px solid #1e293b' }}>
            <div style={{ fontSize: 11, display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ color: '#38bdf8', fontWeight: 600 }}>Sim date:</span>
              <span style={{ fontFamily: 'monospace', fontWeight: 700, color: '#f8fafc' }}>{simCalendarDate}</span>
              <span style={{ color: '#94a3b8', fontSize: 10 }}>(day {currentDay})</span>
            </div>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <button
                onClick={() => setIsPlaying(v => !v)}
                style={{
                  padding: '3px 8px',
                  fontSize: 11,
                  fontWeight: 600,
                  background: isPlaying ? '#e11d48' : '#059669',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 4,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4
                }}
              >
                {isPlaying ? '⏸ Pause' : '▶ Play'}
              </button>
            </div>
          </div>
        )}

        {/* Tab switch */}
        {!collapsed && (
          <div style={{ display: 'flex', gap: 4, background: '#0f172a', padding: 2, borderRadius: 6 }}>
            <button
              onClick={() => handleTabClick('status')}
              style={{
                flex: 1,
                padding: '6px 10px',
                fontSize: 11,
                fontWeight: 600,
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer',
                background: localTab === 'status' ? '#2563eb' : 'transparent',
                color: localTab === 'status' ? '#ffffff' : '#94a3b8'
              }}
            >
              📊 Status & Predictions
            </button>
            <button
              onClick={() => handleTabClick('connection')}
              style={{
                flex: 1,
                padding: '6px 10px',
                fontSize: 11,
                fontWeight: 600,
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer',
                background: localTab === 'connection' ? '#2563eb' : 'transparent',
                color: localTab === 'connection' ? '#ffffff' : '#94a3b8'
              }}
            >
              🔌 How It's Connected
            </button>
          </div>
        )}
      </div>

      {!collapsed && (
        <div style={{ overflowY: 'auto', flex: 1, padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Day slider and Noise Toggle */}
          <div style={{ background: '#1e293b', padding: '10px 12px', borderRadius: 8, border: '1px solid #334155' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: '#cbd5e1' }}>Simulated Day: {currentDay} / 30</span>
              <label style={{ fontSize: 10, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={noiseEnabled}
                  onChange={(e) => {
                    const checked = e.target.checked;
                    projectorSim.setNoiseEnabled(checked);
                    onToggleNoise?.(checked);
                  }}
                  style={{ cursor: 'pointer' }}
                />
                <span>Sensor noise & dropouts</span>
              </label>
            </div>
            <input
              type="range"
              min={0}
              max={30}
              value={currentDay}
              onChange={(e) => onDayChange(parseInt(e.target.value, 10))}
              style={{ width: '100%', accentColor: '#38bdf8', cursor: 'pointer' }}
            />
          </div>

          {/* TAB 1: STATUS & PREDICTIONS */}
          {localTab === 'status' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {PG_PROJECTOR_IDS.map((p) => {
                const pred = predictions[p.deviceId];
                if (!pred) return null;
                const c = stateColors[pred.healthState] ?? stateColors.healthy;
                const fault = faults[p.deviceId] ?? 'none';
                const scores = sparklineData[p.deviceId] ?? [];

                return (
                  <div
                    key={p.deviceId}
                    style={{
                      background: 'rgba(30, 41, 59, 0.7)',
                      border: `1px solid ${pred.healthState === 'failed' ? '#ef4444' : pred.healthState === 'imminent' ? '#f43f5e' : pred.healthState === 'degrading' ? '#d97706' : '#334155'}`,
                      borderRadius: 10,
                      padding: '10px 12px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 8,
                      position: 'relative'
                    }}
                  >
                    {/* Device Header */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span>{p.floorName}</span>
                          <span style={{ fontSize: 10, fontFamily: 'monospace', color: '#94a3b8' }}>({p.deviceId})</span>
                        </div>
                        <div style={{ fontSize: 10, color: '#64748b' }}>IP: {p.ip}:4352 · PJLink Class 2</div>
                      </div>
                      <div
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: 999,
                          background: c.bg,
                          color: c.text,
                          border: `1px solid ${c.border}`
                        }}
                      >
                        {c.label}
                      </div>
                    </div>

                    {/* Metric Row & Sparkline */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#0f172a', padding: '6px 8px', borderRadius: 6 }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                        <div style={{ fontSize: 10, color: '#94a3b8' }}>
                          Health: <span style={{ fontWeight: 700, color: c.text }}>{pred.healthScore}/100</span>
                        </div>
                        <div style={{ fontSize: 10, color: '#94a3b8' }}>
                          Remaining: <span style={{ fontWeight: 700, color: '#f8fafc' }}>{pred.daysRemaining} days</span>
                        </div>
                        <div style={{ fontSize: 10, color: '#94a3b8' }}>
                          Failure Date: <span style={{ fontWeight: 700, color: '#38bdf8' }}>{pred.predictedFailureAt}</span>
                        </div>
                      </div>

                      {/* Health Sparkline (Day 0 to 30) */}
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 2 }}>
                        <span style={{ fontSize: 9, color: '#64748b' }}>Health 0..30d</span>
                        <svg width="100" height="28" style={{ overflow: 'visible' }}>
                          {/* Sparkline curve */}
                          <polyline
                            fill="none"
                            stroke={c.border}
                            strokeWidth="2"
                            points={scores.map((s, idx) => `${(idx / 30) * 100},${26 - (s / 100) * 22}`).join(' ')}
                          />
                          {/* Current day indicator dot */}
                          {scores[currentDay] !== undefined && (
                            <circle
                              cx={(currentDay / 30) * 100}
                              cy={26 - (scores[currentDay] / 100) * 22}
                              r="3.5"
                              fill="#ffffff"
                              stroke={c.border}
                              strokeWidth="2"
                            />
                          )}
                        </svg>
                        <span style={{ fontSize: 9, color: pred.confidence === 'High' ? '#34d399' : '#fbbf24' }}>
                          {pred.confidence} Confidence
                        </span>
                      </div>
                    </div>

                    {/* Telemetry Stats */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: 10, color: '#94a3b8' }}>
                      <div>Lamp: <b style={{ color: '#f1f5f9' }}>{pred.lastReading.lampHours}</b> / {RATED_LAMP_HOURS}h</div>
                      <div>Filter: <b style={{ color: '#f1f5f9' }}>{pred.lastReading.filterHours}</b> / {FILTER_SERVICE_INTERVAL}h</div>
                    </div>

                    {/* Driving Reason and Numbered Contributing Factors */}
                    <div style={{ background: '#0f172a', padding: '6px 8px', borderRadius: 6, border: '1px solid #1e293b' }}>
                      <div style={{ fontSize: 10, fontWeight: 700, color: '#38bdf8', marginBottom: 4 }}>
                        {pred.reasons[0]}
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                        {pred.reasons.slice(1).map((r, i) => (
                          <div key={i} style={{ fontSize: 9.5, color: '#cbd5e1', lineHeight: 1.3 }}>
                            {r}
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Closed-Loop Preventive Work Order */}
                    {pred.workOrder && (
                      <div
                        style={{
                          background: pred.workOrder.isBlocked ? 'rgba(127, 29, 29, 0.4)' : 'rgba(30, 58, 138, 0.4)',
                          border: `1px solid ${pred.workOrder.isBlocked ? '#ef4444' : '#3b82f6'}`,
                          borderRadius: 6,
                          padding: '6px 8px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: 3
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: 10, fontWeight: 700, color: pred.workOrder.isBlocked ? '#fca5a5' : '#93c5fd' }}>
                            🛠️ {pred.workOrder.title} ({pred.workOrder.orderId})
                          </span>
                          <span
                            style={{
                              fontSize: 9,
                              fontWeight: 700,
                              padding: '1px 5px',
                              borderRadius: 4,
                              background: pred.workOrder.isBlocked ? '#ef4444' : '#2563eb',
                              color: '#fff'
                            }}
                          >
                            {pred.workOrder.isBlocked ? 'BLOCKED: STOCK 0' : 'QUEUED'}
                          </span>
                        </div>
                        <div style={{ fontSize: 9.5, color: '#e2e8f0' }}>
                          Part: <b>{pred.workOrder.partName}</b> (In stock: <b>{pred.workOrder.stockCount}</b>)
                        </div>
                        <div style={{ fontSize: 8.5, color: '#cbd5e1', fontStyle: 'italic', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 2 }}>
                          ⚠️ {pred.workOrder.approvalNotice}
                        </div>
                      </div>
                    )}

                    {/* Fault Injection Control */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6, marginTop: 2 }}>
                      <span style={{ fontSize: 10, color: '#94a3b8' }}>Simulate fault:</span>
                      <select
                        value={fault}
                        onChange={(e) => onSetFault(p.deviceId, e.target.value as FaultType)}
                        style={{
                          flex: 1,
                          fontSize: 10,
                          padding: '3px 6px',
                          background: '#1e293b',
                          color: '#f8fafc',
                          border: '1px solid #475569',
                          borderRadius: 4
                        }}
                      >
                        <option value="none">Scripted Pilot Scenario</option>
                        <option value="lamp_wear">Lamp wear (~92% life jump)</option>
                        <option value="dirty_filter">Dirty filter (510h overheat)</option>
                        <option value="fan_fault">Fan fault (bearing failure)</option>
                      </select>
                    </div>
                  </div>
                );
              })}

              {/* CAMPUSOPS DASHBOARD INTEGRATION SECTION */}
              {(() => {
                const targetRoomId = selectedConfig?.roomId ?? 'PG-201';
                const roomOpenReports = dashboardBridge.getOpenReportsForRoom(targetRoomId);
                const lastWarning = dashboardBridge.getLastWarningNotice();

                return (
                  <div style={{ marginTop: 8, padding: '10px 12px', background: '#090d16', borderRadius: 8, border: '1px solid #334155' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                      <span style={{ fontSize: 11, fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 5 }}>
                        <span>🔗</span> CampusOps Dashboard
                      </span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <button
                          onClick={() => window.open('http://localhost:5173', '_blank')}
                          style={{
                            fontSize: 9.5,
                            padding: '3px 8px',
                            borderRadius: 4,
                            background: '#4f46e5',
                            color: '#ffffff',
                            fontWeight: 700,
                            border: 'none',
                            cursor: 'pointer'
                          }}
                          title="Open http://localhost:5173 in a new tab"
                        >
                          Open Dashboard (5173) ↗
                        </button>
                        <span style={{ fontSize: 9.5, padding: '2px 6px', borderRadius: 4, background: '#1e293b', color: '#94a3b8', fontFamily: 'monospace' }}>
                          Room: {targetRoomId}
                        </span>
                      </div>
                    </div>

                    {/* Student Report Simulation Controls */}
                    <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
                      <button
                        onClick={() => dashboardBridge.simulateStudentReport(targetRoomId, 'AV')}
                        style={{
                          flex: 1,
                          padding: '6px 8px',
                          fontSize: 10,
                          fontWeight: 700,
                          background: '#dc2626',
                          color: '#ffffff',
                          border: 'none',
                          borderRadius: 4,
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: 4
                        }}
                        title="Simulate student report for this room"
                      >
                        🚨 Simulate student report (simulated)
                      </button>
                      {roomOpenReports.length > 0 && (
                        <button
                          onClick={() => dashboardBridge.resolveReportsForRoom(targetRoomId)}
                          style={{
                            padding: '6px 10px',
                            fontSize: 10,
                            fontWeight: 700,
                            background: '#16a34a',
                            color: '#ffffff',
                            border: 'none',
                            borderRadius: 4,
                            cursor: 'pointer'
                          }}
                          title="Resolve report"
                        >
                          ✓ Resolve ({roomOpenReports.length})
                        </button>
                      )}
                    </div>

                    {/* Open Reports Status */}
                    {roomOpenReports.length > 0 ? (
                      <div style={{ fontSize: 9.5, color: '#fca5a5', marginBottom: 8, padding: '5px 8px', background: 'rgba(239, 68, 68, 0.18)', borderRadius: 4, border: '1px solid rgba(239, 68, 68, 0.4)' }}>
                        🚨 <b>{roomOpenReports.length} Open Student Report:</b> Needs monitoring (Room {targetRoomId})
                      </div>
                    ) : (
                      <div style={{ fontSize: 9, color: '#64748b', marginBottom: 8 }}>
                        No open student reports for {targetRoomId}. Click button above to simulate.
                      </div>
                    )}

                    {/* Predictive Warning Status & Technician Confirmation Notice */}
                    <div style={{ borderTop: '1px solid #1e293b', paddingTop: 8 }}>
                      {lastWarning ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                          <div style={{ fontSize: 10, color: '#fbbf24', fontWeight: 600 }}>
                            Warning sent to dashboard: {lastWarning.id}, {lastWarning.time}
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <button
                              onClick={() => {
                                navigator.clipboard?.writeText(JSON.stringify(lastWarning.payload, null, 2));
                                setCopiedWarning(true);
                                setTimeout(() => setCopiedWarning(false), 2500);
                              }}
                              style={{
                                padding: '4px 8px',
                                fontSize: 9.5,
                                fontWeight: 600,
                                background: '#334155',
                                color: '#e2e8f0',
                                border: '1px solid #475569',
                                borderRadius: 4,
                                cursor: 'pointer'
                              }}
                            >
                              {copiedWarning ? '✓ Copied to clipboard!' : '📋 Copy warning JSON'}
                            </button>
                            <span style={{ fontSize: 9, color: '#94a3b8' }}>
                              Role: <b>{lastWarning.payload.workerRole}</b> · Mode: <b>{lastWarning.payload.failureMode}</b>
                            </span>
                          </div>
                        </div>
                      ) : (
                        <div style={{ fontSize: 9, color: '#64748b' }}>
                          No warning dispatched yet. Trigger a fault above to dispatch predictive warning.
                        </div>
                      )}

                      {/* Explicit one-line rule notice */}
                      <div style={{ marginTop: 6, fontSize: 8.5, color: '#94a3b8', fontStyle: 'italic', borderLeft: '2px solid #eab308', paddingLeft: 6 }}>
                        ⚠️ Notice: Predictor cannot approve its own warning. The ticket stays a warning until a technician confirms it.
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>
          )}

          {/* TAB 2: HOW IT'S CONNECTED */}
          {localTab === 'connection' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {/* Device Selector */}
              <div style={{ background: '#1e293b', padding: '8px 10px', borderRadius: 8, border: '1px solid #334155' }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 4 }}>Select Projector:</div>
                <select
                  value={localSelectedDev}
                  onChange={(e) => handleDevicePick(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '5px 8px',
                    fontSize: 11,
                    background: '#0f172a',
                    color: '#f8fafc',
                    border: '1px solid #475569',
                    borderRadius: 4
                  }}
                >
                  {PG_PROJECTOR_IDS.map(p => (
                    <option key={p.deviceId} value={p.deviceId}>
                      {p.floorName} — {p.deviceId} ({p.ip})
                    </option>
                  ))}
                </select>
              </div>

              {/* End-to-End Real Architecture Diagram */}
              <div style={{ background: '#1e293b', padding: '10px 12px', borderRadius: 8, border: '1px solid #334155' }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#38bdf8', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span>🌐</span> Real Telemetry Data Pipeline
                </div>
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 6,
                    fontSize: 10,
                    fontFamily: 'monospace',
                    background: '#0f172a',
                    padding: '10px',
                    borderRadius: 6,
                    border: '1px solid #1e293b',
                    lineHeight: 1.4
                  }}
                >
                  <div style={{ color: '#34d399' }}>[Projector LAN Port] : {selectedConfig.ip}:4352</div>
                  <div style={{ color: '#64748b' }}>      │  (PJLink Class 2 / TCP)</div>
                  <div style={{ color: '#cbd5e1' }}>      ▼</div>
                  <div style={{ color: '#38bdf8' }}>[Campus VLAN 10.14.0.0/24]</div>
                  <div style={{ color: '#64748b' }}>      │  (60-second query loop)</div>
                  <div style={{ color: '#cbd5e1' }}>      ▼</div>
                  <div style={{ color: '#fbbf24' }}>[Campus Gateway Daemon: 10.14.0.1]</div>
                  <div style={{ color: '#64748b' }}>      │  (JSON Telemetry via HTTPS)</div>
                  <div style={{ color: '#cbd5e1' }}>      ▼</div>
                  <div style={{ color: '#a78bfa' }}>[CampusOps Maintenance Predictor]</div>
                  <div style={{ color: '#64748b' }}>      │  (Rolling 14-day trend + rules)</div>
                  <div style={{ color: '#cbd5e1' }}>      ▼</div>
                  <div style={{ color: '#f43f5e' }}>[Antigravity 3D Digital Twin & Work Orders]</div>
                </div>
              </div>

              {/* Hardware & Network Spec */}
              <div style={{ background: '#1e293b', padding: '10px 12px', borderRadius: 8, border: '1px solid #334155', fontSize: 10 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#f8fafc', marginBottom: 6 }}>
                  Hardware & Network Identification
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                  <div>Model: <b>Epson EB-L630U WUXGA</b></div>
                  <div>Protocol: <b>PJLink Class 2 (Port 4352)</b></div>
                  <div>IP Address: <b style={{ fontFamily: 'monospace' }}>{selectedConfig.ip}</b></div>
                  <div>MAC: <b style={{ fontFamily: 'monospace' }}>00:26:AB:44:{(selectedConfig.floor * 11 + 10).toString(16).toUpperCase()}:12</b></div>
                  <div>Query Cycle: <b>Every 60 seconds</b></div>
                  <div>Status: <span style={{ color: '#34d399', fontWeight: 700 }}>LIVE SIMULATED</span></div>
                </div>
              </div>

              {/* Live Raw PJLink TX/RX Log */}
              {pjlinkData && (
                <div style={{ background: '#1e293b', padding: '10px 12px', borderRadius: 8, border: '1px solid #334155' }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#34d399', marginBottom: 6, display: 'flex', justifyContent: 'space-between' }}>
                    <span>📡 Live PJLink Raw Exchange (Last 8)</span>
                    <span style={{ fontSize: 9, color: '#94a3b8' }}>TCP 4352</span>
                  </div>
                  <div
                    style={{
                      maxHeight: 160,
                      overflowY: 'auto',
                      fontFamily: 'monospace',
                      fontSize: 9.5,
                      background: '#090d16',
                      padding: 8,
                      borderRadius: 6,
                      border: '1px solid #1e293b',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 4
                    }}
                  >
                    {pjlinkData.exchanges.map((ex, i) => (
                      <div key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: 3 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: '#38bdf8' }}>
                          <span>TX &gt; {ex.cmd}</span>
                          <span style={{ color: '#34d399' }}>RX &lt; {ex.resp}</span>
                        </div>
                        <div style={{ fontSize: 8.5, color: '#64748b' }}>{ex.desc}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Forwarded JSON Payload */}
              {pjlinkData && (
                <div style={{ background: '#1e293b', padding: '10px 12px', borderRadius: 8, border: '1px solid #334155' }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#fbbf24', marginBottom: 6 }}>
                    📦 Forwarded Telemetry JSON Payload
                  </div>
                  <pre
                    style={{
                      fontSize: 9,
                      fontFamily: 'monospace',
                      background: '#090d16',
                      color: '#cbd5e1',
                      padding: 8,
                      borderRadius: 6,
                      overflowX: 'auto',
                      maxHeight: 120,
                      margin: 0
                    }}
                  >
                    {JSON.stringify(pjlinkData.jsonPayload, null, 2)}
                  </pre>
                </div>
              )}

              {/* Signal Origin Classification Table */}
              <div style={{ background: '#1e293b', padding: '10px 12px', borderRadius: 8, border: '1px solid #334155' }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#f8fafc', marginBottom: 6 }}>
                  Signal Classification
                </div>
                <table style={{ width: '100%', fontSize: 9.5, borderCollapse: 'collapse', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #475569', color: '#94a3b8' }}>
                      <th style={{ padding: '3px 0' }}>Signal</th>
                      <th>Source Type</th>
                      <th>Provider</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr style={{ borderBottom: '1px solid #334155' }}>
                      <td style={{ padding: '4px 0', fontFamily: 'monospace' }}>%1LAMP (lampHours)</td>
                      <td style={{ color: '#34d399' }}>Hardware Telemetry</td>
                      <td>Projector Firmware</td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid #334155' }}>
                      <td style={{ padding: '4px 0', fontFamily: 'monospace' }}>%2FILT (filterHours)</td>
                      <td style={{ color: '#34d399' }}>Hardware Telemetry</td>
                      <td>Projector Firmware</td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid #334155' }}>
                      <td style={{ padding: '4px 0', fontFamily: 'monospace' }}>%1ERST (Fan/Temp/Lamp)</td>
                      <td style={{ color: '#34d399' }}>Hardware Status</td>
                      <td>Internal Sensors</td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid #334155' }}>
                      <td style={{ padding: '4px 0', fontFamily: 'monospace' }}>dailyRateHours (6.0 h/d)</td>
                      <td style={{ color: '#fbbf24' }}>Derived Time-Series</td>
                      <td>Campus Gateway</td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid #334155' }}>
                      <td style={{ padding: '4px 0', fontFamily: 'monospace' }}>healthScore (0-100)</td>
                      <td style={{ color: '#a78bfa' }}>Predictor Model</td>
                      <td>Predictor Engine</td>
                    </tr>
                    <tr>
                      <td style={{ padding: '4px 0', fontFamily: 'monospace' }}>predictedFailureAt / WO</td>
                      <td style={{ color: '#f43f5e' }}>Maintenance Rules</td>
                      <td>Closed-Loop Engine</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
