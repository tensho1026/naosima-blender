#!/usr/bin/env python3
"""Blender entry: blender --background --python generate.py -- [--render-previews] [--lod N]

Must be executed by Blender so `bpy` is available.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _blender_argv(argv: list[str]) -> list[str]:
    if "--" in argv:
        return argv[argv.index("--") + 1 :]
    # When blender --python generate.py extra args may still include blender flags
    return [a for a in argv[1:] if not a.startswith("-") or a.startswith("--")]


def main() -> None:
    try:
        import bpy  # noqa: F401
    except ImportError:
        print("This script must be run with Blender:\n  blender --background --python generate.py", file=sys.stderr)
        sys.exit(2)

    parser = argparse.ArgumentParser(description="Generate Naoshima in Blender from GSI DEM + OSM")
    parser.add_argument("--render-previews", action="store_true", help="Render preview cameras to output/previews/")
    parser.add_argument("--lod", type=int, default=None, choices=(0, 1, 2), help="0 overview, 1 default, 2 denser")
    parser.add_argument("--skip-osm", action="store_true", help="(unused placeholder)")
    args = parser.parse_args(_blender_argv(sys.argv))

    from src.config import naoshima_config
    from src.pipeline import generate

    cfg = naoshima_config()
    if args.lod is not None:
        cfg.lod = args.lod
        if args.lod == 0:
            cfg.max_trees = 2500
            cfg.max_rocks = 0
        elif args.lod == 2:
            cfg.max_trees = 10000
            cfg.dem_zoom = 14
    generate(cfg, do_render=args.render_previews)


if __name__ == "__main__":
    main()
