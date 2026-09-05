import bpy
from pathlib import Path
root=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(root/'output/naoshima_refined.blend'))
s=bpy.context.scene
s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True
s.render.resolution_x=1440;s.render.resolution_y=960;s.render.resolution_percentage=100
out=root/'output/refined_previews';out.mkdir(exist_ok=True)
for camera,label in [('Camera_Overview','overview'),('Camera_Miyanoura','miyanoura'),('Camera_Honmura','honmura'),('Camera_NewMuseum','new_museum')]:
    s.camera=bpy.data.objects[camera];s.render.filepath=str(out/(label+'.png'))
    bpy.ops.render.render(write_still=True)
    print('RENDER_DONE',label,flush=True)
