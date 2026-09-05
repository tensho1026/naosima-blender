"""Clip a DEM to joined OSM coastline polygons with Shapely (offline cached GIS).
Run with .venv-gis/bin/python; resulting NPZ loads in Blender without Shapely.
"""
import sys, json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,box
from shapely.ops import triangulate,unary_union
from src.config import naoshima_config
from src.osm import load_or_fetch_osm
from src.dem import load_or_fetch_dem,TerrainSampler
from src.coordinates import CRS
cfg=naoshima_config();crs=CRS(cfg)
osm=load_or_fetch_osm(cfg);dem=load_or_fetch_dem(cfg);sampler=TerrainSampler(dem,crs)
remaining=[list(w.nodes) for w in osm.ways_with('natural',['coastline']) if len(w.nodes)>1]
rings=[];open_chains=0
while remaining:
    chain=remaining.pop()
    while chain[0]!=chain[-1]:
        found=False
        for i,other in enumerate(remaining):
            if chain[-1]==other[0]:chain+=other[1:]
            elif chain[-1]==other[-1]:chain+=other[-2::-1]
            elif chain[0]==other[-1]:chain=other[:-1]+chain
            elif chain[0]==other[0]:chain=other[:0:-1]+chain
            else:continue
            remaining.pop(i);found=True;break
        if not found:break
    if chain[0]==chain[-1]:
        poly=Polygon([crs.to_xy(osm.nodes[n].lat,osm.nodes[n].lon) for n in chain])
        if not poly.is_valid:poly=shapely.make_valid(poly)
        if poly.area>10:rings.append(poly)
    else:open_chains+=1
main=next(p for p in rings if p.contains(Point(0,0)))
print('Closed coast polygons',len(rings),'mainland area',main.area,'open chains',open_chains,flush=True)
# Main island plus mapped closed offshore islands inside DEM coverage.
land=unary_union(rings)
shapely.prepare(land)
xs=sampler._xs;ys=sampler._ys
verts=[];faces=[];lookup={}
def vertex(x,y):
    key=(round(x,6),round(y,6))
    if key not in lookup:
        lookup[key]=len(verts)
        verts.append((x,y,max(.15,sampler.height_at_xy(x,y))))
    return lookup[key]
def add_triangle(coords):
    ids=[vertex(float(x),float(y)) for x,y in coords]
    if len(set(ids))==3:
        a,b,c=[verts[i] for i in ids]
        if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<0:ids.reverse()
        faces.append(ids)
for j in range(len(ys)-1):
    boxes=shapely.box(xs[:-1],ys[j+1],xs[1:],ys[j])
    inside=shapely.covers(land,boxes)
    hit=shapely.intersects(land,boxes)
    for i in np.flatnonzero(hit):
        if inside[i]:
            a=(xs[i],ys[j]);b=(xs[i+1],ys[j]);c=(xs[i+1],ys[j+1]);d=(xs[i],ys[j+1])
            add_triangle((a,d,c));add_triangle((a,c,b))
        else:
            cut=land.intersection(boxes[i])
            parts=list(cut.geoms) if hasattr(cut,'geoms') else [cut]
            for part in parts:
                if part.geom_type!='Polygon' or part.area<1e-8:continue
                for tri in triangulate(part):
                    if part.covers(tri):add_triangle(list(tri.exterior.coords)[:3])
    if j%200==0:print('row',j,'vertices',len(verts),flush=True)
# Vertical edge faces close the exact mapped coastline to below sea level.
from collections import Counter
edges=Counter(tuple(sorted((a,b))) for f in faces for a,b in zip(f,f[1:]+f[:1]))
boundary=[(a,b) for f in faces for a,b in zip(f,f[1:]+f[:1]) if edges[tuple(sorted((a,b)))]==1]
lower={}
for a,b in boundary:
    for i in (a,b):
        if i not in lower:
            x,y,z=verts[i];lower[i]=len(verts);verts.append((x,y,-2))
    faces.extend([(b,a,lower[a]),(b,lower[a],lower[b])])
out=ROOT/'data/cache';out.mkdir(exist_ok=True,parents=True)
np.savez_compressed(out/'coastal_terrain.npz',vertices=np.array(verts,dtype=np.float32),faces=np.array(faces,dtype=np.int32))
report=dict(vertices=len(verts),triangles=len(faces),closed_coast_polygons=len(rings),unclosed_coast_chains=open_chains,main_island_area_m2=main.area,source='OSM coastline + GSI DEM; no surveyed coastal elevations',bbox=cfg.bbox,dem_layer=cfg.dem_layer,dem_zoom=cfg.dem_zoom)
(out/'coastal_terrain.json').write_text(json.dumps(report,indent=2))
print(report,flush=True)
