"""Render the current coloured harbour without changing the saved scene."""
from pathlib import Path
import bpy

root = Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(root / 'output/naoshima_refined.blend'))
scene = bpy.context.scene
scene.camera = bpy.data.objects['Camera_Miyanoura']
scene.render.engine = 'CYCLES'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x = 1440
scene.render.resolution_y = 960
scene.render.resolution_percentage = 100
scene.render.filepath = str(root / 'output/refined_previews/miyanoura_colour.png')
bpy.ops.render.render(write_still=True)
