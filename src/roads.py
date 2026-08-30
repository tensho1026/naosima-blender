"""Road meshes from OSM highways, draped on terrain."""

from __future__ import annotations

import math
from typing import List, Tuple

from .bpy_utils import assign_material, collection, new_mesh_object
from .config import ROAD_WIDTHS_M, LocationConfig
from .coordinates import CRS, sample_polyline
from .dem import TerrainSampler
from .osm import OsmData

Vec2 = Tuple[float, float]


def _width(highway: str) -> float:
    return ROAD_WIDTHS_M.get(highway, ROAD_WIDTHS_M["default"])


def _strip(points: List[Tuple[float, float, float]], width: float):
    if len(points) < 2:
        return None, None
    verts: List[Tuple[float, float, float]] = []
    faces: List[Tuple[int, int, int, int]] = []
    half = width * 0.5
    for i, (x, y, z) in enumerate(points):
        if i < len(points) - 1:
            dx = points[i + 1][0] - x
            dy = points[i + 1][1] - y
        else:
            dx = x - points[i - 1][0]
            dy = y - points[i - 1][1]
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L
        verts.append((x + nx * half, y + ny * half, z))
        verts.append((x - nx * half, y - ny * half, z))
        if i > 0:
            a = (i - 1) * 2
            b = a + 1
            c = i * 2 + 1
            d = i * 2
            faces.append((a, d, c, b))
    return verts, faces


def build_roads(cfg: LocationConfig, osm: OsmData, crs: CRS, sampler: TerrainSampler, mats: dict):
    col = collection("Roads")
    ways = [w for w in osm.ways if "highway" in w.tags and len(w.coords) >= 2]
    count = 0
    step = {0: 12.0, 1: 8.0, 2: 4.0}.get(cfg.lod, 8.0)
    for way in ways:
        hw = way.tags["highway"]
        if hw in ("proposed", "construction", "platform", "corridor"):
            continue
        pts2 = [crs.to_xy(lat, lon) for lat, lon in way.coords]
        sampled = sample_polyline(pts2, step)
        draped = []
        for x, y in sampled:
            z = sampler.height_at_xy(x, y) + 0.12
            draped.append((x, y, z))
        width = _width(hw)
        if cfg.lod == 0 and hw in ("footway", "path", "steps"):
            continue
        verts, faces = _strip(draped, width)
        if not verts:
            continue
        obj = new_mesh_object(f"road_{way.id}", verts, faces, col)
        assign_material(obj, mats["Road"])
        count += 1
    print(f"[roads] created={count} osm_highways={len(ways)}")
    return count
