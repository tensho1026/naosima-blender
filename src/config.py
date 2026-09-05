"""Central geographic and generation settings.

District coordinates that come from published sources are cited in comments.
Values marked APPROXIMATE / UNKNOWN are not treated as surveyed points.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Sequence, Tuple

BBox = Tuple[float, float, float, float]  # south, west, north, east


@dataclass
class DistrictSpec:
    name: str
    name_ja: str
    # Published or OSM-resolved center. If approximate, note is non-empty.
    lat: float
    lon: float
    radius_m: float
    style: str  # traditional / modern_port / fishing / museum / industrial / mixed
    note: str = ""
    osm_name_hints: Sequence[str] = ()


@dataclass
class LandmarkSpec:
    key: str
    name: str
    name_ja: str
    lat: Optional[float]
    lon: Optional[float]
    osm_name_hints: Sequence[str]
    kind: str  # approximate_building | placeholder_art | harbor
    note: str = ""
    asset_filename: str = ""


@dataclass
class LocationConfig:
    location_id: str
    display_name: str
    center_lat: float
    center_lon: float
    bbox: BBox
    sea_level: float = 0.0
    terrain_scale: float = 1.0  # horizontal and vertical, 1.0 = 1 Blender unit = 1 m
    dem_zoom: int = 14
    # GSI tile ids: "dem" (approx 10 m, z<=14), "dem5a" (5 m, typically z=15)
    dem_layer: str = "dem"
    osm_filename: str = "naoshima.osm.json"
    tree_density: float = 0.0018  # instances per m^2 on forest polygons
    max_trees: int = 7000
    max_rocks: int = 250
    max_buildings: int = 2500
    aerial: bool = False
    lod: int = 1  # 0 overview, 1 district, 2 close
    districts: Dict[str, DistrictSpec] = field(default_factory=dict)
    landmarks: List[LandmarkSpec] = field(default_factory=list)


# Wikipedia / common gazetteer center of Naoshima island:
# 34°27′30″N 133°59′00″E = 34.45833, 133.98333
NAOSHIMA_CENTER_LAT = 34.45833
NAOSHIMA_CENTER_LON = 133.98333

# Bounding box covers the main island with a sea buffer.
# Chosen from public maps so Miyanoura (west), Honmura (east),
# the southern museum coast, and the northern industrial area are inside.
# NOT a cadastral boundary.
NAOSHIMA_BBOX: BBox = (34.4350, 133.9620, 34.5080, 134.0200)

SEA_LEVEL = 0.0
TERRAIN_SCALE = 1.0
TREE_DENSITY = 0.0018

# Road widths in meters. OSM rarely has width=* on Naoshima.
# These are typical Japanese rural/island defaults — ESTIMATED.
ROAD_WIDTHS_M = {
    "motorway": 10.0,
    "trunk": 8.0,
    "primary": 6.5,
    "secondary": 5.5,
    "tertiary": 5.0,
    "unclassified": 4.0,
    "residential": 4.0,
    "living_street": 3.5,
    "service": 3.0,
    "track": 2.5,
    "path": 1.6,
    "footway": 1.5,
    "pedestrian": 3.0,
    "cycleway": 1.8,
    "steps": 1.5,
    "default": 3.5,
}

# Building height rules — ESTIMATED when OSM height / building:levels are missing.
STORY_HEIGHT_M = 3.0
DEFAULT_BUILDING_HEIGHT_M = 6.0
DEFAULT_LEVELS_BY_TYPE = {
    "house": 2,
    "detached": 2,
    "semidetached_house": 2,
    "terrace": 2,
    "apartments": 3,
    "residential": 2,
    "garages": 1,
    "garage": 1,
    "shed": 1,
    "hut": 1,
    "warehouse": 2,
    "industrial": 2,
    "retail": 2,
    "commercial": 2,
    "church": 3,
    "temple": 2,
    "shrine": 1,
    "public": 2,
    "school": 2,
    "hotel": 3,
    "roof": 1,
}

# District specs. Centers from published sources where cited; otherwise APPROXIMATE
# and refined at runtime from OSM name matches when available.
NAOSHIMA_DISTRICTS = {
    "miyanoura": DistrictSpec(
        name="Miyanoura",
        name_ja="宮浦",
        # Miyanoura Port: 34.456972, 133.974083
        # Source: public travel gazetteer listing passenger ports (Wikivoyage-style).
        lat=34.456972,
        lon=133.974083,
        radius_m=480.0,
        style="modern_port",
        note="Port coordinates from public gazetteer. Village extent radius is APPROXIMATE.",
        osm_name_hints=("宮浦", "Miyanoura", "海の駅", "Marine Station"),
    ),
    "honmura": DistrictSpec(
        name="Honmura",
        name_ja="本村",
        # Honmura Port: 34.461671, 133.998005
        lat=34.461671,
        lon=133.998005,
        radius_m=520.0,
        style="traditional",
        note="Port coordinates from public gazetteer. Village extent radius is APPROXIMATE.",
        osm_name_hints=("本村", "Honmura", "本村港"),
    ),
    "tsumuura": DistrictSpec(
        name="Tsumuura",
        name_ja="積浦",
        # Fishing settlement between Honmura and the southern museum area
        # (Benesse Art Site press kit: 宮浦・本村・積浦). Exact surveyed centroid UNKNOWN.
        lat=34.4525,
        lon=134.0015,
        radius_m=280.0,
        style="fishing",
        note="APPROXIMATE centroid. Refined from OSM if a matching place/harbour is found.",
        osm_name_hints=("積浦", "Tsumuura"),
    ),
    "gotanji": DistrictSpec(
        name="Kotohiki / Gotanji",
        name_ja="琴弾地",
        # Benesse House address is 直島町琴弾地. Beach by Tsutsuji-so / east gate.
        # Reading ごたんぢ in local tourist writing. Exact centroid UNKNOWN.
        lat=34.4478,
        lon=133.9965,
        radius_m=350.0,
        style="museum",
        note="APPROXIMATE. Named after the 琴弾地 address used by Benesse House.",
        osm_name_hints=("琴弾地", "つつじ荘", "Gotanji", "Tsutsujiso"),
    ),
    "benesse": DistrictSpec(
        name="Benesse House area",
        name_ja="ベネッセハウス周辺",
        lat=34.4465,
        lon=133.9888,
        radius_m=320.0,
        style="museum",
        note="APPROXIMATE until OSM name match. Southern highland museum/hotel area.",
        osm_name_hints=("ベネッセハウス", "Benesse House Museum"),
    ),
    "chichu": DistrictSpec(
        name="Chichu Art Museum area",
        name_ja="地中美術館周辺",
        lat=34.4474,
        lon=133.9848,
        radius_m=220.0,
        style="museum",
        note="APPROXIMATE until OSM way 地中美術館 is resolved.",
        osm_name_hints=("地中美術館", "Chichu Art Museum"),
    ),
    "lee_ufan": DistrictSpec(
        name="Lee Ufan Museum area",
        name_ja="李禹煥美術館周辺",
        # NAVITIME listing: 34.449105, 133.988673 (直島町字倉浦1390)
        lat=34.449105,
        lon=133.988673,
        radius_m=180.0,
        style="museum",
        note="Coordinates from public POI listing (NAVITIME). Building footprint from OSM if present.",
        osm_name_hints=("李禹煥", "Lee Ufan"),
    ),
    "new_museum": DistrictSpec(
        name="Naoshima New Museum area",
        name_ja="直島新美術館周辺",
        lat=34.4579024,
        lon=133.9987355,
        radius_m=180.0,
        style="museum",
        note="APPROXIMATE until OSM name match. Opened as Naoshima New Museum of Art.",
        osm_name_hints=("直島新美術館", "Naoshima New Museum"),
    ),
}

NAOSHIMA_LANDMARKS = [
    LandmarkSpec(
        key="marine_station",
        name="Marine Station Naoshima",
        name_ja="海の駅なおしま",
        lat=34.456972,
        lon=133.974083,
        osm_name_hints=("海の駅なおしま", "海の駅", "Marine Station Naoshima", "直島フェリーターミナル"),
        kind="approximate_building",
        note=(
            "Published: SANAA, ~70 m x ~52 m large thin roof, ~3600 m2, "
            "glass boxes under the roof (Naoshima Town). Approximate Landmark, not a BIM model."
        ),
        asset_filename="marine_station.blend",
    ),
    LandmarkSpec(
        key="miyanoura_port",
        name="Miyanoura Port",
        name_ja="宮浦港",
        lat=34.456972,
        lon=133.974083,
        osm_name_hints=("宮浦港", "Miyanoura Port"),
        kind="harbor",
        note="Harbor identified from gazetteer + OSM harbour/ferry tags.",
    ),
    LandmarkSpec(
        key="chichu",
        name="Chichu Art Museum",
        name_ja="地中美術館",
        lat=None,
        lon=None,
        osm_name_hints=("地中美術館", "Chichu Art Museum"),
        kind="approximate_building",
        note=(
            "Most of the building is underground (Benesse Art Site). "
            "Approximate Landmark: low concrete courts only. Precise interior UNKNOWN."
        ),
        asset_filename="chichu.blend",
    ),
    LandmarkSpec(
        key="lee_ufan",
        name="Lee Ufan Museum",
        name_ja="李禹煥美術館",
        lat=34.449105,
        lon=133.988673,
        osm_name_hints=("李禹煥美術館", "Lee Ufan Museum"),
        kind="approximate_building",
        note="Ando concrete volumes in a valley; exterior is Approximate Landmark.",
        asset_filename="lee_ufan.blend",
    ),
    LandmarkSpec(
        key="benesse_house",
        name="Benesse House",
        name_ja="ベネッセハウス",
        lat=None,
        lon=None,
        osm_name_hints=("ベネッセハウス", "Benesse House Museum"),
        kind="approximate_building",
        note="Ando hotel/museum on the southern highland. Approximate Landmark.",
        asset_filename="benesse_house.blend",
    ),
    LandmarkSpec(
        key="new_museum",
        name="Naoshima New Museum of Art",
        name_ja="直島新美術館",
        lat=None,
        lon=None,
        osm_name_hints=("直島新美術館", "Naoshima New Museum"),
        kind="approximate_building",
        note="Approximate Landmark unless a handmade asset is supplied.",
        asset_filename="new_museum.blend",
    ),
    LandmarkSpec(
        key="red_pumpkin",
        name="Red Pumpkin (placeholder)",
        name_ja="赤かぼちゃ（位置のみ）",
        lat=34.4568,
        lon=133.9737,
        osm_name_hints=("赤かぼちゃ", "Red Pumpkin"),
        kind="placeholder_art",
        note="Artwork is NOT modeled. Landmark Placeholder only. Position APPROXIMATE near Miyanoura green.",
    ),
    LandmarkSpec(
        key="yellow_pumpkin",
        name="Yellow Pumpkin (placeholder)",
        name_ja="南瓜（位置のみ）",
        lat=None,
        lon=None,
        osm_name_hints=("南瓜", "Yellow Pumpkin", "Pumpkin"),
        kind="placeholder_art",
        note="Artwork is NOT modeled. Placeholder only if OSM node exists.",
    ),
]


def naoshima_config() -> LocationConfig:
    return LocationConfig(
        location_id="naoshima",
        display_name="Naoshima",
        center_lat=NAOSHIMA_CENTER_LAT,
        center_lon=NAOSHIMA_CENTER_LON,
        bbox=NAOSHIMA_BBOX,
        sea_level=SEA_LEVEL,
        terrain_scale=TERRAIN_SCALE,
        dem_zoom=14,
        dem_layer="dem",
        osm_filename="naoshima.osm.json",
        tree_density=TREE_DENSITY,
        max_trees=7000,
        max_rocks=250,
        max_buildings=2500,
        lod=1,
        districts=dict(NAOSHIMA_DISTRICTS),
        landmarks=list(NAOSHIMA_LANDMARKS),
    )


def location_from_circle(lat: float, lon: float, radius_m: float, location_id: str = "custom") -> LocationConfig:
    """Future entry point for Teshima / Ogijima / Megijima, etc."""
    import math

    dlat = radius_m / 111_320.0
    dlon = radius_m / (111_320.0 * max(0.2, math.cos(math.radians(lat))))
    bbox = (lat - dlat, lon - dlon, lat + dlat, lon + dlon)
    cfg = naoshima_config()
    return replace(
        cfg,
        location_id=location_id,
        display_name=location_id,
        center_lat=lat,
        center_lon=lon,
        bbox=bbox,
        osm_filename=f"{location_id}.osm.json",
        districts={},
        landmarks=[],
    )


USER_AGENT = "NaoshimaBlenderGenerator/1.0 (GIS visualization; OSM ODbL; GSI tiles)"
OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
GSI_TILE_BASE = "https://cyberjapandata.gsi.go.jp/xyz"

# Preview cameras look from these offsets (east, north, up) in meters relative to a target.
CAMERA_PRESETS = {
    "Camera_Overview": {"target": "center", "offset": (-2800.0, -3200.0, 1600.0), "lens": 35.0},
    "Camera_Miyanoura": {"target": "miyanoura", "offset": (-180.0, -90.0, 45.0), "lens": 28.0},
    "Camera_Honmura": {"target": "honmura", "offset": (160.0, -140.0, 55.0), "lens": 32.0},
    "Camera_Benesse": {"target": "benesse", "offset": (-80.0, -220.0, 70.0), "lens": 32.0},
}

RENDER_SAMPLES = 12
RENDER_RESOLUTION = (1280, 720)
