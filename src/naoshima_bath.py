"""Individual photo-based exterior study of Shinro Ohtake's Naoshima Bath."""
import math
import bpy
from mathutils import Vector
from .coordinates import drop_closing
from .bpy_utils import collection,link_object
from .mesh_batch import Parts

PHOTO='https://benesse-artsite.jp/art/naoshimasento_kv_thumb_01_pc.jpg'


def build_naoshima_bath(way,crs,sampler):
    from .individual_buildings import _material
    ring=drop_closing([crs.to_xy(*p) for p in way.coords])
    a,b=Vector(ring[2]),Vector(ring[1]);u=(b-a).normalized();mid=(a+b)/2
    width=(b-a).length;depth=(Vector(ring[0])-b).length
    root=bpy.data.objects.new('Individual_NaoshimaBath_1362137190',None)
    link_object(root,collection('IndividualBuildings'))
    floor=sampler.height_at_xy(*mid)+.12
    terrain=bpy.data.objects.get('Terrain')
    if terrain:
        from mathutils.bvhtree import BVHTree
        hit=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get()).ray_cast(Vector((mid.x,mid.y,200)),Vector((0,0,-1)))[0]
        if hit:floor=hit.z+.12
    root.location=(*mid,floor)
    root.rotation_euler.z=math.atan2(u.y,u.x)
    root['osm_id']=way.id;root['source']='https://benesse-artsite.jp/art/naoshimasento.html'
    root['reference_photo']=PHOTO
    root['location_reference']='https://www.okayama-japan.jp/tw/spot/220 (34.4580417,133.9751151 inside OSM footprint)'
    root['fidelity']='Photo-based front composition and palette. Dimensions, tile motifs, rooftop assemblage and planting approximated; side/rear unverified. NOT complete replica.'
    palette={'White':(.72,.73,.68),'Green':(.018,.22,.075),'Ochre':(.47,.36,.19),
             'Cream':(.54,.58,.40),'Blue':(.028,.16,.32),'Yellow':(.80,.49,.028),
             'Red':(.47,.035,.032),'Pink':(.40,.10,.13),'Glass':(.06,.12,.08),
             'Dark':(.047,.045,.04),'Floor':(.24,.20,.17),'Gold':(.49,.32,.10),
             'Leaf':(.035,.18,.025),'Trunk':(.24,.15,.074)}
    mats={k:_material('NaoshimaBath_'+k,v,.67 if k!='Glass' else .15) for k,v in palette.items()}
    p=Parts();w=width/2;h=3.45
    # Solid side/rear envelope; no inferred interior layout.
    for xx in (-w,w):p.box('Cream',(xx,depth/2,h/2),(.14,depth,h))
    p.box('Cream',(0,depth,h/2),(width,.15,h))
    # Central recessed green double entrance; flanking tiled exterior walls.
    door_half=1.38
    for xx in (-(w+door_half)/2,(w+door_half)/2):
        p.box('Cream',(xx,.12,h/2),(w-door_half,.24,h))
    p.box('Cream',(0,.12,3.10),(2*door_half,.24,.7))
    p.box('Green',(0,.14,1.45),(2.48,.09,2.72))
    for xx in (-.60,.60):
        p.box('Glass',(xx,.075,1.72),(1.08,.035,1.8))
        p.box('Pink',(xx+(.36 if xx>0 else -.36),.048,1.72),(.29,.018,1.77))
    for xx in (-1.24,0,1.24):p.box('Green',(xx,.015,1.45),(.09,.09,2.77))
    for xx in (-.12,.12):p.tube('Gold',(xx,-.10,.99),(xx,-.10,1.51),.023,10)
    for xx in (-1.52,1.52):p.box('White',(xx,-.10,1.48),(.20,.30,2.97))
    p.box('White',(0,-.10,2.96),(3.23,.30,.17))
    p.box('Floor',(0,-.49,.09),(3.65,1.10,.18))
    p.box('White',(0,1.0,3.53),(width+.60,3.10,.24))
    p.box('Dark',(0,depth/2,3.66),(width,depth,.12))
    # Ochre upper room is offset left, with two horizontal sash windows.
    upper_width=width*.44;upper_x=-w+upper_width/2
    p.box('Ochre',(upper_x,4.0,4.97),(upper_width,4.2,2.58))
    p.box('Dark',(upper_x,4.0,6.32),(upper_width+.24,4.42,.14))
    for xx in (upper_x-upper_width*.24,upper_x+upper_width*.24):
        p.box('Glass',(xx,1.86,5.23),(upper_width*.36,.04,.79))
        for z in (4.82,5.64):p.box('Green',(xx,1.80,z),(upper_width*.39,.09,.06))
        for x in (xx-upper_width*.19,xx,xx+upper_width*.19):p.box('Gold',(x,1.80,5.23),(.045,.09,.82))
    # Observed collage palette; arrangements and motifs are explicitly approximations.
    tile_colours=['Cream','Blue','Ochre','White','Red','Yellow','Blue','White']
    tile=.34
    for side in (-1,1):
        x0=-w if side<0 else door_half+.20
        x1=-door_half-.20 if side<0 else w
        columns=int((x1-x0)/tile)
        for i in range(columns):
            for j in range(5):
                xx=x0+(i+.5)*(x1-x0)/columns;zz=.25+(j+.5)*tile
                key=tile_colours[(i*3+j*5+(2 if side>0 else 0))%len(tile_colours)]
                p.box(key,(xx,-.026,zz),((x1-x0)/columns-.012,.026,tile-.012))
                if (i+j)%3==0:
                    r=.095
                    p.add('White',[(xx-r,-.044,zz),(xx,-.044,zz+r),(xx+r,-.044,zz),(xx,-.044,zz-r)],[(0,1,2,3)])
        p.box('White',((x0+x1)/2,-.05,.20),(x1-x0,.13,.12))
    # Green upper panels and small framed plaques on both sides of the doorway.
    for xx,sx in [(-w+1.0,1.5),(2.15,.80),(w-.80,1.25)]:
        p.box('Green',(xx,-.04,2.45),(sx,.035,1.24))
        p.box('White',(xx,-.067,2.30),(sx*.66,.025,.36))
    # White left post and contrasting gold/white and yellow/red right posts.
    for xx in (-w+.40,2.45,w-.45):
        p.box('White',(xx,-.42,3.28),(.67,.67,.18))
        p.tube('White',(xx,-.42,1.14),(xx,-.42,3.22),.19,16)
        p.tube('Gold',(xx,-.42,.15),(xx,-.42,1.14),.21,16)
        p.box('Gold',(xx,-.42,.13),(.53,.53,.20))
    p.tube('Yellow',(w-.45,-.42,1.14),(w-.45,-.42,3.22),.20,16)
    p.tube('Red',(w-.45,-.42,.18),(w-.45,-.42,1.14),.21,16)
    # Open roof railing, white cantilevers and the characteristic nautical sign.
    for xx in [-w+i*.40 for i in range(int(width/.40)+1)]:p.tube('White',(xx,1.10,3.72),(xx,1.10,4.72),.018,6)
    p.tube('White',(-w,1.10,4.72),(w,1.10,4.72),.025,8)
    for xx in (-w+.20,1.75,w-.1):p.box('White',(xx,2.1,4.68),(.48,4.0,.24))
    for i in range(12):
        xx=-1.81+i*.32
        p.tube('Gold',(xx,-.73,3.91),(xx,-.80,3.91),.095,12)
    # Two front palms, with fan-shaped leaflets; approximate plant geometry.
    for tx,ty,height in [(-w-.10,-1.25,5.7),(w-.10,-1.32,9.2)]:
        p.tube('Trunk',(tx,ty,0),(tx+.24,ty,height),.18,14)
        for j in range(12):
            angle=j*math.tau/12;length=2.0 if height<7 else 2.65
            start=Vector((tx+.24,ty,height));tip=start+Vector((math.cos(angle)*length,math.sin(angle)*length,-.65))
            p.tube('Leaf',start,tip,.022,6)
            tangent=Vector((-math.sin(angle),math.cos(angle),0))
            for k in range(1,10):
                centre=start.lerp(tip,k/10);spread=.47*math.sin(k/10*math.pi)
                for sign in (-1,1):
                    end=centre+tangent*spread*sign+Vector((0,0,-.18))
                    p.add('Leaf',[tuple(centre),tuple(end),tuple(centre+(tip-start)*.08)],[(0,1,2)])
    p.finish('Exterior',root,mats)
    from .bath_sign import build_bath_sign
    build_bath_sign(root,mats)
    return root
