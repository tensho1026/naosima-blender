import bpy,sys
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from src.coordinates import CRS
from src.config import naoshima_config
bpy.ops.wm.open_mainfile(filepath=str(root/'output/naoshima_refined.blend'))
x,y=CRS(naoshima_config()).to_xy(34.4582,133.9758)
c=bpy.data.objects['Camera_Miyanoura'];c.location=(x-70,y-90,190)
c.rotation_euler=(Vector((x,y,8))-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=240
s=bpy.context.scene;s.camera=c;s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True
s.render.resolution_x=1200;s.render.resolution_y=1000;s.render.resolution_percentage=100
s.render.filepath=str(root/'output/refined_previews/miyanoura_roof_review.png')
bpy.ops.render.render(write_still=True)
