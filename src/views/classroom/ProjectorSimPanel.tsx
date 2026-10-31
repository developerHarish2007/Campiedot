import React, { useState } from 'react';
import {
  PG_PROJECTOR_IDS,
  FaultType,
  RATED_LAMP_HOURS,
  FILTER_SERVICE_INTERVAL
} from '../../sim/projectorSim';
import { DevicePrediction } from '../../sim/projectorPredictor';

interface SimPanelProps {
  currentDay: number;
  onDayChange: (day: number) => void;
  predictions: Record<string, DevicePrediction>;
  faults: Record<string, FaultType>;
  onSetFault: (deviceId: string, fault: FaultType) => void;
  onReset: () => void;
}

export function ProjectorSimPanel({
  currentDay,
  onDayChange,
  predictions,
  faults,
  onSetFault,
  onReset
}: SimPanelProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div
      className="projector-sim-panel"
      style={{
        position: 'absolute',
        top: 60,
        right: 18,
        width: 340,
        maxHeight: 'calc(100vh - 140px)',
        background: 'rgba(15, 23, 42, 0.94)',
        backdropFilter: 'blur(12px)',
        border: '1px solid #334155',
        borderRadius: 12,
        boxShadow: '0 12px 32px rgba(0, 0, 0, 0.55)',
        color: '#f8fafc',
        zIndex: 120,
        display: 'flex',
        flexDirection: 'column',
        fontFamily: 'Inter, system-ui, sans-serif',
        overflow: 'hidden',
        pointerEvents: 'auto'
      }}
    >
      {/* Panel Header */}
      <div
        style={{
          padding: '12px 14px',
          borderBottom: '1px solid #334155',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(30, 41, 59, 0.7)'
        }}
      >
        <div>
          <div style={{ fontWeight: 700, fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
            <span>📽️</span> Projector Maintenance Sim
          </div>
          <div style={{ fontSize: 11, color: '#94a3b8' }}>
            Predictive model (rules + trend)
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            onClick={onReset}
            title="Reset faults and day slider"
            style={{
              padding: '4px 8px',
              fontSize: 11,
              background: '#334155',
              color: '#f8fafc',
              border: '1px solid #475569',
              borderRadius: 4,
              cursor: 'pointer'
            }}
          >
            Reset
          </button>
          <button
            onClick={() => setCollapsed(v => !v)}
            style={{
              padding: '4px 8px',
              fontSize: 11,
              background: 'transparent',
              color: '#cbd5e1',
              border: '1px solid #475569',
              borderRadius: 4,
              cursor: 'pointer'
            }}
          >
            {collapsed ? '▼' : '▲'}
          </button>
        </div>
      </div>

      {!collapsed && (
        <div style={{ padding: '12px 14px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Day Slider */}
          <div style={{ background: '#1e293b', padding: '10px 12px', borderRadius: 8, border: '1px solid #334155' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 6 }}>
              <span style={{ fontWeight: 600 }}>Simulated Day</span>
              <span style={{ color: '#38bdf8', fontWeight: 700 }}>Day {currentDay} / 30</span>
            </div>
            <input
              type="range"
              min="0"
              max="30"
              value={currentDay}
              onChange={e => onDayChange(Number(e.target.value))}
              style={{ width: '100%', accentColor: '#38bdf8', cursor: 'pointer' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#64748b', marginTop: 2 }}>
              <span>Day 0 (Base)</span>
              <span>Day 15</span>
              <span>Day 30</span>
            </div>
          </div>

          {/* Projectors List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              PG Smart Labs (5 Projectors)
            </div>

            {PG_PROJECTOR_IDS.map(p => {
              const pred = predictions[p.deviceId];
              const fault = faults[p.deviceId] ?? 'none';
              const state = pred?.healthState ?? 'healthy';

              const stateColor =
                state === 'failed' ? '#ef4444' :
                state === 'imminent' ? '#f97316' :
                state === 'degrading' ? '#eab308' : '#22c55e';

              const stateBg =
                state === 'failed' ? 'rgba(239, 68, 68, 0.18)' :
                state === 'imminent' ? 'rgba(249, 115, 22, 0.18)' :
                state === 'degrading' ? 'rgba(234, 179, 8, 0.18)' : 'rgba(34, 197, 94, 0.18)';

              return (
                <div
                  key={p.deviceId}
                  style={{
                    background: '#1e293b',
                    border: `1px solid ${state === 'imminent' || state === 'failed' ? stateColor : '#334155'}`,
                    borderRadius: 8,
                    padding: '10px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 6
                  }}
                >
                  {/* Top Bar: Room & Health */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontWeight: 700, fontSize: 13 }}>{p.roomId}</span>
                      <span style={{ fontSize: 10, color: '#64748b' }}>{p.deviceId}</span>
                    </div>
                    <span
                      style={{
                        padding: '2px 8px',
                        fontSize: 10,
                        fontWeight: 700,
                        borderRadius: 12,
                        color: stateColor,
                        background: stateBg,
                        border: `1px solid ${stateColor}`
                      }}
                    >
                      {state.toUpperCase()} · {pred?.healthScore ?? 100}%
                    </span>
                  </div>

                  {/* Fault Dropdown */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ fontSize: 11, color: '#94a3b8', minWidth: 64 }}>Fault:</span>
                    <select
                      value={fault}
                      onChange={e => onSetFault(p.deviceId, e.target.value as FaultType)}
                      style={{
                        flex: 1,
                        background: '#0f172a',
                        color: '#f8fafc',
                        border: '1px solid #475569',
                        borderRadius: 4,
                        padding: '3px 6px',
                        fontSize: 11
                      }}
                    >
                      <option value="none">Normal operation</option>
                      <option value="lamp_wear">Lamp wear (~92% life)</option>
                      <option value="dirty_filter">Dirty filter (Overheat) [ASSUMED]</option>
                      <option value="fan_fault">Fan fault (Degrading) [ASSUMED]</option>
                    </select>
                  </div>

                  {/* Metrics Row */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#cbd5e1', marginTop: 2 }}>
                    <span>Lamp: <b>{pred?.lastReading?.lampHours ?? p.baseLampHours}</b>/{RATED_LAMP_HOURS}h</span>
                    <span>Filter: <b>{pred?.lastReading?.filterHours ?? p.baseFilterHours}</b>/{FILTER_SERVICE_INTERVAL}h</span>
                  </div>

                  {/* Prediction summary */}
                  <div style={{ fontSize: 11, color: '#e2e8f0', background: '#0f172a', padding: '6px 8px', borderRadius: 4 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                      <span style={{ color: '#94a3b8' }}>Est. Failure:</span>
                      <span style={{ fontWeight: 600, color: stateColor }}>{pred?.predictedFailureAt ?? '—'}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#94a3b8' }}>Confidence:</span>
                      <span style={{ textTransform: 'capitalize', color: pred?.confidence === 'high' ? '#38bdf8' : '#fbbf24' }}>
                        {pred?.confidence ?? 'high'}
                      </span>
                    </div>
                    {pred?.reasons && pred.reasons.length > 0 && (
                      <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 4, borderTop: '1px solid #1e293b', paddingTop: 4 }}>
                        • {pred.reasons[0]}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
