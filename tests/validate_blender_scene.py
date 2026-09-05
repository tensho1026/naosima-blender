"""Integration invariants; run after generating the refined scene."""
import bpy,json,sys,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.config import naoshima_config
from src.coordinates import CRS
from src.aerial import tile_xy
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'output/naoshima_refined.blend'))
scene=bpy.context.scene
buildings=[o for o in bpy.data.objects if o.name.startswith('bldg_')]
assert len(buildings)==1545,len(buildings)
assert 'bldg_1361954806' not in bpy.data.objects,'Duplicate Art Island Center envelope'
assert 'Individual_ArtIslandCenter_1361954806' in bpy.data.objects
assert 'bldg_1361901029' not in bpy.data.objects,'Duplicate NaoPAM envelope'
assert 'Individual_NaoPAM_1361901029' in bpy.data.objects
ferry=bpy.data.objects['Ferry_Naoshima_2015']
# At the berth the hull must stay over water; do not infer this from its origin.
from mathutils import Vector
from mathutils.bvhtree import BVHTree
coast=bpy.data.objects['Terrain']
bvh=BVHTree.FromObject(coast,bpy.context.evaluated_depsgraph_get())
for x in range(-33,34,3):
    for y in range(-6,7,2):
        point=ferry.matrix_world @ Vector((x,y,100))
        hit=bvh.ray_cast(coast.matrix_world.inverted() @ point,Vector((0,0,-1)))
        assert hit[0] is None,('Ferry intersects land at berth',x,y,hit[0])
assert 'bldg_401738807' not in bpy.data.objects,'Underground museum extruded above ground'
assert 'bldg_75615686' not in bpy.data.objects,'Duplicate terminal envelope'
assert 'MarineStation_OSM_Roof' in bpy.data.objects
assert 'courtyard_18870551_0' in bpy.data.objects
assert bpy.data.objects['bldg_1465161307']['above_ground_floors']==1
assert 'road_57371777' not in bpy.data.objects,'Planned marine highway rendered'
assert all('osm_id' in o and 'source' in o for o in buildings)
for o in buildings:
    z=[v.co.z for v in o.data.vertices]
    assert abs(max(z)-min(z)-o['height_m'])<.001,(o.name,z)
for name,expected in [('TreePrototypes',{'Tree_0','Tree_1','Tree_2'}),('RockPrototypes',{'RockAsset'})]:
    assert {o.name for o in bpy.data.collections[name].objects}==expected
terrain=bpy.data.objects['Terrain']
assert len(terrain.data.vertices)>190000
assert len(terrain.data.materials)==3
crs=CRS(naoshima_config())
uv=terrain.data.uv_layers['GSI_WebMercator']
metas=[json.loads((ROOT/'data/aerial'/name/'metadata.json').read_text()) for name in ('naoshima','honmura_detail','miyanoura_detail')]
for pi in range(0,len(terrain.data.polygons),997):
    poly=terrain.data.polygons[pi]
    meta=metas[poly.material_index];nx=meta['x1']-meta['x0']+1;ny=meta['y1']-meta['y0']+1
    for li in poly.loop_indices:
        p=terrain.data.vertices[terrain.data.loops[li].vertex_index].co
        lat,lon=crs.to_latlon(p.x,p.y);x,y=tile_xy(lat,lon,meta['zoom'])
        wanted=((x-meta['x0'])/nx,1-(y-meta['y0'])/ny)
        assert math.dist(wanted,uv.data[li].uv)<1e-5,(poly.index,wanted,tuple(uv.data[li].uv))
for mat in terrain.data.materials:
    images=[n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE']
    assert len(images)==1 and images[0].packed_file,'Unpacked aerial texture'
for road in bpy.data.collections['Roads'].objects:
    assert all(p.normal.z>0 for p in road.data.polygons),'Inverted road normals'
report=dict(buildings=len(buildings),individual_buildings=2,ferry_berth='water clearance checked',courtyard_buildings=1,marine_station=1,roads=len(bpy.data.collections['Roads'].objects),trees=len(bpy.data.objects['ForestPoints'].data.vertices),terrain_vertices=len(terrain.data.vertices),terrain_faces=len(terrain.data.polygons),packed_aerial_maps=len(terrain.data.materials),status='PASS')
(ROOT/'output/validation_audit.json').write_text(json.dumps(report,indent=2))
print('VALIDATION_PASS',report,flush=True)
