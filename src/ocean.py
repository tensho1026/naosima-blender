"""Seto Inland Sea surface around the island."""

from __future__ import annotations

from .bpy_utils import assign_material, collection, new_mesh_object, shade_smooth
from .config import LocationConfig
from .coordinates import CRS


def build_ocean(cfg: LocationConfig, crs: CRS, mats: dict):
    south, west, north, east = cfg.bbox
    x0, y0 = crs.to_xy(south, west)
    x1, y1 = crs.to_xy(north, east)
    pad = 4000.0
    xmin, xmax = min(x0, x1) - pad, max(x0, x1) + pad
    ymin, ymax = min(y0, y1) - pad, max(y0, y1) + pad
    z = cfg.sea_level - 0.15
    verts = [
        (xmin, ymin, z),
        (xmax, ymin, z),
        (xmax, ymax, z),
        (xmin, ymax, z),
    ]
    col = collection("Ocean")
    obj = new_mesh_object("Ocean", verts, [(0, 1, 2, 3)], col)
    assign_material(obj, mats["Water"])
    shade_smooth(obj)
    print("[ocean] sea plane created")
    return obj
