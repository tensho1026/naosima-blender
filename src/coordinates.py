"""Local tangent-plane coordinates. 1 Blender unit = 1 meter at terrain_scale=1.

Blender: +X east, +Y north, +Z up.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

from .config import LocationConfig

Vec2 = Tuple[float, float]
Vec3 = Tuple[float, float, float]


class CRS:
    def __init__(self, cfg: LocationConfig):
        self.lat0 = cfg.center_lat
        self.lon0 = cfg.center_lon
        self.scale = cfg.terrain_scale
        self.m_per_deg_lat = 111_320.0
        self.m_per_deg_lon = 111_320.0 * math.cos(math.radians(self.lat0))

    def to_xy(self, lat: float, lon: float) -> Vec2:
        x = (lon - self.lon0) * self.m_per_deg_lon * self.scale
        y = (lat - self.lat0) * self.m_per_deg_lat * self.scale
        return (x, y)

    def to_xyz(self, lat: float, lon: float, elev: float) -> Vec3:
        x, y = self.to_xy(lat, lon)
        return (x, y, elev * self.scale)

    def to_latlon(self, x: float, y: float) -> Tuple[float, float]:
        lon = x / (self.m_per_deg_lon * self.scale) + self.lon0
        lat = y / (self.m_per_deg_lat * self.scale) + self.lat0
        return (lat, lon)

    def distance_m(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        x1, y1 = self.to_xy(lat1, lon1)
        x2, y2 = self.to_xy(lat2, lon2)
        return math.hypot(x2 - x1, y2 - y1)


def ring_area(points: Sequence[Vec2]) -> float:
    if len(points) < 3:
        return 0.0
    s = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return 0.5 * s


def ensure_closed(points: List[Vec2]) -> List[Vec2]:
    if len(points) >= 2 and points[0] != points[-1]:
        return points + [points[0]]
    return points


def drop_closing(points: Sequence[Vec2]) -> List[Vec2]:
    pts = list(points)
    if len(pts) >= 2 and pts[0] == pts[-1]:
        pts = pts[:-1]
    return pts


def point_in_ring(x: float, y: float, ring: Sequence[Vec2]) -> bool:
    pts = drop_closing(ring)
    inside = False
    n = len(pts)
    j = n - 1
    for i in range(n):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def centroid(points: Sequence[Vec2]) -> Vec2:
    pts = drop_closing(points)
    if not pts:
        return (0.0, 0.0)
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def longest_edge_dir(points: Sequence[Vec2]) -> Vec2:
    pts = drop_closing(points)
    best = 0.0
    d = (1.0, 0.0)
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy)
        if L > best:
            best = L
            d = (dx / L, dy / L) if L else (1.0, 0.0)
    return d


def sample_polyline(points: Sequence[Vec2], step: float) -> List[Vec2]:
    if len(points) < 2:
        return list(points)
    out = [points[0]]
    acc = 0.0
    for i in range(1, len(points)):
        x0, y0 = points[i - 1]
        x1, y1 = points[i]
        seg = math.hypot(x1 - x0, y1 - y0)
        if seg < 1e-6:
            continue
        while acc + step <= seg:
            acc += step
            t = acc / seg
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
        acc = acc - seg
    if out[-1] != points[-1]:
        out.append(points[-1])
    return out


def iter_grid(n: int) -> Iterable[Tuple[int, int]]:
    for j in range(n):
        for i in range(n):
            yield i, j
