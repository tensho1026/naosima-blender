"""Procedural Principled BSDF materials for Blender 4.5."""

from __future__ import annotations

from typing import Dict

import bpy


def _principled(mat: bpy.types.Material):
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (400, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (0, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return nt, bsdf


def _set_color(bsdf, color, roughness=0.5, metallic=0.0, specular=0.4):
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = metallic
    # Blender 4.x renamed Specular -> Specular IOR Level
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = specular
    elif "Specular" in bsdf.inputs:
        bsdf.inputs["Specular"].default_value = specular


def _noise_bump(nt, bsdf, scale=12.0, strength=0.08):
    tex = nt.nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = scale
    tex.inputs["Detail"].default_value = 6.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


def make_materials() -> Dict[str, bpy.types.Material]:
    mats: Dict[str, bpy.types.Material] = {}

    def new(name):
        mat = bpy.data.materials.new(name)
        mats[name] = mat
        return _principled(mat)

    nt, bsdf = new("Terrain")
    _set_color(bsdf, (0.42, 0.40, 0.32), roughness=0.92)
    _noise_bump(nt, bsdf, scale=8.0, strength=0.12)

    nt, bsdf = new("Forest")
    _set_color(bsdf, (0.18, 0.28, 0.12), roughness=0.95)
    _noise_bump(nt, bsdf, scale=18.0, strength=0.15)

    nt, bsdf = new("Grass")
    _set_color(bsdf, (0.32, 0.42, 0.16), roughness=0.9)
    _noise_bump(nt, bsdf, scale=25.0, strength=0.08)

    nt, bsdf = new("Road")
    _set_color(bsdf, (0.12, 0.12, 0.12), roughness=0.65)

    nt, bsdf = new("Concrete")
    _set_color(bsdf, (0.55, 0.54, 0.50), roughness=0.72)
    _noise_bump(nt, bsdf, scale=30.0, strength=0.04)

    nt, bsdf = new("TraditionalWall")
    # Honmura: yakisugi / plaster — dark brown-gray + off-white mix represented as warm gray
    _set_color(bsdf, (0.45, 0.40, 0.34), roughness=0.78)

    nt, bsdf = new("ModernWall")
    _set_color(bsdf, (0.78, 0.77, 0.74), roughness=0.55)

    nt, bsdf = new("Roof")
    _set_color(bsdf, (0.28, 0.18, 0.14), roughness=0.7)  # kawara-like

    nt, bsdf = new("RoofModern")
    _set_color(bsdf, (0.22, 0.23, 0.25), roughness=0.45)

    nt, bsdf = new("Sand")
    _set_color(bsdf, (0.62, 0.55, 0.40), roughness=0.88)

    nt, bsdf = new("Rock")
    _set_color(bsdf, (0.35, 0.34, 0.32), roughness=0.85)
    _noise_bump(nt, bsdf, scale=14.0, strength=0.22)

    nt, bsdf = new("Water")
    _set_color(bsdf, (0.05, 0.12, 0.16), roughness=0.06, specular=0.7)
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = 0.85
    elif "Transmission" in bsdf.inputs:
        bsdf.inputs["Transmission"].default_value = 0.85
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = 1.333
    if "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = 0.92
    mats["Water"].use_screen_refraction = True
    _noise_bump(nt, bsdf, scale=40.0, strength=0.04)

    nt, bsdf = new("Foliage")
    _set_color(bsdf, (0.12, 0.28, 0.08), roughness=0.85)

    nt, bsdf = new("Trunk")
    _set_color(bsdf, (0.18, 0.10, 0.06), roughness=0.9)

    nt, bsdf = new("Glass")
    _set_color(bsdf, (0.8, 0.9, 0.95), roughness=0.05)
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = 0.9
    if "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = 0.35
    mats["Glass"].blend_method = "BLEND"

    nt, bsdf = new("Steel")
    _set_color(bsdf, (0.55, 0.56, 0.58), roughness=0.35, metallic=0.85)

    nt, bsdf = new("Placeholder")
    _set_color(bsdf, (0.85, 0.15, 0.15), roughness=0.4)

    return mats
