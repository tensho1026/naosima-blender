"""Trace the bath's nautical sign and red kana from its official front photo."""
import math
import bpy
from .bpy_utils import link_object,new_mesh_object
from .building_geometry import triangulate_ring,area


def build_bath_sign(root,mats):
    # Coordinates from the reference crop: x=515,y=65, width=360,height=410.
    # A planar trace preserves the observed silhouette; depth/scale are inferred.
    def point(px,py,depth=-.62):return ((px-174)*.013,depth,3.78+(395-py)*.013)
    def stroke(label,coords,radius,mat,depth=-.62,cyclic=False):
        curve=bpy.data.curves.new('BathSign_'+label,'CURVE');curve.dimensions='3D'
        curve.resolution_u=16;curve.bevel_depth=radius;curve.bevel_resolution=4
        spline=curve.splines.new('BEZIER');spline.bezier_points.add(len(coords)-1)
        for v,(px,py) in zip(spline.bezier_points,coords):
            v.co=point(px,py,depth);v.handle_left_type='AUTO';v.handle_right_type='AUTO'
        spline.use_cyclic_u=cyclic
        obj=bpy.data.objects.new(root.name+'_Sign_'+label,curve);link_object(obj,root.users_collection[0]);obj.parent=root
        curve.materials.append(mat)
        return obj
    def plate(label,outline,mat,depth=-.62):
        # Tessellate front/back independently; concave anchor profile stays filled.
        ring=[(point(x,y)[0],point(x,y)[2]) for x,y in outline]
        if area(ring)<0:ring.reverse()
        n=len(ring);vertices=[(x,d,z) for d in (depth-.035,depth+.035) for x,z in ring]
        triangles=triangulate_ring(ring)
        faces=[tuple(t) for t in triangles]+[tuple(n+i for i in reversed(t)) for t in triangles]
        faces += [(i,i+n,(i+1)%n+n,(i+1)%n) for i in range(n)]
        obj=new_mesh_object(root.name+'_Sign_'+label,vertices,faces,root.users_collection[0]);obj.parent=root;obj.data.materials.append(mat)
        return obj
    white=mats['White']
    plate('LowerBand',[(18,368),(329,368),(329,391),(18,391)],white)
    stroke('PortBow',[(18,384),(18,350),(48,340),(78,322),(105,300),(118,303),(169,333)],.068,white)
    stroke('StarboardBow',[(188,235),(207,264),(231,300),(265,329),(302,347),(329,355),(329,384)],.077,white)
    stroke('LowerRail',[(20,361),(325,361)],.055,white)
    plate('Anchor',[(176,236),(182,233),(190,239),(195,251),(191,272),(190,298),
                    (196,321),(195,332),(186,346),(185,369),(172,369),(172,339),
                    (164,326),(160,313),(169,304),(170,277),(158,267),(166,258),(174,254)],white,-.69)
    stroke('AnchorEye',[(174+12*math.cos(i*math.tau/12),242+12*math.sin(i*math.tau/12)) for i in range(12)],.027,white,-.75,True)
    stroke('CurvedMast',[(175,242),(156,207),(145,176),(139,142),(141,114),(151,89),(157,73)],.020,white,-.48)
    red=mats['Red']
    stroke('KanaLeft',[(149,22),(146,41),(150,49),(158,47),(171,33),(180,29),(188,33),(191,40),(185,46),(176,47)],.025,red,-.48)
    stroke('KanaLoop',[(176,47),(166,41),(166,29),(173,22),(181,23),(181,35),(174,51),(158,72)],.030,red,-.49)
    stroke('KanaInner',[(151,42),(164,39),(177,37)],.019,red,-.51)
    # Rear green arch visible behind the anchor in the photograph.
    stroke('GreenArch',[(130,317),(131,233),(144,191),(164,177),(194,173),(220,183),(232,206),(236,285)],.025,mats['Green'],.15)
    root['sign_fidelity']='Front-photo outline trace of white nautical sign, anchor and red kana; planar reconstruction, scale and depth inferred'
