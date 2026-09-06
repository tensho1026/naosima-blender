"""Yellow Pumpkin exterior study from the 2022 Benesse reference photograph."""
import math
import bpy
from mathutils import Vector
from .bpy_utils import collection,link_object,new_mesh_object
from .mesh_batch import Parts

SOURCE='https://benesse-artsite.jp/special2022/pumpkin.html'


def build_yellow_pumpkin(x,y,osm,crs):
    from .individual_buildings import _material
    from .building_geometry import extrude
    from .coordinates import drop_closing
    col=collection('Landmarks')
    root=bpy.data.objects.new('YellowPumpkin_Exterior',None);link_object(root,col)
    root.location=(x,y,.90)
    root['source']=SOURCE;root['artwork']='草間彌生「南瓜」2022年復元制作'
    root['fidelity']='Photo-based lobed silhouette and longitudinal dot hierarchy; approx 2.5m width/2m height from published original dimensions. Exact dot positions, surface and 2022 dimensions not surveyed.'
    yellow=_material('YellowPumpkin_yellow',(.95,.61,.006),.27)
    black=_material('YellowPumpkin_black',(.006,.008,.006),.29)
    concrete=_material('YellowPumpkin_pier_concrete',(.39,.38,.33),.92)
    rust=_material('YellowPumpkin_bollard_rust',(.19,.095,.043),.88)
    # The mapped pier is separate from the simplified coastline and DEM terrain.
    pier=next(w for w in osm.ways if w.id==231864310)
    ring=drop_closing([crs.to_xy(*p) for p in pier.coords])
    v,f=extrude(ring,-.2,1.1)
    quay=new_mesh_object('YellowPumpkin_Pier_OSM_231864310',v,f,col);quay.data.materials.append(concrete)
    quay['source']='https://www.openstreetmap.org/way/231864310';quay['fidelity']='Survey-tagged OSM plan; 0.9m deck level and thickness estimated, tide not measured'
    # Eight lobes with a flat contact ring and fuller lower body, unlike the red artwork.
    profile=[(0,.83),(.08,1.03),(.30,1.15),(.58,1.14),(.85,1.04),(1.13,.87),(1.40,.67),(1.55,.46),(1.65,.20)]
    slopes=[(s-r)/(b-a) for (a,r),(b,s) in zip(profile,profile[1:])]
    derivatives=[slopes[0]]+[0 if a*b<=0 else 2*a*b/(a+b) for a,b in zip(slopes,slopes[1:])]+[slopes[-1]]
    def radius(z):
        z=max(0,min(1.65,z))
        for i,((a,r),(b,s)) in enumerate(zip(profile,profile[1:])):
            if a<=z<=b:
                t=(z-a)/(b-a)
                return (2*t**3-3*t*t+1)*r+(t**3-2*t*t+t)*(b-a)*derivatives[i]+(-2*t**3+3*t*t)*s+(t**3-t*t)*(b-a)*derivatives[i+1]
        return profile[-1][1]
    def surface(theta,z,offset=0):
        r=radius(z)*(1+.087*math.cos(8*theta))+offset
        return (r*math.cos(theta),r*math.sin(theta),z)
    segments=192;levels=100;verts=[];faces=[]
    for j in range(levels+1):
        for i in range(segments):verts.append(surface(i*math.tau/segments,1.65*j/levels))
    for j in range(levels):
        for i in range(segments):
            a=j*segments+i;b=j*segments+(i+1)%segments;faces.append((a,b,b+segments,a+segments))
    faces.extend([tuple(range(segments-1,-1,-1)),tuple(levels*segments+i for i in range(segments))])
    body=new_mesh_object('YellowPumpkin_LobedBody',verts,faces,col);body.parent=root;body.data.materials.append(yellow)
    for f in body.data.polygons:f.use_smooth=len(f.vertices)==4
    dots=Parts();count=0
    columns=[(-.43,.004),(-.35,.008),(-.26,.013),(-.14,.026),(0,.051),(.14,.026),(.26,.013),(.35,.008),(.43,.004)]
    for lobe in range(8):
        for ci,(fraction,size) in enumerate(columns):
            theta=(lobe+fraction)*math.tau/8
            rows=min(90,int(1.6/(size*2.35)))
            for row in range(rows):
                z=.035+(row+.5+(ci%2)*.3)*1.55/rows
                if z>1.60:continue
                r=size*min(1,radius(z)/.80)
                patch=[surface(theta,z,.003)];pf=[];around=16;radial=3
                for k in range(1,radial+1):
                    for i in range(around):
                        t=i*math.tau/around;dr=r*k/radial
                        patch.append(surface(theta+dr*math.cos(t)/radius(z),z+dr*math.sin(t),.003))
                for i in range(around):pf.append((0,i+1,(i+1)%around+1))
                for k in range(radial-1):
                    a=1+k*around
                    for i in range(around):pf.append((a+i,a+around+i,a+around+(i+1)%around,a+(i+1)%around))
                dots.add('Black',patch,pf);count+=1
    # Bent black stalk with small yellow spots; curve geometry is inferred from photo.
    centres=[Vector(p) for p in [(0,0,1.62),(-.025,0,1.76),(-.08,0,1.89),(-.19,0,1.98),(-.26,0,2.00)]]
    stalk=Parts()
    for a,b,r in zip(centres,centres[1:],[.092,.083,.076,.069]):stalk.tube('Black',a,b,r,24)
    for idx in range(4):
        a,b=centres[idx:idx+2];axis=(b-a).normalized();u=axis.cross(Vector((0,1,0))).normalized();v=axis.cross(u)
        for t in (.25,.70):
            centre=a.lerp(b,t);rad=[.092,.083,.076,.069][idx]
            for k in range(5):
                angle=k*math.tau/5+idx*.2;normal=u*math.cos(angle)+v*math.sin(angle)
                tangent=-u*math.sin(angle)+v*math.cos(angle)
                p=centre+normal*(rad+.003)
                ring=[tuple(p+(.016*math.cos(j*math.tau/12))*tangent+(.016*math.sin(j*math.tau/12))*axis) for j in range(12)]
                stalk.add('Yellow',ring,[tuple(range(12))])
    for obj in dots.finish('Dots',root,{'Black':black})+stalk.finish('Stalk',root,{'Black':black,'Yellow':yellow}):
        for face in obj.data.polygons:face.use_smooth=True
    root['dot_layout_status']=f'{count} surface-conforming approximate dots; ordered by lobe, not measured one-to-one'
    # Weathered short posts at the seaward end, placement estimated from the photo.
    posts=Parts()
    for xx,yy in [(-2.1,-1.4),(2.1,-1.4),(-2.1,1.4),(2.1,1.4)]:
        posts.tube('Rust',(xx,yy,0),(xx+.035,yy,.30),.085,7)
    posts.finish('MooringPosts',root,{'Rust':rust})
    return root
