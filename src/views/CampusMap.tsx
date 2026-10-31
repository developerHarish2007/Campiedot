import { lazy, Suspense, useEffect, useState } from 'react';
import { campusApi } from '../api';
import type { CampusMapStatusResponse, Simulation } from '../contracts';
import { nodeStatusStyle, workOrderLabel } from '../adapters/campusMapAdapter';
import { getBlock, getBlockByNodeId, getRoomsForBlock, getRoom, getRoomByNodeIdOrAlias } from '../data/registry/registryService';

const CampusWorld = lazy(() => import('./CampusWorld').then(m => ({ default: m.CampusWorld })));

export function CampusMap(){
 const [snapshot,setSnapshot]=useState<CampusMapStatusResponse|null>(null),[invariants,setInvariants]=useState<Awaited<ReturnType<typeof campusApi.getInvariants>>>([]);
 const [selectedId,setSelectedId]=useState('building-pg'),[simulation,setSimulation]=useState<Simulation|null>(null),[planIndex,setPlanIndex]=useState(0),[message,setMessage]=useState('');
 const [panelOpen, setPanelOpen]=useState(false); // Collapsible drawer closed by default per spec

 // Interior navigation state (URL-synced & shared with 3D world)
 const [interiorMode, setInteriorMode] = useState<'campus' | 'cutaway' | 'diorama'>('campus');
 const [interiorBlockId, setInteriorBlockId] = useState<string>('PG');
 const [interiorRoomId, setInteriorRoomId] = useState<string>('PG-001');

 const selected=snapshot?.nodes.find(n=>n.id===selectedId);const unmappedWayId=selectedId.startsWith('osm-way-')?selectedId.slice('osm-way-'.length):null;const incident=snapshot?.incidents.find(i=>i.affectedNodeIds.length);
 const refresh=async()=>{try{const [s,i]=await Promise.all([campusApi.getMapStatus(),campusApi.getInvariants()]);setSnapshot(s);setInvariants(i);}catch(e){setMessage(e instanceof Error?e.message:'Could not load campus data');}};

 // Parse debug URLs on mount: ?view=cutaway&block=PG or ?view=room&room=PG-101 or ?view=room&room=PG-201&lab=1
 useEffect(() => {
   const params = new URLSearchParams(window.location.search);
   const view = params.get('view');
   const blockParam = params.get('block');
   const roomParam = params.get('room');

   if (view === 'cutaway' && blockParam) {
     const blk = getBlock(blockParam) ?? getBlockByNodeId(blockParam);
     if (blk) {
       console.log(`[interior] entering ${blk.blockId}`);
       setInteriorBlockId(blk.blockId);
       if (blk.nodeId) setSelectedId(blk.nodeId);
       setInteriorMode('cutaway');
     }
   } else if (view === 'room' && roomParam) {
     const r = getRoom(roomParam) ?? getRoomByNodeIdOrAlias(roomParam);
     if (r) {
       console.log(`[interior] entering ${r.blockId}`);
       setInteriorBlockId(r.blockId);
       setInteriorRoomId(r.roomId);
       setInteriorMode('diorama');
     }
   }
 }, []);

 useEffect(()=>{void refresh();const timer=window.setInterval(()=>void refresh(),2500);return()=>clearInterval(timer);},[]);
 const runSimulation=async()=>{if(!incident)return;setMessage('');try{setSimulation(await campusApi.simulate({scenarioId:'classroom-outage-exam',incidentId:incident.id}));setPlanIndex(0);setPanelOpen(true);}catch(e){setMessage(String(e));}};
 const approve=async()=>{if(!simulation)return;try{setSimulation(await campusApi.approve(simulation.simulationId,{actorId:'demo-procurement-approver',reason:'Approve recovery plan',selectedPlanId:simulation.plans[planIndex].id}));setMessage('Approved. Execution remains a separate action.');}catch(e){setMessage(String(e));}};
 const execute=async()=>{if(!simulation)return;try{setSimulation(await campusApi.execute(simulation.simulationId,{actorId:'demo-facilities-admin',reason:'Execute approved recovery plan',selectedPlanId:simulation.plans[planIndex].id,idempotencyKey:`demo-${simulation.simulationId}`}));await refresh();setMessage('Plan executed.');}catch(e){const err=e as Error&{status?:number;reason?:string};setMessage(err.status===409?`409 · Stale simulation: ${err.reason}`:err.message);}};
 const plan=simulation?.plans[planIndex],stale=simulation&&snapshot&&simulation.basedOnGeneratedAt!==snapshot.generatedAt;

 const handleEnterBuilding = (blockId: string) => {
   const blk = getBlock(blockId) ?? getBlockByNodeId(blockId);
   if (!blk) return;
   console.log(`[interior] entering ${blk.blockId}`);
   setInteriorBlockId(blk.blockId);
   setInteriorMode('cutaway');
   const url = new URL(window.location.href);
   url.searchParams.set('view', 'cutaway');
   url.searchParams.set('block', blk.blockId);
   url.searchParams.delete('room');
   url.searchParams.delete('lab');
   window.history.replaceState(null, '', url.toString());
 };

 const selectedBlock = selectedId ? (getBlockByNodeId(selectedId) ?? getBlock(selectedId)) : null;
 const hasRooms = selectedBlock ? getRoomsForBlock(selectedBlock.blockId).length > 0 : false;

 return <section className={`map-layout ${panelOpen ? 'panel-open' : 'panel-collapsed'}`}><div className="map-frame"><Suspense fallback={<div className="world-wrap world-loading"><span>Loading Campus 3D Scene...</span></div>}><CampusWorld snapshot={snapshot} selectedNodeId={selectedId} onSelectNode={(id) => { setSelectedId(id); }} affectedNodeIds={incident?.affectedNodeIds??[]} whatIfNodeIds={plan?.affectedNodeIds??[]} panelOpen={panelOpen} onTogglePanel={() => setPanelOpen(v => !v)} interiorMode={interiorMode} onInteriorModeChange={setInteriorMode} interiorBlockId={interiorBlockId} onInteriorBlockChange={setInteriorBlockId} interiorRoomId={interiorRoomId} onInteriorRoomChange={setInteriorRoomId} onEnterBuilding={handleEnterBuilding}/></Suspense><div className="map-note">Real campus building footprints and roads from OpenStreetMap · estimated heights where OSM tags are missing · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors</a></div></div><aside className={`side-panel ${panelOpen ? 'open' : 'collapsed'}`}><div className="side-panel-header"><p className="eyebrow" style={{margin:0}}>CAMPUS OPERATIONS</p><button className="panel-close-btn" onClick={() => setPanelOpen(false)} title="Close drawer">✕</button></div><h2>{snapshot?.campusName??'SRM Easwari Engineering College'}</h2><p className="muted">{snapshot?.campusId??'srm-easwari-demo'} · live data refresh 2.5s</p><div className="legend">{Object.entries(nodeStatusStyle).map(([k,v])=><span key={k}><i style={{background:v.color}}/>{v.label}</span>)}</div><hr/><p className="eyebrow">SELECTED NODE</p><h3>{selected?.name??(unmappedWayId?'Unmapped OSM footprint':'Loading campus…')}</h3>{unmappedWayId?<p className="muted">OSM way {unmappedWayId} · real footprint imported; building identity is not confirmed in public map data.</p>:<><p>Status: {selected?.status??'—'}</p>{selected?.nodeType==='BUILDING'&&<p>{selected.heightMeters??'—'} m · {selected.floorCount??'—'} floors</p>}{selected?.nodeType==='ROOM'&&<p>Floor {selected.floor} · capacity {selected.capacity}</p>}</>}
 {selectedBlock && hasRooms && (
   <button
     className="enter-building-btn"
     onClick={() => handleEnterBuilding(selectedBlock.blockId)}
     style={{
       marginTop: 12,
       marginBottom: 6,
       width: '100%',
       padding: '10px 14px',
       background: '#15803d',
       color: '#ffffff',
       border: '1px solid #4ade80',
       borderRadius: 6,
       fontWeight: 700,
       fontSize: 13,
       cursor: 'pointer',
       display: 'flex',
       alignItems: 'center',
       justifyContent: 'center',
       gap: 8,
       boxShadow: '0 2px 8px rgba(0,0,0,0.25)',
       transition: 'background 0.15s ease'
     }}
   >
     🚪 Enter {selectedBlock.displayName}
   </button>
 )}
 {incident&&<><hr/><p className="eyebrow">INCIDENT BLAST RADIUS</p><p>{incident.title}</p><small>{incident.affectedNodeIds.length} affected nodes · {incident.allowedActions.join(', ')}</small>{incident.workOrders.map(wo=><div className="card" key={wo.id}><b>{wo.id} · {workOrderLabel[wo.state]}</b><p>{wo.assignedStaffName} · {wo.blockedReason}</p>{wo.assignmentScore&&<small>Skill {wo.assignmentScore.skill} · availability {wo.assignmentScore.availability} · workload {wo.assignmentScore.workload} · SLA {wo.assignmentScore.sla}</small>}</div>)}</>}
 <hr/><p className="eyebrow">BOOKINGS · INVENTORY · PROVE</p>{snapshot?.bookings.map(b=><div className="card" key={b.id}><b>{b.title}</b><p>{snapshot.nodes.find(n=>n.id===b.roomNodeId)?.name} · {new Date(b.startsAt).toLocaleTimeString([], {hour:'numeric',minute:'2-digit'})} · {b.status}</p><small>Alternative: B204</small></div>)}{snapshot?.parts.map(p=><p key={p.sku}>{p.name}: available {p.availableQty} · reserved {p.reservedQty}</p>)}{invariants.map(i=><p key={i.name} className={i.status==='fail'?'fault':'good'}>{i.status} · {i.name}{i.reason?` — ${i.reason}`:''}</p>)}
 <hr/><p className="eyebrow">WHAT-IF · READ ONLY</p>{!simulation?<button onClick={runSimulation}>Simulate classroom outage</button>:<><div className="plan-switch"><button onClick={()=>setPlanIndex(0)} aria-pressed={planIndex===0}>Plan A</button><button onClick={()=>setPlanIndex(1)} aria-pressed={planIndex===1}>Plan B</button></div><div className="card overlay"><b>{plan?.label} · proposal overlay</b><p>{plan?.summary}</p>{plan?.relocations.map(r=><small key={r.bookingId}>Move {r.bookingId}: {r.fromNodeId} → {r.toNodeId}<br/></small>)}<p>{plan?.impact.estimatedResolutionMinutes} min · {plan?.impact.slaAtRiskCount} SLA at risk</p></div><p className="muted">{stale?'STALE · re-simulate':simulation.status} · based on {simulation.basedOnGeneratedAt}</p>{simulation.status==='PENDING_APPROVAL'&&incident?.allowedActions.includes('APPROVE')&&<button onClick={approve}>Approve plan</button>}{simulation.status==='APPROVED'&&incident?.allowedActions.includes('EXECUTE')&&<button onClick={execute}>Execute plan</button>}<button className="secondary" onClick={()=>{campusApi.enableStaleDemo();setMessage('Next execute will return a stale-state 409.');}}>Demo stale response</button></>}{message&&<div className={message.startsWith('409')?'error':'notice'}>{message}</div>}
 </aside></section>;
}
