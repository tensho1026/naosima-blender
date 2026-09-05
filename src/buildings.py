"""Extrude OSM building polygons onto terrain. Heights are OSM or ESTIMATED."""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

from .bpy_utils import assign_material, collection, new_mesh_object
from .config import (
    DEFAULT_BUILDING_HEIGHT_M,
    DEFAULT_LEVELS_BY_TYPE,
    LocationConfig,
    STORY_HEIGHT_M,
)
from .coordinates import CRS, drop_closing, longest_edge_dir, ring_area
from .dem import TerrainSampler
from .districts import classify_latlon, district_style
from .osm import OsmData, OsmWay, way_centroid

Vec2 = Tuple[float, float]


def _parse_height(tags: dict) -> Optional[float]:
    raw = tags.get("height") or tags.get("building:height")
    if not raw:
        return None
    try:
        s = raw.lower().replace("m", "").replace(" ", "")
        return float(s)
    except ValueError:
        return None


def _parse_levels(tags: dict) -> Optional[int]:
    raw = tags.get("building:levels") or tags.get("levels")
    if not raw:
        return None
    try:
        return max(0, int(float(raw)))
    except ValueError:
        return None


def estimated_height(tags: dict) -> Tuple[float, bool]:
    h = _parse_height(tags)
    if h and h > 0.5:
        return h, False
    levels = _parse_levels(tags)
    if levels is not None:
        return levels * STORY_HEIGHT_M, True
    btype = tags.get("building", "yes")
    levels = DEFAULT_LEVELS_BY_TYPE.get(btype, 2)
    return levels * STORY_HEIGHT_M if btype in DEFAULT_LEVELS_BY_TYPE else DEFAULT_BUILDING_HEIGHT_M, True


def _footprint_xy(way: OsmWay, crs: CRS) -> List[Vec2]:
    pts = [crs.to_xy(lat, lon) for lat, lon in way.coords]
    return drop_closing(pts)


from .building_geometry import extrude as _extrude_mesh, rectangle


