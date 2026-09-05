"""Stable per-building exterior research ledger; unverified is never 'complete'."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.config import naoshima_config
from src.coordinates import drop_closing
from src.osm import load_or_fetch_osm

# Working research envelope, not an administrative boundary or proof of coverage.
BBOX=(34.4515,133.9690,34.4640,133.9815)
DEST=ROOT/'data/reconstruction/miyanoura_buildings.json'

def main():
    previous=json.loads(DEST.read_text()) if DEST.exists() else {'buildings':[]}
    old={row['osm_way_id']:row for row in previous['buildings']}
    rows=[]
    for way in load_or_fetch_osm(naoshima_config()).ways:
        if 'building' not in way.tags:continue
        ring=drop_closing(way.coords)
        if not ring:continue
        lat=sum(p[0] for p in ring)/len(ring);lon=sum(p[1] for p in ring)/len(ring)
        if not (BBOX[0]<=lat<=BBOX[2] and BBOX[1]<=lon<=BBOX[3]):continue
        row=old.get(way.id,{'osm_way_id':way.id,'exterior_status':'unverified',
            'reference_urls':[], 'observed':{},
            'unknown':['height','roof_geometry','wall_materials','front_openings','side_openings','rear_openings','boundary_details']})
        row.update(name=way.tags.get('name',''),centroid_latlon=[lat,lon],osm_tags=way.tags,
                   footprint_latlon=ring,map_url=f'https://www.openstreetmap.org/way/{way.id}')
        if way.id==1361954806:
            row.update(exterior_status='front_photo_model_in_progress',reference_urls=[
                'https://naoshima.net/ja/shop/shop-6795/','https://artisland.jp/pages/access'],
                observed={'front':'entrance left, four display bays right, three wooden planters',
                          'walls':'dark brown vertical boards','rainwater_goods':'reddish brown'},
                unknown=['exact_dimensions','main_roof_tile_layout','side_openings','rear_openings','weathering'])
        if way.id==1361901029:
            row.update(exterior_status='photo_model_in_progress',reference_urls=[
                'https://naoshima.net/ja/foods/foods-6754/'],
                observed={'massing':'taller main house plus single-storey detached dining space',
                          'walls':'dark weathered vertical timber boards',
                          'site':'raised timber deck, planters, sculpted trees, green parasol'},
                unknown=['photo_to_footprint_alignment','roof_subvolumes','exact_dimensions','rear_openings'])
        if way.id==1307364185:
            row.update(exterior_status='photo_model_in_progress',reference_urls=[
                'https://www.postmap.org/photo/1206913',
                'https://location.sevenbank.co.jp/sevenbank/spot/detail?code=0000033134'],
                observed={'front':'left brown brick pier; right-side entry; frosted lower glazing; red post box',
                          'reference_date':'2024-12-18 after relocation'},
                unknown=['exact_dimensions','rear','roof_equipment','fine_signage','parking_extent'])
        rows.append(row)
    rows.sort(key=lambda r:r['osm_way_id'])
    document={'scope':'Miyanoura working research envelope; not an exhaustive real-world building census',
              'bbox_south_west_north_east':BBOX,'source':'OpenStreetMap contributors, ODbL',
              'completion_rule':'Every exterior must be individually evidenced; generic geometry and passing structural tests are not completion.',
              'buildings':rows}
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(document,ensure_ascii=False,indent=2)+'\n')
    print(f'{len(rows)} mapped footprints; {sum(r["exterior_status"]=="unverified" for r in rows)} unverified')

if __name__=='__main__':main()
