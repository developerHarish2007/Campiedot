import { useEffect, useRef, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { Tree, TreePreset } from '@dgreenheck/ez-tree';

export function createProceduralPalm(): { branches: THREE.BufferGeometry; leaves: THREE.BufferGeometry } {
  // Trunk: slender curved coconut palm
  const trunkCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0, 0, 0),
    new THREE.Vector3(0.4, 4, 0.2),
    new THREE.Vector3(0.9, 9, 0.5),
    new THREE.Vector3(1.3, 14, 0.8),
  ]);
  const trunkGeo = new THREE.TubeGeometry(trunkCurve, 20, 0.38, 8, false);

  // Fronds: 16 arching palm fronds
  const frondCount = 16;
  const leafGeos: THREE.BufferGeometry[] = [];

  for (let i = 0; i < frondCount; i++) {
    const angle = (i / frondCount) * Math.PI * 2 + (i % 2 === 0 ? 0.08 : -0.08);
    const droop = 0.55 + (i % 3) * 0.12;
    const length = 4.8 + (i % 2) * 0.6;

    const top = new THREE.Vector3(1.3, 14, 0.8);
    const mid = new THREE.Vector3(
      top.x + Math.cos(angle) * (length * 0.5),
      top.y + 0.9,
      top.z + Math.sin(angle) * (length * 0.5)
    );
    const tip = new THREE.Vector3(
      top.x + Math.cos(angle) * length,
      top.y - droop * 2.2,
      top.z + Math.sin(angle) * length
    );

    const spine = new THREE.CatmullRomCurve3([top, mid, tip]);
    const segments = 10;
    const pts = spine.getPoints(segments);

    const verts: number[] = [];
    const uvs: number[] = [];
    const indices: number[] = [];

    for (let s = 0; s <= segments; s++) {
      const p = pts[s];
      const t = s / segments;
      const width = Math.sin(t * Math.PI) * 0.85 + 0.12;
      const normal = new THREE.Vector3(-Math.sin(angle), 0, Math.cos(angle)).normalize();

      verts.push(p.x - normal.x * width, p.y, p.z - normal.z * width);
      verts.push(p.x + normal.x * width, p.y, p.z + normal.z * width);
      uvs.push(0, t, 1, t);

      if (s < segments) {
        const base = s * 2;
        indices.push(base, base + 1, base + 2);
        indices.push(base + 1, base + 3, base + 2);
      }
    }

    const frondGeo = new THREE.BufferGeometry();
    frondGeo.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3));
    frondGeo.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
    frondGeo.setIndex(indices);
    frondGeo.computeVertexNormals();
    leafGeos.push(frondGeo);
  }

  // Merge leaf geometries
  let totalVerts = 0, totalIndices = 0;
  leafGeos.forEach(g => {
    totalVerts += g.attributes.position.count;
    totalIndices += g.index ? g.index.count : 0;
  });

  const pos = new Float32Array(totalVerts * 3);
  const uv = new Float32Array(totalVerts * 2);
  const norm = new Float32Array(totalVerts * 3);
  const indices = new Uint32Array(totalIndices);

  let vOffset = 0, iOffset = 0, indexVertexOffset = 0;
  leafGeos.forEach(g => {
    pos.set(g.attributes.position.array as Float32Array, vOffset * 3);
    if (g.attributes.uv) uv.set(g.attributes.uv.array as Float32Array, vOffset * 2);
    if (g.attributes.normal) norm.set(g.attributes.normal.array as Float32Array, vOffset * 3);

    if (g.index) {
      const idx = g.index.array;
      for (let j = 0; j < idx.length; j++) indices[iOffset + j] = idx[j] + indexVertexOffset;
      iOffset += idx.length;
    }
    indexVertexOffset += g.attributes.position.count;
    vOffset += g.attributes.position.count;
  });

  const mergedLeaves = new THREE.BufferGeometry();
  mergedLeaves.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  mergedLeaves.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  mergedLeaves.setAttribute('normal', new THREE.BufferAttribute(norm, 3));
  mergedLeaves.setIndex(new THREE.BufferAttribute(indices, 1));

  return { branches: trunkGeo, leaves: mergedLeaves };
}

