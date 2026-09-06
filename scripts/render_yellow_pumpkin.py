from pathlib import Path
import bpy
root=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(root/'output/naoshima_refined.blend'))
s=bpy.context.scene;s.camera=bpy.data.objects['Camera_YellowPumpkin']
s.render.engine='CYCLES';s.cycles.samples=40;s.cycles.use_denoising=True
s.render.resolution_x=1200;s.render.resolution_y=900;s.render.resolution_percentage=100
s.render.filepath=str(root/'output/refined_previews/yellow_pumpkin.png')
bpy.ops.render.render(write_still=True)
