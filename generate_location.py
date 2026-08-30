#!/usr/bin/env python3
"""Future generic generator:

  blender --background --python generate_location.py -- --lat 34.48 --lon 134.06 --radius 2500 --id teshima

This run still defaults to Naoshima when no coords are given.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))


def _argv(argv):
    return argv[argv.index("--") + 1 :] if "--" in argv else argv[1:]


def main() -> None:
    try:
        import bpy  # noqa: F401
    except ImportError:
        print("Run inside Blender.", file=sys.stderr)
        sys.exit(2)

    p = argparse.ArgumentParser()
    p.add_argument("--lat", type=float, default=None)
    p.add_argument("--lon", type=float, default=None)
    p.add_argument("--radius", type=float, default=3500.0, help="meters")
    p.add_argument("--id", dest="location_id", default="custom")
    p.add_argument("--render-previews", action="store_true")
    p.add_argument("--lod", type=int, default=1)
    args = p.parse_args(_argv(sys.argv))

    from src.config import location_from_circle, naoshima_config
    from src.pipeline import generate

    if args.lat is None or args.lon is None:
        cfg = naoshima_config()
    else:
        cfg = location_from_circle(args.lat, args.lon, args.radius, args.location_id)
    cfg.lod = args.lod
    generate(cfg, do_render=args.render_previews, blend_name=f"{cfg.location_id}.blend")


if __name__ == "__main__":
    main()
