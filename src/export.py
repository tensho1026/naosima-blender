from __future__ import annotations

from pathlib import Path

import bpy

from .config import RENDER_RESOLUTION, RENDER_SAMPLES, LocationConfig
from .paths import output_dir, previews_dir


def save_blend(path: Path | None = None) -> Path:
    path = path or (output_dir() / "naoshima.blend")
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    print(f"[export] saved {path}")
    return path


def configure_render(engine: str = "CYCLES") -> None:
    scene = bpy.context.scene
    scene.render.engine = engine
    scene.render.resolution_x = RENDER_RESOLUTION[0]
    scene.render.resolution_y = RENDER_RESOLUTION[1]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    if engine == "CYCLES":
        scene.cycles.device = "CPU"
        scene.cycles.samples = RENDER_SAMPLES
        scene.cycles.use_denoising = True
        scene.cycles.adaptive_min_samples = 4
        scene.cycles.max_bounces = 6
        scene.cycles.diffuse_bounces = 3
        scene.cycles.glossy_bounces = 3
        scene.cycles.transmission_bounces = 4
        scene.cycles.transparent_max_bounces = 4
        scene.cycles.caustics_reflective = False
        scene.cycles.caustics_refractive = False


def render_previews(cfg: LocationConfig) -> None:
    configure_render("CYCLES")
    out = previews_dir()
    mapping = {
        "Camera_Overview": "overview.png",
        "Camera_Miyanoura": "miyanoura.png",
        "Camera_Honmura": "honmura.png",
        "Camera_Benesse": "benesse.png",
    }
    scene = bpy.context.scene
    for cam_name, filename in mapping.items():
        cam = bpy.data.objects.get(cam_name)
        if cam is None:
            print(f"[render] skip missing {cam_name}")
            continue
        scene.camera = cam
        dest = out / filename
        scene.render.filepath = str(dest)
        print(f"[render] {cam_name} -> {dest}")
        bpy.ops.render.render(write_still=True)
    print("[render] previews done")