def build_buildings(
    cfg: LocationConfig,
    osm: OsmData,
    crs: CRS,
    sampler: TerrainSampler,
    mats: dict,
):
    col = collection("Buildings")
    ways = [w for w in osm.ways if w.tags.get("building") not in (None, "no") and len(w.coords) >= 4 and w.coords[0] == w.coords[-1]]
    count = 0
    estimated = 0
    audit = []
    for way in ways:
        if cfg.aerial and cfg.location_id=='naoshima':
            from .individual_buildings import INDIVIDUAL_BUILDINGS
            if way.id in INDIVIDUAL_BUILDINGS:
                audit.append(dict(osm_id=way.id,status='Individual photo-referenced exterior',asset=INDIVIDUAL_BUILDINGS[way.id]))
                continue
        if cfg.location_id == 'naoshima' and way.id == 75615686 and any(s.key == 'marine_station' for s in cfg.landmarks):
            audit.append(dict(osm_id=way.id,status='modeled as Marine Station using this footprint'))
            continue
        if count >= cfg.max_buildings:
            break
        ring = _footprint_xy(way, crs)
        if len(ring) < 3:
            continue
        cx = sum(p[0] for p in ring) / len(ring)
        cy = sum(p[1] for p in ring) / len(ring)
        # Place on highest footprint sample so buildings don't sink into slopes
        zs = [sampler.height_at_xy(x, y) for x, y in ring[:: max(1, len(ring) // 8)] or ring]
        z0 = max(zs) if zs else sampler.height_at_xy(cx, cy)
        height, is_est = estimated_height(way.tags)
        photo_museum = cfg.location_id == 'naoshima' and way.id == 1465161307
        if photo_museum:
            # Official: one above-ground floor; total height inferred from exterior photo.
            height=6.5;is_est=True
        c = way_centroid(way)
        key = classify_latlon(cfg, crs, c[0], c[1]) if c else "other"
        style = district_style(cfg, key)
        if height <= 0:
            audit.append(dict(osm_id=way.id, name=way.tags.get('name',''), status='underground: above-ground levels zero'))
            continue
        roof_shape = way.tags.get('roof:shape')
        domestic = way.tags.get('building') in ('yes','house','detached','residential','terrace','semidetached_house')
        gable = (roof_shape == 'gabled' or (roof_shape is None and domestic and style in ('traditional','fishing','modern_port','mixed'))) and cfg.lod >= 1
        verts, faces = _extrude_mesh(ring, z0, height, gable=gable)
        if photo_museum:
            from .building_geometry import pitched_outline
            verts,faces=pitched_outline(ring,z0,height,3.2)
        if not verts:
            continue
        if is_est:
            estimated += 1
        obj = new_mesh_object(f"bldg_{way.id}", verts, faces, col)
        name = ' '.join(way.tags.get(k,'') for k in ('name','name:ja','name:en'))
        wall = mats['TraditionalWall'] if style == 'traditional' else mats['ModernWall']
        if '直島新美術館' in name:
            wall = mats['BlackPlaster']
        elif way.tags.get('tourism') == 'museum':
            wall = mats['Concrete']
        assign_material(obj, wall)
        obj.data.materials.append(mats['Roof'] if gable else mats['RoofModern'])
        for poly in obj.data.polygons:
            if poly.normal.z > 0.15:
                poly.material_index = 1
        obj['osm_id'] = way.id
        obj['source'] = f'https://www.openstreetmap.org/way/{way.id}'
        obj['name_original'] = name.strip()
        obj['height_m'] = height
        obj['height_status'] = 'ESTIMATED from levels/default' if is_est else 'OSM height'
        obj['roof_status'] = 'OSM shape' if roof_shape else 'ESTIMATED typology; complex footprints flat'
        if photo_museum:
            obj['roof_status']='Pitched roof observed in official photo; ridge and pitch estimated'
            obj['reference']='https://benesse-artsite.jp/nnmoa/art/'
            obj['reference_photo']='https://benesse-artsite.jp/nnmoa/uploads/architecture_04.jpg'
            obj['above_ground_floors']=1
        obj['facade_status'] = 'UNKNOWN; procedural openings are illustrative'
        obj['osm_tags'] = __import__('json').dumps(way.tags,ensure_ascii=False)
        # A continuous plinth connects the level building to sloping DEM samples.
        low = min(zs)-0.2
        if z0-low>0.25:
            fv,ff=_extrude_mesh(ring,low,z0-low,False)
            foundation=new_mesh_object(f'foundation_{way.id}',fv,ff,col)
            assign_material(foundation,mats['Concrete'])
            foundation['status']='ESTIMATED terrain foundation'
        if cfg.lod >= 2 and domestic and not photo_museum and rectangle(ring) and height < 15:
            _facade_details(way.id,ring,z0,height,col,mats)
        audit.append(dict(osm_id=way.id,name=name.strip(),height_m=height,height_estimated=is_est,roof=obj['roof_status'],source=obj['source']))
        count += 1
    print(f"[buildings] created={count} estimated_height={estimated} osm_ways={len(ways)}")
    from .courtyards import build_courtyards
    audit.extend(build_courtyards(cfg,osm,crs,sampler,mats,col))
    from .paths import output_dir
    import json
    (output_dir()/'building_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
    return count


def _facade_details(osm_id,ring,z0,height,col,mats):
    """Plausible openings only. No claim of individual facade survey."""
    from .building_geometry import area
    if area(ring)<0:
        ring=list(reversed(ring))
    verts=[]; faces=[]; indices=[]
    floors=max(1,min(3,int(height/3)))
    for a,b in zip(ring,ring[1:]+ring[:1]):
        length=math.dist(a,b)
        if length<3: continue
        dx,dy=(b[0]-a[0])/length,(b[1]-a[1])/length
        nx,ny=dy,-dx
        bays=max(1,int(length/3.2))
        for floor in range(floors):
            for bay in range(bays):
                center=(bay+0.5)*length/bays
                for width,wh,offset,mi in ((1.5,1.35,0.025,0),(1.32,1.17,0.035,1)):
                    base=len(verts)
                    for along,up in ((-width/2,0),(width/2,0),(width/2,wh),(-width/2,wh)):
                        verts.append((a[0]+dx*(center+along)+nx*offset,a[1]+dy*(center+along)+ny*offset,z0+floor*2.7+0.8+up+(0.09 if mi else 0)))
                    faces.append(tuple(range(base,base+4))); indices.append(mi)
    obj=new_mesh_object(f'facade_{osm_id}',verts,faces,col)
    obj.data.materials.append(mats['Steel']);obj.data.materials.append(mats['WindowDark'])
    for p,mi in zip(obj.data.polygons,indices):p.material_index=mi
    obj['status']='ESTIMATED: generic openings, not measured facade'
