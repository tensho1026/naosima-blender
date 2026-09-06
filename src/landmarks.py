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
    # Coarse DEM contains a several-metre mound beneath the terminal roof.
    # Estimate the quay level from the three lowest perimeter samples instead.
    levels=sorted(sampler.height_at_xy(*p) for p in ring)
    z=sum(levels[:3])/3
    terrain=bpy.data.objects.get('Terrain')
    if terrain:
        xmin=min(p[0] for p in ring)-8;xmax=max(p[0] for p in ring)+8
        ymin=min(p[1] for p in ring)-8;ymax=max(p[1] for p in ring)+8
        targets=[(terrain,-.15)]+[(road,.02) for road in (bpy.data.collections['Roads'].objects if 'Roads' in bpy.data.collections else [])]
        for mesh,offset in targets:
            for vertex in mesh.data.vertices:
                px,py=vertex.co.x,vertex.co.y
                if not(xmin<px<xmax and ymin<py<ymax):continue
                if point_in_ring(px,py,ring):weight=1.0
                else:
                    distance=1e9
                    for a,b in zip(ring,ring[1:]+ring[:1]):
                        ex,ey=b[0]-a[0],b[1]-a[1]
                        t=max(0,min(1,((px-a[0])*ex+(py-a[1])*ey)/(ex*ex+ey*ey)))
                        distance=min(distance,math.hypot(px-a[0]-t*ex,py-a[1]-t*ey))
                    weight=max(0,1-distance/8)
                vertex.co.z=vertex.co.z*(1-weight)+(z+offset)*weight
            mesh.data.update()
        terrain['marine_station_grading']='Estimated quay plane from lowest perimeter DEM samples; 8m transition; not surveyed'

    from .individual_buildings import _material
    from .mesh_batch import Parts
    roof_height=4.6;roof_thickness=.155;grid=6.75
    white=_material('MarineStation_painted_steel',(.72,.73,.70),.45)
    glazing=_material('MarineStation_thin_clear_glass',(.94,.97,.96),.08)
    shader=next(n for n in glazing.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    shader.inputs['Transmission Weight'].default_value=1;shader.inputs['IOR'].default_value=1.46
    v,f=extrude(ring,z+roof_height,roof_thickness)
    roof=new_mesh_object('MarineStation_OSM_Roof',v,f,col);assign_material(roof,white)
    roof['source']='https://www.openstreetmap.org/way/75615686'
    roof['status']='OSM roof footprint; 85mm columns / 6.75m span / 155mm roof from published architect site visit; 4.6m elevation and room positions inferred'
    roof['detail_reference']='https://trim.gangukan.jp/2012/09/29/「建築探訪-62」-naoshima/'
    roof['column_diameter_m']=.085;roof['column_grid_m']=grid;roof['roof_thickness_m']=roof_thickness
    dx,dy=longest_edge_dir(ring)
    if dy<0:dx,dy=-dx,-dy  # +u points NE, toward the public road on the diagram.
    nx,ny=-dy,dx
    def xy(u,v):return x+u*dx+v*nx,y+u*dy+v*ny
    us=[(px-x)*dx+(py-y)*dy for px,py in ring];vs=[(px-x)*nx+(py-y)*ny for px,py in ring]
    nu=int((max(us)-min(us))/grid);nv=int((max(vs)-min(vs))/grid)
    u0=(min(us)+max(us)-nu*grid)/2;v0=(min(vs)+max(vs)-nv*grid)/2
    for i in range(nu+1):
        for j in range(nv+1):
            px,py=xy(u0+i*grid,v0+j*grid)
            if not point_in_ring(px,py,ring):continue
            bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=.0425,depth=roof_height,location=(px,py,z+roof_height/2))
            ob=bpy.context.object;ob.name='MarineStation_Column_ESTIMATED';link_object(ob,col);assign_material(ob,white)
            ob['diameter_m']=.085;ob['grid_origin_status']='Inferred within OSM roof boundary'
    uc=(min(us)+max(us))/2;vc=(min(vs)+max(vs))/2
    from .plan_clipping import clear_station_roads
    clear_station_roads((x,y),(dx,dy),[
        (uc+u-sx/2,vc+v-sy/2,uc+u+sx/2,vc+v+sy/2)
        for u,v,sx,sy in [(3.1,3.2,27.4,25.4),(24,-4.7,12,9.4),(29.3,18.5,8.4,10.2)]])
    plan_source='https://naoshima.net/wp-content/uploads/2015/09/uminoeki.pdf'
    # Diagram north arrow and public-road/ferry sides anchor orientation to the
    # roof's NE/SW axis. Dimensions below are proportional readings, not a survey.
    for i,(u,v,sx,sy) in enumerate(((uc+3.1,vc+3.2,27.4,25.4),)):
        px,py=xy(u,v)
        root=bpy.data.objects.new(f'MarineStation_GlassRoom_{i}_ESTIMATED',None);link_object(root,col)
        root.location=(px,py,z);root.rotation_euler.z=math.atan2(dy,dx)
        root['fidelity']='Main terminal enclosure aligned to official visitor diagram; dimensions estimated by roof scale'
        root['plan_source']=plan_source;root['function']='Passenger terminal, waiting, cafe and visitor information'
        parts=Parts();h=roof_height
        for side in (-1,1):
            parts.box('Glass',(side*sx/2,0,h/2),(.012,sy,h))
            parts.box('Glass',(0,side*sy/2,h/2),(sx,.012,h))
            for height in (.04,h-.04):
                parts.box('Frame',(side*sx/2,0,height),(.04,sy,.04))
                parts.box('Frame',(0,side*sy/2,height),(sx,.04,.04))
        for xx in (-sx/2,sx/2):
            for yy in (-sy/2,sy/2):parts.box('Frame',(xx,yy,h/2),(.045,.045,h))
        # Four exterior door locations shown in the public facilities diagram.
        for along,edge in ((-5.1,sy/2),(7.6,-sy/2),(-4.4,-sy/2)):
            for xx in (along-1,along,along+1):parts.box('Frame',(xx,edge,1.25),(.035,.055,2.5))
            parts.box('Frame',(along,edge,2.5),(2.05,.065,.06))
        for yy in (4.6,5.6,6.6):parts.box('Frame',(sx/2,yy,1.25),(.055,.035,2.5))
        parts.box('Frame',(sx/2,5.6,2.5),(.065,2.05,.06))
        parts.finish('Walls',root,{'Glass':glazing,'Frame':white})
    for label,u,v,sx,sy in [('Lavatory',uc+24,vc-4.7,12.0,9.4),('RestrictedService',uc+29.3,vc+18.5,8.4,10.2)]:
        px,py=xy(u,v)
        ob=_box(f'MarineStation_{label}_PLAN_ESTIMATED',0,0,0,sx,sy,roof_height,col,mats['Concrete'])
        ob.location=(px,py,z);ob.rotation_euler.z=math.atan2(dy,dx)
        ob['plan_source']=plan_source;ob['fidelity']='Separate volume from visitor diagram; wall finish, openings and exact dimensions unverified'
    mirror=_material('MarineStation_mirror_steel',(.73,.74,.73),.065)
    shader=next(n for n in mirror.node_tree.nodes if n.type=='BSDF_PRINCIPLED');shader.inputs['Metallic'].default_value=1
    for i,(u,v,length) in enumerate(((uc-14.0,vc+9.6,5.9),(uc-25.2,vc-2.8,7.8))):
        px,py=xy(u,v)
        ob=_box(f'MarineStation_MirrorPanel_{i}_PLAN_ESTIMATED',0,0,0,.10,length,roof_height,col,mirror)
        ob.location=(px,py,z);ob.rotation_euler.z=math.atan2(dy,dx)
        ob['plan_source']=plan_source;ob['fidelity']='Two freestanding panel positions read from visitor diagram; remaining structural panels not modelled'
    v,f=extrude(ring,z-.15,.15)
    ob=new_mesh_object('MarineStation_Paving',v,f,col);assign_material(ob,mats['Concrete'])
