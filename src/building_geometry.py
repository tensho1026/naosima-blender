"""Dependency-free footprint geometry. Preserve surveyed outlines and total height."""
import math

def area(ring):
    return sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]+ring[:1]))/2

def rectangle(ring):
    if len(ring)!=4:
        return False
    edges=[(ring[(i+1)%4][0]-p[0],ring[(i+1)%4][1]-p[1]) for i,p in enumerate(ring)]
    lengths=[math.hypot(*e) for e in edges]
    return min(lengths)>0.2 and all(abs(sum(a*b for a,b in zip(edges[i],edges[(i+1)%4])))/(lengths[i]*lengths[(i+1)%4])<0.08 for i in range(4))

def extrude(ring,z0,height,gable=False,roof_height=None):
    ring=list(ring)
    if len(ring)<3 or abs(area(ring))<4:
        return None,None
    if area(ring)<0:
        ring.reverse()
    n=len(ring)
    use_gable=gable and rectangle(ring)
    rh=min(2.2,height*0.28) if roof_height is None else max(0,min(roof_height,height*0.8))
    eave=z0+height-(rh if use_gable else 0)
    verts=[(x,y,z0) for x,y in ring]+[(x,y,eave) for x,y in ring]
    faces=[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    faces.append(tuple(range(n-1,-1,-1)))
    if use_gable:
        # Rotate so edge 0 is a long eave, edge 1 is a short gable.
        lengths=[math.dist(ring[i],ring[(i+1)%4]) for i in range(4)]
        k=max(range(4),key=lambda i:lengths[i])
        a,b,c,d=[4+(k+i)%4 for i in range(4)]
        def midpoint(i,j):
            return ((verts[i][0]+verts[j][0])/2,(verts[i][1]+verts[j][1])/2,z0+height)
        verts.extend([midpoint(b,c),midpoint(d,a)])
        faces.extend([(b,c,8),(d,a,9),(a,b,8,9),(c,d,9,8)])
    else:
        faces.append(tuple(range(n,2*n)))
    return verts,faces


def triangulate_ring(ring):
    """Ear clipping for a simple CCW footprint."""
    remaining=list(range(len(ring)));out=[]
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    for _ in range(len(ring)**2):
        if len(remaining)<=3:break
        for k,b in enumerate(remaining):
            a=remaining[k-1];c=remaining[(k+1)%len(remaining)]
            if cross(ring[a],ring[b],ring[c])<=1e-10:continue
            others=[i for i in remaining if i not in (a,b,c)]
            if any(min(cross(ring[a],ring[b],ring[i]),cross(ring[b],ring[c],ring[i]),cross(ring[c],ring[a],ring[i]))>=-1e-10 for i in others):continue
            out.append((a,b,c));remaining.pop(k);break
        else:raise ValueError('Non-simple or degenerate building footprint')
    if len(remaining)==3:out.append(tuple(remaining))
    return out


def pitched_outline(ring,z0,height,roof_height):
    """Closed two-plane roof on a nonrectangular footprint; ridge is inferred."""
    ring=list(ring)
    if area(ring)<0:ring.reverse()
    k=max(range(len(ring)),key=lambda i:math.dist(ring[i],ring[(i+1)%len(ring)]))
    a,b=ring[k],ring[(k+1)%len(ring)];length=math.dist(a,b)
    nx,ny=-(b[1]-a[1])/length,(b[0]-a[0])/length
    projections=[x*nx+y*ny for x,y in ring];mid=(min(projections)+max(projections))/2
    half=(max(projections)-min(projections))/2
    def signed(p):return p[0]*nx+p[1]*ny-mid
    def roof_z(p):return z0+height-roof_height*abs(signed(p))/half
    verts=[];lookup={}
    def vertex(p,z):
        key=(round(p[0],7),round(p[1],7),round(z,7))
        if key not in lookup:lookup[key]=len(verts);verts.append((p[0],p[1],z))
        return lookup[key]
    bottom=[vertex(p,z0) for p in ring];faces=[tuple(reversed(bottom))]
    def intersection(a,b):
        t=signed(a)/(signed(a)-signed(b))
        return (a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1]))
    for i,a in enumerate(ring):
        b=ring[(i+1)%len(ring)]
        top=[vertex(b,roof_z(b))]
        if signed(a)*signed(b)<-1e-10:
            p=intersection(a,b);top.append(vertex(p,roof_z(p)))
        top.append(vertex(a,roof_z(a)))
        faces.append(tuple([bottom[i],bottom[(i+1)%len(ring)]]+top))
    def clip(poly,side):
        out=[]
        for a,b in zip(poly,poly[1:]+poly[:1]):
            ina=side*signed(a)>=-1e-9;inb=side*signed(b)>=-1e-9
            if ina:out.append(a)
            if ina!=inb:out.append(intersection(a,b))
        return out
    for tri in triangulate_ring(ring):
        for side in (-1,1):
            poly=clip([ring[i] for i in tri],side)
            ids=[vertex(p,roof_z(p)) for p in poly]
            ids=list(dict.fromkeys(ids))
            if len(ids)>=3:faces.append(tuple(ids))
    return verts,faces
