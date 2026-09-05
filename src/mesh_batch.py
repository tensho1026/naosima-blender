"""Primitive mesh batching; each asset supplies its own measured/observed layout."""
import math
from mathutils import Vector
from .bpy_utils import new_mesh_object

class Parts:
    def __init__(self):self.groups={}
    def add(self,material,vertices,faces):
        v,f=self.groups.setdefault(material,([],[]));start=len(v)
        v.extend(vertices);f.extend(tuple(start+i for i in face) for face in faces)
    def box(self,mat,center,size):
        x,y,z=center;a,b,c=[s/2 for s in size]
        v=[(x+sx*a,y+sy*b,z+sz*c) for sz in (-1,1) for sx,sy in ((-1,-1),(1,-1),(1,1),(-1,1))]
        self.add(mat,v,[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
    def tube(self,mat,start,end,radius=.05,segments=10):
        a,b=Vector(start),Vector(end);axis=(b-a).normalized()
        u=axis.cross(Vector((0,0,1)))
        if u.length<.01:u=axis.cross(Vector((1,0,0)))
        u.normalize();v=axis.cross(u)
        points=[tuple(p+radius*(math.cos(i*math.tau/segments)*u+math.sin(i*math.tau/segments)*v)) for p in (a,b) for i in range(segments)]
        faces=[tuple(range(segments-1,-1,-1)),tuple(range(segments,segments*2))]+[(i,(i+1)%segments,(i+1)%segments+segments,i+segments) for i in range(segments)]
        self.add(mat,points,faces)
    def finish(self,name,root,mats):
        objects=[]
        for key,(vertices,faces) in self.groups.items():
            obj=new_mesh_object(f'{root.name}_{name}_{key}',vertices,faces,root.users_collection[0])
            obj.parent=root;obj.data.materials.append(mats[key]);objects.append(obj)
        return objects
