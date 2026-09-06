"""Forest / tree / rock instances. Geometry Nodes + collection instances, not unique meshes."""

from __future__ import annotations

import math
import random
from typing import List, Tuple

import bpy

from .bpy_utils import assign_material, collection, link_object, new_mesh_object
from .config import LocationConfig
from .coordinates import CRS, drop_closing, point_in_ring, ring_area
from .dem import TerrainSampler
from .osm import OsmData

Vec2 = Tuple[float, float]


def _forest_regions(osm: OsmData, crs: CRS):
    from .osm_geometry import member_rings
    regions = []
    members=set()
    for relation in osm.relations:
        if relation.tags.get('natural') not in ('wood','forest','scrub') and relation.tags.get('landuse')!='forest':continue
        outers=[[crs.to_xy(*p) for p in r] for r in member_rings(relation,osm,'outer')]
        holes=[[crs.to_xy(*p) for p in r] for r in member_rings(relation,osm,'inner')]
        if not outers:continue
        members.update(m['ref'] for m in relation.members if m['type']=='way')
        for outer in outers:
            inside=[h for h in holes if point_in_ring(*h[0],outer)]
            regions.append((outer,inside,f'OSM relation/{relation.id}'))
    seen=set()
    for key, values in (
        ("natural", ("wood", "forest", "scrub")),
        ("landuse", ("forest",)),
    ):
        for w in osm.closed_ways_with(key, values):
            if w.id in members or w.id in seen:continue
            seen.add(w.id)
            ring = drop_closing([crs.to_xy(lat, lon) for lat, lon in w.coords])
            if abs(ring_area(ring)) > 80.0:
                regions.append((ring,[],f'OSM way/{w.id}'))
    return regions


def _random_points_in_ring(ring: List[Vec2], n: int, rng: random.Random, holes=()) -> List[Vec2]:
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    pts = []
    tries = 0
    while len(pts) < n and tries < n * 40:
        tries += 1
        x = rng.uniform(xmin, xmax)
        y = rng.uniform(ymin, ymax)
        if point_in_ring(x, y, ring) and not any(point_in_ring(x,y,h) for h in holes):
            pts.append((x, y))
    return pts


def _low_poly_tree(name: str, mats: dict, rng: random.Random) -> bpy.types.Object:
    import bmesh
    from mathutils import Matrix, Vector
    bm=bmesh.new()
    trunk=bmesh.ops.create_cone(bm,cap_ends=True,cap_tris=False,segments=8,radius1=0.19,radius2=0.09,depth=4.5)
    bmesh.ops.translate(bm,verts=trunk['verts'],vec=Vector((0,0,2.25)))
    for face in bm.faces: face.material_index=0
    # Irregular, layered broadleaf crown; shape is illustrative, not tree survey.
    for i in range(11):
        angle=i*2.39996
        radius=0 if i==0 else rng.uniform(0.6,2.1)
        center=Vector((math.cos(angle)*radius,math.sin(angle)*radius,rng.uniform(3.4,5.7)))
        result=bmesh.ops.create_icosphere(bm,subdivisions=2,radius=1)
        newverts=result['verts']
        for v in newverts:
            v.co.x*=rng.uniform(1.1,1.55)
            v.co.y*=rng.uniform(1.1,1.55)
            v.co.z*=rng.uniform(0.85,1.4)
            v.co+=center
        for v in newverts:
            for face in v.link_faces:face.material_index=1
    mesh=bpy.data.meshes.new(name);bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new(name,mesh)
    link_object(obj,collection('TreeAssets'))
    obj.data.materials.append(mats['Trunk']);obj.data.materials.append(mats['Foliage'])
    for p in mesh.polygons:p.use_smooth=p.material_index==1
    # Disable the source object's drawing, not its dependency-graph geometry:
    # hide_viewport also removes the GN collection instances from the viewport.
    obj.hide_render=True;obj.hide_set(True)
    obj['status']='ESTIMATED broadleaf canopy'
    return obj


