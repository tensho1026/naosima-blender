"""Clip planar road polygons around documented, oriented building footprints."""

def area(poly):
    return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1])))/2

def subtract_rectangle(poly,bounds):
    """Disjoint outside pieces; linear interpolation retains each vertex's Z."""
    xmin,ymin,xmax,ymax=bounds
    remaining=list(poly);result=[]
    for axis,value,sign in [(0,xmin,1),(0,xmax,-1),(1,ymin,1),(1,ymax,-1)]:
        if not remaining:break
        inside=[];outside=[]
        for a,b in zip(remaining,remaining[1:]+remaining[:1]):
            da=sign*(a[axis]-value);db=sign*(b[axis]-value)
            (inside if da>=0 else outside).append(a)
            if (da<0)!=(db<0):
                t=da/(da-db);p=tuple(a[k]+t*(b[k]-a[k]) for k in range(3))
                inside.append(p);outside.append(p)
        if len(outside)>=3 and area(outside)>1e-8:result.append(outside)
        remaining=inside
    return result

def clear_station_roads(origin,direction,rectangles):
    import bpy
    from mathutils import Vector
    x,y=origin;dx,dy=direction;changed=0
    for road in bpy.data.collections['Roads'].objects:
        if road.type!='MESH':continue
        points=[]
        for v in road.data.vertices:
            p=road.matrix_world@v.co
            points.append(((p.x-x)*dx+(p.y-y)*dy,-(p.x-x)*dy+(p.y-y)*dx,p.z))
        out=[];indices=[];modified=False
        for face in road.data.polygons:
            pieces=[[points[i] for i in face.vertices]]
            for bounds in rectangles:
                new=[]
                for poly in pieces:
                    xs=[p[0] for p in poly];ys=[p[1] for p in poly]
                    if max(xs)<=bounds[0] or min(xs)>=bounds[2] or max(ys)<=bounds[1] or min(ys)>=bounds[3]:new.append(poly);continue
                    clipped=subtract_rectangle(poly,bounds)
                    if abs(sum(area(p) for p in clipped)-area(poly))>1e-7:modified=True
                    new.extend(clipped)
                pieces=new
            out.extend(pieces);indices.extend([face.material_index]*len(pieces))
        if not modified:continue
        inverse=road.matrix_world.inverted();verts=[];faces=[]
        for poly in out:
            start=len(verts)
            verts.extend(tuple(inverse@Vector((x+u*dx-v*dy,y+u*dy+v*dx,z))) for u,v,z in poly)
            faces.append(tuple(range(start,len(verts))))
        mesh=bpy.data.meshes.new(road.name+'_PlanClipped');mesh.from_pydata(verts,[],faces);mesh.update()
        for mat in road.data.materials:mesh.materials.append(mat)
        for f,mi in zip(mesh.polygons,indices):f.material_index=mi
        old=road.data;road.data=mesh
        if old.users==0:bpy.data.meshes.remove(old)
        road['station_plan_clipping']='Road surface excluded from terminal and service enclosures; diagram-derived bounds'
        changed+=1
    return changed
