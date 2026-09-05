"""Approximate landmarks + optional handmade assets in assets/landmarks/.

Artworks are never copied: placeholders only.
"""

from __future__ import annotations

from typing import Optional, Tuple

import bpy

from .bpy_utils import assign_material, collection, empty_marker, link_object, new_mesh_object
from .config import LandmarkSpec, LocationConfig
from .coordinates import CRS, drop_closing, longest_edge_dir, point_in_ring
from .dem import TerrainSampler
from .osm import OsmData, way_centroid
from .paths import landmark_assets_dir


def _resolve_position(spec: LandmarkSpec, osm: OsmData) -> Optional[Tuple[float, float, str]]:
    # Exact name wins over substrings, preventing ticket offices / annexes being used.
    hints={h.casefold() for h in spec.osm_name_hints}
    candidates=[]
    for w in osm.ways_named(spec.osm_name_hints):
        if w.tags.get('route') == 'ferry': continue
        c=way_centroid(w)
        if not c: continue
        names={w.tags.get(k,'').casefold() for k in ('name','name:ja','name:en')}
        candidates.append((0 if names & hints else 2,c[0],c[1],f'OSM way/{w.id}'))
    for n in osm.nodes_named(spec.osm_name_hints):
        names={n.tags.get(k,'').casefold() for k in ('name','name:ja','name:en')}
        candidates.append((1 if names & hints else 3,n.lat,n.lon,f'OSM node/{n.id}'))
    if candidates:
        _,lat,lon,source=min(candidates,key=lambda c:c[0])
        return lat,lon,source
    if spec.lat is not None and spec.lon is not None:
        return spec.lat, spec.lon, "config fallback (see note)"
    return None


def _try_append_asset(spec: LandmarkSpec, location: Tuple[float, float, float]) -> bool:
    path = landmark_assets_dir() / (spec.asset_filename or f"{spec.key}.blend")
    if not path.exists():
        return False
    with bpy.data.libraries.load(str(path), link=False) as (data_from, data_to):
        names = list(data_from.objects)
        data_to.objects = names[:1]
    if not data_to.objects:
        return False
    obj = data_to.objects[0]
    if obj is None:
        return False
    obj.location = location
    link_object(obj, collection("Landmarks"))
    obj.name = f"LandmarkAsset_{spec.key}"
    print(f"[landmarks] replaced {spec.key} with {path.name}")
    return True


def _box(name, cx, cy, cz, sx, sy, sz, col, mat):
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    verts = [
        (cx - hx, cy - hy, cz),
        (cx + hx, cy - hy, cz),
        (cx + hx, cy + hy, cz),
        (cx - hx, cy + hy, cz),
        (cx - hx, cy - hy, cz + sz),
        (cx + hx, cy - hy, cz + sz),
        (cx + hx, cy + hy, cz + sz),
        (cx - hx, cy + hy, cz + sz),
    ]
    faces = [(3, 2, 1, 0), (5, 6, 7, 4), (1, 5, 4, 0), (2, 6, 5, 1), (3, 7, 6, 2), (0, 4, 7, 3)]
    obj = new_mesh_object(name, verts, faces, col)
    assign_material(obj, mat)
    return obj


def _approx_marine_station(x, y, z, mats, col):
    roof = _box("Approx_MarineStation_Roof", x, y, z + 6.5, 70.0, 52.0, 0.35, col, mats["Steel"])
    for i, (dx, dy) in enumerate(((-18, -8), (10, -10), (-8, 12), (16, 8))):
        _box(f"Approx_MarineStation_Glass{i}", x + dx, y + dy, z, 8.0, 6.0, 4.2, col, mats["Glass"])
    # Column spacing is an explicit approximation, roof dimensions from the town.
    for dx in (-30,-18,-6,6,18,30):
        for dy in (-21,-7,7,21):
            bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=0.11,depth=6.5,location=(x+dx,y+dy,z+3.25))
            obj=bpy.context.object;obj.name='Approx_MarineStation_Column'
            link_object(obj,col);assign_material(obj,mats['Steel'])
            obj['status']='ESTIMATED column grid'
    roof['source']='https://www.town.naoshima.lg.jp/about/shisetsu/seastation.html'
    roof['status']='Published roof envelope; arrangement and height estimated'
    return roof


def _approx_chichu(x, y, z, mats, col):
    _box("Approx_Chichu_CourtA", x, y, z, 28.0, 18.0, 1.2, col, mats["Concrete"])
    _box("Approx_Chichu_CourtB", x + 22.0, y + 8.0, z, 16.0, 16.0, 1.0, col, mats["Concrete"])
    _box("Approx_Chichu_CourtC", x - 14.0, y + 16.0, z, 12.0, 22.0, 0.8, col, mats["Concrete"])


def _approx_lee(x, y, z, mats, col):
    _box("Approx_LeeUfan", x, y, z, 24.0, 14.0, 5.5, col, mats["Concrete"])
    _box("Approx_LeeUfan_Wing", x + 10.0, y - 8.0, z, 10.0, 22.0, 4.0, col, mats["Concrete"])


