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
    # Honmura yakisugi / plaster: dark charred cedar brown (literature: 焼杉)
    _set_color(bsdf, (0.055, 0.045, 0.035), roughness=0.82)

    nt, bsdf = new("ModernWall")
    _set_color(bsdf, (0.72, 0.71, 0.68), roughness=0.55)

    nt, bsdf = new("Roof")
    _set_color(bsdf, (0.095, 0.105, 0.12), roughness=0.48)  # kawara-like

    nt, bsdf = new("RoofModern")
    _set_color(bsdf, (0.18, 0.19, 0.21), roughness=0.45)

    nt, bsdf = new("ResidentialGround")
    _set_color(bsdf, (0.38, 0.34, 0.28), roughness=0.9)
    _noise_bump(nt, bsdf, scale=20.0, strength=0.06)

    nt, bsdf = new("Sand")
    _set_color(bsdf, (0.62, 0.55, 0.40), roughness=0.88)

    nt, bsdf = new("Rock")
    _set_color(bsdf, (0.35, 0.34, 0.32), roughness=0.85)
    _noise_bump(nt, bsdf, scale=14.0, strength=0.22)

    nt, bsdf = new("Water")
    _set_color(bsdf, (0.018, 0.055, 0.073), roughness=0.24, specular=0.7)
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = 0.1
    elif "Transmission" in bsdf.inputs:
        bsdf.inputs["Transmission"].default_value = 0.1
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = 1.333
    if "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = 1.0
    if hasattr(mats["Water"], "use_screen_refraction"):
        mats["Water"].use_screen_refraction = True
    _noise_bump(nt, bsdf, scale=40.0, strength=0.04)

    coords=nt.nodes.new('ShaderNodeTexCoord')
    for node in nt.nodes:
        if node.type=='TEX_NOISE':
            node.inputs['Scale'].default_value=0.65
            nt.links.new(coords.outputs['Object'],node.inputs['Vector'])
        elif node.type=='BUMP':
            node.inputs['Strength'].default_value=.18
            node.inputs['Distance'].default_value=.045
    nt, bsdf = new("Foliage")
    _set_color(bsdf, (0.045, 0.14, 0.019), roughness=0.85)

    nt, bsdf = new("Trunk")
    _set_color(bsdf, (0.18, 0.10, 0.06), roughness=0.9)

    nt, bsdf = new("Glass")
    _set_color(bsdf, (0.8, 0.9, 0.95), roughness=0.05)
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = 0.9
    if "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = 0.35
    if hasattr(mats["Glass"], "blend_method"):
        mats["Glass"].blend_method = "BLEND"

    nt, bsdf = new("Steel")
    _set_color(bsdf, (0.55, 0.56, 0.58), roughness=0.35, metallic=0.85)

    nt, bsdf = new("Placeholder")
    _set_color(bsdf, (0.85, 0.15, 0.15), roughness=0.4)

    nt, bsdf = new("BlackPlaster")
    _set_color(bsdf,(0.025,0.027,0.029),roughness=0.87)
    _noise_bump(nt,bsdf,scale=35.0,strength=0.03)
    nt, bsdf = new("WindowDark")
    _set_color(bsdf, (0.035, 0.065, 0.075), roughness=0.23, metallic=0.25)
    # Coordinates in metres prevent a whole facade being treated as one board.
    for name in ('TraditionalWall','Concrete','Roof','RoofModern','ModernWall'):
        mat=mats[name]; nt=mat.node_tree
        bsdf=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
        tex=nt.nodes.new('ShaderNodeTexNoise')
        tex.inputs['Scale'].default_value=7.0 if name!='TraditionalWall' else 25.0
        tex.inputs['Detail'].default_value=3
        coord=nt.nodes.new('ShaderNodeTexCoord')
        nt.links.new(coord.outputs['Object'],tex.inputs['Vector'])
        bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=0.18
        bump.inputs['Distance'].default_value=0.012
        nt.links.new(tex.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
    return mats
