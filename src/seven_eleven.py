"""Naoshima store after relocation, based on the dated 2024 frontage photograph."""
import math
import bpy
from mathutils import Vector
from .coordinates import drop_closing
from .bpy_utils import collection,link_object
from .mesh_batch import Parts


def build_seven_eleven(way,crs,sampler):
    from .individual_buildings import _material
    ring=drop_closing([crs.to_xy(*p) for p in way.coords]);a,b=Vector(ring[1]),Vector(ring[0])
    u=(b-a).normalized();width=(b-a).length;depth=(Vector(ring[2])-a).length
    root=bpy.data.objects.new('Individual_SevenEleven_1307364185',None);link_object(root,collection('IndividualBuildings'))
    root.location=(*a,max(sampler.height_at_xy(*p) for p in ring));root.rotation_euler.z=math.atan2(u.y,u.x)
    root['osm_id']=way.id;root['source']='https://www.postmap.org/photo/1206913'
    root['reference_date']='2024-12-18';root['address_reference']='https://location.sevenbank.co.jp/sevenbank/spot/detail?code=0000033134'
    root['fidelity']='Relocated-store frontage photo; footprint OSM. Heights, bay widths and brick pattern inferred; rear and rooftop plant unknown.'
    mats={k:_material('SevenNaoshima_'+k,c,r) for k,c,r in [
        ('Wall',(.58,.57,.52),.82),('Brick',(.37,.19,.075),.83),('Roof',(.10,.11,.11),.7),
        ('White',(.8,.8,.75),.5),('Orange',(.94,.28,.016),.4),('Green',(.012,.32,.105),.4),
        ('Red',(.62,.025,.038),.4),('Glass',(.23,.30,.28),.16),('Frost',(.48,.52,.49),.32),
        ('Metal',(.31,.34,.33),.24),('Yellow',(.75,.48,.018),.7),('Concrete',(.31,.32,.31),.92),('Asphalt',(.085,.087,.082),.96)]}
    nt=mats['Brick'].node_tree;n=nt.nodes;l=nt.links
    coord=n.new('ShaderNodeTexCoord');sep=n.new('ShaderNodeSeparateXYZ');combine=n.new('ShaderNodeCombineXYZ')
    l.new(coord.outputs['Object'],sep.inputs[0]);l.new(sep.outputs['X'],combine.inputs['X']);l.new(sep.outputs['Z'],combine.inputs['Y'])
    brick=n.new('ShaderNodeTexBrick');brick.inputs['Scale'].default_value=1
    brick.inputs['Brick Width'].default_value=.34;brick.inputs['Row Height'].default_value=.11;brick.inputs['Mortar Size'].default_value=.006
    brick.inputs['Color1'].default_value=(.39,.18,.075,1);brick.inputs['Color2'].default_value=(.61,.40,.21,1);brick.inputs['Mortar'].default_value=(.26,.23,.18,1)
    l.new(combine.outputs[0],brick.inputs['Vector']);bsdf=next(q for q in n if q.type=='BSDF_PRINCIPLED');l.new(brick.outputs['Color'],bsdf.inputs['Base Color'])
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.16;bump.inputs['Distance'].default_value=.004
    l.new(brick.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
    p=Parts();h=3.65;brick_start=width-3.35
    p.box('Wall',(width/2,-depth, h/2),(width,.15,h))
    for x in (0,width):p.box('Wall',(x,-depth/2,h/2),(.15,depth,h))
    p.box('Roof',(width/2,-depth/2,h),(width+.24,depth+.24,.16))
    p.box('Brick',((width+brick_start)/2,0,h/2),(width-brick_start,.16,h))
    # Front glazing extends under the projecting white fascia; door is at photo right.
    p.box('Concrete',(width/2,.42,.07),(width,1.2,.14))
    p.box('Asphalt',(width/2,1.62,-.36),(width+.3,3.32,.72))
    p.box('White',(brick_start/2,.44,3.13),(brick_start+.10,1.05,.62))
    for key,z,th in [('Orange',3.34,.075),('Green',3.17,.12),('Red',3.00,.075)]:
        p.box(key,(brick_start/2,.976,z),(brick_start-.12,.025,th))
    bounds=[.12,1.60,2.72,3.83,5.23,6.75,8.23,9.75,brick_start]
    bounds=sorted(set(x for x in bounds if x<=brick_start))
    for left,right in zip(bounds,bounds[1:]):
        p.box('Glass',((left+right)/2,.01,1.44),(right-left-.055,.045,2.70))
        p.box('Frost',((left+right)/2,.043,.73),(right-left-.06,.02,1.12))
    for x in bounds:p.box('Metal',(x,.07,1.42),(.055,.1,2.77))
    for z in (.15,1.28,2.13,2.80):p.box('Metal',(brick_start/2,.075,z),(brick_start,.10,.045))
    # Entry portal and stainless impact rails visible along this particular frontage.
    for x in (1.60,3.83):p.box('Metal',(x,.27,1.42),(.085,.43,2.76))
    p.box('Metal',(2.715,.27,2.78),(2.35,.43,.15))
    for x in (1.3,4.3,7.1,10.0,width-1.5):
        p.tube('Metal',(x-.55,1.05,.15),(x-.55,1.05,.78),.035)
        p.tube('Metal',(x-.55,1.05,.78),(x+.55,1.05,.78),.035)
        p.tube('Metal',(x+.55,1.05,.78),(x+.55,1.05,.15),.035)
        p.box('Yellow',(x,2.30,.105),(1.00,.22,.21))
    # Red roadside post box at the left brick pier, as photographed after relocation.
    p.tube('Metal',(width-.45,.65,.1),(width-.45,.65,1.05),.065)
    p.box('Red',(width-.45,.65,1.17),(.43,.32,.52))
    p.box('White',(width-.45,.825,1.17),(.22,.015,.19))
    p.box('Roof',(width-.45,.83,1.32),(.23,.02,.035))
    p.box('White',(2.7,1.001,3.14),(.60,.025,.58))
    p.finish('Exterior',root,mats)
    for body,pos,size,key in [('7',(2.7,1.020,3.02),.54,'Red'),('ELEVEN',(2.7,1.026,2.99),.075,'Green')]:
        curve=bpy.data.curves.new('SevenNaoshimaSign','FONT');curve.body=body;curve.size=size;curve.align_x='CENTER'
        obj=bpy.data.objects.new('SevenNaoshimaSign',curve);link_object(obj,collection('IndividualBuildings'));obj.parent=root;obj.location=pos;obj.rotation_euler=(math.pi/2,0,math.pi);curve.materials.append(mats[key])
    return root