interface TreeParams {
  presetName: string;
  leafScale: number;
  leafCount: number;
  leafColor: string;
  alphaTest: number;
}

// Pre-load bark textures once
const texLoader = new THREE.TextureLoader();
function loadBarkTextures() {
  const diff = texLoader.load('/assets/textures/bark_brown_01/bark_brown_01_diff_1k.jpg');
  diff.colorSpace = THREE.SRGBColorSpace;
  diff.wrapS = THREE.RepeatWrapping;
  diff.wrapT = THREE.RepeatWrapping;
  diff.repeat.set(1, 6);

  const nor = texLoader.load('/assets/textures/bark_brown_01/bark_brown_01_nor_gl_1k.jpg');
  nor.wrapS = THREE.RepeatWrapping;
  nor.wrapT = THREE.RepeatWrapping;
  nor.repeat.set(1, 6);

  const rough = texLoader.load('/assets/textures/bark_brown_01/bark_brown_01_rough_1k.jpg');
  rough.wrapS = THREE.RepeatWrapping;
  rough.wrapT = THREE.RepeatWrapping;
  rough.repeat.set(1, 6);

  const ao = texLoader.load('/assets/textures/bark_brown_01/bark_brown_01_ao_1k.jpg');
  ao.wrapS = THREE.RepeatWrapping;
  ao.wrapT = THREE.RepeatWrapping;
  ao.repeat.set(1, 6);

  return { diff, nor, rough, ao };
}

const barkTextures = loadBarkTextures();

function InnerTree({ params, onStats }: { params: TreeParams; onStats: (stats: any) => void }) {
  const groupRef = useRef<THREE.Group>(null);

  useEffect(() => {
    if (!groupRef.current) return;
    const group = groupRef.current;

    while (group.children.length > 0) {
      const c = group.children[0] as any;
      group.remove(c);
      if (c.geometry) c.geometry.dispose();
      if (c.material) {
        if (Array.isArray(c.material)) c.material.forEach((m: any) => m.dispose());
        else c.material.dispose();
      }
    }

    if (params.presetName === 'Palm') {
      const palm = createProceduralPalm();
      if (palm.branches.attributes.uv && !palm.branches.attributes.uv2) {
        palm.branches.setAttribute('uv2', palm.branches.attributes.uv.clone());
      }
      const trunkMat = new THREE.MeshStandardMaterial({
        map: barkTextures.diff,
        normalMap: barkTextures.nor,
        roughnessMap: barkTextures.rough,
        aoMap: barkTextures.ao,
        aoMapIntensity: 1.0,
        color: '#8b6c4b',
        roughness: 0.92,
      });
      const leafMat = new THREE.MeshStandardMaterial({
        color: params.leafColor,
        roughness: 0.65,
        side: THREE.DoubleSide,
      });
      const trunkMesh = new THREE.Mesh(palm.branches, trunkMat);
      trunkMesh.castShadow = true;
      trunkMesh.receiveShadow = true;
      const leafMesh = new THREE.Mesh(palm.leaves, leafMat);
      leafMesh.castShadow = true;
      leafMesh.receiveShadow = true;
      group.add(trunkMesh);
      group.add(leafMesh);
      onStats({
        branchTris: palm.branches.index ? palm.branches.index.count / 3 : 0,
        leafTris: palm.leaves.index ? palm.leaves.index.count / 3 : 0,
        hasLeaves: true,
      });
      return;
    }

    const rawPreset = (TreePreset as any)[params.presetName];
    if (!rawPreset) return;
    const preset = structuredClone(rawPreset);

    preset.leaves.size = params.leafScale;
    preset.leaves.count = params.leafCount;
    preset.leaves.alphaTest = params.alphaTest;

    const tree = new Tree();
    tree.options.copy(preset);
    tree.generate();

    const branchesMesh = tree.branchesMesh;
    const leavesMesh = tree.leavesMesh;
    const origMat = leavesMesh.material as THREE.MeshPhongMaterial;

    const leafTex = origMat.map;
    if (leafTex) {
      leafTex.colorSpace = THREE.SRGBColorSpace;
      leafTex.needsUpdate = true;
    }

    const leafMat = new THREE.MeshStandardMaterial({
      map: leafTex,
      color: new THREE.Color(params.leafColor),
      alphaTest: params.alphaTest,
      alphaToCoverage: true,
      transparent: false,
      depthWrite: true,
      side: THREE.DoubleSide,
      roughness: 0.78,
      metalness: 0.02,
    });

    leavesMesh.material = leafMat;
    leavesMesh.castShadow = true;
    leavesMesh.receiveShadow = true;

    // Attach uv2 for ambient occlusion
    if (branchesMesh.geometry.attributes.uv && !branchesMesh.geometry.attributes.uv2) {
      branchesMesh.geometry.setAttribute('uv2', branchesMesh.geometry.attributes.uv.clone());
    }

    const barkMat = new THREE.MeshStandardMaterial({
      map: barkTextures.diff,
      normalMap: barkTextures.nor,
      roughnessMap: barkTextures.rough,
      aoMap: barkTextures.ao,
      aoMapIntensity: 1.0,
      roughness: 0.92,
      metalness: 0.02,
    });
    branchesMesh.material = barkMat;
    branchesMesh.castShadow = true;
    branchesMesh.receiveShadow = true;

    group.add(branchesMesh);
    group.add(leavesMesh);

    onStats({
      branchTris: branchesMesh.geometry.index ? branchesMesh.geometry.index.count / 3 : 0,
      leafTris: leavesMesh.geometry.index ? leavesMesh.geometry.index.count / 3 : 0,
      hasLeaves: (leavesMesh.geometry.attributes.position?.count ?? 0) > 0,
    });
  }, [params]);

  return <group ref={groupRef} />;
}

