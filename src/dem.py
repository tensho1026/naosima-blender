"""GSI (Geospatial Information Authority of Japan) elevation tiles.

Source: https://cyberjapandata.gsi.go.jp/xyz/{layer}/{z}/{x}/{y}.txt
Spec: https://cyberjapandata.gsi.go.jp/development/demtile.html

Attribution required: 国土地理院 / 地理院タイル
"""

from __future__ import annotations

import json
import math
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

from .config import GSI_TILE_BASE, LocationConfig
from .coordinates import CRS
from .httputil import http_get
from .paths import dem_dir


TILE = 256


def latlon_to_tile(lat: float, lon: float, zoom: int) -> Tuple[float, float]:
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return x, y


def tile_pixel_to_latlon(zoom: int, x: float, y: float) -> Tuple[float, float]:
    n = 2.0 ** zoom
    lon = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / n)))
    return math.degrees(lat_rad), lon


@dataclass
class DEMGrid:
    heights: np.ndarray  # (ny, nx) float32, NaN = nodata / sea
    lats: np.ndarray  # (ny,)
    lons: np.ndarray  # (nx,)
    zoom: int
    layer: str
    origin_note: str

    @property
    def ny(self) -> int:
        return int(self.heights.shape[0])

    @property
    def nx(self) -> int:
        return int(self.heights.shape[1])


