"""Classify points into Miyanoura / Honmura / etc. using config radii + OSM names."""

from __future__ import annotations

import math

from .config import LocationConfig
from .coordinates import CRS
from .osm import OsmData, way_centroid


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def refine_districts_from_osm(cfg: LocationConfig, osm: OsmData) -> None:
    """Update district lat/lon when an OSM named feature is clearly matched.

    Only accept matches close to the published/config coordinate so ferry routes
    or address tags on distant objects cannot pull a district across the island.
    """
    for dist in cfg.districts.values():
        candidates = []
        for node in osm.nodes.values():
            name = " ".join(
                filter(None, (node.tags.get("name"), node.tags.get("name:ja"), node.tags.get("name:en")))
            )
            if any(h in name for h in dist.osm_name_hints):
                candidates.append((node.lat, node.lon, f"OSM node:{name}"))
        for way in osm.ways:
            if way.tags.get("route") == "ferry":
                continue
            name = " ".join(
                filter(None, (way.tags.get("name"), way.tags.get("name:ja"), way.tags.get("name:en")))
            )
            if not any(h in name for h in dist.osm_name_hints):
                continue
            c = way_centroid(way)
            if c:
                candidates.append((c[0], c[1], f"OSM way:{name}"))
        if not candidates:
            continue
        best = None
        best_d = 1e18
        for lat, lon, src in candidates:
            d = _haversine_m(dist.lat, dist.lon, lat, lon)
            if d < best_d:
                best_d = d
                best = (lat, lon, src, d)
        if best and best[3] <= max(800.0, dist.radius_m * 2.5):
            dist.lat, dist.lon = best[0], best[1]
            dist.note = (dist.note + f" OSM-refined ({best[2]}, {best[3]:.0f} m).").strip()
            print(f"[districts] {dist.name} -> {best[2]} shift={best[3]:.0f}m")
        else:
            print(f"[districts] {dist.name} keep config coords (no close OSM name)")


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
