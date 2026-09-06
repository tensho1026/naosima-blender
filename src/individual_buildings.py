"""Building-specific exterior models. Never treat inferred bulk facades as verified."""
import math
import bpy
from mathutils import Vector
from .bpy_utils import collection,link_object
from .coordinates import drop_closing
from .mesh_batch import Parts

INDIVIDUAL_BUILDINGS={1361954806:'art_island_center',1361901029:'naopam',1307364185:'seven_eleven',1362137190:'naoshima_bath'}

def _material(name,color,roughness=.7):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True
    n=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    n.inputs['Base Color'].default_value=(*color,1);n.inputs['Roughness'].default_value=roughness
    return m

def _timber_surface(mat,dark,light):
    """Vertical weathered grain in local metre coordinates; not a photo texture."""
    tree=mat.node_tree;tree.nodes.clear();n=tree.nodes;l=tree.links
    out=n.new('ShaderNodeOutputMaterial');bsdf=n.new('ShaderNodeBsdfPrincipled')
    l.new(bsdf.outputs['BSDF'],out.inputs['Surface'])
    coord=n.new('ShaderNodeTexCoord');scale=n.new('ShaderNodeVectorMath');scale.operation='MULTIPLY'
    scale.inputs[1].default_value=(42,42,1.8);l.new(coord.outputs['Object'],scale.inputs[0])
    grain=n.new('ShaderNodeTexNoise');grain.inputs['Scale'].default_value=1;grain.inputs['Detail'].default_value=3
    l.new(scale.outputs['Vector'],grain.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.18;ramp.color_ramp.elements[0].color=(*dark,1)
    ramp.color_ramp.elements[1].position=.83;ramp.color_ramp.elements[1].color=(*light,1)
    l.new(grain.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs['Color'],bsdf.inputs['Base Color'])
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value=.0015
    l.new(grain.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
    rough=n.new('ShaderNodeMapRange');rough.inputs['To Min'].default_value=.62;rough.inputs['To Max'].default_value=.91
    l.new(grain.outputs['Fac'],rough.inputs['Value']);l.new(rough.outputs['Result'],bsdf.inputs['Roughness'])
    mat['fidelity']='Procedural approximation of observed weathered timber; grain is not surveyed'

def art_island_center(way,crs,sampler):
    ring=drop_closing([crs.to_xy(*p) for p in way.coords])
    # Front is edge 3, facing the mapped street to the NW, not the longest edge.
    a,b=Vector(ring[3]),Vector(ring[0]);u=(b-a).normalized();normal=Vector((-u.y,u.x))
    mid=(a+b)/2;z=sampler.height_at_xy(mid.x,mid.y)
    width=(b-a).length;depth=(Vector(ring[2])-a).length
    root=bpy.data.objects.new('Individual_ArtIslandCenter_1361954806',None);link_object(root,collection('IndividualBuildings'))
    root.location=(mid.x,mid.y,z);root.rotation_euler.z=math.atan2(u.y,u.x)
    root['osm_id']=way.id;root['source']='https://naoshima.net/ja/shop/shop-6795/'
    root['reference_photo']='https://naoshima.net/wp-content/uploads/2025/10/3f10d05d7005595b8a64af699c3524b5-1.jpg'
    root['fidelity']='Front elevation photo-referenced; rear/side openings UNKNOWN; dimensions inferred from OSM'
    root['roof_orientation']='Ridge parallel to street facade, observed in reference; not generic longest-edge rule'
    mats={'Wood':_material('ArtIsland_dark_brown_boards',(.055,.034,.025)),
          'Frame':_material('ArtIsland_dark_window_wood',(.035,.022,.017)),
          'Concrete':_material('ArtIsland_weathered_plinth',(.30,.30,.27),.94),
          'Roof':_material('ArtIsland_grey_kawara',(.105,.115,.13),.48),
          'Copper':_material('ArtIsland_redbrown_gutters',(.24,.085,.049),.5),
          'Glass':_material('ArtIsland_shopfront_glazing',(.07,.105,.094),.2),
          'Paper':_material('ArtIsland_warm_sign',(.70,.67,.49)),
          'Chalk':_material('ArtIsland_chalkboard',(.022,.026,.028)),
          'Soil':_material('ArtIsland_planter_soil',(.055,.035,.018)),
          'Leaves':_material('ArtIsland_planter_green',(.08,.24,.035))}
    _timber_surface(mats['Wood'],(.031,.018,.012),(.145,.089,.057))
    glass=next(n for n in mats['Glass'].node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    glass.inputs['Base Color'].default_value=(.91,.96,.93,1)
    glass.inputs['Transmission Weight'].default_value=1;glass.inputs['IOR'].default_value=1.46
    glass.inputs['Roughness'].default_value=.11
    mats['BookRed']=_material('ArtIsland_display_red',(.48,.026,.015))
    mats['BookBlue']=_material('ArtIsland_display_blue',(.025,.12,.33))
    mats['BookYellow']=_material('ArtIsland_display_yellow',(.67,.44,.025))
    p=Parts();half=width/2
    # Side and rear are simple wood envelopes pending matching photographs.
    p.box('Wood',(0,-depth,1.65),(width,.14,3.3))
    for side in (-1,1):p.box('Wood',(side*half,-depth/2,1.65),(.14,depth,3.3))
    p.box('Concrete',(0,-depth/2,.35),(width,depth,.7))
    # Photo: raised four-part display window to the right of a recessed entrance.
    p.box('Concrete',(.92,-.035,.52),(3.98,.13,1.04))
    p.box('Wood',(0,-.035,2.99),(width,.14,.62))
    for left,right in [(-half,-2.65),(-1.45,-1.10),(2.89,half)]:
        if right>left:p.box('Wood',((left+right)/2,0,1.5),(right-left,.16,3))
    # Unequal bays are recorded explicitly, not a building-wide repeated window rule.
    bounds=[-1.10,-.10,.96,1.89,2.89]
    for left,right in zip(bounds,bounds[1:]):
        p.box('Glass',((left+right)/2,.018,1.82),(right-left-.1,.045,1.48))
    for x in bounds:p.box('Frame',(x,.07,1.83),(.085,.12,1.66))
    for h in (1.02,1.15,2.51,2.67):p.box('Frame',(.895,.09,h),(4.16,.15,.095))
    # Only the shallow display visible through the street glazing is represented.
    # Dimensions/layout are inferred, not a reconstruction of the shop interior.
    p.box('Paper',(.89,-.55,1.8),(4.02,.035,1.5))
    for z in (1.23,1.76,2.24):p.box('Frame',(.89,-.27,z),(3.97,.47,.04))
    for x,z,w,h,color in [(-.79,1.25,.23,.37,'Paper'),(-.45,1.25,.20,.31,'BookRed'),
        (-.68,1.78,.29,.39,'Paper'),(-.36,1.78,.15,.32,'BookBlue'),
        (.11,1.25,.18,.32,'BookYellow'),(.37,1.25,.21,.27,'BookBlue'),(.67,1.25,.16,.39,'Paper'),
        (.14,1.78,.16,.27,'BookRed'),(.47,1.78,.31,.32,'Paper'),
        (1.15,1.25,.19,.32,'BookRed'),(1.38,1.25,.12,.34,'BookYellow'),(1.58,1.25,.17,.28,'BookBlue'),
        (1.17,1.78,.24,.31,'Paper'),(1.52,1.78,.14,.29,'BookYellow'),
        (2.10,1.25,.23,.35,'BookBlue'),(2.40,1.25,.15,.37,'BookRed'),(2.64,1.25,.14,.29,'Paper')]:
        p.box(color,(x,-.19,z+h/2),(w,.12,h))
    p.box('Frame',(-2.10,.04,1.42),(1.17,.12,2.36));p.box('Glass',(-2.10,.12,1.61),(.91,.04,1.74))
    p.box('Concrete',(-2.1,.62,.095),(1.49,1.08,.19))
    p.box('Concrete',(-2.1,.28,.225),(1.39,.54,.26))
    for x in (-2.72,-1.49):p.box('Wood',(x,.17,1.25),(.13,.22,2.5))
    p.box('Paper',(-1.42,.19,1.91),(.35,.04,.77))
    # Main roof has a ridge parallel to the six-metre shopfront.
    v=[(-half-.3,.4,3.25),(half+.3,.4,3.25),(-half-.3,-depth/2,4.6),(half+.3,-depth/2,4.6),(-half-.3,-depth-.35,3.25),(half+.3,-depth-.35,3.25)]
    p.add('Roof',v,[(0,1,3,2),(2,3,5,4)])
    # Close the timber gables: the roof envelope must not expose a triangular void.
    for side in (-1,1):
        points=[(side*half,0,3.25),(side*half,-depth,3.25),(side*half,-depth/2,4.6)]
        p.add('Wood',points,[(0,1,2) if side==1 else (2,1,0)])
    for x in (-half-.3,half+.3):p.tube('Roof',(x,.4,3.25),(x,-depth/2,4.6),.08)
    p.tube('Roof',(-half-.3,-depth/2,4.64),(half+.3,-depth/2,4.64),.12)
    # Small gabled doorway canopy seen on the left in the reference photograph.
    x=-2.1;left=x-1.03;right=x+1.03
    p.add('Roof',[(left,-.1,2.62),(left,1.05,2.62),(x,-.1,3.45),(x,1.05,3.45),(right,-.1,2.62),(right,1.05,2.62)],[(0,2,3,1),(2,4,5,3)])
    # Curved tile courses on the photographed doorway canopy only.
    # Main-roof tile layout remains unverified; do not extrapolate this detail.
    for side in (-1,1):
        for course in range(4):
            start=course*1.03/4;end=min(1.07,(course+1)*1.03/4+.035)
            for column in range(5):
                yc=-.1+column*.23
                verts=[]
                for distance in (start,end):
                    for segment in range(9):
                        t=segment/8
                        verts.append((x+side*distance,yc+t*.23,3.45-distance*.83/1.03+.025+.035*math.sin(t*math.pi)))
                faces=[(j,j+1,j+10,j+9) for j in range(8)]
                if side>0:faces=[tuple(reversed(f)) for f in faces]
                p.add('Roof',verts,faces)
    p.tube('Roof',(x,-.14,3.50),(x,1.10,3.50),.075,12)
    p.add('Wood',[(left,1.04,2.62),(right,1.04,2.62),(x,1.04,3.45)],[(0,1,2)])
    p.box('Paper',(x,1.055,2.93),(1.1,.03,.29))
    # Copper-coloured rainwater goods and individual board seams.
    p.tube('Copper',(-half-.15,.34,3.24),(half+.18,.34,3.24),.065)
    p.tube('Copper',(-1.3,.31,.14),(-1.3,.31,3.2),.05)
    for side in (-1,1):
        for i in range(int(depth/.18)):
            y=-.1-i*.18;p.tube('Frame',(side*(half+.073),y,.72),(side*(half+.073),y,3.22),.008,4)
    for i in range(int(width/.18)):
        x=-half+.08+i*.18;p.tube('Frame',(x,.045,2.73),(x,.045,3.27),.008,4)
    # Three raised wooden planters and the freestanding chalkboard visible at entry.
    for x,w in [(-.63,.9),(.48,1.1),(1.69,1.05)]:
        p.box('Wood',(x,.6,.2),(w,.46,.4));p.box('Soil',(x,.6,.41),(w-.08,.37,.045))
        for i in range(7):
            q=x-w*.4+i*w*.12
            p.tube('Leaves',(q,.58,.42),(q+.08,.61,.60),.10,6)
    p.box('Wood',(2.66,.66,.34),(.76,.55,.16));p.box('Chalk',(2.66,.61,.83),(.65,.065,.92))
    # Our local +Y points toward the street: +X therefore appears on the viewer's
    # left. Mirror the authored elevation, preserving face winding and footprint.
    for key,(vertices,faces) in p.groups.items():
        p.groups[key]=([(-x,y,z) for x,y,z in vertices],[tuple(reversed(f)) for f in faces])
    p.finish('Exterior',root,mats)
    # Shop lettering is spatially positioned like the source sign; not copied imagery.
    curve=bpy.data.curves.new('ArtIslandDoorSign','FONT');curve.body='ART ISLAND';curve.align_x='CENTER';curve.size=.125
    text=bpy.data.objects.new('ArtIslandDoorSign',curve);link_object(text,collection('IndividualBuildings'));text.parent=root
    text.location=(2.1,1.08,2.90);text.rotation_euler=(math.pi/2,0,math.pi);curve.materials.append(mats['Frame'])
    return root

def naopam(way,crs,sampler):
    """Photo-informed volumes for this footprint; roof partition dimensions inferred."""
    ring=drop_closing([crs.to_xy(*q) for q in way.coords])
    a,b=Vector(ring[7]),Vector(ring[0]);u=(b-a).normalized()
    root=bpy.data.objects.new('Individual_NaoPAM_1361901029',None)
    link_object(root,collection('IndividualBuildings'))
    root.location=(*a,max(sampler.height_at_xy(*q) for q in ring))
    root.rotation_euler.z=math.atan2(u.y,u.x)
    root['osm_id']=way.id
    root['source']='https://naoshima.net/ja/foods/foods-6754/'
    root['fidelity']='Photo-informed timber main house and low wings; volume partition, heights and roof pitches inferred; rear unverified'
    local=[((Vector(q)-a).dot(u),(Vector(q)-a).dot(Vector((-u.y,u.x)))) for q in ring]
    mats={'Wood':_material('NaoPAM_charcoal_timber',(.064,.057,.047)),
          'Seam':_material('NaoPAM_board_joints',(.024,.022,.019)),
          'Roof':_material('NaoPAM_weathered_grey_roof',(.27,.28,.25)),
          'Glass':_material('NaoPAM_upper_glass',(.16,.20,.19),.21),
          'Frame':_material('NaoPAM_brown_sash',(.115,.073,.045)),
          'Concrete':_material('NaoPAM_foundation',(.34,.33,.29)),
          'Metal':_material('NaoPAM_gutters',(.11,.13,.13)),
          'Letter':_material('NaoPAM_lettering',(.48,.50,.43))}
    _timber_surface(mats['Wood'],(.026,.025,.022),(.12,.115,.095))
    p=Parts()
    # Keep every jog in the mapped footprint, rather than substituting a rectangle.
    for (x,y),(xx,yy) in zip(local,local[1:]+local[:1]):
        p.add('Wood',[(x,y,.22),(xx,yy,.22),(xx,yy,2.8),(x,y,2.8)],[(0,1,2,3)])
        p.tube('Concrete',(x,y,.17),(xx,yy,.17),.17,4)
    # Raised main house and lower annex roofs: observed height difference.
    x0,x1=.5,8.6;y0,y1=-1.25,-7.30;z0,z1=2.8,5.65
    p.box('Wood',((x0+x1)/2,(y0+y1)/2,(z0+z1)/2),(x1-x0,y0-y1,z1-z0))
    def roof(xa,xb,ya,yb,eave,rise,mat='Roof'):
        ridge=(ya+yb)/2
        p.add(mat,[(xa,ya,eave),(xb,ya,eave),(xa,ridge,eave+rise),(xb,ridge,eave+rise),(xa,yb,eave),(xb,yb,eave)],[(0,1,3,2),(2,3,5,4)])
        for x in (xa+.18,xb-.18):
            p.add('Wood',[(x,ya+.18,eave),(x,yb-.18,eave),(x,ridge,eave+rise)],[(0,1,2)])
        p.tube('Roof',(xa,ridge,eave+rise+.045),(xb,ridge,eave+rise+.045),.085)
        # Standing seams visible in the pale lower roofs of the reference.
        for i in range(int((xb-xa)/.36)+1):
            x=xa+i*.36
            for end in (ya,yb):p.tube('Roof',(x,end,eave+.025),(x,ridge,eave+rise+.025),.012,4)
        for y in (ya,yb):p.tube('Metal',(xa,y,eave),(xb,y,eave),.05)
    roof(.15,8.95,-.8,-7.7,5.64,1.42)
    roof(8.8,14.62,.25,-11.95,2.78,1.10)
    # Low entrance eave in front of the upper house is a separate sloping surface.
    p.add('Roof',[(-.3,.35,2.62),(8.82,.35,2.62),(-.3,-1.35,3.13),(8.82,-1.35,3.13)],[(0,1,3,2)])
    # Continue the low eave around the exposed street-side return.
    p.add('Roof',[(-.25,-1.35,2.62),(.60,-1.35,3.13),(.60,-7.35,3.13),(-.25,-7.35,2.62)],[(0,1,2,3)])
    p.add('Roof',[(.50,-7.25,3.05),(8.8,-7.25,3.05),(8.8,-7.58,2.76),(.50,-7.58,2.76)],[(0,1,2,3)])
    for i in range(26):
        x=-.3+i*.36;p.tube('Roof',(x,.35,2.64),(x,-1.35,3.15),.012,4)
    roof(-.2,5.25,-7.2,-9.07,2.75,.42)
    # Two distinct upstairs window groups recorded from the street photograph.
    for left,right in [(1.22,3.23),(4.55,6.57)]:
        p.box('Glass',((left+right)/2,-1.17,4.38),(right-left,.035,1.61))
        for x in (left,(left+right)/2,right):p.box('Frame',(x,-1.12,4.38),(.065,.09,1.76))
        for z in (3.52,4.26,4.69,5.25):p.box('Frame',((left+right)/2,-1.1,z),(right-left+.12,.1,.055))
        for x in (left+.48,right-.48):p.box('Frame',(x,-1.1,4.41),(.032,.08,1.61))
    for i in range(42):
        x=x0+.1+i*.19
        if x>x1:break
        for low,high in [(2.88,3.48),(5.29,5.62)]:p.tube('Seam',(x,-1.24,low),(x,-1.24,high),.008,4)
    for i in range(31):
        y=y1+.12+i*.19
        p.tube('Seam',(.492,y,2.85),(.492,y,5.62),.008,4)
    # Ground-level openings stay on the observed frontage; rear remains unasserted.
    for left,right in [(1.0,2.45),(3.15,4.75),(6.00,7.60)]:
        p.box('Glass',((left+right)/2,.026,1.48),(right-left,.045,1.92))
        for x in (left,right):p.box('Frame',(x,.075,1.47),(.10,.13,2.06))
    p.tube('Metal',(-.24,.35,2.62),(8.78,.35,2.62),.06)
    p.tube('Metal',(.15,.20,.25),(.15,.20,2.6),.05)
    for i in range(44):
        y=-.12-i*.2
        if y< -8.8:break
        p.tube('Seam',(-.01,y,.32),(-.01,y,2.58),.008,4)
    p.finish('Exterior',root,mats)
    return root

def build_individual_buildings(cfg,osm,crs,sampler):
    if cfg.location_id!='naoshima':return []
    roots=[]
    for way in osm.ways:
        if way.id==1361954806:roots.append(art_island_center(way,crs,sampler))
        elif way.id==1361901029:roots.append(naopam(way,crs,sampler))
        elif way.id==1307364185:
            from .seven_eleven import build_seven_eleven
            roots.append(build_seven_eleven(way,crs,sampler))
        elif way.id==1362137190:
            from .naoshima_bath import build_naoshima_bath
            roots.append(build_naoshima_bath(way,crs,sampler))
    return roots
