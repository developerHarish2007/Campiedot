import { Canvas } from '@react-three/fiber';
import { OrbitControls, Text } from '@react-three/drei';

type Props={name:string;capacity:number;equipment:{id:string;name:string;equipmentType:string;status:string}[];onExit:()=>void};
function Seat({position}:{position:[number,number,number]}){return <group position={position}><mesh position={[0,.22,0]}><boxGeometry args={[.62,.08,.48]}/><meshStandardMaterial color="#a9bfd2"/></mesh><mesh position={[0,.42,-.2]}><boxGeometry args={[.62,.42,.06]}/><meshStandardMaterial color="#7892a9"/></mesh><mesh position={[0,-.02,0]}><boxGeometry args={[.06,.38,.06]}/><meshStandardMaterial color="#596b7b"/></mesh></group>}
function Scene({name,capacity,equipment}:{name:string;capacity:number;equipment:Props['equipment']}){const cols=Math.max(4,Math.ceil(Math.sqrt(capacity*1.45))),rows=Math.ceil(capacity/cols);return <>
 <color attach="background" args={['#111a23']}/><ambientLight intensity={1.6}/><directionalLight position={[5,9,5]} intensity={2}/>
 <mesh rotation={[-Math.PI/2,0,0]} position={[0,-.08,0]}><planeGeometry args={[cols*1.25+5,rows*1.15+7]}/><meshStandardMaterial color="#45534f"/></mesh>
 <mesh position={[0,2,-rows*.58-1]}><boxGeometry args={[cols*1.25+5,4,.14]}/><meshStandardMaterial color="#d6d3c8"/></mesh>
 <mesh position={[0,2,-rows*.58-0.9]}><boxGeometry args={[3,1.15,.08]}/><meshStandardMaterial color="#3b7e96"/></mesh>
 {Array.from({length:capacity},(_,i)=>{const x=(i%cols-(cols-1)/2)*1.15,z=Math.floor(i/cols)*1.05;return <Seat key={i} position={[x,0,z]}/>})}
 {equipment.map((e,i)=><group key={e.id} position={[(i-equipment.length/2)*1.2,1.5,rows*.55+1]}><mesh><boxGeometry args={[.5,.25,.32]}/><meshStandardMaterial color={e.status==='FAULTY'?'#f05e63':'#7fc9a4'} emissive={e.status==='FAULTY'?'#7b1019':'#143f2b'} emissiveIntensity={.4}/></mesh><Text position={[0,.42,0]} fontSize={.2} color="white" anchorX="center">{e.name}</Text></group>)}
 <Text position={[0,4,-rows*.58-1]} fontSize={.4} color="white" anchorX="center">{name}</Text><OrbitControls makeDefault target={[0,0,0]}/>
 </>}
export function RoomInterior(props:Props){return <div className="room-view"><Canvas camera={{position:[7,7,9],fov:48}}><Scene {...props}/></Canvas><div className="room-hud"><div><b>{props.name}</b><small>{props.capacity} seats · procedural interior</small></div><button onClick={props.onExit}>← Campus</button></div><div className="room-legend">Seat layout generated from room capacity · equipment icons from room record · red = faulty</div></div>}
