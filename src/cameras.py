"""Review cameras aimed at published district centers."""

from __future__ import annotations

import math

import bpy
from mathutils import Vector

from .bpy_utils import collection, link_object
from .config import CAMERA_PRESETS, LocationConfig
from .coordinates import CRS
from .dem import TerrainSampler


def setup_cameras(cfg: LocationConfig, crs: CRS, sampler: TerrainSampler):
    col = collection("Cameras")
    targets = {"center": (cfg.center_lat, cfg.center_lon)}
    for key, dist in cfg.districts.items():
        targets[key] = (dist.lat, dist.lon)

    cameras = []
    for name, preset in CAMERA_PRESETS.items():
        tkey = preset["target"]
        if tkey not in targets and tkey != "center":
            # map Camera_Miyanoura -> miyanoura
            tkey = tkey
        latlon = targets.get(tkey) or targets["center"]
        tx, ty = crs.to_xy(latlon[0], latlon[1])
        tz = sampler.height_at_xy(tx, ty) + 4.0
        ox, oy, oz = preset["offset"]
        cam_data = bpy.data.cameras.new(name)
        cam_data.lens = preset["lens"]
        cam_data.clip_end = 20000.0
        cam_data.clip_start = 0.5
        cam = bpy.data.objects.new(name, cam_data)
        cam.location = (tx + ox, ty + oy, tz + oz)
        direction = Vector((tx, ty, tz)) - Vector(cam.location)
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        link_object(cam, col)
        cameras.append(cam)
        print(f"[cameras] {name} at {tuple(round(c, 1) for c in cam.location)}")

    if cameras:
        bpy.context.scene.camera = cameras[0]
    return cameras
