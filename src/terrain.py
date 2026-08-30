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

    faces: List[Tuple[int, int, int, int]] = []
    face_mat: List[int] = []
    polys = _landuse_polygons(osm, crs)

    for j in range(ny - 1):
        for i in range(nx - 1):
            a = int(vert_index[j, i])
            b = int(vert_index[j, i + 1])
            c = int(vert_index[j + 1, i + 1])
            d = int(vert_index[j + 1, i])
            if min(a, b, c, d) < 0:
                continue
            faces.append((a, b, c, d))
            cx = (verts[a][0] + verts[b][0] + verts[c][0] + verts[d][0]) / 4.0
            cy = (verts[a][1] + verts[b][1] + verts[c][1] + verts[d][1]) / 4.0
            cz = (verts[a][2] + verts[b][2] + verts[c][2] + verts[d][2]) / 4.0
            slope = sampler.slope_at_xy(cx, cy)
            face_mat.append(_classify_point(cx, cy, slope, cz, polys))

    col = collection("Terrain")
    obj = new_mesh_object("Terrain", verts, faces, col)
    # Multi-material
    slot_names = ["Grass", "Forest", "TraditionalWall", "Sand", "Rock", "Terrain"]
    # residential uses a dirt/packed earth tone via TraditionalWall as stand-in ground
    obj.data.materials.clear()
    for name in slot_names:
        mat = mats.get(name) or mats["Terrain"]
        obj.data.materials.append(mat)
    for poly, mi in zip(obj.data.polygons, face_mat):
        poly.material_index = int(mi)
    shade_smooth(obj, 45.0)
    print(f"[terrain] verts={len(verts)} faces={len(faces)}")
    return obj
