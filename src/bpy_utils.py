"""Blender 4.5 helpers."""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

import bpy
import bmesh
from mathutils import Vector

Vec2 = Tuple[float, float]
Vec3 = Tuple[float, float, float]


def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0


def collection(name: str, parent: Optional[bpy.types.Collection] = None) -> bpy.types.Collection:
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
    parent = parent or bpy.context.scene.collection
    if col.name not in [c.name for c in parent.children]:
        try:
            parent.children.link(col)
        except RuntimeError:
            pass
    return col


def link_object(obj: bpy.types.Object, col: bpy.types.Collection) -> bpy.types.Object:
    # Unlink from scene root if auto-linked
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def new_mesh_object(
    name: str,
    verts: Sequence[Vec3],
    faces: Sequence[Sequence[int]],
    col: bpy.types.Collection,
    edges: Sequence[Sequence[int]] | None = None,
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(list(verts), [list(e) for e in (edges or [])], [list(f) for f in faces])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    return link_object(obj, col)


def mesh_from_polygon(name: str, ring: Sequence[Vec2], z: float, col: bpy.types.Collection) -> Optional[bpy.types.Object]:
    pts = list(ring)
    if len(pts) >= 2 and pts[0] == pts[-1]:
        pts = pts[:-1]
    if len(pts) < 3:
        return None
    bm = bmesh.new()
    verts = [bm.verts.new((p[0], p[1], z)) for p in pts]
    bm.verts.ensure_lookup_table()
    try:
        bm.faces.new(verts)
    except ValueError:
        # Concave / non-planar: triangle fill via edges
        edges = [bm.edges.new((verts[i], verts[(i + 1) % len(verts)])) for i in range(len(verts))]
        try:
            bmesh.ops.triangle_fill(bm, edges=edges)
        except Exception:
            bm.free()
            return None
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    return link_object(obj, col)


def assign_material(obj: bpy.types.Object, mat: bpy.types.Material) -> None:
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def shade_smooth(obj: bpy.types.Object, auto_smooth: float = 60.0) -> None:
    mesh = obj.data
    for p in mesh.polygons:
        p.use_smooth = True
    if hasattr(mesh, "use_auto_smooth"):
        mesh.use_auto_smooth = True
        mesh.auto_smooth_angle = auto_smooth * 3.14159 / 180.0


def empty_marker(name: str, location: Tuple[float, float, float], col: bpy.types.Collection) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 40.0
    obj.location = location
    return link_object(obj, col)
