"""OSM multipolygon buildings with open courtyards, no guessed interior rooms."""
from collections import Counter
from .coordinates import drop_closing,point_in_ring
from .bpy_utils import new_mesh_object,assign_material

def member_rings(relation,osm,role):
    ways={w.id:w for w in osm.ways}
    pieces=[list(ways[m['ref']].nodes) for m in relation.members if m['type']=='way' and m.get('role','outer')==role and m['ref'] in ways]
    rings=[]
    while pieces:
        chain=pieces.pop()
        if not chain:continue
        while chain[0]!=chain[-1]:
            for i,p in enumerate(pieces):
                if chain[-1]==p[0]:chain+=p[1:]
                elif chain[-1]==p[-1]:chain+=p[-2::-1]
                elif chain[0]==p[-1]:chain=p[:-1]+chain
                elif chain[0]==p[0]:chain=p[:0:-1]+chain
                else:continue
                pieces.pop(i);break
            else:break
        if len(chain)>=4 and chain[0]==chain[-1] and all(n in osm.nodes for n in chain):
            rings.append([(osm.nodes[n].lat,osm.nodes[n].lon) for n in chain[:-1]])
    return rings

def courtyard_mesh(outer,holes,z0,height):
    from mathutils import Vector
    from mathutils.geometry import delaunay_2d_cdt
    points=[];edges=[]
    for ring in [outer]+holes:
        start=len(points);points.extend(Vector(p) for p in ring)
        edges.extend((start+i,start+(i+1)%len(ring)) for i in range(len(ring)))
    xy,_,tris,*_=delaunay_2d_cdt(points,edges,[],0,1e-6)
    roof=[]
    for f in tris:
        cx=sum(xy[i].x for i in f)/len(f);cy=sum(xy[i].y for i in f)/len(f)
        if not point_in_ring(cx,cy,outer) or any(point_in_ring(cx,cy,h) for h in holes):continue
        a,b,c=(xy[i] for i in f[:3])
        if (b-a).cross(c-a)<0:f=list(reversed(f))
        roof.append(list(f))
    n=len(xy)
    verts=[(p.x,p.y,z) for z in (z0,z0+height) for p in xy]
    faces=[tuple(reversed(f)) for f in roof]+[tuple(i+n for i in f) for f in roof]
    counts=Counter(tuple(sorted((a,b))) for f in roof for a,b in zip(f,f[1:]+f[:1]))
    for f in roof:
        for a,b in zip(f,f[1:]+f[:1]):
            if counts[tuple(sorted((a,b)))]==1:faces.append((a,b,b+n,a+n))
    return verts,faces

def build_courtyards(cfg,osm,crs,sampler,mats,col):
    from .buildings import estimated_height
    audit=[]
    for relation in osm.relations:
        if relation.tags.get('building') in (None,'no'):continue
        outers=[[crs.to_xy(*p) for p in r] for r in member_rings(relation,osm,'outer')]
        holes=[[crs.to_xy(*p) for p in r] for r in member_rings(relation,osm,'inner')]
        height,estimated=estimated_height(relation.tags)
        if height<=0:continue
        for index,outer in enumerate(outers):
            inner=[h for h in holes if point_in_ring(*h[0],outer)]
            z=max(sampler.height_at_xy(*p) for p in outer)
            verts,faces=courtyard_mesh(outer,inner,z,height)
            obj=new_mesh_object(f'courtyard_{relation.id}_{index}',verts,faces,col)
            assign_material(obj,mats['ModernWall']);obj.data.materials.append(mats['RoofModern'])
            for poly in obj.data.polygons:
                if poly.normal.z>.1:poly.material_index=1
            obj['osm_relation_id']=relation.id;obj['source']=f'https://www.openstreetmap.org/relation/{relation.id}'
            obj['height_m']=height;obj['height_status']='ESTIMATED' if estimated else 'OSM height'
            obj['facade_status']='UNKNOWN; footprint and courtyard from OSM'
            audit.append(dict(osm_relation_id=relation.id,source=obj['source'],height_m=height,height_estimated=estimated,courtyards=len(inner)))
    return audit
