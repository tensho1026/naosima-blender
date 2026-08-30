"""Full generation pipeline (runs inside Blender)."""

from __future__ import annotations

import sys
from pathlib import Path

from .buildings import build_buildings
from .cameras import setup_cameras
from .coastline import build_coastline
from .config import LocationConfig
from .coordinates import CRS
from .dem import TerrainSampler, load_or_fetch_dem
from .districts import refine_districts_from_osm
from .export import render_previews, save_blend
from .landmarks import build_landmarks
from .lighting import setup_lighting
from .materials import make_materials
from .ocean import build_ocean
from .osm import load_or_fetch_osm
from .paths import output_dir
from .roads import build_roads
from .terrain import build_terrain
from .vegetation import build_vegetation
from .bpy_utils import reset_scene


def generate(cfg: LocationConfig, do_render: bool = False, blend_name: str = "naoshima.blend") -> Path:
    print(f"[pipeline] location={cfg.display_name} lod={cfg.lod} bbox={cfg.bbox}")
    reset_scene()
    dem = load_or_fetch_dem(cfg)
    osm = load_or_fetch_osm(cfg)
    refine_districts_from_osm(cfg, osm)
    crs = CRS(cfg)
    sampler = TerrainSampler(dem, crs, sea_level=cfg.sea_level)
    mats = make_materials()
    build_terrain(cfg, dem, crs, osm, mats, sampler)
    build_ocean(cfg, crs, mats)
    build_coastline(cfg, dem, crs, osm, mats)
    build_buildings(cfg, osm, crs, sampler, mats)
    build_roads(cfg, osm, crs, sampler, mats)
    build_vegetation(cfg, osm, crs, sampler, mats)
    build_landmarks(cfg, osm, crs, sampler, mats)
    setup_lighting(cfg)
    setup_cameras(cfg, crs, sampler)
    out = save_blend(output_dir() / blend_name)
    if do_render:
        render_previews(cfg)
        save_blend(out)
    print("[pipeline] done")
    return out