def _approx_benesse(x, y, z, mats, col):
    _box("Approx_BenesseHouse", x, y, z, 32.0, 18.0, 9.0, col, mats["Concrete"])
    _box("Approx_BenesseHouse_Wing", x + 16.0, y + 6.0, z, 14.0, 12.0, 6.0, col, mats["Concrete"])


def _approx_new_museum(x, y, z, mats, col):
    _box("Approx_NewMuseum", x, y, z, 30.0, 16.0, 8.0, col, mats["Concrete"])


def _placeholder_art(name, x, y, z, mats, col):
    obj=empty_marker(name,(x,y,z),col)
    obj['geometry_status']='UNKNOWN sculpture geometry; position marker only'
    return obj


def build_landmarks(
    cfg: LocationConfig,
    osm: OsmData,
    crs: CRS,
    sampler: TerrainSampler,
    mats: dict,
):
    col = collection("Landmarks")
    markers = collection("DistrictMarkers")
    for dist in cfg.districts.values():
        x, y = crs.to_xy(dist.lat, dist.lon)
        z = sampler.height_at_xy(x, y) + 8.0
        empty_marker(f"District_{dist.name_ja}_{dist.name}", (x, y, z), markers)

    builders = {
        "marine_station": _approx_marine_station,
        "chichu": _approx_chichu,
        "lee_ufan": _approx_lee,
        "benesse_house": _approx_benesse,
        "new_museum": _approx_new_museum,
    }
    placed = 0
    for spec in cfg.landmarks:
        pos = _resolve_position(spec, osm)
        if pos is None:
            print(f"[landmarks] UNKNOWN position for {spec.key}; skipped")
            continue
        lat, lon, src = pos
        x, y = crs.to_xy(lat, lon)
        z = sampler.height_at_xy(x, y)
        empty_marker(f"LM_{spec.key}", (x, y, z + 12.0), col)
        if _try_append_asset(spec, (x, y, z)):
            placed += 1
            continue
        if spec.key == "red_pumpkin" and cfg.aerial:
            from .red_pumpkin import build_red_pumpkin
            art=build_red_pumpkin(x,y,z)
            art['position_source']=src
            placed += 1
            continue
        if spec.kind == "placeholder_art":
            _placeholder_art(f"Placeholder_{spec.key}", x, y, z, mats, col)
            placed += 1
            print(f"[landmarks] placeholder art {spec.key} @ {src}")
            continue
        if spec.kind == "harbor":
            # Mapped coast supplies harbor geometry; no invented quay slab.
            placed += 1
            print(f"[landmarks] harbor marker {spec.key} @ {src}")
            continue
        if spec.key != 'marine_station':
            marker=bpy.data.objects.get(f'LM_{spec.key}')
            marker['position_source']=src
            marker['geometry_status']='UNKNOWN precise architecture; use OSM footprint where available'
            continue
        if spec.key == 'marine_station' and cfg.location_id == 'naoshima':
            way=next((w for w in osm.ways if w.id==75615686),None)
            if way:
                _mapped_station(way,crs,sampler,mats,col)
                placed+=1
                continue
        fn = builders.get(spec.key)
        if fn:
            fn(x, y, z, mats, col)
            placed += 1
            print(f"[landmarks] Approximate Landmark {spec.key} @ {src}")
        else:
            _box(f"Approx_{spec.key}", x, y, z, 12.0, 10.0, 5.0, col, mats["Concrete"])
            placed += 1
    print(f"[landmarks] placed={placed}")
    return placed


def _mapped_station(way,crs,sampler,mats,col):
    from .building_geometry import extrude
    from mathutils import Vector
    import math
    ring=drop_closing([crs.to_xy(*p) for p in way.coords])
    x=sum(p[0] for p in ring)/len(ring);y=sum(p[1] for p in ring)/len(ring)
    z=max(sampler.height_at_xy(*p) for p in ring)
    v,f=extrude(ring,z+5.8,0.22)
    roof=new_mesh_object('MarineStation_OSM_Roof',v,f,col);assign_material(roof,mats['Steel'])
    roof['source']='https://www.openstreetmap.org/way/75615686'
    roof['status']='OSM roof footprint; 5.8m height and column/glass arrangement ESTIMATED'
    dx,dy=longest_edge_dir(ring);nx,ny=-dy,dx
    def xy(u,v):return x+u*dx+v*nx,y+u*dy+v*ny
    for u in range(-36,37,9):
        for v in range(-27,28,9):
            px,py=xy(u,v)
            if not point_in_ring(px,py,ring):continue
            bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.1,depth=5.8,location=(px,py,z+2.9))
            ob=bpy.context.object;ob.name='MarineStation_Column_ESTIMATED';link_object(ob,col);assign_material(ob,mats['Steel'])
    for i,(u,v,sx,sy) in enumerate(((-16,-8,12,8),(8,8,14,10),(18,-12,9,7))):
        px,py=xy(u,v)
        # Local geometry rotates with the mapped roof rather than world axes.
        ob=_box(f'MarineStation_Glass_{i}_ESTIMATED',0,0,0,sx,sy,4.2,col,mats['Glass'])
        ob.location=(px,py,z);ob.rotation_euler.z=math.atan2(dy,dx)
    v,f=extrude(ring,z-.15,.15)
    ob=new_mesh_object('MarineStation_Paving',v,f,col);assign_material(ob,mats['Concrete'])
