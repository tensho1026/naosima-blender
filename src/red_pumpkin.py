"""Photo-informed Red Pumpkin study; dot placement is not a surveyed replica."""
import math
import bpy
from mathutils import Vector
from .bpy_utils import collection,link_object,new_mesh_object
from .mesh_batch import Parts

SOURCE='https://travel.my-kagawa.jp/2021/vol67/spot.html'

def build_red_pumpkin(x,y,z):
    from .individual_buildings import _material
    col=collection('Landmarks');root=bpy.data.objects.new('RedPumpkin_Exterior',None);link_object(root,col)
    root.location=(x,y,z);root['source']=SOURCE
    root['artwork']='草間彌生「赤かぼちゃ」2006年 直島・宮浦港緑地'
    root['fidelity']='Approx. 7m diameter / 4m height from prefectural source; lobes, entrance orientation and dot layout inferred from one view; NOT complete replica'
    red=_material('RedPumpkin_gloss_red',(.66,.013,.008),.24)
    black=_material('RedPumpkin_black_dots',(.006,.007,.008),.27)
    low=-math.asin(1.05/2.15)
    def surface(theta,latitude,offset=0):
        radius=3.18*(1+.095*math.cos(8*theta))*math.cos(latitude)+offset
        return (radius*math.cos(theta),radius*math.sin(theta),1.05+2.15*math.sin(latitude))
    rings,segments=80,240;verts=[];faces=[]
    for j in range(rings):
        latitude=low+(math.pi/2-low)*j/rings
        for i in range(segments):verts.append(surface(i*math.tau/segments,latitude))
    verts.append((0,0,3.2));pole=len(verts)-1
    for j in range(rings-1):
        for i in range(segments):
            a=j*segments+i;b=j*segments+(i+1)%segments;faces.append((a,b,b+segments,a+segments))
    for i in range(segments):faces.append(((rings-1)*segments+i,(rings-1)*segments+(i+1)%segments,pole))
    body=new_mesh_object('RedPumpkin_shell',verts,faces,col);body.parent=root;body.data.materials.append(red)
    for f in body.data.polygons:f.use_smooth=True
    bpy.context.view_layer.objects.active=body;body.select_set(True)
    shell=body.modifiers.new('Wall thickness inferred','SOLIDIFY');shell.thickness=.075;shell.offset=-1
    bpy.ops.object.modifier_apply(modifier=shell.name)
    # Open the hollow shell with an upright rounded entrance visible in reference.
    angle=-.35
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=32,location=(0,0,0))
    cutter=bpy.context.object;cutter.name='TEMP_Pumpkin_entrance'
    cutter.location=(2.9*math.cos(angle),2.9*math.sin(angle),1.12)
    cutter.scale=(1.7,.55,1.3);cutter.rotation_euler.z=angle
    # Boolean in world coordinates before the parent translation is applied.
    root.location=(0,0,0);bpy.context.view_layer.update()
    bpy.context.view_layer.objects.active=body
    boolean=body.modifiers.new('Entrance','BOOLEAN');boolean.operation='DIFFERENCE';boolean.object=cutter;boolean.solver='EXACT'
    bpy.ops.object.modifier_apply(modifier=boolean.name);bpy.data.objects.remove(cutter,do_unlink=True)
    root.location=(x,y,z)
    # Surface-conforming dot patches, varying sizes as observed; layout approximate.
    p=Parts()
    for band,(lat,n,radius) in enumerate([(-.32,14,.62),(.04,18,.29),(.37,14,.55),(.73,17,.24),(1.04,12,.19),(1.29,8,.10)]):
        for i in range(n):
            theta=i*math.tau/n+(band%2)*.16
            dt=abs((theta-angle+math.pi)%math.tau-math.pi)
            size=radius*(.64+.52*((i*7+band*3)%11)/10)
            if dt<.38+size/3 and lat<.62:continue
            patch=[surface(theta,lat,.018)];patch_faces=[];around=40;radial=12
            for rr in range(1,radial+1):
                for k in range(around):
                    t=k*math.tau/around;patch_radius=size*rr/radial
                    patch.append(surface(theta+patch_radius*math.cos(t)/(3.18*max(.18,math.cos(lat))),lat+patch_radius*math.sin(t)/2.15,.018))
            for k in range(around):patch_faces.append((0,k+1,(k+1)%around+1))
            for rr in range(radial-1):
                start=1+rr*around
                for k in range(around):
                    a=start+k;b=start+(k+1)%around
                    patch_faces.append((a,a+around,b+around,b))
            p.add('Black',patch,patch_faces)
    # Bent red stalk; connected sections taper toward the dark end cap.
    points=[(0,0,3.11),(.015,0,3.42),(.10,0,3.80),(.38,0,3.88),(.67,0,3.83)]
    for a,b,r in zip(points,points[1:],[.17,.16,.17,.16]):p.tube('Red',a,b,r,20)
    p.tube('Black',(.65,0,3.83),(.69,0,3.825),.158,20)
    for detail in p.finish('Details',root,{'Black':black,'Red':red}):
        for face in detail.data.polygons:face.use_smooth=True
    return root