export function TreeTestScene() {
  const searchParams = new URLSearchParams(window.location.search);
  const urlPreset = searchParams.get('preset') ?? 'Oak Medium';
  const urlCamera = searchParams.get('camera') ?? 'ground';

  const [cameraMode, setCameraMode] = useState<'ground' | 'aerial' | 'overview'>(
    urlCamera === 'aerial' ? 'aerial' : urlCamera === 'overview' ? 'overview' : 'ground'
  );

  const [params, setParams] = useState<TreeParams>({
    presetName: urlPreset,
    leafScale: 3.4,
    leafCount: 42,
    leafColor: urlPreset === 'Palm' ? '#3d7828' : '#427330',
    alphaTest: 0.2,
  });

  const [stats, setStats] = useState({ branchTris: 0, leafTris: 0, hasLeaves: false });

  // Camera config based on mode
  const camConfig = cameraMode === 'ground'
    ? { position: [12.0, 2.0, 16.0] as [number, number, number], target: [0, 6.0, 0] as [number, number, number], fov: 50 }
    : cameraMode === 'aerial'
      ? { position: [30.0, 32.0, 38.0] as [number, number, number], target: [0, 10.0, 0] as [number, number, number], fov: 45 }
      : { position: [0, 12, 28] as [number, number, number], target: [0, 8.0, 0] as [number, number, number], fov: 42 };

  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative', background: '#98b9da' }}>
      <Canvas
        key={cameraMode}
        camera={{ position: camConfig.position, fov: camConfig.fov }}
        shadows
        gl={{ toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.05 }}
        onCreated={({ scene }) => { (window as any).__SCENE__ = scene; }}
      >
        <ambientLight intensity={0.7} />
        <directionalLight
          position={[25, 45, 25]}
          intensity={2.2}
          castShadow
          shadow-mapSize={[2048, 2048]}
          shadow-bias={-0.0004}
          shadow-camera-near={1}
          shadow-camera-far={110}
          shadow-camera-left={-25}
          shadow-camera-right={25}
          shadow-camera-top={35}
          shadow-camera-bottom={-5}
        />
        <directionalLight position={[-20, 20, -20]} intensity={0.5} color="#d0e5f5" />

        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow>
          <planeGeometry args={[100, 100]} />
          <meshStandardMaterial color="#4f6e3c" roughness={0.92} />
        </mesh>

        <InnerTree params={params} onStats={setStats} />

        <OrbitControls makeDefault target={camConfig.target} minDistance={2} maxDistance={90} />
      </Canvas>

      <div style={{
        position: 'absolute',
        top: 20,
        left: 20,
        background: 'rgba(18, 24, 32, 0.9)',
        color: '#f0f4f8',
        padding: '16px 20px',
        borderRadius: 8,
        maxWidth: 340,
        fontFamily: 'monospace',
        fontSize: 13,
        boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
      }}>
        <h3 style={{ margin: '0 0 10px', fontSize: 16, color: '#68d391' }}>Tree Canopy Verification</h3>

        <div style={{ marginBottom: 12, display: 'flex', gap: 6 }}>
          <button
            onClick={() => setCameraMode('ground')}
            style={{
              flex: 1,
              padding: '6px 8px',
              background: cameraMode === 'ground' ? '#3182ce' : '#2d3748',
              color: '#fff',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              fontWeight: cameraMode === 'ground' ? 'bold' : 'normal',
            }}
          >
            Ground View
          </button>
          <button
            onClick={() => setCameraMode('aerial')}
            style={{
              flex: 1,
              padding: '6px 8px',
              background: cameraMode === 'aerial' ? '#3182ce' : '#2d3748',
              color: '#fff',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              fontWeight: cameraMode === 'aerial' ? 'bold' : 'normal',
            }}
          >
            Aerial View
          </button>
        </div>

        <h3 style={{ margin: '0 0 10px', fontSize: 16, color: '#68d391' }}>Tree Canopy Verification</h3>

        <div style={{ marginBottom: 10 }}>
          <label>Tree Variety: </label>
          <select
            value={params.presetName}
            onChange={e => setParams(p => ({ ...p, presetName: e.target.value }))}
            style={{ background: '#2d3748', color: '#fff', padding: 4, borderRadius: 4, border: '1px solid #4a5568' }}
          >
            {['Oak Medium', 'Oak Small', 'Oak Large', 'Aspen Medium', 'Ash Medium', 'Pine Medium', 'Palm'].map(p => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>

        {params.presetName !== 'Palm' && (
          <>
            <div style={{ marginBottom: 8 }}>
              <label>Canopy Foliage Size ({params.leafScale}): </label>
              <input
                type="range"
                min={1.5}
                max={5.5}
                step={0.1}
                value={params.leafScale}
                onChange={e => setParams(p => ({ ...p, leafScale: parseFloat(e.target.value) }))}
                style={{ width: '100%' }}
              />
            </div>

            <div style={{ marginBottom: 8 }}>
              <label>Leaf Density ({params.leafCount}): </label>
              <input
                type="range"
                min={16}
                max={72}
                step={2}
                value={params.leafCount}
                onChange={e => setParams(p => ({ ...p, leafCount: parseInt(e.target.value) }))}
                style={{ width: '100%' }}
              />
            </div>

            <div style={{ marginBottom: 8 }}>
              <label>Alpha Cutout ({params.alphaTest}): </label>
              <input
                type="range"
                min={0.05}
                max={0.6}
                step={0.05}
                value={params.alphaTest}
                onChange={e => setParams(p => ({ ...p, alphaTest: parseFloat(e.target.value) }))}
                style={{ width: '100%' }}
              />
            </div>
          </>
        )}

        <div style={{ marginBottom: 10 }}>
          <label>Canopy Tint: </label>
          <input
            type="color"
            value={params.leafColor}
            onChange={e => setParams(p => ({ ...p, leafColor: e.target.value }))}
            style={{ verticalAlign: 'middle', marginLeft: 8 }}
          />
          <span style={{ marginLeft: 8 }}>{params.leafColor}</span>
        </div>

        <div style={{ borderTop: '1px solid #4a5568', paddingTop: 8, fontSize: 12 }}>
          <div>Branch triangles: {stats.branchTris.toLocaleString()}</div>
          <div>Leaf triangles: {stats.leafTris.toLocaleString()}</div>
          <div>Canopy Status: <b style={{ color: stats.hasLeaves ? '#68d391' : '#fc8181' }}>{stats.hasLeaves ? 'Full Leafy Canopy' : 'Bare'}</b></div>
          <div style={{ color: '#a0aec0', marginTop: 4 }}>Light shines through leaf gaps with soft sun shadows.</div>
        </div>
      </div>
    </div>
  );
}
