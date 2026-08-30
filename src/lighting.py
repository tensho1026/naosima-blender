"""Daytime Seto Inland Sea lighting: sun + Nishita sky. Not theatrical."""

from __future__ import annotations

import math

import bpy

from .bpy_utils import collection, link_object
from .config import LocationConfig


def setup_lighting(cfg: LocationConfig):
    col = collection("Lighting")
    sun_data = bpy.data.lights.new("Sun", "SUN")
    sun_data.energy = 7.5
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
    if "Sun Elevation" in sky.inputs:
        sky.inputs["Sun Elevation"].default_value = math.radians(52.0)
    if "Sun Rotation" in sky.inputs:
        sky.inputs["Sun Rotation"].default_value = math.radians(200.0)
    if "Air" in sky.inputs:
        sky.inputs["Air"].default_value = 0.9
    if "Dust" in sky.inputs:
        sky.inputs["Dust"].default_value = 0.35
    bg.inputs["Strength"].default_value = 0.85
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    print("[lighting] sun + Nishita sky")
    return sun
