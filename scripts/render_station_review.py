import bpy
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(root/'output/naoshima_refined.blend'))
roof=bpy.data.objects['MarineStation_OSM_Roof'];points=[roof.matrix_world@v.co for v in roof.data.vertices]
x=sum(p.x for p in points)/len(points);y=sum(p.y for p in points)/len(points);z=min(p.z for p in points)-4.6
cam=bpy.data.objects['Camera_Miyanoura'];cam.location=(x-45,y-23,z+1.7)
cam.rotation_euler=(Vector((x,y,z+2.3))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=25
s=bpy.context.scene;s.camera=cam;s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True
s.render.resolution_x=1200;s.render.resolution_y=800;s.render.resolution_percentage=100
s.render.filepath=str(root/'output/refined_previews/station_close.png');bpy.ops.render.render(write_still=True)
