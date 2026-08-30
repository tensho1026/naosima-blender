"""Approximate landmarks + optional handmade assets in assets/landmarks/.

Artworks are never copied: placeholders only.
"""

from __future__ import annotations

from typing import Optional, Tuple

import bpy

from .bpy_utils import assign_material, collection, empty_marker, link_object, new_mesh_object
from .config import LandmarkSpec, LocationConfig
from .coordinates import CRS
from .dem import TerrainSampler
from .osm import OsmData, way_centroid
from .paths import landmark_assets_dir


def _resolve_position(spec: LandmarkSpec, osm: OsmData) -> Optional[Tuple[float, float, str]]:
    for w in osm.ways_named(spec.osm_name_hints):
        c = way_centroid(w)
        if c:
            return c[0], c[1], "OSM way name match"
    nodes = osm.nodes_named(spec.osm_name_hints)
    if nodes:
        return nodes[0].lat, nodes[0].lon, "OSM node name match"
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
    faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    obj = new_mesh_object(name, verts, faces, col)
    assign_material(obj, mat)
    return obj


def _approx_marine_station(x, y, z, mats, col):
    roof = _box("Approx_MarineStation_Roof", x, y, z + 6.5, 70.0, 52.0, 0.35, col, mats["Steel"])
    for i, (dx, dy) in enumerate(((-18, -8), (10, -10), (-8, 12), (16, 8))):
        _box(f"Approx_MarineStation_Glass{i}", x + dx, y + dy, z, 8.0, 6.0, 4.2, col, mats["Glass"])
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
    return _box(name, x, y, z, 2.0, 2.0, 2.0, col, mats["Placeholder"])


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
        if spec.kind == "placeholder_art":
            _placeholder_art(f"Placeholder_{spec.key}", x, y, z, mats, col)
            placed += 1
            print(f"[landmarks] placeholder art {spec.key} @ {src}")
            continue
        if spec.kind == "harbor":
            _box(f"Approx_{spec.key}_quay", x, y - 12.0, z - 0.2, 40.0, 8.0, 0.8, col, mats["Concrete"])
            placed += 1
            print(f"[landmarks] harbor slab {spec.key} @ {src}")
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
