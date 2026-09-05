"""Daytime Seto Inland Sea lighting: sun + Nishita sky. Not theatrical."""

from __future__ import annotations

import math

import bpy

from .bpy_utils import collection, link_object
from .config import LocationConfig


def setup_lighting(cfg: LocationConfig):
    col = collection("Lighting")
    sun_data = bpy.data.lights.new("Sun", "SUN")
    sun_data.energy = 3.2
    sun_data.angle = math.radians(0.53)
    sun_data.color = (1.0, 0.97, 0.92)
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.rotation_euler = (math.radians(28.0), 0.0, math.radians(35.0))
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
    # A clear summer sky for the camera; separately calibrated diffuse illumination.
    coord=nt.nodes.new('ShaderNodeTexCoord')
    split=nt.nodes.new('ShaderNodeSeparateXYZ');nt.links.new(coord.outputs['Normal'],split.inputs[0])
    absolute=nt.nodes.new('ShaderNodeMath');absolute.operation='ABSOLUTE'
    nt.links.new(split.outputs['Z'],absolute.inputs[0])
    ramp=nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color=(.13,.36,.78,1)
    ramp.color_ramp.elements[1].position=.85;ramp.color_ramp.elements[1].color=(.025,.12,.47,1)
    nt.links.new(absolute.outputs[0],ramp.inputs[0])
    visible=nt.nodes.new('ShaderNodeBackground');nt.links.new(ramp.outputs['Color'],visible.inputs['Color'])
    lightpath=nt.nodes.new('ShaderNodeLightPath');mix=nt.nodes.new('ShaderNodeMixShader')
    rays=nt.nodes.new('ShaderNodeMath');rays.operation='MAXIMUM'
    nt.links.new(lightpath.outputs['Is Camera Ray'],rays.inputs[0]);nt.links.new(lightpath.outputs['Is Glossy Ray'],rays.inputs[1])
    nt.links.new(rays.outputs[0],mix.inputs[0]);nt.links.new(bg.outputs[0],mix.inputs[1]);nt.links.new(visible.outputs[0],mix.inputs[2]);nt.links.new(mix.outputs[0],out.inputs['Surface'])
    bpy.context.scene['season_presentation']='Clear summer daylight; artistic weather setting, not a measured date'
    print("[lighting] sun + calibrated ambient daylight")
    return sun
