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
assert len(buildings)==1544,len(buildings)
assert 'bldg_1361954806' not in bpy.data.objects,'Duplicate Art Island Center envelope'
assert 'Individual_ArtIslandCenter_1361954806' in bpy.data.objects
assert 'bldg_1361901029' not in bpy.data.objects,'Duplicate NaoPAM envelope'
assert 'Individual_NaoPAM_1361901029' in bpy.data.objects
assert 'Individual_SevenEleven_1307364185' in bpy.data.objects
assert 'bldg_1307364185' not in bpy.data.objects
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
station_roof=bpy.data.objects['MarineStation_OSM_Roof']
roof_z=[v.co.z for v in station_roof.data.vertices]
assert abs(max(roof_z)-min(roof_z)-.155)<.001,'Station roof thickness differs from reference'
for obj in bpy.data.objects:
    if obj.name.startswith('MarineStation_Column_'):
        assert abs(obj.dimensions.x-.085)<.001 and abs(obj.dimensions.y-.085)<.001,'Station column too thick'
    if obj.name.startswith('MarineStation_GlassRoom_') and obj.type=='EMPTY':
        glass=[c for c in obj.children if c.type=='MESH' and c.name.endswith('_Glass')]
        import bmesh
        assert len(glass)==1
        bm=bmesh.new();bm.from_mesh(glass[0].data);volume=abs(bm.calc_volume());bm.free()
        extent=glass[0].dimensions
        assert 0<volume/(extent.x*extent.y*extent.z)<.02,'Glazed enclosure incorrectly filled with solid glass'
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
from src.vegetation import _forest_regions
from src.osm import load_or_fetch_osm
from src.coordinates import point_in_ring
forest=bpy.data.objects['ForestPoints']
assert forest.modifiers.get('ForestGN') and forest.modifiers['ForestGN'].node_group
regions=_forest_regions(load_or_fetch_osm(naoshima_config()),crs)
assert {'OSM relation/10643315','OSM relation/18742522','OSM relation/18870504'} <= {s for _,_,s in regions}
for outer,holes,source in regions:
    for hole in holes:
        xmin=min(p[0] for p in hole);xmax=max(p[0] for p in hole)
        ymin=min(p[1] for p in hole);ymax=max(p[1] for p in hole)
        for v in forest.data.vertices:
            x,y=v.co.x,v.co.y
            if xmin<x<xmax and ymin<y<ymax:
                assert not point_in_ring(x,y,hole),('Tree placed in forest clearing',source,x,y)
roof_meta=json.loads((ROOT/'data/aerial/miyanoura_detail/metadata.json').read_text())
roof_count=0
for obj in buildings:
    if 'roof_appearance_source' not in obj:continue
    roof_count+=1
    layer=obj.data.uv_layers['GSI_Roof_WebMercator']
    for poly in obj.data.polygons:
        if obj.data.materials[poly.material_index].name!='GSI_Miyanoura_Observed_Roofs':continue
        assert poly.normal.z>.15,('Aerial photograph painted onto wall',obj.name,poly.index)
        for li in poly.loop_indices:
            u,v=layer.data[li].uv
            tx=roof_meta['x0']+u*(roof_meta['x1']-roof_meta['x0']+1)
            ty=roof_meta['y0']+(1-v)*(roof_meta['y1']-roof_meta['y0']+1)
            n=2**roof_meta['zoom']
            lon=tx/n*360-180;lat=math.degrees(math.atan(math.sinh(math.pi*(1-2*ty/n))))
            x,y=crs.to_xy(lat,lon)
            actual=obj.matrix_world@obj.data.vertices[obj.data.loops[li].vertex_index].co
            assert math.hypot(actual.x-x,actual.y-y)<.01,('Roof image misregistered',obj.name)
assert roof_count==516,roof_count
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
report=dict(buildings=len(buildings),individual_buildings=3,ferry_berth='water clearance checked',courtyard_buildings=1,marine_station=1,roads=len(bpy.data.collections['Roads'].objects),trees=len(bpy.data.objects['ForestPoints'].data.vertices),terrain_vertices=len(terrain.data.vertices),terrain_faces=len(terrain.data.polygons),packed_aerial_maps=len(terrain.data.materials),status='PASS')
(ROOT/'output/validation_audit.json').write_text(json.dumps(report,indent=2))
print('VALIDATION_PASS',report,flush=True)
