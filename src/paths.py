from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    return ROOT / "data"


def dem_dir() -> Path:
    p = data_dir() / "dem"
    p.mkdir(parents=True, exist_ok=True)
    return p


def osm_dir() -> Path:
    p = data_dir() / "osm"
    p.mkdir(parents=True, exist_ok=True)
    return p


def cache_dir() -> Path:
    p = data_dir() / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p


def assets_dir() -> Path:
    return ROOT / "assets"


def landmark_assets_dir() -> Path:
    p = assets_dir() / "landmarks"
    p.mkdir(parents=True, exist_ok=True)
    return p


def output_dir() -> Path:
    p = ROOT / "output"
    p.mkdir(parents=True, exist_ok=True)
    return p


def previews_dir() -> Path:
    p = output_dir() / "previews"
    p.mkdir(parents=True, exist_ok=True)
    return p
