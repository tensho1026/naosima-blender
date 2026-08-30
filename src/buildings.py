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
        return max(1, int(float(raw)))
    except ValueError:
        return None


def estimated_height(tags: dict) -> Tuple[float, bool]:
    h = _parse_height(tags)
    if h and h > 0.5:
        return h, False
    levels = _parse_levels(tags)
    if levels:
        return levels * STORY_HEIGHT_M, True
    btype = tags.get("building", "yes")
    levels = DEFAULT_LEVELS_BY_TYPE.get(btype, 2)
    return levels * STORY_HEIGHT_M if btype in DEFAULT_LEVELS_BY_TYPE else DEFAULT_BUILDING_HEIGHT_M, True


def _footprint_xy(way: OsmWay, crs: CRS) -> List[Vec2]:
    pts = [crs.to_xy(lat, lon) for lat, lon in way.coords]
    return drop_closing(pts)


def _extrude_mesh(ring: List[Vec2], z0: float, height: float, gable: bool):
    n = len(ring)
    if n < 3:
        return None, None
    area = abs(ring_area(ring))
    if area < 4.0:
        return None, None
    if ring_area(ring) < 0:
        ring = list(reversed(ring))
    z1 = z0 + height
    verts: List[Tuple[float, float, float]] = []
    for x, y in ring:
        verts.append((x, y, z0))
    for x, y in ring:
        verts.append((x, y, z1))
    faces: List[Tuple[int, ...]] = []
    # sides
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    # bottom (downward)
    faces.append(tuple(range(n - 1, -1, -1)))
    if gable and n >= 4:
        dx, dy = longest_edge_dir(ring)
        cx = sum(p[0] for p in ring) / n
        cy = sum(p[1] for p in ring) / n
        ridge_h = z1 + min(2.2, height * 0.35)
        # two ridge points along longest direction
        span = math.sqrt(area) * 0.35
        r0 = (cx + dx * span, cy + dy * span, ridge_h)
        r1 = (cx - dx * span, cy - dy * span, ridge_h)
        ri0 = len(verts)
        verts.append(r0)
        verts.append(r1)
        # roof as two quads approx using top ring fan to ridge — simple tent
        faces.append(tuple(range(n, 2 * n)))  # still cap, then extra gable faces
        faces.append((ri0, ri0 + 1, 2 * n - 1))
    else:
        faces.append(tuple(range(n, 2 * n)))
    return verts, faces


def build_buildings(
    cfg: LocationConfig,
    osm: OsmData,
    crs: CRS,
    sampler: TerrainSampler,
    mats: dict,
):
    col = collection("Buildings")
    ways = [w for w in osm.ways if "building" in w.tags and len(w.coords) >= 4]
    count = 0
    estimated = 0
    for way in ways:
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
        if is_est:
            estimated += 1
        c = way_centroid(way)
        key = classify_latlon(cfg, crs, c[0], c[1]) if c else "other"
        style = district_style(cfg, key)
        gable = style == "traditional" and cfg.lod >= 1
        if style == "traditional":
            height *= 0.92
        elif style == "modern_port" and way.tags.get("building") in ("warehouse", "industrial", "retail"):
            height *= 1.15
        verts, faces = _extrude_mesh(ring, z0, height, gable=gable)
        if not verts:
            continue
        obj = new_mesh_object(f"bldg_{way.id}", verts, faces, col)
        if style == "traditional":
            assign_material(obj, mats["TraditionalWall"])
            # second slot for roof
            obj.data.materials.append(mats["Roof"])
            nfaces = len(obj.data.polygons)
            if nfaces:
                obj.data.polygons[nfaces - 1].material_index = 1
        elif style in ("museum",):
            assign_material(obj, mats["Concrete"])
        else:
            assign_material(obj, mats["ModernWall"])
            obj.data.materials.append(mats["RoofModern"])
            nfaces = len(obj.data.polygons)
            if nfaces:
                obj.data.polygons[nfaces - 1].material_index = 1
        count += 1
    print(f"[buildings] created={count} estimated_height={estimated} osm_ways={len(ways)}")
    return count
