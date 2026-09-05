"""Georeferenced GSI seamlessphoto; source imagery, not synthesized texture."""
import json
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE = 'https://maps.gsi.go.jp/development/ichiran.html#seamlessphoto'

def tile_xy(lat, lon, zoom):
    n = 2 ** zoom
    return (lon + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n

def fetch_aerial(cfg, zoom=16):
    root = Path(__file__).resolve().parents[1] / 'data' / 'aerial' / cfg.location_id
    root.mkdir(parents=True, exist_ok=True)
    s,w,n,e = cfg.bbox
    x0,y0 = map(math.floor,tile_xy(n,w,zoom))
    x1,y1 = map(math.floor,tile_xy(s,e,zoom))
    def fetch(pair):
        x,y = pair
        path = root / f'{zoom}_{x}_{y}.jpg'
        if not path.exists():
            url = f'https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{zoom}/{x}/{y}.jpg'
            with urlopen(Request(url,headers={'User-Agent':'NaoshimaBlenderGIS/2.0'}), timeout=30) as response:
                raw = response.read()
            if not raw.startswith(b'\xff\xd8'):
                raise ValueError(f'Not JPEG: {url}')
            temp = path.with_suffix('.tmp')
            temp.write_bytes(raw)
            temp.replace(path)
        return str(path)
    with ThreadPoolExecutor(max_workers=6) as pool:
        paths = list(pool.map(fetch,[(x,y) for y in range(y0,y1+1) for x in range(x0,x1+1)]))
    meta = dict(bbox=cfg.bbox,zoom=zoom,x0=x0,y0=y0,x1=x1,y1=y1,source=SOURCE,attribution='国土地理院 / 地理院タイル',capture_date='UNKNOWN: seamless mosaic includes different survey dates',paths=paths)
    (root/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
    return meta

def apply_aerial(obj, crs, cfg, overlay=False):
    import bpy
    import numpy as np
    root = Path(__file__).resolve().parents[1] / 'data' / 'aerial' / cfg.location_id
    meta = json.loads((root/'metadata.json').read_text())
    nx,ny = meta['x1']-meta['x0']+1,meta['y1']-meta['y0']+1
    path = root/'orthophoto.png'
    if not path.exists():
        pixels = np.zeros((ny*256,nx*256,4),dtype=np.float32)
        for i,filename in enumerate(meta['paths']):
            tile = bpy.data.images.load(filename,check_existing=False)
            buf = np.empty(256*256*4,dtype=np.float32)
            tile.pixels.foreach_get(buf)
            x,y=i%nx,ny-1-i//nx
            pixels[y*256:(y+1)*256,x*256:(x+1)*256]=buf.reshape(256,256,4)
            bpy.data.images.remove(tile)
        img=bpy.data.images.new('GSI_Naoshima_Orthophoto',nx*256,ny*256)
        img.pixels.foreach_set(pixels.ravel())
        img.filepath_raw=str(path)
        img.file_format='PNG'
        img.save()
    else:
        img=bpy.data.images.load(str(path),check_existing=True)
    img.pack()
    mat=bpy.data.materials.new('GSI_Orthophoto_Georeferenced')
    mat.use_nodes=True
    nt=mat.node_tree
    bsdf=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
    bsdf.inputs['Roughness'].default_value=0.95
    tex=nt.nodes.new('ShaderNodeTexImage'); tex.image=img
    nt.links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
    if not overlay:obj.data.materials.clear()
    slot=len(obj.data.materials);obj.data.materials.append(mat)
    uv=obj.data.uv_layers.get('GSI_WebMercator') or obj.data.uv_layers.new(name='GSI_WebMercator')
    values=[]
    for v in obj.data.vertices:
        p=obj.matrix_world@v.co
        lat,lon=crs.to_latlon(p.x,p.y)
        x,y=tile_xy(lat,lon,meta['zoom'])
        values.append(((x-meta['x0'])/nx,1-(y-meta['y0'])/ny))
    for p in obj.data.polygons:
        if overlay:
            pos=obj.matrix_world@p.center
            lat,lon=crs.to_latlon(pos.x,pos.y)
            south,west,north,east=cfg.bbox
            if not (south<=lat<=north and west<=lon<=east):continue
        p.material_index=slot
        for li in p.loop_indices:
            uv.data[li].uv=values[obj.data.loops[li].vertex_index]
    obj['source']=SOURCE
    obj['imagery_date']=meta['capture_date']
    return mat
