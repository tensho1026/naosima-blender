"""Terrain mesh from GSI DEM + OSM landuse material slots."""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

import numpy as np

from .bpy_utils import assign_material, collection, new_mesh_object, shade_smooth
from .config import LocationConfig
from .coordinates import CRS, point_in_ring
from .dem import DEMGrid, TerrainSampler, subsample_for_lod
from .osm import OsmData

# Face material indices
MAT_GRASS = 0
MAT_FOREST = 1
MAT_RESIDENTIAL = 2
MAT_SAND = 3
MAT_ROCK = 4
MAT_TERRAIN = 5


def _landuse_polygons(osm: OsmData, crs: CRS) -> List[Tuple[str, List[Tuple[float, float]]]]:
    polys = []
    mapping = {
        ("natural", ("wood", "forest", "scrub")): "forest",
        ("landuse", ("forest",)): "forest",
        ("natural", ("beach", "sand")): "sand",
        ("natural", ("bare_rock", "rock", "cliff", "scree")): "rock",
        ("landuse", ("residential", "commercial", "retail", "farmyard")): "residential",
        ("landuse", ("industrial", "quarry")): "rock",
        ("landuse", ("grass", "meadow", "farmland", "orchard", "vineyard", "recreation_ground")): "grass",
        ("leisure", ("park", "garden", "pitch", "playground")): "grass",
        ("natural", ("grassland", "heath")): "grass",
    }
    for (key, values), klass in mapping.items():
        for w in osm.closed_ways_with(key, values):
            ring = [crs.to_xy(lat, lon) for lat, lon in w.coords]
            polys.append((klass, ring))
    return polys


def _classify_point(x: float, y: float, slope: float, elev: float, polys) -> int:
    klass = None
    for name, ring in polys:
        if point_in_ring(x, y, ring):
            klass = name
            break
    if klass == "forest":
        return MAT_FOREST
    if klass == "sand":
        return MAT_SAND
    if klass == "rock":
        return MAT_ROCK
    if klass == "residential":
        return MAT_RESIDENTIAL
    if klass == "grass":
        return MAT_GRASS
    if slope > 0.55:
        return MAT_ROCK
    if elev < 1.5:
        return MAT_SAND if slope < 0.12 else MAT_TERRAIN
    if elev > 40 and slope > 0.25:
        return MAT_FOREST
    if elev > 15:
        return MAT_FOREST if slope > 0.18 else MAT_GRASS
    return MAT_GRASS


def build_terrain(cfg: LocationConfig, dem: DEMGrid, crs: CRS, osm: OsmData, mats: dict, sampler: TerrainSampler):
    from pathlib import Path
    import json
    cache=Path(__file__).resolve().parents[1]/'data/cache/coastal_terrain.npz'
    if cfg.aerial and cfg.location_id=='naoshima' and cache.exists():
        meta=json.loads(cache.with_suffix('.json').read_text())
        if tuple(meta['bbox']) != tuple(cfg.bbox) or meta['dem_layer']!=cfg.dem_layer or meta['dem_zoom']!=cfg.dem_zoom:
            raise RuntimeError('Coastal mesh cache configuration mismatch; rerun scripts/prepare_coastal_terrain.py')
        with np.load(cache) as data:
            obj=new_mesh_object('Terrain',data['vertices'].tolist(),data['faces'].tolist(),collection('Terrain'))
        assign_material(obj,mats['Terrain']);shade_smooth(obj)
        obj['source']=meta['source'];obj['closed_coast_polygons']=meta['closed_coast_polygons']
        print(f"[terrain] loaded OSM-clipped coast: {len(obj.data.vertices)} vertices")
        return obj
    grid = subsample_for_lod(dem, cfg.lod)
    ny, nx = grid.ny, grid.nx
    print(f"[terrain] mesh {nx} x {ny}")
    heights = grid.heights
    verts = []
    vert_index = np.full((ny, nx), -1, dtype=np.int32)
    sea = cfg.sea_level
    for j in range(ny):
        lat = float(grid.lats[j])
        for i in range(nx):
            lon = float(grid.lons[i])
            h = heights[j, i]
            if np.isnan(h):
                continue
            # Keep near-shore land even if slightly negative (tide / geoid)
            z = max(h, sea + 0.05) * crs.scale
            x, y = crs.to_xy(lat, lon)
            vert_index[j, i] = len(verts)
            verts.append((x, y, z))

    # Pull shoreline verts toward sea level so DEM nodata does not create 10–20 m cliffs.
    ny, nx = grid.ny, grid.nx
    for j in range(ny):
        for i in range(nx):
            vi = int(vert_index[j, i])
            if vi < 0:
                continue
            edge = False
            for dj, di in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                jj, ii = j + dj, i + di
                if jj < 0 or ii < 0 or jj >= ny or ii >= nx or int(vert_index[jj, ii]) < 0:
                    edge = True
                    break
            if edge:
                x, y, z = verts[vi]
                verts[vi] = (x, y, min(z, sea + 0.6))

    faces: List[Tuple[int, int, int, int]] = []
    face_mat: List[int] = []
    from pathlib import Path
    aerial_ready=(Path(__file__).resolve().parents[1]/'data/aerial'/cfg.location_id/'metadata.json').exists()
    polys = [] if aerial_ready else _landuse_polygons(osm, crs)

    for j in range(ny - 1):
        for i in range(nx - 1):
            a = int(vert_index[j, i])
            b = int(vert_index[j, i + 1])
            c = int(vert_index[j + 1, i + 1])
            d = int(vert_index[j + 1, i])
            if min(a, b, c, d) < 0:
                continue
            faces.append((d, c, b, a))
            cx = (verts[a][0] + verts[b][0] + verts[c][0] + verts[d][0]) / 4.0
            cy = (verts[a][1] + verts[b][1] + verts[c][1] + verts[d][1]) / 4.0
            cz = (verts[a][2] + verts[b][2] + verts[c][2] + verts[d][2]) / 4.0
            if aerial_ready:
                face_mat.append(MAT_TERRAIN)
            else:
                slope = sampler.slope_at_xy(cx, cy)
                face_mat.append(_classify_point(cx, cy, slope, cz, polys))

    # Close exposed edges down below water; avoids a floating, paper-thin island.
    from collections import Counter
    edges=Counter(tuple(sorted((a,b))) for face in faces for a,b in zip(face,face[1:]+face[:1]))
    boundary=[(a,b) for face in faces for a,b in zip(face,face[1:]+face[:1]) if edges[tuple(sorted((a,b)))]==1]
    lower={}
    for a,b in boundary:
        for vi in (a,b):
            if vi not in lower:
                x,y,z=verts[vi];lower[vi]=len(verts);verts.append((x,y,(sea-2)*crs.scale))
        faces.append((b,a,lower[a],lower[b]));face_mat.append(MAT_ROCK)
    col = collection("Terrain")
    obj = new_mesh_object("Terrain", verts, faces, col)
    # Multi-material
    slot_names = ["Grass", "Forest", "ResidentialGround", "Sand", "Rock", "Terrain"]
    obj.data.materials.clear()
    for name in slot_names:
        mat = mats.get(name) or mats["Terrain"]
        obj.data.materials.append(mat)
    for poly, mi in zip(obj.data.polygons, face_mat):
        poly.material_index = int(mi)
    shade_smooth(obj, 45.0)
    print(f"[terrain] verts={len(verts)} faces={len(faces)}")
    return obj
