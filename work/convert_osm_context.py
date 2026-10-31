import xml.etree.ElementTree as ET, json, math, re
from pathlib import Path

source = Path('work/osm-surroundings.osm')
root = ET.parse(source).getroot()
base = json.loads(Path('public/data/osm-campus.json').read_text(encoding='utf-8'))
origin = base['origin']
lat0, lon0 = origin['lat'], origin['lon']

def local_xy(lat, lon):
    return {
        'x': round(6378137 * math.radians(lon - lon0) * math.cos(math.radians(lat0)), 3),
        'z': round(6378137 * math.radians(lat0 - lat), 3),
    }

def inside(point, ring):
    x, z = point['x'], point['z']
    hit = False
    j = len(ring) - 1
    for i, a in enumerate(ring):
        b = ring[j]
        if (a['z'] > z) != (b['z'] > z) and x < (b['x'] - a['x']) * (z - a['z']) / (b['z'] - a['z']) + a['x']:
            hit = not hit
        j = i
    return hit

nodes = {n.attrib['id']: (float(n.attrib['lat']), float(n.attrib['lon'])) for n in root.findall('node')}
existing_ids = {str(b['osmWayId']) for b in base['buildings']}
boundary = base['campusBoundary']['footprint']
buildings, roads, landcover = [], [], []
counts = {'buildings': 0, 'roads': 0, 'landuse': 0, 'natural': 0, 'leisure': 0, 'individualTreeNodes': 0}
for way in root.findall('way'):
    tags = {t.attrib['k']: t.attrib['v'] for t in way.findall('tag')}
    refs = [n.attrib['ref'] for n in way.findall('nd')]
    coords = [local_xy(*nodes[ref]) for ref in refs if ref in nodes]
    closed = len(refs) > 3 and refs[0] == refs[-1] and len(coords) >= 4
    wid = int(way.attrib['id'])
    if 'building' in tags and tags['building'] not in ('no', 'construction') and closed:
        counts['buildings'] += 1
        ring = coords[:-1]
        center = {'x': round(sum(p['x'] for p in ring) / len(ring), 3), 'z': round(sum(p['z'] for p in ring) / len(ring), 3)}
        if str(wid) not in existing_ids and not inside(center, boundary):
            xs, zs = [p['x'] for p in ring], [p['z'] for p in ring]
            raw_height = tags.get('height', '')
            height_match = re.search(r'\d+(?:\.\d+)?', raw_height)
            levels_match = re.search(r'\d+(?:\.\d+)?', tags.get('building:levels', ''))
            height = float(height_match.group(0)) if height_match else (float(levels_match.group(0)) * 3.2 if levels_match else None)
            if height is None:
                kind = tags.get('building', '')
                height = {'house': 6.4, 'residential': 6.4, 'apartments': 10.0, 'commercial': 8.0, 'industrial': 7.0}.get(kind, 6.4)
            buildings.append({
                'osmWayId': wid, 'tags': tags, 'footprint': coords, 'centroid': center,
                'widthMeters': round(max(xs) - min(xs), 2), 'depthMeters': round(max(zs) - min(zs), 2),
                'heightMeters': round(height, 2), 'heightSource': 'osm_tag' if height_match or levels_match else 'estimated_context_height'
            })
    if 'highway' in tags and len(coords) >= 2:
        roads.append({'osmWayId': wid, 'tags': tags, 'points': coords})
        counts['roads'] += 1
    if closed and any(k in tags for k in ('landuse', 'natural', 'leisure', 'sport')):
        counts['landuse'] += int('landuse' in tags)
        counts['natural'] += int('natural' in tags)
        counts['leisure'] += int('leisure' in tags)
        landcover.append({'osmWayId': wid, 'tags': tags, 'footprint': coords})

tree_nodes = []
for node in root.findall('node'):
    tags = {t.attrib['k']: t.attrib['v'] for t in node.findall('tag')}
    if tags.get('natural') == 'tree':
        tree_nodes.append({'osmNodeId': int(node.attrib['id']), 'tags': tags, 'position': local_xy(float(node.attrib['lat']), float(node.attrib['lon']))})

out = {
    'attribution': '© OpenStreetMap contributors',
    'sourceUrl': 'https://api.openstreetmap.org/api/0.6/map?bbox=80.1755,13.0300,80.1830,13.0370',
    'retrievedAt': '2026-10-30', 'origin': origin,
    'bbox': {'south': 13.0300, 'west': 80.1755, 'north': 13.0370, 'east': 80.1830},
    'statistics': {**counts, 'contextBuildingsOutsideCampus': len(buildings), 'contextRoads': len(roads), 'landcoverAreas': len(landcover), 'taggedTreeNodes': len(tree_nodes)},
    'buildings': buildings, 'roads': roads, 'landcover': landcover, 'individualTrees': tree_nodes
}
Path('public/data/osm-surroundings.json').write_text(json.dumps(out, separators=(',', ':')), encoding='utf-8')
print(json.dumps(out['statistics'], indent=2))
print('landcover:', [(a['osmWayId'], {k:a['tags'].get(k) for k in ('name','landuse','natural','leisure') if k in a['tags']}) for a in landcover])

