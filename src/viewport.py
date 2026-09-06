"""Keep editable viewport colours consistent with the authored shader palette."""
import bpy


def sync_material_colours():
    count = 0
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        shader = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if shader is None:
            continue
        socket = shader.inputs['Base Color']
        colour = tuple(socket.default_value)
        if socket.is_linked:
            node = socket.links[0].from_node
            if node.type == 'VALTORGB':
                colour = tuple(node.color_ramp.evaluate(.5))
            elif node.type == 'TEX_BRICK':
                a, b = node.inputs['Color1'].default_value, node.inputs['Color2'].default_value
                colour = tuple((x + y) / 2 for x, y in zip(a, b))
            elif node.type == 'TEX_IMAGE':
                # Solid mode cannot show the separate georeferenced UV layers.
                # These are palette proxies only; Material Preview uses the images.
                colour = (.15, .17, .16, 1) if 'Roofs' in mat.name else (.19, .27, .12, 1)
                mat['solid_colour_note'] = 'Approximate overview colour; use Material Preview for source imagery'
            else:
                continue
        mat.diffuse_color = (*colour[:3], 1)
        mat.roughness = shader.inputs['Roughness'].default_value
        mat.metallic = shader.inputs['Metallic'].default_value
        count += 1
    return count


def setup_colour_view():
    count = sync_material_colours()
    scene = bpy.context.scene
    camera = bpy.data.objects.get('Camera_Miyanoura')
    if camera:
        scene.camera = camera
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != 'VIEW_3D':
                continue
            space = area.spaces.active
            space.shading.color_type = 'MATERIAL'
            space.shading.background_type = 'WORLD'
            if screen.name == 'Layout':
                space.shading.type = 'MATERIAL'
                space.shading.use_scene_world = True
                space.shading.use_scene_lights = True
                space.clip_end = 30000
                space.overlay.show_overlays = False
                if camera:
                    space.region_3d.view_perspective = 'CAMERA'
    scene['colour_display'] = 'Material Preview with summer scene lighting; solid colours also synchronized'
    return count
