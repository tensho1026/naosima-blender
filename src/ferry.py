"""Photo-referenced 2015 Shikoku Kisen NAOSHIMA, built in metres.

Operator photograph establishes identity, decks and livery. Hull dimensions
73.96 x 15 m are corroborated by photographic vessel records; detailed offsets
remain photo estimates, not a shipyard drawing. No claim of complete fidelity.
"""
import math
import bpy
from mathutils import Vector
from .bpy_utils import collection,new_mesh_object,link_object

REFERENCE='https://shikokukisen.com/about_ship/'
PHOTO='https://shikokukisen.com/wp-content/uploads/2026/06/photo_naoshima001.jpg'
DIMENSIONS='https://www.kipio.net/ship-naosima-new.html'

from .mesh_batch import Parts


def materials():
    colors={'White':(.82,.85,.84,.32,0),'Glass':(.018,.055,.065,.17,.35),'Red':(.65,.025,.012,.32,0),'Black':(.009,.014,.016,.65,0),'Deck':(.055,.20,.12,.7,0),'Grey':(.35,.39,.37,.56,.1),'Orange':(.92,.12,.018,.45,0),'Rope':(.3,.21,.105,.95,0)}
    out={}
    for name,(r,g,b,rough,metal) in colors.items():
        m=bpy.data.materials.get('Ferry_'+name) or bpy.data.materials.new('Ferry_'+name);m.use_nodes=True
        p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        p.inputs['Base Color'].default_value=(r,g,b,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
        out[name]=m
    return out

def hull_outline(length,width):
    l,w=length/2,width/2
    return [(-l,-w*.68),(-l+3,-w), (l-3,-w),(l,-w*.68),(l,w*.68),(l-3,w),(-l+3,w),(-l,w*.68)]

def create_hull(cfg,crs):
    col=collection('Ferry_Naoshima')
    for obj in list(col.objects):bpy.data.objects.remove(obj,do_unlink=True)
    root=bpy.data.objects.new('Ferry_Naoshima_2015',None);link_object(root,col)
    # Nose toward the mapped vehicle berth; exact mooring is a scene arrangement.
    angle=math.radians(32)
    bx,by=crs.to_xy(34.45698,133.97400)
    root.location=(bx-math.cos(angle)*39.98-math.sin(angle)*4,by-math.sin(angle)*39.98+math.cos(angle)*4,cfg.sea_level)
    root.rotation_euler.z=angle
    root['vessel']='なおしま / NAOSHIMA (2015)';root['source']=REFERENCE;root['reference_photo']=PHOTO
    root['dimensions_source']=DIMENSIONS;root['hull_length_m']=73.96;root['hull_beam_m']=15.0
    root['fidelity']='Photo-referenced exterior; detailed dimensions and mooring estimated; NOT complete replica'
    mats=materials();p=Parts()
    profiles=[(66,12.5,-1.7),(70.5,14.4,0),(73.96,15,2.2),(73.96,15,3.5)]
    vertices=[(x,y,z) for length,width,z in profiles for x,y in hull_outline(length,width)]
    p.add('White',vertices,[tuple(range(7,-1,-1))]+[(layer*8+i,layer*8+(i+1)%8,(layer+1)*8+(i+1)%8,(layer+1)*8+i) for layer in range(3) for i in range(8)])
    # Vehicle deck, passenger deck, roof; side apertures are genuinely open mesh.
    p.box('Deck',(0,0,2.26),(68,14.7,.16))
    p.box('White',(0,0,6.35),(58,15,.24))
    p.box('White',(0,0,9.15),(52,15,.22))
    p.box('Deck',(-22,0,9.29),(8,14.6,.06))
    p.box('White',(0,0,6.75),(51,14.8,.6))
    p.box('White',(0,0,8.9),(51,14.8,.45))
    for side in (-1,1):
        y=side*7.32
        # Long row of tall vehicle deck openings, as visible in operator photo.
        for i in range(25):
            x=-25+i*2.08
            p.box('White',(x,y,4.87),(.22,.22,2.96))
        # Passenger windows and individual white mullions.
        for i in range(25):
            x=-24.1+i*2.0
            p.box('Glass',(x,y,7.88),(1.56,.10,1.37))
            p.box('White',(x+.87,y,7.88),(.22,.22,1.55))
        p.box('White',(0,y,6.1),(52,.28,.35))
        # Livery locations are individually read as a varying size sequence.
        radii=[.74,.5,.63,.87,.48,.78,.55,.83,.53,.74,.6,.83,.52,.75,.56,.8,.52,.68,.48,.66,.48]
        for i,r in enumerate(radii):
            x=-31.5+i*3.1
            p.tube('Red',(x,side*7.505,2.28),(x,side*7.52,2.28),r,32)
        for x in (-32,32):
            p.tube('Black',(x,side*7.5,3.04),(x,side*7.53,3.04),.18,16)
    # Two end bridge houses, unequal lengths, following the photographed profile.
    for x,length in ((23.0,7.5),(-18.5,8.0)):
        p.box('White',(x,0,9.67),(length,14.2,.82))
        p.box('White',(x,0,11.42),(length+.35,14.65,.22))
        for side in (-1,1):
            for i in range(4):p.box('Glass',(x-length/2+.9+i*(length-1.6)/4,side*7.11,10.63),(1.24,.06,1.13))
        for end in (-1,1):
            for i in range(9):p.box('Glass',(x+end*length/2,i*1.42-5.68,10.63),(.06,1.13,1.13))
        for side in (-1,1):p.box('White',(x,side*7.08,10.63),(length,.1,.1))
    # Bow and stern ramp gates span the vehicle lane; closed in the docked model.
    for sign in (-1,1):
        p.box('White',(sign*36.5,0,3.55),(.24,10.5,3.0))
        for j in range(9):p.box('White',(sign*36.66,j*1.16-4.64,3.55),(.11,.065,2.92))
        p.box('Black',(sign*36.5,0,.35),(.32,11.1,.28))
    # Red paired exhaust towers with black caps, behind the shorter bridge.
    for side in (-1,1):
        p.box('Red',(-25.0,side*6.05,10.05),(2.7,1.75,5.0))
        p.box('Black',(-25.1,side*6.05,12.55),(3,1.93,.48))
        p.box('White',(-25.0,side*6.95,11.93),(2.6,.035,.65))
    p.finish('HullDecks',root,mats)
    return root

def add_details(root):
    mats=materials();p=Parts()
    # Rails include both horizontal courses and posts, not solid parapet boxes.
    for z,xmin,xmax,width in ((9.4,-25,25,7.3),(11.57,19,27,7.1),(11.57,-22.5,-14.5,7.1),(3.58,-35,-27,7.0),(3.58,27,35,7.0)):
        for side in (-1,1):
            for dz in (.42,.93):p.tube('White',(xmin,side*width,z+dz),(xmax,side*width,z+dz),.035)
            steps=math.ceil((xmax-xmin)/1.7)
            for i in range(steps+1):
                x=xmin+(xmax-xmin)*i/steps
                p.tube('White',(x,side*width,z),(x,side*width,z+.98),.04)
    for x in (23,-18.5):
        p.tube('White',(x,0,11.55),(x,0,16.2),.13)
        for z,span in ((13.1,1.6),(14.3,2.3),(15.4,1.3)):
            p.tube('White',(x,-span,z),(x,span,z),.055)
            p.box('White',(x,.25,z+.18),(.5,1.3,.2))
        for y in (-5,5):
            p.tube('Grey',(x,y,11.6),(x,0,15.6),.013,6)
        p.tube('White',(x,0,16.2),(x,0,16.8),.035)
    # Roof seating and life-raft canisters visible from the harbor overlook.
    for side in (-1,1):
        for x in range(-11,17,4):
            p.box('Grey',(x,side*4.1,9.68),(2.0,.5,.12))
            p.box('Grey',(x,side*4.32,9.99),(2.0,.12,.65))
            for dx in (-.65,.65):p.box('White',(x+dx,side*4.1,9.48),(.06,.38,.4))
        for x in (-10,-6,13,17):
            p.tube('White',(x,side*6,9.58),(x+1.6,side*6,9.58),.4,16)
        # Life rings: concentric orange torus approximated by tube segments.
        for x in (-13,12):
            for i in range(32):
                a=i*math.tau/32;b=(i+1)*math.tau/32
                p.tube('Orange',(x+.38*math.cos(a),side*7.4,9.9+.38*math.sin(a)),(x+.38*math.cos(b),side*7.4,9.9+.38*math.sin(b)),.085,6)
    # Exposed stairs at the rear of the passenger saloon.
    for side in (-1,1):
        for i in range(15):p.box('Grey',(-27+i*.22,side*5.7,6.45+i*.2),(.27,1.15,.12))
        for y in (side*5.12,side*6.28):p.tube('White',(-27,y,7.45),(-23.7,y,10.45),.045)
    p.finish('ExteriorDetails',root,mats)
    rope=Parts()
    for side in (-1,1):rope.tube('Rope',(34,side*6,3.0),(44,side*6-4,1.8),.055,8)
    rope.finish('Mooring',root,mats)
    # Ship name uses a real Japanese font if one is available.
    from pathlib import Path
    font=None
    candidates=list(Path('/System/Library/Fonts').glob('*ヒラギノ*W3*'))+list(Path('/System/Library/Fonts').glob('*Hiragino*'))
    if candidates:
        try:font=bpy.data.fonts.load(str(candidates[0]))
        except RuntimeError:pass
    for side in (-1,1):
        curve=bpy.data.curves.new('NaoshimaShipName','FONT');curve.body='なおしま' if side==1 else 'ましおな';curve.size=.73;curve.align_x='CENTER';curve.extrude=.003
        if font:
            curve.font=font
            if hasattr(font,'pack'):
                try:font.pack()
                except RuntimeError:pass
        ob=bpy.data.objects.new('Ferry_ShipName',curve);link_object(ob,collection('Ferry_Naoshima'));ob.parent=root
        ob.location=(-30,side*7.53,3.0);ob.rotation_euler=(math.pi/2,0,math.pi if side==1 else 0)
        curve.materials.append(mats['Black'])
    root['detail_status']='Photo estimated positions: windows, dots, bridges, rails, mast, ramps, funnels. Shipyard drawing unavailable.'

def build_ferry(cfg,crs):
    if cfg.location_id!='naoshima':return
    root=create_hull(cfg,crs);add_details(root)
    print('[ferry] NAOSHIMA 2015 photo-referenced exterior at Miyanoura')
    return root