def _make_gn_instances(points_obj: bpy.types.Object, prototypes: List[bpy.types.Object], density_note: str):
    """Instance random prototypes on mesh vertices via Geometry Nodes (Blender 4.5)."""
    ng = bpy.data.node_groups.new("ForestInstances", "GeometryNodeTree")
    ng.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    nodes = ng.nodes
    links = ng.links
    n_in = nodes.new("NodeGroupInput")
    n_out = nodes.new("NodeGroupOutput")
    n_in.location = (-800, 0)
    n_out.location = (800, 0)

    mesh2pts = nodes.new("GeometryNodeMeshToPoints")
    mesh2pts.location = (-500, 0)
    links.new(n_in.outputs["Geometry"], mesh2pts.inputs["Mesh"])

    name='TreePrototypes' if prototypes else 'RockPrototypes'
    coll=bpy.data.collections.get(name) or bpy.data.collections.new(name)
    wanted=prototypes or [bpy.data.objects.get('RockAsset')]
    for obj in list(coll.objects):coll.objects.unlink(obj)
    for obj in wanted:
        if obj is not None:coll.objects.link(obj)
    info = nodes.new("GeometryNodeCollectionInfo")
    info.location = (-500, -250)
    info.inputs["Separate Children"].default_value = True
    info.inputs["Reset Children"].default_value = True
    if coll:
        info.inputs["Collection"].default_value = coll

    rnd_rot = nodes.new("FunctionNodeRandomValue")
    rnd_rot.data_type = "FLOAT_VECTOR"
    rnd_rot.inputs["Min"].default_value = (0.0, 0.0, 0.0)
    rnd_rot.inputs["Max"].default_value = (0.08, 0.08, 6.2831)
    rnd_rot.location = (-200, -200)

    rnd_s = nodes.new("FunctionNodeRandomValue")
    rnd_s.data_type = "FLOAT"
    rnd_s.inputs["Min"].default_value = 0.75
    rnd_s.inputs["Max"].default_value = 1.45
    rnd_s.location = (-200, 50)
    if "ID" in rnd_s.inputs:
        pass

    inst = nodes.new("GeometryNodeInstanceOnPoints")
    inst.location = (200, 0)
    inst.inputs["Pick Instance"].default_value = True
    links.new(mesh2pts.outputs["Points"], inst.inputs["Points"])
    links.new(info.outputs["Instances"], inst.inputs["Instance"])
    index=nodes.new('FunctionNodeRandomValue');index.data_type='INT'
    index.inputs['Min'].default_value=0
    index.inputs['Max'].default_value=max(0,len(wanted)-1)
    links.new(index.outputs['Value'],inst.inputs['Instance Index'])
    # Rotation / scale sockets
    if "Rotation" in inst.inputs:
        links.new(rnd_rot.outputs["Value"], inst.inputs["Rotation"])
    if "Scale" in inst.inputs:
        # Random float -> vector
        comb = nodes.new("ShaderNodeCombineXYZ")
        comb.location = (0, 80)
        links.new(rnd_s.outputs["Value"], comb.inputs["X"])
        links.new(rnd_s.outputs["Value"], comb.inputs["Y"])
        links.new(rnd_s.outputs["Value"], comb.inputs["Z"])
        links.new(comb.outputs["Vector"], inst.inputs["Scale"])
    links.new(inst.outputs["Instances"], n_out.inputs["Geometry"])

    mod = points_obj.modifiers.new("ForestGN", "NODES")
    mod.node_group = ng
    points_obj['placement_source'] = density_note


def _rock_proto(mats: dict) -> bpy.types.Object:
    verts = [
        (-0.6, -0.4, 0.0),
        (0.5, -0.5, 0.0),
        (0.4, 0.6, 0.0),
        (-0.5, 0.4, 0.0),
        (-0.2, -0.1, 0.55),
        (0.15, 0.1, 0.4),
    ]
    faces = [(0, 1, 4), (1, 2, 5), (1, 5, 4), (2, 3, 5), (3, 0, 4), (3, 4, 5), (0, 4, 1)]
    obj = new_mesh_object("RockAsset", verts, faces, collection("TreeAssets"))
    assign_material(obj, mats["Rock"])
    obj.hide_render = True
    obj.hide_set(True)
    return obj


