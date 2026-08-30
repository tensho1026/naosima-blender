"""Classify points into Miyanoura / Honmura / etc. using config radii + OSM names."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from .config import DistrictSpec, LocationConfig
from .coordinates import CRS
from .osm import OsmData, way_centroid


def refine_districts_from_osm(cfg: LocationConfig, osm: OsmData) -> None:
    """Update district lat/lon when an OSM named feature is clearly matched."""
    for dist in cfg.districts.values():
        best = None
        for way in osm.ways_named(dist.osm_name_hints):
            c = way_centroid(way)
            if c:
                best = c
                break
        if best is None:
            nodes = osm.nodes_named(dist.osm_name_hints)
            if nodes:
                best = (nodes[0].lat, nodes[0].lon)
        if best:
            dist.lat, dist.lon = best[0], best[1]
            dist.note = (dist.note + " OSM-refined.").strip()


def classify_xy(cfg: LocationConfig, crs: CRS, x: float, y: float) -> str:
    lat, lon = crs.to_latlon(x, y)
    return classify_latlon(cfg, crs, lat, lon)


def classify_latlon(cfg: LocationConfig, crs: CRS, lat: float, lon: float) -> str:
    best_key = "other"
    best_d = 1e18
    for key, dist in cfg.districts.items():
        d = crs.distance_m(lat, lon, dist.lat, dist.lon)
        if d <= dist.radius_m and d < best_d:
            best_d = d
            best_key = key
    return best_key


def district_style(cfg: LocationConfig, key: str) -> str:
    dist = cfg.districts.get(key)
    return dist.style if dist else "mixed"
