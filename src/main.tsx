import React from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';
import { CampusMap } from './views/CampusMap';
import { TreeTestScene } from './views/TreeTestScene';

const isTreeTest = new URLSearchParams(window.location.search).get('view') === 'tree-test';

function App(){
  if (isTreeTest) return <TreeTestScene />;
  return <main className="shell"><header><div><p className="eyebrow">CAMPUSOPS · DIGITAL TWIN</p><h1>Campus operations, in the world</h1></div><span className="tag">Real OSM footprints · estimated heights</span></header><CampusMap/></main>;
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
