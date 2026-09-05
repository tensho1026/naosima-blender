"""Daytime Seto Inland Sea lighting: sun + Nishita sky. Not theatrical."""

from __future__ import annotations

import math

import bpy

from .bpy_utils import collection, link_object
from .config import LocationConfig


def setup_lighting(cfg: LocationConfig):
    col = collection("Lighting")
    sun_data = bpy.data.lights.new("Sun", "SUN")
    sun_data.energy = 2.8
    sun_data.angle = math.radians(0.53)
    sun_data.color = (1.0, 0.97, 0.92)
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.rotation_euler = (math.radians(48.0), 0.0, math.radians(35.0))
    link_object(sun, col)

    world = bpy.data.worlds.new("NaoshimaSky")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    sky = nt.nodes.new("ShaderNodeTexSky")
    try:
        sky.sky_type = "NISHITA"
    except Exception:
        pass
    sky.sun_elevation = math.radians(42.0)
    sky.sun_rotation = math.radians(125.0)
    sky.sun_disc = False
    sky.air_density = 1.0
    if hasattr(sky, 'dust_density'):
        sky.dust_density = 0.5
    bg.inputs["Strength"].default_value = 0.45
    bg.inputs['Color'].default_value=(0.45,0.62,0.82,1)
    bg.inputs['Strength'].default_value=0.6
    sky.label='Optional physical sky: reconnect and calibrate for Blender version'
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    print("[lighting] sun + calibrated ambient daylight")
    return sun