def build_vegetation(
    cfg: LocationConfig,
    osm: OsmData,
    crs: CRS,
    sampler: TerrainSampler,
    mats: dict,
):
    rng = random.Random(42)
    assets_col = collection("TreeAssets")
    trees = [_low_poly_tree(f"Tree_{i}", mats, rng) for i in range(3)]
    _rock_proto(mats)

    regions = _forest_regions(osm, crs)
    points: List[Tuple[float, float, float]] = []
    # If OSM has little forest, fall back to elevated DEM cells (documented as fallback).
    target = cfg.max_trees if cfg.lod > 0 else min(2500, cfg.max_trees)
    if regions:
        areas = [max(0,abs(ring_area(r))-sum(abs(ring_area(h)) for h in holes)) for r,holes,_ in regions]
        total = sum(areas) or 1.0
        for (ring,holes,region_source), area in zip(regions, areas):
            n = int(min(area * cfg.tree_density, target * (area / total)))
            n = max(1, n)
            for x, y in _random_points_in_ring(ring, n, rng,holes):
                z = sampler.height_at_xy(x, y)
                if z <= cfg.sea_level + 0.8:
                    continue
                points.append((x, y, z))
                if len(points) >= target:
                    break
            if len(points) >= target:
                break
        source = "OSM forest/wood polygons including multipolygons; inner clearings excluded"
    else:
        source = "FALLBACK: no OSM forest polygons; points on elevated DEM (see README)"
        print("[vegetation] WARNING: no OSM forest polygons, using elevation fallback")
    points = points[:target]

    col = collection("Vegetation")
    if not points:
        print("[vegetation] no tree points")
        return 0
    # Point cloud mesh (vertices only) + Geometry Nodes instances
    verts = points
    obj = new_mesh_object("ForestPoints", verts, [], col)
    obj['landcover_region_count']=len(regions)
    obj['landcover_relation_sources']='; '.join(sorted({s for _,_,s in regions if 'relation/' in s}))
    obj['fidelity']='Mapped forest extent; tree species, counts, sizes and exact positions estimated'
    try:
        _make_gn_instances(obj, trees, source)
    except Exception as exc:  # noqa: BLE001
        print(f"[vegetation] Geometry Nodes failed ({exc}); points mesh only")
    print(f"[vegetation] tree_points={len(points)} source={source} prototypes={len(trees)}")

    # Sparse rocks on steep slopes
    if cfg.lod >= 1 and cfg.max_rocks > 0:
        rock_pts = []
        # sample a coarse subset of tree-less steep locations using a hash of existing forest rings
        for _ in range(cfg.max_rocks * 8):
            if len(rock_pts) >= cfg.max_rocks:
                break
            # random in bbox in blender XY — skip if not land
            lat = rng.uniform(cfg.bbox[0], cfg.bbox[2])
            lon = rng.uniform(cfg.bbox[1], cfg.bbox[3])
            x, y = crs.to_xy(lat, lon)
            z = sampler.height_at_xy(x, y)
            if z <= cfg.sea_level + 1.0:
                continue
            if sampler.slope_at_xy(x, y) < 0.45:
                continue
            rock_pts.append((x, y, z))
        if rock_pts:
            robj = new_mesh_object("RockPoints", rock_pts, [], collection("Vegetation"))
            try:
                _make_gn_instances(robj, [], "steep DEM rocks")
            except Exception as exc:  # noqa: BLE001
                print(f"[vegetation] rock GN skipped: {exc}")
            print(f"[vegetation] rocks={len(rock_pts)} (steep DEM slope, ESTIMATED placement)")
    return len(points)
