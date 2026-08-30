"""Island outline from DEM land mask and OSM coastline ways."""

from __future__ import annotations

from typing import List, Tuple

import numpy as np

from .bpy_utils import assign_material, collection, new_mesh_object
from .config import LocationConfig
from .coordinates import CRS
from .dem import DEMGrid
from .osm import OsmData


def _trace_mask_boundary(mask: np.ndarray) -> List[List[Tuple[int, int]]]:
    """March around land/sea edges; returns pixel polylines (coarse)."""
    ny, nx = mask.shape
    edges = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = mask[j, i]
            b = mask[j, i + 1]
            c = mask[j + 1, i]
            if a != b:
                edges.append(((i + 1, j), (i + 1, j + 1)))
            if a != c:
                edges.append(((i, j + 1), (i + 1, j + 1)))
    return edges


def build_coastline(cfg: LocationConfig, dem: DEMGrid, crs: CRS, osm: OsmData, mats: dict):
    col = collection("Coastline")
    verts = []
    edges_idx = []
    # OSM coastline
    n_osm = 0
    for w in osm.ways_with("natural", ("coastline",)):
        if len(w.coords) < 2:
            continue
        start = len(verts)
        for lat, lon in w.coords:
            x, y = crs.to_xy(lat, lon)
            verts.append((x, y, cfg.sea_level + 0.2))
        for i in range(start, len(verts) - 1):
            edges_idx.append((i, i + 1))
        n_osm += 1

    land = np.isfinite(dem.heights)
    # DEM land/sea boundary as extra overlay (helps where OSM coastline is incomplete)
    pix_edges = _trace_mask_boundary(land)
    step = max(1, int({0: 6, 1: 3, 2: 2}.get(cfg.lod, 3)))
    n_dem = 0
    for (i0, j0), (i1, j1) in pix_edges[::step]:
        if j0 >= dem.ny or j1 >= dem.ny or i0 >= dem.nx or i1 >= dem.nx:
            continue
        lat0, lon0 = float(dem.lats[min(j0, dem.ny - 1)]), float(dem.lons[min(i0, dem.nx - 1)])
        lat1, lon1 = float(dem.lats[min(j1, dem.ny - 1)]), float(dem.lons[min(i1, dem.nx - 1)])
        x0, y0 = crs.to_xy(lat0, lon0)
        x1, y1 = crs.to_xy(lat1, lon1)
        a = len(verts)
        verts.append((x0, y0, cfg.sea_level + 0.25))
        verts.append((x1, y1, cfg.sea_level + 0.25))
        edges_idx.append((a, a + 1))
        n_dem += 1

    if not verts:
        print("[coastline] no coastline data")
        return None
    mesh_obj = new_mesh_object("Coastline", verts, [], col, edges=edges_idx)
    assign_material(mesh_obj, mats["Sand"])
    print(f"[coastline] OSM ways={n_osm} DEM edge segments={n_dem}")
    return mesh_obj
