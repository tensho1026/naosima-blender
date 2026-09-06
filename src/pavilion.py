"""Photo-informed faceted mesh pavilion; facet topology remains an approximation."""
import math
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from .bpy_utils import collection,link_object
from .mesh_batch import Parts


def build_pavilion(crs):
    from .individual_buildings import _material
    x,y=crs.to_xy(34.4558431,133.9754375)
    terrain=bpy.data.objects['Terrain']
    hit=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get()).ray_cast(Vector((x,y,100)),Vector((0,0,-1)))[0]
    z=hit.z if hit else 1.0
    if not terrain.get('pavilion_site_refined'):
        previous=terrain.data.attributes.get('pavilion_ground_before_grading')
        if previous:
            for item,vertex in zip(previous.data,terrain.data.vertices):vertex.co.z=item.value
        site=bmesh.new();site.from_mesh(terrain.data)
        for cuts in (4,2):
            selected=set()
            for face in site.faces:
                xs=[v.co.x for v in face.verts];ys=[v.co.y for v in face.verts]
                if max(xs)<x-7 or min(xs)>x+7 or max(ys)<y-7 or min(ys)>y+7:continue
                selected.update(e for e in face.edges if e.calc_length()>2.0)
            if selected:bmesh.ops.subdivide_edges(site,edges=list(selected),cuts=cuts,use_grid_fill=True)
        bmesh.ops.triangulate(site,faces=[f for f in site.faces if len(f.verts)>3])
        site.to_mesh(terrain.data);site.free();terrain.data.update()
        terrain['pavilion_site_refined']=True
    # Coarse DEM tilts across this small level installation. Keep a baseline so
    # repeated rebuilds do not repeatedly flatten the transition around the site.
    baseline=terrain.data.attributes.get('pavilion_ground_before_grading')
    if baseline is None:
        baseline=terrain.data.attributes.new('pavilion_ground_before_grading','FLOAT','POINT')
        for item,vertex in zip(baseline.data,terrain.data.vertices):item.value=vertex.co.z
    saved_level=terrain.get('pavilion_ground_level')
    if saved_level is not None:z=saved_level
    terrain['pavilion_ground_level']=z
    for item,vertex in zip(baseline.data,terrain.data.vertices):
        distance=math.hypot(max(0,abs(vertex.co.x-x)-4.4),max(0,abs(vertex.co.y-y)-4.0))
        if distance<2:
            weight=1-distance/2
            vertex.co.z=item.value*(1-weight)+(z-.12)*weight
    terrain.data.update()
    root=bpy.data.objects.new('NaoshimaPavilion_Exterior',None);link_object(root,collection('Landmarks'))
    root.location=(x,y,z)
    root['source']='https://worldstainless.org/wp-content/uploads/2025/02/Naoshima_Pavilion.pdf'
    root['material_reference']='https://www.takenaka-kanaami.com/mesh/'
    root['position_source']='https://www.openstreetmap.org/node/4265985799'
    root['fidelity']='Asymmetric silhouette and translucent metal mesh from photographs; 8.5x7.5x6.3m scale, exact facets, opening orientation, wire gauge and levelled site estimated. NOT complete replica.'
    white=_material('Pavilion_white_coated_mesh',(.78,.80,.77),.46)
    gravel=_material('Pavilion_gravel',(.42,.41,.33),.96)
    # Explicit profile tiers: a broad floating body tapering toward the offset peak.
    tiers=[(.25,2.00,1.65,-.3),(.8,3.10,2.75,-.1),(1.6,4.25,3.75,0),
           (2.7,4.00,3.52,.08),(3.8,3.52,3.0,.35),(4.65,2.80,2.25,.66),
           (5.4,1.75,1.43,1.04)]
    bm=bmesh.new();n=18
    for j,(height,rx,ry,shift) in enumerate(tiers):
        for i in range(n):
            theta=(i+(j%2)*.41)*math.tau/n
            variation=1+.055*math.sin(i*2.7+j*.9)
            zz=height+.11*math.sin(i*1.7+j)
            # Lower left shoulder and higher right crest visible in the source.
            if j>=3:zz-=max(0,-math.cos(theta))*.48
            bm.verts.new((shift+rx*math.cos(theta)*variation,ry*math.sin(theta)*variation,zz))
    bm.verts.new((1.40,.30,6.30))
    bmesh.ops.convex_hull(bm,input=list(bm.verts),use_existing_faces=False)
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    triangles=[]
    for face in bm.faces:
        centre=face.calc_center_median()
        # Entrance notch and open underside, inferred from the front photograph.
        if centre.y<-.8 and abs(centre.x)<1.15 and centre.z<2.05:continue
        if centre.z<.35:continue
        triangles.append([v.co.copy() for v in face.verts])
    bm.free()
    frames=Parts();mesh=Parts();edges=set();wires=0
    for tri in triangles:
        a,b,c=tri
        for p,q in [(a,b),(b,c),(c,a)]:
            key=tuple(sorted((tuple(round(v,5) for v in p),tuple(round(v,5) for v in q))))
            if key not in edges:frames.tube('White',p,q,.012,8);edges.add(key)
        u=(b-a).normalized();normal=(b-a).cross(c-a).normalized();v=normal.cross(u)
        planar=[(0.,0.),((b-a).dot(u),(b-a).dot(v)),((c-a).dot(u),(c-a).dot(v))]
        # Two perpendicular wire families clipped to each triangular panel.
        for axis in (0,1):
            lo=min(p[axis] for p in planar);hi=max(p[axis] for p in planar)
            for k in range(math.ceil(lo/.045),math.floor(hi/.045)+1):
                value=k*.045;crossings=[]
                for p,q in zip(planar,planar[1:]+planar[:1]):
                    if (p[axis]<=value<q[axis]) or (q[axis]<=value<p[axis]):
                        t=(value-p[axis])/(q[axis]-p[axis])
                        crossings.append((p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])))
                if len(crossings)==2:
                    p,q=[a+u*s+v*t+normal*(.0015 if axis else 0) for s,t in crossings]
                    if (q-p).length>.004:mesh.tube('White',p,q,.0018,4);wires+=1
    frames.finish('PanelFrames',root,{'White':white});mesh.finish('WovenMesh',root,{'White':white})
    base=Parts();points=[(0,0,.20)];faces=[];segments=48
    for rx,ry,h in [(3.2,2.8,.20),(4.0,3.5,.02),(4.3,3.9,-.115)]:
        points.extend((rx*math.cos(i*math.tau/segments),ry*math.sin(i*math.tau/segments),h) for i in range(segments))
    for i in range(segments):faces.append((0,1+i,1+(i+1)%segments))
    for j in range(2):
        start=1+j*segments
        for i in range(segments):faces.append((start+i,start+segments+i,start+segments+(i+1)%segments,start+(i+1)%segments))
    base.add('Gravel',points,faces)
    base.finish('Site',root,{'Gravel':gravel})
    root['panel_count_estimated']=len(triangles);root['wire_count']=wires
    root['mesh_spacing_estimated_m']=.045
    return root
