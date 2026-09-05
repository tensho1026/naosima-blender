import bpy
from pathlib import Path
root=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(root/'output/naoshima_refined.blend'))
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True
s.render.resolution_x=1440;s.render.resolution_y=960;s.render.resolution_percentage=100
for name,label in [('Camera_Ferry','ferry'),('Camera_Miyanoura','miyanoura_summer'),('Camera_ArtIslandCenter','art_island_center'),('Camera_NaoPAM','naopam')]:
    s.camera=bpy.data.objects[name];s.render.filepath=str(root/'output/refined_previews'/(label+'.png'))
    bpy.ops.render.render(write_still=True)
    print('RENDER_DONE',label,flush=True)