class TerrainSampler:
    def __init__(self, dem: DEMGrid, crs: CRS, sea_level: float = 0.0):
        self.dem = dem
        self.crs = crs
        self.sea_level = sea_level
        # Precompute blender XY of DEM corners for bilinear lookup via lat/lon
        self._xs = np.array([crs.to_xy(dem.lats[dem.ny // 2], lon)[0] for lon in dem.lons], dtype=np.float64)
        self._ys = np.array([crs.to_xy(lat, dem.lons[dem.nx // 2])[1] for lat in dem.lats], dtype=np.float64)

    def height_at_latlon(self, lat: float, lon: float) -> float:
        # lons increase east, lats decrease south in array (row 0 = north)
        lons = self.dem.lons
        lats = self.dem.lats
        if lon < lons[0] or lon > lons[-1] or lat > lats[0] or lat < lats[-1]:
            return self.sea_level
        ix = np.searchsorted(lons, lon) - 1
        # lats are descending
        iy = np.searchsorted(-lats, -lat) - 1
        ix = int(np.clip(ix, 0, self.dem.nx - 2))
        iy = int(np.clip(iy, 0, self.dem.ny - 2))
        tx = (lon - lons[ix]) / (lons[ix + 1] - lons[ix] + 1e-16)
        ty = (lats[iy] - lat) / (lats[iy] - lats[iy + 1] + 1e-16)
        h = self.dem.heights
        samples = [h[iy, ix], h[iy, ix + 1], h[iy + 1, ix], h[iy + 1, ix + 1]]
        if any(np.isnan(s) for s in samples):
            valid = [s for s in samples if not np.isnan(s)]
            return float(np.mean(valid)) if valid else self.sea_level
        a = samples[0] * (1 - tx) + samples[1] * tx
        b = samples[2] * (1 - tx) + samples[3] * tx
        return float(a * (1 - ty) + b * ty)

    def height_at_xy(self, x: float, y: float) -> float:
        lat, lon = self.crs.to_latlon(x, y)
        return self.height_at_latlon(lat, lon) * self.crs.scale

    def slope_at_xy(self, x: float, y: float, delta: float = 8.0) -> float:
        h = self.height_at_xy
        dzdx = (h(x + delta, y) - h(x - delta, y)) / (2 * delta)
        dzdy = (h(x, y + delta) - h(x, y - delta)) / (2 * delta)
        return math.hypot(dzdx, dzdy)


def _parse_tile_txt(text: str) -> np.ndarray:
    rows = []
    for line in text.strip().splitlines():
        vals = []
        for tok in line.split(","):
            tok = tok.strip()
            if tok in ("e", "E", "") or tok.lower() == "nan":
                vals.append(np.nan)
            else:
                vals.append(float(tok))
        if len(vals) < TILE:
            vals.extend([np.nan] * (TILE - len(vals)))
        rows.append(vals[:TILE])
    while len(rows) < TILE:
        rows.append([np.nan] * TILE)
    return np.array(rows[:TILE], dtype=np.float32)


def _tile_path(cfg: LocationConfig, tx: int, ty: int) -> Path:
    return dem_dir() / cfg.location_id / cfg.dem_layer / str(cfg.dem_zoom) / f"{tx}_{ty}.txt"


def fetch_tile(cfg: LocationConfig, tx: int, ty: int) -> np.ndarray:
    path = _tile_path(cfg, tx, ty)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        return _parse_tile_txt(path.read_text(encoding="utf-8", errors="replace"))
    url = f"{GSI_TILE_BASE}/{cfg.dem_layer}/{cfg.dem_zoom}/{tx}/{ty}.txt"
    try:
        raw = http_get(url, timeout=45)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            arr = np.full((TILE, TILE), np.nan, dtype=np.float32)
            path.write_text("e," * (TILE - 1) + "e\n", encoding="utf-8")
            return arr
        raise
    text = raw.decode("utf-8", errors="replace")
    path.write_text(text, encoding="utf-8")
    return _parse_tile_txt(text)


def load_or_fetch_dem(cfg: LocationConfig) -> DEMGrid:
    south, west, north, east = cfg.bbox
    x0, y_north = latlon_to_tile(north, west, cfg.dem_zoom)
    x1, y_south = latlon_to_tile(south, east, cfg.dem_zoom)
    tx0, tx1 = int(math.floor(x0)), int(math.floor(x1))
    ty0, ty1 = int(math.floor(y_north)), int(math.floor(y_south))
    ntx, nty = tx1 - tx0 + 1, ty1 - ty0 + 1
    mosaic = np.full((nty * TILE, ntx * TILE), np.nan, dtype=np.float32)
    print(f"[dem] fetching GSI {cfg.dem_layer} z{cfg.dem_zoom} tiles {ntx}x{nty} ({tx0},{ty0})-({tx1},{ty1})")
    for iy, ty in enumerate(range(ty0, ty1 + 1)):
        for ix, tx in enumerate(range(tx0, tx1 + 1)):
            mosaic[iy * TILE : (iy + 1) * TILE, ix * TILE : (ix + 1) * TILE] = fetch_tile(cfg, tx, ty)

    # Geographic coordinates of every pixel center
    lats = np.empty(mosaic.shape[0], dtype=np.float64)
    lons = np.empty(mosaic.shape[1], dtype=np.float64)
    for row in range(mosaic.shape[0]):
        lat, _ = tile_pixel_to_latlon(cfg.dem_zoom, tx0, ty0 + (row + 0.5) / TILE)
        lats[row] = lat
    for col in range(mosaic.shape[1]):
        _, lon = tile_pixel_to_latlon(cfg.dem_zoom, tx0 + (col + 0.5) / TILE, ty0)
        lons[col] = lon

    # Crop to bbox with 1-pixel pad
    col_mask = (lons >= west) & (lons <= east)
    row_mask = (lats >= south) & (lats <= north)
    cols = np.where(col_mask)[0]
    rows = np.where(row_mask)[0]
    if len(cols) == 0 or len(rows) == 0:
        raise RuntimeError("DEM crop is empty; check bbox")
    c0, c1 = max(0, cols[0] - 1), min(mosaic.shape[1], cols[-1] + 2)
    r0, r1 = max(0, rows[0] - 1), min(mosaic.shape[0], rows[-1] + 2)
    heights = mosaic[r0:r1, c0:c1]
    meta = {
        "source": "GSI elevation tiles",
        "url_pattern": f"{GSI_TILE_BASE}/{cfg.dem_layer}/{{z}}/{{x}}/{{y}}.txt",
        "layer": cfg.dem_layer,
        "zoom": cfg.dem_zoom,
        "bbox": cfg.bbox,
        "valid_min": float(np.nanmin(heights)) if np.isfinite(heights).any() else None,
        "valid_max": float(np.nanmax(heights)) if np.isfinite(heights).any() else None,
        "shape": list(heights.shape),
    }
    meta_path = dem_dir() / cfg.location_id / "grid_meta.json"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(
        f"[dem] grid {heights.shape} elev {meta['valid_min']:.1f}..{meta['valid_max']:.1f} m "
        f"(NaN=nodata/sea)"
    )
    return DEMGrid(
        heights=heights,
        lats=lats[r0:r1],
        lons=lons[c0:c1],
        zoom=cfg.dem_zoom,
        layer=cfg.dem_layer,
        origin_note="GSI DEM tiles; nodata is sea or missing",
    )


def subsample_for_lod(dem: DEMGrid, lod: int) -> DEMGrid:
    step = {0: 3, 1: 2, 2: 1}.get(lod, 2)
    if step <= 1:
        return dem
    return DEMGrid(
        heights=dem.heights[::step, ::step],
        lats=dem.lats[::step],
        lons=dem.lons[::step],
        zoom=dem.zoom,
        layer=dem.layer,
        origin_note=dem.origin_note + f" subsample x{step}",
    )
