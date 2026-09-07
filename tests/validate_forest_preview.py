"""Evaluate actual instance output for sparse editing and full-density render branch."""
import bpy
from pathlib import Path

root = Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(root / 'output/naoshima_refined.blend'))
forest = bpy.data.objects['ForestPoints']
ng = next(m.node_group for m in forest.modifiers if m.type == 'NODES')
switch = ng.nodes['ForestPreviewSwitch']
link = switch.inputs['Switch'].links[0]
source = link.from_socket
assert source.node.bl_idname == 'GeometryNodeIsViewport'

def instances():
    forest.update_tag()
    bpy.context.view_layer.update()
    return {i.persistent_id[0]: tuple(i.matrix_world.translation)
            for i in bpy.context.evaluated_depsgraph_get().object_instances
            if i.is_instance and i.parent and i.parent.original == forest}

preview = instances()
dg = bpy.context.evaluated_depsgraph_get()
for tree in bpy.data.collections['TreePrototypes'].objects:
    reduction = tree.modifiers['ViewportCrownReduction']
    assert reduction.show_viewport and not reduction.show_render
    original = tree.data
    light = tree.evaluated_get(dg).data
    assert len(light.polygons) < len(original.polygons) * .3
    assert {p.material_index for p in light.polygons} == {0, 1}, 'Lost trunk or foliage colour'
    for axis in range(3):
        a = [v.co[axis] for v in original.vertices]
        b = [v.co[axis] for v in light.vertices]
        assert abs((max(a)-min(a)) - (max(b)-min(b))) < .15 * (max(a)-min(a)), 'Crown silhouette collapsed'
stride = int(ng.nodes['ViewportTreeStride'].outputs[0].default_value)
assert len(preview) == (len(forest.data.vertices) + stride - 1) // stride
try:
    # Exercise the same false branch selected by Is Viewport during rendering.
    ng.links.remove(link)
    switch.inputs['Switch'].default_value = False
    full = instances()
    assert len(full) == len(forest.data.vertices)
    assert set(preview.values()).issubset(set(full.values()))
finally:
    ng.links.new(source, switch.inputs['Switch'])
print('FOREST_PREVIEW_PASS', {'viewport': len(preview), 'render_branch': len(full), 'stride': stride}, flush=True)
