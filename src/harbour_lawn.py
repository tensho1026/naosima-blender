"""Miyanoura quay lawn traced from the georeferenced GSI aerial image."""
import json
import math
from pathlib import Path
import bpy
from .aerial import SOURCE
from .bpy_utils import collection, new_mesh_object


def _split(poly, a, b):
    inside, outside = [], []
    def signed(p):
        return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
    for p,q in zip(poly,poly[1:]+poly[:1]):
        dp,dq=signed(p),signed(q)
        (inside if dp>=0 else outside).append(p)
        if (dp<0)!=(dq<0):
            t=dp/(dp-dq)
            r=tuple(p[k]+t*(q[k]-p[k]) for k in range(3))
            inside.append(r);outside.append(r)
    return inside,outside


def _ccw(ring):
    from .building_geometry import area
    return ring if area(ring)>0 else list(reversed(ring))


def _subtract(poly, ring):
    pieces=[]
    for a,b in zip(ring,ring[1:]+ring[:1]):
        if len(poly)<3:break
        poly,out=_split(poly,a,b)
        if len(out)>=3:pieces.append(out)
    return pieces


def build_harbour_lawn(crs):
    meta=json.loads((Path(__file__).resolve().parents[1]/'data/aerial/miyanoura_detail/metadata.json').read_text())
    # Pixel coordinates in a crop at x=770,y=610 of the 2304x2048 atlas.
    # Traced turf boundary, central walking strip and paved rectangular pad.
    outline=[(133,295),(247,181),(301,235),(191,350)]
    path=[(175,326),(283,216),(288,221),(180,332)]
    pad=[(253,255),(285,223),(306,242),(272,275)]
    circle=[(191+21*math.cos(i*math.tau/48),332+21*math.sin(i*math.tau/48)) for i in range(48)]
    def project(ring):
        out=[]
        for px,py in ring:
            tx=meta['x0']+(770+px)/256;ty=meta['y0']+(610+py)/256
            n=2**meta['zoom']
            lon=tx/n*360-180;lat=math.degrees(math.atan(math.sinh(math.pi*(1-2*ty/n))))
            out.append(crs.to_xy(lat,lon))
        return _ccw(out)
    boundary=project(outline);holes=[project(p) for p in (path,pad,circle)]
    xmin=min(p[0] for p in boundary);xmax=max(p[0] for p in boundary)
    ymin=min(p[1] for p in boundary);ymax=max(p[1] for p in boundary)
    terrain=bpy.data.objects['Terrain'];verts=[];faces=[]
    for face in terrain.data.polygons:
        poly=[tuple(terrain.matrix_world@terrain.data.vertices[i].co) for i in face.vertices]
        if max(p[0] for p in poly)<xmin or min(p[0] for p in poly)>xmax or max(p[1] for p in poly)<ymin or min(p[1] for p in poly)>ymax:continue
        for a,b in zip(boundary,boundary[1:]+boundary[:1]):
            poly,_=_split(poly,a,b)
            if len(poly)<3:break
        pieces=[poly] if len(poly)>=3 else []
        for hole in holes:
            pieces=[p for q in pieces for p in _subtract(q,hole)]
        for p in pieces:
            start=len(verts);verts.extend((x,y,z+.035) for x,y,z in p)
            faces.append(tuple(range(start,len(verts))))
    old=bpy.data.objects.get('Miyanoura_Quay_Lawn_GSI')
    if old:bpy.data.objects.remove(old,do_unlink=True)
    obj=new_mesh_object('Miyanoura_Quay_Lawn_GSI',verts,faces,collection('Landmarks'))
    from .individual_buildings import _material
    mat=_material('Miyanoura_summer_lawn',(.11,.24,.028),.95)
    nt=mat.node_tree;shader=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
    # Rebuilding does not accumulate shader nodes.
    for node in list(nt.nodes):
        if node.type not in {'BSDF_PRINCIPLED','OUTPUT_MATERIAL'}:nt.nodes.remove(node)
    coord=nt.nodes.new('ShaderNodeTexCoord');noise=nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value=.45;noise.inputs['Detail'].default_value=3
    nt.links.new(coord.outputs['Object'],noise.inputs['Vector'])
    ramp=nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color=(.065,.14,.018,1)
    ramp.color_ramp.elements[1].color=(.24,.34,.065,1)
    nt.links.new(noise.outputs['Fac'],ramp.inputs['Fac']);nt.links.new(ramp.outputs['Color'],shader.inputs['Base Color'])
    obj.data.materials.append(mat)
    obj['source']=SOURCE
    obj['fidelity']='Lawn perimeter and paving exclusions hand-traced from GSI orthophoto; summer colour inferred; terrain-following elevation not surveyed'
    return obj
