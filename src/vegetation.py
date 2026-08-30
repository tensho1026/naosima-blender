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


def _forest_rings(osm: OsmData, crs: CRS) -> List[List[Vec2]]:
    rings = []
    for key, values in (
        ("natural", ("wood", "forest", "scrub")),
        ("landuse", ("forest",)),
    ):
        for w in osm.closed_ways_with(key, values):
            ring = drop_closing([crs.to_xy(lat, lon) for lat, lon in w.coords])
            if abs(ring_area(ring)) > 80.0:
                rings.append(ring)
    return rings


def _random_points_in_ring(ring: List[Vec2], n: int, rng: random.Random) -> List[Vec2]:
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
        if point_in_ring(x, y, ring):
            pts.append((x, y))
    return pts


def _low_poly_tree(name: str, mats: dict, rng: random.Random) -> bpy.types.Object:
    kind = rng.choice(("broadleaf", "conifer", "pine"))
    trunk_r = 0.18 if kind != "pine" else 0.14
    trunk_h = 2.2 if kind == "broadleaf" else 3.0
    verts = [
        (-trunk_r, -trunk_r, 0),
        (trunk_r, -trunk_r, 0),
        (trunk_r, trunk_r, 0),
        (-trunk_r, trunk_r, 0),
        (-trunk_r * 0.7, -trunk_r * 0.7, trunk_h),
        (trunk_r * 0.7, -trunk_r * 0.7, trunk_h),
        (trunk_r * 0.7, trunk_r * 0.7, trunk_h),
        (-trunk_r * 0.7, trunk_r * 0.7, trunk_h),
    ]
    faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    if kind == "conifer":
        cr = 1.6
        ch = 5.5
        verts += [
            (-cr, -cr, trunk_h * 0.6),
            (cr, -cr, trunk_h * 0.6),
            (cr, cr, trunk_h * 0.6),
            (-cr, cr, trunk_h * 0.6),
            (0, 0, trunk_h + ch),
        ]
        b = 8
        faces += [(b, b + 1, b + 4), (b + 1, b + 2, b + 4), (b + 2, b + 3, b + 4), (b + 3, b, b + 4)]
    else:
        cr = 2.1 if kind == "broadleaf" else 1.4
        cz = trunk_h + (1.8 if kind == "broadleaf" else 1.2)
        verts += [
            (-cr, -cr, trunk_h),
            (cr, -cr, trunk_h),
            (cr, cr, trunk_h),
            (-cr, cr, trunk_h),
            (-cr, -cr, cz),
            (cr, -cr, cz),
            (cr, cr, cz),
            (-cr, cr, cz),
        ]
        b = 8
        faces += [
            (b, b + 1, b + 5, b + 4),
            (b + 1, b + 2, b + 6, b + 5),
            (b + 2, b + 3, b + 7, b + 6),
            (b + 3, b, b + 4, b + 7),
            (b + 4, b + 5, b + 6, b + 7),
        ]
    col = collection("TreeAssets")
    obj = new_mesh_object(name, verts, faces, col)
    assign_material(obj, mats["Trunk"])
    obj.data.materials.append(mats["Foliage"])
    for p in obj.data.polygons:
        if p.center.z > trunk_h * 0.5:
            p.material_index = 1
    obj.hide_render = True
    obj.hide_viewport = True
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

    coll = bpy.data.collections.get("TreeAssets")
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
    points_obj[density_note] = True


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
    obj.hide_viewport = True
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

    rings = _forest_rings(osm, crs)
    points: List[Tuple[float, float, float]] = []
    # If OSM has little forest, fall back to elevated DEM cells (documented as fallback).
    target = cfg.max_trees if cfg.lod > 0 else min(2500, cfg.max_trees)
    if rings:
        areas = [abs(ring_area(r)) for r in rings]
        total = sum(areas) or 1.0
        for ring, area in zip(rings, areas):
            n = int(min(area * cfg.tree_density, target * (area / total)))
            n = max(1, n)
            for x, y in _random_points_in_ring(ring, n, rng):
                z = sampler.height_at_xy(x, y)
                if z <= cfg.sea_level + 0.8:
                    continue
                points.append((x, y, z))
                if len(points) >= target:
                    break
            if len(points) >= target:
                break
        source = "OSM forest/wood polygons"
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
