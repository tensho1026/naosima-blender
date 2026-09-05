import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config import naoshima_config
from src.aerial import fetch_aerial
m=fetch_aerial(naoshima_config())
print('Fetched',len(m['paths']),'GSI aerial tiles')

from dataclasses import replace
for name,bbox in [('honmura_detail',(34.4565,133.9910,34.4640,134.0005)),('miyanoura_detail',(34.4520,133.9700,34.4600,133.9810))]:
    m=fetch_aerial(replace(naoshima_config(),location_id=name,bbox=bbox),zoom=18)
    print('Fetched',name,len(m['paths']),'GSI aerial tiles',flush=True)
